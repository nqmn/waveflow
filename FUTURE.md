# RISNet v3 - Future Architecture Direction

## Implementability Verdict

RISNet v3 is implementable in this codebase, but it should be delivered as an
incremental architecture migration rather than a direct folder reshuffle or
rewrite.

The current repository already contains useful foundations for the v3 direction:

- `core/nodes.py` provides the existing `AccessPoint`, `RIS`, and `UE` node model.
- `core/network.py` provides the current AP -> RIS -> UE simulation path.
- `core/environment.py` isolates basic walls, bounds, and line-of-sight checks.
- `core/waveform.py` already contains OFDM, propagation channel, antenna array,
  and RIS reflection primitives.
- `controller/pathfinding` and `controller/beamsweeping` already use registry
  patterns that can evolve into a broader plugin ecosystem.
- `controller/beamsweeping/ml` already contains ML-guided beam sweeping and
  dataset/model tooling.
- `app/` is already an interface layer rather than the core simulator, which
  supports the headless-first goal. It still has some coupling to CLI
  serialization helpers through `app/state_manager.py`.
- `examples/` and notebooks already exist, which supports notebook-native
  research workflows.

The main blocker is not missing RF math. The main blocker is coupling:
`RISNetwork.connect()` currently combines topology lookup, phase computation,
FOV validation, link-budget calculation, fading, feedback handling, active-link
state updates, and API serialization. This method should be decomposed before
introducing the v3 kernel, entity-component model, or spatial channel engine.

Packaging also needs cleanup before a full v3 package layout. `pyproject.toml`
currently packages only `risnet`, while most implementation modules live as
top-level packages such as `core`, `controller`, `cli`, `app`, `config`, and
`utils`. After editable installation, importing `risnet` from outside the
repository fails because `risnet/__init__.py` imports unpackaged top-level
modules such as `core`. The console entry point also references
`risnet.__main__:main`, but there is no `risnet/__main__.py`.

## Vision

RISNet should evolve from:

```text
RIS network simulator
```

into:

```text
Programmable RF intelligence and electromagnetic environment platform
```

The long-term objective is not to compete directly with CST Studio or HFSS in
full-wave electromagnetic simulation.

Instead, RISNet should become:

- AI-native RF simulation platform
- programmable wireless environment framework
- phased-array experimentation platform
- RIS + MIMO + ISAC research toolkit
- notebook-native research environment
- scalable RF digital twin runtime

## Core Philosophy

RISNet v3 should be:

- headless-first
- notebook-native
- CLI-driven
- plugin-oriented
- tensorized
- event-driven
- extensible by design
- AI-native

The architecture should prioritize:

1. composability
2. reproducibility
3. experimentation speed
4. scalable abstractions
5. future-proof simulation primitives

## Current State

The current architecture is primarily:

```text
AP -> RIS -> UE
```

centric.

The future architecture should become:

```text
wave-centric
array-centric
environment-centric
```

where RIS is treated as:

```text
passive phased array
```

instead of a special hardcoded entity.

## Migration Principle

Do not replace `AccessPoint`, `RIS`, `UE`, or `RISNetwork` immediately.

Instead:

1. Preserve the existing public API and CLI behavior.
2. Extract reusable simulation primitives from existing classes.
3. Add adapter layers that let old node objects expose new components.
4. Move new capabilities into v3-style modules.
5. Retire old internals only after tests and examples have migrated.

## Core Architectural Goals

### 1. Simulation Kernel

Introduce a dedicated simulation runtime kernel.

Proposed structure:

```text
kernel/
├── scheduler/
├── runtime/
├── events/
├── execution/
└── registry/
```

Responsibilities:

- event scheduling
- runtime execution
- dependency graph management
- simulation clock
- deterministic reproducibility
- future distributed execution

Implementation note:

Start with a minimal deterministic event loop. Do not start with distributed
execution. The first useful kernel should support scheduled mobility updates,
channel refreshes, beam updates, and metric collection.

### 2. Entity-Component Architecture

Move away from rigid node-based inheritance.

