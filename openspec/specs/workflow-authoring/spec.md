## Purpose

Provide conversation-driven workflow authoring capabilities, allowing users to iteratively create and refine workflow drafts from an Intent Brief, with revision history, synchronized derived views, and gated publishing.

## Requirements

### Requirement: Users can create and iterate workflow authoring sessions
The system SHALL provide an authoring session that starts from an `Intent Brief`, preserves revision history, and allows users to iteratively refine a workflow draft through conversation-driven updates.

#### Scenario: Start a workflow authoring session
- **WHEN** a user submits a new authoring request with an initial intent brief
- **THEN** the system creates an authoring session with a first draft revision that can be further refined

#### Scenario: Produce a new draft revision from authoring updates
- **WHEN** a user continues an existing authoring session with additional instructions
- **THEN** the system records a new draft revision instead of overwriting the previous revision in place

### Requirement: Each authoring revision yields a structured workflow package
The system SHALL materialize each draft revision as a structured workflow package containing the canonical workflow spec and synchronized derived views for human inspection.

#### Scenario: Generate synchronized workflow package projections
- **WHEN** the system stores a new authoring draft revision
- **THEN** that revision includes the canonical `workflow spec`, a human-readable workflow view, a graph projection, and a lint or validation report derived from the same draft

### Requirement: Advanced users can inspect and edit the canonical draft spec
The system SHALL allow an advanced user to inspect and directly edit the canonical workflow draft spec while keeping revision history and derived views consistent.

#### Scenario: Save a raw spec edit as a new revision
- **WHEN** an advanced user edits the raw workflow spec for the current draft
- **THEN** the system stores the edit as a new draft revision and recomputes the derived projections for that revision

### Requirement: Only valid drafts can be published as workflow versions
The system SHALL validate and lint a draft before publication and SHALL reject publication when blocking errors remain.

#### Scenario: Publish a valid draft
- **WHEN** a user publishes a draft revision whose validation and lint checks pass
- **THEN** the system creates a new registered workflow version from that canonical draft

#### Scenario: Reject publication of an invalid draft
- **WHEN** a user attempts to publish a draft revision with blocking validation or lint errors
- **THEN** the system rejects the publish request and reports the blocking issues
