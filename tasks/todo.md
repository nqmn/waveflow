## Task: Replace `waveflow ui links` Wrapper With Native Rich Renderer
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the native `links` renderer changes, the focused smoke assertion updates, and the task/test-suite documentation edits for this task.
Change budget: [files 4] [functions: `risnet.terminal_cli.links_cmd`, `risnet.terminal_cli._render_links_view`, focused smoke assertions] [interfaces: `waveflow ui links` output only] [state mutations: none]

### Scope
- `risnet/terminal_cli.py` — rebuild `waveflow ui links` as a native Rich renderer for link listings while keeping `links plot ...` on the existing plot path.
- `tests/test_smoke.py` — assert the richer native `links` content.
- `tasks/test-suite.md` — record the restored `links` output coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Audit the full legacy `links` listing contract
- [x] Rebuild `ui links` as a native Rich renderer with legacy-parity detail
- [x] Run focused verification and review scope

### Review
- Completed: Rebuilt `waveflow ui links` as a native Rich renderer for active-link listings, using per-link detail panels so full link names and metrics remain visible instead of being truncated in a compact table. Kept `links plot ...` on the existing plot path and updated focused smoke assertions plus the test-suite inventory accordingly.
- Out-of-scope flagged: `links plot ...` still uses the legacy plotting workflow because this task only replaced the link-listing output contract.
- Assumptions invalidated: The initial compact Rich table layout was not sufficient to preserve full link names; the native renderer now uses vertical detail panels to maintain full parity.
- Known debt (acknowledged):
- Limitations: The native `links` renderer now preserves full content but uses a Rich panel-per-link layout rather than the original legacy plain-text block layout.

## Task: Restore Full Legacy `status` Detail in Native Rich Output
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the native `status` renderer changes, the focused smoke assertion updates, and the task/test-suite documentation edits for this task.
Change budget: [files 4] [functions: `risnet.terminal_cli.status`, `risnet.terminal_cli._render_status_view`, focused smoke assertions] [interfaces: `waveflow ui status` output only] [state mutations: none]

### Scope
- `risnet/terminal_cli.py` — rebuild `waveflow ui status` as a native Rich renderer with legacy-parity node, distance, and active-link detail.
- `tests/test_smoke.py` — assert the richer native `status` content.
- `tasks/test-suite.md` — record the restored `status` output coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Audit the full legacy `status` content contract
- [x] Rebuild `ui status` as a native Rich renderer with legacy-parity detail
- [x] Run focused verification and review scope

### Review
- Completed: Rebuilt `waveflow ui status` as a native Rich renderer with legacy-parity node details, pairwise distances, and active-link metrics instead of the previous shortened summary. Updated focused smoke assertions to cover both empty-state and populated rich status output, and refreshed the test-suite inventory to reflect the fuller status contract.
- Out-of-scope flagged: Commands deeper than top-level `waveflow ui status` (for example nested node shells) still follow their existing output contracts.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The section ordering and wording are now Rich-native rather than a byte-for-byte copy of the legacy text, but the underlying information content is preserved.

## Task: Preserve Full Legacy `list` Output in `waveflow ui`
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the `list` command routing change, its smoke assertion update, and the task/test-suite documentation edits for this task.
Change budget: [files 4] [functions: `risnet.terminal_cli.list_nodes`, focused smoke assertion] [interfaces: `waveflow ui list` output only] [state mutations: none]

### Scope
- `risnet/terminal_cli.py` — route `waveflow ui list` through the Rich-wrapped legacy output path instead of the shortened native network renderer.
- `tests/test_smoke.py` — assert the legacy topology content is preserved in the Rich output.
- `tasks/test-suite.md` — record the preserved `list` output coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Audit the full legacy `list` content contract
- [x] Rebuild `ui list` as a native Rich renderer with legacy-parity detail
- [x] Style the ASCII map and legend through Rich while preserving the legacy layout
- [x] Run focused verification and review scope

### Review
- Completed: Rebuilt `waveflow ui list` as a native Rich renderer that preserves the full legacy topology ASCII view and node-coordinate detail without wrapping legacy stdout, then styled the ASCII map and legend through Rich while keeping the underlying layout intact. Updated smoke coverage to assert the preserved topology, legend, and coordinate content in the native Rich output.
- Out-of-scope flagged: `waveflow ui status` still uses the native summarized Rich renderer; this task only restores full native-Rich parity for `list`, which you marked as critical.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The topology map remains an ASCII representation rendered inside Rich because the legacy contract itself is ASCII-based; only the surrounding structure is Rich-native.

## Task: Standardize Top-Level `waveflow ui` Output Through Rich
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Broad / Trivial
Rollback plan: Revert the legacy-output capture/render bridge in `risnet/terminal_cli.py`, the focused smoke assertion updates, and the task/test-suite documentation changes for this task.
Change budget: [files 4] [functions: `risnet.terminal_cli` legacy wrapper bridge and shell fallback rendering, focused smoke assertions] [interfaces: top-level `waveflow ui` output styling only] [state mutations: none beyond existing command side effects]

