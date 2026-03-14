'use client';

import type { Node } from '@xyflow/react';
import Link from 'next/link';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { api } from '@/lib/api';
import type { RunOverview } from '@/lib/api';
import { prettyJson } from '@/lib/format';
import { formatStatusLabel as formatStatusText } from '@/lib/status';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { TabList } from '@/components/ui/TabList';
import { InspectorPanel } from '@/components/ui/InspectorPanel';
import { ClaudeTerminalPanel } from '@/components/claude/ClaudeTerminalPanel';
import { WorkflowGraph } from '@/components/workflow/WorkflowGraph';

const ATTENTION_STATUSES = new Set(['blocked', 'failed', 'timed_out', 'rework_limit', 'stopped']);
const ACTIVE_POLL_INTERVAL_MS = 1500;
const IDLE_POLL_INTERVAL_MS = 8000;

type DriveResult = {
  run_id: string;
  status: string;
  stop_reason: string;
  steps: Array<Record<string, unknown>>;
};

type PreviewPanelState =
  | { kind: 'artifact'; data: any }
  | { kind: 'log'; data: any };

type NodeSelection = {
  node_id: string;
  round_no: number;
};

type TimelineItem = RunOverview['timeline'][number];

export function RunDetailClient({ runId }: { runId: string }) {
  const t = useTranslations('runs');
  const tClaude = useTranslations('claudeTerminal');
  const tStatus = useTranslations('status');
  const queryClient = useQueryClient();
  const [detailTabIndex, setDetailTabIndex] = useState(0);
  const [selectedNode, setSelectedNode] = useState<NodeSelection | null>(null);
  const [inspectorData, setInspectorData] = useState<unknown>(null);
  const [driveMaxSteps, setDriveMaxSteps] = useState('100');
  const [driveResult, setDriveResult] = useState<DriveResult | null>(null);
  const [driveError, setDriveError] = useState<string | null>(null);
  const [previewState, setPreviewState] = useState<PreviewPanelState | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const runQuery = useQuery({
    queryKey: ['run', runId],
    queryFn: () => api.getRun(runId),
    refetchInterval: (query) =>
      ((query.state.data as { run?: { status?: string } } | undefined)?.run?.status === 'running')
        ? ACTIVE_POLL_INTERVAL_MS
        : IDLE_POLL_INTERVAL_MS,
  });

  const overviewQuery = useQuery({
    queryKey: ['run-overview', runId],
    queryFn: () => api.getRunOverview(runId),
    refetchInterval: (query) =>
      ((query.state.data as { status?: string } | undefined)?.status === 'running')
        ? ACTIVE_POLL_INTERVAL_MS
        : IDLE_POLL_INTERVAL_MS,
  });

  const workflowQuery = useQuery({
    queryKey: ['workflow', runQuery.data?.workflow.workflow_id, runQuery.data?.workflow.version],
    queryFn: () => api.getWorkflow(runQuery.data!.workflow.workflow_id, runQuery.data!.workflow.version),
    enabled: Boolean(runQuery.data?.workflow.workflow_id && runQuery.data?.workflow.version),
    staleTime: 60_000,
  });

  const nodeRoundQuery = useQuery({
    queryKey: ['run-node-round', runId, selectedNode?.node_id, selectedNode?.round_no],
    queryFn: () => api.getNodeRound(runId, selectedNode!.node_id, selectedNode!.round_no),
    enabled: Boolean(selectedNode),
    refetchInterval: () =>
      runQuery.data?.run.status === 'running' ? ACTIVE_POLL_INTERVAL_MS : IDLE_POLL_INTERVAL_MS,
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

  const driveMutation = useMutation({
    mutationFn: async () => {
      const parsed = Number.parseInt(driveMaxSteps, 10);
      if (Number.isNaN(parsed) || parsed <= 0) {
        throw new Error(t('drive.invalidSteps'));
      }
      return api.driveRun(runId, { max_steps: parsed });
    },
    onSuccess: async (payload) => {
      setDriveResult(payload);
      setDriveError(null);
      await refresh();
    },
    onError: (mutationError) => {
      setDriveError((mutationError as Error).message);
    },
  });

  const loadArtifactPreview = async (artifactId: string, version: string) => {
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const payload = await api.previewRunArtifact(runId, artifactId, version);
      setPreviewState({ kind: 'artifact', data: payload });
    } catch (mutationError) {
      setPreviewError((mutationError as Error).message);
    } finally {
      setPreviewLoading(false);
    }
  };

  const loadLogPreview = async (path: string) => {
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const payload = await api.previewRunLog(runId, path);
      setPreviewState({ kind: 'log', data: payload });
    } catch (mutationError) {
      setPreviewError((mutationError as Error).message);
    } finally {
      setPreviewLoading(false);
    }
  };

  const run = runQuery.data;
  const overview = overviewQuery.data;
  const workflowDetail = workflowQuery.data;
  const nodeRound = nodeRoundQuery.data;
  const detailTabKeys = ['terminal', 'artifacts', 'callbacks', 'raw'] as const;
  const detailTabs = detailTabKeys.map((key) => t(`detailTabs.${key}`));
  const timelineByNodeId = useMemo(() => {
    if (!overview) {
      return new Map<string, TimelineItem[]>();
    }
    const grouped = new Map<string, TimelineItem[]>();
    for (const item of overview.timeline) {
      const existing = grouped.get(item.node_id) || [];
      existing.push(item);
      grouped.set(item.node_id, existing);
    }
    for (const [nodeId, items] of grouped.entries()) {
      grouped.set(
        nodeId,
        [...items].sort((left, right) => {
          if (left.round_no !== right.round_no) {
            return right.round_no - left.round_no;
          }
          return (right.updated_at || right.created_at || '').localeCompare(left.updated_at || left.created_at || '');
        })
      );
    }
    return grouped;
  }, [overview?.timeline]);

  useEffect(() => {
    if (!overview) {
      return;
    }
    if (!selectedNode) {
      if (overview.current_focus) {
        setSelectedNode({ node_id: overview.current_focus.node_id, round_no: overview.current_focus.round_no });
        setDetailTabIndex(0);
        return;
      }
      if (overview.latest_nodes.length > 0) {
        setSelectedNode({
          node_id: overview.latest_nodes[0].node_id,
          round_no: overview.latest_nodes[0].round_no,
        });
      }
      return;
    }
    const selectedExists = overview.timeline.some(
      (item) => item.node_id === selectedNode.node_id && item.round_no === selectedNode.round_no
    );
    if (!selectedExists) {
      if (overview.current_focus) {
        setSelectedNode({ node_id: overview.current_focus.node_id, round_no: overview.current_focus.round_no });
        setDetailTabIndex(0);
      } else if (overview.latest_nodes.length > 0) {
        setSelectedNode({
          node_id: overview.latest_nodes[0].node_id,
          round_no: overview.latest_nodes[0].round_no,
        });
      } else {
        setSelectedNode(null);
      }
    }
  }, [overview, selectedNode]);

  if (!run || !overview || !workflowDetail) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-stone-500">
        {t('loading')}
      </div>
    );
  }

  const latestByNodeId = new Map(overview.latest_nodes.map((item) => [item.node_id, item]));
  const selectedLatest = selectedNode ? latestByNodeId.get(selectedNode.node_id) : null;
  const canRetry = selectedLatest ? ATTENTION_STATUSES.has(selectedLatest.status) : false;
  const driverRunning = overview.driver.status === 'running';
  const currentFocus = overview.current_focus;
  const currentFocusSelected =
    currentFocus?.node_id === selectedNode?.node_id && currentFocus?.round_no === selectedNode?.round_no;
  const canDrive =
    run.run.status !== 'completed' && run.run.status !== 'stopped' && !driverRunning;
  const previewPayload = previewState?.data?.preview;
  const previewTitle =
    previewState && previewState.kind === 'artifact'
      ? `${previewState.data.artifact_id}@${previewState.data.version}`
      : previewState?.data?.path ?? '';
  const previewSubtitle =
    previewState && previewState.kind === 'artifact'
      ? `${previewState.data.kind} · ${previewState.data.storage_uri}`
      : t('preview.logSubtitle');

  const claudeCalls = nodeRound?.claude_calls;
  const validatorCalls =
    claudeCalls?.validator_calls ||
    (currentFocusSelected ? currentFocus?.validator_calls || [] : []);
  const selectedNodeTimeline = selectedNode ? timelineByNodeId.get(selectedNode.node_id) || [] : [];

  const formatStatusLabel = (status: string | null | undefined) => {
    return formatStatusText(status, tStatus);
  };

  const describeNodeState = ({
    waiting_for_role,
    stop_reason,
    status,
  }: {
    waiting_for_role?: string | null;
    stop_reason?: string | null;
    status?: string | null;
  }) => {
    if (waiting_for_role) {
      return t('focus.waiting', { role: waiting_for_role });
    }
    if (stop_reason) {
      return stop_reason;
    }
    return formatStatusLabel(status);
  };

  const selectNodeRound = (selection: NodeSelection, resetTab = true) => {
    setSelectedNode((current) =>
      current?.node_id === selection.node_id && current.round_no === selection.round_no ? current : selection
    );
    if (resetTab) {
      setDetailTabIndex(0);
    }
  };

  const graphNodes = (workflowDetail.graph.nodes as Node[]).map((node) => {
    const nodeId =
      typeof node.data === 'object' && node.data && 'node_id' in node.data
        ? String((node.data as Record<string, unknown>).node_id)
        : node.id;
    const latest = latestByNodeId.get(nodeId);
    const isCurrent = currentFocus?.node_id === nodeId;
    const isSelected = selectedNode?.node_id === nodeId;
    const status = latest?.status;
    const background =
      status === 'completed' || status === 'passed'
        ? '#dcfce7'
        : status === 'running'
          ? '#e0f2fe'
          : status === 'waiting_executor'
            ? '#e0e7ff'
            : status === 'waiting_validator'
              ? '#ede9fe'
              : status === 'blocked' || status === 'failed' || status === 'timed_out'
                ? '#fee2e2'
                : '#fafaf9';

    return {
      ...node,
      style: {
        ...(node.style || {}),
        border: isCurrent ? '3px solid #d97706' : isSelected ? '3px solid #0f172a' : '1px solid #d6d3d1',
        borderRadius: 24,
        background,
        boxShadow: isCurrent ? '0 0 0 4px rgba(245, 158, 11, 0.16)' : '0 6px 24px rgba(15, 23, 42, 0.06)',
      },
      data: {
        ...(node.data || {}),
        label:
          typeof node.data === 'object' && node.data && 'label' in node.data
            ? `${String((node.data as Record<string, unknown>).label)}${
                latest ? `\n${t('round', { round: latest.round_no })} · ${formatStatusLabel(latest.status)}` : ''
              }`
            : nodeId,
      },
    };
  });

  const selectNode = (nodeId: string) => {
    const latest = latestByNodeId.get(nodeId);
    if (!latest) {
      return;
    }
    selectNodeRound({ node_id: latest.node_id, round_no: latest.round_no });
  };

  const jumpToCurrentFocus = () => {
    if (!currentFocus) {
      return;
    }
    selectNodeRound({ node_id: currentFocus.node_id, round_no: currentFocus.round_no });
  };

  const summaryDescription = currentFocus
    ? describeNodeState(currentFocus)
    : run.run.stop_reason || formatStatusLabel(run.run.status);
  const terminalHint =
    nodeRound?.waiting_for_role === 'executor' && !claudeCalls?.executor_call_id
      ? t('focus.queued')
      : nodeRound?.waiting_for_role === 'validator' && validatorCalls.length === 0
        ? t('detail.waitingValidator')
        : null;

  const renderPreviewContent = (preview: any) => {
    if (!preview) {
      return null;
    }
    if (preview.kind === 'json') {
      return (
        <pre className="whitespace-pre-wrap break-all text-xs leading-6 text-stone-900">
          {prettyJson(preview.content)}
        </pre>
      );
    }
    if (preview.kind === 'text') {
      return (
        <pre className="whitespace-pre-wrap break-all text-xs leading-6 text-stone-900">
          {preview.content}
        </pre>
      );
    }
    if (preview.kind === 'directory') {
      return (
        <div className="space-y-2 text-xs text-stone-700">
          <p>{t('preview.directory')}</p>
          <ul className="list-disc pl-4">
            {(preview.entries || []).map((entry: string) => (
              <li key={entry}>{entry}</li>
            ))}
          </ul>
        </div>
      );
    }
    return <p className="text-xs text-stone-700">{t('preview.binary')}</p>;
  };

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
          <StatusBadge value={run.run.status} />
        </div>
      </div>

      <div className="grid min-h-0 flex-1 gap-4 overflow-hidden p-4 xl:grid-cols-[320px_minmax(0,1fr)]">
        <aside className="grid min-h-0 gap-4">
          <section className="rounded-[2rem] border border-stone-200 bg-stone-950 p-5 text-white shadow-sm">
            <p className="text-xs uppercase tracking-[0.24em] text-stone-400">{t('summary.title')}</p>
            <div className="mt-4 grid gap-3">
              <div className="rounded-3xl border border-white/10 bg-white/5 px-4 py-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-stone-400">{t('summary.runStatus')}</p>
                    <p className="mt-2 text-sm text-white">{summaryDescription}</p>
                  </div>
                  <StatusBadge value={run.run.status} />
                </div>
              </div>
              <div className="rounded-3xl border border-white/10 bg-white/5 px-4 py-4">
                <p className="text-xs uppercase tracking-[0.18em] text-stone-400">{t('summary.currentNode')}</p>
                <p className="mt-2 text-sm text-white">{currentFocus?.node_id || t('focus.empty')}</p>
                <p className="mt-2 text-xs text-stone-300">
                  {currentFocus ? t('round', { round: currentFocus.round_no }) : run.run.stop_reason || t('none')}
                </p>
              </div>
              <div className="rounded-3xl border border-white/10 bg-white/5 px-4 py-4">
                <p className="text-xs uppercase tracking-[0.18em] text-stone-400">{t('summary.driver')}</p>
                <p className="mt-2 text-sm text-white">{t('driver.state', { status: overview.driver.status })}</p>
                <p className="mt-1 text-xs text-stone-300">
                  {overview.driver.mode ? t('driver.mode', { mode: overview.driver.mode }) : t('driver.idle')}
                </p>
              </div>
            </div>

            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => stopMutation.mutate()}
                className="rounded-full border border-white/20 px-4 py-2 text-sm font-medium text-white transition hover:border-white/50"
              >
                {t('stopRun')}
              </button>
              <button
                type="button"
                disabled={!canRetry}
                onClick={() => retryMutation.mutate()}
                className="rounded-full bg-amber-300 px-4 py-2 text-sm font-semibold text-stone-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:bg-stone-500 disabled:text-stone-200"
              >
                {t('retrySelectedNode')}
              </button>
              {currentFocus ? (
                <button
                  type="button"
                  onClick={jumpToCurrentFocus}
                  className="rounded-full border border-amber-300 px-4 py-2 text-sm font-semibold text-amber-200 transition hover:border-amber-200"
                >
                  {t('summary.viewCurrent')}
                </button>
              ) : null}
            </div>

            <details className="mt-5 rounded-3xl border border-white/10 bg-white/5 px-4 py-4">
              <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.18em] text-stone-300">
                {t('summary.advanced')}
              </summary>
              <p className="mt-3 text-xs text-stone-300">
                {driverRunning ? t('drive.runningDescription') : t('drive.description')}
              </p>
              <div className="mt-4">
                <label className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-300">
                  {t('drive.maxSteps')}
                </label>
                <input
                  className="mt-2 w-full rounded-2xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none"
                  value={driveMaxSteps}
                  onChange={(event) => setDriveMaxSteps(event.target.value)}
                  placeholder="100"
                />
              </div>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={() => driveMutation.mutate()}
                  disabled={!canDrive || driveMutation.isPending}
                  className="rounded-full bg-white px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-stone-950 transition hover:bg-stone-200 disabled:cursor-not-allowed disabled:bg-stone-400"
                >
                  {t('drive.button')}
                </button>
                {driveResult ? (
                  <button
                    type="button"
                    onClick={() => setInspectorData(driveResult)}
                    className="rounded-full border border-white/20 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-white transition hover:border-white/40"
                  >
                    {t('drive.inspect')}
                  </button>
                ) : null}
              </div>
              {driveResult ? (
                <div className="mt-4 rounded-[1.5rem] border border-white/10 bg-black/20 px-4 py-4 text-xs text-stone-200">
                  <p>{t('drive.result', { status: driveResult.status })}</p>
                  <p className="mt-1">{t('drive.stopReason', { reason: driveResult.stop_reason || t('none') })}</p>
                  <p className="mt-1">{t('drive.steps', { count: driveResult.steps.length })}</p>
                </div>
              ) : null}
              {driverRunning ? <p className="mt-3 text-xs text-stone-300">{t('drive.disabledWhileRunning')}</p> : null}
              {driveError ? <p className="mt-3 text-xs text-rose-300">{driveError}</p> : null}
            </details>
          </section>
        </aside>

        <section
          data-testid="run-detail-right-column"
          className="min-h-0 overflow-y-auto pr-1"
        >
          <div className="flex min-h-full flex-col gap-4">
          <section className="overflow-hidden rounded-[2rem] border border-stone-200 bg-white shadow-sm">
            <div className="border-b border-stone-200 px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-stone-500">{t('graph.title')}</p>
              <p className="mt-2 text-sm text-stone-600">{t('graph.description')}</p>
              <div className="mt-4 flex flex-wrap gap-2 text-xs text-stone-600">
                <span className="rounded-full bg-amber-100 px-3 py-1 text-amber-900">{t('graph.legend.current')}</span>
                <span className="rounded-full bg-sky-100 px-3 py-1 text-sky-900">{t('graph.legend.running')}</span>
                <span className="rounded-full bg-indigo-100 px-3 py-1 text-indigo-900">{t('graph.legend.waiting')}</span>
                <span className="rounded-full bg-emerald-100 px-3 py-1 text-emerald-900">{t('graph.legend.completed')}</span>
                <span className="rounded-full bg-rose-100 px-3 py-1 text-rose-900">{t('graph.legend.attention')}</span>
              </div>
            </div>
            <div className="h-[480px] bg-stone-50 xl:h-[520px]">
              <WorkflowGraph
                initialNodes={graphNodes}
                initialEdges={workflowDetail.graph.edges as any}
                onNodeClick={(_event, node) => selectNode(node.id)}
              />
            </div>
          </section>

          <section className="relative overflow-hidden rounded-[2rem] border border-stone-200 bg-white shadow-sm">
            <div className="border-b border-stone-200 px-5 py-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-stone-500">{t('detail.title')}</p>
                  {selectedNode ? (
                    <h2 className="mt-2 text-xl font-semibold text-stone-900">
                      {selectedNode.node_id} · {t('round', { round: selectedNode.round_no })}
                    </h2>
                  ) : (
                    <h2 className="mt-2 text-xl font-semibold text-stone-900">{t('detail.emptyTitle')}</h2>
                  )}
                  <p className="mt-2 text-sm text-stone-600">
                    {nodeRound ? describeNodeState(nodeRound) : t('detail.emptyDescription')}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  {selectedNodeTimeline.length > 1 ? (
                    <label className="text-sm text-stone-600">
                      <span className="mr-2">{t('detail.roundSelector')}</span>
                      <select
                        className="rounded-full border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900"
                        value={selectedNode?.round_no ?? ''}
                        onChange={(event) =>
                          selectedNode
                            ? selectNodeRound(
                                {
                                  node_id: selectedNode.node_id,
                                  round_no: Number.parseInt(event.target.value, 10),
                                },
                                false
                              )
                            : undefined
                        }
                      >
                        {selectedNodeTimeline.map((item) => (
                          <option key={`${item.node_id}-${item.round_no}`} value={item.round_no}>
                            {t('round', { round: item.round_no })} · {formatStatusLabel(item.status)}
                          </option>
                        ))}
                      </select>
                    </label>
                  ) : null}
                  {nodeRound ? <StatusBadge value={nodeRound.status} /> : null}
                </div>
              </div>
            </div>

            <div className="border-b border-stone-200 px-5">
              <TabList
                tabs={detailTabs}
                activeTab={detailTabs[detailTabIndex]}
                onTabChange={(tab) => setDetailTabIndex(detailTabs.indexOf(tab))}
              />
            </div>

            <div
              data-testid="node-detail-scroll-region"
              className="p-5 pb-6"
            >
              {!nodeRound ? (
                <div className="rounded-3xl border border-dashed border-stone-300 bg-stone-50 px-5 py-10 text-sm text-stone-500">
                  {t('detail.emptyDescription')}
                </div>
              ) : null}

              {nodeRound && detailTabIndex === 0 && (
                <div className="space-y-4">
                  {currentFocus && !currentFocusSelected ? (
                    <div className="flex flex-wrap items-center justify-between gap-3 rounded-[1.75rem] border border-stone-200 bg-stone-50 p-5">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">
                          {t('detail.viewingHistorical')}
                        </p>
                        <p className="mt-2 text-sm text-stone-700">
                          {currentFocus.node_id} · {t('round', { round: currentFocus.round_no })}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={jumpToCurrentFocus}
                        className="rounded-full border border-stone-300 px-4 py-2 text-sm font-medium text-stone-800 transition hover:border-stone-900"
                      >
                        {t('detail.returnToCurrent')}
                      </button>
                    </div>
                  ) : null}
                  {currentFocusSelected ? (
                    <div className="rounded-[1.75rem] border border-amber-200 bg-amber-50 p-5">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">
                        {t('focus.live')}
                      </p>
                      <p className="mt-2 text-sm text-stone-700">
                        {currentFocus ? describeNodeState(currentFocus) : t('detail.emptyDescription')}
                      </p>
                    </div>
                  ) : null}
                  {terminalHint ? (
                    <div className="rounded-[1.75rem] border border-stone-200 bg-stone-50 p-5 text-sm text-stone-700">
                      {terminalHint}
                    </div>
                  ) : null}
                  <ClaudeTerminalPanel
                    key={`${selectedNode?.node_id}-${selectedNode?.round_no}-executor`}
                    callId={
                      claudeCalls?.executor_call_id ||
                      (currentFocusSelected ? currentFocus?.executor_call_id : undefined)
                    }
                    title={tClaude('executorTitle')}
                    defaultOpen={Boolean(currentFocusSelected && currentFocus?.waiting_for_role === 'executor')}
                  />
                  {validatorCalls.map((item) => (
                    <ClaudeTerminalPanel
                      key={`${selectedNode?.node_id}-${selectedNode?.round_no}-${item.validator_id}`}
                      callId={item.call_id}
                      title={tClaude('validatorTitle', { id: item.validator_id })}
                      defaultOpen={Boolean(
                        currentFocusSelected &&
                          currentFocus?.waiting_for_role === 'validator' &&
                          currentFocus.validator_calls.some(
                            (currentItem) => currentItem.call_id === item.call_id
                          )
                      )}
                    />
                  ))}
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
                            onClick={() => loadLogPreview(ref.path)}
                            className="w-full rounded-3xl border border-stone-200 px-4 py-4 text-left transition hover:border-stone-400"
                          >
                            <p className="text-sm font-medium text-stone-900">{ref.kind}</p>
                            <p className="mt-1 text-xs text-stone-500">{ref.path}</p>
                          </button>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              )}

              {nodeRound && detailTabIndex === 1 && (
                <div className="space-y-3">
                  {nodeRound.artifacts.length === 0 ? (
                    <p className="text-sm text-stone-500">{t('noArtifactsInRound')}</p>
                  ) : (
                    nodeRound.artifacts.map((artifact) => (
                      <button
                        key={`${artifact.artifact_id}-${artifact.version}`}
                        type="button"
                        onClick={() => loadArtifactPreview(artifact.artifact_id, artifact.version)}
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

              {nodeRound && detailTabIndex === 2 && (
                <div className="space-y-3">
                  {nodeRound.callbacks.length === 0 ? (
                    <p className="text-sm text-stone-500">{t('callbacksEmpty')}</p>
                  ) : (
                    nodeRound.callbacks.map((callback) => (
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
                    ))
                  )}
                </div>
              )}

              {nodeRound && detailTabIndex === 3 && (
                <div className="space-y-4">
                  <button
                    type="button"
                    onClick={() => setInspectorData(nodeRound.context)}
                    className="rounded-full border border-stone-300 px-4 py-2 text-sm text-stone-800 transition hover:border-stone-900"
                  >
                    {t('inspectRawContext')}
                  </button>
                  <div className="rounded-[1.75rem] border border-stone-200 bg-stone-950 p-5 text-sm text-stone-100">
                    <pre className="overflow-auto whitespace-pre-wrap break-all">
                      {prettyJson({
                        run,
                        overview,
                        nodeRound,
                      })}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </section>
          {previewState ? (
            <section
              data-testid="run-detail-preview"
              className="rounded-[2rem] border border-stone-200 bg-white px-6 py-5 shadow-sm"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.24em] text-stone-500">{t('preview.title')}</p>
                  <h3 className="mt-2 text-lg font-semibold text-stone-900">{previewTitle}</h3>
                  <p className="mt-2 text-xs text-stone-500">{previewSubtitle}</p>
                </div>
                <button
                  type="button"
                  onClick={() => setPreviewState(null)}
                  className="rounded-full border border-stone-300 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-stone-700 transition hover:border-stone-500"
                >
                  {t('preview.close')}
                </button>
              </div>
              {previewLoading ? (
                <p className="mt-4 text-xs text-stone-500">{t('preview.loading')}</p>
              ) : previewError ? (
                <p className="mt-4 text-xs text-rose-700">{previewError}</p>
              ) : (
                <div className="mt-4 space-y-4">
                  {previewPayload?.truncated ? (
                    <p className="text-xs text-amber-700">
                      {t('preview.truncated', { limit: previewPayload.limit_bytes })}
                    </p>
                  ) : null}
                  <div className="rounded-[1.5rem] border border-stone-200 bg-stone-50 p-4">
                    {renderPreviewContent(previewPayload)}
                  </div>
                  {previewState.kind === 'artifact' ? (
                    <details className="rounded-[1.5rem] border border-stone-200 bg-white p-4">
                      <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.18em] text-stone-600">
                        {t('preview.manifest')}
                      </summary>
                      <pre className="mt-3 whitespace-pre-wrap break-all text-xs text-stone-700">
                        {prettyJson(previewState.data.manifest)}
                      </pre>
                    </details>
                  ) : null}
                  {previewPayload?.path ? (
                    <p className="text-xs text-stone-500">
                      {t('preview.path')}: {previewPayload.path}
                    </p>
                  ) : null}
                </div>
              )}
            </section>
          ) : null}
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
