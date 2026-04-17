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
- `ansible`: inventories, templates, roles, generated playbooks.
- `tests`: backend, integration, orchestrator, frontend, ansible checks.
- `docs`: architecture, runbooks, ADRs, current state.

## Commands
- `make bootstrap`: prepare local environment files and seed data.
- `make up`: run stack with Docker Compose.
- `make down`: stop stack.
- `make lint`: run backend lint/tests + ansible lint checks.
- `make test`: run Python test suites including ansible validation.
- `make test-frontend`: run frontend unit tests.

## Security Restrictions (Mandatory)
- Never execute or generate automations for firewall, sudoers, kernel, networking, secrets, databases, or mass OS upgrades.
- Only allow actions from V1 catalog: `create_user`, `install_service`, `manage_service`, `install_agent`, `deploy_template`.
- Automation generation must be blueprint-driven only (no arbitrary task generation).
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
- Support `AWX_MODE=mock|real`; `mock` is default-safe fallback.

## Mock vs Real Policy
- Default mode is `mock` when AWX credentials are missing/unreachable.
- Real AWX mode requires valid `AWX_URL`, `AWX_TOKEN`, and reachable project/inventory.
- If any external dependency fails, continue with mock path and persist fallback evidence.

## Out of Scope
- Privilege escalation policy changes.
- Arbitrary shell command execution outside blueprints.
- High-risk remediations and broad infrastructure reconfiguration.

## Definition of Done
- End-to-end flow works from intake to audit in mock mode.
- Real AWX integration path is implemented and documented.
- Required docs and runbooks are up to date.
- Automated tests run and results are captured in docs/current-state.md.
