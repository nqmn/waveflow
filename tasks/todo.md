## Task: Commit Pending CLI Startup State-Loading Fixes
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the startup-loading edits in `cli/main_shell.py`, `risnet/terminal_cli.py`, and `risnet/__main__.py`, then rerun the CLI smoke suite.
Change budget: [files 4] [functions: `RISNetCLI.__init__`, terminal CLI shell bootstrap, web bootstrap state initialization] [interfaces: CLI/web startup behavior only] [state mutations: startup load behavior]

### Scope
- `cli/main_shell.py` — allow shell startup to skip auto-loading persisted state when the caller already controls topology loading.
- `risnet/terminal_cli.py` — instantiate `RISNetCLI` with `auto_load=False` on the modern terminal path.
- `risnet/__main__.py` — stop preloading the web state manager with the thread-safe network at bootstrap.
- `tasks/todo.md` — record this scoped startup-fix task.

### Steps
- [x] Review the pending startup-loading diffs and confirm they belong to one behavior fix
- [x] Run the CLI/entrypoint smoke suite against the pending changes
- [x] Commit the three related files as one scoped batch

### Review
- Completed: Confirmed the pending diffs are one coherent startup-loading fix: `RISNetCLI` can now skip auto-loading persisted state when the caller already controls topology/bootstrap flow, the modern terminal path opts into that behavior, and the web bootstrap no longer preloads the state manager with the thread-safe network. Verified with `pytest -q tests/test_smoke.py`, which passed cleanly (`35 passed in 32.06s`).
- Out-of-scope flagged: I did not change the local `.claude/settings.local.json`, nor did I modify any tests or documentation beyond this task log.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This task validates the existing smoke coverage only; it does not add new targeted tests for `auto_load=False` or web state-manager bootstrap semantics.

## Task: Prepare Release 2.0.4 and Trigger PyPI Build
Mode: Standard
Risk: High
Confidence: Guarded
Operational risk: Broad / Partial
Rollback plan: Revert the version bumps in `pyproject.toml` / `setup.py`, delete the local and remote `2.0.4` tag if needed, and restore the prior release metadata if validation fails.
Change budget: [files 3] [functions: none] [interfaces: package metadata version and release tag] [state mutations: git tag and remote push after validation]

### Scope
- `pyproject.toml` — bump the canonical package version from `2.0.3` to `2.0.4`.
- `setup.py` — keep the legacy setuptools mirror version aligned to `2.0.4`.
- `tasks/todo.md` — record this release-preparation task.

### Steps
- [x] Bump package metadata to `2.0.4`
- [x] Validate local build metadata for `2.0.4`
- [x] Commit the release-preparation changes
- [x] Create and push git tag `2.0.4`

### Review
- Completed: Bumped package metadata from `2.0.3` to `2.0.4` in both `pyproject.toml` and `setup.py`, then validated the release locally with `python3 -m build --no-isolation`, which successfully produced `waveflow-sim-2.0.4.tar.gz` and `waveflow_sim-2.0.4-py3-none-any.whl`.
- Out-of-scope flagged: I did not publish directly to PyPI from this environment; publication depends on pushing the release tag so the existing GitHub Actions workflow can perform the authenticated upload.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The local build confirms package metadata and artifact generation only; final PyPI publication depends on the remote CI environment and its configured credentials.

## Task: Point Landing Page Documentation CTA to `TUTORIAL.md`
Mode: Standard
Risk: Low
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: Revert the CTA href change in `index.html` and this task-log entry.
Change budget: [files 2] [functions: none] [interfaces: static landing-page link target only] [state mutations: none]

### Scope
- `index.html` — update the `Read Documentation` CTA so it links directly to the GitHub `TUTORIAL.md` URL.
- `tasks/todo.md` — record this landing-page CTA adjustment.

### Steps
- [x] Locate the documentation CTA in `index.html`
- [x] Change the target URL to the GitHub `TUTORIAL.md` page
- [x] Verify the diff remains limited to `index.html` and this task log

### Review
- Completed: Updated the landing-page `Read Documentation` CTA to point directly to `https://github.com/nqmn/waveflow/blob/main/TUTORIAL.md`.
- Out-of-scope flagged: I did not change any other navigation or documentation links.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This is a single-link landing-page update only.

## Task: Add Future Web/GUI FAQ to `index.html`
Mode: Standard
Risk: Low
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: Revert the added FAQ entry in `index.html` and this task-log entry.
Change budget: [files 2] [functions: none] [interfaces: static landing-page FAQ copy only] [state mutations: none]

### Scope
- `index.html` — add an FAQ entry answering whether a web-based or GUI experience is planned in the future.
- `tasks/todo.md` — record this FAQ addition.

### Steps
- [x] Add a future-facing FAQ for web/GUI plans
- [x] Keep the answer aligned with the current roadmap: yes, in future
- [x] Verify the diff remains limited to `index.html` and this task log

### Review
- Completed: Added a FAQ entry to `index.html` that explicitly states a richer web-based or GUI experience is planned for the future, while clarifying that the current product surface is centered on the terminal and Python workflow.
- Out-of-scope flagged: I did not add any new web application implementation or change the existing UI architecture.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This is roadmap-oriented copy only; it does not introduce a new frontend implementation.

## Task: Add ML, Vision, and UI FAQs to `index.html`
Mode: Standard
Risk: Low
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: Revert the FAQ additions in `index.html` and this task-log entry.
Change budget: [files 2] [functions: none] [interfaces: static landing-page FAQ copy only] [state mutations: none]

### Scope
- `index.html` — add FAQ entries that explicitly cover machine learning support, vision/computer-vision workflows, and UI surfaces.
- `tasks/todo.md` — record this FAQ expansion.

### Steps
- [x] Add an FAQ for built-in ML support
- [x] Add an FAQ for vision / camera-assisted workflows
- [x] Add an FAQ for the available UI surfaces
- [x] Verify the diff remains limited to `index.html` and this task log

### Review
- Completed: Added three focused FAQ entries to `index.html` covering built-in ML support, vision-assisted workflows, and the available UI surfaces so the landing-page FAQ now addresses those product areas directly.
- Out-of-scope flagged: I did not alter the engine FAQ, deployment flow, or broader docs outside this landing page.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This is FAQ copy only; it does not add new product capabilities or browser-test coverage.

## Task: Expand FAQ and Add Mobile Hamburger Navigation in `index.html`
Mode: Standard
Risk: Low
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: Revert the navigation/FAQ edits in `index.html` and this task-log entry.
Change budget: [files 2] [functions: static page JavaScript helpers only] [interfaces: landing-page navigation and FAQ content only] [state mutations: none]

### Scope
- `index.html` — add a usable mobile hamburger menu and expand the FAQ section with broader engine/workflow questions.
- `tasks/todo.md` — record this landing-page enhancement task.

### Steps
- [x] Audit the current landing page navigation and FAQ structure
- [x] Add a mobile hamburger menu with toggle behavior
- [x] Expand the FAQ content while keeping the page styling consistent
- [x] Verify the diff remains limited to the landing page and this task log

### Review
- Completed: Added a mobile hamburger menu with an in-page toggle and close-on-link behavior, expanded the FAQ into a more comprehensive section covering SimRIS vs LightRIS, workflow ownership, validation, deployment, ML usage, and MATLAB dependence, and kept the edits contained to `index.html` plus this task log.
- Out-of-scope flagged: I did not add browser automation, deploy the landing page, or rework other docs/marketing copy outside this file.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This remains a static HTML landing page; the new mobile menu and FAQ behaviors are not covered by automated browser tests.

## Task: Tighten SimRIS/LightRIS Complementarity Copy in `index.html`
Mode: Standard
Risk: Low
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: Revert the `index.html` copy adjustment and this task-log entry.
Change budget: [files 2] [functions: none] [interfaces: static landing-page copy only] [state mutations: none]

### Scope
- `index.html` — replace engine-section wording that implies `SimRIS` and `LightRIS` are interchangeable, and state their complementary roles more explicitly.
- `tasks/todo.md` — record this wording correction.

### Steps
- [x] Audit `index.html` for misleading engine-positioning copy
- [x] Replace the section intro with complementary-role wording
- [x] Verify the diff remains limited to `index.html` and this task log

### Review
- Completed: Updated the engine-section introduction in `index.html` so it now states that Waveflow is built around two complementary engines with distinct roles, rather than implying users simply switch between two substitutes for the same job.
- Out-of-scope flagged: I did not rewrite the rest of the landing page or adjust other docs outside `index.html`.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This is a copy correction only; it does not change the actual engine-selection behavior already implemented in the codebase.

## Task: Correct SimRIS Positioning Copy in `index.html`
Mode: Standard
Risk: Low
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: Revert the copy change in `index.html` and this task-log entry.
Change budget: [files 2] [functions: none] [interfaces: static landing-page copy only] [state mutations: none]

### Scope
- `index.html` — correct the SimRIS FAQ/marketing wording so it states SimRIS is an IEEE/published reference engine integrated into Waveflow, not published by Waveflow itself.
- `tasks/todo.md` — record this copy correction.

### Steps
- [x] Locate the SimRIS/LightRIS comparison copy in `index.html`
- [x] Replace the inaccurate SimRIS ownership wording
- [x] Verify the diff remains limited to the intended copy correction

### Review
- Completed: Corrected the landing-page copy so SimRIS is described as the reference stochastic channel engine integrated from published/IEEE articles to enhance Waveflow, while LightRIS remains Waveflow's native analytical engine for fast system-level evaluation, ML dataset generation, and large beam sweeps.
- Out-of-scope flagged: I did not alter any other marketing copy or documentation wording outside `index.html`.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This is a wording correction only; it does not change engine behavior or documentation elsewhere.

## Task: Add Root Landing Page `index.html`
Mode: Standard
Risk: Low
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: Remove the new root `index.html` file and revert this task-log entry.
Change budget: [files 2] [functions: none] [interfaces: new static landing page only] [state mutations: none]

### Scope
- `index.html` — add the provided marketing landing page as a new root static file.
- `tasks/todo.md` — record this task.

### Steps
- [x] Confirm the repo does not already have a root `index.html`
- [x] Add the provided landing page as `index.html`
- [x] Verify the added file content and working-tree scope

### Review
- Completed: Confirmed there was no existing root `index.html`, then added the provided Waveflow landing page as a new static root file. Verified that the resulting working-tree scope is limited to `index.html` and this task-log entry.
- Out-of-scope flagged: I did not wire this page into any deployment, Python route, or docs navigation, and I did not modify existing HTML files under `risformula/`.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This adds a static HTML entry page only; it does not wire deployment, asset bundling, or automated browser tests.

## Task: Prepare Release 2.0.3 and PyPI Tag Trigger
Mode: Standard
Risk: High
Confidence: Stable
Operational risk: Broad / Partial
Rollback plan: Revert the version bumps in `pyproject.toml` / `setup.py`, restore the prior tag filter in `.github/workflows/publish.yml`, and delete the `2.0.3` tag before it is pushed if validation fails.
Change budget: [files 4] [functions: none] [interfaces: package metadata version and publish-tag CI trigger] [state mutations: git tag only after validation]

### Scope
- `pyproject.toml` — bump the canonical package version from `2.0.2` to `2.0.3`.
- `setup.py` — keep the legacy setuptools mirror version aligned to `2.0.3`.
- `.github/workflows/publish.yml` — allow the PyPI publish workflow to trigger from bare semantic tags such as `2.0.3`, not only `v*`.
- `tasks/todo.md` — record this release-preparation task.

### Steps
- [x] Bump package metadata to `2.0.3`
- [x] Expand the publish workflow tag filter to accept bare semantic tags
- [x] Validate local build metadata
- [ ] Create the `2.0.3` git tag

