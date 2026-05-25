## Purpose

Enable operators to start, monitor, debug, and manually intervene in workflow runs through both API-level mechanisms and the Workflow Studio interface.

## Requirements

### Requirement: Operators can clean up non-running runs and completed batches in bulk
The system SHALL allow operators to select one or more non-running runs from the Studio run inventory and delete them in a single action, SHALL allow operators to delete one or more batches whose status is no longer active, and SHALL preserve row-level batch history even when a referenced run was deleted later.

#### Scenario: Bulk delete selected non-running runs
- **WHEN** an operator selects multiple runs whose statuses are all non-running and confirms bulk deletion
- **THEN** the system deletes each selected run, removes them from the run inventory views, and deletes each corresponding run workspace

#### Scenario: Reject bulk deletion when any selected run is still active
- **WHEN** an operator submits a bulk deletion request that includes a `running` run
- **THEN** the system rejects the request and preserves every selected run and workspace

#### Scenario: Bulk delete completed batches
- **WHEN** an operator selects one or more batches whose status is not `pending` or `running` and confirms deletion
- **THEN** the system deletes those batch records and any remaining deletable run workspaces associated with them

#### Scenario: Preserve batch row history after run cleanup
- **WHEN** a batch item references a run that was deleted individually or through a bulk operation
- **THEN** the batch detail still shows the original row, marks the referenced run as deleted, and disables run-specific navigation or folder-opening actions for that row

### Requirement: Operators can start a run for a workflow version
The system SHALL provide both API-level and studio-facing mechanisms to start a workflow run for a selected workflow version with the required workflow inputs, SHALL render a structured input form when supported workflow input metadata is available, SHALL allow fallback to raw JSON input when metadata is missing or unsupported, SHALL create the run as immediately observable in the run workspace, and SHALL auto-drive the run by default unless the caller explicitly disables automatic driving.

#### Scenario: Start a run with valid structured form inputs
- **WHEN** an operator submits run creation for a registered workflow version through Studio using valid structured workflow input values
- **THEN** the system creates the run, starts automatic driving by default, and makes its execution state observable

#### Scenario: Start a run with valid inputs
- **WHEN** an operator submits a run request for a registered workflow version with the required inputs
- **THEN** the system creates the run, starts automatic driving by default, and makes its execution state observable

#### Scenario: Fall back to raw JSON input for a legacy workflow
- **WHEN** an operator opens run creation for a workflow version whose workflow inputs cannot be fully rendered as supported structured controls
- **THEN** the system allows the operator to review or enter raw JSON input and use that payload for run creation

#### Scenario: Disable automatic driving for advanced control
- **WHEN** an API caller explicitly disables automatic driving while creating a run
- **THEN** the system creates the run without starting a driver and keeps the run observable for later manual dispatch or drive actions

### Requirement: Operators can inspect run and node execution status
The system SHALL provide a run workspace that exposes current and historical run state, node state, round number, waiting actor, and terminal or waiting conditions, SHALL provide a workflow-graph or equivalent progression view that highlights the current active or next-dispatchable node round while the run is still executing, SHALL surface a recent activity feed suitable for live monitoring, SHALL let operators switch node-level details between terminal output, artifacts, callbacks, and raw inspection data, SHALL follow the current focus node round by default while the run is executing, and SHALL let an operator temporarily pin a historical node round until the operator explicitly returns to the current focus.

#### Scenario: View a blocked node
- **WHEN** an operator inspects a run containing a blocked node
- **THEN** the system shows the node as blocked together with its current round and stop condition

#### Scenario: Monitor a currently running node
- **WHEN** an operator opens a run that is still executing
- **THEN** the system highlights the current focus node round in the workflow graph, shows the waiting actor or active role, and presents recent run activity in time order

#### Scenario: Inspect node details from the workflow graph
- **WHEN** an operator clicks a node in the run workspace workflow graph
- **THEN** the system opens that node's latest round details and lets the operator switch between terminal output, artifacts, callbacks, and raw inspection data

#### Scenario: Keep inspecting a historical round during auto-refresh
- **WHEN** an operator manually selects a historical node round while the run is still refreshing
- **THEN** the system keeps that historical round selected until the operator explicitly returns to the current focus

#### Scenario: Explain slow-start and queued states before timeout
- **WHEN** the current focus node round has started a Claude-backed role but has not produced output yet
- **THEN** the system distinguishes whether the round is queued, started with no output yet, or has exceeded the configured first-byte threshold without treating that state as a terminal timeout

### Requirement: Operators can inspect artifact and callback history for troubleshooting
The system SHALL provide access to artifact metadata, callback event history, and related round-level debugging context for a run, including raw protocol payloads or references needed for audit and troubleshooting.

#### Scenario: View callback history for a node round
- **WHEN** an operator requests details for a node round
- **THEN** the system shows the recorded callback events and referenced artifacts for that round

