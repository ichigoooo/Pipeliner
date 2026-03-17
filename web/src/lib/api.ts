export interface WorkflowListItem {
  workflow_id: string;
  title: string;
  purpose: string;
  version_count: number;
  latest_version: string | null;
  updated_at: string | null;
}

export interface WorkflowVersionItem {
  version: string;
  schema_version: string;
  warnings: string[];
  created_at: string | null;
}

export interface WorkflowCard {
  node_id: string;
  title: string;
  purpose: string;
  archetype: string;
  depends_on: string[];
  executor_skill: string | null;
  validator_ids: (string | null)[];
  input_names: (string | null)[];
  output_names: (string | null)[];
  done_means: string | null;
  raw: Record<string, unknown>;
}

export interface WorkflowInputDescriptor {
  name: string;
  shape: string;
  required: boolean;
  summary: string;
  type: 'string' | 'number' | 'boolean' | 'enum' | 'file' | 'json';
  default?: unknown;
  options: string[];
  minimum?: number;
  maximum?: number;
  min_length?: number;
  max_length?: number;
  pattern?: string;
  source: 'explicit' | 'derived';
}

export interface WorkflowProjection {
  metadata: {
    workflow_id: string;
    title: string;
    purpose: string;
    version: string;
    tags: string[];
  };
  inputs: unknown[];
  input_descriptors: WorkflowInputDescriptor[];
  outputs: unknown[];
  cards: WorkflowCard[];
}

export interface GraphProjection {
  nodes: Array<Record<string, unknown>>;
  edges: Array<Record<string, unknown>>;
}

export interface LintReport {
  warnings: string[];
  errors: string[];
  blocking: boolean;
}

export interface WorkflowDetail {
  workflow_id: string;
  version: string;
  title: string;
  warnings: string[];
  spec: Record<string, unknown>;
  workflow_view: WorkflowProjection;
  graph: GraphProjection;
  lint_report: LintReport;
}

export interface AuthoringSource { type: string | null; payload: Record<string, unknown> | null; }

