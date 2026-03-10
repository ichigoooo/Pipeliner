'use client';

import Link from 'next/link';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { api } from '@/lib/api';
import { WorkflowWorkspace } from '@/components/workflow/WorkflowWorkspace';

export default function WorkflowVersionPage({
  params,
}: {
  params: { workflow_id: string; version: string };
}) {
  const router = useRouter();
  const [showStart, setShowStart] = useState(false);
  const [inputsJson, setInputsJson] = useState('{\n  \n}');
  const [error, setError] = useState<string | null>(null);
  const workflowQuery = useQuery({
    queryKey: ['workflow', params.workflow_id, params.version],
    queryFn: () => api.getWorkflow(params.workflow_id, params.version),
  });

  const workflow = workflowQuery.data;
  const startRunMutation = useMutation({
    mutationFn: (inputs: Record<string, unknown>) =>
      api.startRun(params.workflow_id, params.version, inputs),
    onSuccess: (payload) => {
      router.push(`/runs/${payload.run_id}`);
    },
    onError: (mutationError) => {
      setError((mutationError as Error).message);
    },
  });

  if (!workflow) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-stone-500">
        Loading workflow workspace...
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-stone-200 px-6 py-5">
        <Link
          href={`/workflows/${params.workflow_id}`}
          className="text-sm font-medium text-stone-500 transition hover:text-stone-900"
        >
          ← Back to versions
        </Link>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-stone-500">Workflow workspace</p>
            <h1 className="mt-2 text-3xl font-semibold text-stone-900">
              {workflow.workflow_view.metadata.title}
            </h1>
            <p className="mt-2 text-sm leading-6 text-stone-600">
              {workflow.workflow_view.metadata.purpose}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-stone-100 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-stone-700">
              {workflow.version}
            </div>
            <button
              type="button"
              onClick={() => setShowStart((value) => !value)}
              className="rounded-full border border-stone-300 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-stone-700 transition hover:border-stone-900"
            >
              Start Run
            </button>
          </div>
        </div>
        {showStart ? (
          <div className="mt-4 rounded-[2rem] border border-stone-200 bg-white p-4 shadow-sm">
            <label className="text-xs font-semibold uppercase tracking-[0.2em] text-stone-500">
              Run inputs (JSON)
            </label>
            <textarea
              className="mt-3 min-h-32 w-full rounded-3xl border border-stone-200 bg-stone-50 px-4 py-3 font-mono text-xs text-stone-900 outline-none"
              value={inputsJson}
              onChange={(event) => setInputsJson(event.target.value)}
            />
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => {
                  setError(null);
                  let payload: Record<string, unknown>;
                  try {
                    const parsed = JSON.parse(inputsJson || '{}') as Record<string, unknown>;
                    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
                      throw new Error('输入必须是 JSON 对象');
                    }
                    payload = parsed;
                  } catch (parseError) {
                    setError(parseError instanceof Error ? parseError.message : '输入解析失败');
                    return;
                  }
                  startRunMutation.mutate(payload);
                }}
                disabled={startRunMutation.isPending}
                className="rounded-full bg-stone-950 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-white transition hover:bg-stone-800 disabled:cursor-not-allowed disabled:bg-stone-400"
              >
                Launch Run
              </button>
              <button
                type="button"
                onClick={() => setShowStart(false)}
                className="rounded-full border border-stone-300 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-stone-700 transition hover:border-stone-900"
              >
                Cancel
              </button>
              {error ? <p className="text-xs text-rose-700">{error}</p> : null}
            </div>
          </div>
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
