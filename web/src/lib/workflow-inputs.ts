export type WorkflowInputType = 'string' | 'number' | 'boolean' | 'enum' | 'file' | 'json';

export interface WorkflowInputFormConfig {
  type: WorkflowInputType;
  default?: unknown;
  options?: string[];
  minimum?: number;
  maximum?: number;
  min_length?: number;
  max_length?: number;
  pattern?: string;
}

export interface WorkflowInputSpecRecord {
  name: string;
  shape: string;
  required: boolean;
  summary: string;
  form?: WorkflowInputFormConfig;
}

export interface WorkflowInputDescriptor extends WorkflowInputFormConfig {
  name: string;
  shape: string;
  required: boolean;
  summary: string;
  options: string[];
  source: 'explicit' | 'derived';
}

export interface WorkflowInputValidationResult {
  value?: unknown;
  error?: string;
}

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === 'string');
}

function hasNumberConstraint(value: unknown): value is number {
  return typeof value === 'number';
}

function hasConfiguredDefault(value: unknown): boolean {
  return value !== undefined && value !== null;
}

function validateStringLike(
  value: string,
  descriptor: WorkflowInputDescriptor
): WorkflowInputValidationResult {
  if (hasNumberConstraint(descriptor.min_length) && value.length < descriptor.min_length) {
    return { error: `Must be at least ${descriptor.min_length} characters` };
  }
  if (hasNumberConstraint(descriptor.max_length) && value.length > descriptor.max_length) {
    return { error: `Must be at most ${descriptor.max_length} characters` };
  }
  if (typeof descriptor.pattern === 'string' && descriptor.pattern) {
    try {
      const pattern = new RegExp(descriptor.pattern);
      if (!pattern.test(value)) {
        return { error: 'Does not match the required pattern' };
      }
    } catch {
      return { error: 'Pattern is invalid' };
    }
  }
  return { value };
}

export function deriveWorkflowInputType(shape: string): WorkflowInputType {
  const normalized = shape.trim().toLowerCase();
  if (normalized === 'file') {
    return 'file';
  }
  if (normalized === 'json') {
    return 'json';
  }
  if (normalized === 'boolean') {
    return 'boolean';
  }
  if (normalized === 'number' || normalized === 'integer' || normalized === 'float') {
    return 'number';
  }
  return 'string';
}

export function normalizeWorkflowInputSpec(input: unknown): WorkflowInputDescriptor | null {
  if (!isRecord(input)) {
    return null;
  }

  const form = isRecord(input.form) ? input.form : null;
  const derivedType = deriveWorkflowInputType(typeof input.shape === 'string' ? input.shape : 'string');
  const explicitType = typeof form?.type === 'string' ? form.type : null;
  const type = (explicitType || derivedType) as WorkflowInputType;

  return {
    name: typeof input.name === 'string' ? input.name : '',
    shape: typeof input.shape === 'string' ? input.shape : 'string',
    required: Boolean(input.required),
    summary: typeof input.summary === 'string' ? input.summary : '',
    type,
    default: form?.default,
    options: toStringArray(form?.options),
    minimum: typeof form?.minimum === 'number' ? form.minimum : undefined,
    maximum: typeof form?.maximum === 'number' ? form.maximum : undefined,
    min_length: typeof form?.min_length === 'number' ? form.min_length : undefined,
    max_length: typeof form?.max_length === 'number' ? form.max_length : undefined,
    pattern: typeof form?.pattern === 'string' ? form.pattern : undefined,
    source: explicitType ? 'explicit' : 'derived',
  };
}

export function normalizeWorkflowInputSpecs(inputs: unknown): WorkflowInputDescriptor[] {
  if (!Array.isArray(inputs)) {
    return [];
  }
  return inputs
    .map((input) => normalizeWorkflowInputSpec(input))
    .filter((item): item is WorkflowInputDescriptor => item !== null);
}

export function validateWorkflowInputConfig(input: WorkflowInputDescriptor): string[] {
  const issues: string[] = [];
  if (!input.name.trim()) {
    issues.push('Name is required');
  }
  if (!input.summary.trim()) {
    issues.push('Summary is required');
  }

  if (input.type === 'enum') {
    if (input.options.length === 0) {
      issues.push('Enum inputs require at least one option');
    }
    if (new Set(input.options).size !== input.options.length) {
      issues.push('Enum options must be unique');
    }
  } else if (input.options.length > 0) {
    issues.push('Only enum inputs can define options');
  }

  if (input.type === 'number') {
    if (hasNumberConstraint(input.minimum) && hasNumberConstraint(input.maximum) && input.minimum > input.maximum) {
      issues.push('Minimum cannot be greater than maximum');
    }
  } else if (hasNumberConstraint(input.minimum) || hasNumberConstraint(input.maximum)) {
    issues.push('Only number inputs can define minimum or maximum');
  }

  if (input.type === 'string' || input.type === 'file') {
    if (
      hasNumberConstraint(input.min_length) &&
      hasNumberConstraint(input.max_length) &&
      input.min_length > input.max_length
    ) {
      issues.push('Min length cannot be greater than max length');
    }
    if (typeof input.pattern === 'string' && input.pattern) {
      try {
        new RegExp(input.pattern);
      } catch {
        issues.push('Pattern must be a valid regular expression');
      }
    }
  } else if (
    hasNumberConstraint(input.min_length) ||
    hasNumberConstraint(input.max_length) ||
    (typeof input.pattern === 'string' && input.pattern.length > 0)
  ) {
    issues.push('Only string or file inputs can define length constraints or patterns');
  }

  if (hasConfiguredDefault(input.default)) {
    if (input.type === 'json' && typeof input.default === 'string' && input.default.trim()) {
      try {
        JSON.parse(input.default);
      } catch {
        issues.push('Default value must be valid JSON');
        return issues;
      }
    }
    const result = validateWorkflowInputValue(input, input.default);
    if (result.error) {
      issues.push(`Default value: ${result.error}`);
    }
  }

  return issues;
}

