import type { Metadata } from 'next';
import './globals.css';
import '@xyflow/react/dist/style.css';
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
            <main className="flex-1 overflow-auto bg-[radial-gradient(circle_at_top_left,rgba(245,158,11,0.08),transparent_30%),linear-gradient(180deg,#f8f7f4_0%,#f4f3ef_100%)]">
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
