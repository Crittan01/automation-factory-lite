export type Dashboard = {
  total_requests: number;
  automations_reused: number;
  automations_generated: number;
  mean_ticket_to_publish_seconds: number;
  mean_ticket_to_execution_seconds: number;
  success: number;
  failed: number;
  actions_with_approval: number;
};

export type IntakeResponse = {
  id: string;
  status: string;
  risk_level?: string;
  risk_reason?: string;
  requires_approval: boolean;
  approved?: boolean;
  rejection_reason?: string;
  structured_spec: Record<string, unknown>;
  warnings: string[];
  automation_id?: string;
  execution_id?: string;
  created_at: string;
  updated_at: string;
};

export type Host = {
  id: string;
  hostname: string;
  ip: string;
  environment: string;
  owner: string;
  criticality: string;
  operating_system: string;
  tags: string[];
  allowed_actions: string[];
  state: string;
  recent_history: Record<string, unknown>[];
};

export type CatalogAutomation = {
  id: string;
  name: string;
  request_type: string;
  version: string;
  playbook_path: string;
  required_params: string[];
  optional_params: string[];
  risk_level: string;
  status: string;
  last_used?: string;
  origin: string;
  validation_results: Record<string, unknown>;
  metadata: Record<string, unknown>;
};

export type TimelineEvent = {
  actor: string;
  step: string;
  status: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export type ApprovalItem = {
  request_id: string;
  request_text: string;
  risk_level: string;
  risk_reason: string;
  structured_spec: Record<string, unknown>;
  created_at: string;
};

export type Execution = {
  id: string;
  request_id: string;
  awx_mode: string;
  template_name: string;
  hosts: string[];
  extra_vars: Record<string, unknown>;
  job_id: string;
  status: string;
  output_summary: string;
  started_at?: string;
  completed_at?: string;
};

export type AuditEntry = {
  id: string;
  request_id?: string;
  event_type: string;
  message: string;
  payload: Record<string, unknown>;
  created_at: string;
};
