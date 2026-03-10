## Purpose

Provide a language selector in the Settings page for users to switch between supported languages.

## Requirements

### Requirement: Language selector component
The system SHALL provide a language selector component in the Settings page.

#### Scenario: Selector displays current language
- **WHEN** user navigates to the Settings page
- **THEN** a language selector SHALL be visible
- **AND** it SHALL display the currently selected language

#### Scenario: Selector shows available options
- **WHEN** user clicks the language selector
- **THEN** a dropdown or option list SHALL appear
- **AND** it SHALL show: "English" and "中文 (Chinese)"
- **AND** each option SHALL display the native language name

### Requirement: Language switching
The system SHALL change the application language when user selects a different option.

#### Scenario: Language changes immediately
- **WHEN** user selects a different language from the selector
- **THEN** the UI SHALL immediately update to the selected language
- **AND** all visible text SHALL be re-rendered with new translations
- **AND** the preference SHALL be persisted to localStorage

#### Scenario: Language change persists across sessions
- **GIVEN** user has selected "中文" as the language
- **WHEN** user closes and reopens the browser
- **THEN** the application SHALL load with "中文" as the active language

### Requirement: Language selector integration with settings
The system SHALL integrate the language selector into the existing Settings page structure.

#### Scenario: Selector follows settings page style
- **WHEN** the language selector is rendered
- **THEN** it SHALL match the existing settings UI style
- **AND** it SHALL use the same layout and typography as other settings sections

#### Scenario: Language setting is discoverable
- **WHEN** user views the Settings page
- **THEN** the language option SHALL be prominently placed
- **AND** it SHALL have a clear label and description
