## ADDED Requirements

### Requirement: Operators can start a run for a workflow version
The system SHALL provide an operator-facing mechanism to start a workflow run for a selected workflow version with the required workflow inputs.

#### Scenario: Start a run with valid inputs
- **WHEN** an operator submits a run request for a registered workflow version with the required inputs
- **THEN** the system creates the run and makes its execution state observable

### Requirement: Operators can inspect run and node execution status
The system SHALL provide a way to inspect current and historical run state, node state, round number, and terminal or waiting conditions.

#### Scenario: View a blocked node
- **WHEN** an operator inspects a run containing a blocked node
- **THEN** the system shows the node as blocked together with its current round and stop condition

### Requirement: Operators can inspect artifact and callback history for troubleshooting
The system SHALL provide access to artifact metadata and callback event history associated with a run for debugging and audit purposes.

#### Scenario: View callback history for a node round
- **WHEN** an operator requests details for a node round
- **THEN** the system shows the recorded callback events and referenced artifacts for that round

### Requirement: Operators can identify runs requiring manual intervention
The system SHALL expose runs and nodes that require manual intervention because of blocked, failed, timeout, or guard-limit outcomes.

#### Scenario: List runs requiring manual handling
- **WHEN** one or more runs stop because of blocked, failed, timed out, or rework-limit conditions
- **THEN** the system can surface those runs as requiring manual intervention