### Scope
- `risnet/terminal_cli.py` — route legacy-backed top-level `waveflow ui` commands and shell fallback output through a Rich rendering bridge instead of raw `print()` passthrough.
- `tests/test_smoke.py` — assert Rich-panelized output for representative legacy-backed wrappers.
- `tasks/test-suite.md` — record the standardized wrapper output coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add a Rich bridge for captured legacy-backed command output
- [x] Apply the same bridge to native-shell fallback execution
- [x] Run focused verification and review scope

### Review
- Completed: Added a Rich bridge that captures stdout from legacy-backed top-level `waveflow ui` commands and re-renders it inside consistent Rich panels, and applied the same rendering path to native-shell fallback execution. Updated focused smoke assertions for representative wrapper commands and refreshed the test-suite inventory to reflect the richer standardized output.
- Out-of-scope flagged: This task standardizes top-level `waveflow ui` output only; deeper nested node subshells launched from legacy handlers remain on their original interactive text path.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: Legacy-backed commands still preserve their original textual content inside the Rich panels, so their internal wording/section ordering is not yet normalized to the same table structure used by fully native commands such as `status`, `connect`, and `sweep`.

## Task: Validate `connect` Output Against Coordinate Math
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the connect metadata normalization in `core/network.py`, the new characterization test, and the task/test-suite updates for this task.
Change budget: [files 4] [functions: `core.network._collect_connect_phase_data`, focused connect characterization test] [interfaces: `RISNetwork.connect()` geometry metadata only] [state mutations: none beyond existing connect side effects]

### Scope
- `core/network.py` — normalize phase metadata keys so `connect()` exposes geometry fields consistently regardless of the active phase engine.
- `tests/test_connect_characterization.py` — add a focused math cross-check for non-collinear connect geometry output.
- `tasks/test-suite.md` — record the new geometry-validation coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add a coordinate-math characterization test for non-collinear connect geometry
- [x] Normalize connect metadata for hybrid and steering phase-engine key variants
- [x] Run focused verification and review scope

### Review
- Completed: Added a non-collinear coordinate-math characterization test for `RISNetwork.connect()` and normalized `_collect_connect_phase_data()` so hybrid-phase metadata keys (`azimuth_in_deg`, `azimuth_out_deg`, `azimuth_deflection_deg`) are exposed through the canonical connect result fields. This closes the mismatch where native connect output showed zero azimuths despite valid geometry.
- Out-of-scope flagged: The native terminal renderer itself was not further changed in this task; it now benefits automatically from the corrected structured connect metadata.
- Assumptions invalidated: The active hybrid phase engine does not emit `incident_azimuth_deg` / `reflected_azimuth_deg` keys directly; it uses `azimuth_in_deg` / `azimuth_out_deg`, which previously leaked through as zero-valued defaults in the connect result.
- Known debt (acknowledged):
- Limitations: This test validates 2D azimuth/deflection geometry from node coordinates; it does not add a separate 3D elevation cross-check.

## Task: Add Rich Diagnostic Panels to Native `waveflow ui connect`
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the native connect renderer changes, the focused smoke assertions, and the task/test-suite updates for this task.
Change budget: [files 4] [functions: `risnet.terminal_cli._render_connect_result`, focused smoke tests] [interfaces: native `waveflow ui connect` output only] [state mutations: none beyond existing connect side effects]

### Scope
- `risnet/terminal_cli.py` — enrich native `ui connect` output with Rich diagnostic panels built from node state and connect result fields.
- `tests/test_smoke.py` — verify the new diagnostic panels appear on direct and shell-native connect paths.
- `tasks/test-suite.md` — record the richer native connect diagnostics coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Build Rich diagnostic panels from existing connect result data
- [x] Extend smoke coverage for native connect rendering
- [x] Run focused verification and review scope

### Review
- Completed: Replaced the terse native `ui connect` summary-only output with Rich diagnostic panels for connection context, geometry/FOV diagnostics, and RIS steering recommendation, while keeping the modern metrics table. Added focused smoke assertions for direct and shell-native connect paths and updated the test-suite inventory to reflect the richer native diagnostics.
- Out-of-scope flagged: Sweep-mode `connect --sweep` still uses the existing modern sweep summary/table output rather than a matching multi-panel diagnostic layout.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The new panels derive from current node state and connect result fields, so legacy debug details that were never persisted as structured data still cannot be reproduced exactly.

## Task: Lift Full Legacy `connect` Grammar Into Native `waveflow ui connect`
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Broad / Trivial
Rollback plan: Revert the native `ui connect` routing/rendering changes, the focused smoke coverage, and the task/test-suite updates for this task.
Change budget: [files 4] [functions: `risnet.terminal_cli.connect`, focused smoke tests] [interfaces: `waveflow ui connect` grammar and output only] [state mutations: in-memory connect/sweep state within the UI shell]

