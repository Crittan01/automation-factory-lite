import type { Metadata } from 'next';

import { APP_NAME } from '@/lib/branding';

import './globals.css';

export const metadata: Metadata = {
  title: APP_NAME,
  description: 'Fábrica segura de automatización de bajo riesgo',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
