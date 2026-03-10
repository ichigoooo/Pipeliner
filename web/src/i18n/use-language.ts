'use client';

import { useCallback } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { Locale, isValidLocale } from './config';
import { useLanguageStore } from '@/stores/language';

const STORAGE_KEY = 'pipeliner-language';

export function useLanguage() {
  const locale = useLocale();
  const { currentLocale, setLocale } = useLanguageStore();

  const changeLanguage = useCallback(
    (newLocale: Locale) => {
      if (!isValidLocale(newLocale)) {
        console.warn(`Invalid locale: ${newLocale}`);
        return;
      }

      // Persist to localStorage
      if (typeof window !== 'undefined') {
        localStorage.setItem(STORAGE_KEY, newLocale);
      }

      // Update store
      setLocale(newLocale);

      // Reload page to apply new locale
      // This is necessary because next-intl with static export requires a reload
      window.location.reload();
    },
    [setLocale]
  );

  const getStoredLocale = useCallback((): Locale | null => {
    if (typeof window === 'undefined') {
      return null;
    }

    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && isValidLocale(stored)) {
      return stored;
    }
    return null;
  }, []);

  return {
    locale: currentLocale || (locale as Locale),
    changeLanguage,
    getStoredLocale,
  };
}

export { useTranslations };
