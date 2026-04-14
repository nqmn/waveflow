# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RISNet v2.0 is an advanced Reconfigurable Intelligent Surface (RIS) network simulator with modular architecture, beam sweeping algorithms, pathfinding, and MATLAB integration for electromagnetic analysis.

## Build, Test, and Run Commands

### Installation & Setup
```bash
# Install as CLI tool (editable mode for development)
pip install -e .

# Install with ML support
pip install -e ".[ml]"

# Install all dependencies (including dev tools)
pip install -e ".[all]"
```

### Running the Simulator
```bash
# CLI mode (interactive)
risnet
python main.py --cli

# Web interface (http://127.0.0.1:5000)
risnet --web
python main.py --web

# Load topology on startup
python main.py --cli --topology examples/json/example_1_simple.json

# Run direct command
risnet testall
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
- `waveform_controller.py` - OFDM SNR computation, waveform-level beam sweep
- `feedback_channel.py` - UE→AP feedback modeling
- `validation.py` - Topology and physics validators
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
  - `plugins/` - Custom algorithm plugins
- **`beamsweeping/`** - Beam sweep algorithms (registry-based)
  - `algorithms/` - Linear, adaptive, DE, ML-guided, etc.
  - `base.py`, `registry.py` - Framework
  - `ml/` - ML predictors (RF, XGBoost, SVR, MLP)
  - `common.py` - Shared utilities

**`app/`** - Web interface (Flask-based)
- `__init__.py` - Flask app factory
- `api/bp.py` - REST API endpoints (/api/*)
- `web/bp.py` - HTML UI templates
- `thread_safe_network.py` - Thread-safe network wrapper for concurrency
- `state_manager.py` - Network state persistence
- `validators.py` - Input validation

**`cli/`** - Interactive command-line interface
- `__init__.py` - CLI module initialization
- `ap_shell.py` - Access Point-specific commands
- `ue_shell.py` - User Equipment-specific commands
- `test_suite.py` - Built-in test suite (testall, etc.)
- `video_stream.py` - Video streaming simulation

**`config/`** - Configuration management
- `config.py` - Config loader and schema
- Environment defaults

**`risformula/`** - Standalone formula and pattern implementations
- Phase computation formulas
- Pattern generation tools
- `archived/` - Legacy implementations

## Key Concepts

### Beam Sweeping Algorithm Plugin System
Located in `controller/beamsweeping/`, uses registry pattern for dynamic discovery:

**Architecture**:
1. **Base class**: `SweepAlgorithmBase` - Common interface for all sweeps
2. **Registry**: `registry.py` - Decorator-based algorithm registration
3. **Algorithms**: `algorithms/` - Individual implementations (linear, adaptive, DE, ML-guided, etc.)
4. **Loaders**: Auto-discovery from algorithms/ folder or explicit plugins/

**Available algorithms**:
- `linear` / `brute-force` - Uniform angle steps, coarse→fine refinement
- `adaptive` / `center-out` - Specular angle-centered search (~30% faster)
- `de` / `differential-evolution` - Population-based optimization
- `ml` / `ml-guided` - ML predictor (RF, XGBoost, SVR) with refinement
- `edge-center` - Directional exhaustive search
- `prime` - PRIME localization

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
5. Import in `__init__.py` or place in plugins/ for auto-discovery

**Reference**: See `controller/beamsweeping/README.md` for detailed template and examples.

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
Located in `controller/pathfinding/`, uses similar registry pattern:
- `dijkstra` - Optimal SNR paths (Dijkstra's algorithm)
- `astar` - A* with heuristics (optimal with admissible heuristic)
- `greedy` - Fast approximations (no optimality guarantee)
- `exhaustive` - Brute-force all paths (small networks only)

Usage:
```python
from controller.pathfinding import get_algorithm
algo = get_algorithm('dijkstra')
result = algo.find_path(graph, source, target, node_positions)
```

### RIS Phase Management
Two separate systems:
1. **Phase Steering** (`controller/ris_phase/phase_steering.py`) - Geometric phase computation
2. **Phase Optimization** (`controller/ris_phase/phase_optimization.py`) - CVXPY-based optimization

### MATLAB Integration Pattern
The MATLAB bridge uses lazy loading to avoid startup cost:
```python
from matlab_integration import MatlabBridge
bridge = MatlabBridge.get_instance()  # Only starts MATLAB on first use
bridge.plot_beam_pattern(...)  # Engine starts here if not already running
```

### Network State Management
- **CLI mode**: Saves/loads from `.risnet_network.json`
- **Web mode**: Uses `WebStateManager` for persistence
- State includes nodes, positions, and active links

### ML Beam Prediction
Located in `controller/beamsweeping/ml/`:
- `rf.py` - Random Forest predictor (best performance)
- `xgb.py` - XGBoost (not yet implemented)
- `svr.py` - Support Vector Regression
- `mlp.py` - Neural network (PyTorch)
- `base.py` - Base predictor interface
- Models stored in `controller/beamsweeping/ml/models/`

### Angle Conventions
**CRITICAL**: The codebase uses two angle reference systems:
1. **Absolute angles** - Global coordinate system (0° = +X axis, CCW positive)
2. **Offset angles** - Relative to node's `normal_angle_deg` (boresight direction)

RIS and UE nodes have:
- `normal_angle_deg` - Antenna boresight direction (absolute)
- `max_angle_deg` - Field of view (±FOV from normal)

Helper functions in `core/angle_utils.py`:
- `normalize_angle_to_pm180()` - Normalize to [-180, 180]
- `compute_offset_from_normal()` - Convert absolute to offset
- `is_within_fov()` - Check if angle is within FOV
- `compute_absolute_angle_from_offset()` - Convert offset to absolute

### Waveform-Level Simulation
`core/waveform.py` and `controller/waveform_controller.py` provide OFDM simulation:
- 256-subcarrier OFDM with QPSK modulation
- Channel models: AWGN, 3GPP-UMi, custom multipath
- RIS reflection with mutual coupling
- System vs waveform cross-validation
- Reproducible with `set_deterministic_seeds()`

## Important Implementation Details

### Connect Command
The `connect` command supports multiple modes:
```bash
# Basic connection (auto beam angle)
connect AP1 RIS1 UE1