Current model:

```python
AccessPoint
RIS
UE
```

Future model:

```python
Entity(
    components=[
        Position(),
        RFEmitter(),
        RFReceiver(),
        AntennaArray(),
        Beamformer(),
        MobilityModel(),
    ]
)
```

This enables:

- RIS
- phased arrays
- radar
- ISAC
- localization
- mobile arrays
- SDR integration
- cooperative sensing

Implementation note:

Introduce components as additive wrappers first. Existing `AccessPoint`, `RIS`,
and `UE` should be adaptable into entities rather than deleted. For example:

- `AccessPoint` maps to `Position + RFEmitter + Antenna`
- `UE` maps to `Position + RFReceiver + FeedbackReporter`
- `RIS` maps to `Position + AntennaArray + PassiveReflector + Quantizer`

### 3. Phased Array Core Support

Phased arrays should become a first-class primitive.

Proposed structure:

```text
arrays/
├── geometry/
├── steering/
├── beamforming/
├── calibration/
├── codebooks/
└── visualization/
```

Planned support:

- ULA
- UPA
- circular arrays
- sparse arrays
- conformal arrays
- analog beamforming
- digital beamforming
- hybrid beamforming
- adaptive beamforming
- RL-based beamforming
- steering vectors
- array factor computation
- codebooks
- polarization
- calibration
- mutual coupling
- beam pattern analysis

Implementation note:

This is one of the most immediately implementable parts. Existing logic in
`core/waveform.py`, `core/nodes.py`, `core/physics.py`, and
`controller/ris_phase` can be extracted into reusable array modules.

### 4. Spatial Channel Engine

Move from link-based propagation toward spatial channel modeling.

Proposed structure:

```text
channels/
├── spatial/
├── fading/
├── mimo/
├── raytracing/
└── stochastic/
```

Planned features:

- AoA/AoD modeling
- multipath propagation
- Doppler effects
- delay spread
- polarization effects
- mobility-aware fading
- MIMO channels
- RIS-assisted channels

Implementation note:

Start with a `ChannelModel` protocol and a `LinkBudgetChannel` adapter around
the current `Physics` and `RISNetwork.connect()` behavior. Then add spatial and
MIMO models without breaking current tests.

### 5. Environment Scene Graph

Replace the simple wall/obstacle system with a scene graph architecture.

Proposed structure:

```text
world/
├── geometry/
├── materials/
├── actors/
├── mobility/
├── terrain/
├── weather/
└── sensors/
```

Material properties:

- permittivity
- conductivity
- reflectivity
- roughness
- scattering
- absorption

Implementation note:

Keep `Environment` and `Wall` as compatibility objects. Add a `Scene` model
that can import/export current wall data. Avoid forcing 3D dependencies such as
Open3D, Trimesh, or PyVista into the base install.

### 6. Signal Flow Architecture

Waveform simulation should evolve into graph-based signal processing.

Example pipeline:

```text
Signal Source
 -> Modulator
 -> Channel
 -> Array Processing
 -> Beamforming
 -> Receiver
 -> Decoder
 -> Metrics
```

Proposed structure:

```text
signals/
├── modulation/
├── waveform/
├── ofdm/
├── coding/
├── synchronization/
└── pipelines/
```

Implementation note:

Existing waveform primitives can move behind a simple pipeline interface before
adding GNU Radio-style graph execution.

### 7. AI-Native Runtime

RISNet should evolve into a reinforcement-learning-ready environment.

Proposed structure:

```text
ai/
├── rl/
├── datasets/
├── optimization/
├── agents/
└── training/
```

Planned features:

- observation spaces
- action spaces
- reward engines
- online learning hooks
- dataset export
- replay buffers
- multi-agent coordination

Gym-compatible API:

```python
obs, reward, done, info = env.step(action)
```

Implementation note:

Start with a small adapter around existing beam-sweeping and SNR feedback. Do
not require Gymnasium, PyTorch, or JAX in the base install. Put ML/RL backends
behind optional extras.

