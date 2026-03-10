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

export interface WorkflowProjection {
  metadata: {
    workflow_id: string;
    title: string;
    purpose: string;
    version: string;
    tags: string[];
  };
  inputs: unknown[];
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
}

export interface RunSummary {
  run_id: string;
  workflow_id: string;
  version: string;
  status: string;
  stop_reason: string | null;
  created_at: string | null;
  updated_at: string | null;
  attention_node_count?: number;
}

export interface RunDetail {
  run: {
    id: string;
    status: string;
    workspace_root: string;
    stop_reason: string | null;
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

export interface RunOverview {
  run_id: string;
  status: string;
  stop_reason: string | null;
  workflow: {
    workflow_id: string;
    version: string;
    title: string;
  };
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
  }>;
  log_refs: Array<{
    path: string;
    kind: string;
  }>;
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
    const payload = await response.json().catch(() => ({ detail: '请求失败' }));
    throw new Error(payload.detail || '请求失败');
  }

  return response.json() as Promise<T>;
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
  listRuns: async () => request<{ runs: RunSummary[] }>('runs'),
  startRun: async (workflowId: string, version: string, inputs: Record<string, unknown>) =>
    request<{ run_id: string; status: string; workspace_root: string }>('runs', {
      method: 'POST',
      body: JSON.stringify({
        workflow_id: workflowId,
        version,
        inputs,
      }),
    }),
  listAttentionRuns: async () => request<{ runs: AttentionRun[] }>('runs/attention'),
  getRun: async (runId: string) => request<RunDetail>(`runs/${runId}`),
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
  getSettings: async () => request<{ settings: SettingsSnapshot }>('settings'),
};
