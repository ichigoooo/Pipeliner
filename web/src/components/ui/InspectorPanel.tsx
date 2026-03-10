'use client';

import React from 'react';
import { useTranslations } from 'next-intl';

interface InspectorPanelProps {
    title: string;
    data: any;
    onClose?: () => void;
}

export function InspectorPanel({ title, data, onClose }: InspectorPanelProps) {
  const t = useTranslations('common');
  return (
    <div className="flex h-full w-[360px] flex-col bg-stone-950 text-white">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <h3 className="text-sm font-medium">{title}</h3>
        {onClose ? (
          <button onClick={onClose} className="rounded-full bg-white/10 p-2 text-stone-300 transition hover:bg-white/20 hover:text-white">
            <span className="sr-only">{t('close')}</span>
            <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        ) : null}
      </div>
      <div className="flex-1 overflow-auto p-4">
        <pre className="whitespace-pre-wrap break-all text-xs leading-6 text-stone-100">
          <code>{JSON.stringify(data, null, 2)}</code>
        </pre>
      </div>
    </div>
  );
}
