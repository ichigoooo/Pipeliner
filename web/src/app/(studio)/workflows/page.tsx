'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { useState } from 'react';
import { api } from '@/lib/api';
import { formatTimestamp } from '@/lib/format';
import { HelpTooltip } from '@/components/ui/HelpTooltip';

const MAX_PREVIEW_LENGTH = 120;

function ExpandablePurpose({ purpose, t }: { purpose: string; t: (key: string) => string }) {
  const [expanded, setExpanded] = useState(false);

  if (!purpose) {
    return <span className="text-stone-400">-</span>;
  }

  const needsExpansion = purpose.length > MAX_PREVIEW_LENGTH;
  const displayText = expanded || !needsExpansion
    ? purpose
    : purpose.slice(0, MAX_PREVIEW_LENGTH) + '...';

  return (
    <div>
      <p className="text-sm leading-6 text-stone-600 whitespace-pre-wrap">{displayText}</p>
      {needsExpansion && (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="mt-2 text-xs font-medium text-amber-700 hover:text-amber-800 transition"
        >
          {expanded ? t('collapse') : t('expand')}
        </button>
      )}
    </div>
  );
}

export default function WorkflowsPage() {
  const t = useTranslations('workflows');
  const tc = useTranslations('common');
  const workflowsQuery = useQuery({
    queryKey: ['workflows'],
    queryFn: api.listWorkflows,
  });

  const workflows = workflowsQuery.data?.workflows ?? [];

  return (
    <div className="p-6 lg:p-8">
      <div className="mb-8 flex items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <p className="text-xs uppercase tracking-[0.26em] text-stone-500">{t('title')}</p>
            <HelpTooltip content={t('description')} label={t('title')} />
          </div>
          <h1 className="mt-3 text-3xl font-semibold text-stone-900">{t('list')}</h1>
        </div>
        <Link
          href="/authoring"
          className="rounded-full bg-stone-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-stone-800"
        >
          {tc('open')}
        </Link>
      </div>

      <div className="overflow-hidden rounded-[2rem] border border-stone-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-stone-200">
          <thead className="bg-stone-50">
            <tr className="text-left text-xs uppercase tracking-[0.22em] text-stone-500">
              <th className="px-6 py-4">{t('title')}</th>
              <th className="px-6 py-4">Purpose</th>
              <th className="px-6 py-4">{t('version')}</th>
              <th className="px-6 py-4">Latest</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {workflows.map((workflow) => (
              <tr key={workflow.workflow_id} className="align-top">
                <td className="px-6 py-5">
                  <Link
                    href={`/workflows/${workflow.workflow_id}`}
                    className="text-lg font-semibold text-stone-900 transition hover:text-amber-700"
                  >
                    {workflow.title}
                  </Link>
                  <p className="mt-2 text-xs uppercase tracking-[0.2em] text-stone-500">
                    {workflow.workflow_id}
                  </p>
                </td>
                <td className="px-6 py-5">
                  <ExpandablePurpose purpose={workflow.purpose ?? ''} t={tc} />
                </td>
                <td className="px-6 py-5 text-sm text-stone-700">{workflow.version_count}</td>
                <td className="px-6 py-5 text-sm text-stone-700">
                  <div>{workflow.latest_version || '-'}</div>
                  <div className="mt-1 text-xs text-stone-500">
                    {tc('refresh')} {formatTimestamp(workflow.updated_at)}
                  </div>
                </td>
              </tr>
            ))}
            {workflows.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-6 py-12 text-center text-sm text-stone-500">
                  {t('noWorkflows')}
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
