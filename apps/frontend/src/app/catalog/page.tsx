'use client';

import { useEffect, useState } from 'react';

import { AppShell } from '@/components/AppShell';
import { apiGet } from '@/lib/api';
import type { CatalogAutomation } from '@/lib/types';

export default function CatalogPage() {
  const [items, setItems] = useState<CatalogAutomation[]>([]);
  const [selected, setSelected] = useState<CatalogAutomation | null>(null);

  useEffect(() => {
    apiGet<CatalogAutomation[]>('/api/catalog/automations').then((data) => {
      setItems(data);
      setSelected(data[0] ?? null);
    });
  }, []);

  return (
    <AppShell>
      <section className="card p-5">
        <h2 className="text-xl font-bold">Catálogo de Automatizaciones</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500">
                  <th>Nombre</th>
                  <th>Tipo</th>
                  <th>Riesgo</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.id}
                    className="cursor-pointer border-t border-slate-100 hover:bg-sky-50"
                    onClick={() => setSelected(item)}
                  >
                    <td className="py-2">{item.name}</td>
                    <td className="py-2">{item.request_type}</td>
                    <td className="py-2">{item.risk_level}</td>
                    <td className="py-2">{item.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
            <h3 className="text-sm font-bold">Detalle de automatización</h3>
            {selected ? (
              <pre className="mt-2 overflow-x-auto text-xs">{JSON.stringify(selected, null, 2)}</pre>
            ) : (
              <p className="mt-2 text-sm text-slate-500">No hay automatizaciones publicadas todavía.</p>
            )}
          </div>
        </div>
      </section>
    </AppShell>
  );
}
