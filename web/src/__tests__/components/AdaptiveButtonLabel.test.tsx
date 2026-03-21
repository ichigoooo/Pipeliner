import React from 'react';
import { render, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { AdaptiveButtonLabel } from '@/components/ui/AdaptiveButtonLabel';

let mockClientWidth = 240;

const originalClientWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'clientWidth');
const originalScrollWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollWidth');

describe('AdaptiveButtonLabel', () => {
  beforeEach(() => {
    mockClientWidth = 240;

    Object.defineProperty(HTMLElement.prototype, 'clientWidth', {
      configurable: true,
      get() {
        return this.classList.contains('adaptive-button-label-root') ? mockClientWidth : 0;
      },
    });

    Object.defineProperty(HTMLElement.prototype, 'scrollWidth', {
      configurable: true,
      get() {
        const text = this.textContent ?? '';
        const fontSize = Number.parseFloat((this as HTMLElement).style.fontSize || '14');
        return Math.ceil(text.length * fontSize * 0.72);
      },
    });
  });

  afterEach(() => {
    if (originalClientWidth) {
      Object.defineProperty(HTMLElement.prototype, 'clientWidth', originalClientWidth);
    }
    if (originalScrollWidth) {
      Object.defineProperty(HTMLElement.prototype, 'scrollWidth', originalScrollWidth);
    }
  });

  it('keeps the default font size when the label fits', async () => {
    const { container } = render(<AdaptiveButtonLabel text="Launch Run" />);
    const root = container.querySelector('.adaptive-button-label-root');
    const label = container.querySelector('.adaptive-button-label-text');

    await waitFor(() => {
      expect(label).toHaveStyle({ fontSize: '14px' });
    });

    expect(root).not.toHaveAttribute('title');
  });

  it('falls back to the minimum font size and exposes the full label when truncated', async () => {
    mockClientWidth = 60;
    const text = 'Publish latest version to production';
    const { container } = render(<AdaptiveButtonLabel text={text} />);
    const root = container.querySelector('.adaptive-button-label-root');
    const label = container.querySelector('.adaptive-button-label-text');

    await waitFor(() => {
      expect(label).toHaveStyle({ fontSize: '11px' });
    });

    expect(root).toHaveAttribute('title', text);
  });
});
