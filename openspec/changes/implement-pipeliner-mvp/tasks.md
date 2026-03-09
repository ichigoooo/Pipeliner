## 1. Project Setup

- [x] 1.1 Initialize the Python project structure for API, runtime, persistence, storage, CLI, and minimal UI modules
- [x] 1.2 Add and configure core dependencies for FastAPI, Pydantic, SQLAlchemy, Alembic, Typer, and pytest
- [x] 1.3 Add base application configuration for local development, SQLite, and run-root workspace paths

## 2. Protocol Models and Workflow Loading

- [x] 2.1 Implement Pydantic models for workflow spec, node callback payload, artifact manifest, and runtime guards
- [x] 2.2 Implement workflow spec validation and lint rules, including required fields, dependency consistency, and cycle detection
- [x] 2.3 Implement workflow definition and workflow version loading, registration, and retrieval interfaces with clear canonical-spec boundaries

## 3. Persistence and Run Workspace

- [x] 3.1 Create database models and migrations for workflow definitions, workflow versions, runs, node runs, callback events, and artifacts
- [x] 3.2 Implement repository or service-layer persistence for creating runs, node rounds, callback events, and artifact records
- [x] 3.3 Implement run-root workspace creation and local filesystem layout for inputs, node work directories, manifests, payloads, and callback archives

## 4. Runtime State Machine

- [x] 4.1 Implement the minimum run and node-run state machine with executor, validator, pass, revise, blocked, failed, and timeout paths
- [x] 4.2 Implement guard enforcement for timeout, max rework rounds, and manual-stop boundaries
- [x] 4.3 Implement runtime coordination logic for handing executor outputs to validator review and returning revise feedback for rework without semantic judgment in Runtime

## 5. Callback and Artifact Flow

- [x] 5.1 Implement the unified callback API endpoint for executor and validator result submission
- [x] 5.2 Implement callback idempotency handling keyed by `event_id` and reject invalid revise payloads
- [x] 5.3 Implement artifact manifest registration, artifact reference resolution, and immutable artifact version publishing

## 6. Operator Surface

- [x] 6.1 Implement a minimal operator command or API flow to register a workflow version and start a run with workflow inputs
- [x] 6.2 Implement minimal workflow, run, node, callback, and artifact inspection views for troubleshooting and manual intervention discovery
- [x] 6.3 Implement minimal operator visibility for blocked, failed, timed out, or rework-limited runs

## 7. Verification and Developer Support

- [x] 7.1 Add targeted tests for protocol validation, callback idempotency, runtime transitions, and artifact registration
- [x] 7.2 Add one end-to-end MVP workflow fixture covering executor pass, validator revise, and blocked or timeout paths
- [x] 7.3 Document local development and MVP usage flow for registering workflows, starting runs, inspecting execution state, and understanding the canonical workflow view
