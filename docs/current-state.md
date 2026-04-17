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
