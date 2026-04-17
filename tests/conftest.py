from __future__ import annotations

import os

import pytest

os.environ['AWX_MODE'] = 'mock'
os.environ['MOCK_MODE'] = 'true'

from app.database import Base, SessionLocal, engine
from app.settings import get_settings
from services.cmdb_sim.service import seed_cmdb_hosts


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    settings = get_settings()
    with SessionLocal() as db:
        seed_cmdb_hosts(
            db,
            settings.target_host_1,
            settings.target_host_1_name,
            settings.target_host_2,
            settings.target_host_2_name,
        )
    yield