export function validateWorkflowInputValue(
  descriptor: WorkflowInputDescriptor,
  rawValue: unknown
): WorkflowInputValidationResult {
  if (descriptor.type === 'string' || descriptor.type === 'file') {
    if (typeof rawValue !== 'string') {
      return { error: 'Must be a string' };
    }
    return validateStringLike(rawValue, descriptor);
  }

  if (descriptor.type === 'number') {
    if (typeof rawValue !== 'number' || Number.isNaN(rawValue)) {
      return { error: 'Must be a number' };
    }
    if (hasNumberConstraint(descriptor.minimum) && rawValue < descriptor.minimum) {
      return { error: `Must be at least ${descriptor.minimum}` };
    }
    if (hasNumberConstraint(descriptor.maximum) && rawValue > descriptor.maximum) {
      return { error: `Must be at most ${descriptor.maximum}` };
    }
    return { value: rawValue };
  }

  if (descriptor.type === 'boolean') {
    if (typeof rawValue !== 'boolean') {
      return { error: 'Must be true or false' };
    }
    return { value: rawValue };
  }

  if (descriptor.type === 'enum') {
    if (typeof rawValue !== 'string') {
      return { error: 'Must be a string option' };
    }
    if (!descriptor.options.includes(rawValue)) {
      return { error: `Must be one of: ${descriptor.options.join(', ')}` };
    }
    return { value: rawValue };
  }

  return { value: rawValue };
}

export function defaultFormValue(descriptor: WorkflowInputDescriptor): unknown {
  if (hasConfiguredDefault(descriptor.default)) {
    if (descriptor.type === 'json') {
      return JSON.stringify(descriptor.default, null, 2);
    }
    return descriptor.default;
  }
  if (descriptor.type === 'boolean') {
    return false;
  }
  if (descriptor.type === 'json') {
    return '';
  }
  return '';
}

export function buildInitialFormValues(
  descriptors: WorkflowInputDescriptor[]
): Record<string, unknown> {
  const values: Record<string, unknown> = {};
  for (const descriptor of descriptors) {
    values[descriptor.name] = defaultFormValue(descriptor);
  }
  return values;
}

export function serializeWorkflowInputValues(
  descriptors: WorkflowInputDescriptor[],
  rawValues: Record<string, unknown>
): { payload: Record<string, unknown>; errors: Record<string, string> } {
  const payload: Record<string, unknown> = {};
  const errors: Record<string, string> = {};

  for (const descriptor of descriptors) {
    const currentValue = rawValues[descriptor.name];
    if (
      currentValue === undefined ||
      currentValue === null ||
      currentValue === ''
    ) {
      if (hasConfiguredDefault(descriptor.default)) {
        payload[descriptor.name] = descriptor.default;
        continue;
      }
      if (descriptor.required) {
        errors[descriptor.name] = 'This field is required';
      }
      continue;
    }

    if (descriptor.type === 'json') {
      if (typeof currentValue !== 'string') {
        errors[descriptor.name] = 'JSON input must be text';
        continue;
      }
      try {
        payload[descriptor.name] = JSON.parse(currentValue);
      } catch {
        errors[descriptor.name] = 'JSON input is invalid';
      }
      continue;
    }

    if (descriptor.type === 'number') {
      const numeric = typeof currentValue === 'number' ? currentValue : Number(currentValue);
      const result = validateWorkflowInputValue(descriptor, numeric);
      if (result.error) {
        errors[descriptor.name] = result.error;
        continue;
      }
      payload[descriptor.name] = numeric;
      continue;
    }

    const result = validateWorkflowInputValue(descriptor, currentValue);
    if (result.error) {
      errors[descriptor.name] = result.error;
      continue;
    }
    payload[descriptor.name] = result.value;
  }

  return { payload, errors };
}

export function inputTypeShape(type: WorkflowInputType): string {
  if (type === 'number' || type === 'boolean' || type === 'file' || type === 'json') {
    return type;
  }
  return 'string';
}
