## MODIFIED Requirements

### Requirement: Workflow Studio exposes resolved settings and configuration provenance
The system SHALL provide a settings workspace that shows resolved runtime configuration values together with their provenance, and SHALL additionally expose Claude connection diagnostics including resolved base URL, effective API host, proxy presence, and the source from which those diagnostics were derived.

#### Scenario: Inspect a resolved command template
- **WHEN** a user opens the settings workspace and inspects an executor or validator command template
- **THEN** the studio shows the currently effective value together with the source that supplied it

#### Scenario: Inspect Claude connection diagnostics
- **WHEN** a user opens the settings workspace while Claude-backed providers are enabled
- **THEN** the studio shows the resolved Claude base URL, API host, proxy summary, and the source used to derive each value

#### Scenario: Detect missing proxy configuration
- **WHEN** the effective Claude diagnostics indicate that no proxy-related variables are present in the merged environment
- **THEN** the settings workspace highlights that condition as an operational warning rather than showing only raw configuration values
