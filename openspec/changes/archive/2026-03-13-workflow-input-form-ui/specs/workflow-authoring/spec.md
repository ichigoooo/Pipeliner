## ADDED Requirements

### Requirement: Authors can configure workflow input form metadata in Studio
The system SHALL allow workflow authors to create and edit workflow-level input form metadata in Workflow Studio, including supported input type, required flag, default value, enum options, and scalar constraints.

#### Scenario: Save typed workflow input metadata in a draft revision
- **WHEN** an author edits a workflow draft and configures a workflow input with typed form metadata
- **THEN** the system stores that metadata in the resulting draft revision and includes it in the canonical workflow spec for that revision

### Requirement: Authoring surfaces invalid workflow input metadata before publish
The system SHALL surface validation feedback in the authoring flow when workflow input form metadata is incomplete or inconsistent, so authors can correct the draft before publication.

#### Scenario: Show validation feedback for invalid input configuration
- **WHEN** an author configures an invalid workflow input form definition such as duplicate enum values or conflicting numeric bounds
- **THEN** the system marks the input configuration as invalid and reports the issue in the draft validation feedback
