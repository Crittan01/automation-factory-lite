# ADR 0001 - Architecture Decisions

## Status
Accepted

## Context
Need a demo-ready but safe automation platform that creates reusable automation capital and supports both real and disconnected lab conditions.

## Decisions
1. Monorepo with clear module boundaries (`apps`, `services`, `ansible`, `docs`, `tests`).
2. FastAPI + SQLAlchemy backend for API and state persistence.
3. Next.js + TypeScript frontend for executive and technical views.
4. Multi-agent flow with LangGraph-enabled orchestration and deterministic fallback.
5. Strict blueprint-based playbook generation, no arbitrary automation synthesis.
6. Policy-first execution gating (`low`, `medium`, `high`).
7. AWX integration with dual mode (`real` and `mock`) and idempotent bootstrap.
8. SQLite default with Postgres-ready runtime config.
9. Mandatory ticket correlation (`ticket_id`) persisted in request/execution/audit and propagated to AWX extra vars.
10. Optional outbound ITSM webhook notifications are best-effort and non-blocking.
11. Functional ServiceNow simulation with queue agent was added to validate pending-case operations model.
12. Optional MCP server exposes ServiceNow-sim tools for agent-to-platform integration.

## Tradeoffs
- Deterministic parser is safer and predictable but less semantically rich than full LLM parsing.
- Mock mode improves resilience/demo readiness but can differ from AWX behavior details.
- Blueprint restriction limits flexibility but enforces security boundaries.
- Non-blocking ITSM webhook keeps operations resilient, but requires audit review if external ticket updates fail.
- ServiceNow simulation improves demo realism, but is not a full replacement for enterprise ServiceNow APIs/workflows.
