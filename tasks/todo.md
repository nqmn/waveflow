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
