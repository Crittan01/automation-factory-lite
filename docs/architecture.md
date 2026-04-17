# Architecture

## Purpose
Automation Factory Lite is a low-risk automation factory, focused on creating reusable automation capital. It never executes out-of-catalog or forbidden actions.

## Modules
- `apps/backend`: API and persistence.
- `apps/frontend`: executive + technical UI.
- `services/orchestrator`: multi-agent workflow and transitions.
- `services/cmdb_sim`: host and action validation.
- `services/policy_engine`: risk classification and approvals.
- `services/playbook_factory`: secure blueprint-based generation.
- `services/automation_catalog`: reuse-first automation registry.
- `services/awx_client`: AWX publication/execution (`mock` + `real`).
- `ansible`: inventories, templates, static and generated playbooks.

## End-to-end Flow
```mermaid
flowchart LR
    UI[UI Intake] --> API[FastAPI /api/requests]
    API --> ANALISTA[Analista]
    ANALISTA --> CMDB[CMDB Sim Validation]
    CMDB --> CONSTRUCTOR[Constructor]
    CONSTRUCTOR --> CATALOG[Catalog Reuse?]
    CATALOG -->|yes| REVIEW[Revisor/Publicador]
    CATALOG -->|no| FACTORY[Playbook Factory]
    FACTORY --> REVIEW
    REVIEW --> POLICY[Policy Engine]
    POLICY -->|low| AWX[AWX Publish + Execute]
    POLICY -->|medium| APPROVAL[UI Approval]
    APPROVAL --> AWX
    POLICY -->|high / out of scope| REJECT[Reject with explanation]
    AWX --> AUDIT[Audit + Timeline + History]
    REJECT --> AUDIT
```

## Agent Responsibilities
```mermaid
flowchart TD
    A[Analista] --> B[Constructor]
    B --> C[Revisor/Publicador]

    A --- A1[Parse NL request]
    A --- A2[Extract intent/params/targets]
    A --- A3[Emit structured JSON + warnings]

    B --- B1[Search reusable automation]
    B --- B2[Generate only from safe blueprints]
    B --- B3[Create playbook, vars, metadata, readme]

    C --- C1[Policy and risk check]
    C --- C2[Quality and idempotency guard]
    C --- C3[Publish/execute in AWX or wait approval]
```

## Data Model Summary
- `automation_requests`
- `timeline_events`
- `approval_decisions`
- `execution_records`
- `automation_catalog`
- `cmdb_hosts`
- `audit_logs`

## Security Decisions
- Blocked domains: firewall, sudoers, kernel, network, secrets, databases, massive upgrades.
- Strict allowlist on request types and parameters.
- Safe defaulting for minor ambiguities with warning trail.
- No arbitrary playbook synthesis.

## Real vs Mock
- `AWX_MODE=mock` by default.
- Real AWX path available when credentials and connectivity exist.
- If real fails, mock fallback keeps demo and testing functional.