# With explicit beam angle
connect AP1 RIS1 UE1 --beam 45.2

# With beam sweep (algorithm defaults to 'coarse-fine')
connect AP1 RIS1 UE1 --sweep 60 10

# With specific sweep algorithm
connect AP1 RIS1 UE1 --sweep 60 10 --algo de

# ML-guided sweep
connect AP1 RIS1 UE1 --sweep 60 10 --algo ml-guided --ml-predictor rf
```

### Sweep Command Arguments
When adding sweep algorithm parameters in CLI:
- Use `--sweep FOV STEP` for sweep range
- Use `--algo NAME` to select algorithm
- Additional algorithm-specific kwargs passed as `key=value` pairs
- Example: `sweep AP1 RIS1 UE1 60 10 --algo de M=32 target_snr_db=25`

### Adding New CLI Commands
1. Add `do_commandname()` method to `cli/main_shell.py`
2. Add docstring for help text
3. Parse arguments (use `shlex` for complex parsing)
4. Call network or controller methods
5. Format and print results

### Thread Safety in Web Mode
All network access in web mode must go through `ThreadSafeNetwork`:
- Wraps `RISNetwork` with locks
- Used automatically by Flask app
- CLI mode uses direct network access (no locking needed)

### Git Workflow
The repository uses standard git workflow:
- Main branch: `main`
- Recent commit shows DE localization sweep implementation
- Modified file: `controller/beamsweeping/algorithms/de_localization_sweep.py`

### Python Entry Points
The package defines CLI entry point in `pyproject.toml`:
```toml
[project.scripts]
risnet = "risnet.__main__:main"
```
This allows `risnet` command after `pip install -e .`

### Topology Files
JSON topology format in `examples/json/`:
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

## Common Workflows

### Adding a Beam Sweep Algorithm
See `controller/beamsweeping/README.md` for comprehensive guide.

Quick template:
```python
# File: controller/beamsweeping/algorithms/my_algorithm.py
from ..base import SweepAlgorithmBase
from ..registry import register_algorithm

