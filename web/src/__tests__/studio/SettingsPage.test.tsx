import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';
import { NextIntlClientProvider } from 'next-intl';
import SettingsPage from '@/app/(studio)/settings/page';
import { api } from '@/lib/api';
import enMessages from '@/i18n/messages/en.json';

vi.mock('@/lib/api', () => ({
  api: {
    getSettings: vi.fn(),
  },
}));

const mockedApi = vi.mocked(api);

const renderWithClient = (ui: React.ReactElement) => {
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <QueryClientProvider client={client}>{ui}</QueryClientProvider>
    </NextIntlClientProvider>
  );
};

describe('SettingsPage', () => {
  it('shows resolved settings and provenance', async () => {
    mockedApi.getSettings.mockResolvedValue({
      settings: {
        executor_command: {
          value: 'claude -p',
          source: 'env',
          env_key: 'PIPELINER_CLAUDE_EXECUTOR_CMD',
          default: 'claude -p --permission-mode bypassPermissions',
        },
        validator_command: {
          value: 'claude -p',
          source: 'default',
          env_key: 'PIPELINER_CLAUDE_VALIDATOR_CMD',
          default: 'claude -p --permission-mode bypassPermissions',
        },
        storage: {
          backend: {
            value: 'local_fs',
            source: 'code_default',
            env_key: 'PIPELINER_STORAGE_BACKEND',
            default: 'local_fs',
          },
          data_dir: {
            value: '.pipeliner',
            source: 'env',
            env_key: 'PIPELINER_DATA_DIR',
            default: '.pipeliner',
          },
          run_root: {
            value: '.pipeliner/runs',
            source: 'derived_from_data_dir',
            env_key: 'PIPELINER_DATA_DIR',
            default: '.pipeliner/runs',
          },
        },
        database: {
          url: {
            value: 'sqlite:///pipeliner.db',
            source: 'default',
            env_key: 'PIPELINER_DATABASE_URL',
            default: 'sqlite:///pipeliner.db',
          },
          path: {
            value: '.pipeliner/pipeliner.db',
            source: 'derived_from_data_dir',
            env_key: 'PIPELINER_DATA_DIR',
            default: '.pipeliner/pipeliner.db',
          },
        },
        observability: {
          claude_trace_enabled: {
            value: false,
            source: 'default',
            env_key: 'PIPELINER_CLAUDE_TRACE_ENABLED',
            default: false,
          },
        },
        runtime_guards: {
          default_timeout: {
            value: '30m',
            source: 'default',
            env_key: 'PIPELINER_DEFAULT_TIMEOUT',
            default: '30m',
          },
          default_max_rework_rounds: {
            value: 3,
            source: 'default',
            env_key: 'PIPELINER_DEFAULT_MAX_REWORK_ROUNDS',
            default: 3,
          },
          blocked_requires_manual: {
            value: true,
            source: 'default',
            env_key: 'PIPELINER_BLOCKED_REQUIRES_MANUAL',
            default: true,
          },
          failure_requires_manual: {
            value: true,
            source: 'default',
            env_key: 'PIPELINER_FAILURE_REQUIRES_MANUAL',
            default: true,
          },
        },
        providers: [
          {
            provider: 'claude',
            role: 'executor',
            command_template: {
              value: 'claude -p',
              source: 'env',
              env_key: 'PIPELINER_CLAUDE_EXECUTOR_CMD',
              default: 'claude -p --permission-mode bypassPermissions',
            },
          },
        ],
        skills: [
          {
            skill: 'draft-skill',
            used_by: ['wf_test@v1:draft_article'],
          },
        ],
        claude_diagnostics: {
          base_url: { value: 'https://api.example.com/v1', source: 'env' },
          api_host: { value: 'api.example.com', source: 'derived' },
          proxy: {
            process_keys: ['HTTP_PROXY'],
            shell_keys: ['HTTP_PROXY', 'HTTPS_PROXY'],
            effective_keys: ['HTTP_PROXY', 'HTTPS_PROXY'],
            missing: false,
          },
          sources: {
            settings_path: '/Users/test/.claude/settings.json',
            settings_loaded: true,
          },
        },
      },
    });

    renderWithClient(<SettingsPage />);

    expect(await screen.findByText('Resolved configuration + provenance')).toBeInTheDocument();
    expect(screen.getByText('Executor')).toBeInTheDocument();
    expect(screen.getAllByText('claude -p').length).toBeGreaterThan(0);
    expect(screen.getAllByText('env').length).toBeGreaterThan(0);
    expect(screen.getByText('draft-skill')).toBeInTheDocument();
    expect(screen.getByText('wf_test@v1:draft_article')).toBeInTheDocument();
    expect(screen.getByText('Claude Base URL')).toBeInTheDocument();
    expect(screen.getByText('https://api.example.com/v1')).toBeInTheDocument();
    expect(screen.getByText('Proxy detected')).toBeInTheDocument();
  });
});
