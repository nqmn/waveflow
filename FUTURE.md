# Waveflow v3 - Future Architecture Direction

## Implementability Verdict

Waveflow v3 is implementable in this codebase, but it should be delivered as an
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
`RISNetwork.connect()` (lines 211–727, `core/network.py`) combines node lookup,
phase computation via `HybridPhaseEngine`, FOV validation, link-budget
calculation, Rician fading, adaptive feedback loop, active-link state updates,
UE metadata persistence, SNR messaging queries, and quantized phase
serialization. This method must be decomposed before introducing the v3 kernel,
entity-component model, or spatial channel engine.

Packaging is resolved. `pyproject.toml` includes all top-level implementation
packages in its discovery (`app*`, `cli*`, `config*`, `controller*`, `core*`,
`utils*`, `risnet*`). `risnet/__main__.py` exists and backs both
`python -m risnet` and the `risnet` console entry point. `from core import
RISNetwork` and `from risnet import RISnet` import successfully.

No known baseline test failures are currently documented in the targeted
Phase 0/1 compatibility suite.

The verification snippet in the Recommended Development Phases section uses
collinear geometry `(ap1 at 0,0 → ris1 at 5,0 → ue1 at 10,0)` which triggers a
FOV rejection because the AP sits at 180° behind the RIS normal of 0°. The
snippet has been corrected below to use geometry that passes the default ±60°
FOV check.

## Current Implementation Snapshot

These pieces already exist and should be treated as current foundations, not
future-only ideas:

- Typer/Rich terminal commands are available through `waveflow ui ...`.
- `ChannelModel` and `LinkBudgetChannel` already provide a channel adapter
  layer.
- Array-related primitives already exist under `risnet/arrays`.
- Packaging, entry points, and base imports are already working.

The next roadmap sections should therefore focus on expansion and migration, not
on reintroducing these foundations from scratch.

## Vision

Waveflow should evolve from:

```text
RIS network simulator
```

into:

```text
Programmable RF intelligence and electromagnetic environment platform
```

The long-term objective is not to compete directly with CST Studio or HFSS in
full-wave electromagnetic simulation.

Instead, Waveflow should become:

- AI-native RF simulation platform
- programmable wireless environment framework
- phased-array experimentation platform
- RIS + MIMO + ISAC research toolkit
- human-aware RF sensing and beam-focusing platform
- notebook-native research environment
- scalable RF digital twin runtime

## Core Philosophy

Waveflow v3 should be:

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

It should also explicitly support:

- privacy-preserving human presence detection
- human localization and temporal tracking
- spatial energy focusing toward moving targets
- reusable sensing pipelines across phased arrays, Wi-Fi front ends, passive RIS,
  and active RIS

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

The next major generalization should be:

```text
source / array / reflector / target / receiver
```

where:

- a source may be Wi-Fi, SDR, phased array, or another active transmitter
- a reflector may be passive RIS or active RIS
- a target may be a UE, a moving human, or a generalized sensing actor
- a receiver may be a communications endpoint, sensing array, or shared
  measurement surface

This keeps the current `UE` abstraction valid for backward compatibility while
opening a clean path toward human-aware RF sensing and beam focusing.

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
- active RIS
- Wi-Fi sensing front ends
- radar
- ISAC
- localization
- human tracking
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
- passive RIS panels
- active RIS panels
- Wi-Fi and OFDM array experimentation
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

### 3a. Generalized RF Actors and Targets

Waveflow should grow beyond a fixed communications endpoint model.

Proposed additive abstractions:

```text
actors/
├── sources/
├── reflectors/
├── targets/
├── receivers/
└── mobility/
```

Examples:

- `WiFiSource`
- `PhasedArraySource`
- `PassiveRIS`
- `ActiveRIS`
- `UEReceiver`
- `HumanTarget`
- `MobileTarget`

Implementation note:

