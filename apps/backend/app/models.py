from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CMDBHost(Base, TimestampMixin):
    __tablename__ = 'cmdb_hosts'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hostname: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    ip: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    environment: Mapped[str] = mapped_column(String(32), default='dev')
    owner: Mapped[str] = mapped_column(String(255), default='ops')
    criticality: Mapped[str] = mapped_column(String(32), default='medium')
    operating_system: Mapped[str] = mapped_column(String(255), default='linux')
    tags: Mapped[list] = mapped_column(JSON, default=list)
    allowed_actions: Mapped[list] = mapped_column(JSON, default=list)
    state: Mapped[str] = mapped_column(String(32), default='active')
    recent_history: Mapped[list] = mapped_column(JSON, default=list)


class AutomationCatalogEntry(Base, TimestampMixin):
    __tablename__ = 'automation_catalog'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), index=True)
    request_type: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[str] = mapped_column(String(32), default='1.0.0')
    playbook_path: Mapped[str] = mapped_column(String(512))
    required_params: Mapped[list] = mapped_column(JSON, default=list)
    optional_params: Mapped[list] = mapped_column(JSON, default=list)
    risk_level: Mapped[str] = mapped_column(String(16), default='low')
    status: Mapped[str] = mapped_column(String(16), default='draft')
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    origin: Mapped[str] = mapped_column(String(32), default='generated')
    validation_results: Mapped[dict] = mapped_column(JSON, default=dict)
    catalog_metadata: Mapped[dict] = mapped_column('metadata', JSON, default=dict)


class AutomationRequest(Base, TimestampMixin):
    __tablename__ = 'automation_requests'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    raw_request: Mapped[str] = mapped_column(Text)
    requester: Mapped[str] = mapped_column(String(255), default='demo.user')
    structured_spec: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default='received')
    risk_level: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    risk_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    approved: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    automation_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey('automation_catalog.id'), nullable=True)
    execution_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey('execution_records.id'), nullable=True)

    automation: Mapped[Optional['AutomationCatalogEntry']] = relationship('AutomationCatalogEntry')
    execution: Mapped[Optional['ExecutionRecord']] = relationship('ExecutionRecord')
    timeline_events: Mapped[list['TimelineEvent']] = relationship('TimelineEvent', back_populates='request')


class ApprovalDecision(Base, TimestampMixin):
    __tablename__ = 'approval_decisions'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[str] = mapped_column(String(36), ForeignKey('automation_requests.id'), index=True)
    status: Mapped[str] = mapped_column(String(16), default='pending')
    approver: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ExecutionRecord(Base, TimestampMixin):
    __tablename__ = 'execution_records'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[str] = mapped_column(String(36), index=True)
    awx_mode: Mapped[str] = mapped_column(String(16), default='mock')
    template_name: Mapped[str] = mapped_column(String(255))
    hosts: Mapped[list] = mapped_column(JSON, default=list)
    extra_vars: Mapped[dict] = mapped_column(JSON, default=dict)
    job_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default='queued')
    output_summary: Mapped[str] = mapped_column(Text, default='')
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class TimelineEvent(Base):
    __tablename__ = 'timeline_events'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[str] = mapped_column(String(36), ForeignKey('automation_requests.id'), index=True)
    actor: Mapped[str] = mapped_column(String(64))
    step: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default='ok')
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    request: Mapped['AutomationRequest'] = relationship('AutomationRequest', back_populates='timeline_events')


class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    message: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
