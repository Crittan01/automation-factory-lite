from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import AuditLog, AutomationRequest, ServiceNowCase
from services.orchestrator.engine import AutomationOrchestrator
from services.servicenow_sim.service import (
    add_case_event,
    case_to_request_text,
    list_open_cases,
    mark_case_manual_attention,
    request_type_supported,
)


@dataclass
class CaseAgentRunResult:
    scanned: int
    processed: int
    resolved: int
    awaiting_approval: int
    manual_attention: int
    errors: int
    case_numbers: list[str]


def _manual_recommendations(case: ServiceNowCase, reason: str) -> list[str]:
    return [
        f'Validar alcance del caso {case.number} contra catálogo permitido.',
        'Si requiere política adicional, solicitar aprobación formal en UI.',
        f'Reason principal detectada: {reason}',
    ]


def run_pending_cases(
    db: Session,
    *,
    orchestrator: AutomationOrchestrator,
    limit: int = 10,
) -> CaseAgentRunResult:
    candidates = list_open_cases(db, limit=limit)

    processed = 0
    resolved = 0
    awaiting = 0
    manual = 0
    errors = 0
    case_numbers: list[str] = []

    for case in candidates:
        case_numbers.append(case.number)
        case.state = 'in_progress'
        case.last_agent_run_at = datetime.utcnow()
        db.add(case)
        add_case_event(
            db,
            case=case,
            actor='snow_agent',
            event_type='agent_claimed',
            message='Case claimed by automation agent.',
            payload={},
        )
        db.commit()

        try:
            if not request_type_supported(case.request_type):
                reason = (
                    f"Tipo de solicitud '{case.request_type}' fuera de catálogo permitido. "
                    'Caso escalado a atención manual.'
                )
                mark_case_manual_attention(db, case, reason)
                db.add(
                    AuditLog(
                        request_id=None,
                        ticket_id=case.number,
                        event_type='servicenow_case_escalated',
                        message='Case escalated due unsupported request_type.',
                        payload={'request_type': case.request_type, 'suggestions': _manual_recommendations(case, reason)},
                    )
                )
                db.commit()
                manual += 1
                processed += 1
                continue

            text = case_to_request_text(case)
            request = AutomationRequest(
                raw_request=text,
                requester=case.requested_by,
                ticket_id=case.number,
            )
            db.add(request)
            db.commit()
            db.refresh(request)

            final_request = orchestrator.process_request(db, request)
            case.automation_request_id = final_request.id
            case.execution_id = final_request.execution_id
            case.last_agent_run_at = datetime.utcnow()

            if final_request.status == 'executed':
                case.state = 'resolved'
                case.resolution_notes = (
                    f'Automatización ejecutada con éxito. request_id={final_request.id}, '
                    f'execution_id={final_request.execution_id}'
                )
                resolved += 1
            elif final_request.status == 'pending_approval':
                case.state = 'awaiting_approval'
                case.resolution_notes = (
                    'Caso requiere aprobación humana antes de ejecutar. '
                    f'request_id={final_request.id}'
                )
                awaiting += 1
            else:
                reason = final_request.rejection_reason or final_request.risk_reason or 'No fue posible auto-atender.'
                case.state = 'needs_manual_attention'
                case.resolution_notes = reason
                manual += 1

            db.add(case)
            add_case_event(
                db,
                case=case,
                actor='snow_agent',
                event_type='agent_processed',
                message='Case processed by automation agent.',
                payload={
                    'automation_request_id': final_request.id,
                    'execution_id': final_request.execution_id,
                    'request_status': final_request.status,
                },
            )
            db.add(
                AuditLog(
                    request_id=final_request.id,
                    ticket_id=case.number,
                    event_type='servicenow_case_processed',
                    message='ServiceNow case processed by agent.',
                    payload={
                        'case_number': case.number,
                        'case_state': case.state,
                        'request_status': final_request.status,
                    },
                )
            )
            db.commit()
            processed += 1
        except Exception as exc:
            errors += 1
            case.state = 'needs_manual_attention'
            case.resolution_notes = f'Error en agente: {exc}'
            case.last_agent_run_at = datetime.utcnow()
            db.add(case)
            add_case_event(
                db,
                case=case,
                actor='snow_agent',
                event_type='agent_error',
                message='Unexpected error while processing case.',
                payload={'error': str(exc)},
            )
            db.add(
                AuditLog(
                    request_id=None,
                    ticket_id=case.number,
                    event_type='servicenow_case_error',
                    message='Error while processing ServiceNow case.',
                    payload={'error': str(exc), 'case_number': case.number},
                )
            )
            db.commit()

    return CaseAgentRunResult(
        scanned=len(candidates),
        processed=processed,
        resolved=resolved,
        awaiting_approval=awaiting,
        manual_attention=manual,
        errors=errors,
        case_numbers=case_numbers,
    )
