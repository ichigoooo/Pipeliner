## ADDED Requirements

### Requirement: i18n infrastructure setup
The system SHALL provide a complete i18n infrastructure using next-intl for client-side internationalization.

#### Scenario: Configuration file exists
- **WHEN** the application starts
- **THEN** an i18n configuration file SHALL be available at `web/src/i18n/config.ts`
- **AND** it SHALL define supported languages: English (en) and Chinese (zh)
- **AND** it SHALL export a `Locale` type with values `"en" | "zh"`

### Requirement: Translation provider component
The system SHALL provide a React provider component that wraps the application with i18n context.

#### Scenario: Provider wraps the app
- **WHEN** the root layout renders
- **THEN** the application SHALL be wrapped with `I18nProvider`
- **AND** the provider SHALL receive the current locale and messages

### Requirement: Language persistence
The system SHALL persist the user's language preference to localStorage.

#### Scenario: Language change is persisted
- **WHEN** user selects a different language in settings
- **THEN** the selected language code SHALL be stored in localStorage under key `pipeliner-language`
- **AND** the preference SHALL be restored on next app load

#### Scenario: Default language detection
- **WHEN** the app loads without a stored preference
- **THEN** the system SHALL detect the browser language
- **AND** if browser language starts with "zh", use "zh"
- **AND** otherwise, use "en" as default

### Requirement: TypeScript type safety
The system SHALL provide type-safe translations with autocomplete support.

#### Scenario: Translation keys are typed
- **WHEN** a developer uses the translation hook
- **THEN** TypeScript SHALL provide autocomplete for all available translation keys
- **AND** accessing non-existent keys SHALL produce a type error