### 8. Event-Driven Simulation

Introduce a discrete-event simulation runtime.

Proposed structure:

```text
runtime/
├── clock/
├── events/
├── scheduling/
└── synchronization/
```

Planned features:

- mobility evolution
- scheduling
- traffic simulation
- synchronization timing
- online adaptation
- time-varying channels

Implementation note:

This should depend on the kernel and scenario APIs. It should not be embedded
inside `RISNetwork.connect()`.

### 9. Notebook-Native Research Workflow

RISNet v3 should prioritize notebook workflows over GUI-first development.

Planned notebook collections:

```text
notebooks/
├── beamforming/
├── ris/
├── phased_arrays/
├── localization/
├── radar/
├── isac/
├── rl/
└── benchmarks/
```

Goals:

- rapid experimentation
- reproducibility
- visualization
- parameter sweeps
- ML integration
- publication workflows

Implementation note:

Examples should be converted into scenario-backed notebooks where possible.
Notebook dependencies should remain optional.

### 10. CLI-First Workflow

RISNet should remain headless-first.

Example future CLI:

```bash
risnet scenario run urban.yaml
risnet benchmark run massive_mimo
risnet plugin list
risnet array plot ula.yaml
risnet shell
```

Planned tools:

- Typer
- Rich
- Textual

Implementation note:

The current CLI is `cmd.Cmd`-based and large. Add Typer commands beside the
current CLI first, then gradually route old commands through new service APIs.

### 11. Plugin Ecosystem

RISNet should evolve toward a universal plugin architecture.

Proposed structure:

```text
plugins/
├── propagation/
├── arrays/
├── optimization/
├── channels/
├── datasets/
└── visualization/
```

Plugin types:

- propagation models
- channel models
- beamforming strategies
- optimization algorithms
- datasets
- visualization modules
- hardware drivers
- waveform pipelines

Implementation note:

The beamsweeping registry is a better model than the pathfinding singleton. Use
explicit registration metadata, aliases, and conflict detection. Avoid global
state where reproducibility matters.

### 12. Hardware Abstraction Layer

Future support for hardware-in-the-loop experimentation.

Proposed structure:

```text
devices/
├── sdr/
├── drivers/
├── streaming/
└── synchronization/
```

Planned integrations:

- GNU Radio
- USRP
- BladeRF
- HackRF
- RTL-SDR
- SoapySDR

Implementation note:

Keep this out of the base runtime. Hardware support should be optional,
interface-driven, and mockable in tests.

### 13. Tensorized Compute Backend

RISNet should move toward tensorized simulation.

Planned backends:

- NumPy
- CuPy
- PyTorch
- JAX

Goals:

- GPU acceleration
- vectorized propagation
- scalable phased arrays
- differentiable simulation
- AI-native execution

Implementation note:

Start with a backend protocol and NumPy implementation. Avoid rewriting all
math for GPU before array/channel APIs are stable.

### 14. Visualization Strategy

Visualization should remain modular and optional.

Terminal visualization:

- Rich dashboards
- Textual TUI
- runtime monitoring

Notebook visualization:

- Plotly
- PyVista
- Open3D

Future GUI:

- optional web dashboards
- optional 3D visualizers
- optional collaborative interfaces

Implementation note:

The existing Flask app should remain an interface layer, not the owner of
simulation state or simulation logic.

### 15. Differentiable RF Simulation

Long-term research direction.

Future goals:

- learnable beamforming
- differentiable RIS optimization
- end-to-end PHY learning
- gradient-based RF optimization

Potential backends:

- PyTorch
- JAX

Implementation note:

This is a later-stage goal. It depends on tensorized arrays, spatial channels,
and pure functions with minimal hidden mutable state.

## Proposed Future Folder Structure

Target structure:

```text
risnet/
├── kernel/
├── runtime/
├── world/
├── physics/
├── arrays/
├── channels/
├── signals/
├── optimization/
├── ai/
├── devices/
├── visualization/
├── scenarios/
├── benchmarks/
├── notebooks/
├── plugins/
├── interfaces/
└── cli/
```

