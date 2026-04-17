#!/usr/bin/env python3
from __future__ import annotations

import os

import requests

BASE_URL = os.getenv('API_BASE', f"http://localhost:{os.getenv('BACKEND_PORT', '18010')}")


def main() -> None:
    response = requests.post(f'{BASE_URL}/api/bootstrap/awx', timeout=30)
    response.raise_for_status()
    print(response.json())


if __name__ == '__main__':
    main()
