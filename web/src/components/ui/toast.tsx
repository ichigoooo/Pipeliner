'use client';

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

type ToastVariant = 'default' | 'error' | 'success';

export interface ToastInput {
  title?: string;
  description?: string;
  variant?: ToastVariant;
  durationMs?: number;
}

interface ToastItem extends ToastInput {
  id: string;
  durationMs: number;
  variant: ToastVariant;
}

interface ToastContextValue {
  pushToast: (toast: ToastInput) => string;
  dismissToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);
const DEFAULT_DURATION = 6000;

function buildToastId() {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `toast_${Math.random().toString(36).slice(2)}`;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const timeoutsRef = useRef<Map<string, number>>(new Map());

  const dismissToast = useCallback((id: string) => {
    setToasts((items) => items.filter((item) => item.id !== id));
    const timeoutId = timeoutsRef.current.get(id);
    if (timeoutId) {
      window.clearTimeout(timeoutId);
      timeoutsRef.current.delete(id);
    }
  }, []);

  const pushToast = useCallback(
    (toast: ToastInput) => {
      const id = buildToastId();
      const payload: ToastItem = {
        id,
        variant: toast.variant || 'default',
        title: toast.title,
        description: toast.description,
        durationMs: toast.durationMs || DEFAULT_DURATION,
      };
      setToasts((items) => [...items, payload]);
      const timeoutId = window.setTimeout(() => dismissToast(id), payload.durationMs);
      timeoutsRef.current.set(id, timeoutId);
      return id;
    },
    [dismissToast]
  );

  useEffect(() => {
    return () => {
      timeoutsRef.current.forEach((timeoutId) => window.clearTimeout(timeoutId));
      timeoutsRef.current.clear();
    };
  }, []);

  const value = useMemo(() => ({ pushToast, dismissToast }), [pushToast, dismissToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed right-6 top-6 z-50 flex max-h-[70vh] w-[360px] flex-col gap-3"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto rounded-2xl border px-4 py-3 shadow-lg ${
              toast.variant === 'error'
                ? 'border-rose-200 bg-rose-50 text-rose-900'
                : toast.variant === 'success'
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
                  : 'border-stone-200 bg-white text-stone-900'
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                {toast.title ? <p className="text-sm font-semibold">{toast.title}</p> : null}
                {toast.description ? (
                  <p className="mt-1 text-sm leading-6 text-stone-700">{toast.description}</p>
                ) : null}
              </div>
              <button
                type="button"
                onClick={() => dismissToast(toast.id)}
                className="rounded-full border border-transparent px-2 py-1 text-xs text-stone-500 transition hover:border-stone-300"
              >
                Close
              </button>
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return ctx;
}
