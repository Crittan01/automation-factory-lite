'use client';

import { FormEvent, useEffect, useState } from 'react';

import { AppShell } from '@/components/AppShell';
import { MetricCard } from '@/components/MetricCard';
import { apiGet } from '@/lib/api';
import type { AgenticStack, Dashboard, IntakeResponse } from '@/lib/types';

const DEFAULT_RAG_QUERY = 'aprobaciones awx mcp';

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [requests, setRequests] = useState<IntakeResponse[]>([]);
  const [agenticStack, setAgenticStack] = useState<AgenticStack | null>(null);
  const [ragQuery, setRagQuery] = useState<string>(DEFAULT_RAG_QUERY);
  const [stackLoading, setStackLoading] = useState<boolean>(false);
  const [stackError, setStackError] = useState<string>('');
  const [error, setError] = useState<string>('');

  useEffect(() => {
    Promise.all([
      apiGet<Dashboard>('/api/dashboard'),
      apiGet<IntakeResponse[]>('/api/requests'),
      apiGet<AgenticStack>(`/api/agentic/stack?query=${encodeURIComponent(DEFAULT_RAG_QUERY)}&limit=3`),
    ])
      .then(([d, r, stack]) => {
        setDashboard(d);
        setRequests(r.slice(0, 8));
        setAgenticStack(stack);
      })
      .catch((err) => setError(String(err)));
  }, []);

  const techEnabledClass = (enabled: boolean): string =>
    enabled ? 'badge bg-emerald-100 text-emerald-700' : 'badge bg-slate-100 text-slate-600';

  const boolLabel = (enabled: boolean): string => (enabled ? 'Activo' : 'Inactivo');

  const handleRagSearch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedQuery = ragQuery.trim();
    if (normalizedQuery.length < 3) {
      setStackError('La consulta RAG requiere al menos 3 caracteres.');
      return;
    }

    setStackLoading(true);
    setStackError('');
    try {
      const stack = await apiGet<AgenticStack>(`/api/agentic/stack?query=${encodeURIComponent(normalizedQuery)}&limit=5`);
      setAgenticStack(stack);
    } catch (err) {
      setStackError(String(err));
    } finally {
      setStackLoading(false);
    }
  };

  return (
    <AppShell>
      <section className="grid gap-4 md:grid-cols-4">
        <MetricCard title="Solicitudes totales" value={dashboard?.total_requests ?? '-'} />
        <MetricCard title="Automatizaciones reutilizadas" value={dashboard?.automations_reused ?? '-'} />
        <MetricCard title="Automatizaciones nuevas" value={dashboard?.automations_generated ?? '-'} />
        <MetricCard title="Acciones con aprobación" value={dashboard?.actions_with_approval ?? '-'} />
      </section>

      <section className="mt-4 grid gap-4 md:grid-cols-3">
        <MetricCard
          title="Ticket -> publicación"
          value={`${dashboard?.mean_ticket_to_publish_seconds ?? 0}s`}
          subtitle="promedio"
        />
        <MetricCard
          title="Ticket -> ejecución"
          value={`${dashboard?.mean_ticket_to_execution_seconds ?? 0}s`}
          subtitle="promedio"
        />
        <MetricCard title="Éxito / Fallo" value={`${dashboard?.success ?? 0} / ${dashboard?.failed ?? 0}`} />
      </section>

      <section className="mt-4 grid gap-4 md:grid-cols-3">
        <MetricCard title="SNOW abiertos" value={dashboard?.servicenow_open_cases ?? 0} />
        <MetricCard title="SNOW resueltos" value={dashboard?.servicenow_resolved_cases ?? 0} />
        <MetricCard title="SNOW manual" value={dashboard?.servicenow_manual_cases ?? 0} />
      </section>

      <section className="card mt-6 p-5">
        <div className="flex flex-col gap-1">
          <h2 className="text-lg font-bold">Capacidades Agentic (Fase 1)</h2>
          <p className="text-sm text-slate-600">
            Visibilidad de tecnologías activas en esta demo: LLM, RAG, MCP, AWX y LangGraph.
          </p>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-5">
          <article className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-semibold uppercase text-slate-500">LLM</p>
            <p className="mt-2 text-sm font-semibold text-slate-800">
              {agenticStack?.technologies.llm.vendor ?? 'OpenAI'} / {agenticStack?.technologies.llm.model ?? '-'}
            </p>
            <span className={techEnabledClass(agenticStack?.technologies.llm.enabled ?? false)}>
              {boolLabel(agenticStack?.technologies.llm.enabled ?? false)}
            </span>
          </article>

          <article className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-semibold uppercase text-slate-500">RAG</p>
            <p className="mt-2 text-sm font-semibold text-slate-800">
              Docs indexados: {agenticStack?.technologies.rag.documents_indexed ?? 0}
            </p>
            <p className="text-xs text-slate-600">
              Modo: {agenticStack?.technologies.rag.retrieval_mode ?? '-'} / Vector: {agenticStack?.technologies.rag.vector_store ?? '-'}
            </p>
          </article>

          <article className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-semibold uppercase text-slate-500">MCP</p>
            <p className="mt-2 text-sm font-semibold text-slate-800">Modo: {agenticStack?.technologies.mcp.mode ?? '-'}</p>
            <span className={techEnabledClass(agenticStack?.technologies.mcp.enabled ?? false)}>
              {agenticStack?.technologies.mcp.bridge_status ?? 'sin estado'}
            </span>
          </article>

          <article className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-semibold uppercase text-slate-500">AWX</p>
            <p className="mt-2 text-sm font-semibold text-slate-800">Modo: {agenticStack?.technologies.awx.mode ?? '-'}</p>
            <p className="text-xs text-slate-600">{agenticStack?.technologies.awx.url ?? 'Sin URL configurada'}</p>
          </article>

          <article className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-semibold uppercase text-slate-500">LangGraph</p>
            <p className="mt-2 text-sm font-semibold text-slate-800">
              Instalado: {boolLabel(agenticStack?.technologies.langgraph.installed ?? false)}
            </p>
            <span className={techEnabledClass(agenticStack?.technologies.langgraph.active ?? false)}>
              {boolLabel(agenticStack?.technologies.langgraph.active ?? false)}
            </span>
          </article>
        </div>

        <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-bold text-slate-800">Consulta RAG de evidencia</h3>
          <form onSubmit={handleRagSearch} className="mt-3 flex flex-col gap-2 md:flex-row">
            <input
              value={ragQuery}
              onChange={(event) => setRagQuery(event.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
              placeholder="Ejemplo: aprobaciones awx mcp"
            />
            <button
              type="submit"
              disabled={stackLoading}
              className="rounded-xl bg-sky-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              {stackLoading ? 'Consultando...' : 'Consultar'}
            </button>
          </form>

          {stackError ? <p className="mt-3 text-sm text-red-600">{stackError}</p> : null}

          <div className="mt-4 grid gap-3">
            {(agenticStack?.rag_hits ?? []).map((hit) => {
              const fileName = hit.path.split('/').at(-1) ?? hit.path;
              return (
                <article key={`${hit.path}-${hit.score}`} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-mono text-xs font-semibold text-slate-800">{fileName}</p>
                    <span className="badge bg-sky-100 text-sky-700">score {hit.score}</span>
                  </div>
                  <p className="mt-2 text-sm text-slate-700">{hit.snippet}</p>
                  <p className="mt-2 font-mono text-[11px] text-slate-500">{hit.path}</p>
                </article>
              );
            })}
          </div>

          {agenticStack && (agenticStack.rag_hits ?? []).length === 0 ? (
            <p className="mt-3 text-sm text-slate-500">Sin resultados para la consulta actual.</p>
          ) : null}
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {(agenticStack?.agents ?? []).map((agent) => (
            <span key={agent} className="badge bg-indigo-100 text-indigo-700">
              {agent}
            </span>
          ))}
        </div>
      </section>

      <section className="card mt-6 p-5">
        <h2 className="text-lg font-bold">Últimas solicitudes</h2>
        {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500">
                <th className="py-2">ID</th>
                <th className="py-2">Ticket</th>
                <th className="py-2">Estado</th>
                <th className="py-2">Riesgo</th>
                <th className="py-2">Solicitud</th>
              </tr>
            </thead>
            <tbody>
              {requests.map((request) => (
                <tr key={request.id} className="border-t border-slate-100">
                  <td className="py-2 font-mono text-xs">{request.id.slice(0, 8)}</td>
                  <td className="py-2 font-mono text-xs">{request.ticket_id}</td>
                  <td className="py-2">{request.status}</td>
                  <td className="py-2">{request.risk_level ?? '-'}</td>
                  <td className="py-2">{String(request.structured_spec?.raw_text ?? '').slice(0, 90)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}
