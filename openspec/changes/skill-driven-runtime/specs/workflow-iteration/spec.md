## ADDED Requirements

### Requirement: Iteration updates node skill packages when drafts change
The system SHALL update node skill packages and references as part of workflow iteration.

#### Scenario: Update skill references during iteration
- **WHEN** an iteration creates a new draft revision with modified nodes
- **THEN** the system refreshes the corresponding skill reference files for affected nodes