Implementation note:

Do not move every existing top-level package at once. First fix packaging so
the project can reliably install and run tests. Then migrate modules in slices.

## Recommended Technology Stack

Core:

| Purpose | Tool |
| --- | --- |
| CLI | Typer |
| Terminal UI | Rich |
| TUI | Textual |
| Notebook | Jupyter |
| Configs | Pydantic |
| Serialization | YAML |

Scientific compute:

| Purpose | Tool |
| --- | --- |
| CPU compute | NumPy |
| Scientific compute | SciPy |
| GPU compute | CuPy |
| Tensor engine | PyTorch |
| Differentiable compute | JAX |

Geometry and visualization:

| Purpose | Tool |
| --- | --- |
| 2D geometry | Shapely |
| 3D geometry | Trimesh |
| 3D processing | Open3D |
| Interactive plots | Plotly |
| Volumetric visualization | PyVista |

Implementation note:

Most of these should be optional extras. Keep the base install lightweight.

## Recommended Development Phases

Each phase should leave the repository in a runnable state. Do not merge a phase
that requires the next phase to make imports, CLI commands, examples, or tests
work again.

Default phase invariants:

- Preserve the existing public API: `RISNetwork`, `AccessPoint`, `RIS`, `UE`,
  `RISnet`, and current CLI command behavior.
- Keep `RISNetwork.connect()` return keys and side effects compatible unless a
  later migration explicitly adds an adapter and regression tests.
- Prefer additive modules and adapters before moving files.
- Keep heavyweight dependencies optional; the base install should remain usable
  for core simulation and tests.
- Add or update tests in the same phase as the behavior they protect.

Recommended minimum verification after every phase:

```bash
python3 -m compileall core controller cli risnet app config utils
python3 -m pytest tests/test_fixes.py tests/test_physics_fixes.py
python3 - <<'PY'
from core import RISNetwork
from risnet import RISnet
net = RISNetwork(enable_messaging=False)
net.add_ap("ap1", 0, 0)
net.add_ris("ris1", 5, 0)
net.add_ue("ue1", 10, 0)
result = net.connect("ap1", "ris1", "ue1", use_get_snr=False)
assert "snr_dB" in result
assert RISnet is not None
PY
```

If optional dependencies are missing in a local environment, skip only the tests
that require those optional extras and document the skip reason in the phase
review.

### Phase 0 - Packaging and Baseline Stabilization

Goal: make the current code importable and executable from outside the
repository root before changing simulator architecture.

Implementation:

- Fix package discovery so the implementation packages currently living at the
  repository top level are installed or intentionally exposed through a stable
  package layout.
- Add `risnet/__main__.py` or update the `risnet` console entry point to target
  an existing callable.
- Keep `setup.py` as a compatibility shim and make `pyproject.toml` the source
  of packaging truth.
- Move heavy dependencies such as OpenCV, CVXPY, ML, notebook, visualization,
  and hardware tooling into optional extras unless they are required by the
  minimal simulator path.
- Define a small baseline test command for core simulation, physics, import, and
  CLI smoke coverage.

Do not break:

- `from core import RISNetwork`
- `from risnet import RISnet`
- Existing examples that import top-level `core`, `controller`, `cli`, `config`,
  or `utils` modules.
- The current interactive shell entry paths.

Exit gate:

- Editable install works from a directory outside the repository root.
- `python -m risnet` or the `risnet` console command reaches the CLI entry point.
- Baseline tests and compile checks pass.

### Phase 1 - Characterization Tests for Current Behavior

Goal: lock down current behavior before extracting internals from
`RISNetwork.connect()`.

Implementation:

- Add regression tests for a minimal AP -> RIS -> UE connection.
- Capture expected result keys, active-link updates, phase-setting behavior,
  missing-node errors, FOV behavior, deterministic seeded fading, and
  `use_get_snr=False` physics calculation.
- Add import smoke tests for `core`, `controller`, `cli`, `app`, and `risnet`.
- Add CLI smoke tests that instantiate the shell without starting interactive
  input loops.