### Scope
- `risnet/terminal_cli.py` — make native `ui connect` accept the full practical legacy grammar while rendering modern output for both single-connect and `--sweep` modes.
- `tests/test_smoke.py` — verify native UI connect accepts lifted legacy grammar directly and inside the native shell.
- `tasks/test-suite.md` — record the expanded native `connect` coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Reuse `ConnectionHandler` parsing/execution for native `ui connect`
- [x] Replace legacy narrated output with native modern rendering for single and sweep connect paths
- [x] Run focused verification and review scope

### Review
- Completed: Lifted native `waveflow ui connect` onto the legacy `ConnectionHandler` grammar so it now accepts no-arg auto-detect, positional beam-angle/seed syntax, and unified `--sweep` forms while rendering modern summary tables instead of legacy narrated output. Added focused smoke coverage for direct and shell-native legacy-grammar usage and updated the test-suite inventory to reflect the broader native `connect` contract.
- Out-of-scope flagged: Detailed Rich-native re-rendering of every legacy `connect` diagnostic section was not added; this task focused on grammar compatibility plus modern summary output for single-connect and sweep results.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: Some rare legacy-only `connect` diagnostics still collapse into concise failure messages in the native UI instead of reproducing the full narrated debug trace.

## Task: Promote Remaining Legacy Shell Commands into `waveflow ui`
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Broad / Trivial
Rollback plan: Revert the additive explicit subcommand wrappers in `risnet/terminal_cli.py`, the focused smoke coverage, and the documentation/task updates for this task.
Change budget: [files 4] [functions: explicit `waveflow ui` wrappers for `env`, `ap`, `ris`, `ue`, `signal`, `stream`; focused smoke tests] [interfaces: additive `waveflow ui` command surface only] [state mutations: existing in-memory network and environment mutations performed by the legacy command handlers]

### Scope
- `risnet/terminal_cli.py` — expose the remaining practical legacy shell verbs as explicit `waveflow ui` subcommands that share native-shell state and delegate to the established implementations.
- `tests/test_smoke.py` — add focused smoke coverage for the new command wrappers.
- `tasks/test-suite.md` — record the expanded command-surface coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Audit remaining legacy-only shell verbs
- [x] Add explicit `waveflow ui` wrappers for the remaining command surface
- [x] Add focused smoke coverage and run verification

### Review
- Completed: Added explicit `waveflow ui` wrappers for `env`, `ap`, `ris`, `ue`, `signal`, and `stream`, all sharing native-shell state and delegating to the established legacy implementations. Expanded smoke coverage to verify direct wrapper usage from the `ui` surface alongside the native interactive shell behavior, and updated the test-suite inventory for the broader command surface.
- Out-of-scope flagged: Node-name direct subshell entry (`AP1`, `R1`, `UE1`) and the deeper nested node-shell command model remain legacy-only; this task focused on the top-level practical `waveflow ui` command surface.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: Several explicit UI wrappers still render legacy text output rather than Rich-native layouts, because they intentionally preserve the existing handler behavior as the single implementation source.

## Task: Align Native `waveflow ui connect` With Legacy Semantics
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the native `ui connect` parsing/output changes, the focused shell smoke test, and the task/test-suite updates for this task.
Change budget: [files 4] [functions: `risnet.terminal_cli.connect`, focused smoke tests] [interfaces: `waveflow ui connect` argument handling and output only] [state mutations: in-memory connect/sweep state within the UI shell]

### Scope
- `risnet/terminal_cli.py` — make native `ui connect` accept legacy-style arguments, including zero-argument auto-detection, and render legacy-style output without delegating to the legacy shell command.
- `tests/test_smoke.py` — verify native UI shell `connect` works without explicit node arguments and does not emit Typer missing-argument errors.
- `tasks/test-suite.md` — record the native-shell `connect` coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Rework native `ui connect` parsing/execution to match legacy behavior
- [x] Add focused shell smoke coverage for no-arg `connect`
- [x] Run focused verification and review scope

### Review
- Completed: Reworked native `ui connect` to use the legacy connect parser/execution flow inside `terminal_cli.py`, including zero-argument AP/RIS/UE auto-detection, legacy-style detailed connect output, sweep-mode support through the same native command, and compatibility shims for the existing `--beam` and `--seed` option forms.
- Out-of-scope flagged: Existing uncommitted native-shell and wrapper work already present in `tasks/todo.md`, `tasks/test-suite.md`, and `tests/test_smoke.py` remains outside this fix beyond the exact connect-related lines required here.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations:

## Task: Implement Native `waveflow ui shell`
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the native-shell adapter changes in `risnet/terminal_cli.py`, the focused smoke coverage, and the task/test-suite updates for this task.
Change budget: [files 4] [functions: `risnet.terminal_cli.shell`, context-aware terminal command helpers, focused smoke tests] [interfaces: `waveflow ui` and `waveflow ui shell` interactive behavior only] [state mutations: in-memory network state within the interactive shell]

