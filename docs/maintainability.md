# Maintainability Review

## Objective
Clarify what is essential vs optional in this repository to keep long-term maintenance sustainable.

## Core Runtime (Required)
- `apps/backend`
  - API contracts, orchestrator entrypoint, persistence and risk/policy flow.
- `apps/frontend`
  - User interfaces (`/servicenow-connector` executive connector, `/servicenow` technical, plus operational views).
- `services/orchestrator`
  - Multi-actor flow and request lifecycle.
- `services/servicenow_sim`
  - Queue simulation + case agent + MCP server bridge.
  - Can run as dedicated service (`services/servicenow_sim/api.py`) on separate port.
- `services/policy_engine`, `services/playbook_factory`, `services/automation_catalog`, `services/cmdb_sim`, `services/awx_client`
  - Security gates and automation factory behavior.
- `ansible`
  - Restricted playbooks and templates consumed by publication/execution paths.

## Quality Gates (Strongly Recommended)
- `tests`
  - Regression safety for orchestrator, policy, ServiceNow queue agent, and integration flow.
- `docs/architecture.md`, `docs/demo-runbook.md`, `docs/current-state.md`
  - Operational continuity and demo repeatability.
- `AGENTS.md`
  - Normative engineering guardrails.

## Optional / Contextual
- `infra/docker-compose.yml`
  - Useful for local reproducibility but not mandatory when running backend/frontend manually.
- `scripts/*`
  - Convenience for seeding/bootstrap/demo.
- MCP package runtime
  - `services/servicenow_sim/mcp_server.py` is optional if MCP is not needed in the target environment.

## Suggested Lean Profile (if minimizing complexity)
1. Keep only primary UI routes:
   - `/servicenow-connector`
   - `/approvals`
   - `/audit`
2. Keep technical views hidden or move to an admin mode.
3. Keep Docker files only if the team actively uses containerized local environments.
4. Keep test coverage for:
   - policy/risk
   - service queue agent
   - end-to-end mock flow

## Current Recommendation
Maintain current structure as “production-demo” profile:
- It is intentionally broader to support executive demo + technical validation.
- Navigation now prioritizes business value first, while preserving technical depth for troubleshooting.
