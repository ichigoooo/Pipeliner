'use client';

import Link from 'next/link';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { api } from '@/lib/api';
import { StatusBadge } from '@/components/ui/StatusBadge';

export default function AttentionQueuePage() {
  const t = useTranslations('attention');
  const tc = useTranslations('common');
  const router = useRouter();
  const [iterationError, setIterationError] = useState<string | null>(null);
  const attentionQuery = useQuery({
    queryKey: ['attention-runs'],
    queryFn: api.listAttentionRuns,
    refetchInterval: 5_000,
  });

  const iterateMutation = useMutation({
    mutationFn: (runId: string) => api.createAuthoringSessionFromRun({ run_id: runId }),
    onSuccess: (payload) => {
      router.push(`/authoring?session=${payload.session_id}`);
    },
    onError: (mutationError) => {
      setIterationError((mutationError as Error).message);
    },
  });

  const runs = attentionQuery.data?.runs ?? [];

  return (
    <div className="p-6 lg:p-8">
      <div className="mb-8">
        <p className="text-xs uppercase tracking-[0.26em] text-stone-500">{t('title')}</p>
        <h1 className="mt-3 text-3xl font-semibold text-stone-900">{t('description')}</h1>
        <p className="mt-2 text-xs text-stone-500">{t('iterateHint')}</p>
        {iterationError ? <p className="mt-2 text-xs text-rose-700">{iterationError}</p> : null}
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
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs uppercase tracking-[0.18em] text-stone-500">
                {tc('refresh')}: {run.actions.join(', ')}
              </p>
              <button
                type="button"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  iterateMutation.mutate(run.run_id);
                }}
                className="rounded-full border border-amber-300 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-900 transition hover:border-amber-400"
              >
                {t('iterate')}
              </button>
            </div>
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
