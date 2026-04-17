from app.database import SessionLocal
from app.main import servicenow_mcp_status


def test_servicenow_mcp_status_contract() -> None:
    with SessionLocal() as db:
        result = servicenow_mcp_status(db=db)

    assert isinstance(result, dict)
    assert 'enabled' in result
    assert 'mode' in result
    assert 'server_cmd' in result
    assert 'bridge_status' in result
    assert 'queue_open_cases' in result
    assert 'checked_at' in result
