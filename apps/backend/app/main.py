from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
import importlib.util
import uuid

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import and_, func, select, text
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine, get_db
from app.models import (
    ApprovalDecision,
    AuditLog,
    AutomationCatalogEntry,
    AutomationRequest,
    CMDBHost,
    ExecutionRecord,
    ServiceNowCase,
    TimelineEvent,
)
from app.schemas import (
    ApprovalInput,
    ApprovalResponse,
    CatalogResponse,
    ExecutionResponse,
    HostResponse,
    RequestCreate,
    RequestResponse,
    ServiceNowAgentRunResponse,
    ServiceNowCaseCreate,
    ServiceNowCaseDetailResponse,
    ServiceNowCaseEventResponse,
    ServiceNowCaseResponse,
    TimelineEventResponse,
)
from app.settings import get_settings
from services.awx_client.client import build_awx_client
from services.cmdb_sim.service import seed_cmdb_hosts
from services.itsm_notifier.service import notify_ticket_event
from services.orchestrator.engine import AutomationOrchestrator, OrchestratorConfig
from services.servicenow_sim.agent import run_pending_cases
from services.servicenow_sim.external_agent import run_pending_cases_via_external
from services.servicenow_sim.external_client import ExternalServiceNowClient
from services.servicenow_sim.service import (
    add_case_event,
    create_case as create_servicenow_case,
    get_case_by_number,
    list_case_events,
    list_cases as list_servicenow_cases,
    seed_demo_cases,
    seed_demo_cases_force,
)

settings = get_settings()
ROOT_DIR = Path(__file__).resolve().parents[3]
orchestrator = AutomationOrchestrator(OrchestratorConfig(root_dir=str(ROOT_DIR), settings=settings))


def _generate_ticket_id() -> str:
    return f"AFL-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8]}"


def _column_exists(db: Session, table_name: str, column_name: str) -> bool:
    dialect = db.bind.dialect.name if db.bind else ''
    if dialect == 'sqlite':
        rows = db.execute(text(f'PRAGMA table_info({table_name})')).fetchall()
        columns = {str(row[1]) for row in rows}
        return column_name in columns

    query = text(
        'SELECT 1 FROM information_schema.columns '
        'WHERE table_name = :table_name AND column_name = :column_name'
    )
    return db.execute(query, {'table_name': table_name, 'column_name': column_name}).first() is not None


def _ensure_runtime_schema(db: Session) -> None:
    if not _column_exists(db, 'automation_requests', 'ticket_id'):
        db.execute(text('ALTER TABLE automation_requests ADD COLUMN ticket_id VARCHAR(128)'))
        db.execute(
            text(
                "UPDATE automation_requests SET ticket_id = :default_ticket "
                "WHERE ticket_id IS NULL OR ticket_id = ''"
            ),
            {'default_ticket': 'AFL-LEGACY'},
        )
    if not _column_exists(db, 'execution_records', 'ticket_id'):
        db.execute(text('ALTER TABLE execution_records ADD COLUMN ticket_id VARCHAR(128)'))
    if not _column_exists(db, 'audit_logs', 'ticket_id'):
        db.execute(text('ALTER TABLE audit_logs ADD COLUMN ticket_id VARCHAR(128)'))

    db.execute(text('CREATE INDEX IF NOT EXISTS ix_automation_requests_ticket_id ON automation_requests (ticket_id)'))
    db.execute(text('CREATE INDEX IF NOT EXISTS ix_execution_records_ticket_id ON execution_records (ticket_id)'))
    db.execute(text('CREATE INDEX IF NOT EXISTS ix_audit_logs_ticket_id ON audit_logs (ticket_id)'))
    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        _ensure_runtime_schema(db)
        seed_cmdb_hosts(
            db,
            settings.target_host_1,
            settings.target_host_1_name,
            settings.target_host_2,
            settings.target_host_2_name,
        )
        seed_demo_cases(db, [settings.target_host_1_name, settings.target_host_2_name])
    yield


