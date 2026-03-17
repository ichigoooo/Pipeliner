import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NextIntlClientProvider } from 'next-intl';
import { vi } from 'vitest';
import { BatchRunDetailClient } from '@/app/(studio)/runs/batches/[batch_id]/BatchRunDetailClient';
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
    getBatchRun: vi.fn(),
    openRunWorkspace: vi.fn(),
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

describe('BatchRunDetailClient', () => {
  beforeEach(() => {
    mockedApi.getBatchRun.mockReset();
    mockedApi.openRunWorkspace.mockReset();
  });

  it('renders batch items and opens the run workspace', async () => {
    mockedApi.getBatchRun.mockResolvedValue({
      batch: {
        batch_id: 'batch_1',
        workflow_id: 'mvp-review-loop',
        version: '0.1.0',
        status: 'completed',
        total_count: 2,
        success_count: 1,
        failed_count: 1,
        error_message: null,
        created_at: '2026-03-15T01:00:00Z',
        updated_at: '2026-03-15T01:02:00Z',
        started_at: '2026-03-15T01:00:10Z',
        ended_at: '2026-03-15T01:01:59Z',
      },
      items: [
        {
          item_id: 1,
          row_index: 1,
          inputs: { topic: 'alpha' },
          run_id: 'run_1',
          run_deleted: false,
          status: 'completed',
          error_message: null,
          created_at: '2026-03-15T01:00:00Z',
          updated_at: '2026-03-15T01:01:00Z',
          started_at: '2026-03-15T01:00:10Z',
          ended_at: '2026-03-15T01:00:50Z',
        },
        {
          item_id: 2,
          row_index: 2,
          inputs: {},
          run_id: null,
          run_deleted: false,
          status: 'failed',
          error_message: 'topic is required',
          created_at: '2026-03-15T01:00:00Z',
          updated_at: '2026-03-15T01:01:00Z',
          started_at: null,
          ended_at: '2026-03-15T01:00:05Z',
        },
      ],
    });
    mockedApi.openRunWorkspace.mockResolvedValue({
      run_id: 'run_1',
      opened_path: '/tmp/.pipeliner/runs/mvp-review-loop/run_1',
    });

    renderWithClient(<BatchRunDetailClient batchId="batch_1" />);

    expect(await screen.findByText('batch_1')).toBeInTheDocument();
    expect(screen.getByText('View run run_1')).toHaveClass('text-stone-600');
    expect(screen.getByText('topic is required')).toBeInTheDocument();
    expect(screen.getByText('Not started yet')).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole('button', { name: 'Open Folder' })[0]);

    await waitFor(() => {
      expect(mockedApi.openRunWorkspace).toHaveBeenCalledWith('run_1');
    });
    expect(
      await screen.findByText('Opened folder: /tmp/.pipeliner/runs/mvp-review-loop/run_1')
    ).toBeInTheDocument();
  });

  it('marks deleted runs and disables open-folder actions', async () => {
    mockedApi.getBatchRun.mockResolvedValue({
      batch: {
        batch_id: 'batch_1',
        workflow_id: 'mvp-review-loop',
        version: '0.1.0',
        status: 'completed',
        total_count: 1,
        success_count: 1,
        failed_count: 0,
        error_message: null,
        created_at: '2026-03-15T01:00:00Z',
        updated_at: '2026-03-15T01:02:00Z',
        started_at: '2026-03-15T01:00:10Z',
        ended_at: '2026-03-15T01:01:59Z',
      },
      items: [
        {
          item_id: 1,
          row_index: 1,
          inputs: { topic: 'alpha' },
          run_id: 'run_deleted',
          run_deleted: true,
          status: 'completed',
          error_message: null,
          created_at: '2026-03-15T01:00:00Z',
          updated_at: '2026-03-15T01:01:00Z',
          started_at: '2026-03-15T01:00:10Z',
          ended_at: '2026-03-15T01:00:50Z',
        },
      ],
    });

    renderWithClient(<BatchRunDetailClient batchId="batch_1" />);

    expect(await screen.findByText('Run deleted')).toBeInTheDocument();
    expect(screen.queryByText('View run run_deleted')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Open Folder' })).toBeDisabled();
  });
});
