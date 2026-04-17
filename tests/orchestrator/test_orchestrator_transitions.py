from app.database import SessionLocal
from app.models import AutomationRequest
from app.settings import get_settings
from services.orchestrator.engine import AutomationOrchestrator, OrchestratorConfig


def test_orchestrator_fallback_without_graph() -> None:
    orchestrator = AutomationOrchestrator(
        OrchestratorConfig(root_dir='/Ansible/automation-factory-lite', settings=get_settings())
    )
    orchestrator.graph = None

    with SessionLocal() as db:
        req = AutomationRequest(raw_request='Crear usuario pablo en ol9server1', requester='tester')
        db.add(req)
        db.commit()
        db.refresh(req)

        result = orchestrator.process_request(db, req)

        assert result.status in {'executed', 'validated'}
        assert result.structured_spec['request_type'] == 'create_user'


def test_orchestrator_reject_out_of_catalog() -> None:
    orchestrator = AutomationOrchestrator(
        OrchestratorConfig(root_dir='/Ansible/automation-factory-lite', settings=get_settings())
    )

    with SessionLocal() as db:
        req = AutomationRequest(raw_request='Modificar firewall en ol9server1', requester='tester')
        db.add(req)
        db.commit()
        db.refresh(req)

        result = orchestrator.process_request(db, req)

        assert result.status == 'rejected'
        assert result.risk_level == 'high'
