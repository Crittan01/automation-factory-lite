#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'apps' / 'backend'))

from app.database import Base, SessionLocal, engine
from app.models import ApprovalDecision, AutomationRequest, ExecutionRecord, ServiceNowCase
from app.settings import get_settings
from services.cmdb_sim.service import seed_cmdb_hosts
from services.orchestrator.engine import AutomationOrchestrator, OrchestratorConfig
from services.servicenow_sim.agent import run_pending_cases
from services.servicenow_sim.service import create_case


@dataclass
class ScenarioResult:
    name: str
    ticket_id: str
    expected_request_type: str
    detected_request_type: str
    expected_approval: bool
    requires_approval: bool
    final_status: str
    risk_level: str | None
    passed: bool
    awx_mode: str | None
    job_id: str | None
    message: str


def _prepare_db(settings: Any) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_cmdb_hosts(
            db,
            settings.target_host_1,
            settings.target_host_1_name,
            settings.target_host_2,
            settings.target_host_2_name,
        )


def _maybe_auto_approve(db, orchestrator: AutomationOrchestrator, req: AutomationRequest) -> AutomationRequest:
    if req.status != 'pending_approval':
        return req

    approval = db.execute(select(ApprovalDecision).where(ApprovalDecision.request_id == req.id)).scalar_one_or_none()
    if approval is None:
        req.rejection_reason = 'Approval record missing during certification.'
        db.add(req)
        db.commit()
        db.refresh(req)
        return req

    approval.status = 'approved'
    approval.approver = 'cert.bot'
    approval.comment = 'Auto-approved for certification scenario.'
    req.approved = True
    req.status = 'approved'
    db.add(approval)
    db.add(req)
    db.commit()
    db.refresh(req)
    return orchestrator.resume_after_approval(db, req)


