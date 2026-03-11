import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
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
          round_no: 1,
          status: 'blocked',
          waiting_for_role: 'executor',
          stop_reason: 'blocked',
          rework_brief: null,
          created_at: null,
          updated_at: null,
        },
      ],
      latest_nodes: [
        {
          node_id: 'draft_article',
          round_no: 1,
          status: 'blocked',
          waiting_for_role: 'executor',
          stop_reason: 'blocked',
        },
      ],
    });
    mockedApi.getNodeRound.mockResolvedValue({
      node_id: 'draft_article',
      round_no: 1,
      status: 'blocked',
      waiting_for_role: 'executor',
      stop_reason: 'blocked',
      rework_brief: null,
      context: { context_value: 'alpha' },
      callbacks: [
        {
          event_id: 'cb_1',
          actor_role: 'executor',
          validator_id: null,
          execution_status: 'failed',
          verdict_status: null,
          payload: { detail: 'failed' },
        },
      ],
      artifacts: [
        {
          artifact_id: 'artifact_1',
          version: 'v1',
          kind: 'json',
          storage_uri: 'runs/run_1/artifacts/artifact_1@v1',
          digest: 'abc',
        },
      ],
      log_refs: [
        {
          path: 'nodes/draft_article/rounds/1/executor.log',
          kind: 'executor',
        },
      ],
    });
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
    expect(screen.getAllByText('draft_article').length).toBeGreaterThan(0);

    fireEvent.click(screen.getByText('Node Detail'));
    expect(await screen.findByText('Callbacks')).toBeInTheDocument();
    expect(screen.getByText('cb_1')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Inspect raw context'));
    expect(screen.getByText('Run Inspector')).toBeInTheDocument();
    expect(screen.getByText(/context_value/)).toBeInTheDocument();

    fireEvent.click(screen.getByText('Drive'));
    expect(await screen.findByText('Result status: completed')).toBeInTheDocument();

    fireEvent.click(screen.getByText('artifact_1@v1'));
    expect(await screen.findByText('Artifact / Log Preview')).toBeInTheDocument();
    expect(screen.getByText(/ok/)).toBeInTheDocument();
  });
});
