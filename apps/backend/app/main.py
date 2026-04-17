from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine, get_db
from app.models import (
    ApprovalDecision,
    AuditLog,
    AutomationCatalogEntry,
    AutomationRequest,
    CMDBHost,
    ExecutionRecord,
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
    TimelineEventResponse,
)
from app.settings import get_settings
from services.awx_client.client import build_awx_client
from services.cmdb_sim.service import seed_cmdb_hosts
from services.orchestrator.engine import AutomationOrchestrator, OrchestratorConfig

settings = get_settings()
ROOT_DIR = Path(__file__).resolve().parents[3]
orchestrator = AutomationOrchestrator(OrchestratorConfig(root_dir=str(ROOT_DIR), settings=settings))


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_cmdb_hosts(
            db,
            settings.target_host_1,
            settings.target_host_1_name,
            settings.target_host_2,
            settings.target_host_2_name,
        )
    yield


app = FastAPI(title='Automation Factory Lite API', version='1.0.0', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health')
def health() -> dict:
    return {'status': 'ok', 'service': 'automation-factory-lite', 'awx_mode': settings.awx_mode}


@app.post('/api/requests', response_model=RequestResponse)
def create_request(payload: RequestCreate, db: Session = Depends(get_db)) -> RequestResponse:
    record = AutomationRequest(raw_request=payload.text, requester=payload.requester)
    db.add(record)
    db.commit()
    db.refresh(record)

    updated = orchestrator.process_request(db, record)
    return RequestResponse.model_validate(updated)


@app.get('/api/requests', response_model=list[RequestResponse])
def list_requests(status: str | None = Query(default=None), db: Session = Depends(get_db)) -> list[RequestResponse]:
    query = select(AutomationRequest).order_by(AutomationRequest.created_at.desc())
    if status:
        query = query.where(AutomationRequest.status == status)
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
                'request_text': request.raw_request,
                'risk_level': request.risk_level,
                'risk_reason': request.risk_reason,
                'structured_spec': request.structured_spec,
                'created_at': approval.created_at,
            }
        )
    return result


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
    else:
        request.approved = False
        request.status = 'rejected'
        request.rejection_reason = payload.comment or 'Rejected by approver.'
        db.add(request)
        db.add(
            AuditLog(
                request_id=request.id,
                event_type='approval_rejected',
                message='Request rejected during approval.',
                payload={'approver': payload.approver, 'comment': payload.comment},
            )
        )
        db.commit()

    return ApprovalResponse(
        request_id=request_id,
        status=approval.status,
        approver=payload.approver,
        comment=payload.comment,
    )


@app.get('/api/executions', response_model=list[ExecutionResponse])
def list_executions(db: Session = Depends(get_db)) -> list[ExecutionResponse]:
    rows = db.execute(select(ExecutionRecord).order_by(ExecutionRecord.created_at.desc())).scalars().all()
    return [ExecutionResponse.model_validate(r) for r in rows]


@app.get('/api/audit')
def list_audit(db: Session = Depends(get_db), limit: int = Query(default=200, le=1000)) -> list[dict]:
    rows = db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)).scalars().all()
    return [
        {
            'id': item.id,
            'request_id': item.request_id,
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
    }
