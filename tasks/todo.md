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
