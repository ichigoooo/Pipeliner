import React from 'react';
import { render, screen } from '@testing-library/react';
import { NextIntlClientProvider } from 'next-intl';
import { WorkflowWorkspace } from '@/components/workflow/WorkflowWorkspace';
import enMessages from '@/i18n/messages/en.json';

const renderWithI18n = (ui: React.ReactElement) => {
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      {ui}
    </NextIntlClientProvider>
  );
};

// This is a basic rendering test for the component structure
describe('WorkflowWorkspace', () => {
  it('renders without crashing given basic props', () => {
    const mockSpec = {
      metadata: { workflow_id: "test", version: "v1.0.0", title: "Test" },
      nodes: []
    };

    renderWithI18n(
      <WorkflowWorkspace
        spec={mockSpec}
        nodes={[]}
        edges={[]}
        lintWarnings={[]}
      />
    );

    // Check if tabs exist
    expect(screen.getByText('Graph')).toBeInTheDocument();
    expect(screen.getByText('Cards')).toBeInTheDocument();
    expect(screen.getByText('Spec')).toBeInTheDocument();
    expect(screen.getByText('Lint (0)')).toBeInTheDocument();
  });
});
