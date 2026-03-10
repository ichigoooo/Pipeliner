'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useTranslations } from 'next-intl';

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
    <div className="min-h-full bg-[radial-gradient(circle_at_top_left,_rgba(251,191,36,0.18),_transparent_28%),linear-gradient(180deg,_#f8fafc_0%,_#f5f5f4_100%)] p-6 lg:p-8">
      <section className="rounded-[2.5rem] border border-stone-200 bg-white/90 p-8 shadow-xl backdrop-blur">
        <p className="text-xs uppercase tracking-[0.3em] text-stone-500">{t('header')}</p>
        <div className="mt-4 grid gap-8 xl:grid-cols-[minmax(0,1.1fr)_360px]">
          <div>
            <h1 className="max-w-3xl text-4xl font-semibold leading-tight text-stone-950">
              {t('title')}
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-stone-600">
              {t('subtitle')}
            </p>
          </div>
          <div className="grid gap-3">
            {stats.map((item) => (
              <div key={item.label} className="rounded-[1.75rem] border border-stone-200 bg-stone-50 px-5 py-4">
                <p className="text-xs uppercase tracking-[0.22em] text-stone-500">{item.label}</p>
                <p className="mt-2 text-3xl font-semibold text-stone-950">{item.value}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mt-8 grid gap-4 xl:grid-cols-2">
        {shortcuts.map((shortcut) => (
          <Link
            key={shortcut.href}
            href={shortcut.href}
            className="rounded-[2rem] border border-stone-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:border-amber-500 hover:shadow-md"
          >
            <p className="text-xs uppercase tracking-[0.24em] text-stone-500">{shortcut.eyebrow}</p>
            <h2 className="mt-3 text-2xl font-semibold text-stone-950">{shortcut.title}</h2>
            <p className="mt-4 text-sm leading-7 text-stone-600">{shortcut.body}</p>
          </Link>
        ))}
      </section>
    </div>
  );
}
