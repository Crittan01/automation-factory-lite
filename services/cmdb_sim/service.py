from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CMDBHost

ALLOWED_ACTIONS = [
    'create_user',
    'install_service',
    'manage_service',
    'install_agent',
    'deploy_template',
]


@dataclass
class HostValidationResult:
    valid_hosts: list[CMDBHost]
    missing_targets: list[str]
    denied_targets: list[str]


def seed_cmdb_hosts(db: Session, target_host_1: str, target_host_1_name: str, target_host_2: str, target_host_2_name: str) -> None:
    existing = {h.hostname: h for h in db.execute(select(CMDBHost)).scalars().all()}

    defaults = [
        {
            'hostname': target_host_1_name,
            'ip': target_host_1,
            'environment': 'dev',
            'owner': 'platform.ops',
            'criticality': 'medium',
            'operating_system': 'Oracle Linux 9',
            'tags': ['lab', 'linux', 'ol9'],
            'allowed_actions': ALLOWED_ACTIONS,
            'state': 'active',
            'recent_history': [],
        },
        {
            'hostname': target_host_2_name,
            'ip': target_host_2,
            'environment': 'dev',
            'owner': 'platform.ops',
            'criticality': 'medium',
            'operating_system': 'Rocky Linux 9',
            'tags': ['lab', 'linux', 'rocky9'],
            'allowed_actions': ALLOWED_ACTIONS,
            'state': 'active',
            'recent_history': [],
        },
    ]

    for item in defaults:
        if item['hostname'] in existing:
            continue
        db.add(CMDBHost(**item))

    db.commit()


def list_hosts(db: Session) -> list[CMDBHost]:
    return db.execute(select(CMDBHost).order_by(CMDBHost.hostname.asc())).scalars().all()


def get_host(db: Session, identifier: str) -> CMDBHost | None:
    query = select(CMDBHost).where((CMDBHost.hostname == identifier) | (CMDBHost.ip == identifier))
    return db.execute(query).scalar_one_or_none()


def validate_targets(db: Session, targets: list[str], request_type: str) -> HostValidationResult:
    missing: list[str] = []
    denied: list[str] = []
    valid: list[CMDBHost] = []

    for target in targets:
        host = get_host(db, target)
        if host is None:
            missing.append(target)
            continue
        if request_type not in (host.allowed_actions or []):
            denied.append(target)
            continue
        valid.append(host)

    return HostValidationResult(valid_hosts=valid, missing_targets=missing, denied_targets=denied)
