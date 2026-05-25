'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { api } from '@/lib/api';
import { formatTimestamp } from '@/lib/format';
import { HelpTooltip } from '@/components/ui/HelpTooltip';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { StudioPage, StudioPageHeader } from '@/components/ui/StudioPage';

export function WorkflowDetailClient({ workflowId }: { workflowId: string }) {
  const t = useTranslations('workflows');
  const versionsQuery = useQuery({
    queryKey: ['workflow-versions', workflowId],
    queryFn: () => api.listWorkflowVersions(workflowId),
  });

  const versions = versionsQuery.data?.versions ?? [];

  return (
    <StudioPage>
      <Link href="/workflows" className="text-sm font-medium text-stone-500 transition hover:text-stone-900">
        ← {t('backToWorkflows')}
      </Link>
      <StudioPageHeader
        className="mt-4"
        eyebrow={t('versions')}
        title={workflowId}
        description={(
          <span className="inline-flex items-center gap-2">
            {t('selectVersionHint')}
            <HelpTooltip content={t('selectVersionHint')} label={t('versions')} />
          </span>
        )}
      />

      <div className="grid gap-3">
        {versions.map((version) => (
          <Link
            key={version.version}
            href={`/workflows/${workflowId}/${version.version}`}
            className="rounded-3xl border border-stone-200 bg-white p-5 transition hover:border-amber-500 hover:bg-stone-50"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-stone-500">{t('version')}</p>
                <h2 className="mt-2 text-2xl font-semibold text-stone-900">{version.version}</h2>
                <p className="mt-3 text-sm text-stone-500">
                  {t('createdAt', { date: formatTimestamp(version.created_at) })}
                </p>
              </div>
              <StatusBadge value={version.warnings.length ? 'active' : 'published'} />
            </div>
            <div className="mt-4 text-sm text-stone-600">
              <p>{t('schema')}: {version.schema_version}</p>
              <p className="mt-2">
                {t('warnings')}: {version.warnings.length ? version.warnings.join(' | ') : t('noWarnings')}
              </p>
            </div>
          </Link>
        ))}
      </div>
    </StudioPage>
  );
}
