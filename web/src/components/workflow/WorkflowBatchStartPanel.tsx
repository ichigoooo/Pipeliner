'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { AdaptiveButtonLabel } from '@/components/ui/AdaptiveButtonLabel';
import { HelpTooltip } from '@/components/ui/HelpTooltip';

interface WorkflowBatchStartPanelProps {
  error: string | null;
  isSubmitting: boolean;
  onCancel: () => void;
  onSubmit: (file: File) => void;
}

export function WorkflowBatchStartPanel({
  error,
  isSubmitting,
  onCancel,
  onSubmit,
}: WorkflowBatchStartPanelProps) {
  const t = useTranslations('workflows');
  const [file, setFile] = useState<File | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = () => {
    if (!file) {
      setLocalError(t('uploadCsv'));
      return;
    }
    setLocalError(null);
    onSubmit(file);
  };

  return (
    <div className="mt-4 rounded-[2rem] border border-stone-200 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2">
        <label className="text-xs font-semibold uppercase tracking-[0.2em] text-stone-500">
          {t('uploadCsv')}
        </label>
        <HelpTooltip content={t('uploadCsvHint')} label={t('uploadCsv')} />
      </div>
      <div className="mt-4">
        <input
          type="file"
          accept=".csv,text/csv"
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null);
            setLocalError(null);
          }}
          className="w-full rounded-2xl border border-stone-200 bg-stone-50 px-3 py-2 text-sm text-stone-700"
        />
      </div>
      {file ? <p className="mt-2 text-xs text-stone-500">{file.name}</p> : null}
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={isSubmitting}
          className="inline-flex min-w-0 max-w-full items-center justify-center overflow-hidden rounded-full bg-stone-950 px-4 py-2 font-semibold uppercase tracking-[0.18em] text-white transition hover:bg-stone-800 disabled:cursor-not-allowed disabled:bg-stone-400"
        >
          <AdaptiveButtonLabel text={t('startBatch')} maxFontSize={12} />
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="inline-flex min-w-0 max-w-full items-center justify-center overflow-hidden rounded-full border border-stone-300 px-4 py-2 font-semibold uppercase tracking-[0.18em] text-stone-700 transition hover:border-stone-900"
        >
          <AdaptiveButtonLabel text={t('cancel')} maxFontSize={12} />
        </button>
        {localError ? <p className="text-xs text-rose-700">{localError}</p> : null}
        {error ? <p className="text-xs text-rose-700">{error}</p> : null}
      </div>
    </div>
  );
}
