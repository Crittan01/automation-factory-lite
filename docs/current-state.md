# Current State

## Block 1 - Repository and Architecture
### Implemented
- Monorepo structure created under `/Ansible/automation-factory-lite`.
- Base config files: `AGENTS.md`, `.env.example`, `docker-compose.yml`, `Makefile`.
- Mandatory documentation skeleton and module READMEs created.
- `scripts/seed_data.py` now seeds CMDB, baseline catalog entries, and demo history/audit records.

### Mocked
- None in this block.

### Tests Passed
- Not executed in this block.

### Remaining
- Core backend/services implementation and validation.

### Risks / Blockers
- None.

## Block 2 - Backend, Services, Orchestrator
### Implemented
- FastAPI API endpoints for intake, CMDB, catalog, approvals, timeline, AWX bootstrap, audit, dashboard.
- SQLAlchemy models for requests, catalog, CMDB, timeline, approvals, execution, audit.
- Orchestrator with three actor phases and timeline/audit capture.
- Policy engine with low/medium/high gating.
- CMDB simulator and validation.
- Playbook factory with secure blueprints and generated artifacts.
- AWX client with real and mock implementations.

### Mocked
- LLM-driven parsing (deterministic parser used as safe default).
- AWX execution details in mock mode.

### Tests Passed
- Pending execution.

### Remaining
- Run/repair tests and finalize docs with evidence.

### Risks / Blockers
- AWX real behavior depends on external connectivity and credentials.

## Block 3 - Frontend and UX
### Implemented
- Next.js app with 8 mandatory views:
  - Dashboard
  - Intake
  - CMDB
  - Catalog
  - Timeline
  - Approvals
  - Execution AWX
  - Audit
- API integration for each view.
- Visual style system with gradients, custom typography, and card-based executive layout.

### Mocked
- No frontend mock server; views depend on backend API.

### Tests Passed
- Pending execution.

### Remaining
- Execute frontend tests and capture results.

### Risks / Blockers
- Frontend package installation may require external network.

## Block 4 - Validation and Stabilization
### Implemented
- Fixed Python 3.9 compatibility issues for typing annotations and SQLAlchemy models.
- Standardized imports to `app.*` namespace to avoid duplicated SQLAlchemy metadata.
- Added safe `ENABLE_LANGGRAPH` feature flag (default `false`) to keep deterministic fallback stable.
- Hardened Ansible tests for sandboxed execution (`ANSIBLE_LOCAL_TEMP`/`HOME`) and missing tool modules.
- Added root `pytest.ini` for consistent test discovery/import paths.

### Mocked
- `LangGraph` execution path kept disabled by default; sequential multi-agent fallback is active.
- AWX real execution remains unvalidated in this environment (mock path validated).

### Tests Passed
- `pytest -q` from repo root: `14 passed, 7 skipped`.
- Passed suites:
  - `tests/backend/*`
  - `tests/integration/*`
  - `tests/orchestrator/*`
- Skipped suite:
  - `tests/ansible/test_ansible_validation.py` (toolchain modules not installed in environment).

### Remaining
- Run frontend unit tests after Node.js/npm installation.
- Run Ansible lint/syntax checks with full ansible toolchain installed.
- Validate real AWX path in connected environment.

### Risks / Blockers
- This VM currently lacks `node`, `npm`, and `docker`.
- Ansible executables exist but required Python modules (`ansible`, `ansiblelint`, `yamllint`) are unavailable in runtime PATH environment.

## Block 5 - AWX Real Scenario Bootstrap and Validation
### Implemented
- Real AWX connectivity validated against `https://ol9-awx.lab.com/`.
- Idempotent AWX scenario bootstrap executed with:
  - Organization: `Bancolombia` (reused due token scope).
  - Project: `Agents_TI` (SCM git).
  - Inventory: `AutomationFactoryLiteInventory`.
  - Hosts: `ol9server1` (`192.168.250.30`), `rocky9server1` (`192.168.250.40`).
  - Job templates:
    - `AFL - Create User`
    - `AFL - Install Service`
    - `AFL - Manage Service`
    - `AFL - Install Agent`
    - `AFL - Deploy Template`
  - Workflow template: `AFL - Low Risk Factory Workflow`.
- Real launch validated:
  - Initial launch: job `180` (`successful`, but `no hosts matched`).
  - Post client compatibility update (`target`/`target_hosts` enrichment): job `182` (`successful`) with real host execution on `ol9server1`.

