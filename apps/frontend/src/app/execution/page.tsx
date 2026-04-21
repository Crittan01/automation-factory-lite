'use client';

import { useEffect, useMemo, useState } from 'react';

import { AppShell } from '@/components/AppShell';
import { apiGet } from '@/lib/api';
import type { Execution } from '@/lib/types';

export default function ExecutionPage() {
  const [items, setItems] = useState<Execution[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ticketFilter, setTicketFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('todos');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<string | null>(null);

  const loadExecutions = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<Execution[]>('/api/executions');
      setItems(data);
      setLastRefresh(new Date().toISOString());
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'No fue posible cargar ejecuciones AWX.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadExecutions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!autoRefresh) {
      return;
    }
    const timer = window.setInterval(() => {
      loadExecutions();
    }, 15000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh]);

  const filtered = useMemo(() => {
    const byTicket = ticketFilter.trim().toLowerCase();
    return items.filter((item) => {
      const matchesTicket = byTicket === '' || String(item.ticket_id || '').toLowerCase().includes(byTicket);
      const matchesStatus = statusFilter === 'todos' || String(item.status || '').toLowerCase() === statusFilter;
      return matchesTicket && matchesStatus;
    });
  }, [items, statusFilter, ticketFilter]);

  const kpis = useMemo(() => {
    const successSet = new Set(['successful', 'launched', 'executed']);
    const failedSet = new Set(['failed', 'error', 'canceled']);
    const summary = { total: filtered.length, success: 0, failed: 0, other: 0, real: 0 };
    for (const item of filtered) {
      const status = String(item.status || '').toLowerCase();
      if (successSet.has(status)) {
        summary.success += 1;
      } else if (failedSet.has(status)) {
        summary.failed += 1;
      } else {
        summary.other += 1;
      }
      if (String(item.awx_mode || '').toLowerCase() === 'real') {
        summary.real += 1;
      }
    }
    return summary;
  }, [filtered]);

  const statuses = useMemo(() => {
    const values = new Set<string>();
    for (const item of items) {
      const value = String(item.status || '').toLowerCase().trim();
      if (value) {
        values.add(value);
      }
    }
    return ['todos', ...Array.from(values).sort()];
  }, [items]);

  const statusPillClass = (status: string) => {
    const value = status.toLowerCase();
    if (value === 'failed' || value === 'error' || value === 'canceled') {
      return 'bg-rose-100 text-rose-700';
    }
    if (value === 'successful' || value === 'executed') {
      return 'bg-emerald-100 text-emerald-700';
    }
    if (value === 'launched' || value === 'running') {
      return 'bg-sky-100 text-sky-700';
    }
    return 'bg-slate-100 text-slate-700';
  };

  return (
    <AppShell>
      <section className="space-y-4">
        <article className="card p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-bold">Ejecución AWX</h2>
              <p className="mt-1 text-sm text-slate-500">
                Monitorea jobs, filtra por ticket/estado y revisa detalle técnico por ejecución.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={loadExecutions}
                disabled={loading}
                className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
              >
                {loading ? 'Actualizando...' : 'Actualizar ahora'}
              </button>
              <label className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">
                <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
                Auto-refresh 15s
              </label>
            </div>
          </div>
          {lastRefresh ? (
            <p className="mt-2 text-xs text-slate-500">
              Última actualización: {new Date(lastRefresh).toLocaleString('es-CO')}
            </p>
          ) : null}
          {error ? <p className="mt-3 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p> : null}
        </article>

        <div className="grid gap-3 md:grid-cols-5">
          <article className="card p-4">
            <p className="text-xs uppercase text-slate-500">Total filtrado</p>
            <p className="mt-1 text-3xl font-bold">{kpis.total}</p>
          </article>
          <article className="card p-4">
            <p className="text-xs uppercase text-slate-500">Exitosos</p>
            <p className="mt-1 text-3xl font-bold text-emerald-700">{kpis.success}</p>
          </article>
          <article className="card p-4">
            <p className="text-xs uppercase text-slate-500">Fallidos</p>
            <p className="mt-1 text-3xl font-bold text-rose-700">{kpis.failed}</p>
          </article>
          <article className="card p-4">
            <p className="text-xs uppercase text-slate-500">Otros estados</p>
            <p className="mt-1 text-3xl font-bold text-amber-700">{kpis.other}</p>
          </article>
          <article className="card p-4">
            <p className="text-xs uppercase text-slate-500">Modo real</p>
            <p className="mt-1 text-3xl font-bold text-sky-700">{kpis.real}</p>
          </article>
        </div>

        <article className="card p-4">
          <div className="grid gap-3 md:grid-cols-3">
            <div>
              <label className="text-xs font-semibold uppercase text-slate-500">Buscar ticket</label>
              <input
                value={ticketFilter}
                onChange={(e) => setTicketFilter(e.target.value)}
                placeholder="INC000011 o AFL-..."
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase text-slate-500">Estado</label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                {statuses.map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={() => {
                  setTicketFilter('');
                  setStatusFilter('todos');
                }}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700"
              >
                Limpiar filtros
              </button>
            </div>
          </div>
        </article>

        <div className="card overflow-x-auto p-4">
          <table className="w-full min-w-[980px] text-sm">
            <thead>
              <tr className="text-left text-slate-500">
                <th className="py-2">Ticket</th>
                <th className="py-2">Template</th>
                <th className="py-2">Hosts</th>
                <th className="py-2">Modo</th>
                <th className="py-2">Job</th>
                <th className="py-2">Estado</th>
                <th className="py-2">Inicio</th>
                <th className="py-2">Detalle</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr key={item.id} className="border-t border-slate-100 align-top">
                  <td className="py-3 font-mono text-xs">{item.ticket_id ?? '-'}</td>
                  <td className="py-3">{item.template_name}</td>
                  <td className="py-3">{item.hosts.join(', ')}</td>
                  <td className="py-3">
                    <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold">
                      {item.awx_mode}
                    </span>
                  </td>
                  <td className="py-3 font-mono text-xs">{item.job_id}</td>
                  <td className="py-3">
                    <span className={`rounded-full px-2 py-1 text-xs font-semibold ${statusPillClass(item.status)}`}>
                      {item.status}
                    </span>
                  </td>
                  <td className="py-3 text-xs text-slate-600">
                    {item.started_at ? new Date(item.started_at).toLocaleString('es-CO') : '-'}
                  </td>
                  <td className="py-3">
                    <details>
                      <summary className="cursor-pointer text-xs font-semibold text-sky-700">Ver salida</summary>
                      <div className="mt-2 space-y-2 rounded-lg bg-slate-50 p-2">
                        <p className="text-xs text-slate-700 whitespace-pre-wrap">{item.output_summary || '-'}</p>
                        <pre className="max-h-48 overflow-auto rounded bg-slate-900 p-2 text-[11px] text-slate-100">
                          {JSON.stringify(item.extra_vars || {}, null, 2)}
                        </pre>
                      </div>
                    </details>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!loading && filtered.length === 0 ? (
            <p className="py-4 text-sm text-slate-500">No hay ejecuciones que coincidan con los filtros actuales.</p>
          ) : null}
        </div>
      </section>
    </AppShell>
  );
}
