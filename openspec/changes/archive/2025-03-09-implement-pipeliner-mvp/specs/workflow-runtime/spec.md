## ADDED Requirements

### Requirement: Runs are created from a specific workflow version
The system SHALL create each workflow run from an explicit workflow version and SHALL persist the run with an initial execution state.

#### Scenario: Create a run from a workflow version
- **WHEN** an operator starts a run against a registered workflow version
- **THEN** the system creates a new run record linked to that workflow version and marks the run as active

### Requirement: Runtime advances nodes through executor and validator phases
The runtime SHALL progress each node through executor submission, validator review, and terminal pass, revise, or blocked outcomes according to callback results.

#### Scenario: Executor completion sends node to validator
- **WHEN** the runtime receives a successful executor callback for a node round
- **THEN** the node round transitions from awaiting executor to awaiting validator

#### Scenario: Validator pass unlocks downstream work
- **WHEN** the runtime receives a validator callback with verdict `pass`
- **THEN** the current node round is marked passed and downstream eligible nodes become runnable

#### Scenario: Validator revise triggers another round
- **WHEN** the runtime receives a validator callback with verdict `revise`
- **THEN** the runtime opens the next round for the same node and returns the rework brief to the executor path

### Requirement: Runtime enforces safety guard boundaries
The runtime SHALL enforce timeout, maximum rework rounds, and blocked or failed manual stop boundaries before continuing a run.

#### Scenario: Blocked verdict pauses automation
- **WHEN** a validator returns verdict `blocked`
- **THEN** the runtime marks the node and run as requiring manual intervention and does not auto-advance

#### Scenario: Rework limit stops further automatic retries
- **WHEN** a node exceeds the configured maximum rework rounds
- **THEN** the runtime stops automatic progression for that node and marks the run for manual intervention
