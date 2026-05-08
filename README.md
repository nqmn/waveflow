# Waveflow v2.0

[![PyPI version](https://img.shields.io/pypi/v/waveflow-sim)](https://pypi.org/project/waveflow-sim)
[![Python](https://img.shields.io/pypi/pyversions/waveflow-sim)](https://pypi.org/project/waveflow-sim)
[![License](https://img.shields.io/badge/License-Apache_2.0-green.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-nqmn%2Fwaveflow-lightgrey?logo=github)](https://github.com/nqmn/waveflow)

Waveflow is a Python simulator for wireless networks assisted by Reconfigurable Intelligent Surfaces (RIS). It lets researchers and engineers model how passive reflective panels improve signal coverage, optimize beam angles, and evaluate link quality — without physical hardware.

Use it to prototype RIS-assisted network topologies, benchmark beam sweeping algorithms, study propagation physics, simulate OFDM waveforms, and run ML-guided beam prediction — through a scriptable Python API, interactive CLI, or modern terminal commands.

## Quick Start

```bash
pip install waveflow-sim
waveflow
```

Or install from source:

```bash
git clone https://github.com/nqmn/waveflow
cd waveflow
pip install -e .
waveflow
```

Full installation options: **[INSTALL.md](INSTALL.md)**  
Step-by-step tutorials: **[TUTORIAL.md](TUTORIAL.md)**

## Features

| Category | Capability |
|---|---|
| **Network** | 2D/3D node placement (AP, RIS, UE), walls and obstacles, JSON/YAML topology files, random RIS-aware layout generation |
| **Physics** | FSPL, atmospheric absorption, Rician fading, mutual coupling, RIS array gain, phase quantization loss (1–4 bit) |
| **Beam sweeping** | Linear, coarse-fine, differential evolution, ML-guided, hierarchical, PRIME localization, HOG/ArUco vision |
| **Pathfinding** | Dijkstra, A\*, Greedy, Exhaustive across multi-hop RIS networks |
| **Waveform** | OFDM signal simulation, per-subcarrier SNR, multipath, PAPR, waveform-level vs system-level comparison |
| **Feedback** | Closed-loop UE→AP SNR feedback with adaptive beam tracking |
| **ML** | Random Forest, XGBoost, SVR, KNN, LGBM, MLP beam angle predictors; trainable from generated datasets |
| **Streaming** | Per-chunk BER, SER, throughput, and Shannon capacity over active RIS links |
| **Interface** | Interactive CLI, Typer/Rich terminal UI (`waveflow ui`), Python API, headless scenario runner |
| **Validation** | 14-section physics validation suite, 66 pytest checks against analytical reference values |
| **MATLAB** | Optional bridge for far-field beam pattern plots and phase visualisation |

## Channel Engines

Waveflow now exposes two official RIS channel engines:

| Engine | Role | Best for |
|---|---|---|
| `simris` | Published/reference stochastic channel engine | literature-aligned channel studies, `H/G/D` channel tensors, supported channel-aware connect scenarios |
| `lightris` | Native analytical engine | fast system-level evaluation, beam control, tapering-aware workflows, feedback loops, large sweeps, ML dataset generation |

Design intent:
- `SimRIS` and `LightRIS` are complementary, not replacements for each other.
- `connect()` is now **SimRIS-first** by default.
- If a request is outside current SimRIS support, Waveflow falls back explicitly to `lightris` and reports the reason in the result metadata and CLI output.
- Sweep, tapering-heavy, and feedback-heavy workflows remain `LightRIS`-native by design.

## Usage

### Interactive CLI

```bash
waveflow
waveflow> add ap ap1 0 0
waveflow> add ris ris1 5 0 0 16 2
waveflow> add ue ue1 10 3
waveflow> connect ap1 ris1 ue1
SNR: 29.9 dB   Power: -52.3 dBm   Beam angle: 16.7°
waveflow> sweep ap1 ris1 ue1 60 10 --algo coarse-fine
waveflow> stream ap1 ris1 ue1
waveflow> status
waveflow> save mynet.json
waveflow> help
```

Key shell commands:

| Command | What it does |
|---|---|
| `add ap/ris/ue` | Add a node at specific coordinates |
| `add random` | Auto-generate a valid AP + RIS + UE layout |
| `connect` | Compute SNR, power, and beam angle for a link |
| `sweep` | Search for the best beam angle using a chosen algorithm |
| `stream` | Simulate a live data stream and measure throughput |
| `status` | Show all nodes, distances, and active links |
| `list` | Print an ASCII map of the network |
| `links` | Show active links only |
| `clear` | Remove links or the entire network |
| `save / load` | Persist and restore network state to/from JSON |
| `plot` | Visualise sweep or connect results (requires `[plot]`) |
| `signal` | Detailed per-hop signal breakdown |
| `testall` | Run the built-in test suite |
| `testphysics` | Run the physics validation suite |

### Modern Terminal UI

`waveflow ui` now covers both one-shot Rich commands and a native interactive modern shell. Use one-shot commands for scripts, CI, and reproducible runs; use `waveflow ui shell` when you want persistent in-memory state with the same modern command surface.

```bash
# Network status from a topology file
waveflow ui status --topology examples/json/example_1_simple.json

# Connect and get link metrics
waveflow ui connect AP1 R1 UE1 --topology examples/json/example_1_simple.json

# Force the reference engine explicitly
waveflow ui connect AP1 R1 UE1 --topology examples/json/example_1_simple.json --channel-model simris --environment indoor --scenario 1

# Force the native analytical engine explicitly
waveflow ui connect AP1 R1 UE1 --topology examples/json/example_1_simple.json --channel-model lightris

# Beam sweep with live progress bar
waveflow ui sweep AP1 R1 UE1 --topology examples/json/example_1_simple.json --fov 60 --step 10

# Rich-native topology and link inspection
waveflow ui list --topology examples/json/example_1_simple.json
waveflow ui links --topology examples/json/example_1_simple.json

# Run physics validation suite
waveflow ui testphysics

# Run the comprehensive test suite
waveflow ui testall

# Run any legacy CLI command non-interactively
waveflow ui run --topology examples/json/example_1_simple.json signal AP1 R1 UE1 --breakdown

# Open the native interactive modern shell
waveflow ui shell

# All available commands
waveflow ui --help
```

### Python API

High-level API:

```python
from waveflow import RISnet

net = RISnet()
ap  = net.addAP('ap1',  position=(0, 0))
ris = net.addRIS('ris1', position=(5, 0), N=16, bits=2)
ue  = net.addUE('ue1',  position=(10, 3))
net.start()

result = net.ping(ap, ue)
print(f"SNR: {result['snr_dB']:.1f} dB, hops: {result['hops']}")

throughput = net.iperf(ap, ue)
print(f"Throughput: {throughput['throughput_Mbps']:.1f} Mbps")

net.stop()
```

Low-level API:

```python
from core import RISNetwork

net = RISNetwork(enable_messaging=False)
net.add_ap('ap1', 0, 0)
net.add_ris('ris1', 5, 0, N=16, bits=2, max_angle_deg=90)
net.add_ue('ue1', 10, 3)

result = net.connect('ap1', 'ris1', 'ue1', use_get_snr=False)
print(f"SNR:        {result['snr_dB']:.1f} dB")
print(f"Beam angle: {result['beam_angle']:.1f}°")
print(f"Array gain: {result['gain_dBi']:.1f} dBi")
print(f"Quant loss: {result['quant_loss_dB']:.2f} dB")
print(f"Engine used: {result['channel_model_used']}")
```

Explicit engine selection:

```python
simris_result = net.connect(
    'ap1',
    'ris1',
    'ue1',
    channel_model='simris',
    environment='indoor',
    scenario=1,
    use_get_snr=False,
)

lightris_result = net.connect(
    'ap1',
    'ris1',
    'ue1',
    channel_model='lightris',
    use_get_snr=False,
)
```

Notes:
- If `channel_model` is omitted, `connect()` requests `simris` first.
- Unsupported SimRIS requests fall back to `lightris` with:
  - `channel_model_requested`
  - `channel_model_used`
  - `channel_model_fallback_reason`

### Headless Scenario Runner

Run simulations from JSON or YAML files — no Flask, no interactive shell:

```python
from risnet import ScenarioRunner, ScenarioRequest

runner = ScenarioRunner()

# From a topology file
result = runner.run_connect('examples/json/example_1_simple.json', use_get_snr=False)
print(f"SNR: {result.result['snr_dB']:.1f} dB")

# From a YAML scenario file
request = ScenarioRequest.from_file('scenario.yaml')
result = runner.run(request)
```

`scenario.yaml`:

```yaml
topology_path: examples/json/example_1_simple.json
connect:
  ap_name: ap1
  ris_name: ris1
  ue_name: ue1
```

## Beam Sweep Algorithms

```bash
waveflow> sweep ap1 ris1 ue1 60 10 --algo linear
waveflow> sweep ap1 ris1 ue1 60 10 --algo coarse-fine
waveflow> sweep ap1 ris1 ue1 60 10 --algo de
waveflow> sweep ap1 ris1 ue1 60 10 --algo ml-guided --ml-predictor rf
waveflow> sweep ap1 ris1 ue1 60 10 --algo prime
```

| Algorithm | Key | Notes |
|---|---|---|
| Linear brute-force | `linear` | Uniform steps over full FOV |
| Coarse-fine | `coarse-fine` | Two-phase search, ~30% fewer evaluations |
| Differential Evolution | `de` | Population-based global search |
| ML-guided | `ml-guided` | RF / XGBoost / SVR / KNN / LGBM predictor + refinement |
| Hierarchical | `hierarchical` | Multi-resolution sweep |
| PRIME localization | `prime` | Beam measurement → UE position estimate |
| DE localization | `de-localization` | Blind UE localization via DE |

## Optional Extras

```bash
pip install -e ".[plot]"         # matplotlib — enables plot command and charts
pip install -e ".[ml]"           # scikit-learn + torch — ML beam predictors
pip install -e ".[terminal]"     # typer + rich — waveflow ui commands
pip install -e ".[vision]"       # opencv-python — ArUco / HOG vision workflows
pip install -e ".[web]"          # flask + waitress — web interface
pip install -e ".[optimization]" # cvxpy + scs — phase optimization
pip install -e ".[dev]"          # pytest, black, flake8, mypy
pip install -e ".[all]"          # everything above
```

## Vision Integration

The `[vision]` extra enables two camera-assisted workflows:

**ArUco marker positioning** — generate printable fiducial markers, detect them from a camera feed, and derive UE position estimates for use as sweep inputs:

```bash
pip install -e ".[vision]"
PYTHONPATH=. python3 examples/script/example_18_aruco_markers.py
```

```
✓ Successfully saved: aruco_markers/aruco_id_0.png
Generated 5 markers: aruco_markers/batch/aruco_id_{0..4}.png
```

**HOG human detection** — use a histogram-of-oriented-gradients detector on a live webcam feed to locate a person and derive a candidate beam direction:

```bash
PYTHONPATH=. python3 examples/script/example_19_hog_human_detection.py
# Requires a connected webcam
```

Vision is example-driven rather than a full CLI product surface. The intended workflow is: detection output → target angle or position → feed into a sweep algorithm as a candidate beam direction.

## MATLAB Integration

Waveflow includes an optional MATLAB bridge for far-field beam pattern visualisation. The bridge is lazy-loaded — if MATLAB is not installed, all non-MATLAB functionality continues to work normally.

Standalone MATLAB scripts (no Python required) live in `examples/matlab/`:

| Script | What it shows |
|---|---|
| `example_1_beam_pattern_3d.m` | 3D far-field beam pattern, 1D/polar cuts, phase heatmap |
| `example_2_compare_steering_angles.m` | Side-by-side patterns for 6 steering angles |
| `example_3_ris_phase_farfield.m` | Phase maps + 3D far-field (Python-matched parameters) |
| `example_4_ris_phase_farfield_cst_style.m` | CST-style annotated 3D pattern with source/beam arrows |

Run from the MATLAB command window:

```matlab
cd examples/matlab
example_1_beam_pattern_3d
example_3_ris_phase_farfield(0, 5.8e9, 0.45, 0, 45, 0, 16, 16)
```

From Python, the bridge is accessed via `MatlabBridge`:

```python
from matlab_integration import MatlabBridge
bridge = MatlabBridge.get_instance()   # lazy-loaded; MATLAB starts on first use
bridge.plot_beam_pattern(...)
```

The library functions under `matlab_integration/scripts/` (`compute_beam_pattern`, `plot_ris_geometry`, etc.) are called by the Python bridge — they are not intended to be run directly.

## Project Structure

```
waveflow/
├── core/               # Physics, nodes, network manager, waveform, environment
├── controller/         # Beam sweeping, pathfinding, ML predictors, phase control
├── cli/                # Interactive shell (main_shell.py)
├── risnet/             # High-level API, scenario runner (backward-compatible package)
├── waveflow/           # Public package alias (forward-looking name)
├── app/                # Optional Flask web interface
├── config/             # Configuration management
├── utils/              # Link budget, SNR, RSSI, CSI helpers
├── matlab_integration/ # Optional MATLAB bridge for beam pattern plots
├── risformula/         # Standalone formula implementations
├── examples/
│   ├── script/         # 19 runnable Python examples
│   ├── json/           # Topology fixture files
│   └── matlab/         # Standalone MATLAB scripts
├── tests/              # Test suite (pytest)
├── INSTALL.md
├── TUTORIAL.md
└── FUTURE.md           # v3 architecture roadmap
```

## Testing

```bash
# Compile check
python3 -m compileall core controller cli risnet waveflow config utils

# Physics regression
PYTHONPATH=. python3 tests/test_physics_fixes.py

# Physics model validation suite (14 sections, 53 checks)
waveflow ui testphysics

# Full test suite via terminal UI
waveflow ui testall

# Full suite with pytest (66 checks including test_physics_core.py)
pip install -e ".[dev]"
pytest tests/ -v
```

## Roadmap

See [FUTURE.md](FUTURE.md) for the full v3 architecture migration plan — phased arrays, spatial channels, AI-native runtime, and web interface.

## Contributing

Contributions are welcome. Please open an issue to discuss significant changes before submitting a pull request.

## Citation

If you use Waveflow in your research, please cite:

```bibtex
@software{waveflow,
  title  = {Waveflow: RIS-Assisted Wireless Network Simulator with Beam Sweeping, OFDM Waveform Simulation, and ML-Guided Beam Optimization},
  author = {Mohd Adil Mokti},
  year   = {2026},
  url    = {https://github.com/nqmn/waveflow}
}
```

## License

Apache 2.0 — see [LICENSE](LICENSE)