Do not replace `UE` immediately. Introduce `HumanTarget` or `SensingTarget` as
additive actors first, then let scenarios and future runtime services decide
whether a run is communications-centric, sensing-centric, or hybrid.

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
- target-aware scattering
- moving-human measurement sequences

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

The scene model should eventually support:

- tracked human actors
- target trajectories
- reflection and blockage zones
- sensing regions of interest
- device-near-human communication experiments

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

Waveflow should evolve into a reinforcement-learning-ready environment.

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
- tracking-policy training
- beam-focusing toward moving targets

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

Waveflow v3 should prioritize notebook workflows over GUI-first development.

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

Waveflow should remain headless-first.

CLI direction should be explicit:

- `waveflow` remains the legacy CLI surface for backward compatibility
- `waveflow ui` becomes the native modern CLI surface
- `waveflow web` becomes the native modern web surface
- legacy and modern CLI paths may coexist for a migration period, but the long
  term goal is not to make `waveflow ui` a thin wrapper around the legacy shell

Example future CLI:

```bash
waveflow scenario run urban.yaml
waveflow benchmark run massive_mimo
waveflow plugin list
waveflow array plot ula.yaml
waveflow shell
```

Planned tools:

- Typer
- Rich
- Textual

Implementation note:

The legacy interactive CLI is `cmd.Cmd`-based. A Typer/Rich terminal surface
already exists as `waveflow ui ...`; the next step is to expand that surface and
gradually route shared operations through service APIs.

Native modern CLI target:

```text
waveflow                  -> legacy shell / legacy commands
waveflow ui               -> native modern interactive CLI
waveflow web              -> native modern web interface
waveflow ui connect ...   -> modern one-shot command
waveflow ui sweep ...     -> modern one-shot command
waveflow ui status        -> modern one-shot command
```

Implementation note:

Do not keep coupling `waveflow ui` to the legacy `cmd.Cmd` shell as the final
architecture. Transitional fallbacks are acceptable during migration, but the
target state is a modern session model with shared handlers and persistent
interactive state owned by the new CLI stack itself.

### 10a. Rich-Powered RIS Sweep UX

`rich` is a strong fit for RIS research workflows because it can visualize live
parameter sweeps without forcing users into a heavy GUI stack. For phase
sweeps, beam steering, frequency sweeps, angle scans, and codebook exploration,
the terminal can become a first-class research surface rather than a secondary
debug tool.

Useful live terminal capabilities:

- progress bars for long RIS sweep jobs
- real-time metric dashboards for SNR, gain, path loss, AoA, AoD, and best
  candidate tracking
- spectrum-like bar views for frequency or resonance sweeps
- pseudo-heatmaps for beam patterns, phase states, or power maps
- status panels for scenario state, current sweep target, and convergence state
- multi-worker monitoring for parallel sweep or optimization jobs
- convergence tracking for Bayesian optimization, genetic search, or adaptive
  beam tuning

Example sweep progress:

```python
from rich.progress import track
import time

for phase in track(range(360), description="Sweeping RIS phase..."):
    time.sleep(0.01)
```

Example live metrics table:

```python
from rich.live import Live
from rich.table import Table
import random
import time

def make_table():
    table = Table(title="RIS Sweep")
    table.add_column("Iteration")
    table.add_column("Gain (dB)")
    table.add_column("AoA")
    table.add_column("AoD")

    for i in range(5):
        table.add_row(
            str(i),
            f"{random.uniform(10,30):.2f}",
            f"{random.uniform(-90,90):.1f}",
            f"{random.uniform(-90,90):.1f}",
        )

    return table

with Live(make_table(), refresh_per_second=4) as live:
    for _ in range(20):
        time.sleep(0.5)
        live.update(make_table())
```

Example ASCII-style visualization targets:

```text
Beam Intensity

███░░░░░░
█████░░░░
███████░░
█████████
██████░░░
```

```text
RIS Phase Matrix

[  0][ 45][ 90][135]
[180][225][270][315]
```

