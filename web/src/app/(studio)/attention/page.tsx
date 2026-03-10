'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { api } from '@/lib/api';
import { formatTimestamp } from '@/lib/format';
import { StatusBadge } from '@/components/ui/StatusBadge';

export default function AttentionQueuePage() {
  const t = useTranslations('attention');
  const tc = useTranslations('common');
  const attentionQuery = useQuery({
    queryKey: ['attention-runs'],
    queryFn: api.listAttentionRuns,
    refetchInterval: 5_000,
  });

  const runs = attentionQuery.data?.runs ?? [];

  return (
    <div className="p-6 lg:p-8">
      <div className="mb-8">
        <p className="text-xs uppercase tracking-[0.26em] text-stone-500">{t('title')}</p>
        <h1 className="mt-3 text-3xl font-semibold text-stone-900">{t('description')}</h1>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        {runs.map((run) => (
          <Link
            key={run.run_id}
            href={`/runs/${run.run_id}`}
            className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm transition hover:border-amber-500 hover:shadow-md"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-stone-500">{run.workflow_id}</p>
                <h2 className="mt-2 text-xl font-semibold text-stone-900">{run.run_id}</h2>
                <p className="mt-3 text-sm text-stone-600">
                  {t('status.blocked')} {run.version}
                </p>
              </div>
              <StatusBadge value={run.status} />
            </div>
            <p className="mt-4 rounded-3xl bg-amber-50 px-4 py-3 text-sm text-amber-900">
              {run.stop_reason || t('description')}
            </p>
            <p className="mt-3 text-xs uppercase tracking-[0.18em] text-stone-500">
              {tc('refresh')}: {run.actions.join(', ')}
            </p>
          </Link>
        ))}
        {runs.length === 0 ? (
          <div className="rounded-[2rem] border border-dashed border-stone-300 bg-white p-12 text-center text-sm text-stone-500">
            {t('title')}
          </div>
        ) : null}
      </div>
    </div>
  );
}