### Mocked
- For template mapping only: requested V1 playbooks were not present in AWX project repository, so fallback mapping to an available playbook was applied to keep bootstrap functional.

### Tests Passed
- AWX bootstrap script: `python3 scripts/setup_awx_scenario.py` (real mode, successful).
- AWX real launch validation: direct `launch_job(...)` call, job completed successfully.

### Remaining
- Publish V1 playbooks (`playbooks/create_user.yml`, `install_service.yml`, `manage_service.yml`, `install_agent.yml`, `deploy_template.yml`) into the AWX project repository, then rerun bootstrap so each template points to its real restricted playbook.
- Validate real execution semantics for all 3 demo scenarios once playbook mapping is corrected.
- Validate inventory/group mapping expected by final V1 playbooks once mapping is corrected.

### Risks / Blockers
- Current AWX token cannot create new organizations (403 on `POST /api/v2/organizations/`), so bootstrap reuses existing editable org.
- AWX instance does not accept `scm_type=manual`; git-backed project is required.

## Block 6 - Test Toolchain Completion and Hardening
### Implemented
- Installed Node.js 20 + npm in the lab VM for frontend compatibility.
- Installed Ansible Python toolchain (`ansible`, `ansible-lint`, `yamllint`) in user scope.
- Fixed frontend unit test runtime issues:
  - Added explicit React import in `MetricCard` component and test.
  - Replaced `next/font/google` runtime fetch dependency with local CSS font stacks to keep builds stable without external font download.
- Hardened ansible validation test env for sandboxed filesystem constraints:
  - Added controlled temp/cache/ansible-home env values.
  - Preserved user home for python user-site module resolution.
- Updated `Makefile`:
  - `test` now runs python suites including ansible tests.
  - `test-frontend` uses `npm test -- --run`.
  - `lint` now runs `ansible-lint`/`yamllint` with deterministic env and no silent ignore.

### Mocked
- None in this block.

### Tests Passed
- `pytest -q -rA`: `21 passed`.
- `make test`: passed.
- `make test-frontend`: passed (Vitest `1 passed`).
- `make lint`: passed (backend/integration/orchestrator + ansible-lint + yamllint).
- `cd apps/frontend && npm run build`: passed.

### Remaining
- Docker/compose runtime is still not installed in this VM, so `make up` cannot be validated here yet.
- Real AWX templates still require final mapping to V1 playbooks in the project repository.

### Risks / Blockers
- AWX real execution currently uses fallback playbook mapping until V1 playbooks are published in AWX project source.

## Block 7 - AWX Real Mapping Finalized on automation-factory-lite Repo
### Implemented
- Repointed AWX SCM to user repository:
  - `https://github.com/Crittan01/automation-factory-lite.git`
  - branch: `develop`
- Updated AWX template definitions to V1 playbook paths under repo:
  - `ansible/playbooks/create_user.yml`
  - `ansible/playbooks/install_service.yml`
  - `ansible/playbooks/manage_service.yml`
  - `ansible/playbooks/install_agent.yml`
  - `ansible/playbooks/deploy_template.yml`
- Added robust AWX project auto-sync in bootstrap flow:
  - if project playbook list is empty and SCM is enabled, client triggers project update and waits.
- Rebootstrapped AWX scenario successfully:
  - Project: `AutomationFactoryLiteProject` (id `20`)
  - Inventory: `AutomationFactoryLiteInventory` (id `3`)
  - Job templates `14-18` now mapped to V1 playbooks with no unresolved mapping.

### Mocked
- None in this block.

### Tests Passed
- Targeted suites after AWX client changes:
  - `tests/backend/test_awx_mock_client.py`
  - `tests/integration/test_end_to_end_mock.py`
  - `tests/orchestrator/test_orchestrator_transitions.py`
- Full python suite remains green (`pytest -q`: `21 passed`).

### Remaining
- Push updated `install_agent` playbook to remote SCM branch used by AWX so OL9 package fallback logic is active.
- Ensure package repositories on targets include `cockpit` (or fallback `cockpit-ws`) for successful `install_agent` scenario.
- Optional: install Docker/Compose runtime in VM to validate `make up` locally.

