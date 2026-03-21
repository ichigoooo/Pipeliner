'use client';

import Link from 'next/link';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { AdaptiveButtonLabel } from '@/components/ui/AdaptiveButtonLabel';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { api } from '@/lib/api';
import { formatTimestamp, prettyJson } from '@/lib/format';

const ACTIVE_BATCH_STATUSES = new Set(['pending', 'running']);
const BATCH_POLL_INTERVAL_MS = 2_000;

export function BatchRunDetailClient({ batchId }: { batchId: string }) {
  const t = useTranslations('batchRuns');
  const tRuns = useTranslations('runs');
  const tCommon = useTranslations('common');
  const [openingRunId, setOpeningRunId] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const batchQuery = useQuery({
    queryKey: ['batch-run', batchId],
    queryFn: () => api.getBatchRun(batchId),
    refetchInterval: (query) => {
      const status = (query.state.data as { batch?: { status?: string } } | undefined)?.batch?.status;
      return status && ACTIVE_BATCH_STATUSES.has(status) ? BATCH_POLL_INTERVAL_MS : false;
    },
  });

  const openWorkspaceMutation = useMutation({
    mutationFn: (runId: string) => api.openRunWorkspace(runId),
    onMutate: (runId) => {
      setOpeningRunId(runId);
      setActionMessage(null);
      setActionError(null);
    },
    onSuccess: (payload) => {
      setActionMessage(t('openFolderSuccess', { path: payload.opened_path }));
    },
    onError: (mutationError) => {
      setActionError((mutationError as Error).message);
    },
    onSettled: () => {
      setOpeningRunId(null);
    },
  });

  const batch = batchQuery.data?.batch;
  const items = batchQuery.data?.items ?? [];

  if (batchQuery.error) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-sm text-rose-700">
        {(batchQuery.error as Error).message}
      </div>
    );
  }

  if (!batch) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-stone-500">
        {t('loading')}
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8">
      <Link
        href="/runs"
        className="text-sm font-medium text-stone-500 transition hover:text-stone-900"
      >
        ← {tRuns('backToRuns')}
      </Link>

      <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.26em] text-stone-500">{t('details')}</p>
          <h1 className="mt-3 text-3xl font-semibold text-stone-900">{batch.batch_id}</h1>
          <p className="mt-3 text-sm leading-6 text-stone-600">
            {batch.workflow_id} · {t('version')} {batch.version}
          </p>
          {ACTIVE_BATCH_STATUSES.has(batch.status) ? (
            <p className="mt-2 text-xs text-stone-500">{t('autoRefresh')}</p>
          ) : null}
        </div>
        <StatusBadge value={batch.status} />
      </div>

      <div className="mt-8 grid gap-4 md:grid-cols-4">
        <SummaryCard label={t('total')} value={String(batch.total_count)} />
        <SummaryCard label={t('success')} value={String(batch.success_count)} />
        <SummaryCard label={t('failed')} value={String(batch.failed_count)} />
        <SummaryCard label={t('status')} value={batch.status} />
      </div>

      <div className="mt-6 grid gap-4 rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm lg:grid-cols-2">
        <MetaRow label={t('created')} value={formatTimestamp(batch.created_at)} />
        <MetaRow label={t('updated')} value={formatTimestamp(batch.updated_at)} />
        <MetaRow label={t('started')} value={formatTimestamp(batch.started_at)} />
        <MetaRow label={t('ended')} value={formatTimestamp(batch.ended_at)} />
      </div>

      {batch.error_message ? (
        <p className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {batch.error_message}
        </p>
      ) : null}
      {actionMessage ? (
        <p className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {actionMessage}
        </p>
      ) : null}
      {actionError ? (
        <p className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {actionError}
        </p>
      ) : null}

      <div className="mt-8 overflow-hidden rounded-[2rem] border border-stone-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-stone-200">
          <thead className="bg-stone-50">
            <tr className="text-left text-xs uppercase tracking-[0.22em] text-stone-500">
              <th className="px-5 py-4">{t('row')}</th>
              <th className="px-5 py-4">{t('inputs')}</th>
              <th className="px-5 py-4">{t('status')}</th>
              <th className="px-5 py-4">{t('runId')}</th>
              <th className="px-5 py-4">{t('error')}</th>
              <th className="px-5 py-4">{tCommon('open')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {items.map((item) => (
              <tr key={item.item_id} className="align-top">
                <td className="px-5 py-4 text-sm font-medium text-stone-900">{item.row_index}</td>
                <td className="px-5 py-4">
                  <pre className="max-w-md overflow-x-auto whitespace-pre-wrap rounded-2xl bg-stone-950/95 p-3 text-xs leading-5 text-stone-100">
                    {prettyJson(item.inputs)}
                  </pre>
                </td>
                <td className="px-5 py-4">
                  <StatusBadge value={item.status} />
                </td>
                <td className="px-5 py-4 text-sm text-stone-700">
                  {item.run_id && !item.run_deleted ? (
                    <Link
                      href={`/runs/${item.run_id}`}
                      className="font-medium text-stone-600 transition hover:text-stone-900"
                    >
                      {t('viewRun')} {item.run_id}
                    </Link>
                  ) : item.run_id ? (
                    <div className="space-y-1">
                      <span className="font-medium text-stone-700">{item.run_id}</span>
                      <p className="text-xs text-rose-700">{t('deletedRun')}</p>
                    </div>
                  ) : (
                    <span className="text-stone-400">{t('noRun')}</span>
                  )}
                </td>
                <td className="px-5 py-4 text-sm text-rose-700">{item.error_message || '-'}</td>
                <td className="px-5 py-4">
                  <button
                    type="button"
                    disabled={!item.run_id || item.run_deleted || openingRunId === item.run_id}
                    onClick={() => item.run_id && openWorkspaceMutation.mutate(item.run_id)}
                    className="inline-flex min-w-0 max-w-full items-center justify-center overflow-hidden rounded-full border border-stone-300 px-3 py-2 font-semibold uppercase tracking-[0.18em] text-stone-700 transition hover:border-stone-900 disabled:cursor-not-allowed disabled:border-stone-200 disabled:text-stone-400"
                  >
                    <AdaptiveButtonLabel text={t('openFolder')} maxFontSize={12} />
                  </button>
                </td>
              </tr>
            ))}
            {items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-5 py-12 text-center text-sm text-stone-500">
                  {t('empty')}
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
      <p className="text-xs uppercase tracking-[0.2em] text-stone-500">{label}</p>
      <p className="mt-3 text-3xl font-semibold text-stone-900">{value}</p>
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.2em] text-stone-500">{label}</p>
      <p className="mt-2 text-sm text-stone-700">{value}</p>
    </div>
  );
}
