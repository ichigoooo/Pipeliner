## 1. i18n Infrastructure Setup

- [x] 1.1 Install next-intl dependency: `cd web && npm install next-intl@^3`
- [x] 1.2 Create `web/src/i18n/config.ts` with locale type and supported languages
- [x] 1.3 Create `web/src/i18n/provider.tsx` with I18nProvider wrapper component
- [x] 1.4 Create `web/src/i18n/use-language.ts` hook for language switching with localStorage persistence
- [x] 1.5 Create language Zustand store at `web/src/stores/language.ts`

## 2. Translation Files

- [x] 2.1 Create `web/src/i18n/messages/en.json` with English translations
- [x] 2.2 Create `web/src/i18n/messages/zh.json` with Chinese translations
- [x] 2.3 Create `web/src/i18n/messages/index.ts` to export messages by locale

## 3. Provider Integration

- [x] 3.1 Update `web/src/app/providers.tsx` to include I18nProvider
- [x] 3.2 Update `web/src/app/layout.tsx` to initialize language from localStorage or browser
- [x] 3.3 Verify i18n context is available in all client components

## 4. Settings Page Language Selector

- [x] 4.1 Create `web/src/app/(studio)/settings/components/LanguageSelector.tsx`
- [x] 4.2 Add language selector to settings page at `web/src/app/(studio)/settings/page.tsx`
- [x] 4.3 Style selector to match existing settings UI

## 5. Component Translations

- [x] 5.1 Translate `web/src/components/Sidebar.tsx` navigation labels
- [x] 5.2 Translate Settings page title and descriptions
- [x] 5.3 Translate Authoring page labels
- [x] 5.4 Translate Workflows page labels
- [x] 5.5 Translate Runs page labels
- [x] 5.6 Translate Attention page labels
- [x] 5.7 Extract common action buttons (save, cancel, start, retry, stop) to translation keys

## 6. Testing & Verification

- [x] 6.1 Verify language switching works in Settings page
- [x] 6.2 Verify language preference persists after reload
- [x] 6.3 Verify default language detection works (test with different browser languages)
- [x] 6.4 Run frontend tests: `cd web && npm run test`
- [x] 6.5 Manual test: verify all UI text displays correctly in both languages

## 7. Documentation

- [x] 7.1 Add i18n documentation to `web/README.md` (how to add new translations)
- [x] 7.2 Update CLAUDE.md with i18n conventions if needed
