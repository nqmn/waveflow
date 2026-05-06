# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Waveflow v2.0 is an advanced wireless propagation, waveform, and RIS-assisted network simulator. The package was formerly published as RISNet; the `risnet` package name is retained as a backward-compatibility alias. Core physics, beam sweeping algorithms, pathfinding, OFDM waveform simulation, and MATLAB integration are all included.

## Build, Test, and Run Commands

### Installation & Setup
```bash
# Install as CLI tool (editable mode for development)
pip install -e .

# Install with ML support
pip install -e ".[ml]"

# Install with web interface
pip install -e ".[web]"

# Install with Typer/Rich terminal UI
pip install -e ".[terminal]"

# Install all dependencies (including dev tools)
pip install -e ".[all]"
```

### Running the Simulator
```bash
# CLI mode (interactive, default)
waveflow
waveflow --cli
risnet          # backward-compatible alias

# Web interface (http://127.0.0.1:5000)
waveflow --web

# Modern Typer/Rich terminal commands
waveflow --terminal status
waveflow ui demo-connect

# Load topology on startup
waveflow --cli --topology examples/json/example_1_simple.json

# Run direct command and exit
waveflow testall --exec-only
```

### Testing & Code Quality
```bash
# Run pytest test suite
pytest tests/ -v
pytest tests/test_physics_fixes.py

# Run individual test files
python tests/test_de_localization_sweep.py
python tests/test_adaptive_with_ml.py
python tests/evaluate_model_performance.py

# Code quality checks
black . --check  # Format check
flake8 .         # Linting
mypy core/ controller/ --check-untyped-defs

# Run example scripts
python examples/script/example_10_waveform_level.py
python examples/script/example_14_full_integration.py
```

## Architecture Overview

### Core Separation of Concerns

**`core/`** - Low-level physics, propagation models, and network nodes
- `network.py` - Network manager, node registry, connectivity orchestration
- `nodes.py` - AccessPoint, RIS, UE node classes with properties
- `physics.py` - Propagation models (FSPL, atmosphere, Rician, quantization loss, array gain)
- `environment.py` - Walls, obstacles, line-of-sight checking
- `waveform.py` - OFDM signal generation and channel simulation
- `feedback_channel.py` - UE→AP feedback modeling
- `validation.py` - Topology and physics validators
- `angle_utils.py` - Angle normalization, FOV checking, offset conversion
- `signal_processor.py` - Signal processing utilities
- `snr_messaging.py` - SNR message passing
- `ue_receiver.py` - UE receiver model
- `arq_handler.py` - ARQ (Automatic Repeat reQuest) handler
- `adaptive_impairments.py` - Adaptive impairment models
- `quantization/` - (Optional plugin system for custom quantizers)

**`controller/`** - High-level orchestration and algorithms
- `ris_controller.py` - Main orchestrator: pathfinding + beam optimization
- `waveform_controller.py` - Waveform-level SNR and sweep operations
- `beam_tracker.py` - Beam tracking algorithms
- `power_controller.py` - Power management and control
- `adaptive_controller.py` - Adaptive system control
- **`pathfinding/`** - Routing algorithms (registry-based)
  - `base.py`, `dijkstra.py`, `astar.py`, `greedy.py`, `exhaustive.py`
  - `registry.py` - Algorithm factory
- **`beamsweeping/`** - Beam sweep algorithms (registry-based)
  - `algorithms/` - All sweep implementations
  - `base.py`, `registry.py` - Framework
  - `ml/` - ML predictors (RF, XGBoost, SVR, MLP, GMF, VGMF, LGBM, etc.)
  - `common.py` - Shared utilities
- **`beamforming/`** - Beamforming engine (`engine.py`)
- **`beamtracking/`** - Beam tracking module
- **`ris_phase/`** - RIS phase management
  - `phase_steering.py` - Geometric phase computation
  - `phase_optimization.py` - CVXPY-based optimization
  - `phase_hybrid.py` - Hybrid phase approach
  - `phase_manager.py` - Phase manager orchestrator
  - `phase_quantization.py` - Phase quantization utilities

**`risnet/`** - High-level clean API (primary public interface)
- `__init__.py` - `RISnet` class, `Topology` — user-facing API
- `__main__.py` - Entry point for both `waveflow` and `risnet` CLI commands
- `cli.py` - Cmd-based interactive shell
- `terminal_cli.py` - Optional Typer/Rich terminal command surface
- `arrays/` - Array geometry, quantization, steering helpers
- `channels/` - Channel base classes and link budget

