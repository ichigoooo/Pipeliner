'use client';

import Link from 'next/link';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { formatTimestamp, prettyJson } from '@/lib/format';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { TabList } from '@/components/ui/TabList';
import { InspectorPanel } from '@/components/ui/InspectorPanel';

const ATTENTION_STATUSES = new Set(['blocked', 'failed', 'timed_out', 'rework_limit', 'stopped']);

export default function RunDetailPage({ params }: { params: { run_id: string } }) {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('Timeline');
  const [selectedNode, setSelectedNode] = useState<{ node_id: string; round_no: number } | null>(null);
  const [inspectorData, setInspectorData] = useState<unknown>(null);

  const runQuery = useQuery({
    queryKey: ['run', params.run_id],
    queryFn: () => api.getRun(params.run_id),
    refetchInterval: 8_000,
  });

  const overviewQuery = useQuery({
    queryKey: ['run-overview', params.run_id],
    queryFn: () => api.getRunOverview(params.run_id),
    refetchInterval: 8_000,
  });

  useEffect(() => {
    if (!selectedNode && overviewQuery.data?.latest_nodes.length) {
      const latest = overviewQuery.data.latest_nodes[0];
      setSelectedNode({ node_id: latest.node_id, round_no: latest.round_no });
    }
  }, [overviewQuery.data, selectedNode]);

  const nodeRoundQuery = useQuery({
    queryKey: ['run-node-round', params.run_id, selectedNode?.node_id, selectedNode?.round_no],
    queryFn: () => api.getNodeRound(params.run_id, selectedNode!.node_id, selectedNode!.round_no),
    enabled: Boolean(selectedNode),
    refetchInterval: 8_000,
  });

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['run', params.run_id] }),
      queryClient.invalidateQueries({ queryKey: ['run-overview', params.run_id] }),
      queryClient.invalidateQueries({ queryKey: ['run-node-round', params.run_id] }),
    ]);
  };

  const stopMutation = useMutation({
    mutationFn: () => api.stopRun(params.run_id),
    onSuccess: refresh,
  });

  const retryMutation = useMutation({
    mutationFn: () =>
      selectedNode
        ? api.retryNode(params.run_id, selectedNode.node_id, { reason: 'studio retry' })
        : Promise.reject(new Error('请先选择一个 attention node')),
    onSuccess: refresh,
  });

  const run = runQuery.data;
  const overview = overviewQuery.data;
  const nodeRound = nodeRoundQuery.data;
  const tabs = ['Timeline', 'Node Detail', 'Artifacts', 'Raw'];

  if (!run || !overview) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-stone-500">
        Loading run workspace...
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
          ← Back to runs
        </Link>
        <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-stone-500">Run workspace</p>
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
              Stop Run
            </button>
            <button
              type="button"
              disabled={!canRetry}
              onClick={() => retryMutation.mutate()}
              className="rounded-full bg-amber-300 px-4 py-2 text-sm font-semibold text-stone-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:bg-stone-200"
            >
              Retry Selected Node
            </button>
          </div>
        </div>
      </div>

      <div className="grid min-h-0 flex-1 gap-4 p-4 xl:grid-cols-[360px_minmax(0,1fr)]">
        <aside className="grid min-h-0 gap-4">
          <section className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-500">
              Timeline
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
                      <p className="mt-1 text-sm font-medium text-stone-900">Round {item.round_no}</p>
                    </div>
                    <StatusBadge value={item.status} />
                  </div>
                  <p className="mt-3 text-xs text-stone-500">
                    {item.waiting_for_role ? `Waiting ${item.waiting_for_role}` : item.stop_reason || 'No stop reason'}
                  </p>
                </button>
              ))}
            </div>
          </section>

          <section className="rounded-[2rem] border border-stone-200 bg-stone-950 p-5 text-white shadow-sm">
            <p className="text-xs uppercase tracking-[0.24em] text-stone-400">Run health</p>
            <div className="mt-4 grid gap-3">
              <div className="rounded-3xl border border-white/10 bg-white/5 px-4 py-3">
                <p className="text-xs uppercase tracking-[0.18em] text-stone-400">Stop reason</p>
                <p className="mt-2 text-sm">{run.run.stop_reason || 'None'}</p>
              </div>
              <div className="rounded-3xl border border-white/10 bg-white/5 px-4 py-3">
                <p className="text-xs uppercase tracking-[0.18em] text-stone-400">Nodes in latest state</p>
                <p className="mt-2 text-sm">{overview.latest_nodes.length}</p>
              </div>
            </div>
          </section>
        </aside>

        <section className="relative min-h-0 overflow-hidden rounded-[2rem] border border-stone-200 bg-white shadow-sm">
          <div className="border-b border-stone-200 px-5">
            <TabList tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />
          </div>

          <div className="h-[calc(100%-73px)] overflow-auto p-5">
            {activeTab === 'Timeline' && (
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
                    <p className="mt-3 text-sm text-stone-600">Round {item.round_no}</p>
                    <p className="mt-1 text-sm text-stone-500">{item.stop_reason || item.waiting_for_role || '-'}</p>
                  </button>
                ))}
              </div>
            )}

            {activeTab === 'Node Detail' && nodeRound && (
              <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
                <div className="space-y-4">
                  <div className="rounded-[1.75rem] border border-stone-200 bg-stone-50 p-5">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <p className="text-xs uppercase tracking-[0.18em] text-stone-500">
                          {nodeRound.node_id} round {nodeRound.round_no}
                        </p>
                        <p className="mt-2 text-sm text-stone-600">
                          Stop reason: {nodeRound.stop_reason || '-'}
                        </p>
                      </div>
                      <StatusBadge value={nodeRound.status} />
                    </div>
                    <button
                      type="button"
                      onClick={() => setInspectorData(nodeRound.context)}
                      className="mt-4 rounded-full border border-stone-300 px-4 py-2 text-sm text-stone-800 transition hover:border-stone-900"
                    >
                      Inspect raw context
                    </button>
                  </div>

                  <div className="rounded-[1.75rem] border border-stone-200 p-5">
                    <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-stone-500">
                      Callbacks
                    </h3>
                    <div className="mt-4 space-y-3">
                      {nodeRound.callbacks.map((callback) => (
                        <button
                          key={callback.event_id}
                          type="button"
                          onClick={() => setInspectorData(callback.payload)}
                          className="w-full rounded-3xl border border-stone-200 px-4 py-3 text-left transition hover:border-amber-500"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <span className="text-sm font-medium text-stone-900">{callback.event_id}</span>
                            <StatusBadge value={callback.verdict_status || callback.execution_status} />
                          </div>
                          <p className="mt-2 text-xs uppercase tracking-[0.18em] text-stone-500">
                            {callback.actor_role} {callback.validator_id ? `· ${callback.validator_id}` : ''}
                          </p>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="rounded-[1.75rem] border border-stone-200 p-5">
                    <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-stone-500">
                      Artifacts
                    </h3>
                    <div className="mt-4 space-y-3">
                      {nodeRound.artifacts.map((artifact) => (
                        <button
                          key={`${artifact.artifact_id}-${artifact.version}`}
                          type="button"
                          onClick={() => setInspectorData(artifact)}
                          className="w-full rounded-3xl border border-stone-200 px-4 py-3 text-left transition hover:border-amber-500"
                        >
                          <p className="font-medium text-stone-900">
                            {artifact.artifact_id}@{artifact.version}
                          </p>
                          <p className="mt-2 text-sm text-stone-500">{artifact.storage_uri}</p>
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="rounded-[1.75rem] border border-stone-200 p-5">
                    <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-stone-500">
                      Log References
                    </h3>
                    <div className="mt-4 space-y-2 text-sm text-stone-600">
                      {nodeRound.log_refs.map((item) => (
                        <button
                          key={item.path}
                          type="button"
                          onClick={() => setInspectorData(item)}
                          className="block w-full rounded-2xl bg-stone-50 px-3 py-2 text-left transition hover:bg-amber-50"
                        >
                          {item.path}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'Artifacts' && (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {run.artifacts.map((artifact) => (
                  <button
                    key={`${artifact.artifact_id}-${artifact.version}-${artifact.node_id}-${artifact.round_no}`}
                    type="button"
                    onClick={() => setInspectorData(artifact)}
                    className="rounded-[1.75rem] border border-stone-200 p-4 text-left transition hover:border-amber-500"
                  >
                    <p className="text-xs uppercase tracking-[0.18em] text-stone-500">
                      {artifact.node_id} round {artifact.round_no}
                    </p>
                    <h3 className="mt-2 font-semibold text-stone-900">
                      {artifact.artifact_id}@{artifact.version}
                    </h3>
                    <p className="mt-3 text-sm text-stone-600">{artifact.storage_uri}</p>
                  </button>
                ))}
              </div>
            )}

            {activeTab === 'Raw' && (
              <pre className="overflow-auto rounded-[1.75rem] bg-stone-950 p-5 text-xs leading-6 text-stone-100">
                {prettyJson({ run, overview, nodeRound })}
              </pre>
            )}
          </div>

          {inspectorData ? (
            <div className="absolute inset-y-0 right-0 z-10 border-l border-stone-200 shadow-lg">
              <InspectorPanel
                title="Run Inspector"
                data={inspectorData}
                onClose={() => setInspectorData(null)}
              />
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