### Scope
- `risnet/terminal_cli.py` — replace the legacy `cmdloop()` entry path with a native interactive REPL that reuses the Typer/Rich command surface and falls back to the legacy handler for unsupported commands.
- `tests/test_smoke.py` — verify the native shell opens, keeps state across commands, and preserves legacy passthrough behavior on the same shell session.
- `tasks/test-suite.md` — record the native-shell smoke coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Inspect the current terminal UI and shell boundary
- [x] Add a native interactive REPL over the existing Typer/Rich command surface
- [x] Preserve fallback to legacy commands on the same shell state
- [x] Run focused verification and review diff scope

### Review
- Completed: Replaced the `waveflow ui shell` entry path with a native interactive REPL that keeps in-memory network state across modern Typer/Rich commands, while still delegating unsupported commands through the established legacy handler on the same session state. Added focused smoke coverage for bare `waveflow ui` entry and for stateful shell-plus-legacy passthrough behavior, and updated the test-suite inventory accordingly.
- Out-of-scope flagged: Full migration of every legacy interactive command into first-class native Typer/Rich commands remains future work; this task only changed the shell boundary and shared state handling for the existing command surface.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: Unsupported commands inside the native shell still render through the legacy command handler output path rather than native Rich layouts.

## Task: Support `waveflow ui` command surface
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the `risnet/terminal_cli.py` UI command additions, the focused smoke tests, and the `tasks/test-suite.md` update for this task.
Change budget: [files 4] [functions: `risnet.terminal_cli.add`, `risnet.terminal_cli.links`, `risnet.terminal_cli.plot`, focused smoke tests] [interfaces: extend the direct `waveflow ui` CLI surface to cover `add random`, `links`, and `plot`] [state mutations: in-memory network additions/results loading only during command execution]

### Scope
- `risnet/terminal_cli.py` — expose the requested direct `ui` commands, adding `random` support to `add` and first-class `links`/`plot` wrappers where missing.
- `tests/test_smoke.py` — add focused smoke coverage for the requested `ui` command surface.
- `tasks/test-suite.md` — record the expanded CLI smoke coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Record task metadata and scope
- [x] Ensure the requested direct `ui` commands are exposed
- [x] Add focused smoke coverage and update test map
- [x] Run focused verification and review diff scope

### Review
- Completed: Extended the Typer/Rich `ui add` command to accept `random`, AP/RIS/UE count arguments, `--distance min-max`, and `--no-ue`; added first-class `ui links` and `ui plot` wrappers over the established legacy handlers; and expanded smoke coverage for `status`, `list`, `add random`, `connect`, `save`, `load`, `links`, `clear links`, and `plot`.
- Out-of-scope flagged: Existing uncommitted task-file and terminal CLI changes from earlier work, including separate bare-`ui` default-shell changes, remain in the worktree and were not modified beyond the lines required for this task.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations:

## Task: Close Phase 5 Shared Scenario Adoption
Mode: Standard
Risk: Medium
Confidence: Guarded
Operational risk: Broad / Partial
Rollback plan: Revert the shared scenario service extraction, API/CLI adoption changes, scenario validation changes, and the focused test/doc updates for this task.
Change budget: [files 7] [functions: risnet.scenarios shared execution services and validation, app.api connect/sweep routing, risnet.terminal_cli connect routing, focused scenario/smoke tests, FUTURE/test-suite/todo docs] [interfaces: additive scenario service exports only; no public API removals] [state mutations: none beyond existing connect/sweep side effects]

### Scope
- `risnet/scenarios.py` — add shared scenario execution services and stronger request validation while preserving the current runner facade.
- `risnet/__init__.py` — export any additive shared scenario service types used by clients.
- `app/api/bp.py` — route `connect` and `sweep` through the shared scenario service layer.
- `risnet/terminal_cli.py` — route at least one non-interactive CLI execution path through the same shared service layer.
- `tests/test_scenarios.py` and `tests/test_smoke.py` — cover shared service routing, validation failures, and golden example scenario loading.
- `tasks/test-suite.md` and `FUTURE.md` — record the new coverage and close Phase 5 status if completed.

### Steps
- [x] Extract shared scenario execution service
- [x] Route API and one CLI path through the shared service
- [x] Strengthen scenario validation and golden example coverage
- [x] Run focused verification and reassess whether Phase 5 can be closed

### Review
- Completed: Added `ScenarioExecutionService`, routed Flask/API `connect` and `sweep` plus the terminal `ui connect` path through the shared service layer, strengthened scenario request validation, restored environment obstacle loading for example topologies, expanded scenario/smoke coverage, and marked Phase 5 complete in `FUTURE.md`.
- Out-of-scope flagged: Full CLI-wide adoption of the shared service layer and richer runtime-oriented scenario schemas remain later-phase work, not Phase 5 blockers.
- Assumptions invalidated: The obstacle example topology uses a legacy `obstacles` block rather than `walls`, and `NetworkIO.load()` previously ignored environment restoration; this task closed that compatibility gap.
- Known debt (acknowledged):
- Limitations: Non-interactive CLI adoption is intentionally limited to the terminal `connect` path in this phase; sweep live-progress execution still uses the direct algorithm path.

