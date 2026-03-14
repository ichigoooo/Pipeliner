'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { prettyJson } from '@/lib/format';
import {
  WorkflowInputDescriptor,
  buildInitialFormValues,
  serializeWorkflowInputValues,
} from '@/lib/workflow-inputs';

interface WorkflowRunStartPanelProps {
  descriptors: WorkflowInputDescriptor[];
  error: string | null;
  isSubmitting: boolean;
  onCancel: () => void;
  onSubmit: (payload: Record<string, unknown>) => void;
}

export function WorkflowRunStartPanel({
  descriptors,
  error,
  isSubmitting,
  onCancel,
  onSubmit,
}: WorkflowRunStartPanelProps) {
  const t = useTranslations('workflows');
  const [mode, setMode] = useState<'structured' | 'raw'>('structured');
  const [formValues, setFormValues] = useState<Record<string, unknown>>({});
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [rawJson, setRawJson] = useState('{\n  \n}');
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    const nextValues = buildInitialFormValues(descriptors);
    setFormValues(nextValues);
    setFieldErrors({});
    setLocalError(null);
    setRawJson(prettyJson(Object.fromEntries(
      Object.entries(nextValues).flatMap(([name, value]) => {
        if (value === '' || value === undefined) {
          return [];
        }
        try {
          const parsed = typeof value === 'string' && descriptors.find((item) => item.name === name)?.type === 'json'
            ? JSON.parse(value)
            : value;
          return [[name, parsed]];
        } catch {
          return [];
        }
      })
    )));
  }, [descriptors]);

  const submitStructured = () => {
    const result = serializeWorkflowInputValues(descriptors, formValues);
    setFieldErrors(result.errors);
    setLocalError(null);
    if (Object.keys(result.errors).length > 0) {
      return;
    }
    onSubmit(result.payload);
  };

  const submitRaw = () => {
    setFieldErrors({});
    setLocalError(null);
    try {
      const parsed = JSON.parse(rawJson || '{}') as Record<string, unknown>;
      if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
        throw new Error(t('jsonObjectRequired'));
      }
      onSubmit(parsed);
    } catch (parseError) {
      setLocalError(parseError instanceof Error ? parseError.message : t('parseFailed'));
    }
  };

  return (
    <div className="mt-4 rounded-[2rem] border border-stone-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <label className="text-xs font-semibold uppercase tracking-[0.2em] text-stone-500">
            {mode === 'structured' ? t('runInputsForm') : t('runInputs')}
          </label>
          <p className="mt-2 text-xs text-stone-500">
            {mode === 'structured' ? t('runInputsFormHint') : t('runInputsRawHint')}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setMode((current) => (current === 'structured' ? 'raw' : 'structured'))}
          className="rounded-full border border-stone-300 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-stone-700 transition hover:border-stone-900"
        >
          {mode === 'structured' ? t('switchToRaw') : t('switchToForm')}
        </button>
      </div>

      {mode === 'structured' ? (
        <div className="mt-4 space-y-4">
          {descriptors.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-stone-300 bg-stone-50 px-4 py-5 text-sm text-stone-500">
              {t('runInputsEmpty')}
            </div>
          ) : null}
          {descriptors.map((descriptor) => (
            <label key={descriptor.name} className="block space-y-2 text-sm text-stone-700">
              <div className="flex items-center gap-2">
                <span className="font-medium text-stone-900">{descriptor.name}</span>
                {descriptor.required ? (
                  <span className="rounded-full bg-rose-100 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-rose-800">
                    {t('required')}
                  </span>
                ) : null}
                <span className="rounded-full bg-stone-100 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-stone-600">
                  {descriptor.type}
                </span>
              </div>
              <p className="text-xs text-stone-500">{descriptor.summary}</p>

              {descriptor.type === 'boolean' ? (
                <input
                  type="checkbox"
                  checked={Boolean(formValues[descriptor.name])}
                  onChange={(event) =>
                    setFormValues((current) => ({
                      ...current,
                      [descriptor.name]: event.target.checked,
                    }))
                  }
                />
              ) : descriptor.type === 'enum' ? (
                <select
                  className="h-11 w-full rounded-2xl border border-stone-200 bg-stone-50 px-4 text-sm text-stone-900 outline-none"
                  value={String(formValues[descriptor.name] ?? '')}
                  onChange={(event) =>
                    setFormValues((current) => ({
                      ...current,
                      [descriptor.name]: event.target.value,
                    }))
                  }
                >
                  <option value="">{t('selectOption')}</option>
                  {descriptor.options.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              ) : descriptor.type === 'json' ? (
                <textarea
                  className="min-h-32 w-full rounded-3xl border border-stone-200 bg-stone-50 px-4 py-3 font-mono text-xs text-stone-900 outline-none"
                  value={String(formValues[descriptor.name] ?? '')}
                  onChange={(event) =>
                    setFormValues((current) => ({
                      ...current,
                      [descriptor.name]: event.target.value,
                    }))
                  }
                />
              ) : (
                <div className="space-y-2">
                  <input
                    className="h-11 w-full rounded-2xl border border-stone-200 bg-stone-50 px-4 text-sm text-stone-900 outline-none"
                    type={descriptor.type === 'number' ? 'number' : 'text'}
                    placeholder={descriptor.type === 'file' ? t('filePathPlaceholder') : undefined}
                    value={String(formValues[descriptor.name] ?? '')}
                    onChange={(event) =>
                      setFormValues((current) => ({
                        ...current,
                        [descriptor.name]: event.target.value,
                      }))
                    }
                  />
                  {descriptor.type === 'file' ? (
                    <p className="text-xs text-stone-500">{t('filePathHint')}</p>
                  ) : null}
                </div>
              )}

              {fieldErrors[descriptor.name] ? (
                <p className="text-xs text-rose-700">{fieldErrors[descriptor.name]}</p>
              ) : null}
            </label>
          ))}
        </div>
      ) : (
        <textarea
          className="mt-3 min-h-32 w-full rounded-3xl border border-stone-200 bg-stone-50 px-4 py-3 font-mono text-xs text-stone-900 outline-none"
          value={rawJson}
          onChange={(event) => setRawJson(event.target.value)}
        />
      )}

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={mode === 'structured' ? submitStructured : submitRaw}
          disabled={isSubmitting}
          className="rounded-full bg-stone-950 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-white transition hover:bg-stone-800 disabled:cursor-not-allowed disabled:bg-stone-400"
        >
          {t('launchRun')}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-full border border-stone-300 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-stone-700 transition hover:border-stone-900"
        >
          {t('cancel')}
        </button>
        {localError ? <p className="text-xs text-rose-700">{localError}</p> : null}
        {error ? <p className="text-xs text-rose-700">{error}</p> : null}
      </div>
    </div>
  );
}
