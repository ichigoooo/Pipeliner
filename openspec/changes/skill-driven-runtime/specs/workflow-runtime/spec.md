## ADDED Requirements

### Requirement: Runtime dispatch uses project skill directory
The runtime SHALL dispatch executor and validator tasks using the workflow project directory as the working directory.

#### Scenario: Executor dispatch uses project directory
- **WHEN** the runtime dispatches a node executor task
- **THEN** the executor process runs in `projects/<workflow_id>` so that `.claude/skills` are available

### Requirement: Runtime ensures project directory exists
The runtime SHALL ensure the workflow project directory exists before dispatching executor or validator tasks.

#### Scenario: Initialize missing project directory
- **WHEN** a run is dispatched for a workflow without a local project directory
- **THEN** the runtime creates the minimal project directory structure needed for skill discovery
