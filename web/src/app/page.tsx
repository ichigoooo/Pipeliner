'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export default function DashboardPage() {
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
    { label: 'Published Workflows', value: workflowsQuery.data?.workflows.length ?? 0 },
    { label: 'Runs', value: runsQuery.data?.runs.length ?? 0 },
    { label: 'Need Attention', value: attentionQuery.data?.runs.length ?? 0 },
  ];

  const shortcuts = [
    {
      href: '/authoring',
      eyebrow: 'Authoring',
      title: 'Create or revise a workflow draft',
      body: 'Continue a session, inspect revisions, edit raw spec, and publish only when lint passes.',
    },
    {
      href: '/workflows',
      eyebrow: 'Workflow Catalog',
      title: 'Inspect registered versions',
      body: 'Browse cards, graph, spec, and lint from one canonical workflow version.',
    },
    {
      href: '/runs',
      eyebrow: 'Run Workspace',
      title: 'Trace callbacks, artifacts, and rounds',
      body: 'Use the run workspace to inspect node rounds, context payloads, and intervention actions.',
    },
    {
      href: '/settings',
      eyebrow: 'Settings',
      title: 'See resolved config provenance',
      body: 'Compare the effective command templates, storage paths, and runtime guard defaults.',
    },
  ];

  return (
    <div className="min-h-full bg-[radial-gradient(circle_at_top_left,_rgba(251,191,36,0.18),_transparent_28%),linear-gradient(180deg,_#f8fafc_0%,_#f5f5f4_100%)] p-6 lg:p-8">
      <section className="rounded-[2.5rem] border border-stone-200 bg-white/90 p-8 shadow-xl backdrop-blur">
        <p className="text-xs uppercase tracking-[0.3em] text-stone-500">Workflow Studio</p>
        <div className="mt-4 grid gap-8 xl:grid-cols-[minmax(0,1.1fr)_360px]">
          <div>
            <h1 className="max-w-3xl text-4xl font-semibold leading-tight text-stone-950">
              Developer-first control surface for authoring, runs, attention handling, and config provenance.
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-stone-600">
              所有视图都围绕同一份 canonical workflow spec 派生，不再让 graph、cards 或调试面板成为第二份真源。
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
