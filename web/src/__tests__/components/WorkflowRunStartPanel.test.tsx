import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import { NextIntlClientProvider } from 'next-intl';
import { WorkflowRunStartPanel } from '@/components/workflow/WorkflowRunStartPanel';
import enMessages from '@/i18n/messages/en.json';

const renderWithI18n = (ui: React.ReactElement) =>
  render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      {ui}
    </NextIntlClientProvider>
  );

describe('WorkflowRunStartPanel', () => {
  it('serializes structured form values into run inputs', () => {
    const handleSubmit = vi.fn();

    renderWithI18n(
      <WorkflowRunStartPanel
        descriptors={[
          {
            name: 'topic',
            shape: 'string',
            required: true,
            summary: 'Topic to write about',
            type: 'enum',
            options: ['science', 'history'],
            source: 'explicit',
          },
          {
            name: 'retry_count',
            shape: 'number',
            required: false,
            summary: 'Retry count',
            type: 'number',
            default: 2,
            options: [],
            minimum: 1,
            maximum: 5,
            source: 'explicit',
          },
        ]}
        error={null}
        isSubmitting={false}
        onCancel={() => {}}
        onSubmit={handleSubmit}
      />
    );

    fireEvent.change(screen.getByRole('combobox'), {
      target: { value: 'history' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Launch Run' }));

    expect(handleSubmit).toHaveBeenCalledWith({
      topic: 'history',
      retry_count: 2,
    });
  });

  it('supports raw json fallback submission', () => {
    const handleSubmit = vi.fn();

    renderWithI18n(
      <WorkflowRunStartPanel
        descriptors={[]}
        error={null}
        isSubmitting={false}
        onCancel={() => {}}
        onSubmit={handleSubmit}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Use Raw JSON' }));
    fireEvent.change(screen.getByDisplayValue('{}'), {
      target: { value: '{\n  "topic": "science"\n}' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Launch Run' }));

    expect(handleSubmit).toHaveBeenCalledWith({ topic: 'science' });
  });

  it('keeps file inputs as manual local path strings', () => {
    const handleSubmit = vi.fn();

    renderWithI18n(
      <WorkflowRunStartPanel
        descriptors={[
          {
            name: 'source_file',
            shape: 'file',
            required: true,
            summary: 'Source file path',
            type: 'file',
            options: [],
            source: 'explicit',
          },
        ]}
        error={null}
        isSubmitting={false}
        onCancel={() => {}}
        onSubmit={handleSubmit}
      />
    );

    fireEvent.change(screen.getByPlaceholderText('Enter a local file path'), {
      target: { value: '/tmp/source.md' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Launch Run' }));

    expect(screen.getByText(/batch launches/i)).toBeInTheDocument();
    expect(handleSubmit).toHaveBeenCalledWith({ source_file: '/tmp/source.md' });
  });

  it('ignores null length constraints from api descriptors', () => {
    const handleSubmit = vi.fn();

    renderWithI18n(
      <WorkflowRunStartPanel
        descriptors={[
          {
            name: 'source_text',
            shape: 'file',
            required: true,
            summary: 'Source text path',
            type: 'file',
            default: null,
            options: [],
            min_length: null,
            max_length: null,
            pattern: null,
            source: 'explicit',
          } as any,
        ]}
        error={null}
        isSubmitting={false}
        onCancel={() => {}}
        onSubmit={handleSubmit}
      />
    );

    fireEvent.change(screen.getByPlaceholderText('Enter a local file path'), {
      target: { value: '/tmp/source.txt' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Launch Run' }));

    expect(screen.queryByText('Must be at most null characters')).not.toBeInTheDocument();
    expect(handleSubmit).toHaveBeenCalledWith({ source_text: '/tmp/source.txt' });
  });
});
