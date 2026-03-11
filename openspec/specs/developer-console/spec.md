## Purpose

Provide a developer-first Workflow Studio console that enables inspection and operation of workflows, runs, and configuration through synchronized multi-view projections and raw protocol inspection.

## Requirements

### Requirement: Workflow Studio provides synchronized workflow projections
The system SHALL provide a workflow workspace that lets users inspect the same workflow draft or published version through cards, graph, spec, and lint views without introducing a second source of truth.

#### Scenario: Inspect the same workflow through multiple views
- **WHEN** a user opens a workflow in the studio and switches between cards, graph, spec, and lint views
- **THEN** each view reflects the same canonical workflow content for the selected revision or version

### Requirement: Workflow Studio exposes a developer-oriented inspector
The system SHALL provide a developer-oriented inspector that shows the selected workflow, node, run, callback, artifact, or configuration object in structured raw form alongside the higher-level view.

#### Scenario: Inspect a selected node in raw form
- **WHEN** a user selects a node from the workflow graph or node list
- **THEN** the studio shows the node's structured raw fields in an inspector without hiding the higher-level view

### Requirement: Workflow Studio provides a run debugging workspace
The system SHALL provide a run debugging workspace that combines run summary, node rounds, callback events, artifact references, execution context, and log references for the selected run.

#### Scenario: Inspect a node round from the run workspace
- **WHEN** a user opens a run and selects a specific node round
- **THEN** the studio shows the round state together with its callbacks, referenced artifacts, and available context or log references

### Requirement: Workflow Studio exposes resolved settings and configuration provenance
The system SHALL provide a settings workspace that shows resolved runtime configuration values together with their provenance.

#### Scenario: Inspect a resolved command template
- **WHEN** a user opens the settings workspace and inspects an executor or validator command template
- **THEN** the studio shows the currently effective value together with the source that supplied it
