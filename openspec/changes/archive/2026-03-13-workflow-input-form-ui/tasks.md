## 1. Workflow Schema And Validation

- [x] 1.1 Extend workflow input definition parsing and validation to accept optional form metadata for supported input types, defaults, enum options, and scalar constraints
- [x] 1.2 Implement legacy input descriptor normalization so existing workflow definitions without form metadata remain runnable
- [x] 1.3 Add validation coverage for invalid form metadata, legacy compatibility, and run-input serialization rules

## 2. Workflow Authoring Experience

- [x] 2.1 Add Workflow Studio input-field editing controls for input type, required flag, default value, enum options, and scalar constraints
- [x] 2.2 Persist authored input form metadata into the canonical workflow draft spec and keep raw spec projections in sync
- [x] 2.3 Surface draft validation feedback for invalid workflow input configuration before publish

## 3. Run Input Form Experience

- [x] 3.1 Build the run-start input descriptor and typed form renderer for supported workflow input types
- [x] 3.2 Implement manual local file-path entry, structured field validation, and generation of the standard run input JSON payload
- [x] 3.3 Add a raw JSON fallback mode for legacy or unsupported workflow input definitions without breaking run creation

## 4. End-To-End Verification

- [x] 4.1 Add end-to-end coverage for authoring typed inputs, publishing a workflow version, and starting a run from the structured form
- [x] 4.2 Add regression coverage for legacy workflow definitions that start runs through derived defaults or raw JSON fallback