### Review
- Completed: Raised the package metadata in `pyproject.toml` and `setup.py` to `2.0.3`, expanded `.github/workflows/publish.yml` so PyPI publication can be triggered by a bare semantic tag like `2.0.3` in addition to the previous `v*` pattern, corrected the PEP 621 license field to use the checked-in `LICENSE` file, and verified the release metadata locally with `python3 -m build --no-isolation`, which successfully produced both the sdist and wheel for `2.0.3`.
- Out-of-scope flagged: I did not push a tag or publish to PyPI from this environment; that remains gated by the repository remote and PyPI credentials configured in GitHub Actions.
- Assumptions invalidated: None so far.
- Known debt (acknowledged):
- Limitations: The package metadata is now locally buildable, but publishing still depends on pushing the commit/tag to the repository remote so GitHub Actions can upload to PyPI.

## Task: Validate Burtakov 2023 QRIS Regression Suite Registration
Mode: Standard
Risk: Low
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: Revert this task-log entry only.
Change budget: [files 1] [functions: none] [interfaces: test inventory confirmation only] [state mutations: none]

### Scope
- `tests/test_burtakov2023_qris.py` — verify suite structure, actual test count, and pytest status.
- `tasks/test-suite.md` — confirm whether the existing inventory entry is already correct.
- `tasks/todo.md` — record this verification.

### Steps
- [x] Confirm whether `tests/test_burtakov2023_qris.py` is already listed in `tasks/test-suite.md`
- [x] Verify the listed test count against the actual file and run the suite
- [x] Record the verification outcome without changing the inventory when already correct

### Review
- Completed: Confirmed that `tests/test_burtakov2023_qris.py` is already registered in `tasks/test-suite.md` with the correct inventory count (`25` tests). Verified by counting `def test_*` definitions and running `pytest -q tests/test_burtakov2023_qris.py`, which passed cleanly (`25 passed in 0.42s`).
- Out-of-scope flagged: I did not edit `tasks/test-suite.md` because the existing Burtakov entry was already accurate; I also did not touch unrelated working-tree changes in `README.md`, `TUTORIAL.md`, `FUTURE.md`, or `.claude/settings.local.json`.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This task validates registration and execution of the current Burtakov QRIS regression suite only; it does not change the QRIS model coverage itself.

## Task: Document the Official SimRIS and LightRIS Engine Split
Mode: Standard
Risk: Low
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: Revert the README/TUTORIAL wording and this task-log entry.
Change budget: [files 3] [functions: none] [interfaces: documentation only] [state mutations: none]

### Scope
- `README.md` — document the official engine split, default SimRIS-first behavior, fallback semantics, and explicit CLI/API examples.
- `TUTORIAL.md` — teach the engine model, connect CLI flags, and the workflow ownership split between SimRIS and LightRIS.
- `tasks/todo.md` — record this documentation task.

### Steps
- [x] Add an engine-overview section to README
- [x] Update CLI/API examples to show explicit `simris` / `lightris` selection
- [x] Update the tutorial to explain engine ownership and fallback behavior

### Review
- Completed: Updated `README.md` and `TUTORIAL.md` so the official two-engine model is now explicit: `SimRIS` as the reference stochastic engine and `LightRIS` as the native analytical engine. Documented default SimRIS-first `connect()` behavior, explicit fallback to `lightris`, CLI flags (`--channel-model`, `--environment`, `--scenario`), Python API examples for explicit engine selection, and the intentional ownership split where sweep/tapering/feedback remain LightRIS-native workflows.
- Out-of-scope flagged: I did not change the implementation or run extra tests for this docs-only task; the code/test verification was already completed in the preceding integration task.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This updates user-facing documentation only; it does not add new benchmark or publication-facing validation material.

## Task: Complete Engine-Aware CLI Integration for SimRIS and LightRIS
Mode: Standard
Risk: High
Confidence: Guarded
Operational risk: Broad / Partial
Rollback plan: Revert the CLI connect/demo option parsing, engine-aware output rendering, focused smoke/contract tests, and the test-suite/task-log wording for this task.
Change budget: [files 5] [functions: `terminal_cli.connect`, `terminal_cli.demo_connect`, `ConnectionHandler.parse_flags`, `ConnectionHandler.execute_single_connect`, focused smoke/connect tests] [interfaces: CLI engine-selection surface for native connect/demo flows] [state mutations: none beyond existing connect snapshots]

### Scope
- `risnet/terminal_cli.py` — add official engine-selection options to native `ui connect` / `demo-connect` and surface requested/used engine metadata in the Rich output.
- `cli/connection_handler.py` — parse and forward `channel_model`, `environment`, and `scenario` through the connect execution path.
- `tests/test_smoke.py` and `tests/test_connect_characterization.py` — cover CLI-level engine selection and explicit SimRIS->LightRIS fallback visibility.
- `tasks/test-suite.md` — keep test counts and CLI/connect coverage current.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add engine-aware CLI flag parsing for `ui connect` and `demo-connect`
- [x] Surface requested/used/fallback engine metadata in CLI-facing connect output
- [x] Add focused smoke/contract coverage and rerun regression

### Review
- Completed: Added official CLI engine-selection surface for the native UI connect/demo flows. `ConnectionHandler.parse_flags()` and `execute_single_connect()` now accept and forward `--channel-model`, `--environment`, and `--scenario`, while `risnet.terminal_cli.connect()` and `demo-connect` surface `channel_model_requested`, `channel_model_used`, and explicit fallback reasons in user-facing output. Added CLI smoke coverage for `demo-connect --channel-model simris` and for native `ui connect` visibly falling back from unsupported SimRIS requests to `lightris`. Verified with `pytest -q tests/test_smoke.py tests/test_connect_characterization.py tests/test_scenarios.py` (`87 passed`) and `pytest -q tests/test_smoke.py tests/test_lightris_channel.py tests/test_lightris_theory.py tests/test_connect_characterization.py tests/test_scenarios.py tests/test_simris_channel.py tests/test_simris_paper_formulas.py tests/test_simris_physics_regression.py` (`226 passed`).
- Out-of-scope flagged: I did not try to make sweep/feedback/tapering workflows run on SimRIS end-to-end; those remain intentionally LightRIS-owned workflows and still rely on the documented engine boundary.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This completes official engine selection on the core connect path, scenario runner, and native CLI connect/demo surfaces. Remaining specialization is by design: beam-sweep, tapering-heavy, and feedback-heavy workflows stay LightRIS-native rather than being forced into partial SimRIS support.

## Task: Validate and Register Toubal 2025 Beam-Tracking Regression Suite
Mode: Standard
Risk: Low
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: Revert the task-log entry and unstage the new Toubal test file / related roadmap note if needed.
Change budget: [files 2] [functions: none] [interfaces: test inventory confirmation only] [state mutations: none]

### Scope
- `tests/test_toubal2025_beam_tracking.py` — verify the suite structure and pytest status.
- `tasks/test-suite.md` — confirm the file inventory entry is current and accurate.
- `FUTURE.md` — keep the Toubal roadmap references aligned with the new regression file.
- `tasks/todo.md` — record this verification.

### Steps
- [x] Confirm whether `tests/test_toubal2025_beam_tracking.py` is already listed in `tasks/test-suite.md`
- [x] Verify the listed test count against the actual file and run the suite
- [x] Record the verification outcome and prepare the related files for commit

### Review
- Completed: Confirmed that `tests/test_toubal2025_beam_tracking.py` is already registered in `tasks/test-suite.md` with the correct inventory count (`21` tests). Verified by counting `def test_*` definitions and running `pytest -q tests/test_toubal2025_beam_tracking.py`, which passed cleanly (`21 passed`). The roadmap references in `FUTURE.md` already point to this regression file for the deferred RCS/CRLB extensions.
- Out-of-scope flagged: I did not implement the deferred Toubal RCS path-loss model or CRLB analysis; those remain roadmap items only.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This task validates registration and execution of the current Toubal regression suite only; it does not add the future RCS/CRLB coverage described in `FUTURE.md`.

## Task: Formalize LightRIS Analytical Guarantees
Mode: Standard
Risk: High
Confidence: Guarded
Operational risk: Broad / Partial
Rollback plan: Revert the additive LightRIS theory helpers in `core/physics.py` / `utils/lightris.py`, remove the new theory tests, and restore the test-suite/task-log wording for this task.
Change budget: [files 5] [functions: additive LightRIS theory helpers, LightRIS low-level evaluator, new theory tests] [interfaces: additive `Physics`/`utils.lightris` APIs only] [state mutations: none]

### Scope
- `core/physics.py` — add explicit bounded analytical helpers for LightRIS angular deviation, correction losses, and aggregate correction composition.
- `utils/lightris.py` — route LightRIS evaluation through the new bounded theory helpers and expose the composed correction breakdown.
- `tests/test_lightris_channel.py` and/or a new focused LightRIS theory test file — verify monotonicity, bounds, and aggregate-loss consistency.
- `tasks/test-suite.md` — record the new LightRIS theory coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add additive bounded LightRIS theory helpers in `Physics`
- [x] Refactor `utils.lightris` to use those helpers and expose correction-term breakdown
- [x] Add focused LightRIS theory tests and update the test map

### Review
- Completed: Added explicit LightRIS theory helpers to `Physics` for shortest-angle deviation, bounded quadratic steering loss, bounded non-negative loss clamping, and additive correction-term composition. Strengthened `utils.lightris` from a scalar helper into a clearer analytical-model surface by adding `validate_lightris_config()`, `LIGHTRIS_ANALYTICAL_ASSUMPTIONS`, and `evaluate_lightris_decomposition()`, with `evaluate_lightris_metrics()` now embedding the full decomposition payload. Added `tests/test_lightris_theory.py` to enforce the intended guarantees: bounded/symmetric angular deviation, bounded monotone steering loss, additive non-negative correction composition, self-consistent decomposition, configuration validation/assumption surfacing, and monotone LightRIS SNR trends versus transmit power, distance, RIS size, and phase-bit resolution. Verified with `pytest -q tests/test_lightris_theory.py tests/test_lightris_channel.py tests/test_connect_characterization.py tests/test_scenarios.py` (`77 passed`) and `pytest -q tests/test_smoke.py tests/test_lightris_theory.py tests/test_lightris_channel.py tests/test_connect_characterization.py tests/test_scenarios.py tests/test_simris_channel.py tests/test_simris_paper_formulas.py tests/test_simris_physics_regression.py tests/test_johari2025_ris_5ghz.py tests/test_johari2025_physics_regression.py` (`268 passed`).
- Out-of-scope flagged: I did not attempt to prove LightRIS as a full stochastic channel model or to make its correction terms equivalent to SimRIS; this task formalizes the native engine as a bounded analytical complement, not a SimRIS replacement.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The new guarantees are model-internal guarantees for the analytical LightRIS engine. They do not yet provide an external approximation bound against SimRIS or measurement data, which still needs a separate benchmarking/calibration phase for publication.

## Task: Finalize Active LightRIS Naming and Verification
Mode: Standard
Risk: Low
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: Revert the active-doc wording updates and this task-log entry.
Change budget: [files 3] [functions: none] [interfaces: active documentation wording and coverage map only] [state mutations: none]

### Scope
- `FUTURE.md` — keep present-tense LightRIS guidance free of stale `LinkBudgetChannel` wording.
- `tasks/test-suite.md` — keep the active LightRIS adapter coverage wording aligned with `utils.lightris`.
- `tasks/todo.md` — record the closing verification pass for the internal LightRIS rename batch.

### Steps
- [x] Remove the last active-doc references that still described current LightRIS behavior with stale `link_budget` names
- [x] Rerun the focused/broad pytest suites on the current internal-rename branch
- [x] Record the verification status for the closing batch

