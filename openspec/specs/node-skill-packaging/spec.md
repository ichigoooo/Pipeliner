## Purpose

TBD

## Requirements

### Requirement: Node skills are initialized for executor and validators
The system SHALL create a skill package for each node executor and each validator referenced in a workflow draft.

#### Scenario: Initialize node skills on draft save
- **WHEN** a draft revision is created or updated
- **THEN** the system creates missing skill directories for the node executor and validators under `projects/<workflow_id>/.claude/skills/`

### Requirement: Skill templates are created without overwriting user edits
The system SHALL generate an initial `SKILL.md` template when missing and SHALL NOT overwrite an existing `SKILL.md`.

#### Scenario: Preserve existing SKILL.md
- **WHEN** a node skill already exists with `SKILL.md`
- **THEN** the system leaves `SKILL.md` unchanged while still updating references

### Requirement: Node context references are maintained for skills
The system SHALL write a node context reference file that reflects the current node spec for each executor and validator skill.

#### Scenario: Update node context references
- **WHEN** a draft revision is stored with node changes
- **THEN** the system updates the corresponding `references/node_context.json` for each affected skill

### Requirement: Skill names are validated and unique within a workflow
The system SHALL validate that every executor and validator skill name is a valid kebab-case identifier and unique within a workflow.

#### Scenario: Reject invalid skill names
- **WHEN** a draft contains an invalid or duplicated skill name
- **THEN** the system reports a validation error describing the offending skill entry
