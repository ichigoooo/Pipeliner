## Purpose

Provide a structured form-based interface for entering workflow inputs during run creation, supporting typed input controls with validation while maintaining backward compatibility with legacy workflow definitions.

## Requirements

### Requirement: Workflow Studio renders typed workflow input controls
The system SHALL derive a renderable workflow input form from the workflow definition and SHALL render controls for supported input types including `string`, `number`, `boolean`, `enum`, `file`, and `json`.

#### Scenario: Render supported typed inputs
- **WHEN** an operator opens run creation for a workflow version whose inputs declare supported form metadata
- **THEN** the system shows a typed control for each input, pre-populates any declared default value, and labels required fields before submission

### Requirement: File inputs accept manual local path strings
The system SHALL provide a local path string input for workflow inputs declared as `file` and SHALL write the entered path into the generated run input payload.

#### Scenario: Enter a file path for a workflow input
- **WHEN** an operator enters a local file path into a `file` workflow input control
- **THEN** the system stores that path as the value for the workflow input and includes it in the generated run input payload

### Requirement: Workflow input forms validate and serialize before run creation
The system SHALL validate structured workflow input values against required flags, enum options, and declared scalar constraints before submitting the run request, and SHALL serialize accepted values into the standard run input JSON object keyed by workflow input name.

#### Scenario: Block invalid structured input submission
- **WHEN** an operator submits a workflow input form containing a missing required value or a value outside the declared constraints
- **THEN** the system blocks run creation and shows validation feedback for the offending field

#### Scenario: Submit structured form as standard run input JSON
- **WHEN** an operator submits a valid workflow input form
- **THEN** the system generates the standard run input JSON payload and uses that payload for run creation