### Review
- Completed: Cleaned the remaining active `test-suite` wording so the documented helper compatibility now points at `utils.lightris`, and updated the forward-looking `FUTURE.md` language so the current native engine is described directly as `LightRIS` rather than by the old adapter name. Reverified the current branch with `pytest -q tests/test_lightris_channel.py tests/test_connect_characterization.py tests/test_scenarios.py tests/test_smoke.py tests/test_simris_channel.py tests/test_simris_paper_formulas.py tests/test_simris_physics_regression.py tests/test_johari2025_ris_5ghz.py tests/test_johari2025_physics_regression.py` (`255 passed`).
- Out-of-scope flagged: Historical roadmap/task-log entries still mention `LinkBudgetChannel` or `link_budget` where they describe earlier phases; I left those intact as history instead of rewriting past entries.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This closes the active LightRIS naming pass on the Python side, but it does not rewrite historical records or change MATLAB-parity scope for SimRIS.

## Task: Refactor the Native Engine Name to LightRIS
Mode: Standard
Risk: High
Confidence: Stable
Operational risk: Broad / Partial
Rollback plan: Revert the `connect()` selector rename, adapter/export rewiring, LightRIS tests, and roadmap/test-map wording for this task.
Change budget: [files 10] [functions: `RISNetwork.connect`, native channel adapter/export surface, focused connect/scenario tests] [interfaces: public engine naming (`lightris` vs legacy `link_budget`)] [state mutations: none beyond the existing `connect()` snapshots]

### Scope
- `core/network.py` — make `lightris` the official native engine selector and route unsupported SimRIS requests to it explicitly.
- `risnet/channels/` and `waveflow/channels/` — expose `LightRISChannel` as the official native adapter surface.
- `risnet/terminal_cli.py` — switch the demo connect path to the official `LightRISChannel`.
- `tests/test_connect_characterization.py` — cover official `lightris` selection and rejection of the legacy `link_budget` selector.
- `tests/test_link_budget_channel.py` — migrate focused adapter coverage to the `LightRISChannel` surface while keeping the current helper physics under test.
- `tests/test_scenarios.py` — cover scenario passthrough for the official `lightris` selector.
- `FUTURE.md`, `tasks/test-suite.md`, `tasks/todo.md` — keep naming and complementarity guidance current.

### Steps
- [x] Refactor the official native engine selector from `link_budget` to `lightris`
- [x] Expose `LightRISChannel` and update focused code paths/tests to use it
- [x] Verify impacted suites and update roadmap/test-map wording

### Review
- Completed: Promoted `lightris` to the official native engine selector at the `connect()` boundary, so unsupported SimRIS requests now fall back explicitly to `lightris` instead of `link_budget`. Exposed `LightRISChannel` as the official adapter surface, added `risnet.channels.lightris` / `waveflow.channels.lightris` re-export modules, updated the terminal demo command, and migrated focused connect/scenario/adapter tests to the new naming. The public `connect()` surface now rejects the legacy `channel_model="link_budget"` selector, which makes the refactor real rather than alias-based.
- Out-of-scope flagged: I did not rename the low-level helper module `utils/link_budget.py`, the internal adapter file `risnet/channels/link_budget.py`, or the historical test filename `tests/test_link_budget_channel.py`; those remain implementation/history artifacts for now, while the official engine-facing surface is `lightris`.
- Assumptions invalidated: The assumption that the native adapter tests could still compare against bare `connect()` defaults was false after the earlier SimRIS-first switch; they had to compare against explicit `channel_model="lightris"` to stay engine-consistent.
- Known debt (acknowledged):
- Limitations: This completes the public engine-name refactor for the tested surface, but there are still historical internal names (`link_budget`) in helper/module paths that can be cleaned up in a later pass if we decide to fully rename the underlying implementation files.

## Task: Rename the Public Native Helper Surface to LightRIS
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the `risnet.channels` / `waveflow.channels` helper-export changes, the focused LightRIS helper test additions, and the roadmap/test-map wording for this task.
Change budget: [files 4] [functions: LightRIS helper exports, focused helper-equivalence tests] [interfaces: public helper names under `risnet.channels` / `waveflow.channels`] [state mutations: none]

### Scope
- `risnet/channels/lightris.py` and `risnet/channels/__init__.py` — expose official `LightRIS` helper names instead of `build_link_budget_*` on the public channel surface.
- `tests/test_link_budget_channel.py` — migrate the focused helper-equivalence coverage to the `LightRIS` helper names.
- `tasks/test-suite.md` and `tasks/todo.md` — keep the helper-surface coverage map current.

### Steps
- [x] Add official `LightRIS` helper names on the public channel surface
- [x] Migrate focused helper-equivalence coverage to those names
- [x] Verify impacted suites and update the coverage map

### Review
- Completed: Added official `LightRIS` helper names (`build_lightris_config`, `build_lightris_config_from_nodes`, `evaluate_lightris_from_nodes`, `evaluate_lightris_metrics`) on the public `risnet.channels` / `waveflow.channels` surface, and migrated the focused helper-equivalence tests to those names. The low-level `utils/link_budget.py` implementation remains the numerical source of truth for now, but the public helper surface now matches the `LightRIS` engine naming.
- Out-of-scope flagged: I did not rename the low-level utility module `utils/link_budget.py`, the internal adapter carrier file `risnet/channels/link_budget.py`, or the historical test filename `tests/test_link_budget_channel.py` in this task.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: Public helper naming is now aligned to `LightRIS`, but there are still historical internal file/module names that can be cleaned up later if we decide the extra churn is worth it.

## Task: Remove Stale Channel/ Test File Names from the Native LightRIS Surface
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Restore the deleted `risnet/channels/link_budget.py` and `waveflow/channels/link_budget.py` wrappers, rename `tests/test_lightris_channel.py` back to its historical filename, and revert the focused import/reference updates.
Change budget: [files 7] [functions: LightRIS adapter/export wiring, focused connect helper rename, test-file rename] [interfaces: internal module paths and test-file naming for the native LightRIS surface] [state mutations: none]

### Scope
- `risnet/channels/lightris.py` and `risnet/channels/__init__.py` — make the LightRIS module self-contained so the deleted channel wrapper is no longer needed.
- `core/network.py` and `tests/test_connect_characterization.py` — rename the remaining internal connect helper to `lightris`.
- `tests/test_lightris_channel.py` — keep adapter/helper coverage under the new filename after the rename from `test_link_budget_channel.py`.
- `tasks/test-suite.md` and `tasks/todo.md` — keep the test inventory and task log consistent with the renamed files.

### Steps
- [x] Remove stale channel wrapper modules that still carried the `link_budget` filename
- [x] Rename the remaining focused native-adapter test file and helper references to `lightris`
- [x] Verify impacted suites and update the test inventory

### Review
- Completed: Made `risnet/channels/lightris.py` self-contained, removed the stale `risnet/channels/link_budget.py` and `waveflow/channels/link_budget.py` wrappers, renamed the remaining focused adapter test file to `tests/test_lightris_channel.py`, and renamed the internal connect helper to `_prepare_connect_lightris`. Updated the test inventory accordingly.
- Out-of-scope flagged: I intentionally kept `utils/link_budget.py` as the low-level physics utility module for now; this batch removed stale channel-surface names, not the shared utility implementation name.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The official LightRIS engine surface is now free of stale channel/test wrapper filenames, but the low-level numerical utility module still uses the historical `link_budget` name internally.

## Task: Rename the Low-Level Native Utility Module to LightRIS
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Restore `utils/link_budget.py`, revert the utility-import renames across the native/ML/controller modules, and restore the LightRIS helper exports to their previous utility source.
Change budget: [files 20] [functions: low-level LightRIS utility helpers and their imports] [interfaces: internal utility module path and helper names] [state mutations: none]

### Scope
- `utils/lightris.py` and `utils/snr.py` — make `utils.lightris` the low-level source of truth for native engine geometry/physics helpers.
- `controller/`, `risnet/channels/`, and focused tests — update live imports and helper calls to the new utility names.
- `FUTURE.md`, `tasks/test-suite.md`, and `tasks/todo.md` — keep the roadmap and task map aligned with the completed rename.

### Steps
- [x] Create `utils.lightris` and migrate live imports/helper names to it
- [x] Remove the stale `utils/link_budget.py` module
- [x] Verify compile/regression status and update docs/task tracking

### Review
- Completed: Introduced `utils/lightris.py` as the low-level source of truth for the native fast-engine geometry/physics helpers, migrated active imports in `utils/snr.py`, `controller/ris_controller.py`, the ML beam-sweeping modules, and the LightRIS channel/test surface to the new helper names, then removed `utils/link_budget.py`. Also updated the forward-looking parts of `FUTURE.md` so the present-tense roadmap now refers to `LightRIS` instead of `LinkBudgetChannel` where appropriate.
- Out-of-scope flagged: Historical task-log text in `tasks/todo.md` still mentions older `LinkBudgetChannel` / `link_budget` names where it records what happened at the time; I left those as historical artifacts instead of rewriting history.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: Active code paths are now on `utils.lightris`, but some historical roadmap/task text still references `LinkBudgetChannel` when describing past phases.

## Task: Plan `LightRIS` Naming Split in Roadmap
Mode: Standard
Risk: Low
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: Revert the `FUTURE.md` wording and this task-log entry.
Change budget: [files 2] [functions: none] [interfaces: roadmap/documentation only] [state mutations: none]

### Scope
- `FUTURE.md` — add a concrete plan to position `SimRIS` as the published/reference engine and evolve the current `LinkBudgetChannel` path into a novel native engine named `LightRIS`.
- `tasks/todo.md` — record this roadmap task.

### Steps
- [x] Add naming/positioning guidance for `simris` vs `lightris`
- [x] Add a staged migration plan for `LinkBudgetChannel` -> `LightRIS`
- [x] Add a definition-of-done block for the naming split

### Review
- Completed: Updated `FUTURE.md` with a concrete publication-facing split: `SimRIS` stays the literature/reference engine, while the current native link-budget path should evolve into `LightRIS` as the proposed fast engine. Added staged migration guidance, compatibility-alias expectations, and a definition-of-done block for the rename/split.
- Out-of-scope flagged: I did not rename any code, CLI flags, adapters, or tests in this task; this is roadmap planning only.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The `LightRIS` name is now planned in the roadmap, but the actual code-level migration and benchmark/paper positioning work still need separate implementation tasks.

## Task: Tighten Johari 2025 Test Integrity Around Production Physics Utilities
Mode: Standard
Risk: Medium
Confidence: Guarded
Operational risk: Contained / Trivial
Rollback plan: Revert the additive `core/physics.py` utility methods, the Johari test rewrites, and any `tasks/test-suite.md` wording updates for this task.
Change budget: [files 4] [functions: additive EVM/BER physics utilities, focused Johari test rewrites] [interfaces: additive `Physics` methods only] [state mutations: none]

### Scope
- `core/physics.py` — add production utility methods for EVM→SNR and BER-from-EVM so Johari tests can stop relying on local formula helpers.
- `tests/test_johari2025_ris_5ghz.py` — rewrite the Johari comparison tests to use production utilities and fix misleading paper-claim wording.
- `tests/test_johari2025_physics_regression.py` — pin the new production utility outputs directly.
- `tasks/test-suite.md` — update coverage wording if the validation path changes materially.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add additive production utilities for EVM→SNR and BER-from-EVM
- [x] Rewrite Johari tests to use production utilities and tighten misleading assertions/documentation
- [x] Verify focused Johari suites and review the diff for scope discipline

### Review
- Completed: Added additive production helpers `Physics.evm_to_snr_dB()` and `Physics.ber_qpsk_from_evm()`, then rewrote the Johari 2025 comparison/regression suites to use those helpers directly instead of local test-only formula functions. Also corrected the misleading `-3.92 dB` quantization-loss narrative so it now matches the current production sinc² model being tested.
- Out-of-scope flagged: I did not attempt to reconcile the Johari paper's reported BER values with a different link/system model; the tests now clearly validate the production AWGN-style approximation instead of implying paper-perfect BER parity.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This tightening improves test integrity and transparency, but it does not make Waveflow a full EM/SDR reproduction of Johari et al.; absolute gain, full-wave patterns, and hardware-specific effects remain outside scope.

