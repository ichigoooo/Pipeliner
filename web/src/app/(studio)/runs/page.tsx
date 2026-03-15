'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { useMemo, useState } from 'react';
import { api } from '@/lib/api';
import { formatTimestamp } from '@/lib/format';
import { StatusBadge } from '@/components/ui/StatusBadge';

export default function RunsPage() {
  const t = useTranslations('runs');
  const runsQuery = useQuery({
    queryKey: ['runs'],
    queryFn: api.listRuns,
    refetchInterval: 8_000,
  });

  const runs = runsQuery.data?.runs ?? [];
  const [statusFilter, setStatusFilter] = useState('all');
  const [workflowFilter, setWorkflowFilter] = useState('');
  const [onlyAttention, setOnlyAttention] = useState(false);

  const statusOptions = useMemo(() => {
    const values = Array.from(new Set(runs.map((item) => item.status)));
    return ['all', ...values];
  }, [runs]);

  const filteredRuns = useMemo(() => {
    return runs.filter((run) => {
      if (statusFilter !== 'all' && run.status !== statusFilter) {
        return false;
      }
      if (onlyAttention && (run.attention_node_count ?? 0) <= 0) {
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
  }, [onlyAttention, runs, statusFilter, workflowFilter]);

  return (
    <div className="p-6 lg:p-8">
      <div className="mb-8">
        <p className="text-xs uppercase tracking-[0.26em] text-stone-500">{t('title')}</p>
        <h1 className="mt-3 text-3xl font-semibold text-stone-900">{t('list')}</h1>
        <p className="mt-3 text-sm leading-6 text-stone-600">
          {t('noRuns')}
        </p>
      </div>

      <div className="mb-6 grid gap-3 rounded-[2rem] border border-stone-200 bg-white p-4 shadow-sm md:grid-cols-[minmax(0,1fr)_200px_180px]">
        <label className="block text-xs uppercase tracking-[0.2em] text-stone-500">
          {t('status')}
          <select
            className="mt-2 h-11 w-full rounded-2xl border border-stone-200 bg-stone-50 px-3 text-sm text-stone-900"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
          >
            {statusOptions.map((value) => (
              <option key={value} value={value}>
                {value === 'all' ? t('status') : value}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-xs uppercase tracking-[0.2em] text-stone-500">
          Workflow
          <input
            className="mt-2 h-11 w-full rounded-2xl border border-stone-200 bg-stone-50 px-3 text-sm text-stone-900"
            placeholder="workflow_id"
            value={workflowFilter}
            onChange={(event) => setWorkflowFilter(event.target.value)}
          />
        </label>
        <label className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-stone-500">
          <input
            type="checkbox"
            checked={onlyAttention}
            onChange={(event) => setOnlyAttention(event.target.checked)}
          />
          {t('attentionNodes')}
        </label>
      </div>

      <div className="grid gap-4">
        {filteredRuns.map((run) => (
          <Link
            key={run.run_id}
            href={`/runs/${run.run_id}`}
            className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm transition hover:border-amber-500 hover:shadow-md"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-stone-500">{run.workflow_id}</p>
                <h2 className="mt-2 text-xl font-semibold text-stone-900">{run.run_id}</h2>
                <p className="mt-3 text-sm text-stone-600">
                  {t('version')} {run.version} · {t('created')} {formatTimestamp(run.created_at)}
                </p>
              </div>
              <StatusBadge value={run.status} />
            </div>
            <div className="mt-4 grid gap-2 text-sm text-stone-600 md:grid-cols-3">
              <p>{t('stopReason')}: {run.stop_reason || '-'}</p>
              <p>{t('attentionNodes')}: {run.attention_node_count ?? 0}</p>
              <p>{t('updated')}: {formatTimestamp(run.updated_at)}</p>
            </div>
          </Link>
        ))}
        {filteredRuns.length === 0 ? (
          <div className="rounded-[2rem] border border-dashed border-stone-300 bg-white p-12 text-center text-sm text-stone-500">
            {t('noRuns')}
          </div>
        ) : null}
      </div>
    </div>
  );
}
