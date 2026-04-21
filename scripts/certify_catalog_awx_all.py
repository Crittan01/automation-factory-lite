#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from sqlalchemy import select

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'apps' / 'backend'))

from app.database import Base, SessionLocal, engine
from app.models import ApprovalDecision, AutomationRequest, ExecutionRecord
from app.settings import get_settings
from services.cmdb_sim.service import seed_cmdb_hosts
from services.orchestrator.engine import AWX_CANONICAL_AUTOMATIONS, AutomationOrchestrator, OrchestratorConfig


TERMINAL_JOB_STATUSES = {'successful', 'failed', 'error', 'canceled'}


@dataclass
class CatalogScenarioResult:
    name: str
    request_type_expected: str
    request_type_detected: str
    expected_approval: bool
    requires_approval: bool
    request_status: str
    awx_mode: str | None
    template_expected: str
    template_used: str | None
    job_id: str | None
    awx_job_status: str | None
    awx_job_finished: str | None
    passed: bool
    reason: str


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
    approval.comment = 'Auto-approved for full catalog AWX certification.'
    req.approved = True
    req.status = 'approved'
    db.add(approval)
    db.add(req)
    db.commit()
    db.refresh(req)
    return orchestrator.resume_after_approval(db, req)


def _awx_session(settings: Any) -> requests.Session:
    if not settings.awx_url or not settings.awx_token:
        raise RuntimeError('AWX_URL/AWX_TOKEN are required for real certification.')
    session = requests.Session()
    session.headers.update(
        {
            'Authorization': f'Bearer {settings.awx_token}',
            'Content-Type': 'application/json',
        }
    )
    return session


def _wait_awx_job(session: requests.Session, settings: Any, job_id: str, timeout_seconds: int = 180) -> dict:
    base = settings.awx_url.rstrip('/')
    deadline = time.time() + timeout_seconds
    last: dict = {}

    while time.time() < deadline:
        res = session.get(f'{base}/api/v2/jobs/{job_id}/', timeout=30, verify=settings.awx_verify_tls)
        res.raise_for_status()
        last = res.json()
        status = str(last.get('status') or '').lower()
        if status in TERMINAL_JOB_STATUSES:
            return last
        time.sleep(2)

    return last


def _list_awx_templates(session: requests.Session, settings: Any) -> list[str]:
    names: list[str] = []
    next_url = f"{settings.awx_url.rstrip('/')}/api/v2/job_templates/?page_size=200"
    while next_url:
        res = session.get(next_url, timeout=30, verify=settings.awx_verify_tls)
        res.raise_for_status()
        payload = res.json()
        names.extend([str(item.get('name') or '') for item in payload.get('results', [])])
        next_url = payload.get('next')
    return names


