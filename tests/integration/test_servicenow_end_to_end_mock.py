from sqlalchemy import select

from app.database import SessionLocal
from app.models import AutomationRequest, ServiceNowCase
from app.settings import get_settings
from services.orchestrator.engine import AutomationOrchestrator, OrchestratorConfig
from services.servicenow_sim.agent import run_pending_cases
from services.servicenow_sim.service import create_case


def _orchestrator() -> AutomationOrchestrator:
    return AutomationOrchestrator(
        OrchestratorConfig(root_dir='/Ansible/automation-factory-lite', settings=get_settings())
    )


def test_servicenow_case_end_to_end_mock() -> None:
    orchestrator = _orchestrator()
    with SessionLocal() as db:
        case = create_case(
            db,
            short_description='Instalar nginx en rocky9server1',
            request_type='install_service',
            params={'service_name': 'nginx'},
            targets=['rocky9server1'],
            requested_by='snow.integration',
        )

        result = run_pending_cases(db, orchestrator=orchestrator, limit=200)
        assert result.processed >= 1

        updated_case = db.execute(select(ServiceNowCase).where(ServiceNowCase.id == case.id)).scalar_one()
        assert updated_case.state == 'resolved'
        assert updated_case.automation_request_id is not None

        request = db.execute(
            select(AutomationRequest).where(AutomationRequest.id == updated_case.automation_request_id)
        ).scalar_one()
        assert request.ticket_id == updated_case.number
        assert request.status in {'executed', 'validated'}
