from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import requests
from sqlalchemy.orm import Session

repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / 'apps' / 'backend'))

from app.database import Base, SessionLocal, engine, get_db
from app.models import ServiceNowCase
from app.settings import get_settings
from services.cmdb_sim.service import seed_cmdb_hosts
from services.servicenow_sim.service import (
    add_case_event,
    create_case,
    get_case_by_number,
    list_case_events,
    list_cases,
    seed_demo_cases,
    seed_demo_cases_force,
)

settings = get_settings()
AFL_BACKEND_BASE_URL = os.getenv('AFL_BACKEND_BASE_URL', 'http://127.0.0.1:18010').rstrip('/')
AFL_FRONTEND_BASE_URL = os.getenv('AFL_FRONTEND_BASE_URL', 'http://127.0.0.1:13000').rstrip('/')
AFL_APP_NAME = os.getenv('AFL_APP_NAME', 'Fábrica de Automatización TI')
app = FastAPI(title='ServiceNow Sim API', version='1.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


class CaseCreateInput(BaseModel):
    short_description: str = Field(min_length=5)
    description: str | None = None
    request_type: str | None = None
    params: dict = Field(default_factory=dict)
    targets: list[str] = Field(default_factory=list)
    priority: str = '3'
    assignment_group: str = 'automation.factory'
    requested_by: str = 'servicenow.user'


class CaseUpdateInput(BaseModel):
    state: str | None = None
    resolution_notes: str | None = None
    automation_request_id: str | None = None
    execution_id: str | None = None
    append_event: dict | None = None


def _portal_html() -> str:
    html = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ServiceNow Portal (Sim)</title>
  <style>
    :root { color-scheme: light; }
    body { margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background: #f3f7fb; color: #1f2a44; }
    header { background: #1f2a44; color: #fff; padding: 16px 20px; border-bottom: 4px solid #0b5cab; }
    header h1 { margin: 0; font-size: 24px; }
    header p { margin: 4px 0 0; font-size: 12px; opacity: .85; }
    main { max-width: 1300px; margin: 0 auto; padding: 18px; display: grid; gap: 14px; }
    .grid { display: grid; gap: 12px; grid-template-columns: repeat(5, minmax(120px, 1fr)); }
    .card { background: #fff; border: 1px solid #d9e2ef; border-radius: 12px; padding: 12px; box-shadow: 0 2px 10px rgba(31,42,68,.04); }
    .kpi-label { font-size: 11px; text-transform: uppercase; color: #5a6780; letter-spacing: .06em; }
    .kpi-value { font-size: 28px; font-weight: 700; margin-top: 4px; }
    .toolbar { display: flex; gap: 8px; flex-wrap: wrap; }
    button { border: 0; border-radius: 10px; padding: 10px 12px; font-weight: 700; cursor: pointer; }
    .primary { background: #0b5cab; color: #fff; }
    .success { background: #0d8d53; color: #fff; }
    .dark { background: #1f2a44; color: #fff; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { text-align: left; padding: 10px 8px; border-bottom: 1px solid #e7edf5; }
    th { color: #5a6780; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; }
    .pill { padding: 3px 8px; border-radius: 999px; font-size: 11px; border: 1px solid #d9e2ef; }
    .state-new, .state-open, .state-reopened { background: #e9efff; color: #1f3ea1; }
    .state-in_progress { background: #e3f3ff; color: #0b5cab; }
    .state-resolved { background: #e8faef; color: #0d8d53; }
    .state-awaiting_approval { background: #fff6df; color: #a15c00; }
    .state-needs_manual_attention { background: #ffecef; color: #a8243c; }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; }
    .row { display: grid; gap: 12px; grid-template-columns: 2fr 1fr; }
    .muted { color: #5a6780; font-size: 12px; }
    @media (max-width: 980px) { .grid { grid-template-columns: repeat(2, minmax(120px, 1fr)); } .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <header>
    <h1>ServiceNow</h1>
    <p>Cola de incidentes y catálogo | Conectado a __AFL_APP_NAME__</p>
  </header>
  <main>
    <section class="card">
      <div class="toolbar">
        <button class="dark" id="btn-seed">Crear Casos Demo</button>
        <button class="primary" id="btn-refresh">Actualizar Cola</button>
      </div>
      <p class="muted" style="margin-top: 10px">
        Conector de automatización: <span id="connector-status">cargando...</span>
      </p>
      <p class="muted">API de backend: <span class="mono" id="afl-base">__AFL_BACKEND_BASE_URL__</span></p>
      <p class="muted" id="run-summary" style="margin-top: 6px"></p>
    </section>

    <section class="grid">
      <article class="card"><div class="kpi-label">Total</div><div class="kpi-value" id="k-total">0</div></article>
      <article class="card"><div class="kpi-label">Abiertos</div><div class="kpi-value" id="k-open">0</div></article>
      <article class="card"><div class="kpi-label">Resueltos</div><div class="kpi-value" id="k-resolved">0</div></article>
      <article class="card"><div class="kpi-label">En Aprobación</div><div class="kpi-value" id="k-approval">0</div></article>
      <article class="card"><div class="kpi-label">Atención Manual</div><div class="kpi-value" id="k-manual">0</div></article>
    </section>

    <section class="row">
      <article class="card">
        <h3 style="margin: 0 0 10px">Cola de Casos</h3>
        <table>
          <thead>
            <tr>
              <th>Caso</th>
              <th>Descripción Corta</th>
              <th>Estado</th>
              <th>Prioridad</th>
              <th>Grupo Asignado</th>
              <th>Actualizado</th>
            </tr>
          </thead>
          <tbody id="queue-body">
            <tr><td colspan="6" class="muted">Cargando...</td></tr>
          </tbody>
        </table>
      </article>
      <article class="card">
        <h3 style="margin: 0 0 10px">Flujo de Automatización</h3>
        <p class="muted">Este portal solo gestiona la atención ITSM y la cola de casos. La automatización se ejecuta desde __AFL_APP_NAME__.</p>
        <p class="muted">Política de automatización (ejecutada desde el Conector ServiceNow):</p>
        <ul class="muted" style="margin: 6px 0 0 18px; padding: 0;">
          <li>Casos soportados de bajo riesgo: procesados automáticamente.</li>
          <li>Casos de riesgo medio: enviados a flujo de aprobación.</li>
          <li>Casos fuera de alcance: enviados a atención manual.</li>
        </ul>
        <p class="muted" style="margin-top: 10px">
          Abrir Conector ServiceNow:
          <a href="__AFL_FRONTEND_BASE_URL__/servicenow-connector" target="_blank" rel="noreferrer" class="mono">__AFL_FRONTEND_BASE_URL__/servicenow-connector</a>
        </p>
      </article>
    </section>
  </main>
  <script>
    const snowApi = window.location.origin;
    const queueBody = document.getElementById('queue-body');

    async function loadStatus() {
      const statusEl = document.getElementById('connector-status');
      try {
        const res = await fetch(`${snowApi}/api/automation/mcp/status`, { cache: 'no-store' });
        const data = await res.json();
        if (!res.ok) throw new Error(data?.detail || 'estado no disponible');
        const bridgeLabel = data.bridge_status === 'connected' ? 'En línea' : 'Degradado';
        statusEl.textContent = `${bridgeLabel} • modo=${data.mode}`;
      } catch (error) {
        statusEl.textContent = `Sin conexión • ${String(error)}`;
      }
    }

    async function loadCases() {
      const res = await fetch(`${snowApi}/api/cases?limit=300`, { cache: 'no-store' });
      const cases = await res.json();
      if (!res.ok) throw new Error(cases?.detail || 'No fue posible cargar los casos');

      const openStates = new Set(['new', 'open', 'reopened', 'in_progress']);
      const metrics = {
        total: cases.length,
        open: cases.filter(item => openStates.has(item.state)).length,
        resolved: cases.filter(item => item.state === 'resolved').length,
        approval: cases.filter(item => item.state === 'awaiting_approval').length,
        manual: cases.filter(item => item.state === 'needs_manual_attention').length,
      };

      document.getElementById('k-total').textContent = String(metrics.total);
      document.getElementById('k-open').textContent = String(metrics.open);
      document.getElementById('k-resolved').textContent = String(metrics.resolved);
      document.getElementById('k-approval').textContent = String(metrics.approval);
      document.getElementById('k-manual').textContent = String(metrics.manual);

      if (!cases.length) {
        queueBody.innerHTML = `<tr><td colspan="6" class="muted">No hay casos en la cola.</td></tr>`;
        return;
      }

      queueBody.innerHTML = cases.map(item => {
        const shortDescription = item.short_description || '-';
        const priority = item.priority || '-';
        const assignmentGroup = item.assignment_group || '-';
        const updated = item.updated_at ? new Date(item.updated_at).toLocaleString() : '-';
        return `
          <tr>
            <td class="mono">${item.number}</td>
            <td>${shortDescription}</td>
            <td><span class="pill state-${item.state}">${item.state}</span></td>
            <td>${priority}</td>
            <td>${assignmentGroup}</td>
            <td>${updated}</td>
          </tr>
        `;
      }).join('');
    }

    async function seedQueue() {
      const summary = document.getElementById('run-summary');
      summary.textContent = 'Creando casos demo...';
      const res = await fetch(`${snowApi}/api/cases/seed`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) {
        summary.textContent = `Error creando casos demo: ${data?.detail || JSON.stringify(data)}`;
        return;
      }
      const created = Array.isArray(data) ? data.length : 0;
      summary.textContent = created > 0
        ? `Se crearon ${created} casos demo.`
        : 'La cola ya estaba sembrada. No se agregaron duplicados.';
      await loadCases();
    }

    document.getElementById('btn-seed').addEventListener('click', () => seedQueue().catch(console.error));
    document.getElementById('btn-refresh').addEventListener('click', () => Promise.all([loadCases(), loadStatus()]).catch(console.error));

    Promise.all([loadCases(), loadStatus()]).catch(console.error);
    setInterval(() => { loadCases().catch(() => undefined); loadStatus().catch(() => undefined); }, 8000);
  </script>
</body>
</html>
"""
    return (
        html.replace('__AFL_BACKEND_BASE_URL__', AFL_BACKEND_BASE_URL)
        .replace('__AFL_FRONTEND_BASE_URL__', AFL_FRONTEND_BASE_URL)
        .replace('__AFL_APP_NAME__', AFL_APP_NAME)
    )


def _serialize_case(case: ServiceNowCase) -> dict:
    return {
        'id': case.id,
        'number': case.number,
        'short_description': case.short_description,
        'description': case.description,
        'request_type': case.request_type,
        'params': case.params or {},
        'targets': case.targets or [],
        'priority': case.priority,
        'state': case.state,
        'assignment_group': case.assignment_group,
        'requested_by': case.requested_by,
        'automation_request_id': case.automation_request_id,
        'execution_id': case.execution_id,
        'resolution_notes': case.resolution_notes,
        'last_agent_run_at': case.last_agent_run_at,
        'source': case.source,
        'created_at': case.created_at,
        'updated_at': case.updated_at,
    }


@app.on_event('startup')
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_cmdb_hosts(
            db,
            settings.target_host_1,
            settings.target_host_1_name,
            settings.target_host_2,
            settings.target_host_2_name,
        )
        seed_demo_cases(db, [settings.target_host_1_name, settings.target_host_2_name])


@app.get('/health')
def health() -> dict:
    return {'status': 'ok', 'service': 'servicenow-sim', 'time': datetime.utcnow().isoformat()}


@app.get('/api/cases')
def api_list_cases(
    state: str | None = Query(default=None),
    assignment_group: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = list_cases(db, state=state, assignment_group=assignment_group, limit=limit)
    return [_serialize_case(row) for row in rows]


@app.post('/api/cases/seed')
def api_seed_cases(force: bool = Query(default=False), db: Session = Depends(get_db)) -> list[dict]:
    if force:
        rows = seed_demo_cases_force(db, [settings.target_host_1_name, settings.target_host_2_name])
    else:
        rows = seed_demo_cases(db, [settings.target_host_1_name, settings.target_host_2_name])
    return [_serialize_case(item) for item in rows]


@app.post('/api/cases')
def api_create_case(payload: CaseCreateInput, db: Session = Depends(get_db)) -> dict:
    row = create_case(
        db,
        short_description=payload.short_description,
        description=payload.description,
        request_type=payload.request_type,
        params=payload.params,
        targets=payload.targets,
        priority=payload.priority,
        assignment_group=payload.assignment_group,
        requested_by=payload.requested_by,
    )
    return _serialize_case(row)


@app.get('/api/cases/{case_number}')
def api_get_case(case_number: str, db: Session = Depends(get_db)) -> dict:
    row = get_case_by_number(db, case_number)
    if row is None:
        raise HTTPException(status_code=404, detail='Case not found')
    events = list_case_events(db, row.id)
    payload = _serialize_case(row)
    payload['events'] = [
        {
            'actor': event.actor,
            'event_type': event.event_type,
            'message': event.message,
            'payload': event.payload,
            'created_at': event.created_at,
        }
        for event in events
    ]
    return payload


@app.patch('/api/cases/{case_number}')
def api_patch_case(case_number: str, payload: CaseUpdateInput, db: Session = Depends(get_db)) -> dict:
    row = get_case_by_number(db, case_number)
    if row is None:
        raise HTTPException(status_code=404, detail='Case not found')

    if payload.state is not None:
        row.state = payload.state
    if payload.resolution_notes is not None:
        row.resolution_notes = payload.resolution_notes
    if payload.automation_request_id is not None:
        row.automation_request_id = payload.automation_request_id
    if payload.execution_id is not None:
        row.execution_id = payload.execution_id
    row.last_agent_run_at = datetime.utcnow()
    db.add(row)

    if payload.append_event:
        add_case_event(
            db,
            case=row,
            actor=str(payload.append_event.get('actor') or 'servicenow_mcp'),
            event_type=str(payload.append_event.get('event_type') or 'case_updated'),
            message=str(payload.append_event.get('message') or 'Case updated via API.'),
            payload=dict(payload.append_event.get('payload') or {}),
        )

    db.commit()
    db.refresh(row)
    return _serialize_case(row)


@app.get('/', response_class=HTMLResponse)
def portal() -> str:
    return _portal_html()


@app.get('/ui', response_class=HTMLResponse)
def portal_ui() -> str:
    return _portal_html()


@app.get('/api/automation/mcp/status')
def api_connector_status() -> dict:
    try:
        res = requests.get(
            f'{AFL_BACKEND_BASE_URL}/api/servicenow/mcp/status',
            timeout=10,
        )
        res.raise_for_status()
        return res.json()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f'AFL connector status unavailable: {exc}') from exc


@app.post('/api/automation/agent/run')
def api_dispatch_to_afl() -> dict:
    raise HTTPException(
        status_code=410,
        detail=(
            'El despacho directo desde ServiceNow Sim está deshabilitado por diseño. '
            'Ejecuta la automatización desde el Conector ServiceNow (/servicenow-connector).'
        ),
    )
