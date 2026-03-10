export function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return '-';
  }

  return new Date(value).toLocaleString();
}

export function prettyJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

export function classNames(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(' ');
}