### Requirement: Operators can identify runs requiring manual intervention
The system SHALL expose runs and nodes that require manual intervention because of blocked, failed, timeout, or guard-limit outcomes, SHALL present the stop reason and current actionable context in an attention queue or equivalent view, and SHALL keep actionable runs visually separated from currently running runs and archived terminal runs within the main Studio run inventory.

#### Scenario: List runs requiring manual handling
- **WHEN** one or more runs stop because of blocked, failed, timed out, or rework-limit conditions
- **THEN** the system can surface those runs as requiring manual intervention

#### Scenario: Keep active and archived runs discoverable without hiding attention items
- **WHEN** an operator opens the Studio run inventory
- **THEN** the system presents attention runs, currently running runs, and archived terminal runs in separate groups so that actionable work is not buried by historical noise

### Requirement: Operators can perform manual intervention actions from the run workspace
The system SHALL provide state-appropriate manual intervention actions for a run that requires attention, including at least opening its debug context and invoking the allowed continuation, retry, or stop action for the current state.

#### Scenario: Retry or continue an attention run
- **WHEN** an operator opens a run that requires manual intervention and chooses an action allowed for its current state
- **THEN** the system executes the selected action and updates the run workspace with the resulting state

### Requirement: Operators can auto-drive a run
The system SHALL provide an operator-facing action to auto-drive a run until a terminal or attention state, with a configurable maximum step limit, and SHALL prevent overlapping drive operations for the same run.

#### Scenario: Auto-drive a run
- **WHEN** an operator submits an auto-drive request with a max step limit
- **THEN** the system dispatches executable nodes until the run stops or the limit is reached

#### Scenario: Reject overlapping drive requests
- **WHEN** an operator submits a drive request for a run that already has an active driver instance
- **THEN** the system rejects the overlapping request and preserves the currently running driver

### Requirement: Operators can view live execution output for the current node round
The system SHALL expose the currently active executor or validator call for the current focus node round, and SHALL allow the run workspace to stream or poll incremental textual output for that call while it is running.

#### Scenario: View executor output while a node is running
- **WHEN** an operator opens a run whose current focus node round has started an executor call
- **THEN** the system exposes the executor call identifier and incremental textual output for that call

#### Scenario: Show queued execution before output is available
- **WHEN** a node round is the current focus but no executor or validator call has started yet
- **THEN** the system still shows that the round is queued or waiting for dispatch rather than appearing idle

### Requirement: Operators can distinguish automatic driving state from manual controls
The system SHALL expose the current driver state for a run, including whether automatic driving is active, and SHALL let the run workspace disable conflicting manual drive actions while a driver is already running.

#### Scenario: Disable manual drive while automatic driving is active
- **WHEN** an operator views a run that is currently being auto-driven
- **THEN** the system marks the driver as active and disables conflicting manual drive controls

#### Scenario: Re-enable manual drive after driver stops
- **WHEN** the current driver for a run reaches a terminal, attention, stopped, or max-step condition
- **THEN** the system marks the driver as inactive and allows a later manual drive request if the run state still permits it

### Requirement: Operators can manually dispatch executor or validator
The system SHALL allow an operator to manually dispatch an executor or validator for a specific node round from the studio.

#### Scenario: Manually dispatch a node role
- **WHEN** an operator selects a node round and triggers executor or validator dispatch
- **THEN** the system performs the dispatch and records the callback events

### Requirement: Operators can start and monitor batch runs for a workflow version
The system SHALL provide a workflow-version-scoped CSV template containing all declared workflow input names, SHALL accept a CSV upload to create a batch run, SHALL validate each row independently, SHALL execute valid rows sequentially with at most one active run at a time within the batch, and SHALL expose a batch detail view with row-level run status, error reporting, run links, and workspace-opening actions.

#### Scenario: Download a workflow input CSV template
- **WHEN** an operator views a workflow version in Studio and requests the batch template
- **THEN** the system returns a CSV file whose header row contains every declared workflow input name for that workflow version

#### Scenario: Create a batch run from CSV rows
- **WHEN** an operator uploads a CSV file for a workflow version
- **THEN** the system creates a batch run, records one batch item per CSV row, and marks rows with invalid inputs as failed without preventing valid rows from continuing

#### Scenario: Execute batch items sequentially
- **WHEN** a batch run contains multiple valid rows waiting to execute
- **THEN** the system starts and auto-drives only one row's run at a time, waits for that run to reach a terminal state, and only then advances to the next pending row

#### Scenario: Inspect batch results and open a run workspace
- **WHEN** an operator opens a batch detail view after one or more rows have started
- **THEN** the system shows aggregate batch progress, the row-level status and linked run for each item, and allows the operator to open the workspace of a row that produced a run
