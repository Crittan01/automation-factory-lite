from sqlalchemy import select

from app.database import SessionLocal
from app.models import CMDBHost
from services.automation_catalog.service import find_reusable_automation, upsert_generated_automation
from services.cmdb_sim.service import seed_cmdb_hosts
from services.cmdb_sim.service import validate_targets


def test_cmdb_target_validation() -> None:
    with SessionLocal() as db:
        result = validate_targets(db, ['ol9server1'], 'create_directory')
        assert len(result.valid_hosts) == 1
        assert result.missing_targets == []
        assert result.denied_targets == []


def test_catalog_reuse() -> None:
    spec = {
        'request_type': 'create_user',
        'params': {'username': 'alice'},
        'targets': ['ol9server1'],
    }
    with SessionLocal() as db:
        entry = upsert_generated_automation(
            db,
            name='create-user-1',
            request_type='create_user',
            playbook_path='generated/test/playbook.yml',
            required_params=['username'],
            optional_params=[],
            risk_level='low',
            validation_results={'ok': True},
            metadata={'source': 'test'},
            origin='generated',
        )
        reused = find_reusable_automation(db, spec)
        assert reused is not None
        assert reused.id == entry.id


def test_cmdb_seed_has_hosts() -> None:
    with SessionLocal() as db:
        hosts = db.execute(select(CMDBHost)).scalars().all()
        assert len(hosts) >= 2
        assert any('create_directory' in (host.allowed_actions or []) for host in hosts)


def test_cmdb_seed_updates_existing_hosts_with_supported_actions() -> None:
    with SessionLocal() as db:
        host = db.execute(select(CMDBHost).where(CMDBHost.hostname == 'ol9server1')).scalar_one()
        host.allowed_actions = ['create_user']
        db.add(host)
        db.commit()

        seed_cmdb_hosts(
            db,
            target_host_1='192.168.250.30',
            target_host_1_name='ol9server1',
            target_host_2='192.168.250.40',
            target_host_2_name='rocky9server1',
        )

        refreshed = db.execute(select(CMDBHost).where(CMDBHost.hostname == 'ol9server1')).scalar_one()
        assert 'create_user' in (refreshed.allowed_actions or [])
        assert 'check_connectivity' in (refreshed.allowed_actions or [])
