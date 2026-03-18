## ADDED Requirements

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

## MODIFIED Requirements

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

### Requirement: Operators can identify runs requiring manual intervention
The system SHALL expose runs and nodes that require manual intervention because of blocked, failed, timeout, or guard-limit outcomes, SHALL present the stop reason and current actionable context in an attention queue or equivalent view, and SHALL keep actionable runs visually separated from currently running runs and archived terminal runs within the main Studio run inventory.

#### Scenario: List runs requiring manual handling
- **WHEN** one or more runs stop because of blocked, failed, timed out, or rework-limit conditions
- **THEN** the system can surface those runs as requiring manual intervention

#### Scenario: Keep active and archived runs discoverable without hiding attention items
- **WHEN** an operator opens the Studio run inventory
- **THEN** the system presents attention runs, currently running runs, and archived terminal runs in separate groups so that actionable work is not buried by historical noise
