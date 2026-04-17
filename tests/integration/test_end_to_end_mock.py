from sqlalchemy import select

from app.database import SessionLocal
from app.models import ApprovalDecision, AutomationRequest, TimelineEvent
from app.settings import get_settings
from services.orchestrator.engine import AutomationOrchestrator, OrchestratorConfig


def _orchestrator() -> AutomationOrchestrator:
    return AutomationOrchestrator(
        OrchestratorConfig(root_dir='/Ansible/automation-factory-lite', settings=get_settings())
    )


def test_end_to_end_create_user() -> None:
    orchestrator = _orchestrator()

    with SessionLocal() as db:
        req = AutomationRequest(raw_request='Crear usuario analista2 en ol9server1 sin sudo', requester='tester')
        db.add(req)
        db.commit()
        db.refresh(req)

        result = orchestrator.process_request(db, req)
        assert result.status in {'executed', 'validated'}
        assert result.structured_spec['request_type'] == 'create_user'

        timeline = db.execute(select(TimelineEvent).where(TimelineEvent.request_id == req.id)).scalars().all()
        actors = {item.actor for item in timeline}
        assert 'Analista' in actors
        assert 'Constructor' in actors
        assert 'Revisor/Publicador' in actors


def test_end_to_end_medium_requires_approval() -> None:
    orchestrator = _orchestrator()

    with SessionLocal() as db:
        req = AutomationRequest(
            raw_request='Instalar agente telegraf en ol9server1 y rocky9server1',
            requester='tester',
        )
        db.add(req)
        db.commit()
        db.refresh(req)

        result = orchestrator.process_request(db, req)

        assert result.requires_approval is True
        assert result.status == 'pending_approval'

        pending = db.execute(select(ApprovalDecision).where(ApprovalDecision.request_id == req.id)).scalar_one_or_none()
        assert pending is not None
        assert pending.status == 'pending'