### Risks / Blockers
- Demo scenario `install_agent` failed in prior real AWX runs with `telegraf`/`node_exporter` due host package availability, not orchestration or credential issues.

## Block 8 - OL9 Agent Strategy Update (cockpit-first)
### Implemented
- Changed analyzer default for `install_agent` to `cockpit` when agent is not explicitly provided.
- Updated static playbook `ansible/playbooks/install_agent.yml`:
  - default agent: `cockpit`
  - package mapping:
    - `cockpit` -> primary `cockpit`, fallback `cockpit-ws`
    - `node_exporter` -> primary `prometheus-node-exporter`, fallback `node_exporter`
    - `telegraf` -> primary `telegraf`
- Updated secure blueprint template for generated `install_agent` automations to use the same package mapping strategy.
- Updated demo assets to use `cockpit`:
  - `scripts/demo_scenarios.sh`
  - `docs/demo-runbook.md`
  - integration flow text in `tests/integration/test_end_to_end_mock.py`

### Mocked
- None in this block.

### Tests Passed
- `make test` passed.
- `make lint` passed.
- `make test-frontend` passed.
- `pytest -q` passed (`22 passed`).

### Remaining
- Push latest code to the AWX SCM branch (`develop`) so AWX jobs consume the new OL9 package fallback logic.
- Re-run real AWX scenario 3 after SCM sync and confirm successful install on both hosts.

### Risks / Blockers
- Current AWX run still reflects previous remote playbook content until changes are pushed/synced.

## Block 9 - AWX Publish Failure Diagnosis and Fix
### Implemented
- Diagnosed real failure seen in intake requests (`status=failed`) with reason:
  - `400 Client Error: Bad Request for url: https://ol9-awx.lab.com/api/v2/job_templates/`
- Root cause: generated runtime playbook paths (`generated/...`) are not visible to AWX SCM project.
- Implemented AWX-safe fallback in orchestrator publish step:
  - when automation points to `generated/...`, real execution publishes canonical safe playbook by request type (`ansible/playbooks/*.yml`).
- Improved failure observability:
  - Intake UI now shows `rejection_reason` and `risk_reason` directly.
  - Execution failure now stores richer HTTP error details when AWX returns a body.

### Mocked
- None in this block.

### Tests Passed
- `tests/integration/test_end_to_end_mock.py`
- `tests/orchestrator/test_orchestrator_transitions.py`
- `tests/backend/test_analyzer.py`

### Remaining
- Restart backend/frontend processes to load the fix.
- Re-run intake scenarios and validate execution records in `/execution` and audit entries in `/audit`.

### Risks / Blockers
- If AWX still returns 400 after this fix, next likely cause is project sync/credential/template constraints in AWX rather than playbook path resolution.

## Block 10 - Ticket Traceability End-to-End
### Implemented
- Added `ticket_id` correlation across backend models:
  - `automation_requests.ticket_id`
  - `execution_records.ticket_id`
  - `audit_logs.ticket_id`
- Intake API now accepts optional `ticket_id`; if missing, platform auto-generates one (`AFL-...`) and leaves warning evidence.
- Added runtime schema guard on startup to add missing `ticket_id` columns/indexes for existing DBs without requiring manual migration.
- Extended API filtering:
  - `GET /api/requests?ticket_id=...`
  - `GET /api/executions?ticket_id=...`
  - `GET /api/audit?ticket_id=...` (+ optional `request_id`, `event_type`)
- Pending approvals response now includes `ticket_id`.
- Orchestrator now propagates correlation to AWX launches:
  - `afl_ticket_id`
  - `afl_request_id`
- Added optional ITSM webhook notifier (`services/itsm_notifier`) controlled by:
  - `ITSM_WEBHOOK_ENABLED`
  - `ITSM_WEBHOOK_URL`
  - `ITSM_WEBHOOK_TOKEN`
  - `ITSM_WEBHOOK_TIMEOUT_SECONDS`
- Webhook behavior is best-effort/non-blocking; failures are audited as `ticket_notify_failed`.
- Updated UI for managerial traceability:
  - Intake: input/display `ticket_id`
  - Dashboard: ticket column
  - Timeline selector: ticket-centric label
  - Approvals/Execution: ticket visibility
  - Audit: filter by `ticket_id`
- Updated demo script to use deterministic ticket IDs (`AFL-DEMO-001..003`).

### Mocked
- ITSM webhook delivery remains mocked unless a real endpoint is configured.