## Task: Make `waveflow ui` Default to Interactive Shell
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the bare-`ui` routing change, smoke test addition, and documentation inventory updates.
Change budget: [files 4] [functions: risnet.terminal_cli.run, tests/test_smoke.py, tasks/test-suite.md, tasks/todo.md] [interfaces: `waveflow ui` / `python -m risnet ui` no-args behavior only] [state mutations: none beyond existing interactive shell behavior]

### Scope
- `risnet/terminal_cli.py` — route bare `waveflow ui` to the interactive shell.
- `tests/test_smoke.py` — add subprocess smoke coverage for the new bare-`ui` interactive entry behavior.
- `tasks/test-suite.md` — record the new CLI smoke coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Change bare `waveflow ui` behavior to launch interactive shell
- [x] Add focused smoke coverage for entering and exiting the shell
- [x] Run focused verification and review scope

### Review
- Completed: Bare `waveflow ui` now routes to the interactive shell by default when no subcommand is supplied, and smoke coverage verifies that the shell accepts commands over stdin and exits cleanly.
- Out-of-scope flagged: `waveflow ui add random` remains a stateless one-shot command; this task only changes the no-args entry path into the interactive shell.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The interactive shell opened by bare `waveflow ui` is still the established legacy shell surface, now made easier to reach from the `ui` namespace.

## Task: Expand tutorial coverage for sweep, ML, localization, and vision
Mode: Standard
Risk: Low
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: Revert the documentation-only edits in `TUTORIAL.md` and this task entry.
Change budget: [files 2] [functions: none] [interfaces: documentation only] [state mutations: none]

### Scope
- `TUTORIAL.md` — add explicit tutorial coverage for localization-oriented sweep workflows, vision-assisted usage, and richer terminal UX guidance.
- `tasks/todo.md` — record this documentation task.

### Steps
- [x] Inspect current tutorial gaps against requested coverage
- [x] Add tutorial sections for localization, vision, and terminal sweep UX
- [x] Review diff for scope compliance

### Review
- Completed: Expanded `TUTORIAL.md` with localization-oriented sweep guidance, vision-assisted workflow coverage, and a richer terminal UX section aligned with the future roadmap.
- Out-of-scope flagged: Existing tutorial examples remain example-driven for vision; this task did not add or validate new runtime commands.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: Verification was limited to diff review because this task only changed documentation.

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

## Task: Continue Phase 4 Logging Migration for HOG Vision Sweep
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the logging-only hunks in `controller/beamsweeping/algorithms/hog_sweep.py` and `tasks/todo.md`.
Change budget: [files 2] [functions: HOG sweep diagnostics, adaptive-window logs, snapshot/result logging] [interfaces: logging side effects only] [state mutations: none]

### Scope
- `controller/beamsweeping/algorithms/hog_sweep.py` — replace direct stdout diagnostics with module loggers
- `tasks/todo.md` — record this migration slice

### Steps
- [x] Inspect all remaining `print()` call sites in `hog_sweep.py`
- [x] Replace diagnostic stdout output with module loggers
- [x] Verify targeted compilation and smoke coverage

### Review
- Completed: Replaced the HOG vision sweep’s direct stdout diagnostics with module loggers, including camera bootstrap notices, adaptive-window tracing, coordinate-transform details, snapshot summaries, and final result reporting, without changing its sweep result shape.
- Out-of-scope flagged: `FUTURE.md` has unrelated local edits and remains untouched in this pass.
- Assumptions invalidated: None.
- Known debt (acknowledged): There are still non-CLI `print()` calls elsewhere in miscellaneous utilities and demos, but the main vision sweep algorithms are now migrated.
- Limitations: Verification passed with `python3 -m compileall controller/beamsweeping/algorithms/hog_sweep.py` and `.venv/bin/pytest tests/test_smoke.py -q`.

## Task: Complete Phase 4 Exit Gate
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Broad / Trivial
Rollback plan: Revert the Phase 4 closeout hunks in `tests/test_connect_characterization.py`, `tasks/test-suite.md`, `FUTURE.md`, and `tasks/todo.md`.
Change budget: [files 4] [functions: extracted connect helper tests and roadmap closeout only] [interfaces: test coverage and documentation only] [state mutations: none]

### Scope
- `tests/test_connect_characterization.py` — add focused regression coverage for extracted `RISNetwork.connect()` helpers
- `tasks/test-suite.md` — record the expanded connect-helper coverage
- `FUTURE.md` — mark Phase 4 complete where the verified exit gate is now satisfied
- `tasks/todo.md` — record the Phase 4 closeout

