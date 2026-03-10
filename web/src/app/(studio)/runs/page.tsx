'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { formatTimestamp } from '@/lib/format';
import { StatusBadge } from '@/components/ui/StatusBadge';

export default function RunsPage() {
  const runsQuery = useQuery({
    queryKey: ['runs'],
    queryFn: api.listRuns,
    refetchInterval: 8_000,
  });

  const runs = runsQuery.data?.runs ?? [];

  return (
    <div className="p-6 lg:p-8">
      <div className="mb-8">
        <p className="text-xs uppercase tracking-[0.26em] text-stone-500">Runs</p>
        <h1 className="mt-3 text-3xl font-semibold text-stone-900">Execution monitor</h1>
        <p className="mt-3 text-sm leading-6 text-stone-600">
          轮询显示当前 run 状态、attention 节点数量和调试入口。
        </p>
      </div>

      <div className="grid gap-4">
        {runs.map((run) => (
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
                  Version {run.version} · created {formatTimestamp(run.created_at)}
                </p>
              </div>
              <StatusBadge value={run.status} />
            </div>
            <div className="mt-4 grid gap-2 text-sm text-stone-600 md:grid-cols-3">
              <p>Stop reason: {run.stop_reason || '-'}</p>
              <p>Attention nodes: {run.attention_node_count ?? 0}</p>
              <p>Updated: {formatTimestamp(run.updated_at)}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
