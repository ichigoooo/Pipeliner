## ADDED Requirements

### Requirement: Authoring agent runs with project skill context
The system SHALL invoke the authoring agent with the workflow project directory as its working directory so that `.claude/skills` are discoverable.

#### Scenario: Generate draft using project skills
- **WHEN** the authoring agent is invoked for a workflow draft
- **THEN** the agent executes in `projects/<workflow_id>` and can discover the project skills

### Requirement: Authoring agent respects node skill bindings
The authoring agent SHALL keep `executor.skill` and `validators[].skill` consistent with the node skill packages in the project.

#### Scenario: Draft generation preserves skill bindings
- **WHEN** the authoring agent produces a new draft
- **THEN** the draft includes valid executor and validator skill names that map to project skills
