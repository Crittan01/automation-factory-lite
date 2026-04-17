from __future__ import annotations

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / 'apps' / 'backend'))

try:
    from mcp.server.fastmcp import FastMCP
except Exception as exc:  # pragma: no cover - optional runtime dependency
    raise SystemExit(
        "MCP dependency is missing. Install with: "
        "python -m pip install 'mcp>=1.2.0'. "
        f"Original error: {exc}"
    )

from app.settings import get_settings
from services.servicenow_sim.external_client import ExternalServiceNowClient

settings = get_settings()
external = ExternalServiceNowClient.from_settings(settings)
mcp = FastMCP('automation-factory-servicenow-sim')


@mcp.tool()
def list_open_cases(limit: int = 20) -> list[dict]:
    rows = external.list_cases(limit=max(1, min(200, int(limit))))
    return [row for row in rows if row.get('state') in {'new', 'open', 'reopened'}]


@mcp.tool()
def get_case(case_number: str) -> dict:
    try:
        row = external.get_case(case_number)
        return {'found': True, **row}
    except Exception:
        return {'found': False, 'case_number': case_number}


@mcp.tool()
def create_case_tool(
    short_description: str,
    request_type: str = 'create_user',
    target: str = 'ol9server1',
    requested_by: str = 'mcp.user',
) -> dict:
    case = external.create_case(
        {
            'short_description': short_description,
            'request_type': request_type,
            'params': {},
            'targets': [target],
            'requested_by': requested_by,
        }
    )
    return {'number': case.get('number'), 'state': case.get('state')}


@mcp.tool()
def seed_demo_queue() -> list[dict]:
    return external.seed_cases()


if __name__ == '__main__':  # pragma: no cover - manual runtime
    mcp.run()
