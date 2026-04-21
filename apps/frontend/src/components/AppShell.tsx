'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { PropsWithChildren } from 'react';

import { APP_NAME } from '@/lib/branding';

const primaryLinks = [
  { href: '/servicenow-connector', label: 'Conector ServiceNow' },
  { href: '/', label: 'Tablero' },
  { href: '/approvals', label: 'Aprobaciones' },
  { href: '/execution', label: 'Ejecución AWX' },
  { href: '/audit', label: 'Auditoría' },
];

export function AppShell({ children }: PropsWithChildren) {
  const pathname = usePathname();

  return (
    <div className="mx-auto flex min-h-screen max-w-[1400px] flex-col gap-5 p-4 md:flex-row md:p-8">
      <aside className="card h-fit w-full p-4 md:sticky md:top-8 md:w-64">
        <h1 className="text-xl font-black tracking-tight text-slate-900">{APP_NAME}</h1>
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
        </nav>
      </aside>

      <main className="w-full">{children}</main>
    </div>
  );
}