```text
2.4GHz  ████████░░
2.5GHz  ██████████
2.6GHz  ████░░░░░░
```

This is especially valuable for HPC, SSH, remote cluster execution, scripted
batch studies, and notebook-adjacent experimentation where reproducibility and
automation matter more than point-and-click interaction.

Implementation note:

Keep the terminal layer as a thin presentation surface over headless sweep and
optimization services. `rich` should render structured state emitted by core
services, not own RF logic directly.

Suggested command families:

```text
cli/
    sweep
    visualize
    benchmark
    export

ui/
    notebook/
    web/
```

Suggested stack:

- CLI rendering: Rich
- command surface: Typer
- scientific compute: NumPy + SciPy
- GPU and ML: PyTorch
- richer plotting: Plotly
- notebook workflows: Jupyter
- structured config: YAML + Pydantic
- parallel sweeps: Ray or Dask

Strategic direction:

Waveflow should not try to clone MATLAB or CST-style GUI workflows. The more
defensible niche is a programmable RF experimentation framework that is
automation-first, CLI-native, notebook-native, reproducible, and ready for
AI-assisted optimization.

### 10aa. Native Modern Interactive CLI

`waveflow ui` should evolve into a true native interactive CLI rather than a
collection of stateless one-shot commands plus a fallback into the legacy shell.

Core requirements:

- persistent in-session network state
- shared execution services with one-shot CLI commands
- Rich-rendered outputs for status, topology, links, connect, and sweep results
- command history and predictable prompt behavior
- future autocomplete and structured help support

Target interactive workflow:

```text
waveflow ui
waveflow> add random
waveflow> status
waveflow> connect AP1 R1 UE1
waveflow> sweep AP1 R1 UE1 --algo coarse-fine
waveflow> links
waveflow> save demo.json
```

Required architecture:

```text
session context
    +
shared command handlers
    +
shared execution services
    ->
1) modern interactive CLI
2) modern one-shot CLI commands
```

Implementation note:

Avoid making `cmd.Cmd` the owner of modern CLI behavior. The modern shell should
own its own session state and call the same handlers used by one-shot `waveflow ui`
commands. The legacy shell can remain accessible through `waveflow` while the
modern shell matures under `waveflow ui`.

### 10ab. Native Modern Web Surface

Waveflow should also grow a native modern web surface, but only as a peer of
the modern CLI and notebook workflows, not as a separate owner of simulation
state.

Core requirements:

- web clients call the same shared execution services used by `waveflow ui`
- live status, topology, links, localization, sensing, and diagnostics are
  rendered from shared typed results and event streams
- the web layer owns presentation and interaction only, not RF logic
- the web surface remains optional and does not block headless usage

Target surface split:

```text
waveflow       -> legacy CLI
waveflow ui    -> native modern CLI
waveflow web   -> native modern web interface
```

Implementation note:

The current Flask app is a transitional web layer. The target state is a modern
web client that consumes the same scenario, runtime, and diagnostics services
as the CLI. Web-specific state management should stay in the web layer, while
simulation and experiment state remain owned by shared services.

### 10b. Localization, Sensing, and Diagnostics UX

The same terminal-first UX principles should extend beyond RIS sweeping into
localization, radar, ISAC, calibration, and debugging workflows. Researchers
need fast feedback during algorithm development, but they also need the output
to remain scriptable, comparable across runs, and usable over SSH.

Important UX targets:

- localization dashboards showing estimated position, ground truth, error,
  covariance, and confidence region drift
- anchor and path visibility summaries for AoA, ToF, TDoA, RSSI, and fused
  estimators
- live tracking views for mobile UE trajectories and filter state evolution
- diagnostics panels for failed links, blocked paths, FOV rejection, phase
  quantization, and channel-estimation instability
- calibration workflows for array alignment, timing offset, phase offset, and
  synchronization health
