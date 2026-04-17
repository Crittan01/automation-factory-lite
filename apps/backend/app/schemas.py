from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RequestCreate(BaseModel):
    text: str = Field(min_length=3)
    requester: str = Field(default='demo.user')
    ticket_id: str | None = Field(default=None, min_length=3, max_length=128)


class RequestResponse(BaseModel):
    id: str
    ticket_id: str
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
    ticket_id: str | None = None
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


class ServiceNowCaseCreate(BaseModel):
    short_description: str = Field(min_length=5)
    description: str | None = None
    request_type: str | None = None
    params: dict = Field(default_factory=dict)
    targets: list[str] = Field(default_factory=list)
    priority: str = '3'
    assignment_group: str = 'automation.factory'
    requested_by: str = 'servicenow.user'


class ServiceNowCaseEventResponse(BaseModel):
    actor: str
    event_type: str
    message: str
    payload: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ServiceNowCaseResponse(BaseModel):
    id: str
    number: str
    short_description: str
    description: str | None = None
    request_type: str | None = None
    params: dict
    targets: list[str]
    priority: str
    state: str
    assignment_group: str
    requested_by: str
    automation_request_id: str | None = None
    execution_id: str | None = None
    resolution_notes: str | None = None
    last_agent_run_at: datetime | None = None
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ServiceNowCaseDetailResponse(ServiceNowCaseResponse):
    events: list[ServiceNowCaseEventResponse] = Field(default_factory=list)


class ServiceNowAgentRunResponse(BaseModel):
    scanned: int
    processed: int
    resolved: int
    awaiting_approval: int
    manual_attention: int
    errors: int
    case_numbers: list[str]
