import en from './en.json';
import zh from './zh.json';
import { Locale } from '../config';

export const messages: Record<Locale, typeof en> = {
  en,
  zh,
};

export function getMessages(locale: Locale): typeof en {
  return messages[locale] || messages.en;
}