@register_algorithm("my-algo", aliases=("my-alias",))
class MyAlgorithmSweep(SweepAlgorithmBase):
    @property
    def name(self) -> str:
        return "My Algorithm"

    @property
    def description(self) -> str:
        return "My algorithm description"

    def sweep(self, ap_name, ris_name, ue_name, fov=60, step=10, **kwargs):
        # Sweep logic here
        ap, ris, ue = self.network.get(ap_name), self.network.get(ris_name), self.network.get(ue_name)
        # ... compute angles and SNR ...
        return {
            'local_coarse': angles,
            'snr_coarse': snrs,
            'pwr_coarse': powers,
            'local_fine': [...],
            'snr_fine': [...],
            'best_local_fine': float(best_angle),
            'best_snr_fine': float(best_snr)
        }
```

Usage: `risnet> sweep AP1 R1 UE1 60 10 --algo my-algo`

### Network Initialization (Python API)
```python
from core import RISNetwork
from controller.ris_controller import RISController

net = RISNetwork()
controller = RISController(net, net.environment)
net.set_controller(controller)

# Add nodes
net.add_ap('AP1', x=0, y=0)
net.add_ris('R1', x=5, y=0, N=16, bits=2)
net.add_ue('UE1', x=10, y=3)

# Find paths
paths = controller.find_all_paths('AP1', 'UE1', algorithm='dijkstra')
print(f"Found {len(paths)} paths")
```

### Adding New CLI Commands
1. Add `do_commandname()` method to main shell class (in `risnet/cli.py` or `risnet_cli.py`)
2. First parameter is always `self`, subsequent parameters become command arguments
3. Parse arguments using `shlex.split()` for complex input
4. Call network/controller methods
5. Format and print results

```python
def do_mycommand(self, args):
    """My command help text"""
    if not args:
        print("Usage: mycommand <node> <value>")
        return

    parts = args.split()
    node_name = parts[0]
    # ... implementation ...
```

### Phase Quantization
RIS nodes support configurable quantization:
- `bits` parameter in `add_ris()` - Number of phase bits (1, 2, 3, etc.)
- Quantization loss computed in `core/physics.py:quantization_loss_dB()`
- Loss estimated from theoretical RMS (uniform quantizer: σ = Δφ/√12)
- Actual phase states stored in RIS node after sweep

### Physics Models (`core/physics.py`)
Core propagation calculations used in both system-level and waveform-level simulations:
- `path_loss_dB(distance, freq_GHz)` - Free space path loss (FSPL)
- `atmospheric_loss_dB(distance, freq_GHz)` - Atmospheric absorption (ITU models)
- `rician_fading(K_factor_dB)` - Rician fading with K-factor
- `quantization_loss_dB(bits)` - Phase shifter quantization loss (RMS-based)
- `array_gain_dBi(N_elements)` - Antenna array gain (directivity + per-element gain)
- `compute_snr_dB(...)` - Full link budget: TX power - path loss - atmospheric loss ± gains - quantization - noise figure

**SNR Two-Level Approach**:
1. **System-level** (`network.connect()`): Simplified link budget, quick calculations
2. **Waveform-level** (`waveform_controller.compute_waveform_snr()`): Full OFDM with multipath, per-subcarrier, reproducible with seed locking

Both approaches validated to produce consistent results (see `examples/script/example_5_context_manager.py`).

## Debugging Tips

### Enable Verbose Output
```python
# In network.py, many methods accept verbose=True
result = network.connect(ap, ris, ue, verbose=True)
```

### Check Registered Algorithms
```python
from controller.beamsweeping import list_registered_algorithms
print(list_registered_algorithms())
```

### MATLAB Bridge Status
```python
from matlab_integration import MatlabBridge
bridge = MatlabBridge.get_instance()
print(bridge._connected)  # Check if engine is running
```

### Network State Inspection
```bash
# CLI command
list  # Shows all nodes

