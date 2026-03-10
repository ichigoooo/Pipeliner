'use client';

import React from 'react';

interface WorkflowSpecViewProps {
    spec: object;
}

export function WorkflowSpecView({ spec }: WorkflowSpecViewProps) {
  return (
    <div className="h-full w-full overflow-auto bg-stone-950 p-4">
      <pre className="text-sm leading-7 text-stone-100">
        <code>{JSON.stringify(spec, null, 2)}</code>
      </pre>
    </div>
  );
}
