## MODIFIED Requirements

### Requirement: Workflow specifications are validated before acceptance
The system SHALL validate workflow specifications against the declared schema version and SHALL reject workflow definitions that violate required structure, protocol constraints, or workflow input form metadata constraints.

#### Scenario: Reject missing required top-level fields
- **WHEN** a workflow definition is submitted without required top-level fields such as `schema_version`, `metadata`, `inputs`, `outputs`, or `nodes`
- **THEN** the system rejects the definition and reports the validation errors

#### Scenario: Reject unknown schema major versions
- **WHEN** a workflow definition declares a schema major version unsupported by the runtime
- **THEN** the system rejects the definition instead of attempting best-effort parsing

#### Scenario: Reject invalid workflow input form metadata
- **WHEN** a workflow definition declares workflow input form metadata that is internally inconsistent, such as an `enum` input without options or a default value outside the declared constraints
- **THEN** the system rejects the definition and reports the input-specific validation errors

## ADDED Requirements

### Requirement: Workflow inputs can declare structured form metadata
The system SHALL allow each workflow-level input to declare optional structured form metadata that specifies how Workflow Studio collects and validates that input for run creation.

#### Scenario: Register a workflow definition with typed input metadata
- **WHEN** a workflow definition is submitted with workflow inputs that include supported form metadata such as input type, default value, enum options, or scalar constraints
- **THEN** the system stores that metadata with the workflow version so Studio can use it for authoring and run-start rendering

### Requirement: Legacy workflow input definitions remain runnable
The system SHALL preserve compatibility with workflow definitions that omit structured form metadata by deriving a default renderable descriptor from the existing input contract.

#### Scenario: Load a legacy workflow definition without typed input metadata
- **WHEN** a registered workflow version defines workflow inputs using only legacy fields such as `name`, `shape`, `required`, and `summary`
- **THEN** the system accepts the definition and derives default input rendering behavior without requiring an immediate schema rewrite
