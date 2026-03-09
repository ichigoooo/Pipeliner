## 1. Frontend Foundation

- [ ] 1.1 Create the formal studio frontend app with the chosen React/TypeScript framework and shared layout shell
- [ ] 1.2 Add the frontend data access, routing, state query, and editor/graph dependencies needed for the studio
- [ ] 1.3 Define frontend module boundaries for authoring, workflows, runs, debug, attention, and settings

## 2. Authoring APIs And Data Model

- [ ] 2.1 Add backend models and persistence for authoring sessions, draft revisions, and publish metadata
- [ ] 2.2 Implement authoring APIs for session creation, session continuation, draft retrieval, raw spec save, lint retrieval, and publish
- [ ] 2.3 Implement server-side derivation for workflow view, graph projection, and lint report from a canonical draft spec

## 3. Workflow Studio Views

- [ ] 3.1 Build the workflow workspace with cards, graph, spec, and lint tabs backed by the same canonical revision or version
- [ ] 3.2 Build the developer inspector that can show raw workflow and node fields alongside higher-level views
- [ ] 3.3 Add workflow list and version list pages that link into authoring and run start flows

## 4. Run Workspace And Debugging

- [ ] 4.1 Add aggregated backend APIs for run summary, timeline or progression, node rounds, callbacks, artifacts, context, and log references
- [ ] 4.2 Build the run detail workspace with timeline or graph, node round selection, callback/artifact panels, and raw protocol inspector
- [ ] 4.3 Extend run actions to support studio-triggered start, stop, and state-appropriate manual intervention operations

## 5. Attention And Settings

- [ ] 5.1 Build the attention queue view for blocked, failed, timed out, and rework-limit runs
- [ ] 5.2 Add the settings workspace that shows resolved configuration values and their provenance
- [ ] 5.3 Expose provider, skill, command template, storage, and runtime guard configuration through backend settings snapshot APIs

## 6. Validation And Integration

- [ ] 6.1 Add backend tests for authoring session lifecycle, publish gating, aggregated run debug APIs, and manual intervention actions
- [ ] 6.2 Add frontend tests for synchronized workflow views, run workspace inspection flows, and settings provenance display
- [ ] 6.3 Verify the end-to-end developer workflow from authoring a pipeline to launching a run, inspecting artifacts/callbacks, and handling an attention state
