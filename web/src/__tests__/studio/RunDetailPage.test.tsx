import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NextIntlClientProvider } from 'next-intl';
import { vi } from 'vitest';
import { RunDetailClient } from '@/app/(studio)/runs/[run_id]/RunDetailClient';
import { api } from '@/lib/api';
import enMessages from '@/i18n/messages/en.json';

vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock('@/lib/api', () => ({
  api: {
    getRun: vi.fn(),
    getRunOverview: vi.fn(),
    getWorkflow: vi.fn(),
    getNodeRound: vi.fn(),
    stopRun: vi.fn(),
    retryNode: vi.fn(),
    driveRun: vi.fn(),
    previewRunArtifact: vi.fn(),
    previewRunLog: vi.fn(),
  },
}));

const mockedApi = vi.mocked(api);

const renderWithClient = (ui: React.ReactElement) => {
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <QueryClientProvider client={client}>{ui}</QueryClientProvider>
    </NextIntlClientProvider>
  );
};

describe('RunDetailPage', () => {
  it('renders run inspection flow and raw context', async () => {
    mockedApi.getWorkflow.mockResolvedValue({
      workflow_id: 'wf_test',
      version: 'v1',
      title: 'Workflow Test',
      warnings: [],
      spec: {},
      workflow_view: {
        metadata: { workflow_id: 'wf_test', title: 'Workflow Test', purpose: 'Test', version: 'v1', tags: [] },
        inputs: [],
        input_descriptors: [],
        outputs: [],
        cards: [],
      },
      graph: {
        nodes: [
          {
            id: 'draft_article',
            data: { label: 'Draft Article', node_id: 'draft_article', spec: {} },
            position: { x: 0, y: 0 },
          },
        ],
        edges: [],
      },
      lint_report: { warnings: [], errors: [], blocking: false },
    });
    mockedApi.getRun.mockResolvedValue({
      run: {
        id: 'run_1',
        status: 'needs_attention',
        workspace_root: '/tmp/run',
        stop_reason: 'blocked',
      },
      workflow: {
        workflow_id: 'wf_test',
        version: 'v1',
        title: 'Workflow Test',
      },
      nodes: [],
      artifacts: [],
    });
    mockedApi.getRunOverview.mockResolvedValue({
      run_id: 'run_1',
      status: 'needs_attention',
      stop_reason: 'blocked',
      workflow: { workflow_id: 'wf_test', version: 'v1', title: 'Workflow Test' },
      timeline: [
        {
          node_id: 'draft_article',
          round_no: 2,
          status: 'blocked',
          waiting_for_role: 'executor',
          stop_reason: 'blocked',
          rework_brief: null,
          created_at: null,
          updated_at: '2026-03-13T00:00:01Z',
        },
        {
          node_id: 'draft_article',
          round_no: 1,
          status: 'completed',
          waiting_for_role: null,
          stop_reason: null,
          rework_brief: null,
          created_at: null,
          updated_at: null,
        },
      ],
      latest_nodes: [
        {
          node_id: 'draft_article',
          round_no: 2,
          status: 'blocked',
          waiting_for_role: 'executor',
          stop_reason: 'blocked',
        },
      ],
      driver: {
        run_id: 'run_1',
        status: 'idle',
        mode: null,
        max_steps: null,
        started_at: null,
        ended_at: null,
        last_error: null,
        stop_reason: null,
        result_status: null,
      },
      current_focus: {
        node_id: 'draft_article',
        round_no: 2,
        status: 'blocked',
        waiting_for_role: 'executor',
        stop_reason: 'blocked',
        executor_call_id: null,
        validator_calls: [],
      },
      activity: [
        {
          kind: 'node_status_changed',
          node_id: 'draft_article',
          round_no: 1,
          actor_role: null,
          validator_id: null,
          status: 'blocked',
          summary: 'draft_article changed to blocked',
          happened_at: '2026-03-13T00:00:00Z',
          call_id: null,
        },
      ],
    });
    mockedApi.getNodeRound.mockImplementation(async (_runId, _nodeId, roundNo) => ({
      node_id: 'draft_article',
      round_no: roundNo,
      status: roundNo === 2 ? 'blocked' : 'completed',
      waiting_for_role: roundNo === 2 ? 'executor' : null,
      stop_reason: roundNo === 2 ? 'blocked' : null,
      rework_brief: null,
      context: { context_value: roundNo === 2 ? 'alpha' : 'beta' },
      callbacks:
        roundNo === 2
          ? [
              {
                event_id: 'cb_1',
                actor_role: 'executor',
                validator_id: null,
                execution_status: 'failed',
                verdict_status: null,
                payload: { detail: 'failed' },
              },
            ]
          : [],
      artifacts:
        roundNo === 2
          ? [
              {
                artifact_id: 'artifact_1',
                version: 'v1',
                kind: 'json',
                storage_uri: 'runs/run_1/artifacts/artifact_1@v1',
                digest: 'abc',
              },
            ]
          : [],
      log_refs:
        roundNo === 2
          ? [
              {
                path: 'nodes/draft_article/rounds/2/executor.log',
                kind: 'executor',
              },
            ]
          : [],
    }));
    mockedApi.stopRun.mockResolvedValue({ run_id: 'run_1', status: 'stopped', stop_reason: 'manual_stop' });
    mockedApi.retryNode.mockResolvedValue({
      run_id: 'run_1',
      node_id: 'draft_article',
      round_no: 2,
      status: 'waiting_executor',
    });
    mockedApi.driveRun.mockResolvedValue({
      run_id: 'run_1',
      status: 'completed',
      stop_reason: 'terminal_state',
      steps: [],
    });
    mockedApi.previewRunArtifact.mockResolvedValue({
      artifact_id: 'artifact_1',
      version: 'v1',
      kind: 'json',
      storage_uri: 'runs/run_1/artifacts/artifact_1@v1',
      manifest: { artifact_id: 'artifact_1', version: 'v1' },
      preview: {
        kind: 'json',
        content: { ok: true },
        truncated: false,
        size_bytes: 10,
        limit_bytes: 200000,
        path: '/tmp/artifact.json',
      },
    });
    mockedApi.previewRunLog.mockResolvedValue({
      path: 'nodes/draft_article/rounds/1/executor.log',
      preview: {
        kind: 'text',
        content: 'hello log',
        truncated: false,
        size_bytes: 8,
        limit_bytes: 200000,
        path: '/tmp/executor.log',
      },
    });

    renderWithClient(<RunDetailClient runId="run_1" />);

    expect(await screen.findByText('Run workspace')).toBeInTheDocument();
    expect(await screen.findByText('Run overview')).toBeInTheDocument();
    expect(await screen.findByText('Run Graph')).toBeInTheDocument();
    expect(screen.getByTestId('run-detail-right-column')).toBeInTheDocument();
    expect(screen.getByTestId('node-detail-scroll-region')).toBeInTheDocument();
    expect(screen.queryByText('Live Activity')).not.toBeInTheDocument();
    expect(screen.getAllByText('draft_article').length).toBeGreaterThan(0);
    expect(screen.getByText('View current node')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Round'), { target: { value: '1' } });
    await waitFor(() =>
      expect(screen.getByText('draft_article · Round 1')).toBeInTheDocument()
    );

    fireEvent.click(screen.getByText('Raw'));
    fireEvent.click(screen.getByText('Inspect raw context'));
    expect(screen.getByText('Run Inspector')).toBeInTheDocument();
    expect(screen.getAllByText(/context_value/).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByText('Advanced controls'));
    fireEvent.click(screen.getByText('Drive'));
    expect(await screen.findByText('Result status: completed')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'View current node' }));
    await waitFor(() =>
      expect(screen.getByText('draft_article · Round 2')).toBeInTheDocument()
    );

    fireEvent.click(screen.getByText('Callbacks'));
    expect(await screen.findByText('cb_1')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Artifacts'));
    fireEvent.click(screen.getByText('artifact_1@v1'));
    expect(await screen.findByTestId('run-detail-preview')).toBeInTheDocument();
    expect(await screen.findByText('Artifact / Log Preview')).toBeInTheDocument();
    expect(screen.getByText(/ok/)).toBeInTheDocument();
  });

  it('prioritizes current focus and disables manual drive while auto-drive is running', async () => {
    mockedApi.getWorkflow.mockResolvedValue({
      workflow_id: 'wf_live',
      version: 'v2',
      title: 'Workflow Live',
      warnings: [],
      spec: {},
      workflow_view: {
        metadata: { workflow_id: 'wf_live', title: 'Workflow Live', purpose: 'Live', version: 'v2', tags: [] },
        inputs: [],
        input_descriptors: [],
        outputs: [],
        cards: [],
      },
      graph: {
        nodes: [
          {
            id: 'draft_article',
            data: { label: 'Draft Article', node_id: 'draft_article', spec: {} },
            position: { x: 0, y: 0 },
          },
        ],
        edges: [],
      },
      lint_report: { warnings: [], errors: [], blocking: false },
    });
    mockedApi.getRun.mockResolvedValue({
      run: {
        id: 'run_live',
        status: 'running',
        workspace_root: '/tmp/run_live',
        stop_reason: null,
      },
      workflow: {
        workflow_id: 'wf_live',
        version: 'v2',
        title: 'Workflow Live',
      },
      nodes: [],
      artifacts: [],
    });
    mockedApi.getRunOverview.mockResolvedValue({
      run_id: 'run_live',
      status: 'running',
      stop_reason: null,
      workflow: { workflow_id: 'wf_live', version: 'v2', title: 'Workflow Live' },
      timeline: [
        {
          node_id: 'draft_article',
          round_no: 1,
          status: 'waiting_executor',
          waiting_for_role: 'executor',
          stop_reason: null,
          rework_brief: null,
          created_at: null,
          updated_at: null,
        },
      ],
      latest_nodes: [
        {
          node_id: 'draft_article',
          round_no: 1,
          status: 'waiting_executor',
          waiting_for_role: 'executor',
          stop_reason: null,
        },
      ],
      driver: {
        run_id: 'run_live',
        status: 'running',
        mode: 'auto',
        max_steps: 500,
        started_at: '2026-03-13T00:00:00Z',
        ended_at: null,
        last_error: null,
        stop_reason: null,
        result_status: null,
      },
      current_focus: {
        node_id: 'draft_article',
        round_no: 1,
        status: 'waiting_executor',
        waiting_for_role: 'executor',
        stop_reason: null,
        executor_call_id: null,
        validator_calls: [],
      },
      activity: [
        {
          kind: 'node_waiting',
          node_id: 'draft_article',
          round_no: 1,
          actor_role: 'executor',
          validator_id: null,
          status: 'waiting_executor',
          summary: 'draft_article is waiting for executor',
          happened_at: '2026-03-13T00:00:00Z',
          call_id: null,
        },
      ],
    });
    mockedApi.getNodeRound.mockResolvedValue({
      node_id: 'draft_article',
      round_no: 1,
      status: 'waiting_executor',
      waiting_for_role: 'executor',
      stop_reason: null,
      rework_brief: null,
      context: { context_value: 'live' },
      callbacks: [],
      artifacts: [],
      log_refs: [],
      claude_calls: {
        executor_call_id: null,
        validator_calls: [],
      },
    });
    mockedApi.stopRun.mockResolvedValue({ run_id: 'run_live', status: 'stopped', stop_reason: 'manual_stop' });
    mockedApi.retryNode.mockResolvedValue({
      run_id: 'run_live',
      node_id: 'draft_article',
      round_no: 2,
      status: 'waiting_executor',
    });
    mockedApi.driveRun.mockResolvedValue({
      run_id: 'run_live',
      status: 'completed',
      stop_reason: 'terminal_state',
      steps: [],
    });
    mockedApi.previewRunArtifact.mockResolvedValue(null as never);
    mockedApi.previewRunLog.mockResolvedValue(null as never);

    renderWithClient(<RunDetailClient runId="run_live" />);

    expect(await screen.findByText('Run overview')).toBeInTheDocument();
    expect(await screen.findByText('Run Graph')).toBeInTheDocument();
    expect(screen.getByTestId('run-detail-right-column')).toBeInTheDocument();
    expect(screen.getByTestId('node-detail-scroll-region')).toBeInTheDocument();
    expect(screen.queryByText('Live Activity')).not.toBeInTheDocument();
    expect(screen.getAllByText('Waiting for executor').length).toBeGreaterThan(0);
    expect(screen.getByText('Terminal')).toBeInTheDocument();
    expect(
      screen.getAllByText('This round is queued and waiting for the next dispatch to start.').length
    ).toBeGreaterThan(0);
    expect(screen.getByText('No call yet')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Advanced controls'));
    expect(screen.getByRole('button', { name: 'Drive' })).toBeDisabled();
  });
});
