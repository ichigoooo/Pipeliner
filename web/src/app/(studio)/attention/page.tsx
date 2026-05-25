'use client';

import Link from 'next/link';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { api } from '@/lib/api';
import { formatRunStopReason } from '@/lib/run-stop-reason';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { StudioPage, StudioPageHeader } from '@/components/ui/StudioPage';

export default function AttentionQueuePage() {
  const t = useTranslations('attention');
  const tc = useTranslations('common');
  const tr = useTranslations('runs');
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
  const queryError = attentionQuery.error as Error | null;

  return (
    <StudioPage>
      <StudioPageHeader
        eyebrow={t('title')}
        title={t('description')}
        description={t('iterateHint')}
      />
      {iterationError ? <p className="mb-4 text-xs text-rose-700">{iterationError}</p> : null}
      {queryError && runs.length === 0 ? (
        <section className="rounded-3xl border border-rose-200 bg-rose-50 p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-rose-700">{tc('error')}</p>
          <p className="mt-3 text-sm leading-6 text-rose-900">{queryError.message}</p>
          <button
            type="button"
            onClick={() => void attentionQuery.refetch()}
            className="mt-4 rounded-full border border-rose-300 px-4 py-2 text-sm font-medium text-rose-900 transition hover:border-rose-400"
          >
            {tc('retry')}
          </button>
        </section>
      ) : null}

      {attentionQuery.isLoading && runs.length === 0 ? (
        <div className="grid gap-3 xl:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <div
              key={`attention-skeleton-${index}`}
              className="h-44 animate-pulse rounded-3xl border border-stone-200 bg-stone-100"
            />
          ))}
        </div>
      ) : null}

      {!attentionQuery.isLoading && runs.length > 0 ? (
        <div className="grid gap-3 xl:grid-cols-2">
          {runs.map((run) => (
            <Link
              key={run.run_id}
              href={`/runs/${run.run_id}?focus=attention`}
              className="rounded-3xl border border-stone-200 bg-white p-5 transition hover:border-amber-500 hover:bg-stone-50"
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
                {formatRunStopReason(run.stop_reason, tr) || t('description')}
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
        </div>
      ) : null}

      {!attentionQuery.isLoading && !queryError && runs.length === 0 ? (
        <section className="rounded-3xl border border-dashed border-stone-300 bg-white p-12">
          <div className="mx-auto max-w-xl text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-stone-500">{t('title')}</p>
            <h2 className="mt-3 text-2xl font-semibold tracking-[-0.03em] text-stone-900">{t('description')}</h2>
            <p className="mt-3 text-sm leading-6 text-stone-600">{t('iterateHint')}</p>
            <div className="mt-6 flex flex-wrap justify-center gap-3">
              <Link
                href="/runs"
                className="rounded-full border border-stone-300 px-4 py-2 text-sm font-medium text-stone-800 transition hover:border-stone-900"
              >
                {tr('backToRuns')}
              </Link>
              <Link
                href="/authoring"
                className="rounded-full border border-amber-300 bg-amber-100 px-4 py-2 text-sm font-medium text-amber-950 transition hover:border-amber-400 hover:bg-amber-200"
              >
                {t('iterate')}
              </Link>
            </div>
          </div>
        </section>
      ) : null}
    </StudioPage>
  );
}
