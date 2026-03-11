## 1. Skill Packaging & Validation

- [x] 1.1 Implement node-level skill package creation (executor + validators) with safe defaults
- [x] 1.2 Add skill naming validation (kebab-case, length, reserved words) and uniqueness checks
- [x] 1.3 Add node context reference file generation and update rules (no overwrite of SKILL.md)

## 2. Authoring & Iteration Integration

- [x] 2.1 Hook skill package generation into authoring draft save/generate flows
- [x] 2.2 Hook skill package refresh into iteration flows (from version/attention)
- [x] 2.3 Update authoring agent prompts to reference node skills and project working directory

## 3. Runtime Dispatch Updates

- [x] 3.1 Ensure runtime resolves project root for runs and initializes minimal structure if missing
- [x] 3.2 Switch executor dispatch working directory to project root while keeping artifact paths absolute
- [x] 3.3 Switch validator dispatch working directory to project root and preserve current result handling

## 4. Tests & Documentation

- [x] 4.1 Add tests for skill package creation and validation failures
- [x] 4.2 Add tests for authoring/iteration skill sync and runtime dispatch cwd
- [x] 4.3 Update docs to describe node skill packaging and runtime skill discovery behavior