def _run_single_scenario(
    db,
    orchestrator: AutomationOrchestrator,
    *,
    index: int,
    mode: str,
    name: str,
    text: str,
    expected_request_type: str,
    expected_approval: bool,
) -> ScenarioResult:
    ticket_id = f'CERT-{mode.upper()}-{index:03d}'
    req = AutomationRequest(
        raw_request=text,
        requester='cert.runner',
        ticket_id=ticket_id,
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    req = orchestrator.process_request(db, req)
    req = _maybe_auto_approve(db, orchestrator, req)
    db.refresh(req)

    execution = db.execute(select(ExecutionRecord).where(ExecutionRecord.request_id == req.id)).scalar_one_or_none()
    detected = str((req.structured_spec or {}).get('request_type', 'unknown'))

    conditions = [
        detected == expected_request_type,
        req.requires_approval == expected_approval,
        req.status in {'executed', 'validated'},
    ]

    message = (
        f"status={req.status}, risk={req.risk_level}, "
        f"approval={req.requires_approval}, detected={detected}"
    )

    return ScenarioResult(
        name=name,
        ticket_id=ticket_id,
        expected_request_type=expected_request_type,
        detected_request_type=detected,
        expected_approval=expected_approval,
        requires_approval=bool(req.requires_approval),
        final_status=req.status,
        risk_level=req.risk_level,
        passed=all(conditions),
        awx_mode=execution.awx_mode if execution else None,
        job_id=execution.job_id if execution else None,
        message=message,
    )


def _run_servicenow_batch(db, orchestrator: AutomationOrchestrator) -> dict[str, Any]:
    host_1 = 'ol9server1'
    host_2 = 'rocky9server1'
    cases = [
        ('create_user', {'username': 'snow_cert_user'}, [host_1], 'Crear usuario snow_cert_user'),
        ('create_directory', {'directory_path': '/opt/automation_factory_lite/jobs/snow-cert'}, [host_2], 'Crear carpeta segura'),
        ('install_package', {'package_name': 'jq'}, [host_1], 'Instalar paquete jq'),
        ('restart_service', {'service_name': 'nginx'}, [host_2], 'Reiniciar nginx'),
        ('check_uptime', {}, [host_1], 'Uptime'),
        ('check_patch_status', {}, [host_2], 'Patch status'),
        ('check_connectivity', {'connectivity_target': '8.8.8.8'}, [host_1], 'Connectivity'),
        ('unsupported', {'rule': 'open-firewall'}, [host_1], 'Unsupported firewall'),
    ]
    created_numbers: list[str] = []
    for request_type, params, targets, label in cases:
        row = create_case(
            db,
            short_description=f'CERT-SNOW: {label}',
            request_type=request_type,
            params=params,
            targets=targets,
            requested_by='cert.snow',
        )
        created_numbers.append(row.number)

    run_result = run_pending_cases(db, orchestrator=orchestrator, limit=200)

    rows = db.execute(select(ServiceNowCase).where(ServiceNowCase.number.in_(created_numbers))).scalars().all()
    states: dict[str, int] = {}
    for row in rows:
        states[row.state] = states.get(row.state, 0) + 1

    # For certification criteria:
    # - at least one unsupported case should be in manual attention.
    # - supported cases should be processed to resolved or awaiting_approval.
    manual = states.get('needs_manual_attention', 0)
    resolved = states.get('resolved', 0)
    awaiting = states.get('awaiting_approval', 0)
    processed_supported = resolved + awaiting
    supported_count = len([item for item in cases if item[0] != 'unsupported'])

    return {
        'created_cases': created_numbers,
        'agent_run': asdict(run_result),
        'state_counts': states,
        'passed': manual >= 1 and processed_supported >= supported_count - 1,
    }


def run_certification(mode: str, output_path: Path) -> int:
    os.environ['AWX_MODE'] = mode
    get_settings.cache_clear()
    settings = get_settings()

    _prepare_db(settings)
    orchestrator = AutomationOrchestrator(
        OrchestratorConfig(root_dir=str(REPO_ROOT), settings=settings)
    )

    scenarios = [
        ('Create User', 'Crear usuario cert_user_01 en ol9server1 sin sudo', 'create_user', False),
        (
            'Add SSH Key',
            'Agregar clave SSH "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIdemoKey cert@afl" al usuario cert_user_01 en ol9server1',
            'add_ssh_key',
            True,
        ),
        ('Reset Password', 'Resetear contraseña de usuario cert_user_01 en ol9server1', 'reset_password', True),
        (
            'Create Directory',
            'Crear carpeta /opt/automation_factory_lite/jobs/cert-suite en rocky9server1',
            'create_directory',
            False,
        ),
        ('Install Package', 'Instalar paquete jq en rocky9server1', 'install_package', False),
        ('Install Service', 'Instalar nginx en rocky9server1', 'install_service', False),
        ('Restart Service', 'Reiniciar servicio nginx en rocky9server1', 'restart_service', True),
        ('Check Uptime', 'Obtener uptime en ol9server1', 'check_uptime', False),
        ('Check Patch Status', 'Verificar estado de parches en rocky9server1', 'check_patch_status', False),
        ('Check Connectivity', 'Chequeo de conectividad a 8.8.8.8 desde ol9server1', 'check_connectivity', False),
        ('Delete User', 'Eliminar usuario cert_user_01 en ol9server1', 'delete_user', True),
    ]

    results: list[ScenarioResult] = []
    with SessionLocal() as db:
        for idx, (name, text, request_type, approval) in enumerate(scenarios, start=1):
            result = _run_single_scenario(
                db,
                orchestrator,
                index=idx,
                mode=mode,
                name=name,
                text=text,
                expected_request_type=request_type,
                expected_approval=approval,
            )
            results.append(result)

        servicenow_result = _run_servicenow_batch(db, orchestrator)

    passed = [item for item in results if item.passed]
    failed = [item for item in results if not item.passed]

    payload = {
        'timestamp_utc': datetime.utcnow().isoformat(),
        'mode': mode,
        'awx_mode_effective': settings.awx_mode,
        'summary': {
            'total_scenarios': len(results),
            'passed_scenarios': len(passed),
            'failed_scenarios': len(failed),
            'servicenow_passed': bool(servicenow_result.get('passed')),
        },
        'scenario_results': [asdict(item) for item in results],
        'servicenow_result': servicenow_result,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')

    print(json.dumps(payload['summary'], indent=2))
    if failed:
        for item in failed:
            print(f"FAILED: {item.name} -> {item.message}")
        return 1
    if not servicenow_result.get('passed'):
        print('FAILED: ServiceNow certification batch did not meet expected state transitions.')
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='Run full-cycle certification for Automation Factory Lite.')
    parser.add_argument('--mode', choices=['mock', 'real'], required=True, help='AWX mode for certification run')
    parser.add_argument(
        '--output',
        default='.run-logs/certification-report.json',
        help='Output JSON report path',
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    return run_certification(args.mode, output_path)


if __name__ == '__main__':
    raise SystemExit(main())
