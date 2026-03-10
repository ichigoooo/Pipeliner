import React from 'react';
import { render, screen } from '@testing-library/react';
import { WorkflowWorkspace } from '@/components/workflow/WorkflowWorkspace';

// This is a basic rendering test for the component structure
describe('WorkflowWorkspace', () => {
  it('renders without crashing given basic props', () => {
    const mockSpec = {
      metadata: { workflow_id: "test", version: "v1.0.0", title: "Test" },
      nodes: []
    };
    
    render(
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
