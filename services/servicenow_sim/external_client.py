from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class ExternalServiceNowClient:
    base_url: str
    verify_tls: bool = False
    timeout_seconds: int = 5

    @classmethod
    def from_settings(cls, settings: Any) -> 'ExternalServiceNowClient':
        return cls(
            base_url=str(settings.servicenow_external_base_url).rstrip('/'),
            verify_tls=bool(settings.servicenow_external_verify_tls),
            timeout_seconds=max(1, int(settings.servicenow_external_timeout_seconds)),
        )

    def _get(self, path: str, params: dict | None = None) -> Any:
        res = requests.get(
            f'{self.base_url}{path}',
            params=params,
            timeout=self.timeout_seconds,
            verify=self.verify_tls,
        )
        res.raise_for_status()
        return res.json()

    def _post(self, path: str, payload: dict) -> Any:
        res = requests.post(
            f'{self.base_url}{path}',
            json=payload,
            timeout=self.timeout_seconds,
            verify=self.verify_tls,
        )
        res.raise_for_status()
        return res.json()

    def _patch(self, path: str, payload: dict) -> Any:
        res = requests.patch(
            f'{self.base_url}{path}',
            json=payload,
            timeout=self.timeout_seconds,
            verify=self.verify_tls,
        )
        res.raise_for_status()
        return res.json()

    def health(self) -> dict:
        return self._get('/health')

    def list_cases(self, *, state: str | None = None, assignment_group: str | None = None, limit: int = 100) -> list[dict]:
        params = {'limit': max(1, min(500, int(limit)))}
        if state:
            params['state'] = state
        if assignment_group:
            params['assignment_group'] = assignment_group
        return self._get('/api/cases', params=params)

    def get_case(self, case_number: str) -> dict:
        return self._get(f'/api/cases/{case_number}')

    def create_case(self, payload: dict) -> dict:
        return self._post('/api/cases', payload)

    def seed_cases(self, *, force: bool = False) -> list[dict]:
        path = '/api/cases/seed?force=true' if force else '/api/cases/seed'
        return self._post(path, {})

    def update_case(self, case_number: str, payload: dict) -> dict:
        return self._patch(f'/api/cases/{case_number}', payload)
