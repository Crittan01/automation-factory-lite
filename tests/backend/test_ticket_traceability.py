from sqlalchemy import select

from app.database import SessionLocal
from app.models import AuditLog, AutomationRequest, ExecutionRecord
from app.settings import get_settings
from services.orchestrator.engine import AutomationOrchestrator, OrchestratorConfig


def _orchestrator() -> AutomationOrchestrator:
    return AutomationOrchestrator(
        OrchestratorConfig(root_dir='/Ansible/automation-factory-lite', settings=get_settings())
    )


def test_ticket_traceability_persists_in_execution_and_audit() -> None:
    orchestrator = _orchestrator()
    ticket_id = 'AFL-TEST-TRACE-001'

    with SessionLocal() as db:
        req = AutomationRequest(
            raw_request='Crear usuario auditor1 en ol9server1 sin sudo',
            requester='tester',
            ticket_id=ticket_id,
        )
        db.add(req)
        db.commit()
        db.refresh(req)

        result = orchestrator.process_request(db, req)
        assert result.status in {'executed', 'validated'}
        assert result.ticket_id == ticket_id

        execution = db.execute(select(ExecutionRecord).where(ExecutionRecord.request_id == req.id)).scalar_one_or_none()
        assert execution is not None
        assert execution.ticket_id == ticket_id
        assert execution.extra_vars.get('afl_ticket_id') == ticket_id

        audit_rows = db.execute(select(AuditLog).where(AuditLog.request_id == req.id)).scalars().all()
        assert audit_rows
        assert any(item.ticket_id == ticket_id for item in audit_rows)


def test_ticket_filters_for_requests_audit_and_execution() -> None:
    orchestrator = _orchestrator()
    ticket_1 = 'AFL-TEST-FILTER-001'
    ticket_2 = 'AFL-TEST-FILTER-002'

    with SessionLocal() as db:
        req_1 = AutomationRequest(
            raw_request='Crear usuario filtro1 en ol9server1 sin sudo',
            requester='api.tester',
            ticket_id=ticket_1,
        )
        req_2 = AutomationRequest(
            raw_request='Crear usuario filtro2 en ol9server1 sin sudo',
            requester='api.tester',
            ticket_id=ticket_2,
        )
        db.add(req_1)
        db.add(req_2)
        db.commit()
        db.refresh(req_1)
        db.refresh(req_2)

        orchestrator.process_request(db, req_1)
        orchestrator.process_request(db, req_2)

        requests_filtered = db.execute(
            select(AutomationRequest).where(AutomationRequest.ticket_id == ticket_1)
        ).scalars().all()
        assert len(requests_filtered) == 1
        assert requests_filtered[0].ticket_id == ticket_1

        execution_filtered = db.execute(
            select(ExecutionRecord).where(ExecutionRecord.ticket_id == ticket_1)
        ).scalars().all()
        assert len(execution_filtered) == 1
        assert execution_filtered[0].ticket_id == ticket_1

        audit_filtered = db.execute(select(AuditLog).where(AuditLog.ticket_id == ticket_1)).scalars().all()
        assert len(audit_filtered) >= 1
        assert all(item.ticket_id == ticket_1 for item in audit_filtered)