# Or in Python
net.list_nodes()
print(net.nodes)  # Dict of all nodes
```

### Common Issues
1. **MATLAB not found**: MATLAB integration is optional, will fail gracefully if not installed
2. **Import errors**: Ensure you're in project root or installed with `pip install -e .`
3. **Sweep algorithm not found**: Check spelling and that algorithm is imported in `__init__.py`
4. **Angle FOV errors**: Check that beam angle is within node's `max_angle_deg` FOV

## Project Status & Recent Changes

### Current State (v2.0+)
- **Main branch**: All core systems integrated and stable
- **Recent work**: DE (Differential Evolution) localization sweep algorithm (see `controller/beamsweeping/algorithms/de_localization_sweep.py`)
- **Modified files**: Check `git status` for uncommitted work
- **Test coverage**: Unit tests in `tests/`, example scripts in `examples/script/`

### Known Considerations
1. **Angle conventions**: Codebase mixes absolute (global) and relative (node-centric) angles. Always check context - RIS/UE use `normal_angle_deg` and `max_angle_deg` FOV
2. **Quantization**: RMS-based loss model (uniform quantizer, per-element). Coupling effects are configurable (typically off)
3. **ML predictors**: Require pre-trained models (RF, XGBoost, SVR). Auto-loaded if available in `controller/beamsweeping/ml/models/`
4. **MATLAB bridge**: Optional, lazy-loaded. Will fail gracefully if MATLAB not installed
5. **Web thread safety**: Must use `ThreadSafeNetwork` wrapper in Flask app, not direct network access

## Code Conventions

### Naming
- **Modules**: `snake_case.py` (e.g., `ris_controller.py`)
- **Classes**: `PascalCase` (e.g., `RISNetwork`, `SweepAlgorithmBase`)
- **Functions**: `snake_case()` (e.g., `compute_snr_dB()`)
- **Constants**: `UPPER_CASE` (e.g., `DEFAULT_FREQ_GHZ`)
- **Test files**: `test_*.py` in `tests/`
- **Examples**: `example_N_topic.py` in `examples/script/`

### Code Style
- **Format**: Black (100-character lines, see `pyproject.toml`)
- **Imports**: isort-compatible grouping (stdlib, third-party, local)
- **Type hints**: Recommended but not enforced
- **Docstrings**: Google-style for public APIs

### Comments
- Avoid emojis in comments (per project guidelines in `.claude/CLAUDE.md`)
- Explain *why* not *what* - code should be self-documenting
- Flag architectural decisions with `# NOTE:` or `# WARNING:`

## Dependencies

**Core** (required, see `pyproject.toml`):
- `numpy` - Numerical computation
- `flask` - Web framework
- `waitress` - Production WSGI server
- `pyyaml` - Configuration files
- `opencv-python` - Computer vision for ArUco/HOG sweep modes
- `cvxpy`, `scs` - Convex optimization for phase tuning

**Optional ML** (`pip install -e ".[ml]"`):
- `torch>=1.9.0` - Neural network (MLP predictor)
- `scikit-learn` - RF, SVR, LGBM predictors, utilities

**Development** (`pip install -e ".[all]"`):
- `pytest`, `pytest-cov` - Test framework
- `black`, `flake8`, `mypy` - Code quality

## Testing & Validation

### Test Execution
```bash
# Run all tests
pytest tests/ -v

# Run specific test with verbose output
pytest tests/test_physics_fixes.py::test_name -vv

# With coverage report
pytest --cov=core --cov=controller --cov=app tests/

# Run example validation
python examples/script/example_10_waveform_level.py
```

### Test Categories
- **Physics validation**: `test_physics_fixes.py` - FSPL, quantization, array gain
- **Adaptive systems**: `test_adaptive_with_ml.py` - Adaptive controller + ML integration
- **ML benchmarks**: `evaluate_model_performance.py` - Predictor accuracy
- **Integration**: `example_14_full_integration.py` - End-to-end workflow

### Reproducibility
- Use `set_deterministic_seeds()` before waveform experiments (global seed lock)
- Locks NumPy, Python `random`, and other RNG modules
- Critical for validating cross-module consistency (system vs waveform SNR)
