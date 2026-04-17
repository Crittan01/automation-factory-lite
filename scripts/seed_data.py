#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / 'apps' / 'backend'))

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import AuditLog, AutomationCatalogEntry, AutomationRequest, TimelineEvent
from app.settings import get_settings
from services.cmdb_sim.service import seed_cmdb_hosts
from services.servicenow_sim.service import seed_demo_cases


def main() -> None:
    settings = get_settings()
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        seed_cmdb_hosts(
            db,
            settings.target_host_1,
            settings.target_host_1_name,
            settings.target_host_2,
            settings.target_host_2_name,
        )
        seed_demo_cases(db, [settings.target_host_1_name, settings.target_host_2_name])

        existing_catalog = {
            item.name
            for item in db.execute(select(AutomationCatalogEntry).order_by(AutomationCatalogEntry.name.asc())).scalars().all()
        }

        baseline_catalog = [
            AutomationCatalogEntry(
                name='baseline-create-user',
                request_type='create_user',
                version='1.0.0',
                playbook_path='ansible/playbooks/create_user.yml',
                required_params=['username'],
                optional_params=['shell', 'comment'],
                risk_level='low',
                status='published',
                origin='reused',
                validation_results={'seeded': True},
                catalog_metadata={'source': 'seed_data.py'},
            ),
            AutomationCatalogEntry(
                name='baseline-install-nginx',
                request_type='install_service',
                version='1.0.0',
                playbook_path='ansible/playbooks/install_service.yml',
                required_params=['service_name'],
                optional_params=[],
                risk_level='low',
                status='published',
                origin='reused',
                validation_results={'seeded': True},
                catalog_metadata={'source': 'seed_data.py'},
            ),
        ]

        for record in baseline_catalog:
            if record.name not in existing_catalog:
                db.add(record)

        seed_request = db.execute(
            select(AutomationRequest).where(AutomationRequest.requester == 'seed.demo').limit(1)
        ).scalar_one_or_none()
        if seed_request is None:
            req = AutomationRequest(
                raw_request='Crear usuario auditor_seed en ol9server1 sin sudo',
                requester='seed.demo',
                structured_spec={
                    'request_type': 'create_user',
                    'params': {'username': 'auditor_seed'},
                    'targets': [settings.target_host_1_name],
                    'raw_text': 'seeded request',
                },
                status='executed',
                risk_level='low',
                risk_reason='seeded',
                requires_approval=False,
                approved=True,
                warnings=[],
            )
            db.add(req)
            db.flush()
            db.add(
                TimelineEvent(
                    request_id=req.id,
                    actor='Analista',
                    step='seeded_event',
                    status='ok',
                    payload={'note': 'Seeded request timeline'},
                )
            )
            db.add(
                AuditLog(
                    request_id=req.id,
                    ticket_id=req.ticket_id,
                    event_type='seed',
                    message='Seeded CMDB, catalog and demo request history',
                    payload={'script': 'seed_data.py'},
                )
            )

        db.commit()

    print('Seed completed.')


if __name__ == '__main__':
    main()
