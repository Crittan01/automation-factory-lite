# Demo Runbook

## Goal
Demonstrate end-to-end flow with visible multi-agent traceability.

## Preconditions
- Backend and frontend running (`make up` or local processes).
- ServiceNow-sim API running on separate port (`bash scripts/run_servicenow_sim.sh` -> `:18095`).
- API reachable at `http://localhost:18010`.
- UI reachable at `http://localhost:13000`.
- Seed loaded: `python3 scripts/seed_data.py`.
- AWX scenario bootstrapped: `python3 scripts/setup_awx_scenario.py` (when `AWX_MODE=real`).

Recommended start sequence (conflict-safe):
1. `make run-servicenow`
2. `make run-backend`
3. `make run-frontend`

## Steps
1. Open Dashboard and confirm KPIs load.
2. Open Intake and run scenario 1:
   - Ticket: `AFL-DEMO-001`
   - Request: `Crear usuario analista1 en ol9server1 sin sudo`
3. Validate timeline in Timeline view:
   - Analista -> Constructor -> Revisor/Publicador
4. Open Intake and run scenario 2:
   - Ticket: `AFL-DEMO-002`
   - Request: `Instalar nginx en rocky9server1`
5. Validate catalog entry was generated/reused in Catálogo view.
6. Open Intake and run scenario 3:
   - Ticket: `AFL-DEMO-003`
   - Request: `Instalar agente cockpit en ol9server1 y rocky9server1`
7. Open Aprobaciones view:
   - approve pending request
8. Open Ejecución AWX view:
   - confirm template, hosts, vars, status
9. Open Auditoría view:
   - filter by ticket (`AFL-DEMO-001`, etc.) and confirm event trail/evidence payloads.
10. Open standalone ServiceNow portal (`http://localhost:18095/`):
   - click `Create Demo Cases` (idempotent; avoids duplicates)
   - click `Dispatch Eligible Cases`
11. Open AFL ServiceNow connector (`/servicenow-connector`) and validate same queue/traceability from AFL side.
12. Verify queue transitions:
   - supported cases -> `resolved`
   - medium risk -> `awaiting_approval`
   - out-of-catalog -> `needs_manual_attention`
13. Optional technical verification in `/servicenow`:
   - inspect low-level case detail and event timeline.

## CLI Shortcut
```bash
bash scripts/demo_scenarios.sh
```

## Expected Outcomes
- Scenario 1: low risk, auto-executed.
- Scenario 2: low risk, auto-executed.
- Scenario 3: medium risk, pending approval then executed.
- Additional supported examples:
  - `Eliminar usuario legacy_user en ol9server1`
  - `Crear carpeta /opt/automation_factory_lite/jobs/demo en rocky9server1`
  - `Obtener uptime en ol9server1`
- In real lab mode, scenario 3 uses `cockpit` by default for OL9.
- Each scenario is traceable by `ticket_id` in Dashboard, Timeline, Execution and Auditoría.
- ServiceNow-sim agent run leaves per-case event timeline and links to `automation_request_id`/`execution_id`.

## AWX Real Note
- If the AWX project repository does not yet include the V1 playbooks, templates can still launch via fallback mapping for connectivity validation, but functional semantics of V1 actions must be validated after real playbook paths are present.
