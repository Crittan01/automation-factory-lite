# Automation Factory Lite

Automation Factory Lite is a focused automation factory for repetitive, low-risk operations. It accepts natural-language requests, routes them through a multi-agent workflow, reuses or safely generates restricted Ansible automation, publishes/executes in AWX (real or mock), and stores complete audit evidence.

## What this project is
- A reusable automation capital builder (not a generic IT copilot).
- A secure V1 platform limited to low-risk catalog actions.
- A demo-ready lab platform with executive and technical visibility.
- End-to-end ticket traceability (`ticket_id`) across intake, execution, and audit.
- Functional ServiceNow-like queue simulation with autonomous case handling.

## Supported actions (approved catalog)
1. User/access: create user, delete user, reset password (hash), add SSH key
2. Resource: create directory in approved paths
3. Services/software: install allowed service, install allowed package, restart/manage service, install allowed agent
4. Config deployment: deploy template into approved paths
5. Diagnostics/compliance: check uptime, check patch status, connectivity probe
6. Traceability: record result/evidence in CMDB/history/audit

## Quick start
1. `cp .env.example .env`
2. Set real credentials if available (`OPENAI_KEY`, `AWX_*`)
3. `make bootstrap`
4. Start local services in separate terminals:
   - `make up-local-servicenow`
   - `make up-local-backend`
   - `make up-local-frontend`
   - or all together: `make up-all` (alias `make up-local`)
   - legacy alias still available: `make run-dev`
5. Open UI at `http://localhost:13000`
6. Backend API at `http://localhost:18010/docs`

Default conflict-safe ports:
- Frontend (Automation Factory Lite): `13000`
- Backend API (Automation Factory Lite): `18010`
- ServiceNow Sim API (decoupled): `18095`
- Print active ports/URLs from `.env`: `make show-ports`

## Modes
- `mock` (default): no external dependencies required.
- `real`: uses AWX REST API and optional LLM.
- Optional ticket webhook integration for ITSM/status sync (`ITSM_WEBHOOK_*`).
- Optional MCP access for ServiceNow sim queue via `services/servicenow_sim/mcp_server.py`.

## ServiceNow Sim (new)
- Standalone ServiceNow portal (separate service/UI):
  - `http://127.0.0.1:18095/`
  - owns queue view and triggers dispatch to AFL connector
- AFL UI modules:
  - `/servicenow-connector` (AFL connector module; consumes ServiceNow via MCP bridge)
  - `/servicenow-mcp` (legacy alias -> redirects to `/servicenow-connector`)
  - `/servicenow` (technical local view)
- Dedicated ServiceNow-sim API (separate process/port):
  - default: `http://127.0.0.1:18095`
  - start: `bash scripts/run_servicenow_sim.sh`
  - dispatch target configurable via `AFL_BACKEND_BASE_URL` (default `http://127.0.0.1:18010`)
  - connector UI link configurable via `AFL_FRONTEND_BASE_URL` (default `http://127.0.0.1:13000`)
- MCP bridge model:
  - Automation Factory Lite does not share DB with ServiceNow-sim in this mode.
  - AFL connects to ServiceNow-sim through external client endpoints (`/api/servicenow-mcp/*`) as an MCP bridge boundary.
  - If bridge is unavailable, status is reported as `degraded` and queue actions fail fast with `503`.
- API:
  - `GET /api/servicenow/mcp/status`
  - `GET /api/servicenow-mcp/cases`
  - `GET /api/servicenow-mcp/cases/{number}`
  - `POST /api/servicenow-mcp/cases`
  - `POST /api/servicenow-mcp/cases/seed`
  - `POST /api/servicenow-mcp/agent/run`
  - `GET /api/servicenow/cases`
  - `GET /api/servicenow/cases/{number}`
  - `POST /api/servicenow/cases`
  - `POST /api/servicenow/cases/seed`
  - `POST /api/servicenow/agent/run`
- Agent behavior:
  - Resolves supported low-risk cases automatically.
  - Leaves medium-risk cases in `awaiting_approval`.
  - Escalates out-of-catalog cases to `needs_manual_attention` with evidence.
  - ServiceNow portal `Create Demo Cases` is idempotent (no duplicate queue flooding); `force=true` is reserved for controlled test batches.

See:
- `docs/demo-runbook.md`
- `docs/awx-real-setup.md`
- `docs/architecture.md`
- `docs/current-state.md`
- `docs/maintainability.md`
