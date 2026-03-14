type StatusTranslator = ((key: string) => string) & {
  has?: (key: string) => boolean;
};

export function normalizeStatusKey(value: string | null | undefined): string {
  const normalized = value?.trim().toLowerCase();

  return normalized || 'unknown';
}

export function fallbackStatusLabel(value: string | null | undefined): string {
  if (!value) {
    return 'Unknown';
  }

  return value.replaceAll('_', ' ');
}

export function formatStatusLabel(
  value: string | null | undefined,
  translate: StatusTranslator
): string {
  const normalized = normalizeStatusKey(value);

  if (translate.has && !translate.has(normalized)) {
    return fallbackStatusLabel(value);
  }

  try {
    return translate(normalized);
  } catch {
    return fallbackStatusLabel(value);
  }
}
