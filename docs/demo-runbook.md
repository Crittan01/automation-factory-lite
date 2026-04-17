# Demo Runbook

## Goal
Demonstrate end-to-end flow with visible multi-agent traceability.

## Preconditions
- Backend and frontend running (`make up` or local processes).
- API reachable at `http://localhost:8000`.
- UI reachable at `http://localhost:3000`.
- Seed loaded: `python3 scripts/seed_data.py`.
- AWX scenario bootstrapped: `python3 scripts/setup_awx_scenario.py` (when `AWX_MODE=real`).

## Steps
1. Open Dashboard and confirm KPIs load.
2. Open Intake and run scenario 1:
   - `Crear usuario analista1 en ol9server1 sin sudo`
3. Validate timeline in Timeline view:
   - Analista -> Constructor -> Revisor/Publicador
4. Open Intake and run scenario 2:
   - `Instalar nginx en rocky9server1`
5. Validate catalog entry was generated/reused in Catálogo view.
6. Open Intake and run scenario 3:
   - `Instalar agente telegraf en ol9server1 y rocky9server1`
7. Open Aprobaciones view:
   - approve pending request
8. Open Ejecución AWX view:
   - confirm template, hosts, vars, status
9. Open Auditoría view:
   - confirm event trail and evidence payloads.

## CLI Shortcut
```bash
bash scripts/demo_scenarios.sh
```

## Expected Outcomes
- Scenario 1: low risk, auto-executed.
- Scenario 2: low risk, auto-executed.
- Scenario 3: medium risk, pending approval then executed.

## AWX Real Note
- If the AWX project repository does not yet include the V1 playbooks, templates can still launch via fallback mapping for connectivity validation, but functional semantics of V1 actions must be validated after real playbook paths are present.
