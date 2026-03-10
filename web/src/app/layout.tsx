import type { Metadata } from 'next';
import './globals.css';
import { Sidebar } from '@/components/Sidebar';
import { Providers } from '@/app/providers';

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
    <html lang="en" className="h-full bg-stone-100">
      <body className="h-full overflow-hidden bg-stone-100 text-stone-950">
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
