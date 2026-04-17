# AGENTS.md

## Repo Structure
- `apps/backend`: FastAPI API, persistence, orchestration entrypoint.
- `apps/frontend`: Next.js + React + TypeScript UI.
- `services/orchestrator`: multi-agent graph and state transitions.
- `services/awx_client`: AWX REST client (real + mock).
- `services/cmdb_sim`: CMDB simulation logic and policies.
- `services/policy_engine`: risk classification and approval decisions.
- `services/automation_catalog`: automation reuse/publish logic.
- `services/playbook_factory`: restricted blueprint-based playbook generation.
- `services/servicenow_sim`: ServiceNow functional simulation, queue agent, MCP bridge.
- `ansible`: inventories, templates, roles, generated playbooks.
- `tests`: backend, integration, orchestrator, frontend, ansible checks.
- `docs`: architecture, runbooks, ADRs, current state.

## Commands
- `make bootstrap`: prepare local environment files and seed data.
- `make up`: run stack with Docker Compose.
- `make down`: stop stack.
- `make run-servicenow`: run ServiceNow-sim API (separate process).
- `make run-backend`: run Automation Factory Lite backend.
- `make run-frontend`: run Automation Factory Lite frontend.
- `make up-all`: run all three local services together.
- `make run-dev`: legacy alias for `make up-all`.
- `make lint`: run backend lint/tests + ansible lint checks.
- `make test`: run Python test suites including ansible validation.
- `make test-frontend`: run frontend unit tests.
- `python3 services/servicenow_sim/mcp_server.py`: run ServiceNow-sim MCP server (requires `mcp` package).

## Default Local Ports
- AFL frontend: `13000`
- AFL backend: `18010`
- ServiceNow-sim API: `18095`
- ServiceNow standalone portal is served from ServiceNow-sim root: `http://<host>:18095/`
- If a port is busy, change it in `.env`; run scripts must fail fast (no silent port reuse).

## Security Restrictions (Mandatory)
- Never execute or generate automations for firewall, sudoers, kernel, networking, secrets, databases, or mass OS upgrades.
- Only allow actions from the approved catalog:
  - `create_user`, `delete_user`, `reset_password`, `add_ssh_key`
  - `create_directory`
  - `install_service`, `install_package`, `restart_service`, `manage_service`, `install_agent`
  - `deploy_template`
  - `check_uptime`, `check_patch_status`, `check_connectivity`
- Automation generation must be blueprint-driven only (no arbitrary task generation).
- Every request must have `ticket_id` (provided by user or auto-generated fallback) and be traceable in request, execution, and audit records.
- ServiceNow-sim cases must map to `ticket_id=case_number` for traceability.
- Every request must pass risk classification.
- Risk handling:
  - `low`: auto execution allowed.
  - `medium`: explicit approval required.
  - `high` or out-of-catalog: reject with reason.
- Idempotency is required for every generated automation.
- Always audit request, approval, publication, execution events.

## AWX Publication Rules
- Publish only validated `published` automations.
- Use idempotent bootstrap for organization/project/inventory/template.
- Launch jobs only when policy permits and approvals are satisfied.
- Always inject correlation vars in launches: `afl_ticket_id`, `afl_request_id`.
- Support `AWX_MODE=mock|real`; `mock` is default-safe fallback.

## Mock vs Real Policy
- Default mode is `mock` when AWX credentials are missing/unreachable.
- Real AWX mode requires valid `AWX_URL`, `AWX_TOKEN`, and reachable project/inventory.
- Optional external ticket notification is controlled by `ITSM_WEBHOOK_*`; notification failures never block automation flow and must be audited.
- If any external dependency fails, continue with mock path and persist fallback evidence.
- MCP server is optional; core platform must continue without MCP dependency installed.
- AFL must integrate with ServiceNow through MCP bridge contract (`/api/servicenow-mcp/*`) and external ServiceNow service URL, not by direct UI-to-ServiceNow calls.

## Out of Scope
- Privilege escalation policy changes.
- Arbitrary shell command execution outside blueprints.
- High-risk remediations and broad infrastructure reconfiguration.

## Definition of Done
- End-to-end flow works from intake to audit in mock mode.
- Real AWX integration path is implemented and documented.
- Ticket traceability is visible end-to-end (`intake -> execution -> audit`) and filterable by `ticket_id`.
- ServiceNow-sim queue can be processed by agent with visible states (`resolved`, `awaiting_approval`, `needs_manual_attention`) and full case event history.
- Required docs and runbooks are up to date.
- Automated tests run and results are captured in docs/current-state.md.