app = FastAPI(title='Automation Factory Lite API', version='1.0.0', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


def _build_external_servicenow_client(*, check_health: bool = False) -> ExternalServiceNowClient:
    if not settings.servicenow_mcp_enabled:
        raise HTTPException(status_code=503, detail='ServiceNow MCP bridge is disabled by configuration.')
    if not settings.servicenow_external_enabled:
        raise HTTPException(status_code=503, detail='ServiceNow external service is disabled by configuration.')

    client = ExternalServiceNowClient.from_settings(settings)
    if check_health:
        try:
            client.health()
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    'ServiceNow external bridge is unreachable '
                    f'at {settings.servicenow_external_base_url}: {exc}'
                ),
            ) from exc
    return client


def _sync_servicenow_case_after_approval(
    db: Session,
    *,
    request: AutomationRequest,
    decision: str,
    approver: str,
    comment: str | None,
) -> None:
    ticket_id = str(request.ticket_id or '').strip()
    if ticket_id == '' or not ticket_id.upper().startswith('INC'):
        return

    if decision == 'approve':
        if request.status in {'executed', 'validated'}:
            next_state = 'resolved'
            resolution_notes = (
                f'Aprobado por {approver}. '
                f'Automatización ejecutada ({request.status}). '
                f'execution_id={request.execution_id or "-"}'
            )
            event_type = 'approval_approved_execution_finished'
        elif request.status in {'failed', 'rejected'}:
            next_state = 'needs_manual_attention'
            resolution_notes = (
                f'Aprobado por {approver}, pero la ejecución terminó en {request.status}. '
                f'Revisar rechazo/error: {request.rejection_reason or request.risk_reason or "sin detalle"}'
            )
            event_type = 'approval_approved_execution_failed'
        else:
            next_state = 'in_progress'
            resolution_notes = (
                f'Aprobado por {approver}. '
                f'Estado actual de la solicitud={request.status}.'
            )
            event_type = 'approval_approved_in_progress'
    else:
        next_state = 'needs_manual_attention'
        resolution_notes = (
            f'Rechazado por {approver}. '
            f'Motivo: {comment or "sin comentario"}'
        )
        event_type = 'approval_rejected_manual_attention'

    local_case = get_case_by_number(db, ticket_id)
    if local_case is not None:
        local_case.state = next_state
        local_case.resolution_notes = resolution_notes
        local_case.automation_request_id = request.id
        local_case.execution_id = request.execution_id
        local_case.last_agent_run_at = datetime.utcnow()
        db.add(local_case)
        add_case_event(
            db,
            case=local_case,
            actor='approval_engine',
            event_type=event_type,
            message='Estado del caso sincronizado después de decisión de aprobación.',
            payload={
                'decision': decision,
                'approver': approver,
                'request_status': request.status,
                'execution_id': request.execution_id,
            },
        )

    if settings.servicenow_mcp_enabled and settings.servicenow_external_enabled:
        try:
            external = _build_external_servicenow_client(check_health=False)
            external.update_case(
                ticket_id,
                {
                    'state': next_state,
                    'resolution_notes': resolution_notes,
                    'automation_request_id': request.id,
                    'execution_id': request.execution_id,
                    'append_event': {
                        'actor': 'approval_engine',
                        'event_type': event_type,
                        'message': 'Case synchronized from AFL approval decision.',
                        'payload': {
                            'decision': decision,
                            'approver': approver,
                            'request_status': request.status,
                            'execution_id': request.execution_id,
                        },
                    },
                },
            )
            db.add(
                AuditLog(
                    request_id=request.id,
                    ticket_id=ticket_id,
                    event_type='servicenow_case_synced_after_approval',
                    message='External ServiceNow case synchronized after approval decision.',
                    payload={'state': next_state, 'decision': decision},
                )
            )
        except Exception as exc:
            db.add(
                AuditLog(
                    request_id=request.id,
                    ticket_id=ticket_id,
                    event_type='servicenow_case_sync_failed_after_approval',
                    message='Failed to synchronize ServiceNow case after approval decision.',
                    payload={'decision': decision, 'error': str(exc)},
                )
            )

    db.commit()


@app.get('/health')
def health() -> dict:
    return {'status': 'ok', 'service': 'automation-factory-lite', 'awx_mode': settings.awx_mode}


