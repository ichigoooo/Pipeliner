import React from 'react';
import { render, screen } from '@testing-library/react';
import { NextIntlClientProvider } from 'next-intl';
import { StatusBadge } from '@/components/ui/StatusBadge';
import enMessages from '@/i18n/messages/en.json';

const renderWithI18n = (ui: React.ReactElement) =>
  render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      {ui}
    </NextIntlClientProvider>
  );

describe('StatusBadge', () => {
  it('renders translated passed status', () => {
    renderWithI18n(<StatusBadge value="passed" />);

    expect(screen.getByText('Passed')).toBeInTheDocument();
  });

  it('falls back to a human-readable label for unknown statuses', () => {
    renderWithI18n(<StatusBadge value="custom_status" />);

    expect(screen.getByText('custom status')).toBeInTheDocument();
  });
});
