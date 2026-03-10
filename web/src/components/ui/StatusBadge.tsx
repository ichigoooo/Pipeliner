import { classNames } from '@/lib/format';

const STATUS_STYLES: Record<string, string> = {
  completed: 'bg-emerald-100 text-emerald-900',
  running: 'bg-sky-100 text-sky-900',
  needs_attention: 'bg-amber-100 text-amber-900',
  failed: 'bg-rose-100 text-rose-900',
  blocked: 'bg-amber-100 text-amber-900',
  waiting_executor: 'bg-indigo-100 text-indigo-900',
  waiting_validator: 'bg-violet-100 text-violet-900',
  revise: 'bg-orange-100 text-orange-900',
  stopped: 'bg-stone-200 text-stone-800',
  timed_out: 'bg-rose-100 text-rose-900',
  rework_limit: 'bg-fuchsia-100 text-fuchsia-900',
  published: 'bg-emerald-100 text-emerald-900',
  active: 'bg-sky-100 text-sky-900',
};

export function StatusBadge({ value }: { value: string | null | undefined }) {
  const label = value || 'unknown';
  const normalized = label.toLowerCase();

  return (
    <span
      className={classNames(
        'inline-flex rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.18em]',
        STATUS_STYLES[normalized] || 'bg-stone-100 text-stone-800'
      )}
    >
      {label}
    </span>
  );
}
