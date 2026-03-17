'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode, useState, useEffect } from 'react';
import { NextIntlClientProvider } from 'next-intl';
import { defaultTimeZone } from '@/i18n/config';
import { I18nProvider } from '@/i18n/provider';
import { ToastProvider } from '@/components/ui/toast';
import { getMessages } from '@/i18n/messages';
import { Locale, defaultLocale, detectBrowserLocale, isValidLocale } from '@/i18n/config';
import { useLanguageStore } from '@/stores/language';

function I18nWrapper({ children }: { children: ReactNode }) {
  const { currentLocale, setLocale } = useLanguageStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // Detect and set initial locale from localStorage or browser
    const stored = localStorage.getItem('pipeliner-language');
    if (stored && isValidLocale(stored)) {
      setLocale(stored);
    } else {
      const browserLocale = detectBrowserLocale();
      setLocale(browserLocale);
    }
    setMounted(true);
  }, [setLocale]);

  const messages = getMessages(currentLocale);

  // Prevent hydration mismatch by not rendering until mounted
  if (!mounted) {
    return (
      <NextIntlClientProvider locale={defaultLocale} messages={getMessages(defaultLocale)} timeZone={defaultTimeZone}>
        {children}
      </NextIntlClientProvider>
    );
  }

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