- sensing views for radar returns, occupancy hints, and target tracks
- experiment comparison views for baseline versus optimized runs
- structured export paths for logs, tables, traces, and publication-ready data

Example terminal-localization outputs:

```text
Localization Status

UE-07     est=(4.12, 8.44) m
truth     gt =(4.30, 8.02) m
error     0.46 m
method    AoA + RIS-assisted refinement
status    converged
```

```text
Anchor Health

AP-1   LOS   AoA lock     SNR 24.1 dB
AP-2   NLOS  weak path    SNR 11.8 dB
RIS-1  OK    assist path  Gain +7.4 dB
```

```text
Tracker Residuals

t=01  ███░░░░░░
t=02  ████░░░░░
t=03  ██░░░░░░░
```

Example future CLI:

```bash
waveflow ris sweep run config.yaml
waveflow loc track run indoor_lab.yaml
waveflow loc replay logs run_042.json
waveflow sense scan mmwave_corridor.yaml
waveflow diag links urban_ris.yaml
waveflow diag phases experiment_17.yaml
waveflow export metrics run_042 --format parquet
```

Implementation note:

Every UX surface should be backed by typed result objects and event streams from
shared simulation services. A localization solver, sweep engine, or sensing
pipeline should run identically in batch mode, notebook mode, and terminal
mode, with only the presentation layer changing.

Recommended service layout:

```text
services/
    sweep/
    localization/
    sensing/
    diagnostics/
    calibration/
    export/
```

Recommended UX layers:

```text
ui/
    cli/
    notebook/
    web/
    reports/
```

Strategic direction:

The product should feel like an RF experimentation operating system rather than
just a simulator shell. The value is not only accurate physics. The value is a
repeatable workflow for sweep, inspect, localize, diagnose, compare, and export
without leaving programmable environments.

### 10c. Human-Aware Sensing and Beam Focusing

Human-aware RF sensing should become a first-class future workflow, not just a
special-case beam sweep.

Core future capabilities:

- detect human presence without camera-centric assumptions
- estimate human position from RF measurements
- track moving humans over time
- focus reflected or transmitted energy toward the estimated human region
- support both communication enhancement and sensing-only experiments

Important framing:

- this is not an "RF camera" roadmap
- this is not a "wireless CCTV" architecture
- the defensible niche is privacy-preserving spatial intelligence

Practical interpretation:

- for communications experiments, the system may focus energy toward a device
  carried by or near a human
- for sensing experiments, the system may treat the human as a moving RF target
  whose position and motion are inferred from measurements

Implementation note:

The first useful version should support a single moving human in a synthetic
scene, tracked over time, with beam steering or beam focusing driven by the
estimated target state. Multi-human tracking, occupancy fields, and skeletal
inference should remain later phases after the generalized actor and channel
layers are stable.

### 11. Plugin Ecosystem

Waveflow should evolve toward a universal plugin architecture.

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

Waveflow should move toward tensorized simulation.

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

Naming direction:

