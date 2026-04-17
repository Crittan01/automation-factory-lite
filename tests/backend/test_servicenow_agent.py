from sqlalchemy import select

from app.database import SessionLocal
from app.models import AuditLog, ServiceNowCase
from app.settings import get_settings
from services.orchestrator.engine import AutomationOrchestrator, OrchestratorConfig
from services.servicenow_sim.agent import run_pending_cases
from services.servicenow_sim.service import create_case, get_case_by_number, seed_demo_cases, seed_demo_cases_force


def _orchestrator() -> AutomationOrchestrator:
    return AutomationOrchestrator(
        OrchestratorConfig(root_dir='/Ansible/automation-factory-lite', settings=get_settings())
    )


def test_seed_demo_cases() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        rows = seed_demo_cases_force(db, [settings.target_host_1_name, settings.target_host_2_name])
        assert len(rows) >= 10
        numbers = {item.number for item in rows}
        assert len(numbers) == len(rows)


def test_seed_demo_cases_is_idempotent_without_force() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        first = seed_demo_cases(db, [settings.target_host_1_name, settings.target_host_2_name])
        second = seed_demo_cases(db, [settings.target_host_1_name, settings.target_host_2_name])
        assert len(second) == 0
        assert isinstance(first, list)


def test_servicenow_agent_processes_cases_with_traceability() -> None:
    orchestrator = _orchestrator()
    with SessionLocal() as db:
        supported = create_case(
            db,
            short_description='Crear usuario snow_case_1 en ol9server1 sin sudo',
            request_type='create_user',
            params={'username': 'snow_case_1'},
            targets=['ol9server1'],
            priority='3',
            requested_by='snow.user',
        )
        unsupported = create_case(
            db,
            short_description='Cambiar firewall para all hosts',
            request_type='unsupported',
            params={'rule': 'allow_all'},
            targets=['ol9server1'],
            priority='1',
            requested_by='snow.user',
        )

        result = run_pending_cases(db, orchestrator=orchestrator, limit=200)
        assert result.scanned >= 2
        assert result.processed >= 2

        supported_after = get_case_by_number(db, supported.number)
        assert supported_after is not None
        assert supported_after.state in {'resolved', 'awaiting_approval'}
        assert supported_after.automation_request_id is not None

        unsupported_after = get_case_by_number(db, unsupported.number)
        assert unsupported_after is not None
        assert unsupported_after.state == 'needs_manual_attention'

        audit_rows = db.execute(
            select(AuditLog).where(AuditLog.ticket_id.in_([supported.number, unsupported.number]))
        ).scalars().all()
        assert len(audit_rows) >= 2


def test_servicenow_cases_are_queryable() -> None:
    with SessionLocal() as db:
        rows = db.execute(select(ServiceNowCase).order_by(ServiceNowCase.created_at.asc())).scalars().all()
        assert isinstance(rows, list)
