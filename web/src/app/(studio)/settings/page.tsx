'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { api, SettingValue } from '@/lib/api';
import { prettyJson } from '@/lib/format';
import { LanguageSelector } from './components/LanguageSelector';

function SettingRow<T>({ label, setting }: { label: string; setting: SettingValue<T> }) {
  return (
    <div className="grid gap-2 rounded-3xl border border-stone-200 bg-stone-50 px-4 py-4 text-sm text-stone-700 md:grid-cols-[180px_minmax(0,1fr)_120px]">
      <div className="font-medium text-stone-900">{label}</div>
      <div className="break-all">{String(setting.value)}</div>
      <div className="text-xs uppercase tracking-[0.18em] text-stone-500">{setting.source}</div>
    </div>
  );
}

function SettingsSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-500">{title}</h2>
      <div className="mt-4 space-y-3">{children}</div>
    </section>
  );
}

export default function SettingsPage() {
  const t = useTranslations('settings');
  const settingsQuery = useQuery({
    queryKey: ['settings'],
    queryFn: api.getSettings,
  });

  const settings = settingsQuery.data?.settings;

  if (!settings) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-stone-500">
        {t('loading')}
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8">
      <div className="mb-8">
        <p className="text-xs uppercase tracking-[0.26em] text-stone-500">{t('title')}</p>
        <h1 className="mt-3 text-3xl font-semibold text-stone-900">{t('subtitle')}</h1>
        <p className="mt-3 text-sm leading-6 text-stone-600">{t('description')}</p>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-4">
          <SettingsSection title={t('sections.commandTemplates')}>
            <SettingRow label={t('labels.executor')} setting={settings.executor_command} />
            <SettingRow label={t('labels.validator')} setting={settings.validator_command} />
          </SettingsSection>

          <SettingsSection title={t('sections.storageDatabase')}>
            <SettingRow label={t('labels.storageBackend')} setting={settings.storage.backend} />
            <SettingRow label={t('labels.dataDir')} setting={settings.storage.data_dir} />
            <SettingRow label={t('labels.runRoot')} setting={settings.storage.run_root} />
            <SettingRow label={t('labels.databaseUrl')} setting={settings.database.url} />
            <SettingRow label={t('labels.databasePath')} setting={settings.database.path} />
          </SettingsSection>

          <SettingsSection title={t('sections.observability')}>
            <SettingRow label={t('labels.claudeTrace')} setting={settings.observability.claude_trace_enabled} />
            <p className="text-xs text-stone-500">{t('labels.claudeTraceHint')}</p>
          </SettingsSection>

          <SettingsSection title={t('sections.runtimeGuards')}>
            <SettingRow label={t('labels.defaultTimeout')} setting={settings.runtime_guards.default_timeout} />
            <SettingRow
              label={t('labels.maxReworkRounds')}
              setting={settings.runtime_guards.default_max_rework_rounds}
            />
            <SettingRow
              label={t('labels.blockedRequiresManual')}
              setting={settings.runtime_guards.blocked_requires_manual}
            />
            <SettingRow
              label={t('labels.failureRequiresManual')}
              setting={settings.runtime_guards.failure_requires_manual}
            />
          </SettingsSection>

          <SettingsSection title={t('language.title')}>
            <LanguageSelector />
          </SettingsSection>
        </div>

        <div className="space-y-4">
          <SettingsSection title={t('sections.providerBindings')}>
            {settings.providers.map((provider) => (
              <div key={`${provider.provider}-${provider.role}`} className="rounded-3xl bg-stone-50 p-4 text-sm">
                <p className="font-medium text-stone-900">
                  {provider.provider} / {provider.role}
                </p>
                <p className="mt-2 break-all text-stone-600">{provider.command_template.value}</p>
                <p className="mt-2 text-xs uppercase tracking-[0.18em] text-stone-500">
                  {provider.command_template.source}
                </p>
              </div>
            ))}
          </SettingsSection>

          <SettingsSection title={t('sections.observedSkills')}>
            {settings.skills.map((skill) => (
              <div key={skill.skill} className="rounded-3xl border border-stone-200 px-4 py-3 text-sm">
                <p className="font-medium text-stone-900">{skill.skill}</p>
                <p className="mt-2 text-stone-600">{skill.used_by.join(', ')}</p>
              </div>
            ))}
          </SettingsSection>

          <section className="rounded-[2rem] border border-stone-200 bg-stone-950 p-5 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">
              {t('sections.rawSnapshot')}
            </h2>
            <pre className="mt-4 overflow-auto text-xs leading-6 text-stone-100">
              {prettyJson(settings)}
            </pre>
          </section>
        </div>
      </div>
    </div>
  );
}
