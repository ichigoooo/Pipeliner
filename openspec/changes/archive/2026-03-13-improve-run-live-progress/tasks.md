## 1. Automatic Run Driving

- [x] 1.1 Extend run creation requests to accept `auto_drive`, default it to enabled, and start a background driver after run creation
- [x] 1.2 Add a lightweight run-drive coordinator with per-run single-flight protection and explicit driver status reporting
- [x] 1.3 Prevent overlapping manual `/drive` requests while a driver is already active and return a clear conflict response

## 2. Live Run Overview Aggregation

- [x] 2.1 Extend run overview payloads with `driver`, `current_focus`, and `activity` aggregates derived from existing run, node, callback, and Claude call state
- [x] 2.2 Identify the current focus node round for live monitoring and expose the active executor or validator call identifiers when available
- [x] 2.3 Surface queued-or-waiting states even before a Claude call has emitted any output so active runs never appear idle

## 3. Run Workspace Experience

- [x] 3.1 Start runs from Workflow Studio with automatic driving enabled by default and keep the run detail page as the post-start landing target
- [x] 3.2 Rework the run detail page to auto-focus the current node round, show a highlighted workflow graph, and let operators inspect node details via tabbed terminal / artifacts / callbacks / raw views
- [x] 3.3 Default-open the active Claude terminal panel, show driver state in the UI, and disable conflicting manual `Drive` controls while auto-drive is running
- [x] 3.4 Use faster polling while runs are active and fall back to slower refresh after terminal states

## 4. Verification

- [x] 4.1 Add backend coverage for auto-drive startup, driver conflict handling, and the new run overview aggregates
- [x] 4.2 Add frontend coverage for default current-node focus, activity feed rendering, driver-state UI, and manual-drive disabled states
- [x] 4.3 Run the targeted backend and frontend test suites that cover run creation, run driving, and the run detail workspace
