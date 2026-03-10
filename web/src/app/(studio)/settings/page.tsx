'use client';

import { useQuery } from '@tanstack/react-query';
import { api, SettingValue } from '@/lib/api';
import { prettyJson } from '@/lib/format';

function SettingRow<T>({ label, setting }: { label: string; setting: SettingValue<T> }) {
  return (
    <div className="grid gap-2 rounded-3xl border border-stone-200 bg-stone-50 px-4 py-4 text-sm text-stone-700 md:grid-cols-[180px_minmax(0,1fr)_120px]">
      <div className="font-medium text-stone-900">{label}</div>
      <div className="break-all">{String(setting.value)}</div>
      <div className="text-xs uppercase tracking-[0.18em] text-stone-500">{setting.source}</div>
    </div>
  );
}

export default function SettingsPage() {
  const settingsQuery = useQuery({
    queryKey: ['settings'],
    queryFn: api.getSettings,
  });

  const settings = settingsQuery.data?.settings;

  if (!settings) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-stone-500">
        Loading settings snapshot...
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8">
      <div className="mb-8">
        <p className="text-xs uppercase tracking-[0.26em] text-stone-500">Settings</p>
        <h1 className="mt-3 text-3xl font-semibold text-stone-900">Resolved configuration + provenance</h1>
        <p className="mt-3 text-sm leading-6 text-stone-600">
          开发者可以直接看到当前生效值，以及它来自 `default` 还是 `env`。
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-4">
          <section className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-500">
              Command templates
            </h2>
            <div className="mt-4 space-y-3">
              <SettingRow label="Executor" setting={settings.executor_command} />
              <SettingRow label="Validator" setting={settings.validator_command} />
            </div>
          </section>

          <section className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-500">
              Storage + database
            </h2>
            <div className="mt-4 space-y-3">
              <SettingRow label="Storage backend" setting={settings.storage.backend} />
              <SettingRow label="Data dir" setting={settings.storage.data_dir} />
              <SettingRow label="Run root" setting={settings.storage.run_root} />
              <SettingRow label="Database URL" setting={settings.database.url} />
              <SettingRow label="Database path" setting={settings.database.path} />
            </div>
          </section>

          <section className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-500">
              Runtime guards
            </h2>
            <div className="mt-4 space-y-3">
              <SettingRow label="Default timeout" setting={settings.runtime_guards.default_timeout} />
              <SettingRow
                label="Max rework rounds"
                setting={settings.runtime_guards.default_max_rework_rounds}
              />
              <SettingRow
                label="Blocked requires manual"
                setting={settings.runtime_guards.blocked_requires_manual}
              />
              <SettingRow
                label="Failure requires manual"
                setting={settings.runtime_guards.failure_requires_manual}
              />
            </div>
          </section>
        </div>

        <div className="space-y-4">
          <section className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-500">
              Provider bindings
            </h2>
            <div className="mt-4 space-y-3">
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
            </div>
          </section>

          <section className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-500">
              Observed skills
            </h2>
            <div className="mt-4 space-y-3">
              {settings.skills.map((skill) => (
                <div key={skill.skill} className="rounded-3xl border border-stone-200 px-4 py-3 text-sm">
                  <p className="font-medium text-stone-900">{skill.skill}</p>
                  <p className="mt-2 text-stone-600">{skill.used_by.join(', ')}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-[2rem] border border-stone-200 bg-stone-950 p-5 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-[0.24em] text-stone-400">
              Raw snapshot
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
