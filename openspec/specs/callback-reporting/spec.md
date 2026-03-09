## Purpose

TBD

## Requirements

### Requirement: Executor and validator callbacks use one unified reporting protocol
The system SHALL accept executor and validator callbacks through a unified callback contract that identifies actor role, run, node, round, execution status, and result payload.

#### Scenario: Accept executor callback payload
- **WHEN** an executor submits a callback containing run identity, node identity, round number, execution status, and artifact references
- **THEN** the system records the callback event and evaluates it as an executor result for that node round

#### Scenario: Accept validator callback payload
- **WHEN** a validator submits a callback containing run identity, node identity, round number, execution status, verdict, and optional rework brief
- **THEN** the system records the callback event and evaluates it as a validator result for that node round

### Requirement: Callback events are idempotent by event_id
The system SHALL treat `event_id` as the idempotency key for callback ingestion and SHALL prevent duplicate event processing from causing duplicate state transitions.

#### Scenario: Duplicate callback does not advance twice
- **WHEN** the same callback `event_id` is submitted more than once
- **THEN** the system stores or recognizes it as the same event and does not apply state progression twice

### Requirement: Invalid validator revise payloads are rejected
The system SHALL reject validator callbacks with verdict `revise` if they do not include a non-empty `rework_brief.must_fix` list.

#### Scenario: Reject revise callback without actionable fixes
- **WHEN** a validator submits verdict `revise` with a missing or empty `must_fix` list
- **THEN** the system rejects the callback as invalid instead of treating it as a successful review
