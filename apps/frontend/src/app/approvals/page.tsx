'use client';

import { useEffect, useState } from 'react';

import { AppShell } from '@/components/AppShell';
import { apiGet, apiPost } from '@/lib/api';
import type { ApprovalItem } from '@/lib/types';

export default function ApprovalsPage() {
  const [items, setItems] = useState<ApprovalItem[]>([]);
  const [error, setError] = useState('');

  const load = async () => {
    const data = await apiGet<ApprovalItem[]>('/api/approvals/pending');
    setItems(data);
  };

  const decide = async (requestId: string, decision: 'approve' | 'reject') => {
    const comment = decision === 'approve' ? 'Approved from UI' : 'Rejected from UI';
    try {
      await apiPost(`/api/approvals/${requestId}/decision`, {
        approver: 'ui.manager',
        decision,
        comment,
      });
      await load();
    } catch (err) {
      setError(String(err));
    }
  };

  useEffect(() => {
    load().catch((err) => setError(String(err)));
  }, []);

  return (
    <AppShell>
      <section className="card p-5">
        <h2 className="text-xl font-bold">Aprobaciones</h2>
        {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
        <div className="mt-4 space-y-3">
          {items.length === 0 ? <p className="text-sm text-slate-500">No hay solicitudes pendientes.</p> : null}
          {items.map((item) => (
            <article key={item.request_id} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs text-slate-500">{item.request_id}</p>
              <p className="mt-1 text-sm">{item.request_text}</p>
              <p className="mt-1 text-xs text-slate-600">Riesgo: {item.risk_level}</p>
              <p className="mt-1 text-xs text-slate-600">{item.risk_reason}</p>
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => decide(item.request_id, 'approve')}
                  className="rounded-xl bg-emerald-500 px-3 py-2 text-xs font-semibold text-white"
                >
                  Aprobar
                </button>
                <button
                  onClick={() => decide(item.request_id, 'reject')}
                  className="rounded-xl bg-rose-500 px-3 py-2 text-xs font-semibold text-white"
                >
                  Rechazar
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </AppShell>
  );
}
