from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, AutomationRequest
from services.orchestrator.engine import AutomationOrchestrator
from services.policy_engine.service import SUPPORTED_ACTIONS
from services.servicenow_sim.external_client import ExternalServiceNowClient


@dataclass
class ExternalCaseAgentRunResult:
    scanned: int
    processed: int
    resolved: int
    awaiting_approval: int
    manual_attention: int
    errors: int
    case_numbers: list[str]


def _to_text(case: dict) -> str:
    request_type = case.get('request_type')
    params = case.get('params') or {}
    targets = case.get('targets') or ['ol9server1']
    target_text = ' y '.join(targets)

    if request_type == 'create_user':
        return f"Crear usuario {params.get('username', 'operador_demo')} en {target_text} sin sudo"
    if request_type == 'delete_user':
        return f"Eliminar usuario {params.get('username', 'operador_demo')} en {target_text}"
    if request_type == 'reset_password':
        return f"Resetear contraseña de usuario {params.get('username', 'operador_demo')} en {target_text}"
    if request_type == 'add_ssh_key':
        return (
            f"Agregar clave SSH \"{params.get('ssh_public_key', '')}\" al usuario "
            f"{params.get('username', 'operador_demo')} en {target_text}"
        )
    if request_type == 'create_directory':
        return f"Crear carpeta {params.get('directory_path', '/opt/automation_factory_lite/work')} en {target_text}"
    if request_type == 'install_service':
        return f"Instalar {params.get('service_name', 'nginx')} en {target_text}"
    if request_type == 'install_package':
        return f"Instalar paquete {params.get('package_name', 'jq')} en {target_text}"
    if request_type == 'restart_service':
        return f"Reiniciar servicio {params.get('service_name', 'nginx')} en {target_text}"
    if request_type == 'manage_service':
        return f"{params.get('state', 'start')} {params.get('service_name', 'nginx')} en {target_text}"
    if request_type == 'install_agent':
        return f"Instalar agente {params.get('agent_name', 'cockpit')} en {target_text}"
    if request_type == 'deploy_template':
        return f"Desplegar plantilla segura en {params.get('destination_path', '/etc/nginx/conf.d/service.conf')} para {target_text}"
    if request_type == 'check_uptime':
        return f"Obtener uptime en {target_text}"
    if request_type == 'check_patch_status':
        return f"Verificar estado de parches en {target_text}"
    if request_type == 'check_connectivity':
        return f"Chequeo de conectividad a {params.get('connectivity_target', '8.8.8.8')} desde {target_text}"
    return str(case.get('short_description') or 'Solicitud ServiceNow')


def run_pending_cases_via_external(
    db: Session,
    *,
    orchestrator: AutomationOrchestrator,
    client: ExternalServiceNowClient,
    limit: int = 10,
) -> ExternalCaseAgentRunResult:
    queue = client.list_cases(limit=limit)
    candidates = [item for item in queue if item.get('state') in {'new', 'open', 'reopened'}][:limit]

    processed = 0
    resolved = 0
    awaiting = 0
    manual = 0
    errors = 0
    case_numbers: list[str] = []

    for case in candidates:
        case_number = str(case.get('number'))
        case_numbers.append(case_number)
        try:
            client.update_case(
                case_number,
                {
                    'state': 'in_progress',
                    'append_event': {
                        'actor': 'afl_mcp_agent',
                        'event_type': 'agent_claimed',
                        'message': 'Case claimed by Automation Factory Lite via MCP bridge.',
                    },
                },
            )

            request_type = case.get('request_type')
            if request_type and request_type not in SUPPORTED_ACTIONS:
                reason = f"Tipo '{request_type}' fuera del catálogo permitido."
                client.update_case(
                    case_number,
                    {
                        'state': 'needs_manual_attention',
                        'resolution_notes': reason,
                        'append_event': {
                            'actor': 'afl_mcp_agent',
                            'event_type': 'manual_attention_required',
                            'message': 'Unsupported request type; escalated for manual attention.',
                            'payload': {'request_type': request_type},
                        },
                    },
                )
                db.add(
                    AuditLog(
                        request_id=None,
                        ticket_id=case_number,
                        event_type='servicenow_case_escalated',
                        message='External ServiceNow case escalated.',
                        payload={'request_type': request_type},
                    )
                )
                db.commit()
                processed += 1
                manual += 1
                continue

            request = AutomationRequest(
                raw_request=_to_text(case),
                requester=str(case.get('requested_by') or 'servicenow.user'),
                ticket_id=case_number,
            )
            db.add(request)
            db.commit()
            db.refresh(request)

            final_request = orchestrator.process_request(db, request)

            next_state = 'resolved'
            if final_request.status == 'pending_approval':
                next_state = 'awaiting_approval'
                awaiting += 1
            elif final_request.status not in {'executed', 'validated'}:
                next_state = 'needs_manual_attention'
                manual += 1
            else:
                resolved += 1

            client.update_case(
                case_number,
                {
                    'state': next_state,
                    'resolution_notes': final_request.rejection_reason
                    or final_request.risk_reason
                    or f'Processed at {datetime.utcnow().isoformat()}',
                    'automation_request_id': final_request.id,
                    'execution_id': final_request.execution_id,
                    'append_event': {
                        'actor': 'afl_mcp_agent',
                        'event_type': 'agent_processed',
                        'message': 'Case processed through Automation Factory Lite.',
                        'payload': {
                            'request_status': final_request.status,
                            'automation_request_id': final_request.id,
                            'execution_id': final_request.execution_id,
                        },
                    },
                },
            )

            db.add(
                AuditLog(
                    request_id=final_request.id,
                    ticket_id=case_number,
                    event_type='servicenow_case_processed',
                    message='External ServiceNow case processed.',
                    payload={'state': next_state, 'request_status': final_request.status},
                )
            )
            db.commit()
            processed += 1
        except Exception as exc:
            errors += 1
            try:
                client.update_case(
                    case_number,
                    {
                        'state': 'needs_manual_attention',
                        'resolution_notes': f'Error during MCP processing: {exc}',
                        'append_event': {
                            'actor': 'afl_mcp_agent',
                            'event_type': 'agent_error',
                            'message': 'Unexpected processing error.',
                            'payload': {'error': str(exc)},
                        },
                    },
                )
            except Exception:
                pass

            db.add(
                AuditLog(
                    request_id=None,
                    ticket_id=case_number,
                    event_type='servicenow_case_error',
                    message='Error while processing external ServiceNow case.',
                    payload={'error': str(exc)},
                )
            )
            db.commit()

    return ExternalCaseAgentRunResult(
        scanned=len(candidates),
        processed=processed,
        resolved=resolved,
        awaiting_approval=awaiting,
        manual_attention=manual,
        errors=errors,
        case_numbers=case_numbers,
    )