### Steps
- [x] Identify which extracted `connect()` helpers still lacked focused tests
- [x] Add helper-level regression coverage without changing the public facade
- [x] Verify focused connect/smoke coverage and compile checks
- [x] Mark Phase 4 complete in the roadmap once the exit gate passed

### Review
- Completed: Added focused regression coverage for extracted `RISNetwork.connect()` helpers including phase computation, phase payload persistence, result assembly, metadata persistence, messaging override resolution, active-link persistence, last-result persistence, link-budget preparation, and SNR evaluation. Updated `tasks/test-suite.md` and `FUTURE.md` to reflect that the Phase 4 exit gate is now satisfied.
- Out-of-scope flagged: Utility/demo scripts still contain some direct `print()` calls, but the core/library and main sweep algorithm surfaces required for Phase 4 are migrated to logging.
- Assumptions invalidated: One helper test initially assumed a nonexistent `UE.link_metrics` attribute; it was corrected to assert against the actual `UE.get_link_metadata()` contract.
- Known debt (acknowledged): Broader architecture cleanup beyond the Phase 4 exit gate remains for later phases, especially wider Phase 5 client adoption and residual utility-script cleanup.
- Limitations: Verification passed with `python3 -m compileall core controller risnet tests` and `.venv/bin/pytest tests/test_connect_characterization.py tests/test_smoke.py -q`.

## Task: Add Early Sweep UX to Terminal UI
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the UX-only hunks in `risnet/terminal_cli.py`, `tests/test_smoke.py`, `tasks/test-suite.md`, and `tasks/todo.md`.
Change budget: [files 4] [functions: terminal sweep rendering, smoke coverage] [interfaces: `waveflow ui sweep` output and options only] [state mutations: none]

### Scope
- `risnet/terminal_cli.py` — add richer sweep summary rendering and non-invasive `--format`/`--topk` options
- `tests/test_smoke.py` — add smoke coverage for the terminal sweep output
- `tasks/test-suite.md` — record the new smoke coverage
- `tasks/todo.md` — record this UX slice

### Steps
- [x] Inspect existing sweep result shapes across current algorithms
- [x] Add a terminal-only sweep result normalizer and renderer
- [x] Add smoke coverage for the Rich sweep output
- [x] Verify compile and focused smoke coverage

### Review
- Completed: Added presentation-only sweep UX in the Typer/Rich terminal surface with a normalized summary table, top-N measurement table, and `--format`/`--topk` options for `waveflow ui sweep`. Added smoke coverage that exercises the Rich table rendering from outside the repository root with a temporary sweep-safe topology.
- Out-of-scope flagged: This slice does not add live per-iteration progress streams or change any sweep algorithm return payloads.
- Assumptions invalidated: The initial smoke test assumption that `examples/json/example_1_simple.json` was sweep-safe was false because the current geometry trips the RIS FOV gate; the test was corrected to use a self-contained topology fixture.
- Known debt (acknowledged): Live sweep dashboards and per-iteration UX still need a dedicated progress/event protocol from the algorithms rather than result-only rendering in the terminal layer.
- Limitations: Verification covered compile checks and `tests/test_smoke.py`; this slice did not add algorithm-level progress semantics or broader CLI integration tests.

## Task: Add Live Sweep UX to `waveflow ui`
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Broad / Trivial
Rollback plan: Revert the additive progress-callback hooks in `controller/beamsweeping`, the live sweep rendering path in `risnet/terminal_cli.py`, and the matching smoke/docs updates.
Change budget: [files 7] [functions: sweep progress hooks, terminal live renderer, smoke coverage] [interfaces: `waveflow ui sweep` live output and algorithm selection only] [state mutations: none]

### Scope
- `controller/beamsweeping/base.py` — add a minimal optional progress event helper
- `controller/beamsweeping/algorithms/linear_brute_force.py` — emit live progress events during sweep measurements
- `controller/beamsweeping/algorithms/coarse_fine_sweep.py` — emit coarse/fine live progress events during sweep measurements
- `risnet/terminal_cli.py` — use `SweepAlgorithmLoader`, add live Rich rendering, and expose a `--live/--no-live` UX toggle
- `tests/test_smoke.py` — exercise the live terminal sweep path
- `tasks/test-suite.md` — record the live sweep smoke coverage and remaining gap
- `tasks/todo.md` — record this task

### Steps
- [x] Inspect current sweep algorithm interfaces and CLI path
- [x] Add minimal additive progress hooks for supported algorithms
- [x] Add live Typer/Rich sweep rendering without changing result payloads
- [x] Verify compile and focused smoke coverage

### Review
- Completed: Added live Rich sweep rendering to `waveflow ui sweep` with a progress bar, phase/status table, and rolling recent-measurement table. The CLI now routes through `SweepAlgorithmLoader` so `--algo` is honored, and `linear` plus `coarse-fine` emit additive progress events without changing their final result payloads.
- Out-of-scope flagged: This slice does not add live progress for vision, ML, DE-localization, or other specialized sweep algorithms.
- Assumptions invalidated: None.
- Known debt (acknowledged): Progress/event compatibility is still only implemented for `linear` and `coarse-fine`; other algorithms fall back to the final-result UX until they adopt the same callback contract.
- Limitations: Verification covered compile checks and `tests/test_smoke.py`; this slice does not add dedicated algorithm-level tests for the progress callback events.

