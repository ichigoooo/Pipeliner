## MODIFIED Requirements

### Requirement: Operators can identify runs requiring manual intervention
The system SHALL expose runs and nodes that require manual intervention because of blocked, failed, timeout, or guard-limit outcomes, SHALL present the stop reason and current actionable context in an attention queue or equivalent view, and SHALL remove a run from those views once the operator permanently deletes that run.

#### Scenario: Remove an attention run from the queue
- **WHEN** an operator permanently deletes a run that is currently in `needs_attention`
- **THEN** the system removes that run from the attention queue and the general run list

### Requirement: Operators can perform manual intervention actions from the run workspace
The system SHALL provide state-appropriate manual intervention actions for a run that requires attention, including at least opening its debug context, invoking the allowed continuation, retry, or stop action for the current state, and permanently deleting the run when the run is no longer executing.

#### Scenario: Delete a non-running run from the workspace
- **WHEN** an operator opens a run whose status is `needs_attention`, `stopped`, or `completed` and confirms deletion
- **THEN** the system permanently deletes the run record and its run workspace, and the run detail endpoint is no longer available

#### Scenario: Reject deletion for an active run
- **WHEN** an operator attempts to delete a run whose status is `running`
- **THEN** the system rejects the request and preserves the run record and workspace

### Requirement: Operators can inspect batch results and retain row history
The system SHALL expose batch detail rows even if a referenced run was permanently deleted later, and SHALL mark that row as referring to a deleted run while disabling run-specific navigation or workspace-opening actions for that row.

#### Scenario: Keep batch row history after deleting a run
- **WHEN** a batch item references a run that has since been permanently deleted
- **THEN** the batch detail still shows the original row and run identifier, marks the run as deleted, and does not offer links or folder-opening actions for that run
