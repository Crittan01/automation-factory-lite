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

## Tradeoffs
- Deterministic parser is safer and predictable but less semantically rich than full LLM parsing.
- Mock mode improves resilience/demo readiness but can differ from AWX behavior details.
- Blueprint restriction limits flexibility but enforces security boundaries.
