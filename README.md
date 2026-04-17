# Automation Factory Lite

Automation Factory Lite is a focused automation factory for repetitive, low-risk operations. It accepts natural-language requests, routes them through a multi-agent workflow, reuses or safely generates restricted Ansible automation, publishes/executes in AWX (real or mock), and stores complete audit evidence.

## What this project is
- A reusable automation capital builder (not a generic IT copilot).
- A secure V1 platform limited to low-risk catalog actions.
- A demo-ready lab platform with executive and technical visibility.

## Supported V1 actions
1. Create Linux user (no sudo by default)
2. Install allowed service (`nginx` or `httpd`)
3. Manage allowed service state (`start|stop|restart|status`)
4. Install allowed agent
5. Deploy config from template into allowed paths
6. Record result/evidence in simulated CMDB and history

## Quick start
1. `cp .env.example .env`
2. Set real credentials if available (`OPENAI_KEY`, `AWX_*`)
3. `make bootstrap`
4. `make up`
5. Open UI at `http://localhost:3000`
6. Backend API at `http://localhost:8000/docs`

## Modes
- `mock` (default): no external dependencies required.
- `real`: uses AWX REST API and optional LLM.

See:
- `docs/demo-runbook.md`
- `docs/awx-real-setup.md`
- `docs/architecture.md`
- `docs/current-state.md`