## Task: Make Default `connect()` Prefer Official SimRIS with Explicit Fallback
Mode: Standard
Risk: High
Confidence: Stable
Operational risk: Broad / Partial
Rollback plan: Revert the `core/network.py` default-engine change, the `LinkBudgetChannel` compatibility pin, the focused default/fallback tests, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 5] [functions: `RISNetwork.connect`, `LinkBudgetChannel.evaluate`, focused connect/adapter tests] [interfaces: default connect engine-selection behavior and result metadata] [state mutations: active-link and last-connect snapshots remain compatible]

### Scope
- `core/network.py` — make default `connect()` attempt SimRIS first, with explicit fallback to the link-budget engine when unsupported.
- `risnet/channels/link_budget.py` — pin the compatibility adapter to the legacy engine explicitly.
- `tests/test_connect_characterization.py` — add focused coverage for default SimRIS-request fallback behavior.
- `tests/test_link_budget_channel.py` — add focused coverage that the compatibility adapter still requests the link-budget engine explicitly.
- `tasks/test-suite.md` — record the default-engine and compatibility-adapter coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Change default `connect()` engine selection to prefer SimRIS with explicit fallback
- [x] Pin `LinkBudgetChannel` to `channel_model="link_budget"` and add focused tests
- [x] Verify focused suites and review the diff for scope discipline

### Review
- Completed: Changed `RISNetwork.connect()` so a missing `channel_model` now requests the official SimRIS engine first and falls back explicitly to `link_budget` when the request is unsupported. Kept the legacy `LinkBudgetChannel` adapter stable by pinning `channel_model="link_budget"` explicitly, then fixed a real regression uncovered by the new tests: boundary-origin indoor line geometries could trap SimRIS stochastic cluster projection in a non-terminating shrink loop. The SimRIS scatterer generators now cap the shrink loop and clamp back to the source/RIS boundary when the distance collapses, which restores fast completion for the official SimRIS path on that geometry. Verified with focused `connect`/scenario suites and a broader regression pass across smoke, SimRIS, link-budget, and Johari coverage.
- Out-of-scope flagged: I did not broaden SimRIS support for unsupported `connect()` features such as explicit `beam_angle_deg`, tapering-aware SimRIS physics, or feedback-loop integration; those still fall back explicitly to `link_budget`.
- Assumptions invalidated: The assumption that the default-engine switch was only a metadata/performance change was false; it surfaced a real termination bug in SimRIS stochastic cluster projection for a boundary-origin indoor geometry.
- Known debt (acknowledged):
- Limitations: The default `connect()` path is now SimRIS-first, but it still relies on explicit fallback for unsupported SimRIS request shapes and does not imply full numerical parity with the original MATLAB simulator.

## Task: Integrate Official SimRIS Selection into `RISNetwork.connect()`
Mode: Standard
Risk: High
Confidence: Guarded
Operational risk: Broad / Partial
Rollback plan: Revert the `core/network.py` engine-selection changes, the focused `connect()` and scenario tests, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: `RISNetwork.connect`, additive connect-channel helpers, focused connect/scenario tests] [interfaces: additive `channel_model` connect parameter and result metadata] [state mutations: active-link and last-connect snapshots remain compatible]

### Scope
- `core/network.py` — add official SimRIS-vs-link-budget selection at the `connect()` boundary with explicit fallback metadata.
- `tests/test_connect_characterization.py` — add focused coverage for supported SimRIS connect and explicit fallback behavior.
- `tests/test_scenarios.py` — add focused passthrough coverage for `channel_model="simris"` through the scenario runner.
- `tasks/test-suite.md` — record the new connect/scenario engine-selection coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add additive `channel_model` handling plus explicit SimRIS capability/fallback logic in `RISNetwork.connect()`
- [x] Add focused connect/scenario tests and update the test map
- [x] Verify focused suites and review the diff for scope discipline

### Review
- Completed: Integrated explicit `channel_model` selection into `RISNetwork.connect()` so supported `channel_model="simris"` requests now route through the official SimRIS adapter path and return SimRIS tensors/metadata, while unsupported explicit SimRIS requests fall back to the existing link-budget path with an explicit `channel_model_fallback_reason`. Added focused coverage in `tests/test_connect_characterization.py` for both supported and fallback paths, plus a scenario-runner passthrough test in `tests/test_scenarios.py`. Updated `tasks/test-suite.md` to record the new connect/scenario coverage.
- Out-of-scope flagged: `FUTURE.md` was already modified before this task and remains uncommitted, but this batch did not change it further. CLI/UI selection for `channel_model="simris"` was also not implemented here; this task stopped at the `RISNetwork.connect()` and scenario-service boundary.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The official SimRIS path is intentionally conservative for now. It currently falls back to the link-budget engine unless the caller provides an explicit SimRIS `environment` and `scenario`, and it does not yet support explicit beam-angle overrides, fixed RIS-normal overrides, tapering-aware SimRIS physics, or closed-loop feedback on the SimRIS branch.

## Task: Update `waveflow ui` Documentation for Native Modern Shell
Mode: Standard
Risk: Low
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: Revert the README, tutorial, and task-log documentation edits for this task.
Change budget: [files 3] [functions: none] [interfaces: documentation only] [state mutations: none]

### Scope
- `README.md` — update the `waveflow ui` overview and usage examples to reflect one-shot Rich commands plus the native interactive shell.
- `TUTORIAL.md` — correct the `waveflow ui` narrative, `status` and `connect` descriptions, and usage guidance so they match current behavior.
- `tasks/todo.md` — record this task.

### Steps
- [x] Audit the current README and tutorial coverage for `waveflow ui`
- [x] Update the docs to match the native shell and Rich-native command output
- [x] Verify the diff is limited to the requested documentation scope

### Review
- Completed: Updated `README.md` and `TUTORIAL.md` so `waveflow ui` is documented as both a one-shot Rich command surface and a native interactive modern shell, and corrected the `status`, `connect`, and usage guidance to match the current implementation.
- Out-of-scope flagged: Command-by-command screenshot-style output transcripts were not expanded further; this task only corrected the high-level behavior and usage descriptions that had drifted.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The tutorial now describes the richer `status` and `connect` sections textually instead of embedding large verbatim terminal captures, to avoid documentation drift from minor presentational changes.

## Task: Add SimRIS Channel Engine and Comparison Test
Mode: Standard
Risk: Medium
Confidence: Guarded
Operational risk: Contained / Trivial
Rollback plan: Revert the additive `risnet/channels/simris*` engine files, the export wiring, the focused comparison test, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 6] [functions: `SimRISChannel.evaluate`, deterministic SimRIS reference helpers, focused comparison tests] [interfaces: additive `risnet.channels` exports only] [state mutations: none]

### Scope
- `risnet/channels/` — add a scoped SimRIS engine and deterministic reference helpers for published-formula comparison.
- `tests/` — add a focused regression/comparison test against the current Waveflow link-budget path.
- `tasks/test-suite.md` — record the new engine/comparison coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add a scoped SimRIS engine and published-formula helpers under `risnet/channels`
- [x] Add a deterministic comparison test versus the current Waveflow engine
- [x] Verify focused tests and review the diff for scope discipline

### Review
- Completed: Added an additive deterministic SimRIS LOS engine in `risnet/channels/simris.py`, exported it through `risnet.channels` and `waveflow.channels.simris`, and added `tests/test_simris_channel.py` to verify the engine against a published-formula LOS reference slice while comparing its received-power math with the current Waveflow link-budget path. Updated `tasks/test-suite.md` to record the new coverage and the remaining full-SimRIS parity gap.
- Out-of-scope flagged: Full SimRIS v18 stochastic parity was not ported in this task; LOS/NLOS probability sampling, cluster/sub-ray generation, shadow fading, and Monte Carlo realizations remain outside the current engine slice.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The new engine is intentionally limited to a deterministic LOS subset that is directly testable against the published equations; it does not yet claim behavioral equivalence to the full MATLAB simulator.

## Task: Extend SimRIS Engine Toward Full Stochastic Port
Mode: Standard
Risk: Medium
Confidence: Guarded
Operational risk: Contained / Trivial
Rollback plan: Revert the additive stochastic SimRIS engine changes, the new SimRIS tests, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: seeded SimRIS H/G/D generator, stochastic helper functions, focused SimRIS tests] [interfaces: additive `risnet.channels.simris` API only] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — extend the current LOS subset toward the full SimRIS v18 stochastic channel generator with seeded controls.
- `tests/test_simris_channel.py` — add focused tests for each newly ported behavior.
- `tasks/test-suite.md` — record the expanded SimRIS engine coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Extend the SimRIS engine with seeded stochastic H/G/D generation
- [x] Add focused tests for deterministic seed behavior, output shapes, and forced deterministic reductions
- [x] Verify focused tests and review the diff for scope discipline

### Review
- Completed: Extended `risnet/channels/simris.py` from a deterministic LOS slice into a seeded stochastic SimRIS-style H/G/D generator, added additive `SimRISConfig` and `SimRISStochasticChannel` exports, and expanded `tests/test_simris_channel.py` with coverage for tensor shapes, seeded determinism, and forced LOS-only reduction. Updated `tasks/test-suite.md` to record the broader SimRIS engine coverage and the remaining parity gap.
- Out-of-scope flagged: I did not claim full MATLAB v18 equivalence in this batch. The direct-link shared-cluster parity (`h_SISO`-style behavior), several environment-specific edge branches, and GUI validation logic remain outside the implemented/tested scope.
- Assumptions invalidated: Exact element-wise complex equality for the RIS→UE LOS tensor is not stable across deterministic and seeded stochastic paths because the model carries an arbitrary global phase term; the test was tightened to compare the physically meaningful magnitude reduction instead.
- Known debt (acknowledged):
- Limitations: The stochastic engine now produces seeded H/G/D tensors, but some MATLAB-v18 branches are still approximated or omitted, so this is a strong incremental port rather than a completed one-to-one reproduction.

## Task: Port SimRIS Direct-Link NLOS Generation
Mode: Standard
Risk: Medium
Confidence: Guarded
Operational risk: Contained / Trivial
Rollback plan: Revert the additive direct-link SimRIS changes, the new direct-link tests, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: SimRIS direct-link generator, direct-link regression tests] [interfaces: additive `risnet.channels.simris` behavior only] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — extend the direct-path generator so `D` includes SimRIS-style NLOS behavior instead of LOS-only approximation.
- `tests/test_simris_channel.py` — add focused tests for seeded direct-link NLOS behavior.
- `tasks/test-suite.md` — record the expanded SimRIS direct-path coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Extend the SimRIS direct-path generator with NLOS behavior
- [x] Add focused direct-link tests and update the test map
- [x] Verify focused tests and review scope

### Review
- Completed: Extended the SimRIS direct-path generator so `D` now includes seeded NLOS behavior instead of a LOS-only approximation, reusing shared Tx→RIS scatterers for the indoor path and generating seeded Tx→Rx scatterers for the outdoor path. Added focused tests covering indoor direct-link NLOS generation when LOS is forced off and zero-direct-path behavior when both LOS and NLOS are disabled. Updated `tasks/test-suite.md` to record the expanded direct-link coverage.
- Out-of-scope flagged: I still did not claim one-to-one MATLAB v18 parity for every direct-link branch; some detailed angle sampling and branch-specific conventions remain approximated.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The direct-link generator is now materially closer to SimRIS, but golden MATLAB-output parity for the full `D` tensor across multiple scenarios and seeds is still not established.

