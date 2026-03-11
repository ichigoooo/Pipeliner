## ADDED Requirements

### Requirement: Operators can auto-drive a run
The system SHALL provide an operator-facing action to auto-drive a run until a terminal or attention state, with a configurable maximum step limit. 
#### Scenario: Auto-drive a run
- **WHEN** an operator submits an auto-drive request with a max step limit
- **THEN** the system dispatches executable nodes until the run stops or the limit is reached

### Requirement: Operators can manually dispatch executor or validator
The system SHALL allow an operator to manually dispatch an executor or validator for a specific node round from the studio. 
#### Scenario: Manually dispatch a node role
- **WHEN** an operator selects a node round and triggers executor or validator dispatch
- **THEN** the system performs the dispatch and records the callback events