## Task: Clean Invalid-Node Failure for Live Sweep UI
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the pre-live node validation in `risnet/terminal_cli.py`, the matching smoke test, and the task/test-suite updates.
Change budget: [files 4] [functions: terminal sweep preflight validation, smoke coverage] [interfaces: `waveflow ui sweep` invalid-node failure output only] [state mutations: none]

### Scope
- `risnet/terminal_cli.py` — validate AP/RIS/UE names before opening the live Rich UI
- `tests/test_smoke.py` — add a smoke test for the invalid-node failure path
- `tasks/test-suite.md` — record the added smoke coverage
- `tasks/todo.md` — record this task

### Steps
- [x] Inspect the current invalid-node failure path in `waveflow ui sweep`
- [x] Move node validation ahead of the live Rich renderer
- [x] Verify compile and focused smoke coverage

### Review
- Completed: `waveflow ui sweep` now validates the requested AP/RIS/UE names before opening the live Rich renderer, so missing-node failures print a clean terminal error instead of showing a stuck pending sweep panel first.
- Out-of-scope flagged: This slice does not make sweep node lookup case-insensitive or auto-discover default AP/RIS/UE names.
- Assumptions invalidated: None.
- Known debt (acknowledged): The command still requires exact node names from the loaded topology; there is no fuzzy matching or default-role resolution in the interactive CLI path yet.
- Limitations: Verification covered compile checks and `tests/test_smoke.py`; this slice does not add broader CLI usability tests beyond the missing-node failure smoke.

## Task: Make `example_1_simple.json` Sweep-Safe
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the coordinate change in `examples/json/example_1_simple.json`, the new smoke test, and the matching task/test-suite updates.
Change budget: [files 4] [functions: none, example topology and smoke coverage only] [interfaces: bundled example topology behavior only] [state mutations: none]

### Scope
- `examples/json/example_1_simple.json` — adjust the simple example geometry so AP, RIS, and UE are sweep-safe under the current RIS FOV rules
- `tests/test_smoke.py` — add a smoke check that the bundled simple topology supports `waveflow ui sweep`
- `tasks/test-suite.md` — record the added bundled-topology sweep smoke coverage
- `tasks/todo.md` — record this task

### Steps
- [x] Inspect current `example_1_simple.json` usage and geometry
- [x] Update the simple example coordinates to a sweep-safe layout
- [x] Add smoke coverage for sweeping the bundled topology
- [x] Verify compile and focused smoke coverage

### Review
- Completed: Adjusted `examples/json/example_1_simple.json` to a sweep-safe AP/RIS/UE geometry under the default RIS FOV rules and added smoke coverage that runs `waveflow ui sweep` directly against the bundled example file.
- Out-of-scope flagged: This slice does not update the docs text yet; it only makes the bundled example topology itself consistent with the current sweep constraints.
- Assumptions invalidated: The first revised UE position still failed the actual sweep geometry, so the example was corrected again to a passing layout after CLI verification.
- Known debt (acknowledged): The docs still contain older sweep examples and should be aligned with the now sweep-safe bundled topology in a separate documentation pass.
- Limitations: Verification covered `tests/test_smoke.py`, `tests/test_scenarios.py`, and a compile check; this slice did not update broader tutorial/readme wording yet.

## Task: Align `TUTORIAL.md` with Current Sweep UX
Mode: Standard
Risk: Low
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: Revert the tutorial-only wording updates in `TUTORIAL.md` and this task entry.
Change budget: [files 2] [functions: none] [interfaces: documentation only] [state mutations: none]

### Scope
- `TUTORIAL.md` — fix the `waveflow ui sweep` example to include `--topology`, note that `example_1_simple.json` is now sweep-safe, and update the live sweep UX description to match current behavior
- `tasks/todo.md` — record this documentation task

### Steps
- [x] Inspect the current tutorial sweep examples and live UX wording
- [x] Update the stale CLI example and live UX note
- [x] Review diff for scope compliance

### Review
- Completed: Updated the tutorial so the `waveflow ui sweep` example includes the bundled topology path, documented that `example_1_simple.json` is now sweep-safe, and revised the live sweep UX section to reflect the current Rich live path for `linear` and `coarse-fine`.
- Out-of-scope flagged: `README.md` still contains its own sweep example text and was not changed in this pass.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: Verification was limited to diff review because this slice only changed documentation.

## Task: Fix Interactive RIS-Aware UE Fallback
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the fallback/labeling edits in `cli/main_shell.py`, the focused smoke test, and the task/test-suite updates.
Change budget: [files 4] [functions: `RISNetCLI._add_ue_within_ris_fov`, `RISNetCLI.do_add`, `RISNetCLI._handle_add_random`, smoke coverage] [interfaces: interactive shell UE placement messaging/behavior only] [state mutations: none]