## Task: Expand SimRIS Branch Coverage
Mode: Standard
Risk: Medium
Confidence: Guarded
Operational risk: Contained / Trivial
Rollback plan: Revert the additive SimRIS branch fixes, the new scenario/array/outdoor tests, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: targeted SimRIS branch fixes, focused branch-coverage tests] [interfaces: additive `risnet.channels.simris` behavior only] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — audit and tighten scenario 2, UPA, and outdoor stochastic branches where needed.
- `tests/test_simris_channel.py` — add focused tests for scenario 2, UPA arrays, and outdoor stochastic determinism.
- `tasks/test-suite.md` — record the expanded SimRIS branch coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Audit branch behavior and apply targeted parity fixes if required
- [x] Add focused branch-coverage tests and update the test map
- [x] Verify focused tests and review scope

### Review
- Completed: Expanded `tests/test_simris_channel.py` with focused coverage for Scenario 2, square-terminal UPA arrays, and outdoor seeded stochastic replay. The current SimRIS engine passed these branches without requiring extra code changes in this batch, and `tasks/test-suite.md` now records the broader branch coverage explicitly.
- Out-of-scope flagged: This batch did not add MATLAB golden-output fixtures, so it still validates branch behavior through internal consistency and deterministic replay rather than direct MATLAB parity snapshots.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: Branch coverage is now broader, but it still does not prove one-to-one numerical equivalence with MATLAB across all scenarios and seeds.

## Task: Add SimRIS Golden-Parity Harness
Mode: Standard
Risk: Medium
Confidence: Guarded
Operational risk: Contained / Trivial
Rollback plan: Revert the additive parity harness, the focused parity tests, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: parity harness, focused golden tests or deterministic fixture layer] [interfaces: additive SimRIS validation tooling only] [state mutations: none]

### Scope
- `risnet/channels/simris.py` or adjacent validation helper — add the narrowest viable golden-parity harness available in the local environment.
- `tests/test_simris_channel.py` — add focused parity tests using the available reference path.
- `tasks/test-suite.md` — record the new parity coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Probe the local environment for MATLAB/Octave-compatible runtime support
- [x] Implement the best viable parity harness from that result
- [x] Verify focused tests and review scope

### Review
- Completed: Confirmed there is no local `matlab` or `octave` runtime in this environment, so I added the best viable fallback parity layer: a compact seeded regression-signature harness (`summarize_simris_tensors`) plus frozen indoor/outdoor seeded signature tests in `tests/test_simris_channel.py`. Updated `tasks/test-suite.md` to record this new regression-fixture coverage.
- Out-of-scope flagged: True external golden-output comparison against MATLAB/Octave could not be added in this environment because no compatible runtime is installed locally.
- Assumptions invalidated: The environment does not provide `matlab` or `octave`, so parity work had to fall back to deterministic local fixtures rather than external reference execution.
- Known debt (acknowledged):
- Limitations: These frozen signatures are strong local regression guards, but they are still derived from the Python port itself and therefore do not replace true MATLAB-to-Python parity checks.

## Task: Port SimRIS `h_SISO` Branch
Mode: Standard
Risk: Medium
Confidence: Guarded
Operational risk: Contained / Trivial
Rollback plan: Revert the additive `h_SISO` engine changes, the focused `h_SISO` tests, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: additive `h_SISO` generator, focused `h_SISO` tests] [interfaces: additive `risnet.channels.simris` output only] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — add seeded `h_SISO` generation for indoor/outdoor SimRIS branches.
- `tests/test_simris_channel.py` — add focused tests for `h_SISO` presence and seeded behavior.
- `tasks/test-suite.md` — record the new `h_SISO` coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Extend the SimRIS engine with additive `h_SISO` generation
- [x] Add focused `h_SISO` tests and update the test map
- [x] Verify focused tests and review scope

### Review
- Completed: Extended the additive SimRIS engine so the direct-channel tensor is also exposed under the published-model name `h_SISO`, tightened the direct Tx→Rx branch by using MATLAB-style random Rx AoA sampling, and expanded `tests/test_simris_channel.py` to validate `h_SISO` presence, alias parity with `D`, and updated seeded regression fixtures. Updated `tasks/test-suite.md` to record the new `h_SISO` coverage.
- Out-of-scope flagged: This still does not prove one-to-one MATLAB numerical parity for every `h_SISO` branch; the environment still lacks external MATLAB/Octave execution for true golden comparison.
- Assumptions invalidated: The frozen seeded signatures had to be updated after improving the direct Tx→Rx AoA branch, which confirms that the previous fixtures were guarding an earlier approximation rather than the tightened branch.
- Known debt (acknowledged):
- Limitations: `h_SISO` is now represented explicitly and regression-tested, but external parity against MATLAB outputs remains unavailable in the current environment.

## Task: Tighten Indoor RIS→Rx LOS AoA Parity
Mode: Standard
Risk: Medium
Confidence: Guarded
Operational risk: Contained / Trivial
Rollback plan: Revert the additive indoor RIS→Rx LOS AoA parity changes, the focused indoor branch tests, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: indoor RIS→Rx LOS AoA branch, focused indoor branch tests] [interfaces: additive `risnet.channels.simris` behavior only] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — tighten the indoor RIS→Rx LOS branch so Rx AoA sampling matches the MATLAB SimRIS structure more closely.
- `tests/test_simris_channel.py` — add focused tests for the indoor RIS→Rx branch behavior.
- `tasks/test-suite.md` — record the new indoor branch coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Tighten the indoor RIS→Rx LOS branch
- [x] Add focused indoor branch tests and update the test map
- [x] Verify focused tests and review scope

### Review
- Completed: Tightened the indoor RIS→Rx LOS branch so Rx AoA sampling now follows the MATLAB-style seeded random model instead of a purely geometric AoA, expanded `tests/test_simris_channel.py` with a focused indoor branch test for seed-sensitive `G`, and refreshed the frozen indoor/outdoor regression signatures accordingly. Updated `tasks/test-suite.md` to record the new indoor branch coverage.
- Out-of-scope flagged: I did not add an indoor RIS→Rx NLOS branch because that would deviate from the MATLAB code we are using as the reference; this batch stayed aligned to the published branch structure instead of inventing new physics.
- Assumptions invalidated: The indoor/outdoor frozen signatures changed once the RIS→Rx LOS branch was tightened, confirming that the previous fixtures were guarding a weaker approximation.
- Known debt (acknowledged):
- Limitations: This branch is now closer to MATLAB structurally, but true cross-runtime numerical parity is still unavailable without MATLAB/Octave execution.

## Task: Port SimRIS Validation Layer
Mode: Standard
Risk: Medium
Confidence: Guarded
Operational risk: Contained / Trivial
Rollback plan: Revert the additive SimRIS validation helpers, the focused validation tests, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: SimRIS validation helpers, focused validation tests] [interfaces: additive `risnet.channels.simris` validation API only] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — add geometry/config validation helpers that mirror the published MATLAB GUI checks.
- `tests/test_simris_channel.py` — add focused validation tests.
- `tasks/test-suite.md` — record the new validation coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add additive SimRIS validation helpers
- [x] Add focused validation tests and update the test map
- [x] Verify focused tests and review scope

### Review
- Completed: Added `validate_simris_configuration(...)` and `SimRISValidationResult` to mirror the important published MATLAB GUI checks for square-array counts, Tx placement, Rx height, far-field, cell radius, outdoor Tx height ordering, and reference-frequency warnings. Added focused tests for valid indoor geometry, multi-error outdoor rejection, and frequency warnings. Updated `tasks/test-suite.md` to record the new validation coverage.
- Out-of-scope flagged: I did not wire these validation helpers into the stochastic engine as hard blockers yet; they are exposed as additive validation API so we can keep the current engine behavior stable while parity work continues.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The validation layer now mirrors the prominent MATLAB GUI checks, but it still exists as additive API rather than mandatory preflight behavior on every engine call.

## Task: Add Optional SimRIS Validation Preflight
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the additive SimRIS preflight wiring, the focused preflight tests, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: SimRIS engine preflight options, focused preflight tests] [interfaces: additive `validate_preflight` engine option only] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — add optional MATLAB-style validation preflight to the SimRIS engine adapters.
- `tests/test_simris_channel.py` — add focused tests for preflight behavior.
- `tasks/test-suite.md` — record the new preflight coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add optional validation preflight controls to the SimRIS engine adapters
- [x] Add focused preflight tests and update the test map

### Review
- Completed: Wired the additive SimRIS validation layer into the engine adapters behind optional `validate_preflight` and `error_on_invalid` controls, so invalid geometry can now either raise immediately or be reported non-blockingly through the adapter result. Expanded `tests/test_simris_channel.py` with focused adapter-preflight coverage for both behaviors and updated `tasks/test-suite.md` to record the new validation-path coverage.
- Out-of-scope flagged: I did not make preflight validation mandatory on every SimRIS call; the default remains opt-in to avoid changing existing adapter behavior unexpectedly.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The preflight path now mirrors the additive MATLAB-style validation API during adapter execution, but true MATLAB/Octave cross-runtime parity is still unavailable in this environment.

## Task: Expand SimRIS vs Waveflow LOS Comparison Coverage
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the focused SimRIS comparison-test expansion and the `tasks/test-suite.md` updates for this task.
Change budget: [files 3] [functions: generalized SimRIS LOS reference helper, focused comparison tests] [interfaces: test coverage only] [state mutations: none]

### Scope
- `tests/test_simris_channel.py` — generalize the deterministic LOS reference helper and compare SimRIS versus the current Waveflow engine across multiple published-style geometries.
- `tasks/test-suite.md` — record the broader comparison coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Generalize the deterministic SimRIS LOS reference helper for indoor and outdoor LOS cases
- [x] Expand the SimRIS-versus-Waveflow comparison test across multiple published-style geometries
- [x] Verify focused tests and update the test map

### Review
- Completed: Generalized the deterministic SimRIS LOS reference helper so it can score both indoor and outdoor published-style LOS cases, then expanded the SimRIS-versus-Waveflow comparison coverage across indoor Scenario 1, indoor Scenario 2, and outdoor Scenario 1 geometries. Updated `tasks/test-suite.md` to reflect the broader comparison coverage.
- Out-of-scope flagged: This batch still compares only deterministic LOS slices against the current Waveflow link-budget path; it does not claim that SimRIS is uniformly better across full stochastic/NLOS behavior.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The stronger comparison matrix now covers three published-style LOS geometries, but full MATLAB v18 parity still depends on branch-by-branch stochastic validation and external MATLAB/Octave reference execution.

## Task: Add MATLAB-Style `h/g` Output Aliases to SimRIS Port
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the additive SimRIS output-alias changes, the focused alias tests, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: deterministic/stochastic SimRIS output packing, focused alias tests] [interfaces: additive SimRIS output keys only] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — add MATLAB-style `h` and `g` output aliases while preserving existing GUI-style `H/G/D` outputs.
- `tests/test_simris_channel.py` — add focused tests for alias shapes and transpose parity.
- `tasks/test-suite.md` — record the new output-alias coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add additive MATLAB-style `h` and `g` aliases to deterministic and stochastic SimRIS outputs
- [x] Add focused alias tests for shape and transpose parity
- [x] Verify focused tests and update the test map

### Review
- Completed: Added additive MATLAB-style `h` and `g` aliases to both deterministic and stochastic SimRIS outputs so the Python port now exposes both function-level naming (`h/g/h_SISO`) and GUI-level naming (`H/G/D`). Expanded existing SimRIS tests to verify alias shapes and transpose parity without changing the current `H/G/D` contract. Updated `tasks/test-suite.md` to record the new output-alias coverage.
- Out-of-scope flagged: I did not rename or remove the existing `H/G/D` keys; this batch keeps backward compatibility and only adds function-level aliases for closer MATLAB parity.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: Output naming is now closer to MATLAB, but exact branch-by-branch numerical parity still depends on further stochastic validation and external MATLAB/Octave reference comparison.

