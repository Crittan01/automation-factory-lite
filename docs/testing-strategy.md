# Testing Strategy

## Backend Unit Tests
- Analyzer parsing and defaulting behavior.
- Policy engine risk and approval logic.
- CMDB validation.
- Catalog reuse behavior.
- AWX client mock and fallback.

## Integration Tests
- End-to-end request lifecycle in mock mode.
- Medium-risk approval flow.

## Orchestrator Tests
- Graph transition coverage through actor sequence.
- Fallback path when graph mode is disabled.
- Rejection for out-of-catalog request.

## Ansible Validation
- `ansible-playbook --syntax-check` for core playbooks.
- `ansible-lint` and `yamllint` with sandbox-safe env overrides.

## Frontend Tests
- Basic component rendering tests (`MetricCard`).
- UI pages are API-driven and manually verifiable in demo runbook.

## Commands
- Backend: `cd apps/backend && pytest`
- Frontend: `cd apps/frontend && npm test -- --run`
- Ansible checks: `pytest tests/ansible/test_ansible_validation.py`

## Current Environment Notes
- Python suites pass (`tests/backend`, `tests/integration`, `tests/orchestrator`, `tests/ansible`).
- Frontend unit tests pass with Node.js 20 runtime.
- `next build` completes successfully for static pages.
- Docker is not available by default in this VM, so `make up` depends on installing container runtime first.