### Tests Passed
- `python -m pytest -q`: `24 passed`
- `pytest -q tests/backend tests/integration tests/orchestrator`: passed
- `npm test -- --run` (frontend): passed
- `make lint`: passed (`ansible-lint`, `yamllint`, backend/integration/orchestrator tests)

### Remaining
- Optional: add API-level tests with `TestClient` once async test-client behavior is stabilized in this environment.
- Optional: connect real ITSM webhook endpoint for live ticket status synchronization.

### Risks / Blockers
- If webhook URL/token is wrong or unreachable, automation flow still continues (by design), but external ITSM system will not receive updates until fixed.

## Block 11 - ServiceNow Simulation + MCP Queue Agent
### Implemented
- Added ServiceNow functional simulation domain:
  - `servicenow_cases` model with lifecycle states (`new`, `in_progress`, `resolved`, `awaiting_approval`, `needs_manual_attention`).
  - `servicenow_case_events` timeline per case.
- Added backend ServiceNow API:
  - `GET /api/servicenow/cases`
  - `GET /api/servicenow/cases/{number}`
  - `POST /api/servicenow/cases`
  - `POST /api/servicenow/cases/seed`
  - `POST /api/servicenow/agent/run`
- Implemented queue-processing agent:
  - reads pending cases,
  - maps them to automation requests (`ticket_id=case_number`),
  - executes supported requests through existing orchestrator,
  - routes medium-risk to `awaiting_approval`,
  - escalates unsupported requests to `needs_manual_attention`.
- Added full audit correlation for ServiceNow processing events (`servicenow_case_processed`, `servicenow_case_escalated`, `servicenow_agent_run`).
- Added optional MCP server for ServiceNow simulation:
  - `services/servicenow_sim/mcp_server.py`
  - tools for listing/creating/getting cases and running queue agent.
- Added new UI page:
  - `/servicenow` with live polling queue, KPI counters, case detail timeline, quick case creation, seed, and run-agent actions.
- Dashboard now includes ServiceNow queue metrics.

### Mocked
- MCP transport dependency (`mcp` package) is optional and not mandatory for core runtime.
- ServiceNow remains simulated (not calling external ServiceNow SaaS APIs).

### Tests Passed
- New tests added:
  - `tests/backend/test_servicenow_agent.py`
  - `tests/integration/test_servicenow_end_to_end_mock.py`
- Full Python suite: `python -m pytest -q` -> `28 passed`.
- Frontend tests: `npm test -- --run` -> passed.
- Frontend build: `npm run build` -> passed.
- Lint/Ansible checks: `make lint` -> passed.

### Remaining
- Optional: wire real ServiceNow APIs and OAuth to replace simulation backend.
- Optional: register MCP server in client config for direct external agent tooling.

### Risks / Blockers
- If queue receives many medium/high-risk cases, throughput depends on approval/manual process by design.

## Block 12 - UX Simplification (ServiceNow MCP First)
### Implemented
- Simplified sidebar navigation:
  - primary executive modules visible by default.
  - technical modules hidden behind a toggle (`Mostrar/Ocultar Módulos Técnicos`).
- Renamed UI label and framing from `ServiceNow Live` to `ServiceNow MCP`.
- Enhanced `/servicenow` view with explicit backlog section:
  - `Catálogos por Atender` (counts by request type in open queue).
- Added dedicated executive console route:
  - `/servicenow-mcp` with ServiceNow-inspired layout and explicit MCP bridge status.
- Kept all technical modules available but de-emphasized for non-technical demos.

### Mocked
- None in this block.

### Tests Passed
- `npm test -- --run` -> passed.
- `npm run build` -> passed.

### Remaining
- Optional: if desired, remove technical modules entirely from main navigation and expose only via dedicated admin route.

### Risks / Blockers
- None.

## Block 13 - Realistic ServiceNow MCP Console + Maintainability Review
### Implemented
- Added dedicated executive UI route:
  - `/servicenow-mcp`
  - ServiceNow-inspired visual language (header/nav/panel structure).
- Kept `/servicenow` as technical operations view and added cross-link to executive console.
- Added explicit MCP bridge status endpoint:
  - `GET /api/servicenow/mcp/status`
  - fields include enablement, mode, command, package availability and queue snapshot.