## Task: Port SimRIS Published Geometry Presets
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the additive SimRIS geometry-preset helper, the focused preset tests, and the `tasks/test-suite.md`/`FUTURE.md` updates for this task.
Change budget: [files 5] [functions: SimRIS geometry preset helper, focused preset tests, FUTURE status note] [interfaces: additive SimRIS helper only] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — add the published SimRIS GUI recommended geometry presets as a reusable helper.
- `risnet/channels/__init__.py` — export the new helper.
- `tests/test_simris_channel.py` — add focused tests for all four published presets and validation pass-through.
- `tasks/test-suite.md` — record the new preset coverage.
- `FUTURE.md` — mark external MATLAB/Octave golden parity as KIV while internal Python porting continues.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add a reusable SimRIS published-geometry helper
- [x] Add focused preset tests and update the test map
- [x] Update FUTURE.md to defer external MATLAB parity as KIV and verify focused tests

### Review
- Completed: Added `get_simris_published_geometry(...)` to expose the four recommended published SimRIS GUI geometries directly from production code, exported it through `risnet.channels`, and added focused parameterized tests that verify each preset and its validation pass-through. Updated `FUTURE.md` so external MATLAB/Octave golden parity is explicitly KIV while Python-side porting and regression work continue.
- Out-of-scope flagged: I did not wire the preset helper into CLI or scenario-loading flows; this batch only ports the published geometry presets into the SimRIS engine layer and validates them there.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The preset helper now removes duplication around published reference geometries, but full MATLAB v18 parity still depends on further stochastic branch tightening and deferred external verification.

## Task: Add End-to-End Published-Case SimRIS Helpers
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the additive published-case helper functions, the focused end-to-end tests, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: published-case SimRIS helper wrappers, focused end-to-end tests] [interfaces: additive SimRIS helper exports only] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — add helper wrappers that evaluate deterministic and stochastic SimRIS outputs directly from the published GUI presets.
- `risnet/channels/__init__.py` — export the new helpers.
- `tests/test_simris_channel.py` — add focused end-to-end coverage for the new published-case helpers, including outdoor Scenario 2.
- `tasks/test-suite.md` — record the new helper coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add additive published-case SimRIS helper wrappers
- [x] Add focused end-to-end tests for the published-case helpers
- [x] Verify focused tests and update the test map

### Review
- Completed: Added `evaluate_simris_los_published_case(...)` and `simulate_simris_published_case(...)` so production code can evaluate SimRIS deterministic or stochastic outputs directly from the published GUI presets without rebuilding geometry by hand. Exported both helpers through `risnet.channels` and added focused end-to-end coverage that exercises outdoor Scenario 2 through both helper paths.
- Out-of-scope flagged: I did not thread these helpers into CLI or scenario YAML flows; this batch keeps them as additive engine-layer helpers only.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: Published-case helpers now remove more boilerplate around the reference presets, but branch-by-branch stochastic equivalence with MATLAB still requires further tightening and deferred external verification.

## Task: Add Published SimRIS Network Builder
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the additive SimRIS network-builder helper, the focused builder tests, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: published SimRIS network builder, focused builder tests] [interfaces: additive SimRIS helper export only] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — add a helper that builds a `RISNetwork` directly from a published SimRIS GUI preset.
- `risnet/channels/__init__.py` — export the new helper.
- `tests/test_simris_channel.py` — add focused coverage for the builder and a deterministic channel run through the built network.
- `tasks/test-suite.md` — record the new builder coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add an additive published SimRIS network-builder helper
- [x] Add focused tests for builder parity and deterministic channel execution
- [x] Verify focused tests and update the test map

### Review
- Completed: Added `build_simris_published_network(...)` so production code can construct a `RISNetwork` directly from a published SimRIS GUI preset with sensible reference defaults for frequency, power, bandwidth, RIS quantization, and noise figure. Exported the helper through `risnet.channels` and added focused tests that verify parity with the indoor Scenario 1 reference network plus a deterministic `SimRISChannel` run through the built network.
- Out-of-scope flagged: I did not wire the builder into CLI/demo flows; this batch keeps it as an additive engine/helper API only.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The builder now centralizes published reference network construction, but it still serves the Python-side port only; full MATLAB numerical parity remains a separate deferred track.

## Task: Fix Published SimRIS Network Builder Frequency Consistency
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the RIS-frequency fix in the published network builder, the focused frequency assertions, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: published SimRIS network builder, focused frequency tests] [interfaces: additive helper behavior only] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — ensure the published network builder propagates the requested frequency to the RIS as well as the AP.
- `tests/test_simris_channel.py` — add focused assertions for RIS frequency parity at 28 GHz and 73 GHz.
- `tasks/test-suite.md` — record the new builder-frequency coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Propagate builder frequency consistently to the RIS node
- [x] Add focused builder-frequency tests
- [x] Verify focused tests and update the test map

### Review
- Completed: Fixed `build_simris_published_network(...)` so the requested frequency now propagates to the RIS node instead of leaving it at the core `add_ris()` default of `10e9`. Added focused tests that assert AP/RIS frequency parity for the default 28 GHz reference case and for a custom 73 GHz published preset.
- Out-of-scope flagged: I did not retrofit this frequency normalization into unrelated network-building helpers elsewhere in the repo; this batch only fixes the additive SimRIS published-network builder.
- Assumptions invalidated: The previous builder implementation silently inherited `add_ris()`'s default frequency, so the first published-network test was incomplete until RIS frequency parity was asserted directly.
- Known debt (acknowledged):
- Limitations: Published SimRIS reference builders are now frequency-consistent, but broader MATLAB numerical parity still depends on the remaining stochastic-port work and deferred external verification.

## Task: Add Published SimRIS Helper Consistency Checks
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the focused helper-consistency tests and the `tasks/test-suite.md` updates for this task.
Change budget: [files 3] [functions: focused SimRIS helper consistency tests] [interfaces: test coverage only] [state mutations: none]

### Scope
- `tests/test_simris_channel.py` — verify deterministic LOS parity between the published-case helper, the published network builder, and node-level evaluation across all four presets.
- `tasks/test-suite.md` — record the broader helper-consistency coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add focused deterministic helper-consistency tests across all four published presets
- [x] Verify focused tests and update the test map

### Review
- Completed: Added deterministic consistency tests proving that the published-case LOS helper, the published-network builder, and node-level LOS evaluation all return matching `H/G/D` results across indoor/outdoor Scenarios 1 and 2. This closes a drift risk between the additive production helpers that now exist around SimRIS presets.
- Out-of-scope flagged: This batch checks deterministic helper consistency only; it does not yet extend the same equivalence matrix to the stochastic helper path.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: Helper consistency is now enforced for the deterministic path across all four presets, but stochastic branch-by-branch parity with MATLAB remains a separate unresolved track.

## Task: Add Published SimRIS Stochastic Helper Consistency Checks
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the focused stochastic helper-consistency tests and the `tasks/test-suite.md` updates for this task.
Change budget: [files 3] [functions: focused SimRIS stochastic helper consistency tests] [interfaces: test coverage only] [state mutations: none]

### Scope
- `tests/test_simris_channel.py` — verify seeded stochastic parity between the published-case helper and the published-network builder plus node-level evaluation across all four presets.
- `tasks/test-suite.md` — record the broader stochastic helper-consistency coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add focused seeded stochastic helper-consistency tests across all four published presets
- [x] Verify focused tests and update the test map

### Review
- Completed: Added seeded stochastic consistency tests across all four published presets to prove that `simulate_simris_published_case(...)` and `build_simris_published_network(...)` plus `evaluate_simris_from_nodes(...)` produce the same `H/G/D`, MATLAB-style aliases, and stable LOS-indicator metadata under the same seed. This extends the earlier deterministic helper-consistency guard into the stochastic helper path.
- Out-of-scope flagged: I intentionally compare only stable scalar metadata fields (`los_indicator`) instead of raw metadata blobs, because the full metadata structure contains NumPy arrays that are not valid for direct `==` comparison.
- Assumptions invalidated: The first version of this test incorrectly assumed raw metadata dicts could be compared directly; verification showed that was a test bug, not an engine issue, so the assertion was tightened to stable scalar metadata.
- Known debt (acknowledged):
- Limitations: Stochastic helper consistency is now enforced across helpers for all four presets, but branch-by-branch MATLAB numerical parity is still a separate unresolved track.

## Task: Add Published SimRIS Adapter Helpers
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the additive published-case adapter helpers, the focused adapter-parity tests, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: published-case adapter helpers, focused adapter-parity tests] [interfaces: additive SimRIS helper exports only] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — add helper wrappers that return `ChannelEvaluation` directly for deterministic and stochastic published SimRIS presets.
- `risnet/channels/__init__.py` — export the new adapter helpers.
- `tests/test_simris_channel.py` — add focused parity tests against the standard adapters on top of a built published network.
- `tasks/test-suite.md` — record the new adapter-helper coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add additive published-case adapter helper wrappers
- [x] Add focused adapter-helper parity tests across all four presets
- [x] Verify focused tests and update the test map

### Review
- Completed: Added `evaluate_simris_channel_published_case(...)` and `evaluate_simris_stochastic_channel_published_case(...)` so published SimRIS presets can now return full `ChannelEvaluation` adapter results directly, not just raw tensors or built networks. Added parity tests across all four presets showing these helper wrappers match the standard `SimRISChannel` and `SimRISStochasticChannel` evaluations on top of the same built published network.
- Out-of-scope flagged: I did not add equivalent convenience helpers for the current Waveflow link-budget engine; this batch stays scoped to the additive SimRIS port surface.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: Published-case adapter helpers now complete the preset API stack, but they still sit on top of the current Python SimRIS implementation rather than external MATLAB-verified outputs.

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

## Task: Update FUTURE.md with QRIS comparison and current status
Mode: Standard
Risk: Low
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: Revert the FUTURE.md edits for this task.
Change budget: [files 2] [functions: none] [interfaces: documentation only] [state mutations: none]

### Scope
- `FUTURE.md` — add Phase 7b GSCM channel engine section (QRIS-inspired), update Phase 6 current status, update Known Technical Debt, and bring Immediate Action Items to 2026-05-08 state.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add Phase 7b GSCM channel engine section
- [x] Update Phase 6 current status
- [x] Update Known Technical Debt (print(), SNR/link-budget)
- [x] Bring Immediate Action Items to current state

### Review
- Completed: Added Phase 7b GSCM channel engine section with implementation spec, computational design rationale (precomputed scenario channel), integration point, and current status linking back to the existing SimRIS precursor. Updated Phase 6 status to reflect that parallel CLI work is largely done but the kernel itself is not started. Updated Known Technical Debt to mark print() migration as resolved and SNR/link-budget as partially resolved. Brought Immediate Action Items to 2026-05-08 state covering 20 items.
- Out-of-scope flagged: No code was changed; this is documentation only.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: FUTURE.md now reflects the QRIS investigation findings as design intent for Phase 7b; the implementation has not started.

## Task: Align SimRIS Raw Helper Preflight Validation
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the additive raw-helper preflight wiring in `risnet/channels/simris.py`, the focused SimRIS helper tests, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: `evaluate_simris_los_from_nodes`, `evaluate_simris_los_published_case`, `evaluate_simris_from_nodes`, `simulate_simris_published_case`, focused SimRIS helper tests] [interfaces: additive `validate_preflight` / `error_on_invalid` options on existing raw helper APIs] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — add optional preflight validation/reporting parity to the raw node-level and published-case SimRIS helper APIs.
- `tests/test_simris_channel.py` — add focused tests for raw helper raise/report/warning behavior.
- `tasks/test-suite.md` — record the expanded SimRIS helper-preflight coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Wire optional preflight validation into the raw node-level and published-case SimRIS helper APIs
- [x] Add focused raw-helper preflight tests for raise/report/warning behavior
- [x] Verify focused SimRIS and link-budget suites and review scope

