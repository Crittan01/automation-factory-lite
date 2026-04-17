'use client';

import { useEffect, useState } from 'react';

import { AppShell } from '@/components/AppShell';
import { apiGet } from '@/lib/api';
import type { IntakeResponse, TimelineEvent } from '@/lib/types';

export default function TimelinePage() {
  const [requests, setRequests] = useState<IntakeResponse[]>([]);
  const [requestId, setRequestId] = useState('');
  const [events, setEvents] = useState<TimelineEvent[]>([]);

  const loadRequests = async () => {
    const list = await apiGet<IntakeResponse[]>('/api/requests');
    setRequests(list);
    if (list[0]) {
      setRequestId(list[0].id);
    }
  };

  const loadTimeline = async (id: string) => {
    if (!id) return;
    const list = await apiGet<TimelineEvent[]>(`/api/requests/${id}/timeline`);
    setEvents(list);
  };

  useEffect(() => {
    loadRequests();
  }, []);

  useEffect(() => {
    loadTimeline(requestId);
  }, [requestId]);

  return (
    <AppShell>
      <section className="card p-5">
        <h2 className="text-xl font-bold">Timeline Multiagente</h2>
        <select
          value={requestId}
          onChange={(event) => setRequestId(event.target.value)}
          className="mt-3 rounded-xl border border-slate-200 bg-white p-2 text-sm"
        >
          {requests.map((request) => (
            <option key={request.id} value={request.id}>
              {request.id.slice(0, 8)} - {request.status}
            </option>
          ))}
        </select>

        <div className="mt-4 space-y-3">
          {events.map((event) => (
            <article key={`${event.actor}-${event.step}-${event.created_at}`} className="card p-4">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="badge bg-sky-100 text-sky-700">{event.actor}</span>
                <span className="font-semibold">{event.step}</span>
                <span className="text-slate-500">{event.status}</span>
                <span className="text-xs text-slate-400">{new Date(event.created_at).toLocaleString()}</span>
              </div>
              <pre className="mt-2 overflow-x-auto rounded-xl bg-slate-950 p-3 text-xs text-sky-100">
                {JSON.stringify(event.payload, null, 2)}
              </pre>
            </article>
          ))}
        </div>
      </section>
    </AppShell>
  );
}
