'use client';

import { useEffect, useState } from 'react';

import { AppShell } from '@/components/AppShell';
import { MetricCard } from '@/components/MetricCard';
import { apiGet } from '@/lib/api';
import type { Dashboard, IntakeResponse } from '@/lib/types';

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [requests, setRequests] = useState<IntakeResponse[]>([]);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    Promise.all([apiGet<Dashboard>('/api/dashboard'), apiGet<IntakeResponse[]>('/api/requests')])
      .then(([d, r]) => {
        setDashboard(d);
        setRequests(r.slice(0, 8));
      })
      .catch((err) => setError(String(err)));
  }, []);

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
