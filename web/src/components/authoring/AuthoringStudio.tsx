'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FormEvent, ReactNode, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useSearchParams } from 'next/navigation';
import CodeMirror from '@uiw/react-codemirror';
import { json } from '@codemirror/lang-json';
import { api, ApiError, AuthoringDraft } from '@/lib/api';
import { classNames, formatTimestamp, prettyJson } from '@/lib/format';
import { WorkflowWorkspace } from '@/components/workflow/WorkflowWorkspace';
import { ClaudeTerminalPanel } from '@/components/claude/ClaudeTerminalPanel';
import { WorkflowInputEditor } from '@/components/authoring/WorkflowInputEditor';
import { AdaptiveButtonLabel } from '@/components/ui/AdaptiveButtonLabel';
import { HelpTooltip } from '@/components/ui/HelpTooltip';
import { useToast } from '@/components/ui/toast';

const PANEL_CLASS =
  'rounded-[2rem] border border-stone-200/70 bg-white/88 p-5 shadow-[0_24px_70px_-36px_rgba(68,64,60,0.4)] backdrop-blur';

type ActionButtonProps = {
  children: ReactNode;
  disabled?: boolean;
  onClick?: () => void;
  type?: 'button' | 'submit';
  variant?: 'primary' | 'secondary' | 'ghost' | 'accent';
};

function parseSpec(value: string) {
  return JSON.parse(value) as Record<string, unknown>;
}

function buildClaudeCallId(prefix: string) {
  const timestamp = Date.now();
  const nonce = Math.random().toString(36).slice(2, 10);
  return `${prefix}_${timestamp}_${nonce}`;
}

function ActionButton({
  children,
  disabled = false,
  onClick,
  type = 'button',
  variant = 'secondary',
}: ActionButtonProps) {
  const variantClassName = {
    primary:
      'bg-stone-950 text-white shadow-[0_18px_40px_-24px_rgba(28,25,23,0.65)] hover:-translate-y-0.5 hover:bg-stone-900',
    secondary:
      'border border-stone-300 bg-white text-stone-900 hover:-translate-y-0.5 hover:border-stone-400 hover:bg-stone-50',
    ghost:
      'bg-stone-100 text-stone-700 hover:-translate-y-0.5 hover:bg-stone-200',
    accent:
      'border border-amber-300 bg-amber-100 text-amber-950 hover:-translate-y-0.5 hover:border-amber-400 hover:bg-amber-200',
  }[variant];

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={classNames(
        'inline-flex min-w-0 items-center justify-center overflow-hidden rounded-[1.15rem] px-4 py-3 font-medium transition duration-200 active:translate-y-px',
        variantClassName,
        disabled &&
          'cursor-not-allowed border-stone-200 bg-stone-100 text-stone-400 shadow-none hover:translate-y-0 hover:border-stone-200 hover:bg-stone-100'
      )}
    >
      {typeof children === 'string' ? <AdaptiveButtonLabel text={children} /> : children}
    </button>
  );
}

type PendingGenerateReconcile = {
  sessionId: string;
  requestedCallId: string;
  baselineRevision: number | null;
  startedAt: number;
};

type RawSpecBuffer = {
  sessionId: string | null;
  value: string;
  mode: 'manual' | 'synced';
};

function notifyActionError(
  action: 'publish' | 'generate' | 'continue' | 'save',
  error: unknown,
  pushToast: (toast: { title?: string; description?: string; variant?: 'default' | 'error' | 'success' }) => void,
  t: (key: string) => string
) {
  const message = error instanceof Error ? error.message : '请求失败';
  if (action === 'publish' && error instanceof ApiError && error.status === 409) {
    pushToast({
      variant: 'error',
      title: t('errors.publishFailed'),
      description: t('errors.publishConflict'),
    });
    return;
  }
  const key = action === 'publish'
    ? 'errors.publishFailed'
    : action === 'generate'
      ? 'errors.generateFailed'
      : action === 'continue'
        ? 'errors.continueFailed'
        : 'errors.saveFailed';
  pushToast({
    variant: 'error',
    title: t(key),
    description: message,
  });
}

