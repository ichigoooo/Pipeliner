import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Locale, defaultLocale } from '@/i18n/config';

interface LanguageState {
  currentLocale: Locale;
  setLocale: (locale: Locale) => void;
}

export const useLanguageStore = create<LanguageState>()(
  persist(
    (set) => ({
      currentLocale: defaultLocale,
      setLocale: (locale) => set({ currentLocale: locale }),
    }),
    {
      name: 'pipeliner-language',
    }
  )
);
