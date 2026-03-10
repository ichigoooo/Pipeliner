'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { formatTimestamp } from '@/lib/format';
import { StatusBadge } from '@/components/ui/StatusBadge';

export default function WorkflowDetailPage({
  params,
}: {
  params: { workflow_id: string };
}) {
  const versionsQuery = useQuery({
    queryKey: ['workflow-versions', params.workflow_id],
    queryFn: () => api.listWorkflowVersions(params.workflow_id),
  });

  const versions = versionsQuery.data?.versions ?? [];

  return (
    <div className="p-6 lg:p-8">
      <Link href="/workflows" className="text-sm font-medium text-stone-500 transition hover:text-stone-900">
        ← Back to workflows
      </Link>
      <div className="mt-4 flex items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.26em] text-stone-500">Workflow versions</p>
          <h1 className="mt-3 text-3xl font-semibold text-stone-900">{params.workflow_id}</h1>
          <p className="mt-3 text-sm leading-6 text-stone-600">
            选择一个版本进入 cards / graph / spec / lint 同步工作区。
          </p>
        </div>
      </div>

      <div className="mt-8 grid gap-4">
        {versions.map((version) => (
          <Link
            key={version.version}
            href={`/workflows/${params.workflow_id}/${version.version}`}
            className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm transition hover:border-amber-500 hover:shadow-md"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-stone-500">Version</p>
                <h2 className="mt-2 text-2xl font-semibold text-stone-900">{version.version}</h2>
                <p className="mt-3 text-sm text-stone-500">
                  Created {formatTimestamp(version.created_at)}
                </p>
              </div>
              <StatusBadge value={version.warnings.length ? 'active' : 'published'} />
            </div>
            <div className="mt-4 text-sm text-stone-600">
              <p>Schema: {version.schema_version}</p>
              <p className="mt-2">
                Warnings: {version.warnings.length ? version.warnings.join(' | ') : 'No warnings'}
              </p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
