import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import { NextIntlClientProvider } from 'next-intl';
import { WorkflowInputEditor } from '@/components/authoring/WorkflowInputEditor';
import enMessages from '@/i18n/messages/en.json';

const renderWithI18n = (ui: React.ReactElement) =>
  render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      {ui}
    </NextIntlClientProvider>
  );

describe('WorkflowInputEditor', () => {
  it('persists structured input metadata back into the canonical spec', () => {
    const handleChange = vi.fn();
    const rawSpec = JSON.stringify(
      {
        schema_version: 'pipeliner.workflow/v1alpha1',
        metadata: {
          workflow_id: 'wf_test',
          version: 'v1.0.0',
          title: 'Test WF',
          purpose: 'Test purpose',
          tags: [],
        },
        inputs: [
          {
            name: 'topic',
            shape: 'string',
            required: true,
            summary: 'Topic to write about',
          },
        ],
        outputs: [],
        nodes: [],
      },
      null,
      2
    );

    function Harness() {
      const [value, setValue] = React.useState(rawSpec);
      return (
        <WorkflowInputEditor
          rawSpec={value}
          onChange={(nextRawSpec) => {
            handleChange(nextRawSpec);
            setValue(nextRawSpec);
          }}
        />
      );
    }

    renderWithI18n(<Harness />);

    fireEvent.change(screen.getByRole('combobox'), {
      target: { value: 'enum' },
    });
    const optionsLabel = screen.getByText('Enum options').closest('label');
    const optionsInput = optionsLabel?.querySelector('input');
    expect(optionsInput).not.toBeNull();
    fireEvent.change(optionsInput!, {
      target: { value: 'science, history' },
    });

    expect(handleChange).toHaveBeenCalled();
    const lastCall = handleChange.mock.calls.at(-1)?.[0];
    const parsed = JSON.parse(lastCall);

    expect(parsed.inputs[0].form.type).toBe('enum');
    expect(parsed.inputs[0].form.options).toEqual(['science', 'history']);
  });
});
