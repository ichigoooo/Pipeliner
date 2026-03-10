import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';
import RunDetailPage from '@/app/(studio)/runs/[run_id]/page';
import { api } from '@/lib/api';

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
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
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
      artifacts: [],
      log_refs: [],
    });
    mockedApi.stopRun.mockResolvedValue({ run_id: 'run_1', status: 'stopped', stop_reason: 'manual_stop' });
    mockedApi.retryNode.mockResolvedValue({
      run_id: 'run_1',
      node_id: 'draft_article',
      round_no: 2,
      status: 'waiting_executor',
    });

    renderWithClient(<RunDetailPage params={{ run_id: 'run_1' }} />);

    expect(await screen.findByText('Run workspace')).toBeInTheDocument();
    expect(screen.getAllByText('draft_article').length).toBeGreaterThan(0);

    fireEvent.click(screen.getByText('Node Detail'));
    expect(await screen.findByText('Callbacks')).toBeInTheDocument();
    expect(screen.getByText('cb_1')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Inspect raw context'));
    expect(screen.getByText('Run Inspector')).toBeInTheDocument();
    expect(screen.getByText(/context_value/)).toBeInTheDocument();
  });
});
