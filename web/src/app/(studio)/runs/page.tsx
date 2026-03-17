'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { useMemo, useState } from 'react';
import { api } from '@/lib/api';
import type { BatchRunSummary } from '@/lib/api';
import { formatTimestamp } from '@/lib/format';
import { formatRunStopReason } from '@/lib/run-stop-reason';
import { StatusBadge } from '@/components/ui/StatusBadge';

const ACTIVE_BATCH_STATUSES = new Set(['pending', 'running']);

export default function RunsPage() {
  const t = useTranslations('runs');
  const router = useRouter();
  const queryClient = useQueryClient();
  const runsQuery = useQuery({
    queryKey: ['runs'],
    queryFn: api.listRuns,
    retry: false,
    refetchInterval: (query) => (query.state.error ? false : 8_000),
  });
  const batchesQuery = useQuery({
    queryKey: ['batch-runs'],
    queryFn: api.listBatchRuns,
    retry: false,
    refetchInterval: (query) => (query.state.error ? false : 8_000),
  });

  const runs = runsQuery.data?.runs ?? [];
  const batches = batchesQuery.data?.batches ?? [];
  const [statusFilter, setStatusFilter] = useState('all');
  const [workflowFilter, setWorkflowFilter] = useState('');
  const [showArchived, setShowArchived] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deletingRunId, setDeletingRunId] = useState<string | null>(null);
  const [batchDeleteError, setBatchDeleteError] = useState<string | null>(null);
  const [deletingBatchId, setDeletingBatchId] = useState<string | null>(null);
  const [selectedBatchIds, setSelectedBatchIds] = useState<string[]>([]);

  const deleteMutation = useMutation({
    mutationFn: (runId: string) => api.deleteRun(runId),
    onMutate: (runId) => {
      setDeletingRunId(runId);
      setDeleteError(null);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['runs'] });
    },
    onError: (mutationError) => {
      setDeleteError((mutationError as Error).message);
    },
    onSettled: () => {
      setDeletingRunId(null);
    },
  });

  const deleteBatchMutation = useMutation({
    mutationFn: (batchId: string) => api.deleteBatchRun(batchId),
    onMutate: (batchId) => {
      setDeletingBatchId(batchId);
      setBatchDeleteError(null);
    },
    onSuccess: async (_payload, batchId) => {
      setSelectedBatchIds((current) => current.filter((item) => item !== batchId));
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['batch-runs'] }),
        queryClient.invalidateQueries({ queryKey: ['runs'] }),
      ]);
    },
    onError: (mutationError) => {
      setBatchDeleteError((mutationError as Error).message);
    },
    onSettled: () => {
      setDeletingBatchId(null);
    },
  });

  const bulkDeleteBatchMutation = useMutation({
    mutationFn: (batchIds: string[]) => api.bulkDeleteBatchRuns(batchIds),
    onMutate: () => {
      setBatchDeleteError(null);
    },
    onSuccess: async () => {
      setSelectedBatchIds([]);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['batch-runs'] }),
        queryClient.invalidateQueries({ queryKey: ['runs'] }),
      ]);
    },
    onError: (mutationError) => {
      setBatchDeleteError((mutationError as Error).message);
    },
  });

  const statusOptions = useMemo(() => {
    const values = Array.from(new Set(runs.map((item) => item.status)));
    return ['all', ...values];
  }, [runs]);

  const filteredRuns = useMemo(() => {
    return runs.filter((run) => {
      if (statusFilter !== 'all' && run.status !== statusFilter) {
        return false;
      }
      if (workflowFilter.trim()) {
        const target = workflowFilter.trim().toLowerCase();
        if (!run.workflow_id.toLowerCase().includes(target)) {
          return false;
        }
      }
      return true;
    });
  }, [runs, statusFilter, workflowFilter]);

  const groupedRuns = useMemo(() => {
    const actionable: typeof filteredRuns = [];
    const active: typeof filteredRuns = [];
    const archived: typeof filteredRuns = [];

    for (const run of filteredRuns) {
      if (run.status === 'needs_attention') {
        actionable.push(run);
      } else if (run.status === 'running') {
        active.push(run);
      } else {
        archived.push(run);
      }
    }

    return { actionable, active, archived };
  }, [filteredRuns]);

  const sortedBatches = useMemo(() => {
    const parseTime = (value: string | null) => (value ? Date.parse(value) : 0);
    return [...batches].sort((left, right) => {
      const leftActive = ACTIVE_BATCH_STATUSES.has(left.status);
      const rightActive = ACTIVE_BATCH_STATUSES.has(right.status);
      if (leftActive !== rightActive) {
        return leftActive ? -1 : 1;
      }
      return parseTime(right.updated_at) - parseTime(left.updated_at);
    });
  }, [batches]);

  const toggleBatchSelection = (batchId: string) => {
    setSelectedBatchIds((current) =>
      current.includes(batchId)
        ? current.filter((item) => item !== batchId)
        : [...current, batchId]
    );
  };

  const renderRunCard = (run: (typeof filteredRuns)[number]) => {
    const batchId = run.batch_id;
    const canDelete = run.status !== 'running';
    const reason = formatRunStopReason(run.stop_reason, t);
    const summary =
      reason ||
      (run.status === 'running'
        ? t('listSummary.running')
        : run.status === 'completed'
          ? t('listSummary.completed')
          : run.status === 'stopped'
            ? t('listSummary.stopped')
            : t('listSummary.default'));
    return (
      <div
        key={run.run_id}
        className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm transition hover:border-amber-500 hover:shadow-md"
      >
        <div className="flex items-start justify-between gap-4">
          <Link href={`/runs/${run.run_id}`} className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-xs uppercase tracking-[0.22em] text-stone-500">{run.workflow_id}</p>
              <span className="rounded-full bg-stone-100 px-2.5 py-1 text-[11px] font-medium text-stone-600">
                {t('version')} {run.version}
              </span>
              {batchId ? (
                <span className="rounded-full bg-stone-100 px-2.5 py-1 text-[11px] font-medium text-stone-600">
                  {t('batch')}: {batchId}
                </span>
              ) : null}
            </div>
            <h2 className="mt-2 truncate text-xl font-semibold text-stone-900">{run.run_id}</h2>
            <p className="mt-3 text-sm leading-6 text-stone-600">{summary}</p>
            <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-stone-500">
              <span>{t('updated')}: {formatTimestamp(run.updated_at)}</span>
              {run.attention_node_count ? (
                <span className="rounded-full bg-amber-50 px-2.5 py-1 font-medium text-amber-900">
                  {t('attentionNodes')}: {run.attention_node_count}
                </span>
              ) : null}
            </div>
          </Link>
          <div className="flex shrink-0 flex-col items-end gap-2">
            {batchId ? (
              <button
                type="button"
                onClick={() => {
                  router.push(`/runs/batches/${batchId}`);
                }}
                className="rounded-full border border-stone-200 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-stone-600 transition hover:border-amber-400 hover:text-amber-900"
              >
                {t('viewBatch')}
              </button>
            ) : null}
            {canDelete ? (
              <button
                type="button"
                onClick={() => {
                  if (!window.confirm(t('deleteConfirm'))) {
                    return;
                  }
                  deleteMutation.mutate(run.run_id);
                }}
                disabled={deletingRunId === run.run_id}
                className="rounded-full border border-rose-200 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-rose-700 transition hover:border-rose-400 hover:text-rose-900 disabled:cursor-not-allowed disabled:border-stone-200 disabled:text-stone-400"
              >
                {deletingRunId === run.run_id ? t('actions.loading') : t('deleteRun')}
              </button>
            ) : null}
            <StatusBadge value={run.status} />
          </div>
        </div>
      </div>
    );
  };

  const renderBatchCard = (batch: BatchRunSummary) => {
    const isActive = ACTIVE_BATCH_STATUSES.has(batch.status);
    const canDeleteBatch = !isActive;
    const isSelected = selectedBatchIds.includes(batch.batch_id);
    return (
      <div
        key={batch.batch_id}
        className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm transition hover:border-amber-500 hover:shadow-md"
      >
        <div className="flex items-start justify-between gap-4">
          <button
            type="button"
            onClick={() => router.push(`/runs/batches/${batch.batch_id}`)}
            className="min-w-0 flex-1 text-left"
          >
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-xs uppercase tracking-[0.22em] text-stone-500">{batch.workflow_id}</p>
              <span className="rounded-full bg-stone-100 px-2.5 py-1 text-[11px] font-medium text-stone-600">
                {t('version')} {batch.version}
              </span>
              <span className="rounded-full bg-stone-100 px-2.5 py-1 text-[11px] font-medium text-stone-600">
                {t('batchLabel')}
              </span>
            </div>
            <h2 className="mt-2 truncate text-xl font-semibold text-stone-900">{batch.batch_id}</h2>
            <p className="mt-3 text-sm leading-6 text-stone-600">
              {t('batchSummary', {
                total: batch.total_count,
                success: batch.success_count,
                failed: batch.failed_count,
              })}
            </p>
            <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-stone-500">
              <span>{t('updated')}: {formatTimestamp(batch.updated_at)}</span>
              {isActive ? (
                <span className="rounded-full bg-sky-50 px-2.5 py-1 font-medium text-sky-900">
                  {t('batchActive')}
                </span>
              ) : null}
            </div>
          </button>
          <div className="flex shrink-0 flex-col items-end gap-2">
            {canDeleteBatch ? (
              <label className="flex items-center gap-2 text-xs font-medium text-stone-500">
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => toggleBatchSelection(batch.batch_id)}
                  className="h-4 w-4 rounded border-stone-300 text-amber-600 focus:ring-amber-500"
                />
                {t('selectBatch')}
              </label>
            ) : null}
            <span className="rounded-full border border-stone-200 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-stone-600">
              {t('viewBatch')}
            </span>
            {canDeleteBatch ? (
              <button
                type="button"
                onClick={() => {
                  if (!window.confirm(t('deleteBatchConfirm'))) {
                    return;
                  }
                  deleteBatchMutation.mutate(batch.batch_id);
                }}
                disabled={deletingBatchId === batch.batch_id || bulkDeleteBatchMutation.isPending}
                className="rounded-full border border-rose-200 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-rose-700 transition hover:border-rose-400 hover:text-rose-900 disabled:cursor-not-allowed disabled:border-stone-200 disabled:text-stone-400"
              >
                {deletingBatchId === batch.batch_id ? t('actions.loading') : t('deleteBatch')}
              </button>
            ) : null}
            <StatusBadge value={batch.status} />
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="p-6 lg:p-8">
      <div className="mb-8">
        <p className="text-xs uppercase tracking-[0.26em] text-stone-500">{t('title')}</p>
        <h1 className="mt-3 text-3xl font-semibold text-stone-900">{t('list')}</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-stone-600">{t('listDescription')}</p>
      </div>

      {runsQuery.error ? (
        <div className="mb-6 rounded-[2rem] border border-rose-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-rose-700">
            {t('connectionIssueTitle')}
          </p>
          <p className="mt-2 text-sm leading-6 text-stone-700">{t('connectionIssueHint')}</p>
          <p className="mt-3 rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-800">
            {(runsQuery.error as Error).message}
          </p>
        </div>
      ) : null}

      {deleteError ? (
        <div className="mb-6 rounded-[2rem] border border-rose-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-rose-700">
            {t('deleteFailed')}
          </p>
          <p className="mt-3 rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-800">
            {deleteError}
          </p>
        </div>
      ) : null}

      {batchDeleteError ? (
        <div className="mb-6 rounded-[2rem] border border-rose-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-rose-700">
            {t('deleteBatchFailed')}
          </p>
          <p className="mt-3 rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-800">
            {batchDeleteError}
          </p>
        </div>
      ) : null}

      {batchesQuery.error ? (
        <div className="mb-6 rounded-[2rem] border border-rose-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-rose-700">
            {t('batchConnectionIssueTitle')}
          </p>
          <p className="mt-2 text-sm leading-6 text-stone-700">{t('batchConnectionIssueHint')}</p>
          <p className="mt-3 rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-800">
            {(batchesQuery.error as Error).message}
          </p>
        </div>
      ) : null}

      <div className="mb-6 flex flex-wrap items-end gap-3 rounded-[2rem] border border-stone-200 bg-white p-4 shadow-sm">
        <label className="min-w-[220px] flex-1 text-xs uppercase tracking-[0.2em] text-stone-500">
          {t('workflowFilter')}
          <input
            className="mt-2 h-11 w-full rounded-2xl border border-stone-200 bg-stone-50 px-3 text-sm text-stone-900"
            placeholder={t('workflowPlaceholder')}
            value={workflowFilter}
            onChange={(event) => setWorkflowFilter(event.target.value)}
          />
        </label>
        <label className="w-[180px] text-xs uppercase tracking-[0.2em] text-stone-500">
          {t('status')}
          <select
            className="mt-2 h-11 w-full rounded-2xl border border-stone-200 bg-stone-50 px-3 text-sm text-stone-900"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
          >
            {statusOptions.map((value) => (
              <option key={value} value={value}>
                {value === 'all' ? t('allStatuses') : value}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="space-y-6">
        <section className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-stone-500">{t('groups.batch')}</p>
              <p className="mt-1 text-sm text-stone-600">{t('groups.batchHint')}</p>
            </div>
            <div className="flex items-center gap-3">
              <span className="rounded-full bg-stone-100 px-3 py-1 text-xs font-semibold text-stone-700">
                {sortedBatches.length}
              </span>
              {selectedBatchIds.length > 0 ? (
                <button
                  type="button"
                  onClick={() => {
                    if (!window.confirm(t('bulkDeleteBatchConfirm', { count: selectedBatchIds.length }))) {
                      return;
                    }
                    bulkDeleteBatchMutation.mutate(selectedBatchIds);
                  }}
                  disabled={bulkDeleteBatchMutation.isPending}
                  className="rounded-full border border-rose-200 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-rose-700 transition hover:border-rose-400 hover:text-rose-900 disabled:cursor-not-allowed disabled:border-stone-200 disabled:text-stone-400"
                >
                  {bulkDeleteBatchMutation.isPending
                    ? t('actions.loading')
                    : t('bulkDeleteBatch', { count: selectedBatchIds.length })}
                </button>
              ) : null}
            </div>
          </div>
          {sortedBatches.length === 0 ? (
            <div className="rounded-[2rem] border border-dashed border-stone-300 bg-white p-8 text-sm text-stone-500">
              {t('empty.batch')}
            </div>
          ) : (
            <div className="grid gap-4">{sortedBatches.map(renderBatchCard)}</div>
          )}
        </section>

        <section className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-stone-500">{t('groups.actionable')}</p>
              <p className="mt-1 text-sm text-stone-600">{t('groups.actionableHint')}</p>
            </div>
            <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-900">
              {groupedRuns.actionable.length}
            </span>
          </div>
          {groupedRuns.actionable.length === 0 ? (
            <div className="rounded-[2rem] border border-dashed border-stone-300 bg-white p-8 text-sm text-stone-500">
              {t('empty.actionable')}
            </div>
          ) : (
            <div className="grid gap-4">{groupedRuns.actionable.map(renderRunCard)}</div>
          )}
        </section>

        <section className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-stone-500">{t('groups.active')}</p>
              <p className="mt-1 text-sm text-stone-600">{t('groups.activeHint')}</p>
            </div>
            <span className="rounded-full bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-900">
              {groupedRuns.active.length}
            </span>
          </div>
          {groupedRuns.active.length === 0 ? (
            <div className="rounded-[2rem] border border-dashed border-stone-300 bg-white p-8 text-sm text-stone-500">
              {t('empty.active')}
            </div>
          ) : (
            <div className="grid gap-4">{groupedRuns.active.map(renderRunCard)}</div>
          )}
        </section>

        <details
          open={showArchived}
          onToggle={(event) => setShowArchived((event.target as HTMLDetailsElement).open)}
          className="rounded-[2rem] border border-stone-200 bg-white shadow-sm"
        >
          <summary className="cursor-pointer px-5 py-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-stone-500">{t('groups.archived')}</p>
                <p className="mt-1 text-sm text-stone-600">{t('groups.archivedHint')}</p>
              </div>
              <div className="flex items-center gap-3">
                <span className="rounded-full bg-stone-100 px-3 py-1 text-xs font-semibold text-stone-700">
                  {groupedRuns.archived.length}
                </span>
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">
                  {showArchived ? t('collapseArchived') : t('expandArchived')}
                </span>
              </div>
            </div>
          </summary>
          <div className="border-t border-stone-200 px-5 py-5">
            {groupedRuns.archived.length === 0 ? (
              <div className="rounded-[2rem] border border-dashed border-stone-300 bg-stone-50 p-8 text-sm text-stone-500">
                {t('empty.archived')}
              </div>
            ) : (
              <div className="grid gap-4">{groupedRuns.archived.map(renderRunCard)}</div>
            )}
          </div>
        </details>
      </div>
    </div>
  );
}