### Review
- Completed: Added optional `validate_preflight` and `error_on_invalid` controls to the raw deterministic/stochastic node helpers and the published-case raw helpers, so they now mirror the adapter path by either raising on invalid geometry or attaching a non-blocking `validation` payload. Expanded `tests/test_simris_channel.py` with focused coverage for invalid raw-helper raises, non-blocking validation reports, and published-case warning/error surfacing. Updated `tasks/test-suite.md` to record the broader helper-preflight coverage.
- Out-of-scope flagged: I did not make preflight validation mandatory by default, and I did not touch the external MATLAB/Octave KIV work or unrelated new test files already present in the working tree.
- Assumptions invalidated: The first version of the new tests assumed shorter validation strings than the actual helper emits; verification exposed that mismatch and the tests were tightened to match the real messages and substring semantics.
- Known debt (acknowledged):
- Limitations: This closes the parity gap between Python helper call paths, but it still does not provide cross-runtime MATLAB/Octave equivalence proof for the full SimRIS stochastic model.

## Task: Align SimRIS Primitive Helper Preflight Validation
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the additive primitive-helper preflight wiring in `risnet/channels/simris.py`, the focused SimRIS primitive tests, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: `evaluate_simris_los_reference`, `simulate_simris_channels`, focused SimRIS primitive tests] [interfaces: additive `validate_preflight` / `error_on_invalid` options on existing primitive helper APIs] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — add optional preflight validation/reporting parity to the base deterministic and stochastic SimRIS helper APIs.
- `tests/test_simris_channel.py` — add focused tests for primitive helper warning/raise behavior.
- `tasks/test-suite.md` — record the expanded primitive-helper preflight coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Wire optional preflight validation into the base deterministic and stochastic SimRIS helper APIs
- [x] Add focused primitive-helper tests for warning/raise behavior
- [x] Verify focused SimRIS and link-budget suites and review scope

### Review
- Completed: Added optional `validate_preflight` and `error_on_invalid` controls to the base deterministic formula helper and the seeded stochastic tensor generator, so the lowest-level SimRIS APIs now mirror the adapter and wrapper layers by either raising on invalid geometry or attaching a `validation` payload. Expanded `tests/test_simris_channel.py` with focused coverage for a published-band warning on `evaluate_simris_los_reference(...)` and invalid-geometry raising on `simulate_simris_channels(...)`. Updated `tasks/test-suite.md` to record the broader primitive-helper coverage.
- Out-of-scope flagged: I did not remove the duplicated validation calls in upper wrappers, and I did not touch the external MATLAB/Octave KIV work or unrelated new test files already present in the working tree.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This makes the Python-side SimRIS API surface internally consistent, but it still does not prove numerical parity against the full MATLAB simulator without external reference execution.

## Task: Cover SimRIS Published-Case Adapter Preflight Paths
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the focused published-case adapter tests and the `tasks/test-suite.md` updates for this task.
Change budget: [files 3] [functions: focused SimRIS published-case adapter tests] [interfaces: none; coverage only] [state mutations: none]

### Scope
- `tests/test_simris_channel.py` — add focused preflight coverage for the published-case deterministic and stochastic adapter helpers.
- `tasks/test-suite.md` — record the added published-case adapter preflight coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add focused preflight warning/error tests for the published-case adapter helpers
- [x] Verify focused SimRIS and link-budget suites and review scope

### Review
- Completed: Added focused coverage proving that the published-case deterministic adapter helper surfaces non-blocking reference-band warnings and that the published-case stochastic adapter helper surfaces invalid preflight errors on its public `ChannelEvaluation` result path. Updated `tasks/test-suite.md` to record the additional published-case adapter entrypoint coverage.
- Out-of-scope flagged: This batch did not change SimRIS engine behavior; it only tightened coverage on already-supported adapter options.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: The published-case adapter entrypoints are now covered for preflight reporting, but full stochastic numerical parity against MATLAB remains outside the current environment.

## Task: Deduplicate SimRIS Wrapper Preflight Flow
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the wrapper-helper delegation edits in `risnet/channels/simris.py` and this task entry.
Change budget: [files 2] [functions: `evaluate_simris_los_from_nodes`, `evaluate_simris_los_published_case`, `evaluate_simris_from_nodes`, `simulate_simris_published_case`] [interfaces: none; internal delegation only] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — remove duplicated preflight-validation logic from wrapper helpers now that the primitive helpers support the same options directly.
- `tasks/todo.md` — record this task.

### Steps
- [x] Replace wrapper-local validation with direct pass-through to the primitive helper preflight options
- [x] Verify focused SimRIS and link-budget suites and review scope

### Review
- Completed: Simplified the node-level and published-case raw wrapper helpers so they now pass `validate_preflight` and `error_on_invalid` directly down to `evaluate_simris_los_reference(...)` and `simulate_simris_channels(...)` instead of re-running the same validation logic locally. This keeps the wrapper behavior unchanged while removing one obvious source of future drift.
- Out-of-scope flagged: I did not change the adapter-level preflight duplication in this batch, because that would touch a different layer and was not required to keep the helper APIs consistent.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This is an internal cleanup only; it reduces duplication in the raw helper layer but does not change the remaining MATLAB parity gap.

## Task: Deduplicate SimRIS Adapter Preflight Flow
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the adapter delegation edits in `risnet/channels/simris.py` and this task entry.
Change budget: [files 2] [functions: `SimRISChannel.evaluate`, `SimRISStochasticChannel.evaluate`] [interfaces: none; internal delegation only] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — remove duplicated preflight-validation logic from the deterministic and stochastic adapters now that the lower helper layers return the same validation payloads directly.
- `tasks/todo.md` — record this task.

### Steps
- [x] Replace adapter-local validation with direct pass-through to helper preflight options
- [x] Verify focused SimRIS and link-budget suites and review scope

### Review
- Completed: Simplified both SimRIS adapters so they now rely on the validation payload already produced by `evaluate_simris_los_from_nodes(...)` and `evaluate_simris_from_nodes(...)` instead of re-running `_maybe_run_preflight_validation(...)` locally. This keeps adapter results unchanged while removing another layer of duplicated validation flow.
- Out-of-scope flagged: I did not alter the published-case adapter wrappers beyond inheriting the adapter simplification, and I did not touch the external MATLAB/Octave KIV work.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This is internal delegation cleanup only; it reduces drift risk but does not close the remaining stochastic MATLAB parity gap.

## Task: Align SimRIS Stochastic Adapter Result Contract
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the stochastic adapter result-field edit in `risnet/channels/simris.py`, the focused SimRIS adapter test, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: `SimRISStochasticChannel.evaluate`, focused SimRIS stochastic adapter tests] [interfaces: additive result field parity for stochastic adapter] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — add `noise_power_dBm` to the stochastic SimRIS adapter result so it matches the deterministic adapter contract.
- `tests/test_simris_channel.py` — add focused coverage for the stochastic adapter noise-power contract.
- `tasks/test-suite.md` — record the added stochastic adapter contract coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add `noise_power_dBm` to the stochastic SimRIS adapter result
- [x] Add focused stochastic adapter contract test
- [x] Verify focused SimRIS and link-budget suites and review scope

### Review
- Completed: Extended the stochastic SimRIS adapter result with `noise_power_dBm`, bringing it into line with the deterministic adapter and making the `snr_dB = pwr_dBm - noise_power_dBm` relationship explicit on both paths. Added focused coverage to confirm the metric is present and numerically consistent with the published default bandwidth/noise-figure setup. Updated `tasks/test-suite.md` to record the new adapter-contract parity.
- Out-of-scope flagged: I did not change the raw tensor helpers in this batch because the inconsistency was at the adapter contract layer only.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This closes a Python-side result-contract gap, but it does not address the remaining stochastic MATLAB parity work.

## Task: Add Self-Describing Metadata to Stochastic SimRIS Results
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the stochastic helper result-metadata edit in `risnet/channels/simris.py`, the focused SimRIS result-metadata assertion, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: `simulate_simris_channels`, focused SimRIS stochastic helper test] [interfaces: additive metadata fields on stochastic helper output] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — add self-describing configuration metadata to stochastic SimRIS helper results.
- `tests/test_simris_channel.py` — assert that the raw stochastic helper now exposes the configuration metadata.
- `tasks/test-suite.md` — record the added stochastic result-metadata coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add configuration metadata to the stochastic SimRIS helper result
- [x] Add focused assertions for the stochastic helper metadata contract
- [x] Verify focused SimRIS and link-budget suites and review scope

### Review
- Completed: Extended the stochastic SimRIS helper result with `frequency_GHz`, `environment`, `scenario`, `array_type`, and `num_realizations`, making the raw tensor output self-describing in the same way the deterministic helper already is. Added focused assertions to lock this metadata contract in `tests/test_simris_channel.py`. Updated `tasks/test-suite.md` to record the new coverage.
- Out-of-scope flagged: I did not add per-realization path-loss summaries in this batch; this change was limited to stable configuration metadata already known at call time.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This improves Python-side result introspection, but it does not close the remaining stochastic MATLAB parity gap.

## Task: Add Per-Realization Gain Summaries to Stochastic SimRIS Helpers
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the stochastic helper gain-summary edits in `risnet/channels/simris.py`, the focused SimRIS gain-summary tests, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: `simulate_simris_channels`, `SimRISStochasticChannel.evaluate`, focused SimRIS gain-summary tests] [interfaces: additive per-realization summary fields on stochastic helper output] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — add per-realization effective channel-gain summaries to the stochastic helper output and reuse them in the stochastic adapter.
- `tests/test_simris_channel.py` — add focused coverage for the new gain-summary contract and adapter reuse.
- `tasks/test-suite.md` — record the added stochastic gain-summary coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add per-realization gain summaries to the stochastic helper output
- [x] Reuse the helper-supplied first-realization gain in the stochastic adapter
- [x] Add focused tests and verify focused SimRIS and link-budget suites

### Review
- Completed: Extended `simulate_simris_channels(...)` with per-realization `channel_gain_linear` and `channel_gain_dB` summaries, then simplified `SimRISStochasticChannel.evaluate(...)` to reuse the first realization from that helper output instead of recomputing the same effective gain independently. Added focused coverage to verify the helper summaries match a manual reconstruction and that the stochastic adapter’s public `gain_linear` / `gain_dBi` now align with the first stochastic realization. Updated `tasks/test-suite.md` to record the added coverage.
- Out-of-scope flagged: I did not add per-realization path-gain/path-loss breakdowns for each hop in this batch; the scope was limited to the effective end-to-end gain summary already used by the adapter.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This closes another Python-side duplication gap, but it does not resolve the remaining MATLAB stochastic parity work.

## Task: Add Hop-Level LOS Metadata to Stochastic SimRIS Links
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the hop-metadata edits in `risnet/channels/simris.py`, the focused SimRIS metadata-parity test, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: `_generate_tx_ris_channel`, `_generate_ris_rx_channel`, `_generate_direct_channel`, focused SimRIS metadata tests] [interfaces: additive hop-level metadata fields on stochastic results] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — add per-hop LOS metadata (`distance_m`, `los_path_gain_dB`, `los_path_gain_linear`) to the stochastic SimRIS link metadata when that branch is active.
- `tests/test_simris_channel.py` — add focused parity coverage against the deterministic helper for the LOS-only case.
- `tasks/test-suite.md` — record the added hop-level metadata coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add hop-level distance and LOS path-gain metadata to the stochastic SimRIS link generators
- [x] Add focused LOS-only metadata parity test against the deterministic helper
- [x] Verify focused SimRIS and link-budget suites and review scope

