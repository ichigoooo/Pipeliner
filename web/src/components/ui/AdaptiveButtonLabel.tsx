'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { classNames } from '@/lib/format';

interface AdaptiveButtonLabelProps {
  text: string;
  className?: string;
  maxFontSize?: number;
  minFontSize?: number;
}

type LabelLayoutState = {
  fontSize: number;
  truncated: boolean;
};

export function AdaptiveButtonLabel({
  text,
  className,
  maxFontSize = 14,
  minFontSize = 11,
}: AdaptiveButtonLabelProps) {
  const rootRef = useRef<HTMLSpanElement | null>(null);
  const measureRef = useRef<HTMLSpanElement | null>(null);
  const [{ fontSize, truncated }, setLayout] = useState<LabelLayoutState>({
    fontSize: maxFontSize,
    truncated: false,
  });

  const sizeSteps = useMemo(() => {
    const steps: number[] = [];
    for (let size = maxFontSize; size >= minFontSize; size -= 1) {
      steps.push(size);
    }
    return steps;
  }, [maxFontSize, minFontSize]);

  useEffect(() => {
    const root = rootRef.current;
    const measure = measureRef.current;
    if (!root || !measure) {
      return undefined;
    }

    const recalc = () => {
      const availableWidth = root.clientWidth;
      if (availableWidth <= 0) {
        setLayout({ fontSize: maxFontSize, truncated: false });
        return;
      }

      let nextFontSize = minFontSize;
      let fits = false;

      for (const size of sizeSteps) {
        measure.style.fontSize = `${size}px`;
        if (measure.scrollWidth <= availableWidth) {
          nextFontSize = size;
          fits = true;
          break;
        }
      }

      measure.style.fontSize = `${nextFontSize}px`;
      setLayout({
        fontSize: nextFontSize,
        truncated: !fits && measure.scrollWidth > availableWidth,
      });
    };

    recalc();

    if (typeof window === 'undefined' || typeof window.ResizeObserver === 'undefined') {
      return undefined;
    }

    const observer = new window.ResizeObserver(() => recalc());
    observer.observe(root);
    return () => observer.disconnect();
  }, [maxFontSize, minFontSize, sizeSteps, text]);

  return (
    <span
      ref={rootRef}
      title={truncated ? text : undefined}
      className="adaptive-button-label-root relative block min-w-0 flex-1"
    >
      <span
        ref={measureRef}
        aria-hidden="true"
        className="adaptive-button-label-measure pointer-events-none absolute left-0 top-0 invisible whitespace-nowrap"
      >
        {text}
      </span>
      <span
        aria-label={text}
        className={classNames(
          'adaptive-button-label-text block min-w-0 overflow-hidden text-ellipsis whitespace-nowrap text-center leading-[1.15]',
          className
        )}
        style={{ fontSize: `${fontSize}px` }}
      >
        {text}
      </span>
    </span>
  );
}
