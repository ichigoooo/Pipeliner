'use client';

import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { formatStatusLabel } from '@/lib/status';

type ClaudeTerminalPanelProps = {
  callId?: string | null;
  title?: string;
  defaultOpen?: boolean;
  emptyHint?: string;
};

type ClaudeCallPayload = {
  call_id: string;
  offset: number;
  chunk: string;
  status: string;
  done: boolean;
  truncated?: boolean;
  redacted?: boolean;
};

const POLL_INTERVAL_MS = 1500;
const POLL_LIMIT = 20000;

export function ClaudeTerminalPanel({
  callId,
  title,
  defaultOpen = false,
  emptyHint,
}: ClaudeTerminalPanelProps) {
  const t = useTranslations('claudeTerminal');
  const tStatus = useTranslations('status');
  const [open, setOpen] = useState(defaultOpen);
  const [content, setContent] = useState('');
  const [status, setStatus] = useState<string>('unknown');
  const [redacted, setRedacted] = useState(false);
  const [truncated, setTruncated] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const offsetRef = useRef(0);
  const outputRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollTimerRef = useRef<number | null>(null);

  const stopStreaming = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (pollTimerRef.current) {
      window.clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  };

  const appendPayload = (payload: ClaudeCallPayload) => {
    setStatus(payload.status || 'unknown');
    setRedacted(Boolean(payload.redacted));
    setTruncated(Boolean(payload.truncated));
    if (!payload.redacted && payload.chunk) {
      setContent((prev) => prev + payload.chunk);
    }
    offsetRef.current = payload.offset;
  };

  const pollOnce = async () => {
    if (!callId) {
      return;
    }
    const response = await fetch(
      `/api/claude-calls/${encodeURIComponent(callId)}/poll?offset=${offsetRef.current}&limit=${POLL_LIMIT}`,
      { cache: 'no-store' }
    );
    if (!response.ok) {
      throw new Error(t('loadFailed'));
    }
    const payload = (await response.json()) as ClaudeCallPayload;
    appendPayload(payload);
    const hasMore = payload.chunk.length === POLL_LIMIT && !payload.truncated && !payload.redacted;
    if (payload.done && !hasMore) {
      stopStreaming();
    }
  };

  const startPolling = () => {
    if (pollTimerRef.current) {
      return;
    }
    pollOnce().catch((err) => setError((err as Error).message));
    pollTimerRef.current = window.setInterval(() => {
      pollOnce().catch((err) => setError((err as Error).message));
    }, POLL_INTERVAL_MS);
  };

  const startEventSource = () => {
    if (!callId || eventSourceRef.current) {
      return;
    }
    const source = new EventSource(
      `/api/claude-calls/${encodeURIComponent(callId)}/stream?offset=${offsetRef.current}`
    );
    eventSourceRef.current = source;
    source.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as ClaudeCallPayload;
        appendPayload(payload);
        if (payload.done) {
          stopStreaming();
        }
      } catch (err) {
        setError((err as Error).message);
      }
    };
    source.onerror = () => {
      source.close();
      eventSourceRef.current = null;
      startPolling();
    };
  };

  useEffect(() => {
    setContent('');
    setStatus('unknown');
    setRedacted(false);
    setTruncated(false);
    setError(null);
    offsetRef.current = 0;
    stopStreaming();
  }, [callId]);

  useEffect(() => {
    if (!open || !callId) {
      stopStreaming();
      return;
    }
    pollOnce()
      .then(() => startEventSource())
      .catch((err) => {
        setError((err as Error).message);
        startPolling();
      });
    return () => {
      stopStreaming();
    };
  }, [callId, open]);

  useEffect(() => {
    if (!open || !outputRef.current) {
      return;
    }
    outputRef.current.scrollTop = outputRef.current.scrollHeight;
  }, [content, open]);

  const statusLabel = formatStatusLabel(status, tStatus);

  return (
    <section className="rounded-[1.75rem] border border-stone-200 bg-white p-5 shadow-sm">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center justify-between gap-4 text-left"
      >
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-stone-500">{title || t('title')}</p>
          <p className="mt-2 text-xs text-stone-500">{callId ? t('ready') : emptyHint || t('empty')}</p>
        </div>
        <div className="flex items-center gap-3">
          {callId ? <StatusBadge value={status} /> : null}
          <span className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">
            {open ? t('collapse') : t('expand')}
          </span>
        </div>
      </button>

      {open ? (
        <div className="mt-4 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-stone-500">
            <span>{statusLabel}</span>
            {status === 'running' ? <span>{t('streaming')}</span> : null}
            {truncated ? <span className="text-amber-700">{t('truncated')}</span> : null}
          </div>
          <div
            ref={outputRef}
            className="max-h-[260px] overflow-auto rounded-[1.5rem] border border-stone-200 bg-stone-950 p-4 text-xs text-stone-100"
          >
            {redacted ? (
              <>
                <p className="text-amber-200">{t('redacted')}</p>
                <p className="mt-2 text-xs text-amber-200">{t('redactedHint')}</p>
              </>
            ) : content ? (
              <pre className="whitespace-pre-wrap break-all">{content}</pre>
            ) : (
              <p className="text-stone-400">{callId ? t('noOutput') : emptyHint || t('empty')}</p>
            )}
          </div>
          {error ? <p className="text-xs text-rose-700">{error}</p> : null}
        </div>
      ) : null}
    </section>
  );
}
