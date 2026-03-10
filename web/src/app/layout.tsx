import type { Metadata } from 'next';
import { IBM_Plex_Mono, Space_Grotesk } from 'next/font/google';
import './globals.css';
import { Sidebar } from '@/components/Sidebar';
import { Providers } from '@/app/providers';

const grotesk = Space_Grotesk({
  subsets: ['latin'],
  variable: '--font-space-grotesk',
});

const mono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-ibm-plex-mono',
});

export const metadata: Metadata = {
  title: 'Pipeliner Workflow Studio',
  description: 'Developer console for Pipeliner workflows.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" className="h-full bg-stone-100">
      <body className={`${grotesk.variable} ${mono.variable} h-full overflow-hidden bg-stone-100 text-stone-950`}>
        <Providers>
          <div className="flex h-full overflow-hidden">
            <Sidebar />
            <main className="flex-1 overflow-auto">
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
