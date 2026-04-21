'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';

import { AppShell } from '@/components/AppShell';
import { apiGet, apiPost } from '@/lib/api';
import type { ServiceNowAgentRun, ServiceNowCase } from '@/lib/types';

const QUICK_CASES = [
  {
    title: 'Crear Usuario',
    payload: {
      short_description: 'Crear usuario sn_auto_1 en ol9server1 sin sudo',
      request_type: 'create_user',
      params: { username: 'sn_auto_1' },
      targets: ['ol9server1'],
      priority: '3',
      requested_by: 'sn.portal',
    },
  },
  {
    title: 'Instalar Nginx',
    payload: {
      short_description: 'Instalar nginx en rocky9server1',
      request_type: 'install_service',
      params: { service_name: 'nginx' },
      targets: ['rocky9server1'],
      priority: '3',
      requested_by: 'sn.portal',
    },
  },
  {
    title: 'Agregar Clave SSH',
    payload: {
      short_description: 'Añadir clave SSH a usuario sn_auto_1 en ol9server1',
      request_type: 'add_ssh_key',
      params: {
        username: 'sn_auto_1',
        ssh_public_key: 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIdemoKey sn.portal',
      },
      targets: ['ol9server1'],
      priority: '2',
      requested_by: 'sn.portal',
    },
  },
  {
    title: 'Crear Carpeta',
    payload: {
      short_description: 'Crear carpeta /opt/automation_factory_lite/jobs/sn_portal en rocky9server1',
      request_type: 'create_directory',
      params: { directory_path: '/opt/automation_factory_lite/jobs/sn_portal' },
      targets: ['rocky9server1'],
      priority: '3',
      requested_by: 'sn.portal',
    },
  },
  {
    title: 'Diagnóstico Uptime',
    payload: {
      short_description: 'Obtener uptime en ol9server1',
      request_type: 'check_uptime',
      params: {},
      targets: ['ol9server1'],
      priority: '4',
      requested_by: 'sn.portal',
    },
  },
  {
    title: 'Caso Fuera de Catálogo',
    payload: {
      short_description: 'Abrir firewall para puerto 8443',
      request_type: 'unsupported',
      params: { port: 8443 },
      targets: ['ol9server1'],
      priority: '1',
      requested_by: 'sn.portal',
    },
  },
];

function stateBadge(state: string): string {
  if (state === 'resolved') return 'bg-emerald-100 text-emerald-700';
  if (state === 'awaiting_approval') return 'bg-amber-100 text-amber-700';
  if (state === 'needs_manual_attention') return 'bg-rose-100 text-rose-700';
  if (state === 'in_progress') return 'bg-sky-100 text-sky-700';
  return 'bg-slate-100 text-slate-700';
}

const REQUEST_TYPE_ORDER = [
  'create_user',
  'delete_user',
  'reset_password',
  'add_ssh_key',
  'create_directory',
  'install_service',
  'install_package',
  'restart_service',
  'manage_service',
  'install_agent',
  'deploy_template',
  'check_uptime',
  'check_patch_status',
  'check_connectivity',
  'unsupported',
];

