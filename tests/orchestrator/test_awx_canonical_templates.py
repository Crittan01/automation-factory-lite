from types import SimpleNamespace

from sqlalchemy import select

from app.database import SessionLocal
from app.models import AutomationRequest, ExecutionRecord
from app.settings import get_settings
import services.orchestrator.engine as engine_module
from services.orchestrator.engine import AutomationOrchestrator, OrchestratorConfig


class _CaptureAWXClient:
    def __init__(self) -> None:
        self.published: list[tuple[str, str, str]] = []
        self.launched: list[tuple[str, list[str], dict]] = []

    def publish_job_template(self, name: str, playbook_path: str, inventory_name: str) -> dict:
        self.published.append((name, playbook_path, inventory_name))
        return {'id': 'jt-1', 'name': name}

    def launch_job(self, template_name: str, limit_hosts: list[str], extra_vars: dict) -> SimpleNamespace:
        self.launched.append((template_name, limit_hosts, extra_vars))
        return SimpleNamespace(
            mode='mock',
            template_name=template_name,
            job_id='mock-job-1',
            status='successful',
            summary='ok',
        )


def test_awx_uses_canonical_template_names_for_generated_artifacts(monkeypatch) -> None:
    captured_awx = _CaptureAWXClient()
    monkeypatch.setattr(engine_module, 'build_awx_client', lambda _settings: captured_awx)

    orchestrator = AutomationOrchestrator(
        OrchestratorConfig(root_dir='/Ansible/automation-factory-lite', settings=get_settings())
    )

    with SessionLocal() as db:
        request = AutomationRequest(raw_request='Crear usuario analista_demo en ol9server1', requester='tester')
        db.add(request)
        db.commit()
        db.refresh(request)

        result = orchestrator.process_request(db, request)
        assert result.status in {'executed', 'validated'}

        assert captured_awx.published
        assert captured_awx.launched
        published_name, published_playbook, _inventory = captured_awx.published[-1]
        launched_name, _hosts, _vars = captured_awx.launched[-1]

        assert published_name == 'AFL - Create User'
        assert published_playbook == 'ansible/playbooks/create_user.yml'
        assert launched_name == 'AFL - Create User'

        execution = db.execute(select(ExecutionRecord).where(ExecutionRecord.request_id == request.id)).scalar_one()
        assert execution.template_name == 'AFL - Create User'