**`waveflow/`** - Forward-looking package alias
- Re-exports everything from `risnet` for the new package name
- `arrays/`, `channels/` - Mirrors `risnet` subpackages

**`app/`** - Web interface (Flask-based, optional `[web]` extra)
- `__init__.py` - Flask app factory
- `api/bp.py` - REST API endpoints (/api/*)
- `web/bp.py` - HTML UI templates
- `thread_safe_network.py` - Thread-safe network wrapper for concurrency
- `state_manager.py` - Network state persistence
- `validators.py` - Input validation

**`cli/`** - Legacy interactive command-line interface (Cmd-based)
- `main_shell.py` - Main shell, `RISNetCLI` class
- `connection_handler.py` - Connection orchestration
- `helpers.py` - Shared CLI utilities
- `ap_shell.py` - Access Point-specific commands
- `ris_shell.py` - RIS-specific commands
- `ue_shell.py` - User Equipment-specific commands
- `matlab_commands.py` - MATLAB bridge commands
- `test_suite.py` - Built-in test suite (testall, etc.)
- `video_stream.py` - Video streaming simulation

**`utils/`** - Shared utilities
- `link_budget.py` - Link budget calculations
- `csi.py` - Channel State Information helpers
- `rssi.py` - RSSI utilities
- `snr.py` - SNR helpers
- `metric_selector.py` - Metric selection logic
- `aruco_utils.py` - ArUco marker utilities
- `cam_oa_marker.py`, `cam_oa_server.py`, `camera_stream_server.py` - Camera/streaming tools

**`config/`** - Configuration management
- `config.py` - Config loader and schema

**`risformula/`** - Standalone formula and pattern implementations
- `localization_de.py` - DE localization formulas
- `pattern_gen_hybrid.py` - Hybrid pattern generation
- `archived/` - Legacy implementations

## Key Concepts

### Beam Sweeping Algorithm Plugin System
Located in `controller/beamsweeping/`, uses registry pattern for dynamic discovery.

**Available algorithms**:

| Name | Aliases | Description |
|---|---|---|
| `linear` | `brute-force` | Uniform angle steps |
| `coarse-fine` | `two-phase`, `center-out`, `adaptive` | Coarse then fine refinement (default) |
| `de` | `differential-evolution`, `de-localization` | Differential Evolution optimization |
| `ml` | `ml-guided`, `gmf` | ML predictor with refinement |
| `edge` | `edge-center`, `directional-search`, `exhaustive` | Directional exhaustive search |
| `hierarchical` | `hierarchical-sweep`, `hierarchical-refinement` | Hierarchical multi-resolution sweep |
| `adaptive-directional` | `directional`, `refinement`, `adaptive-refinement` | Adaptive directional refinement |
| `prime` | `prime-inference`, `power-ris-estimation`, `anm` | PRIME localization |
| `hog` | `human`, `hog_human` | HOG human detection sweep |
| `opencv` | `vision`, `aruco` | OpenCV/ArUco vision sweep |

**All algorithms return**:
```python
{
    'local_coarse': [...],      # Coarse phase angles
    'snr_coarse': [...],        # SNR for coarse angles
    'pwr_coarse': [...],        # Power for coarse angles
    'local_fine': [...],        # Fine phase angles
    'snr_fine': [...],          # SNR for fine angles
    'best_local_fine': float,   # Best angle (degrees)
    'best_snr_fine': float      # Best SNR (dB)
}
```

**To add a new algorithm**:
1. Create `controller/beamsweeping/algorithms/my_algorithm.py`
2. Inherit from `SweepAlgorithmBase`, set `name` and `description` properties
3. Implement `sweep(ap_name, ris_name, ue_name, fov=60, step=10, **kwargs) -> Dict`
4. Decorate class with `@register_algorithm("my-algo", aliases=("alias",))`
5. Import in `algorithms/__init__.py`

**Reference**: See `controller/beamsweeping/ALGORITHM_TEMPLATE.md` for detailed template.

### Network Connection Flow
```python
# CLI command: connect AP1 RIS1 UE1 --sweep 60 10 --algo coarse-fine
# ↓
# cli/main_shell.py:do_connect() parses arguments
# ↓
# cli/connection_handler.py:handle_connect() orchestrates
# ↓
# If --sweep: get algorithm from registry, call sweep()
# Otherwise: network.connect() for direct connection
# ↓
# Results formatted and displayed with tables
```

### Pathfinding
Located in `controller/pathfinding/`, uses registry pattern:
- `dijkstra` - Optimal SNR paths
- `astar` - A* with heuristics
- `greedy` - Fast approximations
- `exhaustive` - Brute-force all paths (small networks only)

```python
from controller.pathfinding import get_algorithm
algo = get_algorithm('dijkstra')
result = algo.find_path(graph, source, target, node_positions)
```

### RIS Phase Management
Located in `controller/ris_phase/`:
1. `phase_steering.py` - Geometric phase computation
2. `phase_optimization.py` - CVXPY-based optimization
3. `phase_hybrid.py` - Hybrid approach combining steering and optimization
4. `phase_manager.py` - Orchestrates phase subsystems
5. `phase_quantization.py` - Quantization of phase states

### MATLAB Integration Pattern
```python
from matlab_integration import MatlabBridge
bridge = MatlabBridge.get_instance()  # Lazy-loaded; MATLAB starts on first use
bridge.plot_beam_pattern(...)
```

### Network State Management
- **CLI mode**: Saves/loads from `.risnet_network.json`
- **Web mode**: Uses `WebStateManager` for persistence

### ML Beam Prediction
Located in `controller/beamsweeping/ml/`:
- `rf.py` - Random Forest
- `xgb.py` / `vxgb.py` - XGBoost variants
- `svr.py` - Support Vector Regression
- `gmf.py` / `vgmf.py` / `kgmf.py` - GMF variants
- `lgbm.py` - LightGBM
- `knn.py` - K-Nearest Neighbours
- `lr.py` - Linear Regression
- `trivial.py` - Trivial baseline
- `smart_predictor.py` - Auto-selects best predictor
- `dt.py` - Decision Tree
- `base.py` - Base predictor interface
- Models stored in `controller/beamsweeping/ml/models/`

### Angle Conventions
**CRITICAL**: Two angle reference systems are in use:
1. **Absolute angles** - Global coordinate system (0° = +X axis, CCW positive)
2. **Offset angles** - Relative to node's `normal_angle_deg` (boresight direction)

Helper functions in `core/angle_utils.py`:
- `normalize_angle_to_pm180()` - Normalize to [-180, 180]
- `compute_offset_from_normal()` - Convert absolute to offset
- `is_within_fov()` - Check if angle is within FOV
- `compute_absolute_angle_from_offset()` - Convert offset to absolute

### Waveform-Level Simulation
`core/waveform.py` and `controller/waveform_controller.py`:
- 256-subcarrier OFDM with QPSK modulation
- Channel models: AWGN, 3GPP-UMi, custom multipath
- RIS reflection with mutual coupling
- Reproducible with `set_deterministic_seeds()`

## Important Implementation Details

### Entry Points
`pyproject.toml` defines two CLI entry points:
```toml
[project.scripts]
waveflow = "waveflow.__main__:main"   # Primary (new name)
risnet   = "risnet.__main__:main"     # Backward-compatible alias
```
Both resolve to the same `main()` function in `risnet/__main__.py`.

### High-Level API (`risnet` / `waveflow`)
```python
from risnet import RISnet, Topology   # or: from waveflow import RISnet

net = RISnet()
ap  = net.addAP('ap1', position=(0, 0))
ris = net.addRIS('ris1', position=(5, 0))
ue  = net.addUE('ue1', position=(10, 3))
net.start()
paths  = net.findPaths(ap, ue)
result = net.connect(ap, ris, ue)
net.stop()
```

### Low-Level API (`core` / `controller`)
```python
from core import RISNetwork
from controller.ris_controller import RISController

net = RISNetwork()
controller = RISController(net, net.environment)
net.set_controller(controller)

net.add_ap('AP1', x=0, y=0)
net.add_ris('R1', x=5, y=0, N=16, bits=2)
net.add_ue('UE1', x=10, y=3)

paths = controller.find_all_paths('AP1', 'UE1', algorithm='dijkstra')
```

### Connect Command
```bash
connect AP1 RIS1 UE1                            # Auto beam angle
connect AP1 RIS1 UE1 --beam 45.2               # Explicit beam angle
connect AP1 RIS1 UE1 --sweep 60 10             # Sweep (default algo: coarse-fine)
connect AP1 RIS1 UE1 --sweep 60 10 --algo de   # Specific sweep algorithm
connect AP1 RIS1 UE1 --sweep 60 10 --algo ml-guided --ml-predictor rf
```

### Sweep Command Arguments
```bash
sweep AP1 RIS1 UE1 60 10 --algo de M=32 target_snr_db=25
```

### Adding New CLI Commands
1. Add `do_commandname()` method to `cli/main_shell.py`
2. Add docstring for help text
3. Parse arguments with `shlex`
4. Call network or controller methods
5. Format and print results

### Thread Safety in Web Mode
All network access in web mode must go through `ThreadSafeNetwork` and `ThreadSafeController`:
- Wraps `RISNetwork` / `RISController` with locks
- Used automatically by Flask app

### Topology Files
```json
{
  "nodes": {
    "ap1": {"type": "ap", "x": 0, "y": 0, "power_dBm": 20},
    "ris1": {"type": "ris", "x": 5, "y": 0, "N": 16, "bits": 2},
    "ue1": {"type": "ue", "x": 10, "y": 3}
  },
  "walls": [
    {"start": [2, -2], "end": [2, 2], "attenuation_dB": 20}
  ]
}
```

## Physics Models (`core/physics.py`)

- `path_loss_dB(distance, freq_GHz)` - Free space path loss (FSPL)
- `atmospheric_loss_dB(distance, freq_GHz)` - Atmospheric absorption (ITU)
- `rician_fading(K_factor_dB)` - Rician fading with K-factor
- `quantization_loss_dB(bits)` - Phase shifter quantization loss (RMS-based)
- `array_gain_dBi(N_elements)` - Antenna array gain
- `compute_snr_dB(...)` - Full link budget

**SNR Two-Level Approach**:
1. **System-level** (`network.connect()`): Simplified link budget, quick
2. **Waveform-level** (`waveform_controller.compute_waveform_snr()`): Full OFDM, per-subcarrier

## Debugging Tips

### Check Registered Algorithms
```python
from controller.beamsweeping import list_registered_algorithms
print(list_registered_algorithms())
```

### Enable Verbose Output
```python
result = network.connect(ap, ris, ue, verbose=True)
```

### Network State Inspection
```bash
list   # CLI command — shows all nodes
```

### MATLAB Bridge Status
```python
from matlab_integration import MatlabBridge
bridge = MatlabBridge.get_instance()
print(bridge._connected)
```

### Common Issues
1. **MATLAB not found**: Optional — fails gracefully if not installed
2. **Import errors**: Ensure `pip install -e .` from project root
3. **Sweep algorithm not found**: Check spelling; verify import in `algorithms/__init__.py`
4. **Angle FOV errors**: Beam angle must be within node's `max_angle_deg` FOV
5. **Web dependencies missing**: Install with `pip install -e ".[web]"` — flask/waitress are optional

## Code Conventions

### Naming
- **Modules**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions**: `snake_case()`
- **Constants**: `UPPER_CASE`
- **Test files**: `test_*.py` in `tests/`
- **Examples**: `example_N_topic.py` in `examples/script/`

### Code Style
- **Format**: Black (100-character lines)
- **Imports**: isort-compatible grouping (stdlib, third-party, local)
- **Type hints**: Recommended but not enforced
- **Docstrings**: Google-style for public APIs
- **Comments**: Avoid emojis; explain *why* not *what*; flag decisions with `# NOTE:` or `# WARNING:`

## Dependencies

**Core** (always installed):
- `numpy`, `scipy` - Numerical computation
- `pyyaml` - Configuration files

**Optional extras**:
- `[web]` - `flask`, `waitress`
- `[vision]` - `opencv-python`
- `[optimization]` - `cvxpy`, `scs`
- `[plot]` - `matplotlib`
- `[terminal]` - `typer`, `rich`
- `[ml]` - `torch>=1.9.0`, `scikit-learn`
- `[dev]` - `pytest`, `pytest-cov`, `black`, `flake8`, `mypy`, `matplotlib`

## Testing & Validation

```bash
pytest tests/ -v
pytest tests/test_physics_fixes.py::test_name -vv
pytest --cov=core --cov=controller --cov=app tests/
```

### Test Categories
- **Physics validation**: `test_physics_fixes.py`
- **Adaptive systems**: `test_adaptive_with_ml.py`
- **ML benchmarks**: `evaluate_model_performance.py`
- **DE sweep**: `test_de_localization_sweep.py`
- **Link budget**: `test_link_budget_channel.py`
- **Smoke tests**: `test_smoke.py`

### Reproducibility
Use `set_deterministic_seeds()` before waveform experiments — locks NumPy, Python `random`, and other RNG modules.
