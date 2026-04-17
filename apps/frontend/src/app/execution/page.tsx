'use client';

import { useEffect, useState } from 'react';

import { AppShell } from '@/components/AppShell';
import { apiGet } from '@/lib/api';
import type { Execution } from '@/lib/types';

export default function ExecutionPage() {
  const [items, setItems] = useState<Execution[]>([]);

  useEffect(() => {
    apiGet<Execution[]>('/api/executions').then(setItems);
  }, []);

  return (
    <AppShell>
      <section className="card p-5">
        <h2 className="text-xl font-bold">Ejecución AWX</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500">
                <th>Ticket</th>
                <th>Template</th>
                <th>Hosts</th>
                <th>Modo</th>
                <th>Job</th>
                <th>Estado</th>
                <th>Resumen</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-t border-slate-100">
                  <td className="py-2 font-mono text-xs">{item.ticket_id ?? '-'}</td>
                  <td className="py-2">{item.template_name}</td>
                  <td className="py-2">{item.hosts.join(', ')}</td>
                  <td className="py-2">{item.awx_mode}</td>
                  <td className="py-2 font-mono text-xs">{item.job_id}</td>
                  <td className="py-2">{item.status}</td>
                  <td className="py-2">{item.output_summary}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}
