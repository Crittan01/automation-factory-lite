from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests


@dataclass
class ITSMNotificationResult:
    attempted: bool
    delivered: bool
    error: str | None = None


def notify_ticket_event(
    settings: Any,
    *,
    ticket_id: str,
    request_id: str | None,
    event_type: str,
    status: str,
    payload: dict,
) -> ITSMNotificationResult:
    if not getattr(settings, 'itsm_webhook_enabled', False):
        return ITSMNotificationResult(attempted=False, delivered=False)

    webhook_url = getattr(settings, 'itsm_webhook_url', None)
    if not webhook_url:
        return ITSMNotificationResult(attempted=False, delivered=False)

    headers = {'Content-Type': 'application/json'}
    token = getattr(settings, 'itsm_webhook_token', None)
    if token:
        headers['Authorization'] = f'Bearer {token}'

    body = {
        'ticket_id': ticket_id,
        'request_id': request_id,
        'event_type': event_type,
        'status': status,
        'timestamp': datetime.utcnow().isoformat(),
        'payload': payload,
    }

    try:
        response = requests.post(
            webhook_url,
            json=body,
            headers=headers,
            timeout=max(1, int(getattr(settings, 'itsm_webhook_timeout_seconds', 5))),
        )
        response.raise_for_status()
        return ITSMNotificationResult(attempted=True, delivered=True)
    except Exception as exc:
        return ITSMNotificationResult(attempted=True, delivered=False, error=str(exc))
