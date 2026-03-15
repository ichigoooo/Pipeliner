'use client';

import { useTranslations } from 'next-intl';
import { prettyJson } from '@/lib/format';
import {
  WorkflowInputDescriptor,
  WorkflowInputType,
  inputTypeShape,
  normalizeWorkflowInputSpecs,
  validateWorkflowInputConfig,
} from '@/lib/workflow-inputs';

interface WorkflowInputEditorProps {
  rawSpec: string;
  onChange: (nextRawSpec: string) => void;
  compact?: boolean;
}


function parseSpec(rawSpec: string): Record<string, unknown> | null {
  try {
    const parsed = JSON.parse(rawSpec) as Record<string, unknown>;
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function buildInputSpec(input: WorkflowInputDescriptor): Record<string, unknown> {
  const form: Record<string, unknown> = { type: input.type };
  if (input.default !== undefined && input.default !== '') {
    if (input.type === 'json' && typeof input.default === 'string') {
      try {
        form.default = JSON.parse(input.default);
      } catch {
        form.default = input.default;
      }
    } else {
      form.default = input.default;
    }
  }
  if (input.type === 'enum' && input.options.length > 0) {
    form.options = input.options;
  }
  if (input.type === 'number') {
    if (input.minimum !== undefined) {
      form.minimum = input.minimum;
    }
    if (input.maximum !== undefined) {
      form.maximum = input.maximum;
    }
  }
  if (input.type === 'string' || input.type === 'file') {
    if (input.min_length !== undefined) {
      form.min_length = input.min_length;
    }
    if (input.max_length !== undefined) {
      form.max_length = input.max_length;
    }
    if (input.pattern) {
      form.pattern = input.pattern;
    }
  }

  const shouldPersistForm =
    input.source === 'explicit' ||
    input.type !== 'string' ||
    Object.keys(form).length > 1;

  return {
    name: input.name,
    shape: inputTypeShape(input.type),
    required: input.required,
    summary: input.summary,
    ...(shouldPersistForm ? { form } : {}),
  };
}

function emptyInput(): WorkflowInputDescriptor {
  return {
    name: '',
    shape: 'string',
    required: false,
    summary: '',
    type: 'string',
    default: '',
    options: [],
    source: 'explicit',
  };
}

export function WorkflowInputEditor({ rawSpec, onChange, compact = false }: WorkflowInputEditorProps) {
  const t = useTranslations('authoring');
  const parsedSpec = parseSpec(rawSpec);
  const inputs = normalizeWorkflowInputSpecs(parsedSpec?.inputs);
  const containerPadding = compact ? 'p-4' : 'p-5';
  const sectionSpacing = compact ? 'mt-3 space-y-3' : 'mt-4 space-y-4';
  const gridGap = compact ? 'gap-3' : 'gap-4';
  const inputHeight = compact ? 'h-10' : 'h-11';
  const headerSpacing = compact ? 'mt-1.5' : 'mt-2';
  const buttonPadding = compact ? 'px-3 py-1.5' : 'px-4 py-2';

  const commitInputs = (nextInputs: WorkflowInputDescriptor[]) => {
    if (!parsedSpec) {
      return;
    }
    const nextSpec = JSON.parse(JSON.stringify(parsedSpec)) as Record<string, unknown>;
    nextSpec.inputs = nextInputs.map((input) => buildInputSpec(input));
    onChange(prettyJson(nextSpec));
  };

  const updateInput = (
    index: number,
    updater: (current: WorkflowInputDescriptor) => WorkflowInputDescriptor
  ) => {
    const nextInputs = inputs.map((input, currentIndex) =>
      currentIndex === index ? updater(input) : input
    );
    commitInputs(nextInputs);
  };

  if (!parsedSpec) {
    return (
      <div className="rounded-[2rem] border border-rose-200 bg-rose-50 p-5 text-sm text-rose-900">
        {t('inputs.invalidRawSpec')}
      </div>
    );
  }

  return (
    <div className={`rounded-[2rem] border border-stone-200 bg-white ${containerPadding} shadow-sm`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-stone-500">
            {t('inputs.title')}
          </p>
          <p className={`${headerSpacing} text-xs text-stone-500`}>{t('inputs.description')}</p>
        </div>
        <button
          type="button"
          onClick={() => commitInputs([...inputs, emptyInput()])}
          className={`rounded-full border border-stone-300 ${buttonPadding} text-xs font-semibold uppercase tracking-[0.18em] text-stone-700 transition hover:border-stone-900`}
        >
          {t('inputs.add')}
        </button>
      </div>

      <div className={sectionSpacing}>
        {inputs.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-stone-300 bg-stone-50 px-4 py-5 text-sm text-stone-500">
            {t('inputs.empty')}
          </div>
        ) : null}

        {inputs.map((input, index) => {
          const issues = validateWorkflowInputConfig(input);
          return (
            <div key={`${input.name || 'workflow-input'}-${index}`} className="rounded-3xl border border-stone-200 bg-stone-50 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold text-stone-900">
                  {input.name || t('inputs.untitled', { index: index + 1 })}
                </p>
                <button
                  type="button"
                  onClick={() => commitInputs(inputs.filter((_, currentIndex) => currentIndex !== index))}
                  className="text-xs font-semibold uppercase tracking-[0.18em] text-rose-700 transition hover:text-rose-900"
                >
                  {t('inputs.remove')}
                </button>
              </div>

              <div className={`mt-4 grid ${gridGap} md:grid-cols-2`}>
                <label className="space-y-2 text-sm text-stone-700">
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">
                    {t('inputs.fields.name')}
                  </span>
                  <input
                    className={`${inputHeight} w-full rounded-2xl border border-stone-200 bg-white px-4 text-sm text-stone-900 outline-none`}
                    value={input.name}
                    onChange={(event) =>
                      updateInput(index, (current) => ({ ...current, name: event.target.value }))
                    }
                  />
                </label>

                <label className="space-y-2 text-sm text-stone-700">
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">
                    {t('inputs.fields.type')}
                  </span>
                  <select
                    className={`${inputHeight} w-full rounded-2xl border border-stone-200 bg-white px-4 text-sm text-stone-900 outline-none`}
                    value={input.type}
                    onChange={(event) => {
                      const nextType = event.target.value as WorkflowInputType;
                      updateInput(index, (current) => ({
                        ...current,
                        type: nextType,
                        shape: inputTypeShape(nextType),
                        default: nextType === 'boolean' ? false : '',
                        options: nextType === 'enum' ? current.options : [],
                        minimum: nextType === 'number' ? current.minimum : undefined,
                        maximum: nextType === 'number' ? current.maximum : undefined,
                        min_length:
                          nextType === 'string' || nextType === 'file'
                            ? current.min_length
                            : undefined,
                        max_length:
                          nextType === 'string' || nextType === 'file'
                            ? current.max_length
                            : undefined,
                        pattern:
                          nextType === 'string' || nextType === 'file'
                            ? current.pattern
                            : undefined,
                        source: 'explicit',
                      }));
                    }}
                  >
                    <option value="string">string</option>
                    <option value="number">number</option>
                    <option value="boolean">boolean</option>
                    <option value="enum">enum</option>
                    <option value="file">file</option>
                    <option value="json">json</option>
                  </select>
                </label>

                <label className="space-y-2 text-sm text-stone-700 md:col-span-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">
                    {t('inputs.fields.summary')}
                  </span>
                  <input
                    className={`${inputHeight} w-full rounded-2xl border border-stone-200 bg-white px-4 text-sm text-stone-900 outline-none`}
                    value={input.summary}
                    onChange={(event) =>
                      updateInput(index, (current) => ({ ...current, summary: event.target.value }))
                    }
                  />
                </label>

                <label className="flex items-center gap-3 text-sm font-medium text-stone-700">
                  <input
                    type="checkbox"
                    checked={input.required}
                    onChange={(event) =>
                      updateInput(index, (current) => ({
                        ...current,
                        required: event.target.checked,
                      }))
                    }
                  />
                  {t('inputs.fields.required')}
                </label>

                {input.type === 'boolean' ? (
                  <label className="flex items-center gap-3 text-sm font-medium text-stone-700">
                    <input
                      type="checkbox"
                      checked={Boolean(input.default)}
                      onChange={(event) =>
                        updateInput(index, (current) => ({
                          ...current,
                          default: event.target.checked,
                          source: 'explicit',
                        }))
                      }
                    />
                    {t('inputs.fields.default')}
                  </label>
                ) : (
                  <label className="space-y-2 text-sm text-stone-700">
                    <span className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">
                      {t('inputs.fields.default')}
                    </span>
                    {input.type === 'json' ? (
                      <textarea
                        className="min-h-24 w-full rounded-3xl border border-stone-200 bg-white px-4 py-3 text-sm text-stone-900 outline-none"
                        value={typeof input.default === 'string' ? input.default : JSON.stringify(input.default ?? '', null, 2)}
                        onChange={(event) =>
                          updateInput(index, (current) => ({
                            ...current,
                            default: event.target.value,
                            source: 'explicit',
                          }))
                        }
                      />
                    ) : (
                      <input
                        className={`${inputHeight} w-full rounded-2xl border border-stone-200 bg-white px-4 text-sm text-stone-900 outline-none`}
                        type={input.type === 'number' ? 'number' : 'text'}
                        value={String(input.default ?? '')}
                        onChange={(event) =>
                          updateInput(index, (current) => ({
                            ...current,
                            default:
                              input.type === 'number' && event.target.value !== ''
                                ? Number(event.target.value)
                                : event.target.value,
                            source: 'explicit',
                          }))
                        }
                      />
                    )}
                  </label>
                )}

                {input.type === 'enum' ? (
                  <label className="space-y-2 text-sm text-stone-700 md:col-span-2">
                    <span className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">
                      {t('inputs.fields.options')}
                    </span>
                    <input
                      className={`${inputHeight} w-full rounded-2xl border border-stone-200 bg-white px-4 text-sm text-stone-900 outline-none`}
                      value={input.options.join(', ')}
                      onChange={(event) =>
                        updateInput(index, (current) => ({
                          ...current,
                          options: event.target.value
                            .split(',')
                            .map((item) => item.trim())
                            .filter(Boolean),
                          source: 'explicit',
                        }))
                      }
                    />
                  </label>
                ) : null}

                {input.type === 'number' ? (
                  <>
                    <label className="space-y-2 text-sm text-stone-700">
                      <span className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">
                        {t('inputs.fields.minimum')}
                      </span>
                      <input
                        className={`${inputHeight} w-full rounded-2xl border border-stone-200 bg-white px-4 text-sm text-stone-900 outline-none`}
                        type="number"
                        value={input.minimum ?? ''}
                        onChange={(event) =>
                          updateInput(index, (current) => ({
                            ...current,
                            minimum: event.target.value === '' ? undefined : Number(event.target.value),
                            source: 'explicit',
                          }))
                        }
                      />
                    </label>
                    <label className="space-y-2 text-sm text-stone-700">
                      <span className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">
                        {t('inputs.fields.maximum')}
                      </span>
                      <input
                        className={`${inputHeight} w-full rounded-2xl border border-stone-200 bg-white px-4 text-sm text-stone-900 outline-none`}
                        type="number"
                        value={input.maximum ?? ''}
                        onChange={(event) =>
                          updateInput(index, (current) => ({
                            ...current,
                            maximum: event.target.value === '' ? undefined : Number(event.target.value),
                            source: 'explicit',
                          }))
                        }
                      />
                    </label>
                  </>
                ) : null}

                {input.type === 'string' || input.type === 'file' ? (
                  <>
                    <label className="space-y-2 text-sm text-stone-700">
                      <span className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">
                        {t('inputs.fields.minLength')}
                      </span>
                      <input
                        className={`${inputHeight} w-full rounded-2xl border border-stone-200 bg-white px-4 text-sm text-stone-900 outline-none`}
                        type="number"
                        value={input.min_length ?? ''}
                        onChange={(event) =>
                          updateInput(index, (current) => ({
                            ...current,
                            min_length: event.target.value === '' ? undefined : Number(event.target.value),
                            source: 'explicit',
                          }))
                        }
                      />
                    </label>
                    <label className="space-y-2 text-sm text-stone-700">
                      <span className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">
                        {t('inputs.fields.maxLength')}
                      </span>
                      <input
                        className={`${inputHeight} w-full rounded-2xl border border-stone-200 bg-white px-4 text-sm text-stone-900 outline-none`}
                        type="number"
                        value={input.max_length ?? ''}
                        onChange={(event) =>
                          updateInput(index, (current) => ({
                            ...current,
                            max_length: event.target.value === '' ? undefined : Number(event.target.value),
                            source: 'explicit',
                          }))
                        }
                      />
                    </label>
                    <label className="space-y-2 text-sm text-stone-700 md:col-span-2">
                      <span className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">
                        {t('inputs.fields.pattern')}
                      </span>
                      <input
                        className={`${inputHeight} w-full rounded-2xl border border-stone-200 bg-white px-4 text-sm text-stone-900 outline-none`}
                        value={input.pattern ?? ''}
                        onChange={(event) =>
                          updateInput(index, (current) => ({
                            ...current,
                            pattern: event.target.value || undefined,
                            source: 'explicit',
                          }))
                        }
                      />
                    </label>
                  </>
                ) : null}
              </div>

              {issues.length > 0 ? (
                <div className="mt-4 space-y-2">
                  {issues.map((issue) => (
                    <div
                      key={issue}
                      className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
                    >
                      {issue}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
