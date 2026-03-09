## ADDED Requirements

### Requirement: Artifacts are registered through manifests and stable references
The system SHALL register produced artifacts through an artifact manifest containing at least `artifact_id`, `version`, `kind`, producer context, storage location, integrity digest, and creation time.

#### Scenario: Register a produced artifact
- **WHEN** a node produces an artifact for a run round
- **THEN** the system records a manifest for that artifact and makes it resolvable by `{ artifact_id, version }`

### Requirement: Artifact references resolve through the registry
The system SHALL resolve artifact references used in callbacks and downstream node inputs through the artifact registry rather than requiring payload bodies to be embedded in the callback.

#### Scenario: Resolve downstream artifact reference
- **WHEN** the runtime needs to hand an upstream artifact to a validator or downstream node
- **THEN** the runtime resolves the referenced manifest and uses its storage metadata to locate the payload

### Requirement: Artifact versions are immutable once published
The system SHALL treat a published artifact version as immutable and SHALL require a new version when revised output is submitted.

#### Scenario: Revised output creates a new artifact version
- **WHEN** an executor resubmits an artifact after validator-requested rework
- **THEN** the system registers the new output under a new artifact version instead of overwriting the earlier version

### Requirement: Local artifact storage follows run-scoped layout
The system SHALL store MVP artifacts under a run-scoped local filesystem workspace that separates payloads and metadata for traceability.

#### Scenario: Store artifact under run root
- **WHEN** a run produces artifact payload files on the local filesystem
- **THEN** the system stores them under that run's workspace using a path convention that preserves run identity and artifact version identity
