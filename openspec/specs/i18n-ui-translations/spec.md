## Purpose

Ensure all UI text in Pipeliner Studio is translatable and available in supported languages.

## Requirements

### Requirement: Translation message files
The system SHALL provide translation files for all supported languages.

#### Scenario: English translations exist
- **WHEN** the locale is set to "en"
- **THEN** the system SHALL load translations from `web/src/i18n/messages/en.json`
- **AND** all UI text SHALL be displayed in English

#### Scenario: Chinese translations exist
- **WHEN** the locale is set to "zh"
- **THEN** the system SHALL load translations from `web/src/i18n/messages/zh.json`
- **AND** all UI text SHALL be displayed in Chinese

### Requirement: All UI text is translatable
The system SHALL extract all user-facing text into translation keys.

#### Scenario: Navigation sidebar is translated
- **WHEN** user views the sidebar
- **THEN** all navigation labels SHALL display in the current language
- **AND** keys SHALL include: `sidebar.nav.authoring`, `sidebar.nav.workflows`, `sidebar.nav.runs`, `sidebar.nav.attention`, `sidebar.nav.settings`

#### Scenario: Settings page is translated
- **WHEN** user views the settings page
- **THEN** all settings labels and descriptions SHALL display in the current language
- **AND** keys SHALL include: `settings.title`, `settings.language.title`, `settings.language.description`, `settings.language.option.en`, `settings.language.option.zh`

#### Scenario: Workflow pages are translated
- **WHEN** user views workflow-related pages
- **THEN** all labels, buttons, and descriptions SHALL display in the current language
- **AND** common action keys SHALL include: `common.save`, `common.cancel`, `common.start`, `common.retry`, `common.stop`, `common.loading`

### Requirement: Translation completeness
The system SHALL ensure all translation keys exist in both language files.

#### Scenario: Missing translations fallback
- **WHEN** a translation key is missing in the current language
- **THEN** the system SHALL fallback to English
- **AND** log a warning in development mode
