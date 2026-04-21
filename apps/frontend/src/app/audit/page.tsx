'use client';

import { useEffect, useMemo, useState } from 'react';

import { AppShell } from '@/components/AppShell';
import { apiGet } from '@/lib/api';
import type { AuditEntry } from '@/lib/types';

export default function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [ticketId, setTicketId] = useState('');
  const [eventFilter, setEventFilter] = useState('');

  const load = async () => {
    const params = new URLSearchParams();
    if (ticketId.trim()) {
      params.set('ticket_id', ticketId.trim());
    }
    const query = params.toString();
    const data = await apiGet<AuditEntry[]>(`/api/audit${query ? `?${query}` : ''}`);
    setEntries(data);
  };

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    const needle = eventFilter.toLowerCase().trim();
    if (!needle) {
      return entries;
    }
    return entries.filter((entry) => entry.event_type.toLowerCase().includes(needle));
  }, [entries, eventFilter]);

  return (
    <AppShell>
      <section className="card p-5">
        <h2 className="text-xl font-bold">Auditoría</h2>
        <div className="mt-3 grid gap-2 md:grid-cols-3">
          <input
            value={ticketId}
            onChange={(event) => setTicketId(event.target.value)}
            placeholder="Filtrar por ticket_id"
            className="rounded-xl border border-slate-200 p-2 text-sm"
          />
          <input
            value={eventFilter}
            onChange={(event) => setEventFilter(event.target.value)}
            placeholder="Filtrar por tipo de evento"
            className="rounded-xl border border-slate-200 p-2 text-sm"
          />
          <button onClick={load} className="rounded-xl bg-sky-500 px-4 py-2 text-sm font-semibold text-white">
            Buscar
          </button>
        </div>
        <div className="mt-4 space-y-3">
          {filtered.map((entry) => (
            <article key={entry.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs font-semibold text-slate-700">{entry.event_type}</p>
              <p className="text-xs text-slate-500">Ticket: {entry.ticket_id ?? '-'}</p>
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
