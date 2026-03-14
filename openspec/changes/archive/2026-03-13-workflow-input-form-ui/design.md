## Context

Workflow definitions currently expose only a thin input contract (`name`, `shape`, `required`, `summary`). That is sufficient for validation and runtime payload wiring, but it is not sufficient for Workflow Studio to render an operator-friendly input experience. In practice, operators still need to hand-author JSON before starting a run, and workflow authors cannot declare how an input should be entered or constrained in the UI.

This change adds typed workflow input metadata that can be authored in Workflow Studio, stored in the canonical workflow spec, and consumed by the run-start experience. The implementation must preserve compatibility with existing workflow definitions that do not yet declare typed metadata.

The affected areas are cross-cutting:

- workflow definition validation and compatibility behavior
- workflow authoring draft editing and persistence
- run-start UI, client-side validation, and request serialization

## Goals / Non-Goals

**Goals:**

- Add a minimal, structured workflow input metadata model that is rich enough to drive form rendering for common scalar and local file-path string inputs.
- Let authors configure input types and constraints during workflow creation and editing without requiring raw JSON edits.
- Render typed run-start forms from workflow input metadata and serialize them into the existing run input payload shape.
- Keep existing workflow definitions runnable by deriving sensible defaults and preserving a raw JSON fallback path.

**Non-Goals:**

- Introducing nested object or array form builders beyond the existing raw JSON escape hatch.
- Uploading file contents to the backend or artifact registry as part of run creation; file inputs remain local path references.
- Changing the runtime execution protocol or node-level input contracts.
- Replacing the raw spec editor for advanced users.

## Decisions

### 1. Workflow-level inputs gain a dedicated form metadata block

Workflow inputs will continue to use `shape` as the contract-level data shape. A new optional form metadata block will carry UI-oriented information such as input type, default value, enum options, and scalar constraints.

This separates two concerns cleanly:

- `shape` remains the stable workflow contract already used by validation and downstream reasoning.
- form metadata expresses how Studio should collect the value from an operator.

Alternative considered:

- Overloading `shape` to represent both contract shape and UI input type was rejected because `shape` is already used as a broader contract concept (`json`, `file`, etc.) and cannot cleanly express enum options or numeric constraints without becoming ambiguous.

### 2. The canonical workflow spec remains the single source of truth

The authoring UI will edit structured controls, but persistence still writes the canonical workflow spec. The raw spec view, validation pipeline, and publish flow therefore continue to operate on one representation rather than a parallel authoring-only model.

Alternative considered:

- Storing separate authoring-only UI metadata outside the workflow spec was rejected because it would create drift between what authors configure and what runtime consumes.

### 3. Runtime derives a normalized input descriptor before rendering

The run-start experience will build a normalized descriptor for each workflow input:

- If explicit form metadata exists, use it.
- If explicit metadata is absent, derive a default descriptor from the existing input definition.
- If the resulting descriptor is unsupported or ambiguous, fall back to raw JSON editing for that input set.

The derivation rules stay intentionally small:

- `shape = file` defaults to a local path text field.
- `shape = json` defaults to a raw JSON textarea.
- other legacy shapes default to simple text entry unless explicit metadata says otherwise.

Alternative considered:

- Rejecting legacy workflows until authors backfill typed metadata was rejected because it would break existing runnable definitions and create unnecessary migration work.

### 4. Validation is split between immediate UI feedback and authoritative backend checks

Studio should provide inline feedback for obvious errors such as missing enum options, invalid numeric bounds, or missing required values. The backend remains authoritative for definition validation and run-start validation so API-created runs and raw JSON submissions follow the same rules.

Alternative considered:

- Client-only validation was rejected because it would allow invalid definitions or run inputs to bypass Studio.

### 5. File inputs remain manual local-path entry in MVP

File-type inputs use manual local path string entry and store that value in the generated run input JSON. This keeps the payload batch-friendly, matches CLI-style launch flows, and avoids adding browser-native file integration, upload, staging, or artifact-registration concerns to this change.

Alternative considered:

- Opening a local file chooser was rejected for the web Studio MVP because standard browser environments cannot reliably provide a usable local absolute path, and because batch launch flows still need plain path-string input.
- Immediate upload or artifact registration at input time was rejected because it would expand scope into storage lifecycle, security, and transport concerns not required to make run input authoring usable.

## Risks / Trade-offs

- [Schema drift between legacy and typed inputs] -> Normalize descriptors in one shared utility and reuse it in authoring preview, run-start rendering, and server-side validation.
- [Authors may expect richer field types such as lists or nested objects] -> Keep raw JSON fallback available and document MVP-supported types clearly.
- [Local file paths are environment-specific] -> Treat file inputs as operator-local path strings and validate only presence and path string shape during run creation.
- [Two entry modes can confuse operators] -> Default to the structured form when possible and expose raw JSON as an explicit fallback rather than a competing primary mode.

## Migration Plan

1. Extend workflow input validation to accept optional form metadata while preserving existing definitions with no metadata.
2. Update authoring draft persistence so new or edited inputs can store typed metadata in the canonical workflow spec.
3. Update run creation UI and backend validation to consume normalized input descriptors.
4. Keep raw JSON entry available during rollout so unsupported or partially migrated workflows remain operable.
5. If rollout issues appear, disable the structured form renderer and keep raw JSON entry active because the canonical run payload shape is unchanged.

## Open Questions

- Should enum options support separate display labels in MVP, or only stored values?
- Do we need an explicit `json` form type distinct from `shape = json`, or is raw JSON textarea sufficient for the first iteration?
- Should run-start remember the last submitted values per workflow version, or is that a later usability improvement?
