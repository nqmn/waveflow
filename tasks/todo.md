## Task: Phase 2 Array Quantization Helpers
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert this task's new helper/test files and export additions.
Change budget: files 3 functions: quantization helpers interfaces: risnet.arrays exports state mutations: None

### Scope
- risnet/arrays/quantization.py - additive uniform phase quantization helpers.
- risnet/arrays/__init__.py - export the additive helpers.
- tests/test_array_quantization.py - equivalence coverage against existing quantization code.

### Steps
- [x] Inspect current quantization APIs
- [x] Add additive array quantization wrappers
- [x] Add equivalence tests
- [x] Run focused and full verification

### Review
- Completed: Added additive quantization helpers and equivalence tests.
- Out-of-scope flagged: Pre-existing staged file moves and FUTURE.md changes were not touched.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations:

## Task: Phase 2 Route Low-Risk Array Call Sites
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the internal delegation edits in controller/ris_phase.
Change budget: files 3 functions: PhaseSteeringEngine._synthetic_element_positions, PhaseSteeringEngine.linear_steering_phases, PhaseQuantizer mapping helpers, UniformQuantizer.quantize interfaces: None state mutations: None

### Scope
- controller/ris_phase/phase_steering.py - delegate steering geometry/math to additive array primitives.
- controller/ris_phase/phase_quantization.py - delegate uniform quantizer mapping/math to additive quantization primitives.
- tests/test_array_primitives.py and tests/test_array_quantization.py - keep equivalence coverage meaningful after delegation.

### Steps
- [x] Route steering helpers through array primitives
- [x] Route uniform quantization helpers through array primitives
- [x] Run focused and full verification

### Review
- Completed: Routed low-risk steering and uniform quantization methods through array primitives.
- Out-of-scope flagged: Pre-existing staged file moves and unrelated modified docs/config remain untouched.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations:

## Task: Phase 3 Link Budget Channel Adapter
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Delete risnet/channels and its tests.
Change budget: files 4 functions: ChannelModel.evaluate, LinkBudgetChannel.evaluate interfaces: additive risnet.channels API state mutations: optional through existing RISNetwork.connect only

### Scope
- risnet/channels/base.py - channel protocol and evaluation result container.
- risnet/channels/link_budget.py - adapter over RISNetwork.connect.
- risnet/channels/__init__.py - public additive exports.
- tests/test_link_budget_channel.py - equivalence, blocked-path, and error-path coverage.

### Steps
- [x] Add channel protocol/result container
- [x] Add LinkBudgetChannel adapter
- [x] Add equivalence and error-path tests
- [x] Run focused and full verification

### Review
- Completed: Added the additive channel protocol and LinkBudgetChannel adapter with equivalence, blocked-path, and error coverage.
- Out-of-scope flagged: Existing staged moves and unrelated docs/config changes remain untouched.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: Adapter delegates to RISNetwork.connect; it is not a new physics implementation. Environment walls are characterized but not applied to connect link budget in this phase.

## Task: Phase 4 Extract Connect Node Lookup
Mode: Standard
Risk: High
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert core/network.py and the focused test additions for this task.
Change budget: files 2 functions: RISNetwork._resolve_connect_nodes, RISNetwork.connect interfaces: no public interface changes state mutations: None

### Scope
- core/network.py - extract the existing connect node lookup and missing-node error branch.
- tests/test_connect_characterization.py - add focused coverage for the extracted helper's success/error behavior.

### Steps
- [x] Extract node lookup helper without changing the public connect facade
- [x] Add service-level helper tests
- [x] Run focused and full verification

### Review
- Completed: Extracted connect node lookup into a helper and added direct helper coverage.
- Out-of-scope flagged: TUTORIAL.md remains modified but unrelated.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: Only the node lookup branch was extracted in this slice.

## Task: Soft Rebrand to Waveflow
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Broad / Trivial
Rollback plan: Revert the additive waveflow package wrappers, metadata edits, and docs rename edits.
Change budget: files 20 functions: package entry points only interfaces: PyPI name waveflow, CLI waveflow, import waveflow, compatibility risnet CLI/import state mutations: None