export default function ServiceNowPage() {
  const [cases, setCases] = useState<ServiceNowCase[]>([]);
  const [selectedNumber, setSelectedNumber] = useState('');
  const [selected, setSelected] = useState<ServiceNowCase | null>(null);
  const [runResult, setRunResult] = useState<ServiceNowAgentRun | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const loadQueue = async () => {
    const rows = await apiGet<ServiceNowCase[]>('/api/servicenow/cases?limit=200');
    setCases(rows);
    if (!selectedNumber && rows[0]) {
      setSelectedNumber(rows[0].number);
    }
  };

  const loadDetail = async (caseNumber: string) => {
    if (!caseNumber) return;
    const detail = await apiGet<ServiceNowCase>(`/api/servicenow/cases/${caseNumber}`);
    setSelected(detail);
  };

  const runAgent = async () => {
    setBusy(true);
    setError('');
    try {
      const result = await apiPost<ServiceNowAgentRun>('/api/servicenow/agent/run?limit=15', {});
      setRunResult(result);
      await loadQueue();
      if (selectedNumber) {
        await loadDetail(selectedNumber);
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  const seedCases = async () => {
    setBusy(true);
    setError('');
    try {
      await apiPost('/api/servicenow/cases/seed', {});
      await loadQueue();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  const createQuickCase = async (payload: Record<string, unknown>) => {
    setBusy(true);
    setError('');
    try {
      await apiPost('/api/servicenow/cases', payload);
      await loadQueue();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    loadQueue().catch((err) => setError(String(err)));
  }, []);

  useEffect(() => {
    loadDetail(selectedNumber).catch((err) => setError(String(err)));
  }, [selectedNumber]);

  useEffect(() => {
    const timer = setInterval(() => {
      loadQueue().catch(() => undefined);
      if (selectedNumber) {
        loadDetail(selectedNumber).catch(() => undefined);
      }
    }, 5000);
    return () => clearInterval(timer);
  }, [selectedNumber]);

  const metrics = useMemo(() => {
    const total = cases.length;
    const open = cases.filter((item) => ['new', 'open', 'reopened', 'in_progress'].includes(item.state)).length;
    const resolved = cases.filter((item) => item.state === 'resolved').length;
    const manual = cases.filter((item) => item.state === 'needs_manual_attention').length;
    const approval = cases.filter((item) => item.state === 'awaiting_approval').length;
    return { total, open, resolved, manual, approval };
  }, [cases]);

  const backlogByCatalog = useMemo(() => {
    const openStates = new Set(['new', 'open', 'reopened', 'in_progress']);
    const grouped = new Map<string, number>();
    for (const type of REQUEST_TYPE_ORDER) {
      grouped.set(type, 0);
    }
    for (const item of cases) {
      if (!openStates.has(item.state)) continue;
      const key = item.request_type || 'unsupported';
      grouped.set(key, (grouped.get(key) || 0) + 1);
    }
    return REQUEST_TYPE_ORDER.map((key) => ({ key, count: grouped.get(key) || 0 }));
  }, [cases]);

  return (
    <AppShell>
      <section className="relative overflow-hidden rounded-3xl border border-sky-100 bg-white/90 p-6 shadow-sm">
        <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-sky-200/40 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-20 -left-16 h-52 w-52 rounded-full bg-emerald-200/40 blur-3xl" />
        <h2 className="text-2xl font-black text-slate-900">Cola ServiceNow (técnico/local)</h2>
        <p className="mt-2 max-w-3xl text-sm text-slate-600">
          Vista técnica local para diagnóstico. Para operación realista, usa el portal ServiceNow separado y
          el módulo Conector ServiceNow en la interfaz principal.
        </p>
        <Link href="/servicenow-connector" className="mt-2 inline-block text-xs font-semibold text-sky-700 underline">
          Abrir Conector ServiceNow
        </Link>

        <div className="mt-4 flex flex-wrap gap-2">
          <button
            onClick={seedCases}
            disabled={busy}
            className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            Sembrar Casos Demo
          </button>
          <button
            onClick={runAgent}
            disabled={busy}
            className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            Ejecutar Agente Ahora
          </button>
          <button
            onClick={() => loadQueue().catch((err) => setError(String(err)))}
            className="rounded-xl bg-sky-500 px-4 py-2 text-sm font-semibold text-white"
          >
            Refrescar Cola
          </button>
        </div>

        {runResult ? (
          <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800">
            Ejecución: escaneados={runResult.scanned}, procesados={runResult.processed}, resueltos={runResult.resolved},
            en_aprobación={runResult.awaiting_approval}, manual={runResult.manual_attention}, errores={runResult.errors}
          </div>
        ) : null}
        {error ? <p className="mt-3 text-sm text-rose-700">{error}</p> : null}
      </section>

      <section className="mt-4 grid gap-4 md:grid-cols-5">
        <article className="card p-4">
          <p className="text-xs uppercase text-slate-500">Total</p>
          <p className="mt-1 text-2xl font-black">{metrics.total}</p>
        </article>
        <article className="card p-4">
          <p className="text-xs uppercase text-slate-500">Abiertos</p>
          <p className="mt-1 text-2xl font-black text-sky-700">{metrics.open}</p>
        </article>
        <article className="card p-4">
          <p className="text-xs uppercase text-slate-500">Resueltos</p>
          <p className="mt-1 text-2xl font-black text-emerald-700">{metrics.resolved}</p>
        </article>
        <article className="card p-4">
          <p className="text-xs uppercase text-slate-500">Aprobación</p>
          <p className="mt-1 text-2xl font-black text-amber-700">{metrics.approval}</p>
        </article>
        <article className="card p-4">
          <p className="text-xs uppercase text-slate-500">Manual</p>
          <p className="mt-1 text-2xl font-black text-rose-700">{metrics.manual}</p>
        </article>
      </section>

      <section className="mt-4 card p-4">
        <h3 className="text-lg font-black">Catálogos por Atender</h3>
        <p className="mt-1 text-xs text-slate-500">Pendientes en cola abierta por tipo de automatización.</p>
        <div className="mt-3 grid gap-3 md:grid-cols-3 lg:grid-cols-6">
          {backlogByCatalog.map((item) => (
            <article key={item.key} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
              <p className="text-[11px] uppercase tracking-wide text-slate-500">{item.key}</p>
              <p className="mt-1 text-2xl font-black text-slate-900">{item.count}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="mt-4 grid gap-4 md:grid-cols-3">
        {QUICK_CASES.map((item) => (
          <article key={item.title} className="card p-4">
            <p className="text-sm font-bold text-slate-800">{item.title}</p>
            <p className="mt-1 text-xs text-slate-500">{item.payload.short_description as string}</p>
            <button
              onClick={() => createQuickCase(item.payload)}
              disabled={busy}
              className="mt-3 rounded-xl bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-sky-50"
            >
              Crear Caso
            </button>
          </article>
        ))}
      </section>

      <section className="mt-4 grid gap-4 md:grid-cols-2">
        <article className="card overflow-x-auto p-4">
          <h3 className="text-lg font-black">Casos Pendientes y Históricos</h3>
          <table className="mt-3 w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500">
                <th>Caso</th>
                <th>Estado</th>
                <th>Tipo</th>
                <th>Prioridad</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((item) => (
                <tr
                  key={item.id}
                  onClick={() => setSelectedNumber(item.number)}
                  className="cursor-pointer border-t border-slate-100 hover:bg-sky-50"
                >
                  <td className="py-2 font-mono text-xs">{item.number}</td>
                  <td className="py-2">
                    <span className={`badge ${stateBadge(item.state)}`}>{item.state}</span>
                  </td>
                  <td className="py-2">{item.request_type ?? 'solicitud_nl'}</td>
                  <td className="py-2">{item.priority}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <article className="card p-4">
          <h3 className="text-lg font-black">Detalle de Caso</h3>
          {selected ? (
            <>
              <div className="mt-2 rounded-xl border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs text-slate-500">{selected.number}</p>
                <p className="text-sm font-semibold">{selected.short_description}</p>
                <p className="mt-1 text-xs text-slate-600">Estado: {selected.state}</p>
                <p className="mt-1 text-xs text-slate-600">Request ID: {selected.automation_request_id ?? '-'}</p>
                <p className="mt-1 text-xs text-slate-600">ID de ejecución: {selected.execution_id ?? '-'}</p>
                <p className="mt-2 text-xs text-slate-600">{selected.resolution_notes ?? 'Sin notas de resolución.'}</p>
              </div>

              <div className="mt-3 space-y-2">
                {(selected.events || []).map((event) => (
                  <article key={`${event.actor}-${event.created_at}-${event.event_type}`} className="rounded-xl border border-slate-200 p-2">
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
            <p className="mt-2 text-sm text-slate-500">Selecciona un caso para ver su trazabilidad.</p>
          )}
        </article>
      </section>
    </AppShell>
  );
}
