'use client';

import { useEffect, useId, useRef, useState } from 'react';
import { CircleHelp } from 'lucide-react';
import { classNames } from '@/lib/format';

interface HelpTooltipProps {
  content: string;
  label: string;
  className?: string;
  panelClassName?: string;
}

export function HelpTooltip({
  content,
  label,
  className,
  panelClassName,
}: HelpTooltipProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const tooltipId = useId();

  useEffect(() => {
    if (!open) {
      return undefined;
    }

    const handlePointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, [open]);

  return (
    <div
      ref={rootRef}
      className={classNames('relative inline-flex items-center', className)}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
          setOpen(false);
        }
      }}
    >
      <button
        type="button"
        aria-label={label}
        aria-expanded={open}
        aria-describedby={open ? tooltipId : undefined}
        onPointerDown={(event) => event.stopPropagation()}
        onFocus={() => setOpen(true)}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          setOpen((current) => !current);
        }}
        className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-stone-200 bg-white/88 text-stone-500 transition duration-200 hover:-translate-y-0.5 hover:border-amber-300 hover:text-stone-900"
      >
        <CircleHelp className="h-3.5 w-3.5" strokeWidth={1.8} />
      </button>

      {open ? (
        <div
          id={tooltipId}
          role="tooltip"
          className={classNames(
            'absolute right-0 top-[calc(100%+0.65rem)] z-30 w-64 rounded-[1.1rem] border border-stone-200/90 bg-white/96 px-4 py-3 text-sm leading-6 text-stone-700 shadow-[0_22px_45px_-28px_rgba(68,64,60,0.45)] backdrop-blur',
            panelClassName
          )}
        >
          {content}
        </div>
      ) : null}
    </div>
  );
}