### Scope
- pyproject.toml - publish metadata and scripts for waveflow while retaining risnet CLI alias.
- setup.py - mirror legacy setuptools metadata and scripts.
- waveflow/* - additive compatibility package that re-exports the existing implementation.
- README.md, INSTALL.md, TUTORIAL.md - primary docs rename and compatibility notes.
- tests/test_smoke.py - verify new CLI/import surface while keeping old alias coverage.

### Steps
- [x] Add additive waveflow package wrappers
- [x] Update package metadata and console scripts
- [x] Update primary docs for waveflow install/import/CLI
- [ ] Run focused verification

### Review
- Completed:
- Out-of-scope flagged:
- Assumptions invalidated:
- Known debt (acknowledged):
- Limitations:

## Task: Add Typer/Rich Terminal UI
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert risnet/terminal_cli.py and the entrypoint/test additions.
Change budget: files 3 functions: risnet.__main__.main, risnet.terminal_cli.run interfaces: additive --terminal/ui CLI surface state mutations: None

### Scope
- risnet/terminal_cli.py - additive Typer/Rich command surface.
- risnet/__main__.py - route --terminal and ui commands to the new terminal UI while preserving legacy behavior.
- tests/test_smoke.py - smoke coverage for the new terminal UI commands.

### Steps
- [x] Add lazy Typer/Rich terminal command module
- [x] Route terminal commands from existing entrypoint
- [x] Add smoke tests for terminal status and demo connect
- [x] Run focused and full verification

### Review
- Completed: Added lazy Typer/Rich terminal commands and routed them through --terminal/ui.
- Out-of-scope flagged:
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: Legacy cmd.Cmd shell remains the default CLI; Typer/Rich is additive.

## Task: Phase 4 connect facade decomposition
Mode: Standard
Risk: High
Confidence: Guarded
Operational risk: Broad / Partial
Rollback plan: Revert the helper extraction in `core/network.py` and rerun connect characterization tests.
Change budget: [files 2] [functions: RISNetwork.connect, new internal helpers, targeted tests only if required] [interfaces: none] [state mutations: none beyond existing connect side effects]

### Scope
- `core/network.py` — extract a cohesive internal step from `RISNetwork.connect()` while preserving public behavior
- `tests/test_connect_characterization.py` — only if existing characterization coverage needs a narrow addition

### Steps
- [x] Capture task metadata and approved risk
- [x] Inspect connect internals and choose the smallest safe extraction
- [x] Implement the extraction behind the existing public facade
- [x] Verify targeted behavior and review diff scope

### Review
- Completed: Extracted beam/geometry/FOV preparation into `_resolve_connect_geometry()` and kept `RISNetwork.connect()` as the public compatibility facade.
- Out-of-scope flagged: Existing roadmap and branding changes remain untouched outside the current task.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: `pytest` is not installed in the current environment, so verification used `compileall` and direct runtime assertions instead of the full characterization runner.

## Task: Phase 4 connect phase extraction
Mode: Standard
Risk: High
Confidence: Guarded
Operational risk: Broad / Partial
Rollback plan: Revert the phase helper extraction in `core/network.py` and rerun the focused connect and channel pytest suites.
Change budget: [files 2] [functions: RISNetwork.connect, new internal phase helpers, targeted tests only if required] [interfaces: none] [state mutations: none beyond existing connect side effects]

### Scope
- `core/network.py` — extract phase computation and phase payload persistence from `RISNetwork.connect()` while preserving behavior
- `tests/test_connect_characterization.py` — only if a direct helper assertion becomes necessary

### Steps
- [x] Append task metadata and rollback notes
- [x] Extract phase computation helper
- [x] Extract phase payload/persistence helper
- [x] Run focused pytest verification and diff review

### Review
- Completed: Extracted `_compute_connect_phases()` and `_collect_connect_phase_data()` from `RISNetwork.connect()` while keeping the public result shape and canonical RIS-node persistence behavior unchanged.
- Out-of-scope flagged: Existing roadmap and branding changes remain untouched outside the current task.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: Verification ran through `.venv` because the system Python environment is externally managed.

## Task: Phase 4 connect tail extraction
Mode: Standard
Risk: High
Confidence: Guarded
Operational risk: Broad / Partial
Rollback plan: Revert the tail helper extraction in `core/network.py` and rerun the focused connect and channel pytest suites.
Change budget: [files 2] [functions: RISNetwork.connect, new result/persistence helpers, targeted tests only if required] [interfaces: none] [state mutations: none beyond existing connect side effects]

### Scope
- `core/network.py` — extract result assembly and persistence/update tail from `RISNetwork.connect()` while preserving behavior
- `tests/test_connect_characterization.py` — only if direct helper assertions become necessary

### Steps
- [x] Append task metadata and rollback notes
- [x] Extract result assembly helper
- [x] Extract metadata persistence and active-link/last-result update helpers
- [x] Run focused pytest verification and diff review

### Review
- Completed: Extracted `_build_connect_result()`, `_persist_connect_feedback_measurement()`, `_persist_connect_metadata()`, `_resolve_connect_reported_snr()`, `_store_connect_active_link()`, and `_store_last_connect_result()` while preserving the current ordering and compatibility behavior.
- Out-of-scope flagged: Existing roadmap and branding changes remain untouched outside the current task.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: Verification ran through `.venv` because the system Python environment is externally managed.

## Task: Phase 4 connect physics extraction
Mode: Standard
Risk: High
Confidence: Guarded
Operational risk: Broad / Partial
Rollback plan: Revert the physics helper extraction in `core/network.py` and rerun the focused connect and channel pytest suites.
Change budget: [files 2] [functions: RISNetwork.connect, new path-loss/gain/SNR helpers, targeted tests only if required] [interfaces: none] [state mutations: none beyond existing connect side effects]

### Scope
- `core/network.py` — extract the remaining path-loss, gain, fading, and array-factor SNR block from `RISNetwork.connect()` while preserving behavior
- `tests/test_connect_characterization.py` — only if direct helper assertions become necessary

### Steps
- [x] Append task metadata and rollback notes
- [x] Extract link-budget setup helper
- [x] Extract SNR and array-factor computation helper
- [x] Run focused pytest verification and diff review

### Review
- Completed: Extracted `_prepare_connect_link_budget()` and `_compute_connect_snr()` while preserving the current metric outputs and result ordering.
- Out-of-scope flagged: Existing roadmap and branding changes remain untouched outside the current task.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: Verification ran through `.venv` because the system Python environment is externally managed.

## Task: Phase 5 minimal scenario runner
Mode: Standard
Risk: Medium
Confidence: Guarded

Operational risk: Contained / Trivial
Rollback plan: Revert the additive scenario runner module and its focused tests.
Change budget: [files 3] [functions: new scenario runner API, targeted tests, additive export if required] [interfaces: additive risnet scenario surface only] [state mutations: none beyond existing network/load/connect side effects]

### Scope
- `risnet/scenarios.py` — additive headless scenario runner for JSON topologies
- `risnet/__init__.py` — only if a public export is needed
- `tests/test_scenarios.py` — focused headless runner coverage

### Steps
- [x] Add minimal scenario runner API on top of `NetworkIO` and `RISNetwork.connect()`
- [x] Add focused tests for loading topology JSON and executing a connect request
- [x] Run focused pytest verification and diff review

### Review
- Completed: Added `ScenarioRunner`/`ScenarioRunResult` for loading JSON topologies and executing a headless connect workflow, plus focused tests for load, run, and missing-node behavior.
- Out-of-scope flagged: Existing roadmap and branding changes remain untouched outside the current task.
- Assumptions invalidated: The stock `example_1_simple.json` topology is not directly connectable under default RIS FOV, so the execution test now uses a valid temporary topology while keeping the stock file for load-only coverage.
- Known debt (acknowledged):
- Limitations: This first slice supports JSON topology loading and a single headless connect flow; batch scenarios and richer scenario schemas remain future work.

## Task: Phase 5 scenario request schema
Mode: Standard
Risk: Medium
Confidence: Guarded
Operational risk: Contained / Trivial
Rollback plan: Revert the additive request-schema changes in `risnet/scenarios.py`, exports, and focused tests.
Change budget: [files 3] [functions: additive request dataclasses and run entrypoint, targeted tests, additive export if required] [interfaces: additive risnet scenario request surface only] [state mutations: none beyond existing network/load/connect side effects]

### Scope
- `risnet/scenarios.py` — additive request dataclasses and `run()` entrypoint for connect scenarios
- `risnet/__init__.py` — only for additive exports
- `tests/test_scenarios.py` — focused request-schema coverage

### Steps
- [x] Add minimal request dataclasses and `run()` entrypoint
- [x] Add focused tests for request-based execution
- [x] Run focused pytest verification and diff review

### Review
- Completed: Added `ConnectScenario`, `ScenarioRequest`, and `ScenarioRunner.run()` as a minimal explicit request surface on top of the headless runner, with focused request-schema coverage.
- Out-of-scope flagged: Existing roadmap and branding changes remain untouched outside the current task.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The request schema currently supports one connect action only; multi-step scenarios and richer declarative formats remain future work.

## Task: Phase 5 scenario action list
Mode: Standard
Risk: Medium
Confidence: Guarded
Operational risk: Contained / Trivial
Rollback plan: Revert the additive action-list changes in `risnet/scenarios.py`, exports, and focused tests.
Change budget: [files 3] [functions: additive action-list request handling and sequence result, targeted tests, additive export if required] [interfaces: additive risnet scenario action-list surface only] [state mutations: none beyond existing network/load/connect side effects]

### Scope
- `risnet/scenarios.py` — additive action-list support while preserving single-action request behavior
- `risnet/__init__.py` — only for additive exports
- `tests/test_scenarios.py` — focused multi-action coverage

### Steps
- [x] Add action-list request handling with backward-compatible single-action support
- [x] Add focused tests for multi-action execution
- [x] Run focused pytest verification and diff review

### Review
- Completed: Added action-list support with shared-network execution, `ScenarioSequenceResult`, and backward-compatible single-action request handling.
- Out-of-scope flagged: Existing roadmap and branding changes remain untouched outside the current task.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The action list currently supports repeated connect actions only; additional action types such as sweep remain future work.

## Task: Phase 5 sweep action support
Mode: Standard
Risk: Medium
Confidence: Guarded
Operational risk: Contained / Trivial
Rollback plan: Revert the additive sweep-action changes in `risnet/scenarios.py`, exports, and focused tests.
Change budget: [files 3] [functions: additive sweep dataclass and runner path, targeted tests, additive export if required] [interfaces: additive risnet scenario sweep surface only] [state mutations: none beyond existing network/load/sweep side effects]

### Scope
- `risnet/scenarios.py` — additive `SweepScenario` and sweep execution path
- `risnet/__init__.py` — only for additive exports
- `tests/test_scenarios.py` — focused sweep coverage

### Steps
- [x] Add dedicated sweep action support while preserving existing connect paths
- [x] Add focused tests for request-based sweep execution
- [x] Run focused pytest verification and diff review

### Review
- Completed: Added `SweepScenario`, request-based sweep execution, and mixed connect/sweep action-list support with shared-network execution.
- Out-of-scope flagged: Existing roadmap and branding changes remain untouched outside the current task.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The action list now supports connect and sweep only; richer declarative scenario documents and additional action types remain future work.

## Task: Phase 5 serializable scenario documents
Mode: Standard
Risk: Medium
Confidence: Guarded
Operational risk: Contained / Trivial
Rollback plan: Revert the additive document-parsing changes in `risnet/scenarios.py` and focused tests.
Change budget: [files 2] [functions: additive request parsing from dict/file, targeted tests] [interfaces: additive scenario document loading only] [state mutations: none beyond existing runner execution]

### Scope
- `risnet/scenarios.py` — additive `ScenarioRequest.from_dict()` and `from_file()` support for JSON/YAML
- `tests/test_scenarios.py` — focused document-loading coverage

### Steps
- [x] Add additive request parsing from dict and file
- [x] Add focused tests for JSON/YAML document loading and execution
- [x] Run focused pytest verification and diff review

### Review
- Completed: Added `ScenarioRequest.from_dict()` and `from_file()` with JSON/YAML support, plus focused tests for dict parsing and document-based execution.
- Out-of-scope flagged: Existing roadmap and branding changes remain untouched outside the current task.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The document format is intentionally minimal and maps directly onto the current dataclasses; schema validation and richer document structure remain future work.

## Task: FUTURE roadmap status alignment
Mode: Standard
Risk: Low
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: Revert the `FUTURE.md` and task-log hunks if any status labels are incorrect.
Change budget: [files 2] [functions: N/A] [interfaces: none] [state mutations: roadmap text only]

### Scope
- `FUTURE.md` — align phase and action-item statuses with the current implementation state
- `tasks/todo.md` — record this docs-only status pass

### Steps
- [x] Capture the current implemented status of the roadmap sections ✓
- [x] Update `FUTURE.md` for Phases 1-5 and the Immediate Action Items
- [x] Review the diff for scope and accuracy

### Review
- Completed: Updated `FUTURE.md` so Phases 2-5 now carry explicit current-status text and the Immediate Action Items now mark implemented work as Done, Mostly Done, or In Progress.
- Out-of-scope flagged: Existing uncommitted code changes in `README.md`, `risnet/scenarios.py`, and `tests/test_scenarios.py` were left untouched.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This pass only aligned roadmap status text; it did not resolve any underlying technical debt items.

## Task: Test suite reference cleanup
Mode: Standard
Risk: Low
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: Revert the `tasks/test-suite.md` and task-log hunks if the wording proves inaccurate.
Change budget: [files 2] [functions: N/A] [interfaces: none] [state mutations: docs text only]

### Scope
- `tasks/test-suite.md` — clarify suitability for the current Waveflow repo and align its authority wording with `AGENTS.md`
- `tasks/todo.md` — record this docs-only cleanup

### Steps
- [x] Review the current test-suite reference against the repo state
- [x] Update runner classification, execution guidance, and source-of-truth wording
- [x] Review the diff for scope and accuracy

### Review
- Completed: Clarified runner types, split execution guidance by baseline vs manual/direct execution, removed the missing `VALIDATION.md` dependency from the gap/tolerance wording, and restored authoritative wording so the document matches `AGENTS.md`.
- Out-of-scope flagged:
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This pass aligns wording and guidance only; it does not convert the remaining manual or weak tests into stronger automated coverage.

## Task: Fix stale RMS phase error expectation
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: Revert the targeted test and roadmap/test-suite doc hunks if the corrected expectation proves inconsistent with the current wrapped phase-error implementation.
Change budget: [files 4] [functions: `tests/test_fixes.py::test_rms_phase_error`, related roadmap/test-suite status text] [interfaces: none] [state mutations: docs and test assertions only]

### Scope
- `tests/test_fixes.py` — replace the stale RMS phase-error expectation with an enforced current wrapped-error assertion
- `tasks/test-suite.md` — remove stale-failure language if the targeted verification passes
- `FUTURE.md` — clear the stale test note from current status/action items if the fix lands
- `tasks/todo.md` — record this work

### Steps
- [x] Inspect the current test and confirm whether the stale note still reflects repo reality
- [x] Patch the test to assert the correct wrapped RMS expectation and update the related docs
- [x] Re-run targeted verification and review the diff for scope

### Review
- Completed: Confirmed `tests/test_fixes.py` TEST 3 had no assertion, replaced the stale range check with explicit wrapped-error and RMS assertions, and cleared the stale-failure notes from `tasks/test-suite.md` and `FUTURE.md`.
- Out-of-scope flagged:
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: Verification for this slice was targeted to `tests/test_fixes.py`; it did not re-run the broader suite.

## Task: Expand testall diagnostic coverage
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the additive `cli/test_suite.py` and `tasks/test-suite.md` hunks if the new diagnostic sections prove noisy or incompatible with the current CLI surface.
Change budget: [files 3] [functions: additive `cli/test_suite.py` sections for contract, channel, and scenario checks; test-suite reference updates] [interfaces: existing `waveflow ui testall` output only] [state mutations: temporary topology files during runtime only]

### Scope
- `cli/test_suite.py` — preserve the existing testall flow while adding connect contract, `LinkBudgetChannel`, and `ScenarioRunner` diagnostic sections
- `tasks/test-suite.md` — describe the broader `waveflow ui testall` diagnostic coverage accurately
- `tasks/todo.md` — record this work

### Steps
- [x] Inspect the current testall implementation and adjacent APIs for scenario and channel checks
- [x] Implement additive diagnostic sections and update the test-suite reference
- [x] Run focused verification and review the diff for scope

### Review
- Completed: Expanded `waveflow ui testall` with additive connect-contract, `LinkBudgetChannel`, and `ScenarioRunner` sections while preserving the existing physics-heavy diagnostic flow; updated `tasks/test-suite.md` to describe the broader built-in diagnostic coverage.
- Out-of-scope flagged:
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: `testall` is still a diagnostic suite and does not replace the broader pytest-based regression matrix.

## Task: Fix HOG Example Current API Usage
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: Revert the example rewrite, the smoke test addition, and the test-suite note for this task.
Change budget: [files 4] [functions: example helper wiring only] [interfaces: none] [state mutations: none]

### Scope
- `examples/hog_human_detection_example.py` — replace stale `NetworkManager`/`RISController.execute_sweep()` usage with the current `RISNetwork` + sweep loader APIs
- `tests/test_smoke.py` — add a smoke import/build check for the example
- `tasks/test-suite.md` — record the updated smoke coverage
- `tasks/todo.md` — track this task

### Steps
- [x] Inspect the current example breakages and adjacent sweep APIs
- [x] Rewrite the example onto the supported network and sweep entry points
- [x] Run focused verification and review diff scope

### Review
- Completed: Rewired the HOG example to the current `RISNetwork` and registered sweep loader APIs, then added a smoke check that loads the example by file path and validates demo-network construction.
- Out-of-scope flagged: The example still depends on optional OpenCV/camera availability at runtime; this task only fixed the stale API usage and import path.
- Assumptions invalidated: The first smoke-test implementation assumed `examples/` was an importable package; verification showed it is a plain directory, so the test now loads by file path.
- Known debt (acknowledged):
- Limitations: This task does not validate live camera execution or HOG detection quality.

## Task: Finish Phase 2 and Phase 3 Migration
Mode: Standard
Risk: High
Confidence: Stable
Operational risk: Broad / Partial
Rollback plan: Revert the additive helper-routing changes in `core/physics.py`, `controller/ris_phase/phase_quantization.py`, `utils/link_budget.py`, `utils/snr.py`, `risnet/channels/*`, `controller/ris_controller.py`, and the focused test/doc hunks for this task.
Change budget: [files 10] [functions: shared array-factor and quantization delegation, shared RIS link-budget helpers, channel re-exports, focused tests/docs] [interfaces: none] [state mutations: none]

### Scope
- `core/physics.py` — route the far-field array-factor implementation through `risnet.arrays`
- `controller/ris_phase/phase_quantization.py` — route quantization analyzer math through additive array quantization primitives
- `utils/link_budget.py` — make shared RIS link-budget config/evaluation the source of truth
- `utils/snr.py` — reuse the shared Phase 3 link-budget evaluation helper
- `risnet/channels/link_budget.py` and `risnet/channels/__init__.py` — keep the channel-facing adapter/re-export surface intact
- `controller/ris_controller.py` — reuse the shared RIS link-budget helper where applicable without changing public APIs
- `tests/test_link_budget_channel.py`, `FUTURE.md`, `tasks/test-suite.md`, `tasks/todo.md` — focused verification and status updates

### Steps
- [x] Inspect the remaining Phase 2/3 migration gaps and adjacent compatibility surfaces
- [x] Finish the Phase 2 helper routing through `risnet.arrays`
- [x] Finish the Phase 3 shared RIS link-budget consolidation and channel re-exports
- [x] Run focused verification and review diff scope

### Review
- Completed: Routed `Physics.compute_array_factor()` and quantization analyzer math through the additive array primitives, consolidated shared RIS link-budget helpers in `utils/link_budget.py`, re-exported them through `risnet.channels`, and updated focused tests plus roadmap/test-suite status text.
- Out-of-scope flagged: The controller-layer `PhaseEngine` decoupling called out in `FUTURE.md` item 6 remains unresolved and was not touched.
- Assumptions invalidated: Importing shared channel helpers through the `risnet` package created a circular import during test collection; the final implementation keeps `utils/link_budget.py` as the low-level source of truth and uses `risnet.channels` as a compatibility re-export layer.
- Known debt (acknowledged):
- Limitations: Verification for this slice was focused to `tests/test_array_primitives.py`, `tests/test_array_quantization.py`, `tests/test_link_budget_channel.py`, and `tests/test_smoke.py`; it did not rerun the full repository suite.

## Task: Introduce Core PhaseEngine Abstraction
Mode: Standard
Risk: High
Confidence: Guarded
Operational risk: Broad / Partial
Rollback plan: Revert the additive phase-engine abstraction and adapter files plus the `core/network.py`, `core/nodes.py`, and roadmap/task-log hunks for this task.
Change budget: [files 7] [functions: core phase-engine registry, controller adapter registration, core node/network phase-engine call sites, roadmap/task record] [interfaces: additive `core.phase_engine` only] [state mutations: none]

### Scope
- `core/phase_engine.py` — add a core-owned phase-engine abstraction and registry
- `controller/ris_phase/core_adapter.py` and `controller/ris_phase/__init__.py` — register the existing controller-backed implementation
- `core/network.py` — replace direct controller tapering import with the core phase-engine service
- `core/nodes.py` — replace direct controller phase-computation and phase-manager imports with the core phase-engine service
- `FUTURE.md` and `tasks/todo.md` — record the roadmap/task status for item 6

### Steps
- [x] Inspect the remaining core-to-controller phase-engine dependency points
- [x] Add the core abstraction and controller compatibility adapter
- [x] Redirect the current core call sites through the abstraction without changing public behavior
- [x] Run focused verification and review diff scope

### Review
- Completed: Added `core.phase_engine`, registered the existing controller-backed implementation through `controller/ris_phase/core_adapter.py`, and removed the direct controller phase imports from `core/network.py` and `core/nodes.py`.
- Out-of-scope flagged: The unrelated stale smoke test reference to `examples/hog_human_detection_example.py` is currently broken because that file is absent from the worktree; this task did not modify it.
- Assumptions invalidated: None.
- Known debt (acknowledged): The controller-backed phase implementation remains the default runtime provider behind the core registry, so the broader controller/core split is not fully complete yet.
- Limitations: Focused verification passed for `tests/test_connect_characterization.py`, `tests/test_hybrid_mode.py`, and `tests/test_side_lobes.py`, and compile checks passed. The broader smoke subset was blocked by the pre-existing missing example file.

## Task: Document Canonical CLI Relationship
Mode: Standard
Risk: Low
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: Revert the documentation-only hunks in `FUTURE.md`, `README.md`, `TUTORIAL.md`, and `tasks/todo.md`.
Change budget: [files 4] [functions: none] [interfaces: documentation only] [state mutations: none]

### Scope
- `FUTURE.md` — resolve the duplicate-CLI ambiguity by documenting the current canonical shell
- `README.md` — state which CLI surface is primary
- `TUTORIAL.md` — state which CLI surface is primary
- `tasks/todo.md` — record this docs-only pass

### Steps
- [x] Inspect the actual CLI entry wiring and shell usage points
- [x] Update the roadmap and user docs to name the canonical shell explicitly
- [x] Review the diff for scope and consistency

### Review
- Completed: Documented `cli/main_shell.py` as the canonical full interactive shell used by `python -m risnet`, the `waveflow` console entry point, and `waveflow ui shell`, while clarifying that `risnet/cli.py` remains a legacy alternate shell and `waveflow/cli.py` is a compatibility wrapper.
- Out-of-scope flagged: This pass did not consolidate or delete any CLI implementations.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The duplicate shell code still exists; this only removes ambiguity about which path is primary.

## Task: Begin Phase 4 Logging Migration
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Broad / Trivial
Rollback plan: Revert the logging-only hunks in `risnet/__init__.py`, `core/network.py`, `controller/adaptive_controller.py`, `controller/pathfinding/registry.py`, `controller/ris_phase/phase_manager.py`, `FUTURE.md`, and `tasks/todo.md`.
Change budget: [files 7] [functions: start/stop, verbose reporting helpers, node listing, adaptive summary, pathfinding registration, phase report] [interfaces: logging side effects only] [state mutations: none]

### Scope
- `risnet/__init__.py` — replace library `print()` status output with logger calls
- `core/network.py` — replace node listing `print()` with logger calls
- `controller/adaptive_controller.py` — replace summary `print()` with logger calls
- `controller/pathfinding/registry.py` — replace registration `print()` with logger calls
- `controller/ris_phase/phase_manager.py` — replace phase report `print()` with logger calls
- `FUTURE.md` — mark the logging migration as in progress
- `tasks/todo.md` — record this migration slice

### Steps
- [x] Discover the existing logging pattern in adjacent controller modules
- [x] Replace direct `print()` usage in the selected public/library modules
- [x] Verify imports, focused tests, and compile checks

### Review
- Completed: Replaced direct `print()` reporting with module loggers in the public `RISnet` facade, `RISNetwork` node listing, adaptive-controller summary output, pathfinding auto-registration, and RIS phase reporting. Updated `FUTURE.md` to reflect that the Phase 4 logging migration is now in progress rather than untouched.
- Out-of-scope flagged: Print-heavy diagnostics remain in CLI surfaces, tools, and several algorithm/helper modules.
- Assumptions invalidated: None.
- Known debt (acknowledged): This slice does not finish the full repo-wide non-CLI logging migration; several beam-sweeping and utility modules still emit direct stdout diagnostics.
- Limitations: Focused verification passed with `python3 -m compileall risnet core controller` and `.venv/bin/pytest tests/test_smoke.py tests/test_connect_characterization.py tests/test_scenarios.py -q`.

## Task: Continue Phase 4 Logging Migration for Non-Vision Sweep Algorithms
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the logging-only hunks in `controller/beamsweeping/algorithms/ml_guided_sweep.py`, `controller/beamsweeping/algorithms/prime_sweep.py`, and `tasks/todo.md`.
Change budget: [files 3] [functions: ML sweep diagnostics, PRIME estimator diagnostics] [interfaces: logging side effects only] [state mutations: none]

### Scope
- `controller/beamsweeping/algorithms/ml_guided_sweep.py` — replace diagnostic `print()` output with logger calls
- `controller/beamsweeping/algorithms/prime_sweep.py` — replace debug estimator `print()` output with logger calls
- `tasks/todo.md` — record this follow-up slice

### Steps
- [x] Inspect the remaining non-vision sweep diagnostics
- [x] Replace direct stdout diagnostics with module loggers
- [x] Verify targeted compilation and focused smoke coverage

### Review
- Completed: Replaced direct stdout diagnostics in the non-vision `MLGuidedSweep` and `PRIME` algorithms with module loggers. The ML-guided codebook/result summaries now log at info level, and the PRIME estimator dump is reduced to debug-level logging.
- Out-of-scope flagged: Vision/camera-based sweep modules still emit direct stdout diagnostics and remain for a later migration slice.
- Assumptions invalidated: None.
- Known debt (acknowledged): The Phase 4 logging migration still has a large remaining surface in camera/vision helpers and other utility modules.
- Limitations: Verification passed with `python3 -m compileall controller/beamsweeping/algorithms/ml_guided_sweep.py controller/beamsweeping/algorithms/prime_sweep.py` and `.venv/bin/pytest tests/test_smoke.py -q`.

## Task: Continue Phase 4 Logging Migration for ArUco Utilities
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the logging-only hunks in `utils/aruco_utils.py`, `controller/beamsweeping/algorithms/aruco_utils.py`, and `tasks/todo.md`.
Change budget: [files 3] [functions: marker save/grid diagnostics and demo output] [interfaces: logging side effects only] [state mutations: none]

### Scope
- `utils/aruco_utils.py` — replace helper/demo `print()` output with logger calls
- `controller/beamsweeping/algorithms/aruco_utils.py` — apply the same logger conversion to the duplicate helper module
- `tasks/todo.md` — record this migration slice

### Steps
- [x] Inspect both ArUco utility copies
- [x] Replace direct stdout diagnostics with module loggers in both copies
- [x] Verify targeted compilation and smoke coverage

### Review
- Completed: Replaced direct stdout diagnostics in both ArUco utility copies with module loggers, keeping the duplicated helper behavior aligned while the repository still carries both modules.
- Out-of-scope flagged: The broader camera viewer and OpenCV sweep modules still emit direct stdout diagnostics.
- Assumptions invalidated: None.
- Known debt (acknowledged): The duplicated ArUco utility modules still exist; this slice only kept their logging behavior consistent.
- Limitations: Verification passed with `python3 -m compileall utils/aruco_utils.py controller/beamsweeping/algorithms/aruco_utils.py` and `.venv/bin/pytest tests/test_smoke.py -q`.

## Task: Continue Phase 4 Logging Migration for OpenCV Support Modules
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the logging-only hunks in `controller/beamsweeping/algorithms/opencv_mock.py`, `controller/beamsweeping/algorithms/opencv_viewer.py`, and `tasks/todo.md`.
Change budget: [files 3] [functions: mock-camera diagnostics, viewer entrypoint diagnostics] [interfaces: logging side effects only] [state mutations: none]

### Scope
- `controller/beamsweeping/algorithms/opencv_mock.py` — replace support/demo `print()` output with logger calls
- `controller/beamsweeping/algorithms/opencv_viewer.py` — replace support/viewer `print()` output with logger calls
- `tasks/todo.md` — record this migration slice

### Steps
- [x] Inspect the remaining OpenCV support-module diagnostics
- [x] Replace direct stdout diagnostics with module loggers
- [x] Verify targeted compilation and smoke coverage

### Review
- Completed: Replaced direct stdout diagnostics in the OpenCV mock-camera and viewer support modules with module loggers, keeping their demo/entrypoint behavior intact while removing non-CLI library prints.
- Out-of-scope flagged: The main `opencv_sweep.py` and `hog_sweep.py` algorithms still emit direct stdout diagnostics.
- Assumptions invalidated: None.
- Known debt (acknowledged): The OpenCV/HOG sweep algorithms remain the major unfinished logging surface in the vision stack.
- Limitations: Verification passed with `python3 -m compileall controller/beamsweeping/algorithms/opencv_mock.py controller/beamsweeping/algorithms/opencv_viewer.py` and `.venv/bin/pytest tests/test_smoke.py -q`.

## Task: Continue Phase 4 Logging Migration for OpenCV Vision Sweep
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the logging-only hunks in `controller/beamsweeping/algorithms/opencv_sweep.py` and `tasks/todo.md`.
Change budget: [files 2] [functions: OpenCV sweep diagnostics and validation display logging] [interfaces: logging side effects only] [state mutations: none]

### Scope
- `controller/beamsweeping/algorithms/opencv_sweep.py` — replace direct stdout diagnostics with module loggers
- `tasks/todo.md` — record this migration slice

### Steps
- [x] Inspect all remaining `print()` call sites in `opencv_sweep.py`
- [x] Replace diagnostic stdout output with module loggers
- [x] Verify targeted compilation and smoke coverage

### Review
- Completed: Replaced the OpenCV vision sweep’s diagnostic stdout output with module loggers, including node/bootstrap notices, coordinate-transform tracing, deflection-angle tracing, diagnostics, and result summaries, without changing the sweep result structure.
- Out-of-scope flagged: `hog_sweep.py` remains the largest unfinished non-CLI logging surface.
- Assumptions invalidated: None.
- Known debt (acknowledged): The vision stack still has a large amount of direct stdout output in `hog_sweep.py`.
- Limitations: Verification passed with `python3 -m compileall controller/beamsweeping/algorithms/opencv_sweep.py` and `.venv/bin/pytest tests/test_smoke.py -q`.
