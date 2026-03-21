'use client';
import type { Node } from '@xyflow/react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { api } from '@/lib/api';
import type { RunOverview } from '@/lib/api';
import { formatTimestamp, prettyJson } from '@/lib/format';
import { formatRunStopReason } from '@/lib/run-stop-reason';
import { formatStatusLabel as formatStatusText } from '@/lib/status';
import { AdaptiveButtonLabel } from '@/components/ui/AdaptiveButtonLabel';
import { HelpTooltip } from '@/components/ui/HelpTooltip';
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
type DispatchableAction = RunOverview['dispatchable'][number];

export function RunDetailClient({ runId }: { runId: string }) {
  const t = useTranslations('runs');
  const tClaude = useTranslations('claudeTerminal');
  const tStatus = useTranslations('status');
  const router = useRouter();
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const focusParam = searchParams?.get('focus') ?? null;
  const [focusApplied, setFocusApplied] = useState(false);
  const [followCurrentFocus, setFollowCurrentFocus] = useState(true);
  const [detailTabIndex, setDetailTabIndex] = useState(0);
  const [selectedNode, setSelectedNode] = useState<NodeSelection | null>(null);
  const [inspectorData, setInspectorData] = useState<unknown>(null);
  const [driveMaxSteps, setDriveMaxSteps] = useState('100');
  const [driveResult, setDriveResult] = useState<DriveResult | null>(null);
  const [driveError, setDriveError] = useState<string | null>(null);
  const [previewState, setPreviewState] = useState<PreviewPanelState | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [artifactActionMessage, setArtifactActionMessage] = useState<string | null>(null);
  const [artifactActionError, setArtifactActionError] = useState<string | null>(null);
  const [primaryActionError, setPrimaryActionError] = useState<string | null>(null);
  const [dispatchingKey, setDispatchingKey] = useState<string | null>(null);
  const [dispatchError, setDispatchError] = useState<string | null>(null);

  const runQuery = useQuery({
    queryKey: ['run', runId],
    queryFn: () => api.getRun(runId),
    retry: false,
    refetchInterval: (query) =>
      query.state.error
        ? false
        : ((query.state.data as { run?: { status?: string } } | undefined)?.run?.status === 'running')
        ? ACTIVE_POLL_INTERVAL_MS
        : IDLE_POLL_INTERVAL_MS,
  });

  const overviewQuery = useQuery({
    queryKey: ['run-overview', runId],
    queryFn: () => api.getRunOverview(runId),
    retry: false,
    refetchInterval: (query) =>
      query.state.error
        ? false
        : ((query.state.data as { status?: string } | undefined)?.status === 'running')
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
    retry: false,
    refetchInterval: () =>
      runQuery.error
        ? false
        : runQuery.data?.run.status === 'running'
          ? ACTIVE_POLL_INTERVAL_MS
          : IDLE_POLL_INTERVAL_MS,
  });

  const executorCallId = nodeRoundQuery.data?.claude_calls?.executor_call_id || null;
  const executorCallQuery = useQuery({
    queryKey: ['claude-call-meta', executorCallId],
    queryFn: () => api.getClaudeCall(executorCallId!),
    enabled: Boolean(executorCallId),
    retry: false,
    refetchInterval: (query) => {
      const status = (query.state.data as { status?: string } | undefined)?.status;
      return status === 'running' || !status ? ACTIVE_POLL_INTERVAL_MS : false;
    },
  });
  const activeValidatorCallId =
    nodeRoundQuery.data?.waiting_for_role === 'validator'
      ? nodeRoundQuery.data?.claude_calls?.validator_calls?.[0]?.call_id || null
      : null;
  const validatorCallQuery = useQuery({
    queryKey: ['claude-call-meta', activeValidatorCallId],
    queryFn: () => api.getClaudeCall(activeValidatorCallId!),
    enabled: Boolean(activeValidatorCallId),
    retry: false,
    refetchInterval: (query) => {
      const status = (query.state.data as { status?: string } | undefined)?.status;
      return status === 'running' || !status ? ACTIVE_POLL_INTERVAL_MS : false;
    },
  });

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['run', runId] }),
      queryClient.invalidateQueries({ queryKey: ['run-overview', runId] }),
      queryClient.invalidateQueries({ queryKey: ['run-node-round', runId] }),
    ]);
  };

  const refetchPage = async () => {
    await Promise.all([
      runQuery.refetch(),
      overviewQuery.refetch(),
      workflowQuery.refetch(),
      nodeRoundQuery.refetch(),
    ]);
  };

  const stopMutation = useMutation({
    mutationFn: () => api.stopRun(runId),
    onSuccess: refresh,
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteRun(runId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['runs'] }),
        queryClient.invalidateQueries({ queryKey: ['attention-runs'] }),
      ]);
      router.push('/runs');
    },
    onError: (mutationError) => {
      setPrimaryActionError((mutationError as Error).message);
    },
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

  const primaryActionMutation = useMutation({
    mutationFn: async () => {
      const parsed = Number.parseInt(driveMaxSteps, 10);
      const maxSteps = Number.isNaN(parsed) || parsed <= 0 ? 100 : parsed;
      const latest = selectedNode ? overview?.latest_nodes.find((item) => item.node_id === selectedNode.node_id) : null;
      const viewingHistoricalRound = Boolean(
        latest && selectedNode && latest.round_no !== selectedNode.round_no
      );
      const selectedActions = selectedNode
        ? (overview?.dispatchable || []).filter(
            (action) => action.node_id === selectedNode.node_id && action.round_no === selectedNode.round_no
          )
        : [];
      const executorAction = selectedActions.find((action) => action.kind === 'executor');
      const validatorAction = selectedActions.find(
        (action) => action.kind === 'validator' && action.validator_id
      );

      if (viewingHistoricalRound && latest) {
        return {
          kind: 'jump' as const,
          selection: { node_id: latest.node_id, round_no: latest.round_no },
        };
      }

      if (selectedNode && selectedLatest && ATTENTION_STATUSES.has(selectedLatest.status)) {
        await api.retryNode(runId, selectedNode.node_id, { reason: 'studio retry' });
        const driveResult = await api.driveRun(runId, { max_steps: maxSteps });
        return { kind: 'drive' as const, driveResult };
      }

      if (executorAction) {
        await api.dispatchExecutor(runId, executorAction.node_id, { round_no: executorAction.round_no });
        return { kind: 'dispatch' as const };
      }

      if (validatorAction && validatorAction.validator_id) {
        await api.dispatchValidator(runId, validatorAction.node_id, validatorAction.validator_id, {
          round_no: validatorAction.round_no,
        });
        return { kind: 'dispatch' as const };
      }

      if ((overview?.dispatchable || []).length > 0) {
        const driveResult = await api.driveRun(runId, { max_steps: maxSteps });
        return { kind: 'drive' as const, driveResult };
      }

      return { kind: 'noop' as const };
    },
    onSuccess: async (payload) => {
      setPrimaryActionError(null);
      if (payload.kind === 'jump') {
        selectNodeRound(payload.selection);
        return;
      }
      if (payload.kind === 'drive') {
        setDriveResult(payload.driveResult);
        setDriveError(null);
      }
      await refresh();
    },
    onError: (mutationError) => {
      setPrimaryActionError((mutationError as Error).message);
    },
  });

  const loadArtifactPreview = async (artifactId: string, version: string) => {
    setArtifactActionMessage(null);
    setArtifactActionError(null);
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
    setArtifactActionMessage(null);
    setArtifactActionError(null);
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

  const openArtifactFolder = async (artifactId: string, version: string) => {
    setArtifactActionMessage(null);
    setArtifactActionError(null);
    try {
      const payload = await api.openRunArtifactFolder(runId, artifactId, version);
      setArtifactActionMessage(t('artifactActions.opened', { path: payload.opened_path }));
    } catch (mutationError) {
      setArtifactActionError((mutationError as Error).message);
    }
  };

  const copyArtifactUri = async (value: string) => {
    setArtifactActionMessage(null);
    setArtifactActionError(null);
    try {
      await navigator.clipboard.writeText(value);
      setArtifactActionMessage(t('artifactActions.copied', { value }));
    } catch (mutationError) {
      setArtifactActionError((mutationError as Error).message);
    }
  };

  const dispatchAction = async (action: RunOverview['dispatchable'][number]) => {
    const key = `${action.kind}:${action.node_id}:${action.round_no}:${action.validator_id || ''}`;
    setDispatchError(null);
    setDispatchingKey(key);
    try {
      if (action.kind === 'executor') {
        await api.dispatchExecutor(runId, action.node_id, { round_no: action.round_no });
      } else if (action.validator_id) {
        await api.dispatchValidator(runId, action.node_id, action.validator_id, { round_no: action.round_no });
      } else {
        throw new Error('validator_id missing');
      }
      await refresh();
    } catch (mutationError) {
      setDispatchError((mutationError as Error).message);
    } finally {
      setDispatchingKey(null);
    }
  };

  const applyNodeSelection = (
    selection: NodeSelection,
    options?: { resetTab?: boolean; followCurrentFocus?: boolean }
  ) => {
    const resetTab = options?.resetTab ?? true;
    setSelectedNode((current) =>
      current?.node_id === selection.node_id && current.round_no === selection.round_no ? current : selection
    );
    if (options?.followCurrentFocus !== undefined) {
      setFollowCurrentFocus(options.followCurrentFocus);
    }
    if (resetTab) {
      setDetailTabIndex(0);
    }
  };

  const selectNodeRound = (selection: NodeSelection, resetTab = true) => {
    applyNodeSelection(selection, { resetTab });
  };

  const selectNodeRoundManually = (selection: NodeSelection, resetTab = true) => {
    applyNodeSelection(selection, { resetTab, followCurrentFocus: false });
  };

  const run = runQuery.data;
  const overview = overviewQuery.data;
  const workflowDetail = workflowQuery.data;
  const nodeRound = nodeRoundQuery.data;
  const executorCallMeta = executorCallQuery.data;
  const validatorCallMeta = validatorCallQuery.data;
  const pageLoadError = (runQuery.error || overviewQuery.error || workflowQuery.error) as Error | null;
  const nodeDetailError = nodeRoundQuery.error as Error | null;
  const detailTabKeys = ['overview', 'artifacts'] as const;
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
    const defaultSelection = overview.current_focus
      ? { node_id: overview.current_focus.node_id, round_no: overview.current_focus.round_no }
      : overview.latest_nodes.length > 0
        ? {
            node_id: overview.latest_nodes[0].node_id,
            round_no: overview.latest_nodes[0].round_no,
          }
        : null;
    if (!selectedNode) {
      if (defaultSelection) {
        applyNodeSelection(defaultSelection, { followCurrentFocus });
      }
      return;
    }
    if (
      followCurrentFocus &&
      defaultSelection &&
      (selectedNode.node_id !== defaultSelection.node_id || selectedNode.round_no !== defaultSelection.round_no)
    ) {
      applyNodeSelection(defaultSelection, { followCurrentFocus: true });
      return;
    }
    const selectedExists = overview.timeline.some(
      (item) => item.node_id === selectedNode.node_id && item.round_no === selectedNode.round_no
    );
    if (!selectedExists) {
      if (defaultSelection) {
        applyNodeSelection(defaultSelection, { followCurrentFocus });
      } else {
        setSelectedNode(null);
      }
    }
  }, [followCurrentFocus, overview, selectedNode]);

  useEffect(() => {
    if (!overview || focusApplied || focusParam !== 'attention') {
      return;
    }
    const attention = overview.summary?.attention_nodes || [];
    if (attention.length > 0) {
      selectNodeRoundManually({ node_id: attention[0].node_id, round_no: attention[0].round_no });
      setFocusApplied(true);
    }
  }, [focusApplied, focusParam, overview]);

  useEffect(() => {
    if (!executorCallMeta || !nodeRound) {
      return;
    }
    if (
      nodeRound.waiting_for_role === 'executor' &&
      (executorCallMeta.status === 'completed' || executorCallMeta.status === 'failed')
    ) {
      void refresh();
    }
  }, [executorCallMeta, nodeRound, refresh]);

  useEffect(() => {
    if (!validatorCallMeta || !nodeRound) {
      return;
    }
    if (
      nodeRound.waiting_for_role === 'validator' &&
      (validatorCallMeta.status === 'completed' || validatorCallMeta.status === 'failed')
    ) {
      void refresh();
    }
  }, [nodeRound, refresh, validatorCallMeta]);

  if (pageLoadError && (!run || !overview || !workflowDetail)) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="w-full max-w-xl rounded-[2rem] border border-rose-200 bg-white p-6 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-rose-700">
            {t('connectionIssueTitle')}
          </p>
          <p className="mt-3 text-sm leading-6 text-stone-700">{t('connectionIssueHint')}</p>
          <p className="mt-3 rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-800">
            {pageLoadError.message}
          </p>
          <button
            type="button"
            onClick={() => void refetchPage()}
            className="mt-4 rounded-full border border-stone-300 px-4 py-2 text-sm font-medium text-stone-800 transition hover:border-stone-900"
          >
            {t('retryLoad')}
          </button>
        </div>
      </div>
    );
  }
  if (!run || !overview || !workflowDetail) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-stone-500">
        {t('loading')}
      </div>
    );
  }

  const dispatchable = overview.dispatchable || [];  
  const summary = overview.summary || { node_counts: {}, attention_nodes: [] };  
  const attentionNodes = summary.attention_nodes;  
  const nodeCounts = summary.node_counts;  

  const latestByNodeId = new Map(overview.latest_nodes.map((item) => [item.node_id, item]));
  const selectedLatest = selectedNode ? latestByNodeId.get(selectedNode.node_id) : null;
  const selectedDispatchable = selectedNode
    ? dispatchable.filter(
        (action) => action.node_id === selectedNode.node_id && action.round_no === selectedNode.round_no
      )
    : [];
  const selectedExecutorAction = selectedDispatchable.find((action) => action.kind === 'executor');
  const selectedValidatorActions = selectedDispatchable.filter(
    (action) => action.kind === 'validator' && action.validator_id
  );
  const viewingHistoricalRound = Boolean(
    selectedNode && selectedLatest && selectedNode.round_no !== selectedLatest.round_no
  );
  const canRetry = selectedLatest ? ATTENTION_STATUSES.has(selectedLatest.status) : false;
  const driverRunning = overview.driver.status === 'running';
  const currentFocus = overview.current_focus;
  const currentFocusSelected =
    currentFocus?.node_id === selectedNode?.node_id && currentFocus?.round_no === selectedNode?.round_no;
  const canDrive =
    run.run.status !== 'completed' && run.run.status !== 'stopped' && !driverRunning;
  const likelyStalled = run.run.status === 'running' && overview.driver.status === 'idle';
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

  const formatBytes = (value: number | null | undefined) => {
    if (value === null || value === undefined) {
      return null;
    }
    if (value < 1024) {
      return `${value} B`;
    }
    if (value < 1024 * 1024) {
      return `${(value / 1024).toFixed(1)} KB`;
    }
    if (value < 1024 * 1024 * 1024) {
      return `${(value / 1024 / 1024).toFixed(1)} MB`;
    }
    return `${(value / 1024 / 1024 / 1024).toFixed(1)} GB`;
  };

  const buildLogMeta = (ref: { size_bytes?: number | null; updated_at?: string | null }) => {
    const sizeLabel = formatBytes(ref.size_bytes);
    if (sizeLabel && ref.updated_at) {
      return t('logMeta', { size: sizeLabel, time: formatTimestamp(ref.updated_at) });
    }
    if (sizeLabel) {
      return t('logMeta', { size: sizeLabel, time: '-' });
    }
    return t('logMetaMissing');
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
      return formatRunStopReason(stop_reason, t) || stop_reason;
    }
    return formatStatusLabel(status);
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
    selectNodeRoundManually({ node_id: latest.node_id, round_no: latest.round_no });
  };

  const jumpToCurrentFocus = () => {
    if (!currentFocus) {
      return;
    }
    applyNodeSelection(
      { node_id: currentFocus.node_id, round_no: currentFocus.round_no },
      { followCurrentFocus: true }
    );
  };

  const formattedRunStopReason = formatRunStopReason(run.run.stop_reason, t);
  const summaryDescription = currentFocus
    ? describeNodeState(currentFocus)
    : formattedRunStopReason || formatStatusLabel(run.run.status);
  const terminalHint =
    nodeRound?.waiting_for_role === 'executor' && !claudeCalls?.executor_call_id
      ? t('focus.queued')
      : nodeRound?.waiting_for_role === 'validator' && validatorCalls.length === 0
        ? t('detail.waitingValidator')
        : null;
  const executorTerminalEmptyHint =
    nodeRound?.waiting_for_role === 'executor' && !claudeCalls?.executor_call_id
      ? t('detail.executorNotStarted')
      : undefined;
  const executorActivityHint = (() => {
    if (nodeRound?.waiting_for_role !== 'executor') {
      return null;
    }
    if (!executorCallMeta) {
      return executorTerminalEmptyHint || null;
    }
    if (executorCallMeta.status === 'running' && executorCallMeta.bytes_written > 0) {
      return t('detail.executorStreaming');
    }
    if (executorCallMeta.status === 'running') {
      return t('detail.executorStartedNoOutput', {
        time: formatTimestamp(executorCallMeta.started_at),
      });
    }
    if (executorCallMeta.status === 'completed') {
      return t('detail.executorFinishedSyncing');
    }
    if (executorCallMeta.status === 'failed') {
      return t('detail.executorFailedSyncing');
    }
    return executorTerminalEmptyHint || null;
  })();
  const slowStartMeta =
    nodeRound?.waiting_for_role === 'executor'
      ? executorCallMeta
      : nodeRound?.waiting_for_role === 'validator'
        ? validatorCallMeta
        : null;
  const slowStartHint =
    slowStartMeta?.status === 'running' &&
    Boolean(slowStartMeta?.slow_start_detected) &&
    (slowStartMeta?.bytes_written ?? 0) === 0
      ? t('detail.slowStartWarning', {
          role: nodeRound?.waiting_for_role || 'executor',
          time: formatTimestamp(slowStartMeta?.slow_start_at || slowStartMeta?.started_at),
        })
      : null;
  const primaryAction = (() => {
    if (viewingHistoricalRound && selectedLatest) {
      return {
        label: t('actions.returnToLatest'),
        hint: t('actions.returnToLatestHint'),
        disabled: false,
      };
    }
    if (driverRunning) {
      return {
        label: t('actions.running'),
        hint: t('actions.runningHint'),
        disabled: true,
      };
    }
    if (canRetry && selectedNode) {
      return {
        label: t('actions.retryAndRun'),
        hint: t('actions.retryAndRunHint'),
        disabled: false,
      };
    }
    if (selectedExecutorAction) {
      return {
        label: t('actions.startExecution'),
        hint: t('actions.startExecutionHint'),
        disabled: false,
      };
    }
    if (selectedValidatorActions.length === 1) {
      return {
        label: t('actions.startValidation'),
        hint: t('actions.startValidationHint'),
        disabled: false,
      };
    }
    if (dispatchable.length > 0 && canDrive) {
      return {
        label: t('actions.continueRun'),
        hint: t('actions.continueRunHint'),
        disabled: false,
      };
    }
    if (run.run.status === 'completed') {
      return {
        label: t('actions.completed'),
        hint: t('actions.completedHint'),
        disabled: true,
      };
    }
    if (run.run.status === 'stopped') {
      return {
        label: t('actions.stopped'),
        hint: t('actions.stoppedHint'),
        disabled: true,
      };
    }
    return {
      label: t('actions.none'),
      hint: t('actions.noneHint'),
      disabled: true,
    };
  })();
  const showStopButton = run.run.status === 'running' || run.run.status === 'needs_attention';
  const showDeleteButton = run.run.status !== 'running';
  const showJumpToCurrentFocus = Boolean(currentFocus && !currentFocusSelected && !followCurrentFocus);
  const showTechnicalOutput = Boolean(
    claudeCalls?.executor_call_id || validatorCalls.length > 0 || executorTerminalEmptyHint
  );

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
        <div className="flex flex-wrap items-center gap-4 text-sm font-medium">
          <Link href="/runs" className="text-stone-500 transition hover:text-stone-900">
            ← {t('backToRuns')}
          </Link>
          {run.run.batch_id ? (
            <Link
              href={`/runs/batches/${run.run.batch_id}`}
              className="text-stone-500 transition hover:text-stone-900"
            >
              {t('viewBatch')}
            </Link>
          ) : null}
        </div>
        <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-stone-500">{t('workspace')}</p>
            <h1 className="mt-2 text-3xl font-semibold text-stone-500">{run.run.id}</h1>
            <p className="mt-3 text-sm leading-6 text-stone-600">
              {run.workflow.workflow_id}@{run.workflow.version} · workspace {run.run.workspace_root}
            </p>
          </div>
          <StatusBadge value={run.run.status} />
        </div>
      </div>

      <div className="grid min-h-0 flex-1 gap-4 overflow-hidden p-4 xl:grid-cols-[320px_minmax(0,1fr)]">
        <aside className="grid min-h-0 gap-4 overflow-y-auto">
          <section className="rounded-[2rem] border border-stone-200 bg-stone-950 p-5 text-white shadow-sm">
            <p className="text-xs uppercase tracking-[0.24em] text-stone-400">{t('summary.title')}</p>
            <div className="mt-4 rounded-3xl border border-white/10 bg-white/5 px-4 py-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.18em] text-stone-400">{t('summary.runStatus')}</p>
                  <p className="mt-2 text-sm leading-6 text-white">{summaryDescription}</p>
                </div>
                <StatusBadge value={run.run.status} />
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.18em] text-stone-400">{t('summary.currentNode')}</p>
                  <p className="mt-1 text-sm text-white">{selectedNode?.node_id || currentFocus?.node_id || t('focus.empty')}</p>
                  <p className="mt-1 text-xs text-stone-300">
                    {selectedNode ? t('round', { round: selectedNode.round_no }) : currentFocus ? t('round', { round: currentFocus.round_no }) : t('none')}
                  </p>
                </div>
                <div>
                  <p className="text-[11px] uppercase tracking-[0.18em] text-stone-400">{t('summary.driver')}</p>
                  <p className="mt-1 text-sm text-white">{t('driver.state', { status: overview.driver.status })}</p>
                  <p className="mt-1 text-xs text-stone-300">
                    {overview.driver.mode ? t('driver.mode', { mode: overview.driver.mode }) : t('driver.idle')}
                  </p>
                </div>
              </div>
            </div>

            {formattedRunStopReason ? (
              <div className="mt-4 rounded-3xl border border-amber-300/30 bg-amber-200/10 px-4 py-4">
                <p className="text-xs uppercase tracking-[0.18em] text-amber-200">{t('stopReason')}</p>
                <p className="mt-2 text-sm leading-6 text-amber-50">{formattedRunStopReason}</p>
              </div>
            ) : null}

            {likelyStalled ? (
              <div className="mt-4 rounded-3xl border border-amber-300/30 bg-amber-200/10 px-4 py-4">
                <p className="text-xs uppercase tracking-[0.18em] text-amber-200">{t('summary.driver')}</p>
                <p className="mt-2 text-sm leading-6 text-amber-50">{t('driver.stalledHint')}</p>
              </div>
            ) : null}
          </section>

          <section className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
            <p className="text-xs uppercase tracking-[0.22em] text-stone-500">{t('actions.title')}</p>
            <p className="mt-2 text-sm text-stone-600">{primaryAction.hint}</p>
            <button
              type="button"
              disabled={primaryAction.disabled || primaryActionMutation.isPending}
              onClick={() => primaryActionMutation.mutate()}
              className="mt-4 inline-flex w-full min-w-0 items-center justify-center overflow-hidden rounded-full bg-amber-300 px-4 py-3 font-semibold text-stone-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:bg-stone-200 disabled:text-stone-500"
            >
              <AdaptiveButtonLabel
                text={primaryActionMutation.isPending ? t('actions.loading') : primaryAction.label}
              />
            </button>
            <div className="mt-4 flex flex-wrap gap-3">
              {showStopButton ? (
                <button
                  type="button"
                  onClick={() => stopMutation.mutate()}
                  className="inline-flex min-w-0 max-w-full items-center justify-center overflow-hidden rounded-full border border-stone-300 px-4 py-2 font-medium text-stone-800 transition hover:border-stone-900"
                >
                  <AdaptiveButtonLabel text={t('stopRun')} />
                </button>
              ) : null}
              {showDeleteButton ? (
                <button
                  type="button"
                  onClick={() => {
                    if (!window.confirm(t('deleteConfirm'))) {
                      return;
                    }
                    deleteMutation.mutate();
                  }}
                  disabled={deleteMutation.isPending}
                  className="inline-flex min-w-0 max-w-full items-center justify-center overflow-hidden rounded-full border border-rose-200 px-4 py-2 font-medium text-rose-800 transition hover:border-rose-400 disabled:cursor-not-allowed disabled:border-stone-200 disabled:text-stone-400"
                >
                  <AdaptiveButtonLabel
                    text={deleteMutation.isPending ? t('actions.loading') : t('deleteRun')}
                  />
                </button>
              ) : null}
              {showJumpToCurrentFocus ? (
                <button
                  type="button"
                  onClick={jumpToCurrentFocus}
                  className="inline-flex min-w-0 max-w-full items-center justify-center overflow-hidden rounded-full border border-stone-300 px-4 py-2 font-medium text-stone-800 transition hover:border-stone-900"
                >
                  <AdaptiveButtonLabel text={t('summary.viewCurrent')} />
                </button>
              ) : null}
            </div>
            {primaryActionError ? (
              <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
                {primaryActionError}
              </div>
            ) : null}
          </section>

          <section className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
            <p className="text-xs uppercase tracking-[0.22em] text-stone-500">{t('detail.roundSummary')}</p>
            <p className="mt-2 text-sm font-medium text-stone-900">
              {selectedNode ? `${selectedNode.node_id} · ${t('round', { round: selectedNode.round_no })}` : t('detail.emptyTitle')}
            </p>
            <p className="mt-2 text-sm leading-6 text-stone-600">
              {nodeRound ? describeNodeState(nodeRound) : t('detail.emptyDescription')}
            </p>
            {executorActivityHint ? (
              <p className="mt-2 text-sm leading-6 text-sky-700">{executorActivityHint}</p>
            ) : null}
            <div className="mt-4 flex flex-wrap gap-2">
              {Object.entries(nodeCounts).length === 0 ? (
                <span className="rounded-full bg-stone-100 px-3 py-1 text-xs text-stone-500">{t('none')}</span>
              ) : (
                Object.entries(nodeCounts).map(([status, count]) => (
                  <span key={status} className="rounded-full bg-stone-100 px-3 py-1 text-xs text-stone-700">
                    {formatStatusLabel(status)} · {count}
                  </span>
                ))
              )}
            </div>
          </section>

          <details className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
              <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.18em] text-stone-700">
                {t('summary.advanced')}
              </summary>
              <div className="mt-3 flex items-center gap-2">
                <HelpTooltip
                  content={driverRunning ? t('drive.runningDescription') : t('drive.description')}
                  label={t('summary.advanced')}
                />
              </div>
              <div className="mt-4 space-y-4">
                <div className="rounded-3xl border border-stone-200 bg-stone-50 px-4 py-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-stone-500">{t('summary.nextActions')}</p>
                  <p className="mt-2 text-sm text-stone-600">{t('summary.dispatchableCount', { count: dispatchable.length })}</p>
                  {dispatchable.length === 0 ? (
                    <p className="mt-3 text-sm text-stone-500">{t('noDispatchable')}</p>
                  ) : (
                    <div className="mt-3 space-y-2">
                      {dispatchable.map((action) => {
                        const key = `${action.kind}:${action.node_id}:${action.round_no}:${action.validator_id || ''}`;
                        return (
                          <div
                            key={key}
                            className="flex items-center justify-between gap-3 rounded-2xl border border-stone-200 bg-white px-3 py-3"
                          >
                            <div>
                              <p className="text-sm font-medium text-stone-900">{action.kind}</p>
                              <p className="mt-1 text-xs text-stone-500">
                                {action.node_id} · {t('round', { round: action.round_no })}
                                {action.validator_id ? ` · ${action.validator_id}` : ''}
                              </p>
                            </div>
                            <button
                              type="button"
                              onClick={() => void dispatchAction(action as DispatchableAction)}
                              disabled={driverRunning || dispatchingKey === key}
                              className="inline-flex min-w-0 max-w-full items-center justify-center overflow-hidden rounded-full border border-stone-300 px-3 py-1.5 font-semibold uppercase tracking-[0.18em] text-stone-800 transition hover:border-stone-900 disabled:cursor-not-allowed disabled:border-stone-200 disabled:text-stone-400"
                            >
                              <AdaptiveButtonLabel text={t('summary.dispatchNow')} maxFontSize={12} />
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  )}
                  {dispatchError ? <p className="mt-3 text-sm text-rose-700">{dispatchError}</p> : null}
                </div>

                <div className="rounded-3xl border border-stone-200 bg-stone-50 px-4 py-4">
                  <label className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">
                    {t('drive.maxSteps')}
                  </label>
                  <input
                    className="mt-2 h-11 w-full rounded-2xl border border-stone-200 bg-white px-3 text-sm text-stone-900 outline-none"
                    value={driveMaxSteps}
                    onChange={(event) => setDriveMaxSteps(event.target.value)}
                    placeholder="100"
                  />
                  <div className="mt-4 flex flex-wrap items-center gap-3">
                    <button
                      type="button"
                      onClick={() => driveMutation.mutate()}
                      disabled={!canDrive || driveMutation.isPending}
                      className="inline-flex min-w-0 max-w-full items-center justify-center overflow-hidden rounded-full border border-stone-300 px-4 py-2 font-semibold uppercase tracking-[0.18em] text-stone-800 transition hover:border-stone-900 disabled:cursor-not-allowed disabled:border-stone-200 disabled:text-stone-400"
                    >
                      <AdaptiveButtonLabel text={t('drive.button')} maxFontSize={12} />
                    </button>
                    {driveResult ? (
                      <button
                        type="button"
                        onClick={() => setInspectorData(driveResult)}
                        className="inline-flex min-w-0 max-w-full items-center justify-center overflow-hidden rounded-full border border-stone-300 px-4 py-2 font-semibold uppercase tracking-[0.18em] text-stone-800 transition hover:border-stone-900"
                      >
                        <AdaptiveButtonLabel text={t('drive.inspect')} maxFontSize={12} />
                      </button>
                    ) : null}
                  </div>
                </div>
              </div>
              {driveResult ? (
                <div className="mt-4 rounded-[1.5rem] border border-stone-200 bg-stone-50 px-4 py-4 text-xs text-stone-700">
                  <p>{t('drive.result', { status: driveResult.status })}</p>
                  <p className="mt-1">
                    {t('drive.stopReason', {
                      reason: formatRunStopReason(driveResult.stop_reason, t) || t('none'),
                    })}
                  </p>
                  <p className="mt-1">{t('drive.steps', { count: driveResult.steps.length })}</p>
                </div>
              ) : null}
              {driverRunning ? <p className="mt-3 text-sm text-stone-500">{t('drive.disabledWhileRunning')}</p> : null}
              {driveError ? <p className="mt-3 text-sm text-rose-700">{driveError}</p> : null}
            </details>
        </aside>

        <section
          data-testid="run-detail-right-column"
          className="min-h-0 overflow-y-auto pr-1"
        >
          <div className="flex min-h-full flex-col gap-4">
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
                            ? selectNodeRoundManually(
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
                  {showJumpToCurrentFocus ? (
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
                        className="inline-flex min-w-0 max-w-full items-center justify-center overflow-hidden rounded-full border border-stone-300 px-4 py-2 font-medium text-stone-800 transition hover:border-stone-900"
                      >
                        <AdaptiveButtonLabel text={t('detail.returnToCurrent')} />
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
                  {executorActivityHint ? (
                    <div className="rounded-[1.75rem] border border-sky-200 bg-sky-50 p-5 text-sm text-stone-700">
                      {executorActivityHint}
                    </div>
                  ) : null}
                  {slowStartHint ? (
                    <div className="rounded-[1.75rem] border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
                      {slowStartHint}
                    </div>
                  ) : null}
                  {terminalHint ? (
                    <div className="rounded-[1.75rem] border border-amber-200 bg-amber-50 p-5 text-sm text-stone-700">
                      {terminalHint}
                    </div>
                  ) : null}

                  {nodeDetailError ? (
                    <div className="rounded-[1.75rem] border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800">
                      {nodeDetailError.message}
                    </div>
                  ) : null}

                  <details className="rounded-[1.75rem] border border-stone-200 bg-white p-5">
                    <summary className="cursor-pointer text-sm font-semibold text-stone-900">
                      {t('technicalOutput')}
                    </summary>
                    <div className="mt-4 space-y-4">
                      {showTechnicalOutput ? (
                        <>
                          <ClaudeTerminalPanel
                            key={`${selectedNode?.node_id}-${selectedNode?.round_no}-executor`}
                            callId={
                              claudeCalls?.executor_call_id ||
                              (currentFocusSelected ? currentFocus?.executor_call_id : undefined)
                            }
                            title={tClaude('executorTitle')}
                            emptyHint={executorTerminalEmptyHint}
                          />
                          {validatorCalls.map((item) => (
                            <ClaudeTerminalPanel
                              key={`${selectedNode?.node_id}-${selectedNode?.round_no}-${item.validator_id}`}
                              callId={item.call_id}
                              title={tClaude('validatorTitle', { id: item.validator_id })}
                            />
                          ))}
                        </>
                      ) : (
                        <p className="text-sm text-stone-500">{executorTerminalEmptyHint || tClaude('empty')}</p>
                      )}
                    </div>
                  </details>

                  <details className="rounded-[1.75rem] border border-stone-200 bg-white p-5">
                    <summary className="cursor-pointer text-sm font-semibold text-stone-900">
                      {t('technicalLogs')}
                    </summary>
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
                            <p className="mt-1 text-[11px] text-stone-400">{buildLogMeta(ref)}</p>
                          </button>
                        ))
                      )}
                    </div>
                  </details>

                  <details className="rounded-[1.75rem] border border-stone-200 bg-white p-5">
                    <summary className="cursor-pointer text-sm font-semibold text-stone-900">
                      {t('technicalCallbacks')}
                    </summary>
                    <div className="mt-4 space-y-3">
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
                  </details>

                  <details className="rounded-[1.75rem] border border-stone-200 bg-white p-5">
                    <summary className="cursor-pointer text-sm font-semibold text-stone-900">
                      {t('technicalRaw')}
                    </summary>
                    <div className="mt-4 space-y-4">
                      <button
                        type="button"
                        onClick={() => setInspectorData(nodeRound.context)}
                        className="inline-flex min-w-0 max-w-full items-center justify-center overflow-hidden rounded-full border border-stone-300 px-4 py-2 text-stone-800 transition hover:border-stone-900"
                      >
                        <AdaptiveButtonLabel text={t('inspectRawContext')} />
                      </button>
                      <div className="rounded-[1.5rem] border border-stone-200 bg-stone-950 p-5 text-sm text-stone-100">
                        <pre className="overflow-auto whitespace-pre-wrap break-all">
                          {prettyJson({
                            run,
                            overview,
                            nodeRound,
                          })}
                        </pre>
                      </div>
                    </div>
                  </details>
                </div>
              )}

              {nodeRound && detailTabIndex === 1 && (
                <div className="space-y-3">
                  {artifactActionMessage ? (
                    <div className="rounded-[1.5rem] border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
                      {artifactActionMessage}
                    </div>
                  ) : null}
                  {artifactActionError ? (
                    <div className="rounded-[1.5rem] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
                      {artifactActionError}
                    </div>
                  ) : null}
                  {nodeRound.artifacts.length === 0 ? (
                    <p className="text-sm text-stone-500">{t('noArtifactsInRound')}</p>
                  ) : (
                    nodeRound.artifacts.map((artifact) => (
                      <div
                        key={`${artifact.artifact_id}-${artifact.version}`}
                        className="w-full rounded-[1.75rem] border border-stone-200 px-5 py-4 text-left"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-medium text-stone-900">
                              {artifact.artifact_id}@{artifact.version}
                            </p>
                            <p className="mt-1 text-xs uppercase tracking-[0.18em] text-stone-500">
                              {artifact.kind}
                            </p>
                            <p className="mt-2 text-xs text-stone-500">{artifact.storage_uri}</p>
                          </div>
                          <div className="flex flex-col items-end gap-2">
                            <button
                              type="button"
                              onClick={() => void openArtifactFolder(artifact.artifact_id, artifact.version)}
                              className="inline-flex min-w-0 max-w-full items-center justify-center overflow-hidden rounded-full border border-amber-300 px-3 py-1 font-semibold uppercase tracking-[0.18em] text-amber-900 transition hover:border-amber-400"
                            >
                              <AdaptiveButtonLabel text={t('preview.openFolder')} maxFontSize={12} />
                            </button>
                            <button
                              type="button"
                              onClick={() => void copyArtifactUri(artifact.storage_uri)}
                              className="inline-flex min-w-0 max-w-full items-center justify-center overflow-hidden rounded-full border border-stone-300 px-3 py-1 font-semibold uppercase tracking-[0.18em] text-stone-700 transition hover:border-stone-900"
                            >
                              <AdaptiveButtonLabel text={t('artifactActions.copyUri')} maxFontSize={12} />
                            </button>
                            <button
                              type="button"
                              onClick={() => void loadArtifactPreview(artifact.artifact_id, artifact.version)}
                              className="inline-flex min-w-0 max-w-full items-center justify-center overflow-hidden rounded-full border border-stone-300 px-3 py-1 font-semibold uppercase tracking-[0.18em] text-stone-700 transition hover:border-stone-900"
                            >
                              <AdaptiveButtonLabel text={t('artifactActions.preview')} maxFontSize={12} />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </section>

          <details className="overflow-hidden rounded-[2rem] border border-stone-200 bg-white shadow-sm">
            <summary className="cursor-pointer px-5 py-4 text-sm font-semibold text-stone-900">
              {t('graph.title')}
            </summary>
            <div className="border-t border-stone-200 px-5 py-4">
              <div className="mb-4 flex items-center gap-2">
                <HelpTooltip content={t('graph.description')} label={t('graph.title')} />
              </div>
              <div className="flex flex-wrap gap-2 text-xs text-stone-600">
                <span className="rounded-full bg-amber-100 px-3 py-1 text-amber-900">{t('graph.legend.current')}</span>
                <span className="rounded-full bg-sky-100 px-3 py-1 text-sky-900">{t('graph.legend.running')}</span>
                <span className="rounded-full bg-indigo-100 px-3 py-1 text-indigo-900">{t('graph.legend.waiting')}</span>
                <span className="rounded-full bg-emerald-100 px-3 py-1 text-emerald-900">{t('graph.legend.completed')}</span>
                <span className="rounded-full bg-rose-100 px-3 py-1 text-rose-900">{t('graph.legend.attention')}</span>
              </div>
            </div>
            <div className="h-[360px] border-t border-stone-200 bg-stone-50 xl:h-[420px]">
              <WorkflowGraph
                initialNodes={graphNodes}
                initialEdges={workflowDetail.graph.edges as any}
                onNodeClick={(_event, node) => selectNode(node.id)}
              />
            </div>
          </details>
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
                  className="inline-flex min-w-0 max-w-full items-center justify-center overflow-hidden rounded-full border border-stone-300 px-3 py-1 font-semibold uppercase tracking-[0.18em] text-stone-700 transition hover:border-stone-500"
                >
                  <AdaptiveButtonLabel text={t('preview.close')} maxFontSize={12} />
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
