## ADDED Requirements

### Requirement: Workflow definitions are versioned and loadable
The system SHALL allow an operator or local toolchain to register a workflow definition identified by a stable `workflow_id` and a workflow `version`, and SHALL make that exact version loadable for future run creation.

#### Scenario: Load a registered workflow version
- **WHEN** a valid workflow definition with `workflow_id` and `version` is registered
- **THEN** the system stores it as an addressable workflow version that can be selected when creating a run

### Requirement: Workflow specifications are validated before acceptance
The system SHALL validate workflow specifications against the declared schema version and SHALL reject workflow definitions that violate required structure or protocol constraints.

#### Scenario: Reject missing required top-level fields
- **WHEN** a workflow definition is submitted without required top-level fields such as `schema_version`, `metadata`, `inputs`, `outputs`, or `nodes`
- **THEN** the system rejects the definition and reports the validation errors

#### Scenario: Reject unknown schema major versions
- **WHEN** a workflow definition declares a schema major version unsupported by the runtime
- **THEN** the system rejects the definition instead of attempting best-effort parsing

### Requirement: Workflow dependency graphs pass lint before activation
The system SHALL lint node dependency graphs before a workflow version becomes runnable, including dependency existence, `depends_on` and `inputs.from` consistency, and cycle detection.

#### Scenario: Reject a node output reference not declared in depends_on
- **WHEN** a node input references another node output but that upstream node is absent from the current node's `depends_on`
- **THEN** the system rejects the workflow version with a lint error

#### Scenario: Reject cyclic node dependencies
- **WHEN** the node dependency graph contains a cycle
- **THEN** the system rejects the workflow version with a cycle detection error