- `waveflow web` should eventually become the canonical native web surface
- legacy `--web` or older Flask launch paths may remain transitional aliases
  during migration, but should not define the long-term architecture

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
waveflow/
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
PYTHONPATH=. python3 tests/test_physics_fixes.py
python3 - <<'PY'
from core import RISNetwork
from risnet import RISnet
# ap1 at (0,2), ris1 at (5,2) with default normal=0 and max_angle=90,
# ue1 at (10,5) -- both AP and UE within RIS FOV
net = RISNetwork(enable_messaging=False)
net.add_ap("ap1", 0, 2)
net.add_ris("ris1", 5, 2, max_angle_deg=90)
net.add_ue("ue1", 10, 5)
result = net.connect("ap1", "ris1", "ue1", use_get_snr=False)
assert "snr_dB" in result, f"Missing snr_dB, got: {list(result.keys())}"
assert RISnet is not None
print("Baseline OK — snr_dB:", result["snr_dB"])
PY
```

Note: `pytest` requires installation; use
`PYTHONPATH=. python3 tests/<file>.py` as the fallback runner until a virtual
environment is established.

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

Current status (verified 2026-05-06):

- Complete: packaging and import wiring are in place.
- Complete: heavyweight dependencies (OpenCV, CVXPY, ML, visualization) are in
  optional extras.
- Incomplete: `pytest` is not installed in the system environment. Tests must
  currently be run via `PYTHONPATH=. python3 tests/<file>.py`. A virtual
  environment with `pip install -e ".[dev]"` is needed before pytest-based CI
  can run.
- Incomplete: the baseline verification snippet in this document used broken
  collinear geometry (AP behind RIS FOV). Fixed above.
- Remaining decision: whether top-level packages stay top-level long term or
  migrate under `risnet/` as part of the v3 folder structure.

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

Current status:

- Complete: `tests/test_connect_characterization.py` covers the current
  `RISNetwork.connect()` result shape, deterministic seeded metrics,
  `active_links`, `last_connect_result`, phase persistence, no-active-link mode,
  missing-node errors, FOV rejection, `compute_phases=False`, and beam-miss
  reporting.
- Complete: import, module CLI, console CLI, and minimal runtime smoke tests are
  covered by `tests/test_smoke.py`.
- Complete: no production refactor was introduced for this phase.

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

Current status:

- Complete: additive array geometry, steering, array-factor, and quantization
  primitives exist under `risnet/arrays`.
- Complete: low-risk call sites now reuse those primitives through
  `controller/ris_phase`, `core.physics.compute_array_factor()`, and the
  quantization analyzer while preserving existing imports and behavior.

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

Current status:

- Complete: `ChannelModel` and `LinkBudgetChannel` are implemented and covered
  by focused adapter tests.
- Complete: the shared RIS link-budget configuration and evaluation helpers are
  consolidated in `utils/link_budget.py`, re-exported through
  `risnet.channels`, and reused by `utils.snr` without changing public
  compatibility surfaces.

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

Current status:

- Complete: `RISNetwork.connect()` now delegates node lookup,
  geometry/FOV preparation, phase computation, channel/link-budget evaluation,
  feedback persistence, active-link persistence, and last-result persistence
  through focused internal helpers while preserving the public facade.
- Complete: the public compatibility surface is covered by the Phase 1
  characterization tests, and the extracted helper services now have focused
  regression coverage in `tests/test_connect_characterization.py`.

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

Current status:

- Complete: the headless scenario layer exists through `ScenarioRunner`,
  `ScenarioExecutionService`, request objects, `connect` and `sweep` actions,
  ordered action lists, and JSON/YAML scenario request documents.
- Complete: Flask/API `connect` and `sweep` route through the shared headless
  scenario execution service instead of calling `RISNetwork` methods directly.
- Complete: a non-interactive CLI connect path routes through the same shared
  scenario execution service.
- Complete: scenario validation now rejects mixed top-level/action request
  shapes, malformed `kwargs`, and empty `topology_path` values with explicit
  errors.
- Complete: golden example topology coverage now includes simple, obstacle, and
  grid fixtures through the shared loading path.
- Remaining future work: richer scenario schemas and broader client adoption are
  no longer Phase 5 blockers and can proceed incrementally in later phases.

Phase 5 closeout checklist (completed):

- Route web/API `connect` and `sweep` execution through the shared headless
  service layer instead of calling `_net.connect()` and `_net.sweep()` directly.
- Route at least one non-interactive CLI execution path through the same
  headless scenario service API.
- Add stable golden fixtures for:
  - simple topology
  - obstacle topology
  - grid topology
- Expand scenario request validation beyond minimal dataclass parsing.
- Document the canonical boundaries between:
  - topology files
  - scenario request files
  - scenario result objects
- Add regression tests proving the shared service layer produces equivalent
  results across direct API use and client wrappers.

Phase 5 completion gate (satisfied):

- Flask/API, headless runner, and at least one CLI execution path share the
  same scenario execution service.
- Golden scenario fixtures exist and are covered by tests.
- Scenario documents fail clearly on malformed action or topology inputs.
- Existing JSON examples remain loadable through the shared path.

CLI migration consequence:

- Phase 5 now provides the shared service foundation needed for `waveflow ui`
  to become a native modern CLI without depending on the legacy shell for core
  execution behavior.

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

Recommended first slice for Phase 6:

- Add a minimal simulation clock with integer or fixed-step time progression.
- Add a deterministic trajectory iterator for position updates.
- Add a small metric sampling loop that repeatedly calls shared services and
  records results by timestep.
- Keep this runtime outside `RISNetwork.connect()` and outside UI/client code.
- Validate that `t=0` with no movement matches the existing static scenario
  output exactly.

Parallel CLI work that can begin after Phase 5:

- add a modern `SessionContext` for `waveflow ui`
- route native interactive `add`, `status`, `list`, `links`, `connect`, and
  `save/load` through shared handlers
- keep `waveflow` on the legacy shell surface until modern interactive parity is
  sufficient

### Phase 7 - Spatial Channels, MIMO, and Generalized RF Nodes

Goal: add new channel capabilities beside the link-budget adapter.

Implementation:

- Add AoA/AoD representations, array-to-array evaluation, MIMO channel
  matrices, and RIS-assisted spatial channel models as new `ChannelModel`
  implementations.
- Add generalized scenario support for phased arrays, Wi-Fi-like OFDM sources,
  passive RIS, and active RIS without forcing every run through AP -> RIS -> UE.
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

### Phase 7a - Human-Aware Sensing and Beam Focusing

Goal: extend the simulator from UE-centric communications into moving-human RF
sensing and target-aware beam steering.

Implementation:

- Add `HumanTarget` or `SensingTarget` as an additive actor, not as a direct
  replacement for `UE`.
- Add mobility models and deterministic target trajectories to the runtime.
- Generate target-aware measurement sequences using spatial channels, CSI, RSSI,
  Doppler, or hybrid observables depending on scenario configuration.
- Add localization and tracking services that estimate target position over
  time, then expose that state to beamforming or beam-focusing controllers.
- Support two experiment modes:
  - sensing mode: localize and track the human as a target
  - enhancement mode: steer energy toward a device carried by or near the human

Do not break:

- Existing `UE`-based communication scenarios.
- Existing beam sweep and localization tests.
- Base install when optional visualization, ML, or hardware extras are absent.

Exit gate:

- A synthetic single-human moving scenario runs deterministically.
- Tracking output can drive beam steering or beam focusing in a repeatable way.
- Legacy AP -> RIS -> UE scenarios remain compatible.

Recommended first slice for Phase 7a:

1. Add `HumanTarget` as an additive actor with position, optional height, and
   simple reflective/scattering metadata.
2. Add a synthetic moving-target scenario that updates the target over time
   using the Phase 6 runtime loop.
3. Generate a measurement timeline per timestep using existing channel, CSI,
   RSSI, and optional Doppler-capable primitives.
4. Add a minimal tracking service:
   - nearest-state smoothing, or
   - Kalman filter based state estimation
5. Feed the tracked target state into beam steering or beam-focusing logic.
6. Keep `UE` scenarios unchanged; do not replace `UE` with `HumanTarget`.

Definition of done for the first Phase 7a slice:

- One moving synthetic human can be tracked over time.
- The estimated target state can steer or focus the beam repeatably.
- The execution path is headless-first and scenario-driven.
- No existing AP -> RIS -> UE workflow regresses.

Practical sequencing:

```text
Phase 5 closeout
    ->
