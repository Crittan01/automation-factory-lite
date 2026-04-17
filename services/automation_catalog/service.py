from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AutomationCatalogEntry


def _signature(spec: dict) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    request_type = spec.get('request_type', '')
    param_keys = tuple(sorted((spec.get('params') or {}).keys()))
    targets = tuple(sorted(spec.get('targets') or []))
    return request_type, param_keys, targets


def find_reusable_automation(db: Session, spec: dict) -> AutomationCatalogEntry | None:
    request_type, param_keys, _ = _signature(spec)
    entries = db.execute(
        select(AutomationCatalogEntry)
        .where(AutomationCatalogEntry.request_type == request_type)
        .where(AutomationCatalogEntry.status == 'published')
        .order_by(AutomationCatalogEntry.updated_at.desc())
    ).scalars().all()

    for entry in entries:
        if tuple(sorted(entry.required_params)) == param_keys:
            entry.last_used = datetime.utcnow()
            db.add(entry)
            db.commit()
            db.refresh(entry)
            return entry

    return None


def upsert_generated_automation(
    db: Session,
    *,
    name: str,
    request_type: str,
    playbook_path: str,
    required_params: list[str],
    optional_params: list[str],
    risk_level: str,
    validation_results: dict,
    metadata: dict,
    origin: str,
) -> AutomationCatalogEntry:
    existing = db.execute(
        select(AutomationCatalogEntry)
        .where(AutomationCatalogEntry.name == name)
        .where(AutomationCatalogEntry.request_type == request_type)
    ).scalar_one_or_none()

    if existing:
        existing.playbook_path = playbook_path
        existing.required_params = required_params
        existing.optional_params = optional_params
        existing.risk_level = risk_level
        existing.validation_results = validation_results
        existing.catalog_metadata = metadata
        existing.origin = origin
        existing.status = 'published'
        existing.last_used = datetime.utcnow()
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    record = AutomationCatalogEntry(
        name=name,
        request_type=request_type,
        version='1.0.0',
        playbook_path=playbook_path,
        required_params=required_params,
        optional_params=optional_params,
        risk_level=risk_level,
        status='published',
        last_used=datetime.utcnow(),
        origin=origin,
        validation_results=validation_results,
        catalog_metadata=metadata,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
