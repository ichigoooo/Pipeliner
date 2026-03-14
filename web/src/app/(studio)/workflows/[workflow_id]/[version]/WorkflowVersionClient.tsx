'use client';

import Link from 'next/link';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { api } from '@/lib/api';
import { WorkflowWorkspace } from '@/components/workflow/WorkflowWorkspace';
import { WorkflowRunStartPanel } from '@/components/workflow/WorkflowRunStartPanel';

export function WorkflowVersionClient({
  workflowId,
  version,
}: {
  workflowId: string;
  version: string;
}) {
  const t = useTranslations('workflows');
  const router = useRouter();
  const [showStart, setShowStart] = useState(false);
  const [purposeExpanded, setPurposeExpanded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [iterationError, setIterationError] = useState<string | null>(null);
  const workflowQuery = useQuery({
    queryKey: ['workflow', workflowId, version],
    queryFn: () => api.getWorkflow(workflowId, version),
  });

  const workflow = workflowQuery.data;
  const purpose = workflow?.workflow_view.metadata.purpose?.trim() || '';
  const shouldCollapsePurpose = purpose.length > 220;

  useEffect(() => {
    setPurposeExpanded(false);
  }, [workflowId, version]);

  const startRunMutation = useMutation({
    mutationFn: (inputs: Record<string, unknown>) =>
      api.startRun(workflowId, version, inputs, { auto_drive: true }),
    onSuccess: (payload) => {
      router.push(`/runs/${payload.run_id}`);
    },
    onError: (mutationError) => {
      setError((mutationError as Error).message);
    },
  });

  const iterateMutation = useMutation({
    mutationFn: () =>
      api.createAuthoringSessionFromVersion({
        workflow_id: workflowId,
        version,
      }),
    onSuccess: (payload) => {
      router.push(`/authoring?session=${payload.session_id}`);
    },
    onError: (mutationError) => {
      setIterationError((mutationError as Error).message);
    },
  });

  if (!workflow) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-stone-500">
        {t('loadingWorkspace')}
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-stone-200 px-6 py-5">
        <Link
          href={`/workflows/${workflowId}`}
          className="text-sm font-medium text-stone-500 transition hover:text-stone-900"
        >
          ← {t('backToVersions')}
        </Link>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-stone-500">{t('workspace')}</p>
            <h1 className="mt-2 text-3xl font-semibold text-stone-900">
              {workflow.workflow_view.metadata.title}
            </h1>
            {purpose ? (
              <div className="mt-2 max-w-5xl">
                <div className="relative">
                  <p
                    data-testid="workflow-purpose"
                    className={`whitespace-pre-wrap text-sm leading-6 text-stone-600 ${
                      shouldCollapsePurpose && !purposeExpanded ? 'max-h-24 overflow-hidden' : ''
                    }`}
                  >
                    {purpose}
                  </p>
                  {shouldCollapsePurpose && !purposeExpanded ? (
                    <span className="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-white to-transparent" />
                  ) : null}
                </div>
                {shouldCollapsePurpose ? (
                  <button
                    type="button"
                    aria-expanded={purposeExpanded}
                    onClick={() => setPurposeExpanded((value) => !value)}
                    className="mt-2 rounded-full border border-stone-300 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-stone-700 transition hover:border-stone-900"
                  >
                    {purposeExpanded ? t('collapsePurpose') : t('expandPurpose')}
                  </button>
                ) : null}
              </div>
            ) : null}
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-stone-100 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-stone-700">
              {workflow.version}
            </div>
            <button
              type="button"
              onClick={() => iterateMutation.mutate()}
              className="rounded-full border border-amber-300 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-amber-900 transition hover:border-amber-400"
            >
              {t('iterate')}
            </button>
            <button
              type="button"
              onClick={() => setShowStart((value) => !value)}
              className="rounded-full border border-stone-300 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-stone-700 transition hover:border-stone-900"
            >
              {t('startRun')}
            </button>
          </div>
        </div>
        <p className="mt-3 text-xs text-stone-500">{t('iterateHint')}</p>
        {iterationError ? <p className="mt-2 text-xs text-rose-700">{iterationError}</p> : null}
        {showStart ? (
          <WorkflowRunStartPanel
            descriptors={workflow.workflow_view.input_descriptors}
            error={error}
            isSubmitting={startRunMutation.isPending}
            onCancel={() => setShowStart(false)}
            onSubmit={(payload) => {
              setError(null);
              startRunMutation.mutate(payload);
            }}
          />
        ) : null}
      </div>

      <div className="min-h-0 flex-1">
        <WorkflowWorkspace
          spec={workflow.spec}
          cards={workflow.workflow_view.cards}
          nodes={workflow.graph.nodes as never[]}
          edges={workflow.graph.edges as never[]}
          lintWarnings={workflow.lint_report.warnings}
          lintErrors={workflow.lint_report.errors}
        />
      </div>
    </div>
  );
}