- Added MCP bridge env config:
  - `SERVICENOW_MCP_ENABLED`
  - `SERVICENOW_MCP_MODE`
  - `SERVICENOW_MCP_ENDPOINT`
  - `SERVICENOW_MCP_SERVER_CMD`
- Updated navigation prioritization:
  - business modules first
  - technical modules hidden behind toggle.
- Added maintainability document:
  - `docs/maintainability.md` with core vs optional modules and lean-profile recommendations.
- Refined global visual palette for more coherent enterprise look.

### Mocked
- Real external ServiceNow SaaS API integration is still simulated through internal ServiceNow domain + MCP bridge.

### Tests Passed
- `python -m pytest -q` -> `29 passed`
- `pytest tests/backend tests/integration tests/orchestrator -q` -> passed
- `npm test -- --run` -> passed
- `npm run build` -> passed
- `make lint` -> passed

### Remaining
- Optional: replace simulated ServiceNow backend with real ServiceNow table APIs (OAuth).
- Optional: role-based UI mode (executive vs admin) to hide technical routes by permission instead of toggle.

### Risks / Blockers
- Branding can only be “ServiceNow-inspired” to avoid exact product UI cloning constraints.

## Block 14 - Service Separation (ServiceNow Sim on Dedicated Port)
### Implemented
- Added dedicated ServiceNow-sim API app:
  - `services/servicenow_sim/api.py`
  - runnable in separate process/port (`8095` default).
- Added external ServiceNow client for Automation Factory Lite:
  - `services/servicenow_sim/external_client.py`
- Added external MCP worker flow:
  - `services/servicenow_sim/external_agent.py`
  - `/api/servicenow-mcp/agent/run` now processes queue from external ServiceNow service.
- Added proxy-style MCP endpoints in AFL backend:
  - `/api/servicenow-mcp/cases*`
  - `/api/servicenow-mcp/agent/run`
- MCP status endpoint now reports external service reachability and bridge degradation state.
- Added helper script:
  - `scripts/run_servicenow_sim.sh`

### Mocked
- External ServiceNow is still simulation; integration pattern now mirrors separated real-service topology.

### Tests Passed
- `python -m pytest -q` -> `29 passed`
- `npm test -- --run` -> passed
- `npm run build` -> passed
- `make lint` -> passed

### Remaining
- Optional: replace simulated ServiceNow API with real ServiceNow OAuth/table APIs under same external-client contract.

### Risks / Blockers
- Running only backend/frontend without starting ServiceNow-sim service leaves MCP status in degraded mode (by design).

## Block 15 - Conflict-Safe Ports + MCP Bridge Hardening
### Implemented
- Normalized local default ports to reduce conflicts with common dev processes:
  - AFL backend: `18010`
  - AFL frontend: `13000`
  - ServiceNow-sim API: `18095`
- Updated config defaults:
  - `.env.example`
  - `apps/backend/app/settings.py`
  - `apps/frontend/src/lib/api.ts`
  - `docker-compose.yml` default host mappings.
- Updated local `.env` with the same conflict-safe defaults and explicit ServiceNow bridge config:
  - `SERVICENOW_MCP_MODE=external_http_bridge`
  - `SERVICENOW_SIM_HOST`, `SERVICENOW_SIM_PORT`
  - `SERVICENOW_EXTERNAL_BASE_URL=http://127.0.0.1:18095`
- Added operational run scripts with port-collision guardrails:
  - `scripts/run_backend.sh`
  - `scripts/run_frontend.sh`
  - `scripts/run_servicenow_sim.sh` (enhanced to read `.env` + check free port)
  - `scripts/run_dev_stack.sh` (single command startup for all services).
- Added Make targets:
  - `run-backend`, `run-frontend`, `run-servicenow`, `run-dev`.
- Hardened MCP bridge endpoints in backend:
  - `/api/servicenow-mcp/*` now fail fast with `503` and explicit reason when bridge/service is disabled or unreachable.
  - `/api/servicenow/mcp/status` now exposes integration model and expected external service host/port.

### Mocked
- ServiceNow remains simulated (separate service process), but now via explicit external bridge contract from AFL.

### Tests Passed
- `pytest tests/backend tests/integration tests/orchestrator -q` -> passed (`22 passed`).
- `cd apps/frontend && npm test -- --run` -> passed (`1 passed`).

