import React from 'react';
import { classNames } from '@/lib/format';

export function StudioPage({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className="min-h-full px-4 py-5 md:px-6 lg:px-8">
      <div className={classNames('mx-auto w-full max-w-[1560px]', className)}>
        {children}
      </div>
    </div>
  );
}

export function StudioPageHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
}: {
  eyebrow: string;
  title: string;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <header
      className={classNames(
        'mb-6 flex flex-wrap items-end justify-between gap-4 border-b border-stone-200 pb-4',
        className
      )}
    >
      <div className="min-w-0">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-stone-500">
          {eyebrow}
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.02em] text-stone-900">
          {title}
        </h1>
        {description ? (
          <div className="mt-2 text-sm leading-6 text-stone-600">{description}</div>
        ) : null}
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </header>
  );
}
