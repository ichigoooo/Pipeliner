'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useTranslations } from 'next-intl';
import { StudioPage, StudioPageHeader } from '@/components/ui/StudioPage';

export default function DashboardPage() {
  const t = useTranslations('dashboard');

  const workflowsQuery = useQuery({ queryKey: ['dashboard-workflows'], queryFn: api.listWorkflows });
  const runsQuery = useQuery({
    queryKey: ['dashboard-runs'],
    queryFn: api.listRuns,
    refetchInterval: 8_000,
  });
  const attentionQuery = useQuery({
    queryKey: ['dashboard-attention'],
    queryFn: api.listAttentionRuns,
    refetchInterval: 5_000,
  });

  const stats = [
    { label: t('stats.publishedWorkflows'), value: workflowsQuery.data?.workflows.length ?? 0 },
    { label: t('stats.runs'), value: runsQuery.data?.runs.length ?? 0 },
    { label: t('stats.needAttention'), value: attentionQuery.data?.runs.length ?? 0 },
  ];

  const shortcuts = [
    {
      href: '/authoring',
      eyebrow: t('shortcuts.authoring.eyebrow'),
      title: t('shortcuts.authoring.title'),
      body: t('shortcuts.authoring.body'),
    },
    {
      href: '/workflows',
      eyebrow: t('shortcuts.catalog.eyebrow'),
      title: t('shortcuts.catalog.title'),
      body: t('shortcuts.catalog.body'),
    },
    {
      href: '/runs',
      eyebrow: t('shortcuts.workspace.eyebrow'),
      title: t('shortcuts.workspace.title'),
      body: t('shortcuts.workspace.body'),
    },
    {
      href: '/settings',
      eyebrow: t('shortcuts.settings.eyebrow'),
      title: t('shortcuts.settings.title'),
      body: t('shortcuts.settings.body'),
    },
  ];

  return (
    <StudioPage>
      <StudioPageHeader
        eyebrow={t('header')}
        title={t('title')}
        description={t('subtitle')}
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_340px]">
        <section className="overflow-hidden rounded-3xl border border-stone-200 bg-white">
          <div className="border-b border-stone-200 px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-stone-500">
              {t('shortcuts.authoring.eyebrow')}
            </p>
          </div>
          <div className="divide-y divide-stone-100">
            {shortcuts.map((shortcut) => (
              <Link
                key={shortcut.href}
                href={shortcut.href}
                className="block px-5 py-4 transition hover:bg-stone-50"
              >
                <p className="text-[11px] uppercase tracking-[0.2em] text-stone-500">{shortcut.eyebrow}</p>
                <h2 className="mt-1 text-xl font-semibold text-stone-900">{shortcut.title}</h2>
                <p className="mt-2 text-sm leading-6 text-stone-600">{shortcut.body}</p>
              </Link>
            ))}
          </div>
        </section>

        <aside className="rounded-3xl border border-stone-200 bg-white">
          <div className="border-b border-stone-200 px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-stone-500">
              {t('stats.runs')}
            </p>
          </div>
          <div className="divide-y divide-stone-100 px-5">
            {stats.map((item) => (
              <div key={item.label} className="py-4">
                <p className="text-xs uppercase tracking-[0.2em] text-stone-500">{item.label}</p>
                <p className="mt-1 text-3xl font-semibold tracking-[-0.03em] text-stone-900">{item.value}</p>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </StudioPage>
  );
}