Do not break:

- Current result dictionary shape from `RISNetwork.connect()`.
- Existing test expectations unless the test is proven stale and replaced with
  an explicit compatibility decision.

Exit gate:

- New characterization tests fail on intentional compatibility breaks and pass
  on the current implementation.
- No production code refactor is included in this phase.

### Phase 2 - Extract Array and Phase Primitives

Goal: introduce reusable phased-array primitives without changing network
behavior.

Implementation:

- Add a small additive array module for ULA/UPA geometry, steering vectors, and
  array-factor utilities.
- Wrap existing phase quantization and phase steering logic behind narrow
  interfaces while leaving `controller/ris_phase` imports valid.
- Add tests comparing extracted primitives against current calculations in
  `core/waveform.py`, `core/nodes.py`, `core/physics.py`, and
  `controller/ris_phase`.
- Route only low-risk call sites through the new wrappers after equivalence is
  proven.

Do not break:

- Existing `RIS` geometry and phase attributes.
- Beam-sweeping algorithm imports and registry discovery.
- Existing phase plots and MATLAB bridge inputs.

Exit gate:

- Old and new primitive calculations match within documented tolerances.
- Existing beam-sweeping tests still pass.

### Phase 3 - Extract Channel Interface Around Existing Link Budget

Goal: create the first channel abstraction as an adapter over existing physics,
not as a new physics model.

Implementation:

- Add a `ChannelModel` protocol or abstract base with a minimal evaluate method.
- Add a `LinkBudgetChannel` adapter that delegates to current `Physics`,
  waveform, and `RISNetwork.connect()` calculations.
- Add tests proving the adapter reproduces current SNR, power, path-loss, and
  gain outputs for fixed seeds.
- Keep direct `Physics` imports working while new services adopt the adapter.

Do not break:

- `core.physics.Physics` public helpers.
- `utils.link_budget`, `utils.snr`, `utils.rssi`, and existing controller code.
- Any return fields consumed by Flask, CLI serialization, or notebooks.

Exit gate:

- `RISNetwork.connect(..., use_get_snr=False)` produces equivalent results
  before and after the adapter route.
- Adapter tests cover missing paths, blocked paths, and deterministic seeded
  links.

### Phase 4 - Decompose `RISNetwork.connect()` Behind Compatibility Facade

Goal: split the high-risk method into testable services while preserving the
public method.

Implementation:

- Extract only cohesive internal steps: node lookup, geometry/FOV validation,
  phase computation, channel evaluation, feedback loop handling, active-link
  update, and result serialization.
- Keep `RISNetwork.connect()` as the single public compatibility facade.
- Add service-level tests for each extracted step plus end-to-end compatibility
  tests for the facade.
- Move one step at a time and rerun characterization tests after each extraction.

Do not break:

- Method signature and default argument behavior.
- Error messages used by tests or users.
- `last_connect_result`, `active_links`, feedback channels, and messaging
  behavior.

Exit gate:

- Public facade outputs match Phase 1 characterization tests.
- Each extracted service has focused tests.
- Flask, CLI, and examples still call the same public method successfully.

### Phase 5 - Scenario API and Headless Runner

Goal: make simulations executable without Flask or the interactive shell.

Implementation:

- Add scenario loading around existing JSON examples and any current YAML
  topology concepts.
- Add a scenario runner that builds `RISNetwork`, nodes, walls, impairments, and
  connection requests through public service APIs.
- Keep Flask, CLI, and notebooks as clients of the same headless runner where
  practical.
- Add golden scenario fixtures for simple, obstacle, and grid topologies.

Do not break:

- Existing `examples/json/*.json` files.
- Current CLI commands for adding nodes and connecting links.
- `app/state_manager.py` serialization behavior until an adapter replaces it.

Exit gate:

- A scenario can run from a test without importing Flask.
- Existing JSON examples either load directly or have documented compatibility
  adapters.

### Phase 6 - Minimal Runtime Kernel

