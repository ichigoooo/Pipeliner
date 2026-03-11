## ADDED Requirements

### Requirement: Authoring persists node skill packages in project directories
The system SHALL maintain project-level skill packages for each node executor and validator when authoring drafts.

#### Scenario: Create project skill packages during authoring
- **WHEN** a draft revision is created from an authoring session
- **THEN** the system ensures `projects/<workflow_id>/.claude/skills` contains the executor and validator skill packages for that draft

### Requirement: Authoring validates skill names for drafts
The system SHALL validate executor and validator skill names when storing or publishing drafts.

#### Scenario: Draft fails validation on invalid skill names
- **WHEN** a draft is saved with a skill name that violates naming rules
- **THEN** the system records validation errors and blocks publish until corrected