### Remaining
- Optional: add real ServiceNow OAuth/table implementation behind the same `ExternalServiceNowClient` contract.
- Optional: add a dedicated process supervisor (systemd/pm2) for persistent local lab runtime.

### Risks / Blockers
- If external ServiceNow-sim service is down, MCP queue operations intentionally return `503` (explicitly visible in UI/API).

## Block 16 - ServiceNow Standalone Portal + AFL Connector Renaming
### Implemented
- Exposed ServiceNow as standalone UI on dedicated service/port:
  - `GET /` on ServiceNow-sim (`:18095`) now serves ServiceNow portal (no more root 404).
  - Portal manages queue visibility and dispatches pending cases to AFL connector.
- Added ServiceNow-sim integration proxy endpoints:
  - `GET /api/automation/mcp/status` (proxy to AFL connector status)
  - `POST /api/automation/agent/run` (dispatch to AFL `/api/servicenow-mcp/agent/run`)
- Renamed AFL business module from `ServiceNow MCP` to `ServiceNow Connector`:
  - new route: `/servicenow-connector`
  - legacy route `/servicenow-mcp` kept as redirect for compatibility.
- Updated AFL navigation and technical view links to use connector naming.

### Mocked
- ServiceNow remains simulated, but with separated UI/service boundary that mirrors real platform topology.

### Tests Passed
- `pytest tests/backend tests/integration tests/orchestrator -q` -> passed (`22 passed`).
- `cd apps/frontend && npm test -- --run` -> passed (`1 passed`).

### Remaining
- Optional: add automated browser test for ServiceNow standalone portal.
- Optional: replace simulated ServiceNow APIs with real ServiceNow OAuth/table APIs under the same proxy contract.

### Risks / Blockers
- ServiceNow portal dispatch action depends on AFL backend availability; if AFL is down, dispatch endpoint returns `502` with explicit error.

## Block 17 - ServiceNow Portal UX Realism Tuning
### Implemented
- Reworded ServiceNow standalone portal copy to business/operations language (less technical endpoint-centric text).
- Updated main actions for realistic operator flow:
  - `Create Demo Cases`
  - `Dispatch Eligible Cases`
  - `Refresh Queue`
- Improved queue table to resemble incident/work queue usage:
  - columns now include short description, priority, assignment group.
- Kept technical details in secondary context while preserving traceability.
- Added configurable link from ServiceNow portal to AFL connector UI via:
  - `AFL_FRONTEND_BASE_URL`

### Mocked
- ServiceNow remains simulated, but UX now better mirrors practical ITSM usage semantics.

### Tests Passed
- `pytest tests/backend tests/integration tests/orchestrator -q` -> passed (`22 passed`).
- `cd apps/frontend && npm test -- --run` -> passed (`1 passed`).
- `cd apps/frontend && npm run build` -> passed.

### Remaining
- Optional: add server-side templating or separate static assets for easier portal theming/customization.

### Risks / Blockers
- Visual parity with full enterprise ServiceNow product remains intentionally approximate (no product cloning).

## Block 18 - Demo Case Seeding Feedback and Forced Batches
### Implemented
- Added forced seeding path for ServiceNow demo queue:
  - `POST /api/cases/seed?force=true` creates a fresh batch every click.
  - Each forced batch gets unique tags in short description/username to avoid “no visible change” confusion.
- Updated ServiceNow standalone portal button behavior:
  - `Create Demo Cases` now calls forced seeding and shows explicit success/failure summary.
- Propagated forced seeding support to AFL connector/local technical views:
  - `/api/servicenow-mcp/cases/seed?force=true`
  - `/api/servicenow/cases/seed?force=true`
- Extended external client and backend bridge endpoints to accept `force` flag.

### Mocked
- None in this block.

### Tests Passed
- `pytest tests/backend tests/integration tests/orchestrator -q` -> passed (`22 passed`).
- `cd apps/frontend && npm test -- --run` -> passed (`1 passed`).
- `cd apps/frontend && npm run build` -> passed.

### Remaining
- Optional: add a dedicated “idempotent seed” button for teams that prefer static repeatable demo dataset.

### Risks / Blockers
- Repeated forced seeding intentionally grows queue volume; use periodically clean/reset procedures in long demo sessions.