@app.post('/api/requests', response_model=RequestResponse)
def create_request(payload: RequestCreate, db: Session = Depends(get_db)) -> RequestResponse:
    requested_ticket = (payload.ticket_id or '').strip()
    auto_generated = requested_ticket == ''
    ticket_id = requested_ticket if requested_ticket else _generate_ticket_id()
    initial_warnings = ['ticket_id autogenerado por plataforma'] if auto_generated else []
    record = AutomationRequest(
        raw_request=payload.text,
        requester=payload.requester,
        ticket_id=ticket_id,
        warnings=initial_warnings,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    updated = orchestrator.process_request(db, record)
    return RequestResponse.model_validate(updated)


@app.get('/api/requests', response_model=list[RequestResponse])
def list_requests(
    status: str | None = Query(default=None),
    ticket_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[RequestResponse]:
    query = select(AutomationRequest).order_by(AutomationRequest.created_at.desc())
    if status:
        query = query.where(AutomationRequest.status == status)
    if ticket_id:
        query = query.where(AutomationRequest.ticket_id == ticket_id)
    rows = db.execute(query).scalars().all()
    return [RequestResponse.model_validate(r) for r in rows]


@app.get('/api/requests/{request_id}', response_model=RequestResponse)
def get_request(request_id: str, db: Session = Depends(get_db)) -> RequestResponse:
    row = db.execute(select(AutomationRequest).where(AutomationRequest.id == request_id)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail='Request not found')
    return RequestResponse.model_validate(row)


@app.get('/api/requests/{request_id}/timeline', response_model=list[TimelineEventResponse])
def get_timeline(request_id: str, db: Session = Depends(get_db)) -> list[TimelineEventResponse]:
    rows = db.execute(
        select(TimelineEvent)
        .where(TimelineEvent.request_id == request_id)
        .order_by(TimelineEvent.created_at.asc())
    ).scalars().all()
    return [TimelineEventResponse.model_validate(r) for r in rows]


@app.get('/api/cmdb/hosts', response_model=list[HostResponse])
def cmdb_hosts(
    environment: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    criticality: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[HostResponse]:
    query = select(CMDBHost).order_by(CMDBHost.hostname.asc())
    if environment:
        query = query.where(CMDBHost.environment == environment)
    if owner:
        query = query.where(CMDBHost.owner == owner)
    if criticality:
        query = query.where(CMDBHost.criticality == criticality)

    rows = db.execute(query).scalars().all()
    return [HostResponse.model_validate(r) for r in rows]


@app.get('/api/catalog/automations', response_model=list[CatalogResponse])
def list_catalog(status: str | None = Query(default=None), db: Session = Depends(get_db)) -> list[CatalogResponse]:
    query = select(AutomationCatalogEntry).order_by(AutomationCatalogEntry.updated_at.desc())
    if status:
        query = query.where(AutomationCatalogEntry.status == status)
    rows = db.execute(query).scalars().all()
    return [CatalogResponse.model_validate(r) for r in rows]


@app.get('/api/approvals/pending')
def pending_approvals(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(ApprovalDecision, AutomationRequest)
        .join(AutomationRequest, AutomationRequest.id == ApprovalDecision.request_id)
        .where(ApprovalDecision.status == 'pending')
        .order_by(ApprovalDecision.created_at.asc())
    ).all()

    result = []
    for approval, request in rows:
        result.append(
            {
                'request_id': request.id,
                'ticket_id': request.ticket_id,
                'request_text': request.raw_request,
                'risk_level': request.risk_level,
                'risk_reason': request.risk_reason,
                'structured_spec': request.structured_spec,
                'created_at': approval.created_at,
            }
        )
    return result


@app.get('/api/servicenow/mcp/status')
def servicenow_mcp_status(db: Session = Depends(get_db)) -> dict:
    mcp_installed = importlib.util.find_spec('mcp') is not None
    open_cases = 0
    external_reachable = False
    external_error: str | None = None
    if settings.servicenow_external_enabled:
        try:
            client = _build_external_servicenow_client(check_health=True)
            external_cases = client.list_cases(limit=300)
            open_cases = len(
                [item for item in external_cases if item.get('state') in {'new', 'open', 'reopened', 'in_progress'}]
            )
            external_reachable = True
        except HTTPException as exc:
            external_error = str(exc.detail)
        except Exception as exc:
            external_error = str(exc)
    if not external_reachable:
        open_cases = db.scalar(
            select(func.count())
            .select_from(ServiceNowCase)
            .where(ServiceNowCase.state.in_(['new', 'open', 'reopened', 'in_progress']))
        ) or 0
    return {
        'enabled': settings.servicenow_mcp_enabled,
        'mode': settings.servicenow_mcp_mode,
        'integration_model': 'afl_backend_to_servicenow_via_mcp_bridge',
        'endpoint': settings.servicenow_mcp_endpoint,
        'server_cmd': settings.servicenow_mcp_server_cmd,
        'mcp_package_installed': mcp_installed,
        'bridge_status': 'connected' if (settings.servicenow_mcp_enabled and external_reachable) else 'degraded',
        'external_service_enabled': settings.servicenow_external_enabled,
        'external_service_url': settings.servicenow_external_base_url,
        'expected_external_service': {
            'host': settings.servicenow_sim_host,
            'port': settings.servicenow_sim_port,
        },
        'external_service_reachable': external_reachable,
        'external_service_error': external_error,
        'queue_open_cases': open_cases,
        'checked_at': datetime.utcnow().isoformat(),
    }


@app.get('/api/servicenow-mcp/cases')
def list_servicenow_mcp_cases(
    state: str | None = Query(default=None),
    assignment_group: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
) -> list[dict]:
    client = _build_external_servicenow_client(check_health=True)
    return client.list_cases(state=state, assignment_group=assignment_group, limit=limit)


@app.get('/api/servicenow-mcp/cases/{case_number}')
def get_servicenow_mcp_case(case_number: str) -> dict:
    client = _build_external_servicenow_client(check_health=True)
    return client.get_case(case_number)


@app.post('/api/servicenow-mcp/cases')
def create_servicenow_mcp_case(payload: ServiceNowCaseCreate) -> dict:
    client = _build_external_servicenow_client(check_health=True)
    return client.create_case(payload.model_dump())


@app.post('/api/servicenow-mcp/cases/seed')
def seed_servicenow_mcp_cases(force: bool = Query(default=False)) -> list[dict]:
    client = _build_external_servicenow_client(check_health=True)
    return client.seed_cases(force=force)


@app.post('/api/servicenow-mcp/agent/run', response_model=ServiceNowAgentRunResponse)
def run_servicenow_mcp_agent(limit: int = Query(default=5, ge=1, le=50), db: Session = Depends(get_db)) -> ServiceNowAgentRunResponse:
    client = _build_external_servicenow_client(check_health=True)
    result = run_pending_cases_via_external(
        db,
        orchestrator=orchestrator,
        client=client,
        limit=limit,
    )
    db.add(
        AuditLog(
            request_id=None,
            ticket_id=None,
            event_type='servicenow_mcp_agent_run',
            message='External ServiceNow MCP queue agent run executed.',
            payload={
                'scanned': result.scanned,
                'processed': result.processed,
                'resolved': result.resolved,
                'awaiting_approval': result.awaiting_approval,
                'manual_attention': result.manual_attention,
                'errors': result.errors,
                'case_numbers': result.case_numbers,
            },
        )
    )
    db.commit()
    return ServiceNowAgentRunResponse(
        scanned=result.scanned,
        processed=result.processed,
        resolved=result.resolved,
        awaiting_approval=result.awaiting_approval,
        manual_attention=result.manual_attention,
        errors=result.errors,
        case_numbers=result.case_numbers,
    )


@app.post('/api/servicenow-mcp/cases/{case_number}/process', response_model=ServiceNowAgentRunResponse)
def process_servicenow_mcp_case(case_number: str, db: Session = Depends(get_db)) -> ServiceNowAgentRunResponse:
    client = _build_external_servicenow_client(check_health=True)
    try:
        case = client.get_case(case_number)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f'Case {case_number} not found or unavailable: {exc}') from exc

    current_state = str(case.get('state') or '').strip()
    if current_state not in {'new', 'open', 'reopened', 'in_progress'}:
        raise HTTPException(
            status_code=409,
            detail=(
                f'Case {case_number} cannot be processed from state={current_state}. '
                'Only new/open/reopened/in_progress states are processable.'
            ),
        )

    result = run_pending_cases_via_external(
        db,
        orchestrator=orchestrator,
        client=client,
        limit=1,
        specific_case_number=case_number,
    )
    db.add(
        AuditLog(
            request_id=None,
            ticket_id=case_number,
            event_type='servicenow_mcp_case_run',
            message='External ServiceNow MCP single-case run executed.',
            payload={
                'scanned': result.scanned,
                'processed': result.processed,
                'resolved': result.resolved,
                'awaiting_approval': result.awaiting_approval,
                'manual_attention': result.manual_attention,
                'errors': result.errors,
                'case_numbers': result.case_numbers,
            },
        )
    )
    db.commit()
    return ServiceNowAgentRunResponse(
        scanned=result.scanned,
        processed=result.processed,
        resolved=result.resolved,
        awaiting_approval=result.awaiting_approval,
        manual_attention=result.manual_attention,
        errors=result.errors,
        case_numbers=result.case_numbers,
    )


@app.get('/api/servicenow/cases', response_model=list[ServiceNowCaseResponse])
def list_servicenow(
    state: str | None = Query(default=None),
    assignment_group: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
) -> list[ServiceNowCaseResponse]:
    rows = list_servicenow_cases(db, state=state, assignment_group=assignment_group, limit=limit)
    return [ServiceNowCaseResponse.model_validate(item) for item in rows]


@app.post('/api/servicenow/cases/seed', response_model=list[ServiceNowCaseResponse])
def seed_servicenow(force: bool = Query(default=False), db: Session = Depends(get_db)) -> list[ServiceNowCaseResponse]:
    if force:
        rows = seed_demo_cases_force(db, [settings.target_host_1_name, settings.target_host_2_name])
    else:
        rows = seed_demo_cases(db, [settings.target_host_1_name, settings.target_host_2_name])
    db.add(
        AuditLog(
            request_id=None,
            ticket_id=None,
            event_type='servicenow_seed',
            message='Seeded ServiceNow simulation demo cases.',
            payload={'created': len(rows), 'force': force},
        )
    )
    db.commit()
    return [ServiceNowCaseResponse.model_validate(item) for item in rows]


@app.post('/api/servicenow/cases', response_model=ServiceNowCaseResponse)
def create_servicenow(payload: ServiceNowCaseCreate, db: Session = Depends(get_db)) -> ServiceNowCaseResponse:
    row = create_servicenow_case(
        db,
        short_description=payload.short_description,
        description=payload.description,
        request_type=payload.request_type,
        params=payload.params,
        targets=payload.targets,
        priority=payload.priority,
        assignment_group=payload.assignment_group,
        requested_by=payload.requested_by,
    )
    db.add(
        AuditLog(
            request_id=None,
            ticket_id=row.number,
            event_type='servicenow_case_created',
            message='Case created in ServiceNow simulation.',
            payload={'case_number': row.number, 'request_type': row.request_type, 'priority': row.priority},
        )
    )
    db.commit()
    db.refresh(row)
    return ServiceNowCaseResponse.model_validate(row)


@app.get('/api/servicenow/cases/{case_number}', response_model=ServiceNowCaseDetailResponse)
def get_servicenow_case(case_number: str, db: Session = Depends(get_db)) -> ServiceNowCaseDetailResponse:
    row = get_case_by_number(db, case_number)
    if row is None:
        raise HTTPException(status_code=404, detail='Case not found')

    events = list_case_events(db, row.id)
    base = ServiceNowCaseResponse.model_validate(row)
    return ServiceNowCaseDetailResponse(
        **base.model_dump(),
        events=[ServiceNowCaseEventResponse.model_validate(event) for event in events],
    )


@app.post('/api/servicenow/agent/run', response_model=ServiceNowAgentRunResponse)
def run_servicenow_agent(limit: int = Query(default=5, ge=1, le=50), db: Session = Depends(get_db)) -> ServiceNowAgentRunResponse:
    result = run_pending_cases(db, orchestrator=orchestrator, limit=limit)
    db.add(
        AuditLog(
            request_id=None,
            ticket_id=None,
            event_type='servicenow_agent_run',
            message='ServiceNow queue agent run executed.',
            payload={
                'scanned': result.scanned,
                'processed': result.processed,
                'resolved': result.resolved,
                'awaiting_approval': result.awaiting_approval,
                'manual_attention': result.manual_attention,
                'errors': result.errors,
                'case_numbers': result.case_numbers,
            },
        )
    )
    db.commit()
    return ServiceNowAgentRunResponse(
        scanned=result.scanned,
        processed=result.processed,
        resolved=result.resolved,
        awaiting_approval=result.awaiting_approval,
        manual_attention=result.manual_attention,
        errors=result.errors,
        case_numbers=result.case_numbers,
    )


@app.post('/api/approvals/{request_id}/decision', response_model=ApprovalResponse)
def decide_approval(request_id: str, payload: ApprovalInput, db: Session = Depends(get_db)) -> ApprovalResponse:
    request = db.execute(select(AutomationRequest).where(AutomationRequest.id == request_id)).scalar_one_or_none()
    if request is None:
        raise HTTPException(status_code=404, detail='Request not found')

    approval = db.execute(select(ApprovalDecision).where(ApprovalDecision.request_id == request_id)).scalar_one_or_none()
    if approval is None:
        raise HTTPException(status_code=404, detail='Approval record not found')

    decision = payload.decision.lower().strip()
    if decision not in {'approve', 'reject'}:
        raise HTTPException(status_code=400, detail='Decision must be approve or reject')

    approval.status = 'approved' if decision == 'approve' else 'rejected'
    approval.approver = payload.approver
    approval.comment = payload.comment
    db.add(approval)

    if decision == 'approve':
        request.approved = True
        request.status = 'approved'
        db.add(request)
        db.commit()
        db.refresh(request)
        request = orchestrator.resume_after_approval(db, request)
        result = notify_ticket_event(
            settings,
            ticket_id=request.ticket_id,
            request_id=request.id,
            event_type='approval_decision',
            status='approved',
            payload={'approver': payload.approver, 'comment': payload.comment},
        )
        if result.attempted and not result.delivered:
            db.add(
                AuditLog(
                    request_id=request.id,
                    ticket_id=request.ticket_id,
                    event_type='ticket_notify_failed',
                    message='Webhook notification failed for approval decision.',
                    payload={'error': result.error, 'decision': 'approved'},
                )
            )
            db.commit()
        _sync_servicenow_case_after_approval(
            db,
            request=request,
            decision='approve',
            approver=payload.approver,
            comment=payload.comment,
        )
    else:
        request.approved = False
        request.status = 'rejected'
        request.rejection_reason = payload.comment or 'Rejected by approver.'
        db.add(request)
        db.add(
            AuditLog(
                request_id=request.id,
                ticket_id=request.ticket_id,
                event_type='approval_rejected',
                message='Request rejected during approval.',
                payload={'approver': payload.approver, 'comment': payload.comment},
            )
        )
        db.commit()
        result = notify_ticket_event(
            settings,
            ticket_id=request.ticket_id,
            request_id=request.id,
            event_type='approval_decision',
            status='rejected',
            payload={'approver': payload.approver, 'comment': payload.comment},
        )
        if result.attempted and not result.delivered:
            db.add(
                AuditLog(
                    request_id=request.id,
                    ticket_id=request.ticket_id,
                    event_type='ticket_notify_failed',
                    message='Webhook notification failed for approval decision.',
                    payload={'error': result.error, 'decision': 'rejected'},
                )
            )
            db.commit()
        _sync_servicenow_case_after_approval(
            db,
            request=request,
            decision='reject',
            approver=payload.approver,
            comment=payload.comment,
        )

    return ApprovalResponse(
        request_id=request_id,
        status=approval.status,
        approver=payload.approver,
        comment=payload.comment,
    )


@app.get('/api/executions', response_model=list[ExecutionResponse])
def list_executions(
    ticket_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ExecutionResponse]:
    query = select(ExecutionRecord).order_by(ExecutionRecord.created_at.desc())
    if ticket_id:
        query = query.where(ExecutionRecord.ticket_id == ticket_id)
    rows = db.execute(query).scalars().all()
    return [ExecutionResponse.model_validate(r) for r in rows]


@app.get('/api/audit')
def list_audit(
    db: Session = Depends(get_db),
    limit: int = Query(default=200, le=1000),
    ticket_id: str | None = Query(default=None),
    request_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
) -> list[dict]:
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    if ticket_id:
        query = query.where(AuditLog.ticket_id == ticket_id)
    if request_id:
        query = query.where(AuditLog.request_id == request_id)
    if event_type:
        query = query.where(AuditLog.event_type == event_type)
    rows = db.execute(query.limit(limit)).scalars().all()
    return [
        {
            'id': item.id,
            'request_id': item.request_id,
            'ticket_id': item.ticket_id,
            'event_type': item.event_type,
            'message': item.message,
            'payload': item.payload,
            'created_at': item.created_at,
        }
        for item in rows
    ]


@app.post('/api/bootstrap/awx')
def bootstrap_awx(db: Session = Depends(get_db)) -> dict:
    client = build_awx_client(settings)
    result = client.bootstrap()
    db.add(
        AuditLog(
            event_type='awx_bootstrap',
            request_id=None,
            ticket_id=None,
            message=f'AWX bootstrap in mode={result.mode}',
            payload={
                'organization': result.organization,
                'project': result.project,
                'inventory': result.inventory,
                'notes': result.notes,
                'resources': result.resources,
            },
        )
    )
    db.commit()
    return {
        'mode': result.mode,
        'organization': result.organization,
        'project': result.project,
        'inventory': result.inventory,
        'notes': result.notes,
        'resources': result.resources,
    }


@app.post('/api/seeds/cmdb')
def reseed_cmdb(db: Session = Depends(get_db)) -> dict:
    seed_cmdb_hosts(
        db,
        settings.target_host_1,
        settings.target_host_1_name,
        settings.target_host_2,
        settings.target_host_2_name,
    )
    return {'status': 'ok'}


@app.get('/api/dashboard')
def dashboard(db: Session = Depends(get_db)) -> dict:
    total_requests = db.scalar(select(func.count()).select_from(AutomationRequest)) or 0
    reused = db.scalar(
        select(func.count())
        .select_from(TimelineEvent)
        .where(and_(TimelineEvent.actor == 'Constructor', TimelineEvent.step == 'reuse_automation'))
    ) or 0
    generated = db.scalar(
        select(func.count())
        .select_from(TimelineEvent)
        .where(and_(TimelineEvent.actor == 'Constructor', TimelineEvent.step == 'generate_blueprint_automation', TimelineEvent.status == 'ok'))
    ) or 0
    success = db.scalar(
        select(func.count())
        .select_from(AutomationRequest)
        .where(AutomationRequest.status == 'executed')
    ) or 0
    failed = db.scalar(
        select(func.count())
        .select_from(AutomationRequest)
        .where(AutomationRequest.status.in_(['failed', 'rejected']))
    ) or 0
    approvals = db.scalar(
        select(func.count())
        .select_from(ApprovalDecision)
        .where(ApprovalDecision.status.in_(['pending', 'approved', 'rejected']))
    ) or 0
    snow_open = db.scalar(
        select(func.count())
        .select_from(ServiceNowCase)
        .where(ServiceNowCase.state.in_(['new', 'open', 'reopened', 'in_progress']))
    ) or 0
    snow_resolved = db.scalar(
        select(func.count())
        .select_from(ServiceNowCase)
        .where(ServiceNowCase.state == 'resolved')
    ) or 0
    snow_manual = db.scalar(
        select(func.count())
        .select_from(ServiceNowCase)
        .where(ServiceNowCase.state == 'needs_manual_attention')
    ) or 0

    rows = db.execute(select(AutomationRequest).order_by(AutomationRequest.created_at.asc())).scalars().all()
    publish_deltas: list[float] = []
    execute_deltas: list[float] = []

    for row in rows:
        if row.status in {'automation_generated', 'automation_reused', 'validated', 'executed'}:
            publish_deltas.append((row.updated_at - row.created_at).total_seconds())
        if row.status == 'executed':
            execute_deltas.append((row.updated_at - row.created_at).total_seconds())

    mean_publish = round(sum(publish_deltas) / len(publish_deltas), 2) if publish_deltas else 0.0
    mean_execute = round(sum(execute_deltas) / len(execute_deltas), 2) if execute_deltas else 0.0

    return {
        'timestamp': datetime.utcnow().isoformat(),
        'total_requests': total_requests,
        'automations_reused': reused,
        'automations_generated': generated,
        'mean_ticket_to_publish_seconds': mean_publish,
        'mean_ticket_to_execution_seconds': mean_execute,
        'success': success,
        'failed': failed,
        'actions_with_approval': approvals,
        'servicenow_open_cases': snow_open,
        'servicenow_resolved_cases': snow_resolved,
        'servicenow_manual_cases': snow_manual,
    }
