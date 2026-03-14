import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NextIntlClientProvider } from 'next-intl';
import { vi } from 'vitest';
import { WorkflowVersionClient } from '@/app/(studio)/workflows/[workflow_id]/[version]/WorkflowVersionClient';
import { api } from '@/lib/api';
import enMessages from '@/i18n/messages/en.json';

vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

const pushMock = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}));

vi.mock('@/components/workflow/WorkflowWorkspace', () => ({
  WorkflowWorkspace: () => <div data-testid="workflow-workspace">workspace</div>,
}));

vi.mock('@/components/workflow/WorkflowRunStartPanel', () => ({
  WorkflowRunStartPanel: () => <div data-testid="workflow-run-start-panel">start panel</div>,
}));

vi.mock('@/lib/api', () => ({
  api: {
    getWorkflow: vi.fn(),
    startRun: vi.fn(),
    createAuthoringSessionFromVersion: vi.fn(),
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

describe('WorkflowVersionClient', () => {
  it('collapses a long workflow purpose by default and toggles expansion', async () => {
    mockedApi.getWorkflow.mockResolvedValue({
      workflow_id: 'classical-text-to-csv',
      version: '0.2.0',
      title: 'Workflow title',
      warnings: [],
      spec: {},
      workflow_view: {
        metadata: {
          workflow_id: 'classical-text-to-csv',
          title: 'Workflow title',
          purpose: 'Long purpose. '.repeat(40),
          version: '0.2.0',
          tags: [],
        },
        inputs: [],
        input_descriptors: [],
        outputs: [],
        cards: [],
      },
      graph: {
        nodes: [],
        edges: [],
      },
      lint_report: {
        warnings: [],
        errors: [],
        blocking: false,
      },
    });

    renderWithClient(<WorkflowVersionClient workflowId="classical-text-to-csv" version="0.2.0" />);

    expect(await screen.findByText('Workflow title')).toBeInTheDocument();
    const purpose = screen.getByTestId('workflow-purpose');
    expect(purpose.className).toContain('max-h-24');
    expect(screen.getByRole('button', { name: 'Expand description' })).toHaveAttribute('aria-expanded', 'false');

    fireEvent.click(screen.getByRole('button', { name: 'Expand description' }));
    expect(screen.getByRole('button', { name: 'Collapse description' })).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByTestId('workflow-purpose').className).not.toContain('max-h-24');

    fireEvent.click(screen.getByRole('button', { name: 'Collapse description' }));
    expect(screen.getByRole('button', { name: 'Expand description' })).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getByTestId('workflow-purpose').className).toContain('max-h-24');
  });
});