### Review
- Completed: Extended the stochastic link metadata for Tx→RIS, RIS→Rx, and Tx→Rx so each branch now records `distance_m`, and when LOS is active also records `los_path_gain_dB` and `los_path_gain_linear`. Added a focused LOS-only parity test showing that these stochastic metadata summaries match the deterministic helper’s published path-gain outputs for the same geometry. Updated `tasks/test-suite.md` to record the new coverage.
- Out-of-scope flagged: I did not add equivalent NLOS aggregate path-gain metadata in this batch because there is not a single deterministic per-hop NLOS scalar in the current stochastic formulation.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This improves stochastic introspection and deterministic parity for LOS metadata, but it does not close the remaining MATLAB stochastic parity work.

## Task: Expose Deterministic SimRIS Hop Metadata Symmetrically
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the deterministic metadata edit in `risnet/channels/simris.py`, the focused SimRIS metadata-parity assertions, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: `evaluate_simris_los_reference`, focused SimRIS metadata tests] [interfaces: additive deterministic metadata field] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — expose deterministic hop-level metadata (`tx_ris`, `ris_rx`, `direct`) alongside the existing deterministic SimRIS summaries.
- `tests/test_simris_channel.py` — extend the LOS-only metadata parity test so deterministic and stochastic helpers are both checked explicitly.
- `tasks/test-suite.md` — record the deterministic/stochastic metadata symmetry coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add deterministic hop metadata to `evaluate_simris_los_reference(...)`
- [x] Extend focused metadata parity assertions across deterministic and stochastic helpers
- [x] Verify focused SimRIS and link-budget suites and review scope

### Review
- Completed: Extended the deterministic SimRIS helper with a `metadata` block containing `tx_ris`, `ris_rx`, and `direct` hop summaries, reusing the same distance and LOS path-gain information already available from the lower link generators. Tightened the existing LOS-only parity test so deterministic and stochastic helpers are both checked explicitly for matching hop-level metadata. Updated `tasks/test-suite.md` to record the new symmetry coverage.
- Out-of-scope flagged: I did not add stochastic-style per-realization wrapper lists to the deterministic helper; it remains a single deterministic evaluation with a single metadata block.
- Assumptions invalidated: An initial edit tried to construct the no-direct-path metadata before `d_tx_rx` had been computed; this was corrected immediately before verification.
- Known debt (acknowledged):
- Limitations: Deterministic and stochastic LOS introspection are now more symmetric, but full stochastic MATLAB parity remains the main unresolved work.

## Task: Add NLOS Structure Summaries to Stochastic SimRIS Metadata
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the NLOS-summary edits in `risnet/channels/simris.py`, the focused SimRIS metadata test, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: `_generate_tx_side_scatterers`, `_generate_ris_side_scatterers`, `_generate_tx_ris_channel`, `_generate_ris_rx_channel`, `_generate_direct_channel`, focused SimRIS metadata tests] [interfaces: additive NLOS summary fields on stochastic metadata] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — expose stable NLOS structure summaries (`nlos_cluster_count`, `nlos_subray_count`, `nlos_active_scatterer_count`) on stochastic link metadata.
- `tests/test_simris_channel.py` — add focused coverage for indoor and outdoor stochastic metadata summaries.
- `tasks/test-suite.md` — record the added NLOS metadata coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Extend scatterer-generation metadata with cluster and sub-ray counts
- [x] Surface stable NLOS summary counts on stochastic link metadata
- [x] Add focused metadata coverage and verify focused SimRIS and link-budget suites

### Review
- Completed: Extended the stochastic scatterer-generation metadata to retain cluster counts and sub-ray counts, then surfaced stable NLOS summaries (`nlos_cluster_count`, `nlos_subray_count`, `nlos_active_scatterer_count`) on the Tx→RIS, RIS→Rx, and direct-link metadata where NLOS branches are active. Added focused tests covering both indoor shared-cluster behavior and outdoor scattered branches. Updated `tasks/test-suite.md` to record the new stochastic metadata coverage.
- Out-of-scope flagged: I did not invent a single NLOS path-gain scalar summary in this batch, because that would flatten a multi-scatter stochastic branch into a misleading metric.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This improves stochastic structure introspection considerably, but the remaining work is still the deeper MATLAB parity of the stochastic physics itself.

## Task: Add LOS-Component Summaries to Stochastic SimRIS Results
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the stochastic LOS-summary edits in `risnet/channels/simris.py`, the focused SimRIS LOS-summary tests, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: `simulate_simris_channels`, focused SimRIS LOS-summary tests] [interfaces: additive per-realization LOS summary arrays on stochastic helper output] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — add per-realization LOS-component summaries (`los_path_gain_*`, `theta_*`, `ris_pattern_*`) to the stochastic helper output.
- `tests/test_simris_channel.py` — add focused coverage for deterministic parity in the LOS-only case and `NaN` semantics when LOS is absent.
- `tasks/test-suite.md` — record the added stochastic LOS-summary coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add per-realization LOS-component summary arrays to the stochastic helper output
- [x] Add focused tests for deterministic parity and explicit no-LOS `NaN` behavior
- [x] Verify focused SimRIS and link-budget suites and review scope

### Review
- Completed: Extended the stochastic SimRIS helper with per-realization LOS-component summary arrays for path gain, RIS incidence/departure elevation, and RIS element-pattern gain. Added focused tests proving that the LOS-only stochastic case matches the deterministic helper and that these arrays resolve to `NaN` when the LOS component is forced off. Updated `tasks/test-suite.md` to record the new stochastic summary coverage.
- Out-of-scope flagged: I did not expose equivalent top-level NLOS path-gain arrays because the current stochastic model does not reduce the NLOS branch to a single physically honest scalar per hop.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This further improves Python-side introspection and deterministic/stochastic symmetry, but the remaining unresolved work is still the deeper MATLAB parity of the stochastic model.

## Task: Complete Stochastic LOS Path-Loss Summary Symmetry
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the stochastic LOS path-loss summary edit in `risnet/channels/simris.py`, the focused SimRIS LOS-summary assertions, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: `simulate_simris_channels`, focused SimRIS LOS-summary tests] [interfaces: additive per-realization LOS path-loss arrays on stochastic helper output] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — add `los_path_loss_*_dB` arrays alongside the existing stochastic LOS path-gain summaries.
- `tests/test_simris_channel.py` — extend LOS-summary coverage for deterministic parity and explicit `NaN` behavior on the new path-loss arrays.
- `tasks/test-suite.md` — record the added stochastic LOS path-loss coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add per-realization LOS path-loss arrays to the stochastic helper output
- [x] Extend focused LOS-summary tests for deterministic parity and no-LOS `NaN` behavior
- [x] Verify focused SimRIS and link-budget suites and review scope

### Review
- Completed: Extended the stochastic SimRIS helper with `los_path_loss_ap_ris_dB`, `los_path_loss_ris_ue_dB`, and `los_path_loss_direct_dB`, completing the symmetry with the existing LOS path-gain summaries and the deterministic helper’s top-level path-loss fields. Tightened the LOS-summary tests so they now cover deterministic parity and explicit `NaN` behavior for the new path-loss arrays. Updated `tasks/test-suite.md` to record the new coverage.
- Out-of-scope flagged: I did not add top-level non-LOS path-loss arrays, because the current stochastic NLOS formulation still does not reduce to a single physically honest scalar per hop.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This likely closes the last obvious Python-side LOS-summary contract gap; the remaining unresolved work is the deeper stochastic MATLAB parity.

## Task: Align Public Stochastic Adapter Scalar LOS Summaries
Mode: Standard
Risk: Medium
Confidence: Stable
Operational risk: Contained / Trivial
Rollback plan: Revert the stochastic adapter scalar-summary aliases in `risnet/channels/simris.py`, the focused SimRIS adapter tests, and the `tasks/test-suite.md` updates for this task.
Change budget: [files 4] [functions: `SimRISStochasticChannel.evaluate`, focused SimRIS adapter scalar-summary tests] [interfaces: additive scalar alias parity on public stochastic adapter results] [state mutations: none]

### Scope
- `risnet/channels/simris.py` — expose first-realization scalar aliases for LOS path gain/loss, RIS angles, and RIS pattern summaries on the public stochastic adapter result.
- `tests/test_simris_channel.py` — add focused coverage for deterministic parity and no-LOS `NaN` semantics on those scalar aliases.
- `tasks/test-suite.md` — record the added public stochastic adapter coverage.
- `tasks/todo.md` — record this task.

### Steps
- [x] Add first-realization scalar LOS-summary aliases to the public stochastic adapter result
- [x] Add focused tests for deterministic parity and no-LOS `NaN` behavior
- [x] Fix the scalar-alias override bug exposed during verification and rerun focused suites

### Review
- Completed: Extended the public stochastic adapter result with first-realization scalar aliases for LOS path gain/loss, RIS angles, and RIS pattern summaries so the public stochastic contract now more closely mirrors the deterministic adapter. Added focused tests for deterministic parity and explicit no-LOS `NaN` semantics. Verification exposed a real bug where the new scalar aliases were being overwritten by `**tensors`; the result-dict order was corrected so the scalar aliases now survive as intended. Updated `tasks/test-suite.md` to record the new coverage.
- Out-of-scope flagged: I did not add analogous scalar aliases for NLOS structure summaries on the adapter result because those are already available through the nested metadata and do not need lossy flattening.
- Assumptions invalidated: The first implementation assumed the new scalar aliases would survive the result merge order, but `**tensors` was overriding them; this was fixed before completion.
- Known debt (acknowledged):
- Limitations: This likely closes the remaining obvious public adapter contract gap on the Python side; the remaining unresolved work is the deeper stochastic MATLAB parity.

## Task: Verify Additional SimRIS Formula and Physics Suites
Mode: Standard
Risk: Low
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: N/A — verification only.
Change budget: [files 1] [functions: none] [interfaces: none] [state mutations: none]

### Scope
- `tasks/todo.md` — record the review/run of the existing auxiliary SimRIS test suites.

### Steps
- [x] Inspect `tests/test_simris_paper_formulas.py` and `tests/test_simris_physics_regression.py`
- [x] Run both suites and capture their status
- [x] Confirm whether `tasks/test-suite.md` already records them accurately

### Review
- Completed: Reviewed `tests/test_simris_paper_formulas.py` and `tests/test_simris_physics_regression.py`, then ran both directly. `test_simris_paper_formulas.py` passed with `34 passed in 0.50s`, and `test_simris_physics_regression.py` passed with `28 passed in 0.52s`. `tasks/test-suite.md` already contained both files in the inventory and coverage sections, so no update there was needed.
- Out-of-scope flagged: I did not merge these auxiliary checks into the main `test_simris_channel.py` suite; they remain separate by design because they pin paper formulas and frozen physics values.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This batch only verified the auxiliary suites and their documentation status; it did not change engine behavior or close any additional MATLAB-parity gaps.

## Task: Update FUTURE.md with Official SimRIS Engine Fallback Policy
Mode: Standard
Risk: Low
Confidence: Stable
Operational risk: Local / Trivial
Rollback plan: Revert the `FUTURE.md` wording for this task.
Change budget: [files 2] [functions: none] [interfaces: planning/documentation only] [state mutations: none]

### Scope
- `FUTURE.md` — clarify that SimRIS should become the official engine for supported scenarios, while unsupported requests fall back to `LinkBudgetChannel` explicitly at the engine boundary.
- `tasks/todo.md` — record this task.

### Steps
- [x] Update the Phase 7b integration sequence with explicit fallback rules
- [x] Update the engine policy and definition-of-done bullets

### Review
- Completed: Updated `FUTURE.md` so the SimRIS integration plan now states that SimRIS should become the official engine for supported channel-aware workflows, while unsupported configurations fall back cleanly to `LinkBudgetChannel` with an explicit reason surfaced in metadata/diagnostics. The plan now forbids silent engine mixing and requires capability checks at the engine boundary.
- Out-of-scope flagged: I did not implement the fallback behavior itself in code; this task only clarified the integration policy in the roadmap.
- Assumptions invalidated: None.
- Known debt (acknowledged):
- Limitations: This is roadmap clarification only; code integration, capability checks, and fallback diagnostics still need implementation.
