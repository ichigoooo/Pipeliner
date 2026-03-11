## MODIFIED Requirements

### Requirement: Operators can start a run for a workflow version
The system SHALL provide both API-level and studio-facing mechanisms to start a workflow run for a selected workflow version with the required workflow inputs, and SHALL make the created run immediately observable in the run workspace.

#### Scenario: Start a run with valid inputs
- **WHEN** an operator submits a run request for a registered workflow version with the required inputs
- **THEN** the system creates the run and makes its execution state observable

### Requirement: Operators can inspect run and node execution status
The system SHALL provide a run workspace that exposes current and historical run state, node state, round number, waiting actor, and terminal or waiting conditions, including a timeline or equivalent progression view for the run.

#### Scenario: View a blocked node
- **WHEN** an operator inspects a run containing a blocked node
- **THEN** the system shows the node as blocked together with its current round and stop condition

### Requirement: Operators can inspect artifact and callback history for troubleshooting
The system SHALL provide access to artifact metadata, callback event history, and related round-level debugging context for a run, including raw protocol payloads or references needed for audit and troubleshooting.

#### Scenario: View callback history for a node round
- **WHEN** an operator requests details for a node round
- **THEN** the system shows the recorded callback events and referenced artifacts for that round

### Requirement: Operators can identify runs requiring manual intervention
The system SHALL expose runs and nodes that require manual intervention because of blocked, failed, timeout, or guard-limit outcomes, and SHALL present the stop reason and current actionable context in an attention queue or equivalent view.

#### Scenario: List runs requiring manual handling
- **WHEN** one or more runs stop because of blocked, failed, timed out, or rework-limit conditions
- **THEN** the system can surface those runs as requiring manual intervention

## ADDED Requirements

### Requirement: Operators can perform manual intervention actions from the run workspace
The system SHALL provide state-appropriate manual intervention actions for a run that requires attention, including at least opening its debug context and invoking the allowed continuation, retry, or stop action for the current state.

#### Scenario: Retry or continue an attention run
- **WHEN** an operator opens a run that requires manual intervention and chooses an action allowed for its current state
- **THEN** the system executes the selected action and updates the run workspace with the resulting state
