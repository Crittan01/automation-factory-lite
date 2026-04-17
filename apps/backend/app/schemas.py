from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RequestCreate(BaseModel):
    text: str = Field(min_length=3)
    requester: str = Field(default='demo.user')


class RequestResponse(BaseModel):
    id: str
    status: str
    risk_level: str | None = None
    risk_reason: str | None = None
    requires_approval: bool = False
    approved: bool | None = None
    rejection_reason: str | None = None
    structured_spec: dict
    warnings: list[str]
    automation_id: str | None = None
    execution_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApprovalInput(BaseModel):
    approver: str
    decision: str
    comment: str | None = None


class ApprovalResponse(BaseModel):
    request_id: str
    status: str
    approver: str
    comment: str | None


class HostResponse(BaseModel):
    id: str
    hostname: str
    ip: str
    environment: str
    owner: str
    criticality: str
    operating_system: str
    tags: list[str]
    allowed_actions: list[str]
    state: str
    recent_history: list[dict]

    model_config = ConfigDict(from_attributes=True)


class CatalogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    name: str
    request_type: str
    version: str
    playbook_path: str
    required_params: list[str]
    optional_params: list[str]
    risk_level: str
    status: str
    last_used: datetime | None = None
    origin: str
    validation_results: dict
    metadata: dict = Field(validation_alias='catalog_metadata', serialization_alias='metadata')


class TimelineEventResponse(BaseModel):
    actor: str
    step: str
    status: str
    payload: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExecutionResponse(BaseModel):
    id: str
    request_id: str
    awx_mode: str
    template_name: str
    hosts: list[str]
    extra_vars: dict
    job_id: str
    status: str
    output_summary: str
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
