## 1. Backend Batch Run Orchestration

- [x] 1.1 Add batch run persistence models, repository support, and service logic for CSV template generation, CSV parsing, row validation, and batch/item state transitions
- [x] 1.2 Add batch run API endpoints for template download, batch creation, batch detail lookup, and run workspace opening, and wire a sequential batch coordinator that reuses existing auto-drive behavior
- [x] 1.3 Add backend verification coverage for CSV-driven batch creation, row-level failure handling, batch detail inspection, and run workspace opening

## 2. Workflow Studio Batch Launch Experience

- [x] 2.1 Extend the workflow version page with template download and batch-start entry points alongside the existing single-run start flow
- [x] 2.2 Build the batch upload panel and the batch detail page with aggregate counters, row-level statuses, run detail links, open-workspace actions, and active polling while a batch is still running
- [x] 2.3 Update the frontend API/route proxy layer to support batch-run endpoints and `multipart/form-data` uploads without breaking existing JSON-based calls

## 3. Verification

- [x] 3.1 Add frontend coverage for batch launch entry points and batch detail interactions
- [x] 3.2 Run targeted backend and frontend verification for batch-run flows, including production build validation
