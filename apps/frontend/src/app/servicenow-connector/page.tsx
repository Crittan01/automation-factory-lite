'use client';

import { useEffect, useMemo, useState } from 'react';

import { apiGet, apiPost } from '@/lib/api';
import { APP_NAME } from '@/lib/branding';
import type { ServiceNowAgentRun, ServiceNowCase, ServiceNowMcpStatus } from '@/lib/types';

const TABS = [
  { id: 'queue', label: 'Cola' },
  { id: 'catalog', label: 'Backlog de Catálogo' },
  { id: 'trace', label: 'Trazabilidad' },
] as const;

const STATE_COLORS: Record<string, string> = {
  resolved: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  awaiting_approval: 'bg-amber-100 text-amber-800 border-amber-200',
  needs_manual_attention: 'bg-rose-100 text-rose-800 border-rose-200',
  in_progress: 'bg-sky-100 text-sky-800 border-sky-200',
  new: 'bg-indigo-100 text-indigo-800 border-indigo-200',
  open: 'bg-indigo-100 text-indigo-800 border-indigo-200',
  reopened: 'bg-indigo-100 text-indigo-800 border-indigo-200',
};

function prettyState(state: string): string {
  return state.replaceAll('_', ' ');
}

export default function ServiceNowConnectorPage() {
  const [cases, setCases] = useState<ServiceNowCase[]>([]);
  const [status, setStatus] = useState<ServiceNowMcpStatus | null>(null);
  const [selectedCase, setSelectedCase] = useState<ServiceNowCase | null>(null);
  const [runResult, setRunResult] = useState<ServiceNowAgentRun | null>(null);
  const [tab, setTab] = useState<(typeof TABS)[number]['id']>('queue');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const loadAll = async () => {
    const [queue, mcp] = await Promise.all([
      apiGet<ServiceNowCase[]>('/api/servicenow-mcp/cases?limit=300'),
      apiGet<ServiceNowMcpStatus>('/api/servicenow/mcp/status'),
    ]);
    setCases(queue);
    setStatus(mcp);
    if (!selectedCase && queue[0]) {
      const detail = await apiGet<ServiceNowCase>(`/api/servicenow-mcp/cases/${queue[0].number}`);
      setSelectedCase(detail);
    }
  };

  const runAgentBatch = async () => {
    setLoading(true);
    setError('');
    try {
      const result = await apiPost<ServiceNowAgentRun>('/api/servicenow-mcp/agent/run?limit=20', {});
      setRunResult(result);
      await loadAll();
      if (selectedCase) {
        const detail = await apiGet<ServiceNowCase>(`/api/servicenow-mcp/cases/${selectedCase.number}`);
        setSelectedCase(detail);
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  const runSelectedCase = async () => {
    if (!selectedCase?.number) {
      setError('Selecciona un caso antes de ejecutar en modo individual.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const result = await apiPost<ServiceNowAgentRun>(
        `/api/servicenow-mcp/cases/${selectedCase.number}/process`,
        {},
      );
      setRunResult(result);
      await loadAll();
      const detail = await apiGet<ServiceNowCase>(`/api/servicenow-mcp/cases/${selectedCase.number}`);
      setSelectedCase(detail);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  const seedDemo = async () => {
    setLoading(true);
    setError('');
    try {
      const created = await apiPost<ServiceNowCase[]>('/api/servicenow-mcp/cases/seed', {});
      setRunResult({
        scanned: created.length,
        processed: 0,
        resolved: 0,
        awaiting_approval: 0,
        manual_attention: 0,
        errors: 0,
        case_numbers: created.map((item) => item.number),
      });
      await loadAll();
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  const selectCase = async (caseNumber: string) => {
    const detail = await apiGet<ServiceNowCase>(`/api/servicenow-mcp/cases/${caseNumber}`);
    setSelectedCase(detail);
  };

  useEffect(() => {
    loadAll().catch((err) => setError(String(err)));
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      loadAll().catch(() => undefined);
    }, 5000);
    return () => clearInterval(timer);
  }, [selectedCase]);

  const kpis = useMemo(() => {
    const open = cases.filter((item) => ['new', 'open', 'reopened', 'in_progress'].includes(item.state)).length;
    const resolved = cases.filter((item) => item.state === 'resolved').length;
    const approval = cases.filter((item) => item.state === 'awaiting_approval').length;
    const manual = cases.filter((item) => item.state === 'needs_manual_attention').length;
    return { open, resolved, approval, manual, total: cases.length };
  }, [cases]);

  const backlog = useMemo(() => {
    const openStates = new Set(['new', 'open', 'reopened', 'in_progress']);
    const groups: Record<string, number> = {};
    for (const item of cases) {
      if (!openStates.has(item.state)) continue;
      const key = item.request_type || 'sin_tipo';
      groups[key] = (groups[key] || 0) + 1;
    }
    return Object.entries(groups).sort((a, b) => b[1] - a[1]);
  }, [cases]);

  return (
    <div className="min-h-screen bg-[#eef2f7] font-sans text-[#1e2a44]">
      <header className="border-b border-[#1f2a44] bg-[#1f2a44] px-6 py-4 text-white">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between">
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em] text-slate-300">{APP_NAME}</p>
            <h1 className="text-2xl font-bold">Conector ServiceNow</h1>
          </div>
          <div className="text-right text-xs">
            <p>Modo MCP: {status?.mode ?? 'cargando...'}</p>
            <p className={status?.bridge_status === 'connected' ? 'text-emerald-300' : 'text-amber-300'}>
              Puente: {status?.bridge_status ?? '-'}
            </p>
            <p className={status?.external_service_reachable ? 'text-emerald-300' : 'text-rose-300'}>
              Servicio: {status?.external_service_reachable ? 'disponible' : 'no disponible'}
            </p>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-[1500px] gap-4 px-4 py-6 md:grid-cols-[260px_1fr]">
        <aside className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Navegación</p>
          <nav className="mt-3 grid gap-2">
            {TABS.map((item) => (
              <button
                key={item.id}
                onClick={() => setTab(item.id)}
                className={`rounded-lg px-3 py-2 text-left text-sm font-semibold ${
                  tab === item.id ? 'bg-[#0b5cab] text-white' : 'bg-slate-100 text-slate-700'
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>

          <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs">
            <p className="font-semibold text-slate-700">Conexión MCP</p>
            <p className="mt-1 text-slate-600">Paquete: {status?.mcp_package_installed ? 'instalado' : 'faltante'}</p>
            <p className="text-slate-600">Cmd: {status?.server_cmd ?? '-'}</p>
            <p className="text-slate-600">URL del servicio: {status?.external_service_url ?? '-'}</p>
            <p className="text-slate-600">Casos abiertos: {status?.queue_open_cases ?? 0}</p>
            {status?.external_service_url ? (
              <a
                href={status.external_service_url}
                target="_blank"
                rel="noreferrer"
                className="mt-2 inline-block font-semibold text-sky-700 underline"
              >
                Abrir portal ServiceNow
              </a>
            ) : null}
          </div>

          <div className="mt-4 grid gap-2">
            <button
              onClick={seedDemo}
              disabled={loading}
              className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              Sincronizar cola demo (sin duplicados)
            </button>
            <button
              onClick={runAgentBatch}
              disabled={loading}
              className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              Procesar lote (20 casos)
            </button>
            <button
              onClick={runSelectedCase}
              disabled={loading || !selectedCase}
              className="rounded-lg bg-amber-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              Procesar caso seleccionado
            </button>
            <p className="text-[11px] text-slate-500">
              Los botones ejecutan backend real: lote (`POST /api/servicenow-mcp/agent/run`) o individual
              (`POST /api/servicenow-mcp/cases/{'{number}'}/process`).
            </p>
          </div>
        </aside>

        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-5">
            <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs uppercase text-slate-500">Total</p>
              <p className="mt-1 text-3xl font-bold">{kpis.total}</p>
            </article>
            <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs uppercase text-slate-500">Abiertos</p>
              <p className="mt-1 text-3xl font-bold text-indigo-700">{kpis.open}</p>
            </article>
            <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs uppercase text-slate-500">Resueltos</p>
              <p className="mt-1 text-3xl font-bold text-emerald-700">{kpis.resolved}</p>
            </article>
            <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs uppercase text-slate-500">En aprobación</p>
              <p className="mt-1 text-3xl font-bold text-amber-700">{kpis.approval}</p>
            </article>
            <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs uppercase text-slate-500">Atención manual</p>
              <p className="mt-1 text-3xl font-bold text-rose-700">{kpis.manual}</p>
            </article>
          </div>

          {runResult ? (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
              {runResult.processed === 0
                ? `Resultado de sincronización: creados=${runResult.scanned}.`
                : `Ejecución del conector: escaneados=${runResult.scanned}, procesados=${runResult.processed}, resueltos=${runResult.resolved}, en_aprobación=${runResult.awaiting_approval}, manual=${runResult.manual_attention}`}
            </div>
          ) : null}
          {error ? <p className="text-sm text-rose-700">{error}</p> : null}

          {tab === 'catalog' ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="text-lg font-bold">Backlog de catálogo</h2>
              <p className="mt-1 text-xs text-slate-500">Casos pendientes agrupados por tipo de automatización.</p>
              <div className="mt-3 grid gap-3 md:grid-cols-3 lg:grid-cols-5">
                {backlog.length === 0 ? (
                  <p className="text-sm text-slate-500">No hay backlog abierto.</p>
                ) : (
                  backlog.map(([key, count]) => (
                    <article key={key} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                      <p className="text-xs uppercase tracking-wide text-slate-500">{key}</p>
                      <p className="mt-1 text-2xl font-bold text-slate-900">{count}</p>
                    </article>
                  ))
                )}
              </div>
            </div>
          ) : null}

          {tab === 'queue' || tab === 'trace' ? (
            <div className="grid gap-4 md:grid-cols-2">
              <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <h2 className="text-lg font-bold">Cola de casos</h2>
                <div className="mt-3 max-h-[520px] overflow-y-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-slate-500">
                        <th className="py-2">Caso</th>
                        <th className="py-2">Estado</th>
                        <th className="py-2">Tipo</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cases.map((item) => (
                        <tr
                          key={item.id}
                          className="cursor-pointer border-t border-slate-100 hover:bg-slate-50"
                          onClick={() => selectCase(item.number).catch((err) => setError(String(err)))}
                        >
                          <td className="py-2 font-mono text-xs">{item.number}</td>
                          <td className="py-2">
                            <span className={`rounded-full border px-2 py-1 text-xs ${STATE_COLORS[item.state] || 'bg-slate-100'}`}>
                              {prettyState(item.state)}
                            </span>
                          </td>
                          <td className="py-2">{item.request_type ?? 'solicitud_nl'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </article>

              <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <h2 className="text-lg font-bold">Detalle y trazabilidad</h2>
                {selectedCase ? (
                  <>
                    <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 p-3">
                      <p className="text-xs text-slate-500">{selectedCase.number}</p>
                      <p className="text-sm font-semibold">{selectedCase.short_description}</p>
                      <p className="mt-1 text-xs text-slate-600">Estado: {prettyState(selectedCase.state)}</p>
                      <p className="mt-1 text-xs text-slate-600">Solicitud de automatización: {selectedCase.automation_request_id ?? '-'}</p>
                      <p className="mt-1 text-xs text-slate-600">Ejecución: {selectedCase.execution_id ?? '-'}</p>
                      <p className="mt-2 text-xs text-slate-600">{selectedCase.resolution_notes ?? 'Sin notas de resolución aún.'}</p>
                    </div>

                    <div className="mt-3 max-h-[360px] space-y-2 overflow-y-auto">
                      {(selectedCase.events || []).map((event) => (
                        <article key={`${event.actor}-${event.event_type}-${event.created_at}`} className="rounded-lg border border-slate-200 p-2">
                          <p className="text-xs font-semibold text-slate-700">
                            {event.actor} · {event.event_type}
                          </p>
                          <p className="text-xs text-slate-600">{event.message}</p>
                          <p className="text-[11px] text-slate-400">{new Date(event.created_at).toLocaleString()}</p>
                        </article>
                      ))}
                    </div>
                  </>
                ) : (
                  <p className="mt-2 text-sm text-slate-500">Selecciona un caso de la cola.</p>
                )}
              </article>
            </div>
          ) : null}
        </section>
      </main>
    </div>
  );
}
