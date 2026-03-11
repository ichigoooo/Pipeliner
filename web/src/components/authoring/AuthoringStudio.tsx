'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useSearchParams } from 'next/navigation';
import CodeMirror from '@uiw/react-codemirror';
import { json } from '@codemirror/lang-json';
import { api, AuthoringDraft, AuthoringSession } from '@/lib/api';
import { formatTimestamp, prettyJson } from '@/lib/format';
import { WorkflowWorkspace } from '@/components/workflow/WorkflowWorkspace';

function parseSpec(value: string) {
  return JSON.parse(value) as Record<string, unknown>;
}

export function AuthoringStudio() {
  const t = useTranslations('authoring');
  const searchParams = useSearchParams();
  const sessionFromQuery = searchParams.get('session');
  const queryClient = useQueryClient();
  const sessionsQuery = useQuery({
    queryKey: ['authoring-sessions'],
    queryFn: api.listAuthoringSessions,
    refetchInterval: 10_000,
  });

  const sessions = sessionsQuery.data?.sessions ?? [];
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [queryApplied, setQueryApplied] = useState(false);
  const [title, setTitle] = useState('Developer Workflow Studio');
  const [intentBrief, setIntentBrief] = useState(
    'Author a developer-first pipeline with inspectable drafts and settings provenance.'
  );
  const [instruction, setInstruction] = useState(
    'Refine the workflow while keeping workflow spec as the only canonical source.'
  );
  const [rawSpec, setRawSpec] = useState('{}');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (sessionFromQuery && !queryApplied) {
      setSelectedSessionId(sessionFromQuery);
      setQueryApplied(true);
      return;
    }
    if (!selectedSessionId && sessions.length > 0) {
      setSelectedSessionId(sessions[0].session_id);
    }
  }, [queryApplied, sessionFromQuery, sessions, selectedSessionId]);

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

  useEffect(() => {
    if (!draftQuery.data) {
      return;
    }
    setRawSpec(prettyJson(draftQuery.data.spec_json));
  }, [draftQuery.data?.revision]);

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
      setSelectedSessionId(payload.session_id);
      await invalidateSession(payload.session_id);
    },
  });

  const saveDraftMutation = useMutation({
    mutationFn: ({ sessionId, draft, note }: { sessionId: string; draft: Record<string, unknown>; note?: string }) =>
      api.saveDraft(sessionId, { spec: draft, instruction: note }),
    onSuccess: async (payload) => {
      setRawSpec(prettyJson(payload.spec_json));
      await invalidateSession(payload.session_id);
    },
  });

  const continueMutation = useMutation({
    mutationFn: ({ sessionId, draft, note }: { sessionId: string; draft: Record<string, unknown>; note: string }) =>
      api.continueSession(sessionId, { spec: draft, instruction: note }),
    onSuccess: async (payload) => {
      setRawSpec(prettyJson(payload.spec_json));
      await invalidateSession(payload.session_id);
    },
  });

  const generateMutation = useMutation({
    mutationFn: ({ sessionId, draft, note }: { sessionId: string; draft: Record<string, unknown>; note: string }) =>
      api.generateDraft(sessionId, { spec: draft, instruction: note }),
    onSuccess: async (payload) => {
      setRawSpec(prettyJson(payload.spec_json));
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
  const canPublish = activeDraft ? !activeDraft.lint_report.blocking : false;
  const draftList = draftsQuery.data?.drafts ?? [];
  const messages = messagesQuery.data?.messages ?? [];

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
        value: activeDraft?.lint_report.errors.length ?? 0,
      },
    ],
    [activeDraft?.lint_report.errors.length, draftList.length, sessions.length, t]
  );

  const submitCreateSession = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
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
    try {
      const draft = parseSpec(rawSpec);
      await generateMutation.mutateAsync({
        sessionId: selectedSessionId,
        draft,
        note: instruction,
      });
    } catch (mutationError) {
      setError((mutationError as Error).message);
    }
  };

  return (
    <div className="grid h-full min-h-0 gap-4 overflow-hidden p-4 xl:grid-cols-[280px_minmax(520px,1.25fr)_minmax(320px,1fr)]">
      <section className="flex min-h-0 flex-col rounded-[2rem] border border-stone-200 bg-stone-950 p-5 text-white shadow-xl">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-stone-400">{t('title')}</p>
          <h1 className="mt-3 text-2xl font-semibold">{t('subtitle')}</h1>
          <p className="mt-3 text-sm leading-6 text-stone-300">{t('description')}</p>
        </div>

        <div className="mt-6 grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
          {summary.map((item) => (
            <div key={item.label} className="rounded-3xl border border-white/10 bg-white/5 px-4 py-3">
              <p className="text-xs uppercase tracking-[0.24em] text-stone-400">{item.label}</p>
              <p className="mt-2 text-2xl font-semibold">{item.value}</p>
            </div>
          ))}
        </div>

        <div className="mt-6 min-h-0 flex-1 overflow-auto">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">
              {t('sessions')}
            </h2>
            <span className="text-xs text-stone-500">{t('total', { count: sessions.length })}</span>
          </div>
          <div className="space-y-3">
            {sessions.map((session: AuthoringSession) => (
              <button
                key={session.session_id}
                type="button"
                onClick={() => setSelectedSessionId(session.session_id)}
                className={`w-full rounded-3xl border px-4 py-4 text-left transition ${
                  selectedSessionId === session.session_id
                    ? 'border-amber-300 bg-amber-300/10'
                    : 'border-white/10 bg-white/5 hover:border-white/30'
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <h3 className="font-medium">{session.title}</h3>
                  <span className="rounded-full bg-white/10 px-2 py-1 text-[11px] uppercase tracking-[0.18em] text-stone-300">
                    {session.status}
                  </span>
                </div>
                <p className="mt-2 text-xs text-stone-400">
                  {t('updated')} {formatTimestamp(session.updated_at)}
                </p>
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="flex min-h-0 flex-col overflow-hidden">
        <div className="grid min-h-0 flex-1 grid-rows-[auto_auto_auto_1fr] gap-4 overflow-auto pb-4 pr-2">
          <div className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
            <p className="text-xs uppercase tracking-[0.24em] text-stone-500">{t('newSession')}</p>
            <p className="mt-2 text-xs text-stone-500">{t('help.newSession')}</p>
            <form className="mt-4 space-y-4" onSubmit={submitCreateSession}>
              <div className="space-y-2">
                <label className="text-xs font-semibold uppercase tracking-[0.24em] text-stone-500">
                  {t('field.sessionTitle')}
                </label>
                <p className="text-xs text-stone-500">{t('help.sessionTitle')}</p>
                <input
                  className="h-11 w-full rounded-2xl border border-stone-200 bg-stone-50 px-4 text-sm text-stone-900 outline-none placeholder:text-stone-400"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder={t('placeholder.sessionTitle')}
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-semibold uppercase tracking-[0.24em] text-stone-500">
                  {t('field.intentBrief')}
                </label>
                <p className="text-xs text-stone-500">{t('help.intentBrief')}</p>
                <textarea
                  className="min-h-28 w-full rounded-3xl border border-stone-200 bg-stone-50 px-4 py-3 text-sm text-stone-900 outline-none placeholder:text-stone-400"
                  value={intentBrief}
                  onChange={(event) => setIntentBrief(event.target.value)}
                  placeholder={t('placeholder.intentBrief')}
                />
              </div>
              <button
                type="submit"
                className="w-full rounded-full bg-stone-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-stone-800"
              >
                {t('createSession')}
              </button>
            </form>
          </div>

          <div className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-stone-500">{t('selectedSession')}</p>
                <h2 className="mt-2 text-xl font-semibold text-stone-900">
                  {currentSession?.title || t('empty.noSession')}
                </h2>
                <p className="mt-3 text-sm leading-6 text-stone-600">
                  {currentSession?.intent_brief || t('empty.selectSession')}
                </p>
              </div>
              {currentSession?.published_workflow_id ? (
                <div className="rounded-3xl bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
                  {t('published')} {currentSession.published_workflow_id}@{currentSession.published_version}
                </div>
              ) : null}
            </div>
          </div>

          <div className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
            <label className="text-xs font-semibold uppercase tracking-[0.24em] text-stone-500">
              {t('instruction')}
            </label>
            <p className="mt-2 text-xs text-stone-500">{t('help.instruction')}</p>
            <textarea
              className="mt-3 min-h-28 w-full rounded-3xl border border-stone-200 bg-stone-50 px-4 py-3 text-sm text-stone-900 outline-none"
              value={instruction}
              onChange={(event) => setInstruction(event.target.value)}
            />
            <div className="mt-4 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => submitDraft('save')}
                className="rounded-full border border-stone-300 px-4 py-2 text-sm font-medium text-stone-800 transition hover:border-stone-900"
              >
                {t('saveDraft')}
              </button>
              <button
                type="button"
                onClick={() => submitDraft('continue')}
                className="rounded-full bg-stone-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-stone-800"
              >
                {t('continue')}
              </button>
              <button
                type="button"
                onClick={submitGenerate}
                disabled={!selectedSessionId || generateMutation.isPending}
                className="rounded-full border border-amber-300 px-4 py-2 text-sm font-medium text-amber-900 transition hover:border-amber-400 disabled:cursor-not-allowed disabled:border-stone-200 disabled:text-stone-400"
              >
                {t('generate')}
              </button>
              <button
                type="button"
                disabled={!selectedSessionId || !activeDraft || !canPublish}
                onClick={() =>
                  selectedSessionId &&
                  activeDraft &&
                  publishMutation.mutate({ sessionId: selectedSessionId, revision: activeDraft.revision })
                }
                className="rounded-full bg-amber-300 px-4 py-2 text-sm font-semibold text-stone-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:bg-stone-200"
              >
                {t('publish')}
              </button>
            </div>
            {error ? <p className="mt-3 text-sm text-rose-700">{error}</p> : null}
          </div>

          <div className="grid min-h-0 gap-4 pb-2 lg:grid-cols-[minmax(0,1fr)_280px]">
          <div className="flex min-h-0 flex-col rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-stone-500">{t('canonicalSpec')}</p>
                <p className="mt-2 text-xs text-stone-500">{t('help.canonicalSpec')}</p>
                <p className="mt-2 text-sm text-stone-600">
                  {t('revisionInfo', { revision: activeDraft?.revision ?? '-', time: formatTimestamp(activeDraft?.created_at) })}
                </p>
              </div>
            </div>
            <div className="mt-4 min-h-[320px] flex-1 overflow-hidden rounded-[1.75rem] border border-stone-200 bg-stone-50">
              <CodeMirror
                value={rawSpec}
                extensions={[json()]}
                basicSetup={{ lineNumbers: true }}
                height="100%"
                onChange={(value) => setRawSpec(value)}
                className="h-full text-xs"
              />
            </div>
          </div>

          <div className="grid min-h-0 grid-rows-[minmax(220px,1fr)_minmax(220px,1fr)] gap-4">
            <div className="min-h-0 overflow-auto rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
              <h3 className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-500">
                {t('messages')}
              </h3>
              <p className="mt-2 text-xs text-stone-500">{t('help.messages')}</p>
              <div className="mt-4 space-y-3">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`rounded-3xl px-4 py-3 text-sm ${
                      message.role === 'system'
                        ? 'bg-stone-900 text-white'
                        : 'bg-stone-100 text-stone-800'
                    }`}
                  >
                    <div className="mb-1 flex items-center justify-between gap-2 text-[11px] uppercase tracking-[0.18em]">
                      <span>{message.role}</span>
                      <span>r{message.revision ?? '-'}</span>
                    </div>
                    <p className="leading-6">{message.content}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="min-h-0 overflow-auto rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
              <h3 className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-500">
                {t('revisionHistory')}
              </h3>
              <p className="mt-2 text-xs text-stone-500">{t('help.revisionHistory')}</p>
              <div className="mt-4 space-y-3">
                {draftList.map((draft) => (
                  <button
                    key={draft.revision}
                    type="button"
                    onClick={() => setRawSpec(prettyJson(draft.spec_json))}
                    className="w-full rounded-3xl border border-stone-200 px-4 py-3 text-left transition hover:border-amber-500"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-medium text-stone-900">
                        {t('revision')} {draft.revision}
                      </span>
                      <span className="text-xs uppercase tracking-[0.18em] text-stone-500">
                        {draft.lint_report.blocking ? t('status.blocking') : t('status.ready')}
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-stone-500">{formatTimestamp(draft.created_at)}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
        </div>
      </section>

      <section className="min-h-0 rounded-[2rem] border border-stone-200 bg-white shadow-sm">
        {activeDraft ? (
          <WorkflowWorkspace
            spec={activeDraft.spec_json}
            cards={activeDraft.workflow_view.cards}
            nodes={activeDraft.graph.nodes as never[]}
            edges={activeDraft.graph.edges as never[]}
            lintWarnings={activeDraft.lint_report.warnings}
            lintErrors={activeDraft.lint_report.errors}
          />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-stone-500">
            {t('empty.workspaceHint')}
          </div>
        )}
      </section>
    </div>
  );
}