def run_catalog_awx_certification(output_path: Path) -> int:
    os.environ['AWX_MODE'] = 'real'
    get_settings.cache_clear()
    settings = get_settings()
    if settings.awx_mode != 'real':
        raise RuntimeError('AWX_MODE must resolve to real for this certification.')

    _prepare_db(settings)
    orchestrator = AutomationOrchestrator(OrchestratorConfig(root_dir=str(REPO_ROOT), settings=settings))
    awx = _awx_session(settings)

    scenarios = [
        ('Create User', 'Crear usuario cert_all_user en ol9server1 sin sudo', 'create_user', False),
        ('Delete User', 'Eliminar usuario cert_all_user en ol9server1', 'delete_user', True),
        ('Reset Password', 'Resetear contraseña de usuario cert_all_user en ol9server1', 'reset_password', True),
        (
            'Add SSH Key',
            'Agregar clave SSH "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIdemoKey cert@afl" al usuario cert_all_user en ol9server1',
            'add_ssh_key',
            True,
        ),
        (
            'Create Directory',
            'Crear carpeta /opt/automation_factory_lite/jobs/cert-all en rocky9server1',
            'create_directory',
            False,
        ),
        ('Install Service', 'Instalar nginx en rocky9server1', 'install_service', False),
        ('Install Package', 'Instalar paquete jq en rocky9server1', 'install_package', False),
        ('Restart Service', 'Reiniciar servicio nginx en rocky9server1', 'restart_service', True),
        ('Manage Service', 'Detener nginx en rocky9server1', 'manage_service', True),
        ('Install Agent', 'Instalar agente cockpit en ambos hosts', 'install_agent', True),
        ('Deploy Template', 'Desplegar plantilla en rocky9server1', 'deploy_template', False),
        ('Check Uptime', 'Obtener uptime en ol9server1', 'check_uptime', False),
        ('Check Patch Status', 'Verificar estado de parches en rocky9server1', 'check_patch_status', False),
        ('Check Connectivity', 'Chequeo de conectividad a 8.8.8.8 desde ol9server1', 'check_connectivity', False),
    ]

    results: list[CatalogScenarioResult] = []
    with SessionLocal() as db:
        for idx, (name, text, request_type, expected_approval) in enumerate(scenarios, start=1):
            ticket_id = f'CERT-ALL-{idx:03d}'
            req = AutomationRequest(raw_request=text, requester='cert.runner', ticket_id=ticket_id)
            db.add(req)
            db.commit()
            db.refresh(req)

            req = orchestrator.process_request(db, req)
            req = _maybe_auto_approve(db, orchestrator, req)
            db.refresh(req)

            execution = db.execute(select(ExecutionRecord).where(ExecutionRecord.request_id == req.id)).scalar_one_or_none()
            detected_type = str((req.structured_spec or {}).get('request_type') or '')
            expected_template = AWX_CANONICAL_AUTOMATIONS[request_type]['template_name']

            job_status = None
            job_finished = None
            if execution and execution.job_id:
                awx_job = _wait_awx_job(awx, settings, execution.job_id)
                job_status = str(awx_job.get('status') or '')
                job_finished = str(awx_job.get('finished') or '')

            checks = [
                detected_type == request_type,
                bool(req.requires_approval) == expected_approval,
                req.status in {'executed', 'validated'},
                execution is not None,
                (execution.awx_mode == 'real') if execution else False,
                (execution.template_name == expected_template) if execution else False,
                job_status in TERMINAL_JOB_STATUSES,
            ]

            fail_reasons: list[str] = []
            if detected_type != request_type:
                fail_reasons.append(f'detected={detected_type}')
            if bool(req.requires_approval) != expected_approval:
                fail_reasons.append(f'approval_expected={expected_approval} got={req.requires_approval}')
            if req.status not in {'executed', 'validated'}:
                fail_reasons.append(f'request_status={req.status}')
            if execution is None:
                fail_reasons.append('missing_execution_record')
            else:
                if execution.awx_mode != 'real':
                    fail_reasons.append(f'awx_mode={execution.awx_mode}')
                if execution.template_name != expected_template:
                    fail_reasons.append(f'template_used={execution.template_name}')
            if job_status not in TERMINAL_JOB_STATUSES:
                fail_reasons.append(f'awx_job_status={job_status}')

            results.append(
                CatalogScenarioResult(
                    name=name,
                    request_type_expected=request_type,
                    request_type_detected=detected_type,
                    expected_approval=expected_approval,
                    requires_approval=bool(req.requires_approval),
                    request_status=req.status,
                    awx_mode=(execution.awx_mode if execution else None),
                    template_expected=expected_template,
                    template_used=(execution.template_name if execution else None),
                    job_id=(execution.job_id if execution else None),
                    awx_job_status=job_status,
                    awx_job_finished=job_finished,
                    passed=all(checks),
                    reason='ok' if all(checks) else '; '.join(fail_reasons),
                )
            )

    awx_templates = set(_list_awx_templates(awx, settings))
    required_templates = {item['template_name'] for item in AWX_CANONICAL_AUTOMATIONS.values()}
    missing_templates = sorted(required_templates - awx_templates)

    passed = [item for item in results if item.passed]
    failed = [item for item in results if not item.passed]
    job_status_counts: dict[str, int] = {}
    for item in results:
        key = item.awx_job_status or 'unknown'
        job_status_counts[key] = job_status_counts.get(key, 0) + 1

    payload = {
        'timestamp_utc': datetime.utcnow().isoformat(),
        'mode': 'real',
        'awx_url': settings.awx_url,
        'summary': {
            'total_catalog_cases': len(results),
            'passed_cases': len(passed),
            'failed_cases': len(failed),
            'missing_awx_canonical_templates': len(missing_templates),
        },
        'awx_job_status_counts': job_status_counts,
        'missing_templates': missing_templates,
        'results': [asdict(item) for item in results],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')

    print(json.dumps(payload['summary'], indent=2))
    print(json.dumps({'awx_job_status_counts': job_status_counts}, indent=2))
    if failed:
        for item in failed:
            print(f'FAILED: {item.name} -> {item.reason}')
    if missing_templates:
        print(f'FAILED: Missing AWX templates: {missing_templates}')

    if failed or missing_templates:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='Certify all catalog cases against real AWX.')
    parser.add_argument(
        '--output',
        default='.run-logs/certification-catalog-awx-all.json',
        help='Output JSON report path',
    )
    args = parser.parse_args()
    return run_catalog_awx_certification(Path(args.output))


if __name__ == '__main__':
    raise SystemExit(main())
