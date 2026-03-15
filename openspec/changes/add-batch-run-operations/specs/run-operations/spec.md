## ADDED Requirements

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
