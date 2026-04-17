#!/usr/bin/env python3
from __future__ import annotations

import requests

BASE_URL = 'http://localhost:8000'


def main() -> None:
    response = requests.post(f'{BASE_URL}/api/bootstrap/awx', timeout=30)
    response.raise_for_status()
    print(response.json())


if __name__ == '__main__':
    main()