export function AuthoringStudio() {
  const t = useTranslations('authoring');
  const tClaude = useTranslations('claudeTerminal');
  const { pushToast } = useToast();
  const searchParams = useSearchParams();
  const sessionFromQuery = searchParams.get('session');
  const queryClient = useQueryClient();
  const sessionsQuery = useQuery({
    queryKey: ['authoring-sessions'],
    queryFn: api.listAuthoringSessions,
    refetchInterval: 10_000,
  });

  const sessions = useMemo(() => sessionsQuery.data?.sessions ?? [], [sessionsQuery.data?.sessions]);
  const [manualSelectedSessionId, setManualSelectedSessionId] = useState<string | null>(null);
  const [title, setTitle] = useState('Developer Workflow Studio');
  const [intentBrief, setIntentBrief] = useState(
    'Author a developer-first pipeline with inspectable drafts and settings provenance.'
  );
  const [instruction, setInstruction] = useState(
    'Refine the workflow while keeping workflow spec as the only canonical source.'
  );
  const [rawSpecBuffer, setRawSpecBuffer] = useState<RawSpecBuffer>({
    sessionId: null,
    value: '{}',
    mode: 'synced',
  });
  const [error, setError] = useState<string | null>(null);
  const [reconcilingGenerate, setReconcilingGenerate] = useState(false);
  const [claudeCallId, setClaudeCallId] = useState<string | null>(null);
  const [pendingGenerateReconcile, setPendingGenerateReconcile] =
    useState<PendingGenerateReconcile | null>(null);

  const selectedSessionId = useMemo(() => {
    if (manualSelectedSessionId) {
      return manualSelectedSessionId;
    }
    if (sessionFromQuery) {
      if (sessions.length === 0) {
        return sessionFromQuery;
      }
      return sessions.some((session) => session.session_id === sessionFromQuery)
        ? sessionFromQuery
        : sessions[0]?.session_id ?? null;
    }
    return sessions[0]?.session_id ?? null;
  }, [manualSelectedSessionId, sessionFromQuery, sessions]);

  const sessionDetailQuery = useQuery({
    queryKey: ['authoring-session', selectedSessionId],
    queryFn: () => api.getAuthoringSession(selectedSessionId!),
    enabled: Boolean(selectedSessionId),
  });

  const draftQuery = useQuery({
    queryKey: ['authoring-draft-latest', selectedSessionId],
    queryFn: () => api.getLatestDraft(selectedSessionId!),
    enabled: Boolean(selectedSessionId),
    refetchInterval: 10_000,
  });

  const draftsQuery = useQuery({
    queryKey: ['authoring-drafts', selectedSessionId],
    queryFn: () => api.listAuthoringDrafts(selectedSessionId!),
    enabled: Boolean(selectedSessionId),
  });

  const messagesQuery = useQuery({
    queryKey: ['authoring-messages', selectedSessionId],
    queryFn: () => api.listAuthoringMessages(selectedSessionId!),
    enabled: Boolean(selectedSessionId),
    refetchInterval: 10_000,
  });

  const invalidateSession = async (sessionId: string) => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['authoring-sessions'] }),
      queryClient.invalidateQueries({ queryKey: ['authoring-session', sessionId] }),
      queryClient.invalidateQueries({ queryKey: ['authoring-draft-latest', sessionId] }),
      queryClient.invalidateQueries({ queryKey: ['authoring-drafts', sessionId] }),
      queryClient.invalidateQueries({ queryKey: ['authoring-messages', sessionId] }),
    ]);
  };

  const createSessionMutation = useMutation({
    mutationFn: api.createAuthoringSession,
    onSuccess: async (payload) => {
      setManualSelectedSessionId(payload.session_id);
      setRawSpecBuffer({ sessionId: payload.session_id, value: '{}', mode: 'synced' });
      await invalidateSession(payload.session_id);
    },
  });

  const saveDraftMutation = useMutation({
    mutationFn: ({ sessionId, draft, note }: { sessionId: string; draft: Record<string, unknown>; note?: string }) =>
      api.saveDraft(sessionId, { spec: draft, instruction: note }),
    onSuccess: async (payload) => {
      queryClient.setQueryData(['authoring-draft-latest', payload.session_id], payload);
      setRawSpecBuffer({
        sessionId: payload.session_id,
        value: prettyJson(payload.spec_json),
        mode: 'synced',
      });
      await invalidateSession(payload.session_id);
    },
  });

  const continueMutation = useMutation({
    mutationFn: ({ sessionId, draft, note }: { sessionId: string; draft: Record<string, unknown>; note: string }) =>
      api.continueSession(sessionId, { spec: draft, instruction: note }),
    onSuccess: async (payload) => {
      queryClient.setQueryData(['authoring-draft-latest', payload.session_id], payload);
      setRawSpecBuffer({
        sessionId: payload.session_id,
        value: prettyJson(payload.spec_json),
        mode: 'synced',
      });
      await invalidateSession(payload.session_id);
    },
  });

  const generateMutation = useMutation({
    mutationFn: ({
      sessionId,
      draft,
      note,
      callId,
    }: {
      sessionId: string;
      draft: Record<string, unknown>;
      note: string;
      callId?: string;
    }) => api.generateDraft(sessionId, { spec: draft, instruction: note, claude_call_id: callId }),
    onSuccess: async (payload) => {
      setClaudeCallId((current) => (payload.claude_call_id ? payload.claude_call_id : current));
      setReconcilingGenerate(false);
      setPendingGenerateReconcile(null);
      queryClient.setQueryData(['authoring-draft-latest', payload.session_id], payload);
      setRawSpecBuffer({
        sessionId: payload.session_id,
        value: prettyJson(payload.spec_json),
        mode: 'synced',
      });
      await invalidateSession(payload.session_id);
    },
  });

  const publishMutation = useMutation({
    mutationFn: ({ sessionId, revision }: { sessionId: string; revision: number }) =>
      api.publishSession(sessionId, revision),
    onSuccess: async (payload) => {
      await invalidateSession(payload.session_id);
    },
  });

  const activeDraft: AuthoringDraft | undefined = draftQuery.data;
  const currentSession = sessionDetailQuery.data;
  const draftList = draftsQuery.data?.drafts ?? [];
  const messages = messagesQuery.data?.messages ?? [];
  const canPublish = activeDraft ? !activeDraft.lint_report.blocking : false;
  const warningCount = activeDraft?.lint_report.warnings.length ?? 0;
  const blockingCount = activeDraft?.lint_report.errors.length ?? 0;
  const remoteRawSpec = activeDraft ? prettyJson(activeDraft.spec_json) : '{}';
  const rawSpec =
    rawSpecBuffer.sessionId === selectedSessionId && rawSpecBuffer.mode === 'manual'
      ? rawSpecBuffer.value
      : remoteRawSpec;
  const generateRecovered =
    Boolean(
      activeDraft &&
      pendingGenerateReconcile &&
      selectedSessionId === pendingGenerateReconcile.sessionId &&
      (
        activeDraft.claude_call_id === pendingGenerateReconcile.requestedCallId ||
        (pendingGenerateReconcile.baselineRevision === null
          ? activeDraft.revision > 0
          : activeDraft.revision > pendingGenerateReconcile.baselineRevision)
      )
    );
  const statusMessage = generateRecovered
    ? t('generateRecovered')
    : reconcilingGenerate
      ? t('generateReconciling')
      : null;
  const effectiveClaudeCallId = claudeCallId ?? activeDraft?.claude_call_id ?? null;
  const publishLabel = canPublish ? t('allClear') : t('publishBlocked');
  const publishDescriptor = currentSession?.published_workflow_id
    ? `${currentSession.published_workflow_id}@${currentSession.published_version}`
    : t('notPublished');

  const summary = useMemo(
    () => [
      {
        label: t('summary.sessions'),
        value: sessions.length,
      },
      {
        label: t('summary.revisions'),
        value: draftList.length,
      },
      {
        label: t('summary.blockingIssues'),
        value: blockingCount,
      },
    ],
    [blockingCount, draftList.length, sessions.length, t]
  );

  const submitCreateSession = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setReconcilingGenerate(false);
    setPendingGenerateReconcile(null);
    setClaudeCallId(null);
    try {
      await createSessionMutation.mutateAsync({ title, intent_brief: intentBrief });
    } catch (mutationError) {
      setError((mutationError as Error).message);
    }
  };

  const submitDraft = async (mode: 'save' | 'continue') => {
    if (!selectedSessionId) {
      setError(t('empty.selectSession'));
      return;
    }

    setError(null);
    setReconcilingGenerate(false);
    setPendingGenerateReconcile(null);
    setClaudeCallId(null);
    try {
      const draft = parseSpec(rawSpec);
      if (mode === 'save') {
        await saveDraftMutation.mutateAsync({
          sessionId: selectedSessionId,
          draft,
          note: instruction || undefined,
        });
      } else {
        await continueMutation.mutateAsync({
          sessionId: selectedSessionId,
          draft,
          note: instruction,
        });
      }
    } catch (mutationError) {
      notifyActionError(mode === 'save' ? 'save' : 'continue', mutationError, pushToast, t);
      setError((mutationError as Error).message);
    }
  };

  const submitGenerate = async () => {
    if (!selectedSessionId) {
      setError(t('empty.selectSession'));
      return;
    }
    if (!instruction.trim()) {
      setError(t('empty.instruction'));
      return;
    }

    setError(null);
    setReconcilingGenerate(false);
    try {
      const draft = parseSpec(rawSpec);
      const callId = buildClaudeCallId('claude_authoring');
      setClaudeCallId(callId);
      setPendingGenerateReconcile({
        sessionId: selectedSessionId,
        requestedCallId: callId,
        baselineRevision: activeDraft?.revision ?? null,
        startedAt: Date.now(),
      });
      await generateMutation.mutateAsync({
        sessionId: selectedSessionId,
        draft,
        note: instruction,
        callId,
      });
      setError(null);
    } catch (mutationError) {
      notifyActionError('generate', mutationError, pushToast, t);
      setError((mutationError as Error).message);
      setReconcilingGenerate(true);
      setRawSpecBuffer({
        sessionId: selectedSessionId,
        value: rawSpec,
        mode: 'synced',
      });
      await invalidateSession(selectedSessionId);
    }
  };

  const handlePublish = async () => {
    if (!selectedSessionId || !activeDraft) {
      return;
    }
    setError(null);
    try {
      await publishMutation.mutateAsync({
        sessionId: selectedSessionId,
        revision: activeDraft.revision,
      });
    } catch (mutationError) {
      notifyActionError('publish', mutationError, pushToast, t);
      setError((mutationError as Error).message);
    }
  };

  const handleSelectSession = (sessionId: string) => {
    setManualSelectedSessionId(sessionId);
    setPendingGenerateReconcile(null);
    setReconcilingGenerate(false);
    setError(null);
    setClaudeCallId(null);
  };

  const handleRawSpecChange = (value: string) => {
    setRawSpecBuffer({
      sessionId: selectedSessionId,
      value,
      mode: 'manual',
    });
  };

  return (
    <div className="relative min-h-full overflow-hidden bg-[#f4efe6]">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-[radial-gradient(circle_at_top_left,rgba(245,158,11,0.18),transparent_58%),radial-gradient(circle_at_top_right,rgba(120,113,108,0.14),transparent_44%)]" />
      <div className="pointer-events-none absolute inset-0 opacity-40 [background-image:linear-gradient(rgba(120,113,108,0.06)_1px,transparent_1px),linear-gradient(90deg,rgba(120,113,108,0.06)_1px,transparent_1px)] [background-size:26px_26px]" />

      <div className="relative mx-auto flex min-h-full max-w-[1820px] flex-col gap-5 p-4 lg:p-6">
        <section className="overflow-hidden rounded-[2.2rem] border border-stone-200/80 bg-[linear-gradient(135deg,rgba(255,252,247,0.96),rgba(246,240,231,0.92))] p-5 shadow-[0_24px_70px_-42px_rgba(68,64,60,0.42)]">
          <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px] xl:items-start">
            <div>
              <div className="flex items-center gap-2">
                <p className="text-[0.72rem] font-semibold tracking-[0.26em] text-stone-500">
                  {t('title')}
                </p>
                <HelpTooltip content={t('description')} label={t('title')} />
              </div>
              <h1 className="mt-3 text-3xl font-semibold tracking-[-0.04em] text-stone-950 sm:text-[2.15rem]">
                {t('heroTitle')}
              </h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-stone-600">
                {t('subtitle')}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <span className="rounded-full border border-stone-200 bg-white/70 px-3 py-1 text-[11px] font-medium text-stone-700">
                  01 · {t('heroSteps.session')}
                </span>
                <span className="rounded-full border border-stone-200 bg-white/70 px-3 py-1 text-[11px] font-medium text-stone-700">
                  02 · {t('heroSteps.guide')}
                </span>
                <span className="rounded-full border border-stone-200 bg-white/70 px-3 py-1 text-[11px] font-medium text-stone-700">
                  03 · {t('heroSteps.publish')}
                </span>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-3">
              {summary.map((item) => (
                <div
                  key={item.label}
                  className="rounded-[1.45rem] border border-stone-200/80 bg-white/82 px-4 py-4 shadow-[0_18px_32px_-28px_rgba(68,64,60,0.4)]"
                >
                  <p className="text-xs font-medium tracking-[0.12em] text-stone-500">
                    {item.label}
                  </p>
                  <p className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-stone-950 tabular-nums">
                    {item.value}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <div className="grid min-h-0 flex-1 gap-5 xl:grid-cols-[320px_minmax(0,1.55fr)_360px]">
          <aside className="flex min-h-0 flex-col gap-5">
            <section className={classNames(PANEL_CLASS, 'flex min-h-0 flex-col overflow-hidden')}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <p className="text-[0.72rem] font-semibold tracking-[0.18em] text-stone-500">
                    {t('sessionExplorer')}
                  </p>
                  <HelpTooltip content={t('sessionExplorerHint')} label={t('sessionExplorer')} />
                </div>
                <span className="rounded-full bg-stone-100 px-3 py-1 text-xs font-medium text-stone-600">
                  {t('total', { count: sessions.length })}
                </span>
              </div>

              <div className="mt-5 min-h-0 flex-1 space-y-3 overflow-auto pr-1">
                {sessionsQuery.isLoading && sessions.length === 0 ? (
                  Array.from({ length: 3 }).map((_, index) => (
                    <div
                      key={`session-skeleton-${index}`}
                      className="animate-pulse rounded-[1.65rem] border border-stone-200/70 bg-stone-100/80 p-4"
                    >
                      <div className="h-4 w-2/3 rounded-full bg-stone-200" />
                      <div className="mt-3 h-3 w-1/2 rounded-full bg-stone-200" />
                      <div className="mt-5 grid grid-cols-2 gap-2">
                        <div className="h-14 rounded-2xl bg-white" />
                        <div className="h-14 rounded-2xl bg-white" />
                      </div>
                    </div>
                  ))
                ) : sessions.length === 0 ? (
                  <div className="rounded-[1.65rem] border border-dashed border-stone-300 bg-stone-50 px-4 py-6 text-sm leading-6 text-stone-500">
                    {t('sessionEmpty')}
                  </div>
                ) : (
                  sessions.map((session) => {
                    const isActive = selectedSessionId === session.session_id;
                    const revisionValue = session.latest_revision ?? '-';
                    const draftCountValue = session.draft_count ?? '-';

                    return (
                      <button
                        key={session.session_id}
                        type="button"
                        onClick={() => handleSelectSession(session.session_id)}
                        className={classNames(
                          'w-full rounded-[1.65rem] border px-4 py-4 text-left transition duration-200',
                          isActive
                            ? 'border-amber-300 bg-amber-50 shadow-[0_20px_40px_-30px_rgba(245,158,11,0.8)]'
                            : 'border-stone-200 bg-white hover:-translate-y-0.5 hover:border-stone-300 hover:bg-stone-50'
                        )}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="truncate text-base font-semibold tracking-[-0.02em] text-stone-950">
                              {session.title}
                            </p>
                            <p className="mt-2 text-xs text-stone-500 tabular-nums">
                              {t('updated')} {formatTimestamp(session.updated_at)}
                            </p>
                          </div>
                          <div className="flex flex-col items-end gap-2">
                            <span className="rounded-full bg-stone-950 px-2.5 py-1 text-[11px] font-medium text-white">
                              {session.status}
                            </span>
                            {isActive ? (
                              <span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-medium text-stone-700">
                                {t('selectedBadge')}
                              </span>
                            ) : null}
                          </div>
                        </div>

                        <div className="mt-4 grid gap-2 sm:grid-cols-2">
                          <div className="rounded-2xl bg-white/90 px-3 py-3">
                            <p className="text-[11px] font-medium tracking-[0.12em] text-stone-500">
                              {t('latestRevision')}
                            </p>
                            <p className="mt-1 text-sm font-semibold text-stone-900 tabular-nums">
                              {revisionValue}
                            </p>
                          </div>
                          <div className="rounded-2xl bg-white/90 px-3 py-3">
                            <p className="text-[11px] font-medium tracking-[0.12em] text-stone-500">
                              {t('draftCount')}
                            </p>
                            <p className="mt-1 text-sm font-semibold text-stone-900 tabular-nums">
                              {draftCountValue}
                            </p>
                          </div>
                        </div>

                        <p className="mt-3 truncate text-xs text-stone-500">
                          {session.published_workflow_id
                            ? `${session.published_workflow_id}@${session.published_version}`
                            : t('notPublished')}
                        </p>
                      </button>
                    );
                  })
                )}
              </div>
            </section>

            <section className={classNames(PANEL_CLASS, 'bg-[linear-gradient(180deg,rgba(255,251,244,0.95),rgba(250,247,241,0.92))]')}>
              <div className="flex items-center gap-2">
                <p className="text-[0.72rem] font-semibold tracking-[0.18em] text-stone-500">
                  {t('newSession')}
                </p>
                <HelpTooltip content={t('help.newSession')} label={t('newSession')} />
              </div>

              <form className="mt-5 space-y-4" onSubmit={submitCreateSession}>
                <label className="block space-y-2">
                  <span className="text-xs font-medium tracking-[0.12em] text-stone-600">
                    {t('field.sessionTitle')}
                  </span>
                  <input
                    className="h-11 w-full rounded-[1rem] border border-stone-200 bg-white/90 px-4 text-sm text-stone-900 placeholder:text-stone-400"
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                    placeholder={t('placeholder.sessionTitle')}
                  />
                </label>

                <label className="block space-y-2">
                  <span className="text-xs font-medium tracking-[0.12em] text-stone-600">
                    {t('field.intentBrief')}
                  </span>
                  <textarea
                    className="min-h-28 w-full rounded-[1.3rem] border border-stone-200 bg-white/90 px-4 py-3 text-sm text-stone-900 placeholder:text-stone-400"
                    value={intentBrief}
                    onChange={(event) => setIntentBrief(event.target.value)}
                    placeholder={t('placeholder.intentBrief')}
                  />
                </label>

                <ActionButton
                  type="submit"
                  variant="primary"
                  disabled={createSessionMutation.isPending}
                >
                  {t('createSession')}
                </ActionButton>
              </form>
            </section>
          </aside>

          <section className="flex min-h-0 flex-col gap-5">
            <section className={classNames(PANEL_CLASS, 'overflow-hidden bg-[linear-gradient(160deg,rgba(255,255,255,0.96),rgba(248,243,235,0.92))]')}>
              <div className="grid gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full border border-stone-200 bg-white/80 px-3 py-1.5 text-xs font-medium text-stone-600">
                      {t('currentCycle')}
                    </span>
                    {currentSession?.status ? (
                      <span className="rounded-full bg-stone-950 px-3 py-1.5 text-xs font-medium text-white">
                        {currentSession.status}
                      </span>
                    ) : null}
                  </div>

                  <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
                    <div className="min-w-0">
                      <h2 className="text-3xl font-semibold tracking-[-0.04em] text-stone-950 text-balance">
                        {currentSession?.title || t('empty.noSession')}
                      </h2>
                      <p className="mt-3 max-w-2xl text-sm leading-7 text-stone-600">
                        {currentSession?.intent_brief || t('empty.selectSession')}
                      </p>
                    </div>
                    <div className="rounded-[1.4rem] border border-stone-200/80 bg-white/80 px-4 py-3 text-sm text-stone-700">
                      <p className="text-xs font-medium tracking-[0.12em] text-stone-500">
                        {t('publishedVersion')}
                      </p>
                      <p className="mt-1 font-semibold text-stone-950">{publishDescriptor}</p>
                    </div>
                  </div>

                  <div className="mt-5 grid gap-3 sm:grid-cols-3">
                    <div className="rounded-[1.4rem] border border-stone-200/80 bg-white/80 px-4 py-4">
                      <p className="text-[11px] font-medium tracking-[0.12em] text-stone-500">
                        {t('latestRevision')}
                      </p>
                      <p className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-stone-950 tabular-nums">
                        {activeDraft?.revision ?? '-'}
                      </p>
                    </div>
                    <div className="rounded-[1.4rem] border border-stone-200/80 bg-white/80 px-4 py-4">
                      <p className="text-[11px] font-medium tracking-[0.12em] text-stone-500">
                        {t('warnings')}
                      </p>
                      <p className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-stone-950 tabular-nums">
                        {warningCount}
                      </p>
                    </div>
                    <div className="rounded-[1.4rem] border border-stone-200/80 bg-white/80 px-4 py-4">
                      <p className="text-[11px] font-medium tracking-[0.12em] text-stone-500">
                        {t('summary.blockingIssues')}
                      </p>
                      <p className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-stone-950 tabular-nums">
                        {blockingCount}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="rounded-[1.8rem] border border-stone-200/80 bg-white/80 p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.85)]">
                  <div className="flex items-center gap-2">
                    <p className="text-[0.72rem] font-semibold tracking-[0.18em] text-stone-500">
                      {t('instruction')}
                    </p>
                    <HelpTooltip content={t('instructionHint')} label={t('instruction')} />
                  </div>

                  <textarea
                    className="mt-4 min-h-36 w-full rounded-[1.4rem] border border-stone-200 bg-[#faf7f2] px-4 py-3 text-sm leading-6 text-stone-900 placeholder:text-stone-400"
                    value={instruction}
                    onChange={(event) => setInstruction(event.target.value)}
                    placeholder={t('placeholder.instruction')}
                  />

                  <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    <ActionButton
                      onClick={() => submitDraft('save')}
                      disabled={!selectedSessionId || saveDraftMutation.isPending}
                      variant="secondary"
                    >
                      {t('saveDraft')}
                    </ActionButton>
                    <ActionButton
                      onClick={() => submitDraft('continue')}
                      disabled={!selectedSessionId || continueMutation.isPending}
                      variant="primary"
                    >
                      {t('continue')}
                    </ActionButton>
                    <ActionButton
                      onClick={submitGenerate}
                      disabled={!selectedSessionId || generateMutation.isPending}
                      variant="accent"
                    >
                      {t('generate')}
                    </ActionButton>
                    <ActionButton
                      onClick={handlePublish}
                      disabled={!selectedSessionId || !activeDraft || !canPublish || publishMutation.isPending}
                      variant="ghost"
                    >
                      {t('publish')}
                    </ActionButton>
                  </div>

                  {statusMessage ? (
                    <p className="mt-4 rounded-[1.25rem] border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-950">
                      {statusMessage}
                    </p>
                  ) : null}
                  {error ? (
                    <p className="mt-4 rounded-[1.25rem] border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-900">
                      {error}
                    </p>
                  ) : null}
                </div>
              </div>
            </section>

            <div className="grid min-h-0 flex-1 gap-5 2xl:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
              <section className={classNames(PANEL_CLASS, 'flex min-h-[34rem] flex-col')}>
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="flex items-center gap-2">
                    <p className="text-[0.72rem] font-semibold tracking-[0.18em] text-stone-500">
                      {t('latestDraft')}
                    </p>
                    <HelpTooltip content={t('latestDraftHint')} label={t('latestDraft')} />
                  </div>
                  <div className="rounded-[1.2rem] border border-stone-200 bg-stone-50 px-4 py-3 text-right text-xs text-stone-600">
                    <p className="font-medium tracking-[0.12em] text-stone-500">
                      {t('revisionInfo', {
                        revision: activeDraft?.revision ?? '-',
                        time: formatTimestamp(activeDraft?.created_at),
                      })}
                    </p>
                  </div>
                </div>

                <div className="mt-5 min-h-0 flex-1 overflow-hidden rounded-[1.75rem] border border-stone-200/80 bg-[#f7f3ec]">
                  <CodeMirror
                    value={rawSpec}
                    extensions={[json()]}
                    basicSetup={{ lineNumbers: true }}
                    height="100%"
                    onChange={handleRawSpecChange}
                    className="h-full text-xs"
                  />
                </div>
              </section>

              <section className={classNames(PANEL_CLASS, 'flex min-h-[34rem] flex-col overflow-hidden')}>
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="flex items-center gap-2">
                    <p className="text-[0.72rem] font-semibold tracking-[0.18em] text-stone-500">
                      {t('workflowPreview')}
                    </p>
                    <HelpTooltip content={t('workflowPreviewHint')} label={t('workflowPreview')} />
                  </div>
                  <div
                    className={classNames(
                      'rounded-full px-3 py-1.5 text-xs font-medium',
                      canPublish ? 'bg-amber-100 text-amber-950' : 'bg-stone-100 text-stone-700'
                    )}
                  >
                    {publishLabel}
                  </div>
                </div>

                <div className="mt-5 min-h-0 flex-1 overflow-hidden rounded-[1.75rem] border border-stone-200/80 bg-white">
                  {activeDraft ? (
                    <WorkflowWorkspace
                      spec={activeDraft.spec_json}
                      cards={activeDraft.workflow_view.cards}
                      nodes={activeDraft.graph.nodes as never[]}
                      edges={activeDraft.graph.edges as never[]}
                      lintWarnings={activeDraft.lint_report.warnings}
                      lintErrors={activeDraft.lint_report.errors}
                      inputEditor={
                        <WorkflowInputEditor
                          rawSpec={rawSpec}
                          onChange={handleRawSpecChange}
                          compact
                        />
                      }
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center px-6 text-center text-sm leading-6 text-stone-500">
                      {t('empty.workspaceHint')}
                    </div>
                  )}
                </div>
              </section>
            </div>
          </section>

          <aside className="flex min-h-0 flex-col gap-5">
            <section
              className={classNames(
                PANEL_CLASS,
                'bg-[linear-gradient(180deg,rgba(255,251,244,0.95),rgba(255,255,255,0.92))]'
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <p className="text-[0.72rem] font-semibold tracking-[0.18em] text-stone-500">
                    {t('publishReadiness')}
                  </p>
                  <HelpTooltip
                    content={t('publishReadinessHint')}
                    label={t('publishReadiness')}
                  />
                </div>
                <span
                  className={classNames(
                    'rounded-full px-3 py-1.5 text-xs font-medium',
                    canPublish ? 'bg-amber-100 text-amber-950' : 'bg-stone-100 text-stone-700'
                  )}
                >
                  {publishLabel}
                </span>
              </div>

              <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                <div className="rounded-[1.4rem] border border-stone-200/80 bg-white/85 px-4 py-4">
                  <p className="text-[11px] font-medium tracking-[0.12em] text-stone-500">
                    {t('summary.blockingIssues')}
                  </p>
                  <p className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-stone-950 tabular-nums">
                    {blockingCount}
                  </p>
                </div>
                <div className="rounded-[1.4rem] border border-stone-200/80 bg-white/85 px-4 py-4">
                  <p className="text-[11px] font-medium tracking-[0.12em] text-stone-500">
                    {t('warnings')}
                  </p>
                  <p className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-stone-950 tabular-nums">
                    {warningCount}
                  </p>
                </div>
                <div className="rounded-[1.4rem] border border-stone-200/80 bg-white/85 px-4 py-4">
                  <p className="text-[11px] font-medium tracking-[0.12em] text-stone-500">
                    {t('publishedVersion')}
                  </p>
                  <p className="mt-2 text-sm font-semibold leading-6 text-stone-950">
                    {publishDescriptor}
                  </p>
                </div>
              </div>

              <div className="mt-5">
                <ActionButton
                  onClick={handlePublish}
                  disabled={!selectedSessionId || !activeDraft || !canPublish || publishMutation.isPending}
                  variant="primary"
                >
                  {t('publish')}
                </ActionButton>
              </div>
            </section>

            <section className={classNames(PANEL_CLASS, 'flex min-h-0 flex-col overflow-hidden')}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <p className="text-[0.72rem] font-semibold tracking-[0.18em] text-stone-500">
                    {t('revisionHistory')}
                  </p>
                  <HelpTooltip
                    content={t('help.revisionHistory')}
                    label={t('revisionHistory')}
                  />
                </div>
                <span className="rounded-full bg-stone-100 px-3 py-1 text-xs font-medium text-stone-600">
                  {draftList.length}
                </span>
              </div>

              <div className="mt-5 min-h-0 flex-1 space-y-3 overflow-auto pr-1">
                {draftList.length === 0 ? (
                  <div className="rounded-[1.65rem] border border-dashed border-stone-300 bg-stone-50 px-4 py-6 text-sm leading-6 text-stone-500">
                    {t('historyEmpty')}
                  </div>
                ) : (
                  draftList.map((draft) => (
                    <button
                      key={draft.revision}
                      type="button"
                      onClick={() =>
                        setRawSpecBuffer({
                          sessionId: selectedSessionId,
                          value: prettyJson(draft.spec_json),
                          mode: 'manual',
                        })
                      }
                      className="w-full rounded-[1.65rem] border border-stone-200 bg-white px-4 py-4 text-left transition duration-200 hover:-translate-y-0.5 hover:border-stone-300 hover:bg-stone-50"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-base font-semibold tracking-[-0.02em] text-stone-950">
                            {t('revision')} {draft.revision}
                          </p>
                          <p className="mt-2 text-xs text-stone-500 tabular-nums">
                            {formatTimestamp(draft.created_at)}
                          </p>
                        </div>
                        <span
                          className={classNames(
                            'rounded-full px-2.5 py-1 text-[11px] font-medium',
                            draft.lint_report.blocking
                              ? 'bg-stone-100 text-stone-700'
                              : 'bg-amber-100 text-amber-950'
                          )}
                        >
                          {draft.lint_report.blocking ? t('status.blocking') : t('status.ready')}
                        </span>
                      </div>
                      <p className="mt-4 text-xs font-medium tracking-[0.12em] text-stone-500">
                        {t('loadRevision')}
                      </p>
                    </button>
                  ))
                )}
              </div>
            </section>

            <section className={classNames(PANEL_CLASS, 'flex min-h-0 flex-col overflow-hidden')}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <p className="text-[0.72rem] font-semibold tracking-[0.18em] text-stone-500">
                    {t('messages')}
                  </p>
                  <HelpTooltip content={t('help.messages')} label={t('messages')} />
                </div>
                <span className="rounded-full bg-stone-100 px-3 py-1 text-xs font-medium text-stone-600">
                  {messages.length}
                </span>
              </div>

              <div className="mt-5 min-h-0 flex-1 space-y-3 overflow-auto pr-1">
                {messages.length === 0 ? (
                  <div className="rounded-[1.65rem] border border-dashed border-stone-300 bg-stone-50 px-4 py-6 text-sm leading-6 text-stone-500">
                    {t('messageEmpty')}
                  </div>
                ) : (
                  messages.map((message) => (
                    <div
                      key={message.id}
                      className={classNames(
                        'rounded-[1.65rem] px-4 py-4',
                        message.role === 'system'
                          ? 'bg-stone-950 text-white'
                          : 'border border-stone-200 bg-stone-50 text-stone-800'
                      )}
                    >
                      <div className="flex items-center justify-between gap-2 text-[11px] font-medium tracking-[0.14em]">
                        <span>{message.role}</span>
                        <span className="tabular-nums">r{message.revision ?? '-'}</span>
                      </div>
                      <p className="mt-3 text-sm leading-6">{message.content}</p>
                    </div>
                  ))
                )}
              </div>
            </section>

            <ClaudeTerminalPanel
              callId={effectiveClaudeCallId}
              title={tClaude('authoringTitle')}
            />
          </aside>
        </div>
      </div>
    </div>
  );
}
