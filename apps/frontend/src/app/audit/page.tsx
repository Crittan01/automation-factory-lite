'use client';

import { useEffect, useMemo, useState } from 'react';

import { AppShell } from '@/components/AppShell';
import { apiGet } from '@/lib/api';
import type { AuditEntry } from '@/lib/types';

export default function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    apiGet<AuditEntry[]>('/api/audit').then(setEntries);
  }, []);

  const filtered = useMemo(() => {
    const needle = filter.toLowerCase();
    return entries.filter((entry) => entry.event_type.toLowerCase().includes(needle));
  }, [entries, filter]);

  return (
    <AppShell>
      <section className="card p-5">
        <h2 className="text-xl font-bold">Auditoría</h2>
        <input
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          placeholder="Filtrar por event_type"
          className="mt-3 rounded-xl border border-slate-200 p-2 text-sm"
        />
        <div className="mt-4 space-y-3">
          {filtered.map((entry) => (
            <article key={entry.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs font-semibold text-slate-700">{entry.event_type}</p>
              <p className="text-sm text-slate-600">{entry.message}</p>
              <p className="text-xs text-slate-400">{new Date(entry.created_at).toLocaleString()}</p>
              <pre className="mt-2 overflow-x-auto text-xs text-slate-700">{JSON.stringify(entry.payload, null, 2)}</pre>
            </article>
          ))}
        </div>
      </section>
    </AppShell>
  );
}