Phase 6 minimal clock + trajectory loop
    ->
Phase 7a single moving human + tracking + beam focus
```

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

## Web Interface (Planned)

The Flask-based web interface (`app/`) exists in the codebase but is not yet complete or supported as a user-facing feature. It is excluded from the current README.

Planned capabilities:

- REST API endpoints (`/api/*`) for network control and monitoring
- HTML UI for topology visualization and node management
- Real-time SNR and beam state display
- Integration with the headless scenario runner (Phase 5)

Current status:

- `app/` module exists with `api/bp.py`, `web/bp.py`, `thread_safe_network.py`, and `state_manager.py`
- Entry point reachable via `waveflow --web` but not production-ready
- Will be completed after the headless scenario runner (Phase 5) is stable

## Known Technical Debt

Findings from codebase audit (2026-05-06). Items are cross-referenced to
migration phases where resolution is blocked or required.

### Circular Import: core → controller

Resolved 2026-05-06 for the direct-import portion of the issue. `core/`
now owns a `PhaseEngine` abstraction and registry, while
`controller/ris_phase/core_adapter.py` registers the existing controller-backed
implementation. `core/network.py` and `core/nodes.py` no longer import
controller phase classes directly.

Residual debt: the controller-backed implementation is still the default
runtime provider behind the core registry. That is compatible with the current
architecture migration, but the broader controller/core separation is not fully
complete yet.

### Duplicate CLI Implementations

`risnet/cli.py` (728 lines) and `cli/main_shell.py` (2557 lines) both implement
`do_add`, `do_list`, `do_clear`, `do_exit`, `do_quit`, and other commands with
overlapping but non-identical behavior. Neither file documents its relationship
to the other.

Resolution (documented 2026-05-06): `cli/main_shell.py` is the canonical full
interactive shell used by `python -m risnet`, the `waveflow` console entry
point, and `waveflow ui shell`. `risnet/cli.py` remains a legacy alternate
shell surface and `waveflow/cli.py` remains a compatibility export wrapper.
Consolidation is still optional future cleanup, but the current relationship is
no longer ambiguous.

### Monolithic CLI Shell

`cli/main_shell.py` is 2557 lines with 56 methods handling node management,
beam sweep orchestration, signal processing, plotting, and topology
serialization in a single class. `cli/connection_handler.py` is 1455 lines with
methods exceeding 500 lines of nested logic.

Resolution: split into focused collaborators (NodeManager,
BeamSweepOrchestrator, MetricsCalculator) after Phase 1 characterization tests
lock down current CLI behavior.

### Broken Example: NetworkManager

Resolved 2026-05-06. The HOG human-detection example now lives at
`examples/script/example_19_hog_human_detection.py`, uses the current
`RISNetwork` + `SweepAlgorithmLoader` APIs, and is covered by the smoke suite.

Residual note: any remaining references to the old top-level example path
should be treated as stale documentation/tests and repointed to the script
example path.

### print() Throughout Library Code

Core simulation modules and the main beam-sweeping algorithm surfaces now use
Python's `logging` module instead of direct `print()` diagnostics, which keeps
test capture and production embedding cleaner.

Residual note: a few utility/demo scripts still print directly, particularly
camera helper scripts under `utils/` and standalone mock/demo entrypoints.
Those are now tooling cleanup rather than Phase 4 blockers.

### Star Imports in waveflow/

`waveflow/__init__.py` re-exports the entire `risnet` namespace via
`from risnet import *`. This suppresses flake8 with `# noqa: F401,F403` and
makes it impossible to know what is available in the `waveflow` namespace
without reading `risnet/__init__.py`.

Resolution: replace with explicit named imports or a documented `__all__` list.
Low risk, low priority.

### SNR / Link Budget Utilities Scattered

`utils/link_budget.py`, `utils/snr.py`, `utils/rssi.py`, and
`core/physics.py:compute_snr_dB()` all perform overlapping link budget
calculations with no clear ownership boundary.

Resolution: consolidate under the `ChannelModel` adapter introduced in Phase 3.
Route existing callers through the adapter progressively rather than deleting
utility files immediately.

### Hardcoded Configuration Constants

Physics defaults are scattered as module-level literals: `target_snr_dB = 20.0`
(`core/nodes.py:69`), `presence_detection_tolerance_deg = 5.0`
(`core/network.py:48`), and others. The `config/` module exists but is
minimally used.

Resolution: consolidate into the `Config` object already used by `risnet/
__init__.py` and inject it at construction time. Do not require Pydantic in the
base install until Phase 5 or later.

---

## Immediate Action Items

Status as of 2026-05-06:

1. ~~Fix packaging and entry points.~~ — Done. All packages discoverable,
   `risnet/__main__.py` exists, imports verified.
2. Set up a virtual environment and install `pytest` via `pip install -e
   ".[dev]"` so the test suite can run without `PYTHONPATH` hacks.
3. ~~Fix the stale expected value in `tests/test_fixes.py` TEST 3 (Phase 1
   prerequisite before any refactoring).~~ — Done.
4. ~~Fix `examples/hog_human_detection_example.py` — remove or update the
   `NetworkManager` reference to use the current `RISNetwork` API.~~ — Done.
   The maintained example now lives at
   `examples/script/example_19_hog_human_detection.py`.
5. ~~Add characterization regression tests for `RISNetwork.connect()` output
   shape, FOV errors, seeded fading, and active-link behavior (Phase 1).~~ —
   Done. Covered by `tests/test_connect_characterization.py`.
6. ~~Introduce a `PhaseEngine` abstract base in `core/` and remove the
   `core/network.py:20` controller import (prerequisite for Phase 4).~~ —
   Done. Core now routes phase operations through `core.phase_engine`, and the
   controller implementation is registered via a compatibility adapter.
7. ~~Add a small `arrays/` module with ULA/UPA geometry and steering vector
   tests (Phase 2).~~ — Done. Additive array primitives are in
   `risnet/arrays`, routed through the low-risk legacy call sites, and covered
   by focused equivalence tests.
8. ~~Extract a `ChannelModel` interface and wrap current link-budget behavior
   (Phase 3).~~ — Done. `ChannelModel`, `LinkBudgetChannel`, and shared
   RIS link-budget helpers are in place and reused by the overlapping utility
   paths without changing compatibility surfaces.
9. ~~Split `RISNetwork.connect()` into smaller internal services without changing
   its public return shape (Phase 4).~~ — Done. The public facade is preserved,
   the major internal steps are extracted behind focused helpers, and helper
   coverage now lives alongside the public characterization tests.
10. ~~Replace `print()` with `logging` in all non-CLI library modules (Phase 4).~~
    — Done for the core/library surface. Core simulation modules and the main
    sweep algorithms now use logger-based reporting; remaining direct prints are
    limited to utility/demo scripts and are no longer Phase 4 blockers.
11. ~~Decide canonical CLI implementation and document or consolidate the
    `risnet/cli.py` vs `cli/main_shell.py` relationship (before Phase 5).~~ —
    Done for documentation. `cli/main_shell.py` is the canonical full shell;
    `risnet/cli.py` is retained as a legacy alternate shell and
    `waveflow/cli.py` is a compatibility wrapper.
12. ~~Add a scenario runner that executes AP → RIS → UE without Flask (Phase 5).~~
    — Done. `ScenarioRunner` executes headless `connect`/`sweep` flows and
    ordered action sequences from code and JSON/YAML request documents.
13. Keep Flask, notebooks, and CLI as clients of the same headless service APIs.
    Status: In Progress.

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

Waveflow v3 should become:

```text
Headless programmable RF simulation core
+
CLI orchestration
+
Notebook-native experimentation
+
AI-native wireless systems runtime
```

with phased arrays, Wi-Fi front ends, passive RIS, active RIS, waveform
simulation, human-aware sensing, and intelligent optimization built on top of
reusable simulation primitives.