## Block 19 - Expanded Operational Catalog + Seed Idempotency + Full Certification
### Implemented
- Expanded approved automation catalog end-to-end (analyzer, policy, blueprint factory, AWX canonical mapping, CMDB permissions, ServiceNow mapping):
  - `create_user`, `delete_user`, `reset_password`, `add_ssh_key`
  - `create_directory`
  - `install_service`, `install_package`, `restart_service`, `manage_service`, `install_agent`
  - `deploy_template`
  - `check_uptime`, `check_patch_status`, `check_connectivity`
- Added secure static playbooks for the new actions:
  - `ansible/playbooks/delete_user.yml`
  - `ansible/playbooks/reset_password.yml`
  - `ansible/playbooks/add_ssh_key.yml`
  - `ansible/playbooks/create_directory.yml`
  - `ansible/playbooks/install_package.yml`
  - `ansible/playbooks/restart_service.yml`
  - `ansible/playbooks/check_uptime.yml`
  - `ansible/playbooks/check_patch_status.yml`
  - `ansible/playbooks/check_connectivity.yml`
- Updated AWX job-template bootstrap definitions to include the expanded playbook set.
- Fixed `manage_service` static playbook to consume `state` from request params.
- Adjusted ServiceNow simulation seeding model:
  - default seed is now idempotent (no duplicate queue flooding).
  - forced seeding is still available via API (`force=true`) for controlled test batches.
  - demo queue now includes varied real-like case payloads across user/access, resources, services/software, diagnostics/compliance, and one unsupported case.
- UI/UX updates:
  - AFL `/servicenow-connector`: sync button now non-duplicating and explicit that MCP worker executes real backend endpoint.
  - Intake examples now include expanded catalog operations.

### Mocked
- AWX real execution is still environment-dependent; mock mode remains validated fallback.
- ServiceNow remains simulated but integrated through external MCP bridge contract.

### Tests Passed
- `pytest tests/backend tests/integration tests/orchestrator -q` -> passed (`34 passed`).
- `pytest tests/ansible/test_ansible_validation.py -q` -> passed (`16 passed`).
- `pytest -q` -> passed (`50 passed`).
- `cd apps/frontend && npm test -- --run` -> passed (`1 passed`).
- `cd apps/frontend && npm run build` -> passed (all routes build successfully).

### Remaining
- Validate full AWX real execution for each newly added catalog action against reachable hosts/repositories.
- Optional: add browser E2E tests for ServiceNow standalone and AFL connector UI interactions.

### Risks / Blockers
- Some package/service outcomes in real hosts depend on repository availability and host state (expected for OL9/Rocky lab conditions).

## Block 20 - Certification Run (Mock 100% + Real AWX Gap Identified)
### Implemented
- Added full-cycle certification runner:
  - `scripts/certify_full_cycle.py`
  - validates all requested operational cases end-to-end:
    - user/access (`create_user`, `delete_user`, `reset_password`, `add_ssh_key`)
    - resources (`create_directory`)
    - services/software (`install_package`, `install_service`, `restart_service`)
    - diagnostics/compliance (`check_uptime`, `check_patch_status`, `check_connectivity`)
  - includes approval auto-flow for medium-risk scenarios during certification run.
  - includes ServiceNow queue batch certification with state transition checks.

### Mocked
- Mock mode (`--mode mock`) used AWX mock client and completed full matrix successfully.

### Tests Passed
- `python3 scripts/certify_full_cycle.py --mode mock --output .run-logs/certification-mock.json`
  - result: `11/11` scenarios passed, ServiceNow batch passed.
- `pytest -q`
  - result: `50 passed`.
- `pytest tests/ansible/test_ansible_validation.py -q`
  - result: `16 passed`.
- `cd apps/frontend && npm test -- --run && npm run build`
  - frontend tests/build passed.

### Remaining
- Real AWX certification currently fails for the newly added actions because AWX project SCM branch does not yet contain the new playbooks.
- Evidence from real run:
  - `python3 scripts/certify_full_cycle.py --mode real --output .run-logs/certification-real.json`
  - failures show: `400 Bad Request: {"playbook":["Playbook not found for project."]}` for new playbooks.

### Risks / Blockers
- Git push to `origin/develop` failed from this environment due missing GitHub push credentials:
  - `fatal: could not read Username for 'https://github.com': No such device or address`
- Until repository branch used by AWX contains new playbooks and AWX project sync is re-run, real-mode certification cannot reach 100% for the new action set.
