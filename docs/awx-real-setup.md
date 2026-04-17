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
- Project: `AutomationFactoryLiteProject` (id `20`)
- Inventory: `AutomationFactoryLiteInventory` (id `3`)
- Workflow: `AFL - Low Risk Factory Workflow`
- Job templates map directly to V1 playbooks:
  - `ansible/playbooks/create_user.yml`
  - `ansible/playbooks/install_service.yml`
  - `ansible/playbooks/manage_service.yml`
  - `ansible/playbooks/install_agent.yml`
  - `ansible/playbooks/deploy_template.yml`
- Demo launch evidence:
  - job `185` (`AFL - Create User`): `successful`
  - job `187` (`AFL - Install Service`): `successful`
  - job `188` (`AFL - Install Agent`): `failed` (`No package telegraf available.` on both hosts)
  - job `189` (`AFL - Install Agent` with `node_exporter`): `failed` (`No package node_exporter available.` on both hosts)

## Publish + Execute Path
- Create request from UI or `/api/requests`.
- Revisor/Publicador publishes job template and launches job when policy allows.
- Job details visible in `/api/executions`.

## Host Connection Notes
- Ensure AWX inventory includes:
  - `ol9server1 ansible_host=192.168.250.30`
  - `rocky9server1 ansible_host=192.168.250.40`
- Ensure credentials can SSH and escalate as required.
- For OL9/Rocky9, prefer `cockpit` and map package installation to `cockpit` with fallback `cockpit-ws`.
- If package repos still do not provide these names, add the required repository mirror before running install-agent.
- After changing playbooks locally, push to the AWX SCM branch and run `python3 scripts/setup_awx_scenario.py` to force project sync before re-testing.

## Troubleshooting
- If AWX API unavailable, service falls back to mock mode for continuity.
- Check `/api/audit` for execution failures and payload details.
- If AWX rejects template creation with `playbook not found`, sync project repository and ensure V1 playbooks exist in that repo.

## Data Needed to Complete Full Real Mapping
- Git repository/branch reachable by AWX that contains:
  - `ansible/playbooks/create_user.yml`
  - `ansible/playbooks/install_service.yml`
  - `ansible/playbooks/manage_service.yml`
  - `ansible/playbooks/install_agent.yml`
  - `ansible/playbooks/deploy_template.yml`
- Confirmed machine credential id or name with SSH access to:
  - `192.168.250.30`
  - `192.168.250.40`
