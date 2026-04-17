'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { PropsWithChildren, useMemo, useState } from 'react';

const primaryLinks = [
  { href: '/servicenow-connector', label: 'ServiceNow Connector' },
  { href: '/', label: 'Dashboard' },
  { href: '/approvals', label: 'Aprobaciones' },
  { href: '/execution', label: 'Ejecución AWX' },
  { href: '/audit', label: 'Auditoría' },
];

const technicalLinks = [
  { href: '/servicenow', label: 'ServiceNow Ops (Tech)' },
  { href: '/intake', label: 'Intake' },
  { href: '/cmdb', label: 'CMDB' },
  { href: '/catalog', label: 'Catálogo' },
  { href: '/timeline', label: 'Timeline' },
];

export function AppShell({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const [showTechnical, setShowTechnical] = useState(false);
  const isTechnicalRoute = useMemo(() => technicalLinks.some((link) => link.href === pathname), [pathname]);
  const shouldShowTechnical = showTechnical || isTechnicalRoute;

  return (
    <div className="mx-auto flex min-h-screen max-w-[1400px] flex-col gap-5 p-4 md:flex-row md:p-8">
      <aside className="card h-fit w-full p-4 md:sticky md:top-8 md:w-64">
        <h1 className="text-xl font-black tracking-tight text-slate-900">Automation Factory Lite</h1>
        <p className="mt-2 text-sm text-slate-600">Fábrica segura de automatización reutilizable</p>

        <nav className="mt-4 grid gap-2">
          {primaryLinks.map((link) => {
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
                  active ? 'bg-sky-500 text-white' : 'bg-slate-100 text-slate-700 hover:bg-sky-50'
                }`}
              >
                {link.label}
              </Link>
            );
          })}

          <button
            onClick={() => setShowTechnical((current) => !current)}
            className="mt-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-600"
          >
            {shouldShowTechnical ? 'Ocultar Módulos Técnicos' : 'Mostrar Módulos Técnicos'}
          </button>

          {shouldShowTechnical
            ? technicalLinks.map((link) => {
                const active = pathname === link.href;
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
                      active ? 'bg-sky-500 text-white' : 'bg-slate-100 text-slate-700 hover:bg-sky-50'
                    }`}
                  >
                    {link.label}
                  </Link>
                );
              })
            : null}
        </nav>
      </aside>

      <main className="w-full">{children}</main>
    </div>
  );
}
