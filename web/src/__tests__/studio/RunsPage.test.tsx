import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NextIntlClientProvider } from 'next-intl';
import { vi } from 'vitest';
import RunsPage from '@/app/(studio)/runs/page';
import { api } from '@/lib/api';
import enMessages from '@/i18n/messages/en.json';

const pushMock = vi.fn();

vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock('@/lib/api', () => ({
  api: {
    listRuns: vi.fn(),
    listBatchRuns: vi.fn(),
    deleteRun: vi.fn(),
    bulkDeleteRuns: vi.fn(),
    deleteBatchRun: vi.fn(),
    bulkDeleteBatchRuns: vi.fn(),
  },
}));

const mockedApi = vi.mocked(api);
const confirmMock = vi.fn();

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

describe('RunsPage', () => {
  beforeEach(() => {
    confirmMock.mockReset();
    confirmMock.mockReturnValue(true);
    vi.stubGlobal('confirm', confirmMock);
    mockedApi.listRuns.mockReset();
    mockedApi.listBatchRuns.mockReset();
    mockedApi.listBatchRuns.mockResolvedValue({ batches: [] });
    mockedApi.deleteRun.mockReset();
    mockedApi.bulkDeleteRuns.mockReset();
    mockedApi.deleteBatchRun.mockReset();
    mockedApi.bulkDeleteBatchRuns.mockReset();
    pushMock.mockReset();
  });

  it('groups runs by status and keeps archived runs collapsed by default', async () => {
    mockedApi.listRuns.mockResolvedValue({
      runs: [
        {
          run_id: 'run_attention',
          workflow_id: 'wf_alpha',
          version: '1.0.0',
          status: 'needs_attention',
          stop_reason: 'validator blocked',
          created_at: '2026-03-16T10:00:00Z',
          updated_at: '2026-03-16T10:10:00Z',
          attention_node_count: 1,
          batch_id: null,
        },
        {
          run_id: 'run_running',
          workflow_id: 'wf_beta',
          version: '2.0.0',
          status: 'running',
          stop_reason: null,
          created_at: '2026-03-16T11:00:00Z',
          updated_at: '2026-03-16T11:05:00Z',
          attention_node_count: 0,
          batch_id: 'batch_1',
        },
        {
          run_id: 'run_completed',
          workflow_id: 'wf_gamma',
          version: '3.0.0',
          status: 'completed',
          stop_reason: null,
          created_at: '2026-03-16T12:00:00Z',
          updated_at: '2026-03-16T12:10:00Z',
          attention_node_count: 0,
          batch_id: null,
        },
      ],
    });

    renderWithClient(<RunsPage />);

    expect(await screen.findByText('Run List')).toBeInTheDocument();
    expect(await screen.findByText('run_attention')).toBeInTheDocument();
    expect(await screen.findByText('run_running')).toBeInTheDocument();
    expect(screen.getByText('Needs attention')).toBeInTheDocument();
    expect(screen.getByText('In progress')).toBeInTheDocument();
    expect(screen.getByText('Completed and stopped')).toBeInTheDocument();
    expect(screen.getByText('run_completed')).not.toBeVisible();

    fireEvent.click(screen.getByText('Expand archive'));
    expect(await screen.findByText('run_completed')).toBeVisible();
  });

  it('keeps batch navigation as a secondary action', async () => {
    mockedApi.listRuns.mockResolvedValue({
      runs: [
        {
          run_id: 'run_running',
          workflow_id: 'wf_beta',
          version: '2.0.0',
          status: 'running',
          stop_reason: null,
          created_at: '2026-03-16T11:00:00Z',
          updated_at: '2026-03-16T11:05:00Z',
          attention_node_count: 0,
          batch_id: 'batch_1',
        },
      ],
    });

    renderWithClient(<RunsPage />);

    fireEvent.click(await screen.findByRole('button', { name: 'View Batch' }));
    expect(pushMock).toHaveBeenCalledWith('/runs/batches/batch_1');
  });

  it('renders batch cards so batch detail remains re-enterable from the runs page', async () => {
    mockedApi.listRuns.mockResolvedValue({ runs: [] });
    mockedApi.listBatchRuns.mockImplementation(async () => ({
      batches: [
        {
          batch_id: 'batch_1',
          workflow_id: 'wf_beta',
          version: '2.0.0',
          status: 'running',
          total_count: 3,
          success_count: 1,
          failed_count: 0,
          error_message: null,
          created_at: '2026-03-16T11:00:00Z',
          updated_at: '2026-03-16T11:05:00Z',
          started_at: '2026-03-16T11:00:30Z',
          ended_at: null,
        },
      ],
    }));

    renderWithClient(<RunsPage />);

    expect(await screen.findByText('Batch runs')).toBeInTheDocument();
    expect(await screen.findByText('batch_1')).toBeInTheDocument();
    fireEvent.click(screen.getByText('batch_1'));
    expect(pushMock).toHaveBeenCalledWith('/runs/batches/batch_1');
  });

  it('deletes a completed batch from its card', async () => {
    mockedApi.listRuns.mockResolvedValue({ runs: [] });
    mockedApi.listBatchRuns.mockResolvedValue({
      batches: [
        {
          batch_id: 'batch_done',
          workflow_id: 'wf_beta',
          version: '2.0.0',
          status: 'completed',
          total_count: 2,
          success_count: 2,
          failed_count: 0,
          error_message: null,
          created_at: '2026-03-16T11:00:00Z',
          updated_at: '2026-03-16T11:05:00Z',
          started_at: '2026-03-16T11:00:30Z',
          ended_at: '2026-03-16T11:10:00Z',
        },
      ],
    });
    mockedApi.deleteBatchRun.mockResolvedValue({
      batch_id: 'batch_done',
      workflow_id: 'wf_beta',
      deleted_run_ids: ['run_1'],
      deleted: true,
    });

    renderWithClient(<RunsPage />);

    fireEvent.click(await screen.findByRole('button', { name: 'Delete Batch' }));
    await waitFor(() => {
      expect(mockedApi.deleteBatchRun).toHaveBeenCalledWith('batch_done');
    });
  });

  it('bulk deletes selected completed batches', async () => {
    mockedApi.listRuns.mockResolvedValue({ runs: [] });
    mockedApi.listBatchRuns.mockResolvedValue({
      batches: [
        {
          batch_id: 'batch_a',
          workflow_id: 'wf_beta',
          version: '2.0.0',
          status: 'completed',
          total_count: 2,
          success_count: 2,
          failed_count: 0,
          error_message: null,
          created_at: '2026-03-16T11:00:00Z',
          updated_at: '2026-03-16T11:05:00Z',
          started_at: '2026-03-16T11:00:30Z',
          ended_at: '2026-03-16T11:10:00Z',
        },
        {
          batch_id: 'batch_b',
          workflow_id: 'wf_beta',
          version: '2.0.1',
          status: 'failed',
          total_count: 2,
          success_count: 1,
          failed_count: 1,
          error_message: 'failed',
          created_at: '2026-03-16T12:00:00Z',
          updated_at: '2026-03-16T12:05:00Z',
          started_at: '2026-03-16T12:00:30Z',
          ended_at: '2026-03-16T12:10:00Z',
        },
      ],
    });
    mockedApi.bulkDeleteBatchRuns.mockResolvedValue({
      batch_ids: ['batch_a', 'batch_b'],
      deleted_count: 2,
      deleted: true,
    });

    renderWithClient(<RunsPage />);

    const checkboxes = await screen.findAllByRole('checkbox');
    fireEvent.click(checkboxes[0]);
    fireEvent.click(checkboxes[1]);
    fireEvent.click(screen.getByRole('button', { name: 'Delete 2 selected batches' }));
    await waitFor(() => {
      expect(mockedApi.bulkDeleteBatchRuns).toHaveBeenCalledWith(['batch_b', 'batch_a']);
    });
  });

  it('deletes a non-running run after confirmation', async () => {
    mockedApi.listRuns.mockResolvedValue({
      runs: [
        {
          run_id: 'run_attention',
          workflow_id: 'wf_alpha',
          version: '1.0.0',
          status: 'needs_attention',
          stop_reason: 'validator blocked',
          created_at: '2026-03-16T10:00:00Z',
          updated_at: '2026-03-16T10:10:00Z',
          attention_node_count: 1,
          batch_id: null,
        },
      ],
    });
    mockedApi.deleteRun.mockResolvedValue({
      run_id: 'run_attention',
      workflow_id: 'wf_alpha',
      batch_id: null,
      workspace_root: 'runs/wf_alpha/run_attention',
      deleted: true,
    });

    renderWithClient(<RunsPage />);

    fireEvent.click(await screen.findByRole('button', { name: 'Delete Run' }));
    expect(confirmMock).toHaveBeenCalled();
    await waitFor(() => {
      expect(mockedApi.deleteRun).toHaveBeenCalledWith('run_attention');
    });
  });

  it('bulk deletes selected non-running runs', async () => {
    mockedApi.listRuns.mockResolvedValue({
      runs: [
        {
          run_id: 'run_b',
          workflow_id: 'wf_alpha',
          version: '1.0.1',
          status: 'completed',
          stop_reason: null,
          created_at: '2026-03-16T12:00:00Z',
          updated_at: '2026-03-16T12:10:00Z',
          attention_node_count: 0,
          batch_id: null,
        },
        {
          run_id: 'run_a',
          workflow_id: 'wf_alpha',
          version: '1.0.0',
          status: 'needs_attention',
          stop_reason: 'validator blocked',
          created_at: '2026-03-16T10:00:00Z',
          updated_at: '2026-03-16T10:10:00Z',
          attention_node_count: 1,
          batch_id: null,
        },
      ],
    });
    mockedApi.bulkDeleteRuns.mockResolvedValue({
      run_ids: ['run_a', 'run_b'],
      deleted_count: 2,
      deleted: true,
    });

    renderWithClient(<RunsPage />);

    const checkboxes = await screen.findAllByRole('checkbox');
    fireEvent.click(checkboxes[0]);
    fireEvent.click(checkboxes[1]);
    fireEvent.click(screen.getByRole('button', { name: 'Delete 2 selected runs' }));
    await waitFor(() => {
      expect(mockedApi.bulkDeleteRuns).toHaveBeenCalledWith(['run_a', 'run_b']);
    });
  });
});