Goal: add deterministic scheduling without embedding runtime concerns inside
`RISNetwork.connect()`.

Implementation:

- Add a minimal clock, event queue, seeded execution context, and metric
  collector.
- Schedule mobility updates, channel refreshes, beam updates, and metric
  sampling through the scenario runner.
- Keep runtime state outside node classes except through existing public update
  methods.

Do not break:

- Direct one-shot `RISNetwork.connect()` usage.
- Static scenario results when no runtime events are scheduled.
- Deterministic seeded behavior captured in Phase 1 and Phase 3 tests.

Exit gate:

- Running a static scenario through the runtime matches the non-runtime result.
- Scheduled updates are deterministic under a fixed seed.

### Phase 7 - Spatial Channels and MIMO

Goal: add new channel capabilities beside the link-budget adapter.

Implementation:

- Add AoA/AoD representations, array-to-array evaluation, MIMO channel
  matrices, and RIS-assisted spatial channel models as new `ChannelModel`
  implementations.
- Add regression tests for angle normalization, steering vectors, path loss,
  SNR, and beam patterns.
- Route scenarios to spatial channels only through explicit configuration.

Do not break:

- Default channel behavior.
- Existing link-budget tests and examples.
- Base install without optional visualization or GPU dependencies.

Exit gate:

- Existing simulations still use `LinkBudgetChannel` by default.
- Spatial-channel scenarios pass dedicated tests without changing compatibility
  results.

### Phase 8 - AI Runtime and Dataset Tools

Goal: expose learning-friendly interfaces without making ML dependencies
mandatory.

Implementation:

- Add observation, action, reward, and episode interfaces around scenario/runtime
  APIs.
- Add a Gym-compatible adapter behind an optional extra.
- Add dataset export and replay-buffer utilities.
- Move training scripts into structured tools only after import paths and data
  paths are covered by tests.

Do not break:

- Existing ML-guided beam-sweeping algorithms.
- Base install without PyTorch, JAX, Gymnasium, or scikit-learn.
- Existing dataset/model tooling under `controller/beamsweeping/ml`.

Exit gate:

- Core tests pass without ML extras installed.
- ML tests are optional and clearly marked.

### Phase 9 - Hardware, Visualization, and Digital Twin Runtime

Goal: add integration-heavy features only after deterministic local execution is
stable.

Implementation:

- Add mockable SDR/device interfaces before real hardware backends.
- Add optional monitoring, streaming, notebook, and visualization adapters.
- Keep distributed execution behind explicit configuration and after local
  runtime reproducibility is proven.

Do not break:

- Base install and core simulation tests.
- Headless CLI and notebook workflows when hardware dependencies are absent.
- Deterministic local runtime behavior.

Exit gate:

- Hardware-facing tests use mocks by default.
- Optional integration tests are isolated from core CI.

## Immediate Action Items

The next practical engineering tasks are:

1. Fix packaging and entry points.
2. Add a small `arrays/` module with ULA/UPA geometry and steering vector tests.
3. Extract a `ChannelModel` interface and wrap current link-budget behavior.
4. Split `RISNetwork.connect()` into smaller internal services without changing
   its public return shape.
5. Add a scenario runner that can execute AP -> RIS -> UE through the new
   service layer.
6. Keep Flask, notebooks, and CLI as clients of the same headless service APIs.

## Risks

- A direct rewrite would likely break the CLI, examples, and tests.
- Moving files before fixing packaging will make imports harder to reason about.
- Adding GPU, RL, or hardware dependencies to the base install will make the
  project harder to run and test.
- Entity-component architecture can become over-abstracted if introduced before
  array and channel primitives are stable.
- The existing tests include some expectations that may be stale relative to the
  current physics implementation, such as RIS array gain behavior.

## Final Direction

RISNet v3 should become:

```text
Headless programmable RF simulation core
+
CLI orchestration
+
Notebook-native experimentation
+
AI-native wireless systems runtime
```

with phased arrays, RIS, waveform simulation, and intelligent optimization built
on top of reusable simulation primitives.
