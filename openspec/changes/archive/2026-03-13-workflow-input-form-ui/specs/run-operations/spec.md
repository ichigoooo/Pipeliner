## MODIFIED Requirements

### Requirement: Operators can start a run for a workflow version
The system SHALL provide both API-level and studio-facing mechanisms to start a workflow run for a selected workflow version with the required workflow inputs, SHALL render a structured input form when supported workflow input metadata is available, SHALL allow fallback to raw JSON input when metadata is missing or unsupported, and SHALL make the created run immediately observable in the run workspace.

#### Scenario: Start a run with valid structured form inputs
- **WHEN** an operator submits run creation for a registered workflow version through Studio using valid structured workflow input values
- **THEN** the system creates the run and makes its execution state observable

#### Scenario: Fall back to raw JSON input for a legacy workflow
- **WHEN** an operator opens run creation for a workflow version whose workflow inputs cannot be fully rendered as supported structured controls
- **THEN** the system allows the operator to review or enter raw JSON input and use that payload for run creation
