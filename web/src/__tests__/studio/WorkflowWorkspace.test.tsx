import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { WorkflowWorkspace } from '@/components/workflow/WorkflowWorkspace';

vi.mock('@/components/workflow/WorkflowGraph', () => ({
  WorkflowGraph: ({ initialNodes }: { initialNodes: Array<{ id: string }> }) => (
    <div data-testid="workflow-graph">Graph nodes: {initialNodes.length}</div>
  ),
}));

describe('WorkflowWorkspace', () => {
  it('renders synchronized views and raw inspector', () => {
    const spec = { metadata: { workflow_id: 'wf_test' }, nodes: [{ node_id: 'node_a' }] };
    const cards = [
      {
        node_id: 'node_a',
        title: 'Node A',
        purpose: 'Purpose A',
        archetype: 'draft',
        depends_on: [],
        executor_skill: 'draft-skill',
        validator_ids: ['review'],
        input_names: [],
        output_names: [],
        done_means: 'done',
        raw: { node_id: 'node_a', foo: 'bar' },
      },
    ];
    const nodes = [
      {
        id: 'node_a',
        data: { spec: { node_id: 'node_a', foo: 'bar' } },
        position: { x: 0, y: 0 },
      },
    ];

    render(
      <WorkflowWorkspace
        spec={spec}
        cards={cards}
        nodes={nodes as never[]}
        edges={[]}
        lintWarnings={['Deprecated field']}
        lintErrors={['Missing output']}
      />
    );

    expect(screen.getByTestId('workflow-graph')).toHaveTextContent('Graph nodes: 1');

    fireEvent.click(screen.getByText('Cards'));
    fireEvent.click(screen.getByText('Node A'));
    expect(screen.getByText('Raw Inspector')).toBeInTheDocument();
    const nodeLabels = screen.getAllByText(/node_a/);
    expect(nodeLabels.length).toBeGreaterThan(0);

    fireEvent.click(screen.getByText('Spec'));
    expect(screen.getByText(/"workflow_id": "wf_test"/)).toBeInTheDocument();

    fireEvent.click(screen.getByText('Lint (2)'));
    expect(screen.getByText('Missing output')).toBeInTheDocument();
    expect(screen.getByText('Deprecated field')).toBeInTheDocument();
  });
});
