'use client';

import { useState } from 'react';

import { AppShell } from '@/components/AppShell';
import { apiPost } from '@/lib/api';
import type { IntakeResponse } from '@/lib/types';

const EXAMPLES = [
  'Crear usuario analista1 en ol9server1 sin sudo',
  'Instalar nginx en rocky9server1',
  'Instalar agente telegraf en ol9server1 y rocky9server1',
];

export default function IntakePage() {
  const [mode, setMode] = useState<'form' | 'chat'>('form');
  const [text, setText] = useState(EXAMPLES[0]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<IntakeResponse | null>(null);
  const [error, setError] = useState('');

  const submit = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await apiPost<IntakeResponse>('/api/requests', {
        text,
        requester: 'demo.user',
      });
      setResult(response);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <section className="card p-5">
        <h2 className="text-xl font-bold">Intake de Solicitud</h2>
        <p className="mt-2 text-sm text-slate-600">
          Ingresa solicitud en lenguaje natural. El Analista la convertirá en JSON estructurado y ejecutará el flujo
          multiagente.
        </p>

        <div className="mt-4 flex gap-2">
          <button
            className={`rounded-xl px-3 py-2 text-sm font-semibold ${
              mode === 'form' ? 'bg-sky-500 text-white' : 'bg-slate-100 text-slate-700'
            }`}
            onClick={() => setMode('form')}
          >
            Formulario
          </button>
          <button
            className={`rounded-xl px-3 py-2 text-sm font-semibold ${
              mode === 'chat' ? 'bg-sky-500 text-white' : 'bg-slate-100 text-slate-700'
            }`}
            onClick={() => setMode('chat')}
          >
            Chat
          </button>
        </div>

        <div className="mt-4 grid gap-2 md:grid-cols-3">
          {EXAMPLES.map((example) => (
            <button
              key={example}
              onClick={() => setText(example)}
              className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-left text-sm hover:border-sky-300"
            >
              {example}
            </button>
          ))}
        </div>

        <div className="mt-4">
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={mode === 'chat' ? 3 : 6}
            className="w-full rounded-2xl border border-slate-200 bg-white p-3 text-sm"
          />
        </div>

        <button
          onClick={submit}
          disabled={loading}
          className="mt-3 rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          {loading ? 'Procesando...' : 'Enviar solicitud'}
        </button>

        {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
      </section>

      <section className="card mt-4 p-5">
        <h3 className="text-lg font-bold">Salida del Analista (JSON estructurado)</h3>
        {result ? (
          <>
            <p className="mt-2 text-sm">
              Estado: <span className="badge bg-sky-100 text-sky-700">{result.status}</span>
            </p>
            {result.rejection_reason ? (
              <p className="mt-2 text-sm text-red-700">Motivo: {result.rejection_reason}</p>
            ) : null}
            {result.risk_reason ? <p className="mt-1 text-xs text-slate-600">Riesgo: {result.risk_reason}</p> : null}
            <pre className="mt-3 overflow-x-auto rounded-xl bg-slate-950 p-4 text-xs text-sky-100">
              {JSON.stringify(result.structured_spec, null, 2)}
            </pre>
            {result.warnings.length ? (
              <div className="mt-2">
                {result.warnings.map((warning) => (
                  <p key={warning} className="text-xs text-amber-700">
                    - {warning}
                  </p>
                ))}
              </div>
            ) : null}
          </>
        ) : (
          <p className="mt-2 text-sm text-slate-500">Sin salida todavía.</p>
        )}
      </section>
    </AppShell>
  );
}