export interface AuthoringSession {
  session_id: string;
  title: string;
  status: string;
  latest_revision?: number | null;
  draft_count?: number | null;
  published_workflow_id?: string | null;
  published_version?: string | null;
  published_revision?: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface AuthoringSessionDetail extends AuthoringSession {
  intent_brief: string;
  published_at?: string | null;
}

export interface AuthoringMessage {
  id: number;
  session_id: string;
  revision: number | null;
  role: string;
  content: string;
  created_at: string | null;
}

export interface AuthoringDraft {
  session_id: string;
  revision: number;
  spec_json: Record<string, unknown>;
  workflow_view: WorkflowProjection;
  graph: GraphProjection;
  lint_report: LintReport;
  lint_warnings: string[];
  created_at: string | null;
  claude_call_id?: string | null;
}

export interface ClaudeCallMetadata {
  call_id: string;
  role: string;
  status: string;
  started_at: string;
  ended_at: string | null;
  exit_code: number | null;
  error_message: string | null;
  bytes_written: number;
  truncated: boolean;
  limit_bytes: number;
  output_path: string;
  command: string | null;
  context: Record<string, unknown>;
  redacted?: boolean;
}

export interface ClaudeCallPoll {
  call_id: string;
  offset: number;
  chunk: string;
  status: string;
  done: boolean;
  truncated?: boolean;
  redacted?: boolean;
}

export interface RunSummary {
  run_id: string;
  workflow_id: string;
  version: string;
  status: string;
  stop_reason: string | null;
  created_at: string | null;
  updated_at: string | null;
  batch_id?: string | null;
  attention_node_count?: number;
}

export interface BatchRunSummary {
  batch_id: string;
  workflow_id: string;
  version: string;
  status: string;
  total_count: number;
  success_count: number;
  failed_count: number;
  error_message: string | null;
  created_at: string | null;
  updated_at: string | null;
  started_at: string | null;
  ended_at: string | null;
}

export interface DeleteBatchRunResult {
  batch_id: string;
  workflow_id: string;
  deleted_run_ids: string[];
  deleted: boolean;
}

export interface BulkDeleteBatchRunsResult {
  batch_ids: string[];
  deleted_count: number;
  deleted: boolean;
}

export interface BatchRunItem {
  item_id: number;
  row_index: number;
  inputs: Record<string, unknown>;
  run_id: string | null;
  run_deleted?: boolean;
  status: string;
  error_message: string | null;
  created_at: string | null;
  updated_at: string | null;
  started_at: string | null;
  ended_at: string | null;
}

export interface BatchRunDetail {
  batch: BatchRunSummary;
  items: BatchRunItem[];
}

export interface BatchRunStartResponse extends BatchRunSummary {
  driver: Record<string, unknown>;
}

export interface RunDetail {
  run: {
    id: string;
    status: string;
    workspace_root: string;
    stop_reason: string | null;
    batch_id?: string | null;
  };
  workflow: {
    workflow_id: string;
    version: string;
    title: string;
  };
  nodes: Array<{
    node_id: string;
    round_no: number;
    status: string;
    waiting_for_role: string | null;
    stop_reason: string | null;
  }>;
  artifacts: Array<{
    artifact_id: string;
    version: string;
    kind: string;
    storage_uri: string;
    node_id: string;
    round_no: number;
  }>;
}

export interface DeleteRunResult {
  run_id: string;
  workflow_id: string;
  batch_id: string | null;
  workspace_root: string;
  deleted: boolean;
}

export interface RunArtifactFolderOpenResult {
  artifact_id: string;
  version: string;
  target_path: string;
  opened_path: string;
}

export interface RunWorkspaceOpenResult {
  run_id: string;
  opened_path: string;
}

export interface RunOverview {
  run_id: string;
  status: string;
  stop_reason: string | null;
  workflow: {
    workflow_id: string;
    version: string;
    title: string;
  };
  summary: {
    node_counts: Record<string, number>;
    attention_nodes: Array<{
      node_id: string;
      round_no: number;
      status: string;
      waiting_for_role: string | null;
      stop_reason: string | null;
    }>;
  };
  dispatchable: Array<{
    kind: 'executor' | 'validator';
    node_id: string;
    round_no: number;
    validator_id?: string;
  }>;
  timeline: Array<{
    node_id: string;
    round_no: number;
    status: string;
    waiting_for_role: string | null;
    stop_reason: string | null;
    rework_brief: Record<string, unknown> | null;
    created_at: string | null;
    updated_at: string | null;
  }>;
  latest_nodes: Array<{
    node_id: string;
    round_no: number;
    status: string;
    waiting_for_role: string | null;
    stop_reason: string | null;
  }>;
  driver: {
    run_id: string;
    status: string;
    mode: string | null;
    max_steps: number | null;
    started_at: string | null;
    ended_at: string | null;
    last_error: string | null;
    stop_reason: string | null;
    result_status: string | null;
  };
  current_focus: {
    node_id: string;
    round_no: number;
    status: string;
    waiting_for_role: string | null;
    stop_reason: string | null;
    executor_call_id: string | null;
    validator_calls: Array<{
      validator_id: string;
      call_id: string;
    }>;
  } | null;
  activity: Array<{
    kind: string;
    node_id: string | null;
    round_no: number | null;
    actor_role: string | null;
    validator_id: string | null;
    status: string;
    summary: string;
    happened_at: string;
    call_id: string | null;
  }>;
}

export interface NodeRoundDetail {
  node_id: string;
  round_no: number;
  status: string;
  waiting_for_role: string | null;
  stop_reason: string | null;
  rework_brief: Record<string, unknown> | null;
  context: Record<string, unknown> | null;
  callbacks: Array<{
    event_id: string;
    actor_role: string;
    validator_id: string | null;
    execution_status: string;
    verdict_status: string | null;
    payload: Record<string, unknown>;
  }>;
  artifacts: Array<{
    artifact_id: string;
    version: string;
    kind: string;
    storage_uri: string;
    digest: string;
    node_id: string;
    round_no: number;
  }>;
  log_refs: Array<{
    path: string;
    kind: string;
    size_bytes: number | null;
    updated_at: string | null;
  }>;
  claude_calls?: {
    executor_call_id: string | null;
    validator_calls: Array<{
      validator_id: string;
      call_id: string;
    }>;
  };
}

export interface AttentionRun {
  run_id: string;
  workflow_id: string;
  version: string;
  status: string;
  stop_reason: string | null;
  created_at: string | null;
  updated_at: string | null;
  actions: string[];
}

export interface SettingsSnapshot {
  executor_command: SettingValue<string>;
  validator_command: SettingValue<string>;
  storage: {
    backend: SettingValue<string>;
    data_dir: SettingValue<string>;
    run_root: SettingValue<string>;
  };
  database: {
    url: SettingValue<string>;
    path: SettingValue<string>;
  };
  observability: {
    claude_trace_enabled: SettingValue<boolean>;
  };
  runtime_guards: {
    default_timeout: SettingValue<string>;
    default_max_rework_rounds: SettingValue<number>;
    blocked_requires_manual: SettingValue<boolean>;
    failure_requires_manual: SettingValue<boolean>;
  };
  providers: Array<{
    provider: string;
    role: string;
    command_template: SettingValue<string>;
  }>;
  skills: Array<{
    skill: string;
    used_by: string[];
  }>;
}

export interface SettingValue<T> {
  value: T;
  source: string;
  env_key: string;
  default: T;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function readErrorMessage(response: Response): Promise<string> {
  const payload = await response.json().catch(() => ({ detail: '请求失败' }));
  return payload.detail || '请求失败';
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/${path}`, {
    ...init,
    headers: {
      'content-type': 'application/json',
      ...(init?.headers || {}),
    },
    cache: 'no-store',
  });

  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response), response.status);
  }

  return response.json() as Promise<T>;
}

async function requestForm<T>(path: string, form: FormData): Promise<T> {
  const response = await fetch(`/api/${path}`, {
    method: 'POST',
    body: form,
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response), response.status);
  }
  return response.json() as Promise<T>;
}

async function requestBlob(path: string): Promise<Blob> {
  const response = await fetch(`/api/${path}`, {
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response), response.status);
  }
  return response.blob();
}

export const api = {
  listWorkflows: async () => request<{ workflows: WorkflowListItem[] }>('workflows'),
  listWorkflowVersions: async (workflowId: string) =>
    request<{ workflow_id: string; versions: WorkflowVersionItem[] }>(
      `workflows/${workflowId}/versions`
    ),
  getWorkflow: async (workflowId: string, version: string) =>
    request<WorkflowDetail>(`workflows/${workflowId}/versions/${version}`),
  listAuthoringSessions: async () =>
    request<{ sessions: AuthoringSession[] }>('authoring/sessions'),
  createAuthoringSession: async (payload: { title: string; intent_brief: string }) =>
    request<{ session_id: string; title: string; status: string; latest_revision: number }>('authoring/sessions', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getAuthoringSession: async (sessionId: string) =>
    request<AuthoringSessionDetail>(`authoring/sessions/${sessionId}`),
  listAuthoringDrafts: async (sessionId: string) =>
    request<{ drafts: AuthoringDraft[] }>(`authoring/sessions/${sessionId}/drafts`),
  getLatestDraft: async (sessionId: string) =>
    request<AuthoringDraft>(`authoring/sessions/${sessionId}/drafts/latest`),
  getDraft: async (sessionId: string, revision: number) =>
    request<AuthoringDraft>(`authoring/sessions/${sessionId}/drafts/${revision}`),
  listAuthoringMessages: async (sessionId: string) =>
    request<{ messages: AuthoringMessage[] }>(`authoring/sessions/${sessionId}/messages`),
  saveDraft: async (
    sessionId: string,
    payload: { spec: Record<string, unknown>; instruction?: string }
  ) =>
    request<AuthoringDraft>(`authoring/sessions/${sessionId}/drafts`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  continueSession: async (
    sessionId: string,
    payload: { instruction: string; spec: Record<string, unknown> }
  ) =>
    request<AuthoringDraft>(`authoring/sessions/${sessionId}/continue`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  publishSession: async (sessionId: string, revision?: number) =>
    request<{ workflow_id: string; version: string; session_id: string; revision: number }>(
      `authoring/sessions/${sessionId}/publish${revision ? `?revision=${revision}` : ''}`,
      {
        method: 'POST',
      }
    ),
  generateDraft: async (
    sessionId: string,
    payload: { instruction: string; spec?: Record<string, unknown>; claude_call_id?: string }
  ) =>
    request<AuthoringDraft>(`authoring/sessions/${sessionId}/generate`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getClaudeCall: async (callId: string) =>
    request<ClaudeCallMetadata>(`claude-calls/${callId}`),
  pollClaudeCall: async (callId: string, offset: number, limit = 20000) =>
    request<ClaudeCallPoll>(`claude-calls/${callId}/poll?offset=${offset}&limit=${limit}`),
  createAuthoringSessionFromVersion: async (payload: { workflow_id: string; version: string; title?: string; intent_brief?: string }) =>
    request<{ session_id: string; title: string; status: string; latest_revision: number }>(
      'authoring/sessions/from-version',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    ),
  createAuthoringSessionFromRun: async (payload: { run_id: string; node_id?: string; round_no?: number; title?: string; intent_brief?: string }) =>
    request<{ session_id: string; title: string; status: string; latest_revision: number }>(
      'authoring/sessions/from-run',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    ),
  listRuns: async () => request<{ runs: RunSummary[] }>('runs'),
  downloadWorkflowInputTemplate: async (workflowId: string, version: string) =>
    requestBlob(`workflows/${workflowId}/versions/${version}/inputs/template.csv`),
  startBatchRun: async (workflowId: string, version: string, file: File) => {
    const form = new FormData();
    form.append('file', file, file.name);
    return requestForm<BatchRunStartResponse>(
      `workflows/${workflowId}/versions/${version}/batch-runs`,
      form
    );
  },
  listBatchRuns: async () => request<{ batches: BatchRunSummary[] }>('batch-runs'),
  deleteBatchRun: async (batchId: string) =>
    request<DeleteBatchRunResult>(`batch-runs/${batchId}`, {
      method: 'DELETE',
    }),
  bulkDeleteBatchRuns: async (batchIds: string[]) =>
    request<BulkDeleteBatchRunsResult>('batch-runs/bulk-delete', {
      method: 'POST',
      body: JSON.stringify({ batch_ids: batchIds }),
    }),
  getBatchRun: async (batchId: string) => request<BatchRunDetail>(`batch-runs/${batchId}`),
  startRun: async (
    workflowId: string,
    version: string,
    inputs: Record<string, unknown>,
    options?: { auto_drive?: boolean }
  ) =>
    request<{ run_id: string; status: string; workspace_root: string }>('runs', {
      method: 'POST',
      body: JSON.stringify({
        workflow_id: workflowId,
        version,
        inputs,
        auto_drive: options?.auto_drive ?? true,
      }),
    }),
  listAttentionRuns: async () => request<{ runs: AttentionRun[] }>('runs/attention'),
  getRun: async (runId: string) => request<RunDetail>(`runs/${runId}`),
  deleteRun: async (runId: string) =>
    request<DeleteRunResult>(`runs/${runId}`, {
      method: 'DELETE',
    }),
  getRunOverview: async (runId: string) =>
    request<RunOverview>(`runs/${runId}/debug/overview`),
  getNodeRound: async (runId: string, nodeId: string, roundNo: number) =>
    request<NodeRoundDetail>(`runs/${runId}/debug/nodes/${nodeId}/rounds/${roundNo}`),
  stopRun: async (runId: string, reason = 'manual_stop') =>
    request<{ run_id: string; status: string; stop_reason: string }>(`runs/${runId}/stop`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),
  retryNode: async (
    runId: string,
    nodeId: string,
    reworkBrief?: Record<string, unknown>
  ) =>
    request<{ run_id: string; node_id: string; round_no: number; status: string }>(
      `runs/${runId}/nodes/${nodeId}/retry`,
      {
        method: 'POST',
        body: JSON.stringify({ rework_brief: reworkBrief ?? null }),
      }
    ),
  driveRun: async (
    runId: string,
    payload: { max_steps?: number; executor_command_template?: string; validator_command_template?: string }
  ) =>
    request<{ run_id: string; status: string; stop_reason: string; steps: Record<string, unknown>[] }>(
      `runs/${runId}/drive`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    ),
  dispatchExecutor: async (
    runId: string,
    nodeId: string,
    payload: { round_no?: number; command_template?: string }
  ) =>
    request<Record<string, unknown>>(`runs/${runId}/nodes/${nodeId}/executor/dispatch`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  dispatchValidator: async (
    runId: string,
    nodeId: string,
    validatorId: string,
    payload: { round_no?: number; command_template?: string }
  ) =>
    request<Record<string, unknown>>(
      `runs/${runId}/nodes/${nodeId}/validators/${validatorId}/dispatch`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    ),
  previewRunArtifact: async (runId: string, artifactId: string, version: string) =>
    request<any>(`runs/${runId}/artifacts/${artifactId}/versions/${version}/preview`),
  openRunArtifactFolder: async (runId: string, artifactId: string, version: string) =>
    request<RunArtifactFolderOpenResult>(`runs/${runId}/artifacts/${artifactId}/versions/${version}/open-folder`, {
      method: 'POST',
    }),
  openRunWorkspace: async (runId: string) =>
    request<RunWorkspaceOpenResult>(`runs/${runId}/open-folder`, {
      method: 'POST',
    }),
  previewRunLog: async (runId: string, path: string) =>
    request<any>(`runs/${runId}/logs/preview?path=${encodeURIComponent(path)}`),
  getSettings: async () => request<{ settings: SettingsSnapshot }>('settings'),
};
