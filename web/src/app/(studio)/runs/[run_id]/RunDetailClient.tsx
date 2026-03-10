'use client';

import Link from 'next/link';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { api } from '@/lib/api';
import { prettyJson } from '@/lib/format';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { TabList } from '@/components/ui/TabList';
import { InspectorPanel } from '@/components/ui/InspectorPanel';

const ATTENTION_STATUSES = new Set(['blocked', 'failed', 'timed_out', 'rework_limit', 'stopped']);

export function RunDetailClient({ runId }: { runId: string }) {
  const t = useTranslations('runs');
  const queryClient = useQueryClient();
  const [activeTabIndex, setActiveTabIndex] = useState(0);
  const [selectedNode, setSelectedNode] = useState<{ node_id: string; round_no: number } | null>(null);
  const [inspectorData, setInspectorData] = useState<unknown>(null);

  const runQuery = useQuery({
    queryKey: ['run', runId],
    queryFn: () => api.getRun(runId),
    refetchInterval: 8_000,
  });

  const overviewQuery = useQuery({
    queryKey: ['run-overview', runId],
    queryFn: () => api.getRunOverview(runId),
    refetchInterval: 8_000,
  });

  useEffect(() => {
    if (!selectedNode && overviewQuery.data?.latest_nodes.length) {
      const latest = overviewQuery.data.latest_nodes[0];
      setSelectedNode({ node_id: latest.node_id, round_no: latest.round_no });
    }
  }, [overviewQuery.data, selectedNode]);

  const nodeRoundQuery = useQuery({
    queryKey: ['run-node-round', runId, selectedNode?.node_id, selectedNode?.round_no],
    queryFn: () => api.getNodeRound(runId, selectedNode!.node_id, selectedNode!.round_no),
    enabled: Boolean(selectedNode),
    refetchInterval: 8_000,
  });

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['run', runId] }),
      queryClient.invalidateQueries({ queryKey: ['run-overview', runId] }),
      queryClient.invalidateQueries({ queryKey: ['run-node-round', runId] }),
    ]);
  };

  const stopMutation = useMutation({
    mutationFn: () => api.stopRun(runId),
    onSuccess: refresh,
  });

  const retryMutation = useMutation({
    mutationFn: () =>
      selectedNode
        ? api.retryNode(runId, selectedNode.node_id, { reason: 'studio retry' })
        : Promise.reject(new Error('请先选择一个 attention node')),
    onSuccess: refresh,
  });

  const run = runQuery.data;
  const overview = overviewQuery.data;
  const nodeRound = nodeRoundQuery.data;
  const tabKeys = ['timeline', 'nodeDetail', 'artifacts', 'raw'] as const;
  const tabs = tabKeys.map((key) => t(`tabs.${key}`));

  if (!run || !overview) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-stone-500">
        {t('loading')}
      </div>
    );
  }

  const selectedLatest = overview.latest_nodes.find(
    (item) => item.node_id === selectedNode?.node_id && item.round_no === selectedNode?.round_no
  );
  const canRetry = selectedLatest ? ATTENTION_STATUSES.has(selectedLatest.status) : false;

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-stone-200 px-6 py-5">
        <Link href="/runs" className="text-sm font-medium text-stone-500 transition hover:text-stone-900">
          ← {t('backToRuns')}
        </Link>
        <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-stone-500">{t('workspace')}</p>
            <h1 className="mt-2 text-3xl font-semibold text-stone-900">{run.run.id}</h1>
            <p className="mt-3 text-sm leading-6 text-stone-600">
              {run.workflow.workflow_id}@{run.workflow.version} · workspace {run.run.workspace_root}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <StatusBadge value={run.run.status} />
            <button
              type="button"
              onClick={() => stopMutation.mutate()}
              className="rounded-full border border-stone-300 px-4 py-2 text-sm font-medium text-stone-800 transition hover:border-stone-900"
            >
              {t('stopRun')}
            </button>
            <button
              type="button"
              disabled={!canRetry}
              onClick={() => retryMutation.mutate()}
              className="rounded-full bg-amber-300 px-4 py-2 text-sm font-semibold text-stone-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:bg-stone-200"
            >
              {t('retrySelectedNode')}
            </button>
          </div>
        </div>
      </div>

      <div className="grid min-h-0 flex-1 gap-4 p-4 xl:grid-cols-[360px_minmax(0,1fr)]">
        <aside className="grid min-h-0 gap-4">
          <section className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-500">
              {t('timeline')}
            </h2>
            <div className="mt-4 space-y-3">
              {overview.timeline.map((item) => (
                <button
                  key={`${item.node_id}-${item.round_no}`}
                  type="button"
                  onClick={() => setSelectedNode({ node_id: item.node_id, round_no: item.round_no })}
                  className={`w-full rounded-3xl border px-4 py-4 text-left transition ${
                    selectedNode?.node_id === item.node_id && selectedNode.round_no === item.round_no
                      ? 'border-amber-400 bg-amber-50'
                      : 'border-stone-200 hover:border-stone-400'
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.18em] text-stone-500">{item.node_id}</p>
                      <p className="mt-1 text-sm font-medium text-stone-900">{t('round', { round: item.round_no })}</p>
                    </div>
                    <StatusBadge value={item.status} />
                  </div>
                  <p className="mt-3 text-xs text-stone-500">
                    {item.waiting_for_role ? t('waitingFor', { role: item.waiting_for_role }) : item.stop_reason || t('noStopReason')}
                  </p>
                </button>
              ))}
            </div>
          </section>

          <section className="rounded-[2rem] border border-stone-200 bg-stone-950 p-5 text-white shadow-sm">
            <p className="text-xs uppercase tracking-[0.24em] text-stone-400">{t('runHealth')}</p>
            <div className="mt-4 grid gap-3">
              <div className="rounded-3xl border border-white/10 bg-white/5 px-4 py-3">
                <p className="text-xs uppercase tracking-[0.18em] text-stone-400">{t('stopReason')}</p>
                <p className="mt-2 text-sm">{run.run.stop_reason || t('none')}</p>
              </div>
              <div className="rounded-3xl border border-white/10 bg-white/5 px-4 py-3">
                <p className="text-xs uppercase tracking-[0.18em] text-stone-400">{t('nodesInLatestState')}</p>
                <p className="mt-2 text-sm">{overview.latest_nodes.length}</p>
              </div>
            </div>
          </section>
        </aside>

        <section className="relative min-h-0 overflow-hidden rounded-[2rem] border border-stone-200 bg-white shadow-sm">
          <div className="border-b border-stone-200 px-5">
            <TabList tabs={tabs} activeTab={tabs[activeTabIndex]} onTabChange={(tab) => setActiveTabIndex(tabs.indexOf(tab))} />
          </div>

          <div className="h-[calc(100%-73px)] overflow-auto p-5">
            {activeTabIndex === 0 && (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {overview.latest_nodes.map((item) => (
                  <button
                    key={`${item.node_id}-${item.round_no}`}
                    type="button"
                    onClick={() => {
                      setSelectedNode({ node_id: item.node_id, round_no: item.round_no });
                      setInspectorData(item);
                    }}
                    className="rounded-[1.75rem] border border-stone-200 p-4 text-left transition hover:border-amber-500"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="font-semibold text-stone-900">{item.node_id}</h3>
                      <StatusBadge value={item.status} />
                    </div>
                    <p className="mt-3 text-sm text-stone-600">{t('round', { round: item.round_no })}</p>
                    <p className="mt-1 text-sm text-stone-500">{item.stop_reason || item.waiting_for_role || '-'}</p>
                  </button>
                ))}
              </div>
            )}

            {activeTabIndex === 1 && nodeRound && (
              <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
                <div className="space-y-4">
                  <div className="rounded-[1.75rem] border border-stone-200 bg-stone-50 p-5">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <p className="text-xs uppercase tracking-[0.18em] text-stone-500">
                          {nodeRound.node_id} round {nodeRound.round_no}
                        </p>
                        <p className="mt-2 text-sm text-stone-600">
                          {t('stopReasonLabel', { reason: nodeRound.stop_reason || '-' })}
                        </p>
                      </div>
                      <StatusBadge value={nodeRound.status} />
                    </div>
                    <button
                      type="button"
                      onClick={() => setInspectorData(nodeRound.context)}
                      className="mt-4 rounded-full border border-stone-300 px-4 py-2 text-sm text-stone-800 transition hover:border-stone-900"
                    >
                      {t('inspectRawContext')}
                    </button>
                  </div>

                  <div className="rounded-[1.75rem] border border-stone-200 bg-white p-5">
                    <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-stone-500">{t('callbacks')}</h3>
                    <div className="mt-4 space-y-3">
                      {nodeRound.callbacks.map((callback) => (
                        <button
                          key={callback.event_id}
                          type="button"
                          onClick={() => setInspectorData(callback)}
                          className="w-full rounded-3xl border border-stone-200 px-4 py-4 text-left transition hover:border-stone-400"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <div>
                              <p className="text-sm font-medium text-stone-900">{callback.event_id}</p>
                              <p className="mt-1 text-xs uppercase tracking-[0.18em] text-stone-500">
                                {callback.actor_role}
                                {callback.validator_id ? ` · ${callback.validator_id}` : ''}
                              </p>
                            </div>
                            <StatusBadge value={callback.execution_status || callback.verdict_status || 'reported'} />
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <aside className="space-y-4">
                  <div className="rounded-[1.75rem] border border-stone-200 bg-white p-5">
                    <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-stone-500">{t('artifacts')}</h3>
                    <div className="mt-4 space-y-3">
                      {nodeRound.artifacts.length === 0 ? (
                        <p className="text-sm text-stone-500">{t('noArtifactsInRound')}</p>
                      ) : (
                        nodeRound.artifacts.map((artifact) => (
                          <button
                            key={`${artifact.artifact_id}-${artifact.version}`}
                            type="button"
                            onClick={() => setInspectorData(artifact)}
                            className="w-full rounded-3xl border border-stone-200 px-4 py-4 text-left transition hover:border-stone-400"
                          >
                            <p className="text-sm font-medium text-stone-900">
                              {artifact.artifact_id}@{artifact.version}
                            </p>
                            <p className="mt-1 text-xs text-stone-500">{artifact.kind}</p>
                          </button>
                        ))
                      )}
                    </div>
                  </div>

                  <div className="rounded-[1.75rem] border border-stone-200 bg-white p-5">
                    <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-stone-500">{t('logRefs')}</h3>
                    <div className="mt-4 space-y-3">
                      {nodeRound.log_refs.length === 0 ? (
                        <p className="text-sm text-stone-500">{t('noLogsInRound')}</p>
                      ) : (
                        nodeRound.log_refs.map((ref) => (
                          <button
                            key={`${ref.kind}-${ref.path}`}
                            type="button"
                            onClick={() => setInspectorData(ref)}
                            className="w-full rounded-3xl border border-stone-200 px-4 py-4 text-left transition hover:border-stone-400"
                          >
                            <p className="text-sm font-medium text-stone-900">{ref.kind}</p>
                            <p className="mt-1 text-xs text-stone-500">{ref.path}</p>
                          </button>
                        ))
                      )}
                    </div>
                  </div>
                </aside>
              </div>
            )}

            {activeTabIndex === 2 && (
              <div className="space-y-3">
                {run.artifacts.length === 0 ? (
                  <p className="text-sm text-stone-500">{t('noArtifactsRegistered')}</p>
                ) : (
                  run.artifacts.map((artifact) => (
                    <button
                      key={`${artifact.artifact_id}-${artifact.version}`}
                      type="button"
                      onClick={() => setInspectorData(artifact)}
                      className="w-full rounded-[1.75rem] border border-stone-200 px-5 py-4 text-left transition hover:border-amber-500"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-medium text-stone-900">
                            {artifact.artifact_id}@{artifact.version}
                          </p>
                          <p className="mt-1 text-xs uppercase tracking-[0.18em] text-stone-500">
                            {artifact.kind}
                          </p>
                        </div>
                        <span className="text-xs text-stone-500">{artifact.storage_uri}</span>
                      </div>
                    </button>
                  ))
                )}
              </div>
            )}

            {activeTabIndex === 3 && (
              <div className="rounded-[1.75rem] border border-stone-200 bg-stone-950 p-5 text-sm text-stone-100">
                <pre className="overflow-auto whitespace-pre-wrap break-all">
                  {prettyJson({
                    run,
                    overview,
                    nodeRound,
                  })}
                </pre>
              </div>
            )}
          </div>
        </section>
      </div>

      {inspectorData !== null && (
        <InspectorPanel
          title={t('inspectorTitle')}
          data={inspectorData}
          onClose={() => setInspectorData(null)}
        />
      )}
    </div>
  );
}
