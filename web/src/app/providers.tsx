'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode, useState, useEffect } from 'react';
import { NextIntlClientProvider } from 'next-intl';
import { defaultTimeZone } from '@/i18n/config';
import { ToastProvider } from '@/components/ui/toast';
import { getMessages } from '@/i18n/messages';
import { detectBrowserLocale, isValidLocale } from '@/i18n/config';
import { useLanguageStore } from '@/stores/language';

function I18nWrapper({ children }: { children: ReactNode }) {
  const { currentLocale, setLocale } = useLanguageStore();

  useEffect(() => {
    // Detect and set initial locale from localStorage or browser
    const stored = localStorage.getItem('pipeliner-language');
    if (stored && isValidLocale(stored)) {
      setLocale(stored);
    } else {
      const browserLocale = detectBrowserLocale();
      setLocale(browserLocale);
    }
  }, [setLocale]);

  const messages = getMessages(currentLocale);

  return (
    <NextIntlClientProvider locale={currentLocale} messages={messages} timeZone={defaultTimeZone}>
      {children}
    </NextIntlClientProvider>
  );
}

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 1,
            refetchOnWindowFocus: false,
            staleTime: 5_000,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider><I18nWrapper>{children}</I18nWrapper></ToastProvider>
    </QueryClientProvider>
  );
}
