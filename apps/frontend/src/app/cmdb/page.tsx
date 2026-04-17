'use client';

import { useEffect, useState } from 'react';

import { AppShell } from '@/components/AppShell';
import { apiGet } from '@/lib/api';
import type { Host } from '@/lib/types';

export default function CmdbPage() {
  const [hosts, setHosts] = useState<Host[]>([]);
  const [selected, setSelected] = useState<Host | null>(null);
  const [environment, setEnvironment] = useState('');
  const [owner, setOwner] = useState('');
  const [criticality, setCriticality] = useState('');

  const load = async () => {
    const params = new URLSearchParams();
    if (environment) params.set('environment', environment);
    if (owner) params.set('owner', owner);
    if (criticality) params.set('criticality', criticality);
    const query = params.toString();
    const data = await apiGet<Host[]>(`/api/cmdb/hosts${query ? `?${query}` : ''}`);
    setHosts(data);
    setSelected(data[0] ?? null);
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <AppShell>
      <section className="card p-5">
        <h2 className="text-xl font-bold">CMDB Simulada</h2>
        <div className="mt-3 grid gap-2 md:grid-cols-4">
          <input
            placeholder="environment"
            value={environment}
            onChange={(event) => setEnvironment(event.target.value)}
            className="rounded-xl border border-slate-200 p-2 text-sm"
          />
          <input
            placeholder="owner"
            value={owner}
            onChange={(event) => setOwner(event.target.value)}
            className="rounded-xl border border-slate-200 p-2 text-sm"
          />
          <input
            placeholder="criticality"
            value={criticality}
            onChange={(event) => setCriticality(event.target.value)}
            className="rounded-xl border border-slate-200 p-2 text-sm"
          />
          <button onClick={load} className="rounded-xl bg-sky-500 px-4 py-2 text-sm font-semibold text-white">
            Filtrar
          </button>
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500">
                  <th>Hostname</th>
                  <th>IP</th>
                  <th>Entorno</th>
                </tr>
              </thead>
              <tbody>
                {hosts.map((host) => (
                  <tr
                    key={host.id}
                    className="cursor-pointer border-t border-slate-100 hover:bg-sky-50"
                    onClick={() => setSelected(host)}
                  >
                    <td className="py-2">{host.hostname}</td>
                    <td className="py-2">{host.ip}</td>
                    <td className="py-2">{host.environment}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
            <h3 className="text-sm font-bold">Detalle de host</h3>
            {selected ? (
              <pre className="mt-2 overflow-x-auto text-xs">{JSON.stringify(selected, null, 2)}</pre>
            ) : (
              <p className="mt-2 text-sm text-slate-500">Selecciona un host.</p>
            )}
          </div>
        </div>
      </section>
    </AppShell>
  );
}
