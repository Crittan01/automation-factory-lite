# Backend (FastAPI)

Provides APIs for intake, orchestration, CMDB simulation, automation catalog, approvals, AWX execution, dashboard metrics, and audit history.

## Run
```bash
export PYTHONPATH=/Ansible/automation-factory-lite/apps/backend:/Ansible/automation-factory-lite
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Test
```bash
pytest
```
