export type Dashboard = {
  total_requests: number;
  automations_reused: number;
  automations_generated: number;
  mean_ticket_to_publish_seconds: number;
  mean_ticket_to_execution_seconds: number;
  success: number;
  failed: number;
  actions_with_approval: number;
  servicenow_open_cases?: number;
  servicenow_resolved_cases?: number;
  servicenow_manual_cases?: number;
};

export type IntakeResponse = {
  id: string;
  ticket_id: string;
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
  ticket_id: string;
  request_text: string;
  risk_level: string;
  risk_reason: string;
  structured_spec: Record<string, unknown>;
  created_at: string;
};

export type Execution = {
  id: string;
  request_id: string;
  ticket_id?: string;
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
  ticket_id?: string;
  event_type: string;
  message: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export type ServiceNowCaseEvent = {
  actor: string;
  event_type: string;
  message: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export type ServiceNowCase = {
  id: string;
  number: string;
  short_description: string;
  description?: string;
  request_type?: string;
  params: Record<string, unknown>;
  targets: string[];
  priority: string;
  state: string;
  assignment_group: string;
  requested_by: string;
  automation_request_id?: string;
  execution_id?: string;
  resolution_notes?: string;
  last_agent_run_at?: string;
  source: string;
  created_at: string;
  updated_at: string;
  events?: ServiceNowCaseEvent[];
};

export type ServiceNowAgentRun = {
  scanned: number;
  processed: number;
  resolved: number;
  awaiting_approval: number;
  manual_attention: number;
  errors: number;
  case_numbers: string[];
};

export type ServiceNowMcpStatus = {
  enabled: boolean;
  mode: string;
  endpoint?: string;
  server_cmd: string;
  mcp_package_installed: boolean;
  bridge_status: string;
  external_service_enabled?: boolean;
  external_service_url?: string;
  external_service_reachable?: boolean;
  external_service_error?: string;
  queue_open_cases: number;
  checked_at: string;
};

export type AgenticStack = {
  checked_at: string;
  technologies: {
    llm: {
      enabled: boolean;
      vendor: string;
      model: string;
    };
    rag: {
      enabled: boolean;
      documents_indexed: number;
      retrieval_mode: string;
      vector_store: string;
    };
    mcp: {
      enabled: boolean;
      mode?: string;
      bridge_status?: string;
      external_service_reachable?: boolean;
    };
    awx: {
      mode: string;
      real_enabled: boolean;
      url?: string | null;
    };
    langgraph: {
      enabled_by_config: boolean;
      installed: boolean;
      active: boolean;
    };
  };
  agents: string[];
  rag_query?: string | null;
  rag_hits: AgenticRagHit[];
};

export type AgenticRagHit = {
  path: string;
  score: number;
  snippet: string;
};
