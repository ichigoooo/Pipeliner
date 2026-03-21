'use client';

import { useLanguage } from '@/i18n/use-language';
import { useTranslations } from 'next-intl';
import { locales, localeNames, type Locale } from '@/i18n/config';
import { HelpTooltip } from '@/components/ui/HelpTooltip';

export function LanguageSelector() {
  const t = useTranslations('settings.language');
  const { locale, changeLanguage } = useLanguage();

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLocale = e.target.value as Locale;
    changeLanguage(newLocale);
  };

  return (
    <div className="grid gap-2 rounded-3xl border border-stone-200 bg-stone-50 px-4 py-4 text-sm text-stone-700 md:grid-cols-[180px_minmax(0,1fr)]">
      <div className="flex items-center gap-2 font-medium text-stone-900">
        <span>{t('title')}</span>
        <HelpTooltip content={t('description')} label={t('title')} />
      </div>
      <div className="flex items-center gap-4">
        <select
          value={locale}
          onChange={handleChange}
          className="rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm text-stone-900 focus:border-amber-400 focus:outline-none focus:ring-1 focus:ring-amber-400"
        >
          {locales.map((loc) => (
            <option key={loc} value={loc}>
              {localeNames[loc]}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
