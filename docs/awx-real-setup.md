# AWX Real Setup

## Required Inputs
- `AWX_URL` (example: `https://ol9-awx.lab.com`)
- `AWX_TOKEN` (admin token or scoped token with object creation + launch permissions)
- Project source available to AWX (manual/scm sync strategy)
- Reachable target hosts from AWX execution environment

## Environment Configuration
1. Copy `.env.example` to `.env`.
2. Set:
   - `AWX_MODE=real`
   - `AWX_URL=<your_awx_url>`
   - `AWX_TOKEN=<your_awx_token>`
   - `AWX_VERIFY_TLS=false` (or `true` with trusted certs)
   - `AWX_ORGANIZATION`, `AWX_PROJECT`, `AWX_INVENTORY`
   - `AWX_CREDENTIAL_ID=<machine_credential_id>` (recommended)
   - `AWX_PROJECT_SCM_TYPE=git`
   - `AWX_PROJECT_SCM_URL=<git_repo_with_playbooks>`
   - `AWX_PROJECT_SCM_BRANCH=<branch>`

## Bootstrap AWX Objects
```bash
curl -X POST http://localhost:8000/api/bootstrap/awx
```
Expected: organization, project, and inventory created or reused idempotently.

Alternative direct script:
```bash
python3 scripts/setup_awx_scenario.py
```

Latest validated lab run (April 17, 2026):
- Organization: `Bancolombia`
- Project: `Agents_TI` (id `8`)
- Inventory: `AutomationFactoryLiteInventory` (id `3`)
- Workflow: `AFL - Low Risk Factory Workflow`
- Real AWX job validation:
  - job `180`: `successful`, but `no hosts matched`
  - job `182`: `successful`, host targeting fixed using `target`/`target_hosts` launch vars compatibility

## Publish + Execute Path
- Create request from UI or `/api/requests`.
- Revisor/Publicador publishes job template and launches job when policy allows.
- Job details visible in `/api/executions`.

## Host Connection Notes
- Ensure AWX inventory includes:
  - `ol9server1 ansible_host=192.168.250.30`
  - `rocky9server1 ansible_host=192.168.250.40`
- Ensure credentials can SSH and escalate as required.

## Troubleshooting
- If AWX API unavailable, service falls back to mock mode for continuity.
- Check `/api/audit` for execution failures and payload details.
- If AWX rejects template creation with `playbook not found`, sync project repository and ensure V1 playbooks exist in that repo.

## Data Needed to Complete Full Real Mapping
- Git repository/branch reachable by AWX that contains:
  - `playbooks/create_user.yml`
  - `playbooks/install_service.yml`
  - `playbooks/manage_service.yml`
  - `playbooks/install_agent.yml`
  - `playbooks/deploy_template.yml`
- Confirmed machine credential id or name with SSH access to:
  - `192.168.250.30`
  - `192.168.250.40`