### Scope
- `cli/main_shell.py` — stop claiming RIS-aware placement when the AP is unreachable and fall back immediately to unconstrained UE placement
- `tests/test_smoke.py` — add focused coverage for the unreachable-AP fallback path
- `tasks/test-suite.md` — record the new interactive-shell fallback coverage
- `tasks/todo.md` — record this task

### Steps
- [x] Inspect the RIS-aware UE placement path and identify the inconsistent fallback branch
- [x] Fix the helper/caller behavior so unreachable AP geometry falls back cleanly
- [x] Verify compile and focused smoke coverage

### Review
- Completed: The interactive shell now falls back immediately to unconstrained UE placement when the AP is outside the RIS deflection capability, and the success message no longer claims “RIS-aware placement” in that case.
- Out-of-scope flagged: This slice does not redesign the shell’s random topology generator or auto-correct RIS/AP placement to guarantee reachability.
- Assumptions invalidated: None.
- Known debt (acknowledged): Random AP/RIS placement can still produce unreachable geometries; this fix only prevents the shell from mislabeling the resulting UE placement as RIS-aware.
- Limitations: Verification covered `tests/test_smoke.py` and compile checks; this slice does not yet add end-to-end subprocess coverage for the full interactive shell transcript.

## Task: Fix DE Sweep Result Printer Compatibility
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the result-normalization edits in `cli/connection_handler.py`, the focused smoke test, and the task/test-suite updates.
Change budget: [files 4] [functions: `ConnectionHandler.print_sweep_results`, smoke coverage] [interfaces: legacy `connect --sweep ... --algo de` display path only] [state mutations: none]

### Scope
- `cli/connection_handler.py` — make the legacy sweep result printer tolerate DE-style NumPy payloads instead of assuming list/dict truthiness everywhere
- `tests/test_smoke.py` — add focused coverage for the DE result-printer compatibility path
- `tasks/test-suite.md` — record the added printer compatibility coverage
- `tasks/todo.md` — record this task

### Steps
- [x] Inspect the DE result shape and locate the ambiguous truth-value branch in the legacy printer
- [x] Normalize sequence inputs and guard dict-only measurement table logic
- [x] Verify compile and focused smoke coverage

### Review
- Completed: The legacy unified sweep printer now normalizes NumPy sequence payloads from DE-style results and only treats `measurements` as a structured table when it is actually a dict. This removes the ambiguous truth-value failure in `connect --sweep ... --algo de`.
- Out-of-scope flagged: This slice does not redesign the DE algorithm output schema or add end-to-end interactive-shell subprocess coverage for `connect --sweep --algo de`.
- Assumptions invalidated: The first regression test harness used `list.append` directly as `print_func`, which was incompatible with blank-line calls; it was corrected to a compatible collector.
- Known debt (acknowledged):
- Limitations: Verification covered `tests/test_smoke.py` and compile checks; this slice does not yet exercise the full interactive shell transcript under subprocess.

## Task: Fix `waveflow ui run` Legacy Flag Passthrough
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the Typer passthrough edit in `risnet/terminal_cli.py`, the smoke/doc updates, and this task entry.
Change budget: [files 5] [functions: terminal `run` command, smoke coverage, docs examples] [interfaces: `waveflow ui run` argument parsing only] [state mutations: none]

### Scope
- `risnet/terminal_cli.py` — allow `waveflow ui run` to pass unknown trailing flags like `--breakdown` through to the legacy shell command
- `tests/test_smoke.py` — add smoke coverage for `waveflow ui run --topology ... signal ... --breakdown`
- `tasks/test-suite.md` — record the added passthrough coverage
- `README.md` and `TUTORIAL.md` — update examples to include `--topology` and the fixed `run` invocation form
- `tasks/todo.md` — record this task

### Steps
- [x] Inspect the `run` command wiring and confirm Typer is consuming legacy flags
- [x] Allow passthrough of trailing legacy options and update examples
- [x] Verify compile and focused smoke coverage

### Review
- Completed: `waveflow ui run` now passes unknown trailing flags like `--breakdown` through to the legacy shell command, and the README/TUTORIAL examples now show the correct `--topology` usage and passthrough invocation form.
- Out-of-scope flagged: This slice does not make the Typer/Rich UI stateful; commands like `waveflow ui sweep` still require `--topology` or explicit node creation in the same command path.
- Assumptions invalidated: The first implementation used `ctx: typer.Context` without making `typer` visible to Typer’s runtime annotation resolver, which broke multiple `waveflow ui` commands; the fix exposed the local Typer import through module globals before command registration.
- Known debt (acknowledged):
- Limitations: Verification covered `tests/test_smoke.py` and compile checks; this slice does not add broader command-by-command coverage for every legacy shell verb through `waveflow ui run`.
