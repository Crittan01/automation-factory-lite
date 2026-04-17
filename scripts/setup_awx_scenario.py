#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / 'apps' / 'backend'))

from app.settings import get_settings
from services.awx_client.client import build_awx_client


def main() -> None:
    settings = get_settings()
    client = build_awx_client(settings)
    result = client.bootstrap()

    print(json.dumps(
        {
            'mode': result.mode,
            'organization': result.organization,
            'project': result.project,
            'inventory': result.inventory,
            'notes': result.notes,
            'resources': result.resources,
        },
        indent=2,
    ))


if __name__ == '__main__':
    main()
