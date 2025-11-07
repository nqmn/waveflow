# RISNet v2.0 - Advanced RIS Network Simulator

A modular, full-featured Reconfigurable Intelligent Surface (RIS) network simulator with advanced pathfinding algorithms, beam sweeping, and environment modeling.

## Features

### 🎯 Core Capabilities
- **Multi-Algorithm Pathfinding**: Dijkstra, A*, Greedy, Exhaustive search
- **Advanced Beam Sweeping**: Greedy adaptive search with CFAR detection
- **Environment Modeling**: Walls, obstacles, line-of-sight checking
- **Centralized Controller**: Intelligent network orchestration
- **Modular Architecture**: Clean, stackable Python modules

### 📊 Physics Models
- Free Space Path Loss (FSPL)
- Atmospheric absorption
- Rician fading
- RIS array gain with quantization loss
- Mutual coupling effects
- Beam steering angle loss

### 🌐 Web Interface
- Interactive 2D visualization
- Real-time metrics dashboard
- Drag-and-drop node positioning
- Path visualization
- Controller statistics

## Quick Links

- **[Quick Start](docs/QUICKSTART.md)** - Get started in 30 seconds
- **[Architecture](docs/ARCHITECTURE.md)** - Technical deep-dive
- **[Project Structure](docs/STRUCTURE.md)** - File organization
- **[Development Guide](docs/CLAUDE.md)** - For developers using Claude Code

## Architecture

```
risnet/
├── main.py             # Web interface + CLI entry point
├── risnet.py           # High-level Python API
│
├── core/               # Core physics & nodes
│   ├── nodes.py        # Node classes (AP, RIS, UE)
│   ├── network.py      # Network manager
│   ├── physics.py      # Propagation models
│   ├── environment.py  # Walls/obstacles
│   ├── waveform.py     # Waveform-level operations
│   └── quantization/   # ✓ Modular phase quantization (NEW)
│       ├── base.py
│       ├── uniform.py  # Standard quantization (default)
│       ├── legacy.py   # Backward compatible
│       ├── registry.py # Plugin registry & loader
│       └── plugins/    # Custom quantizers
│
├── controller/         # Control & decision-making
│   ├── ris_controller.py
│   ├── waveform_controller.py
│   │
│   ├── pathfinding/    # ✓ Pathfinding algorithms (MOVED HERE)
│   │   ├── base.py
│   │   ├── dijkstra.py
│   │   ├── astar.py
│   │   ├── greedy.py
│   │   ├── exhaustive.py
│   │   ├── engine.py
│   │   ├── registry.py
│   │   └── plugins/    # Custom algorithms
│   │
│   └── beamforming/    # ✓ Beamforming engines (MOVED HERE)
│       ├── engine.py
│       └── plugins/    # Custom beamformers
│
├── config/             # Configuration management
├── examples/           # Example scripts
├── tests/              # Test suite
├── docs/               # Documentation
└── requirements.txt    # Dependencies
```

### Architecture Improvements (v2.0+)

**✓ Clean Separation of Concerns:**
- `core/` = Low-level physics and network nodes
- `controller/` = High-level control decisions and algorithms
- `core/quantization/` = Modular, plugin-based phase quantization
- `controller/pathfinding/` = Semantic placement of routing algorithms
- `controller/beamforming/` = Semantic placement of beam optimization

**✓ Plugin System:**
- All major components support custom plugins
- `core/quantization/plugins/` - Add custom quantizers
- `controller/pathfinding/plugins/` - Add custom pathfinding algorithms
- `controller/beamforming/plugins/` - Add custom beamforming methods

**✓ Modular & Extensible:**
- Easy to add new quantization methods without modifying core
- Registry-based algorithm discovery
- Plugin auto-loading from folders

## Installation & Quick Start

### 1. Install RISNet

```bash
# Clone or navigate to the repository
cd risnet

# Install as a command-line tool
pip install -e .
```

### 2. Run the Simulator

```bash
# Option 1a: Interactive CLI (default)
risnet

# Option 1b: Direct command (non-interactive)
risnet testall                          # Quick test
risnet add ap ap1 0 0                   # Add access point
risnet help                             # Show commands

# Option 2: Web interface
risnet --web

# Then open browser to: http://127.0.0.1:5000

# Option 3: Use Python API
from risnet import RISnet
net = RISnet()
# ... your code
```

### 3. CLI Commands

You can use these commands either:
- **Interactively**: Type `risnet` then enter commands
- **Directly**: `risnet <command> [args]`

```bash
# Interactive mode
risnet
risnet> testall                                    # Quick test
risnet> add ap ap1 0 0                             # Add access point
risnet> add ris ris1 5 0 0 16 2                    # Add RIS surface
risnet> add ue ue1 10 3                            # Add user equipment
risnet> list                                       # List all nodes
risnet> connect ap1 ris1 ue1                       # Connect with beam sweep
risnet> sweep ap1 ris1 ue1 60 10                   # Perform beam sweeping
risnet> waveform_snr ap1 ris1 ue1 10               # Waveform-level SNR
risnet> waveform_compare ap1 ris1 ue1              # System vs Waveform comparison
risnet> waveform_beam_sweep ap1 ris1 ue1 30 10     # Waveform-level beam sweep
risnet> waveform_validate                          # Validate topology & physics
risnet> help                                       # Show all commands
risnet> quit                                       # Exit

# Direct command mode (non-interactive)
risnet testall                          # Quick test
risnet waveform_snr ap1 ris1 ue1        # Run waveform SNR calculation
risnet help                             # Show all commands
```

### Waveform-Level Commands (System ↔ Waveform Cross-Validation)

**Both CLI and web interface** support identical waveform-level operations:

| Command | CLI | Web API | Purpose |
|---------|-----|---------|---------|
| `waveform_snr` | ✓ | `/api/waveform/snr` | OFDM-based SNR with quantization effects |
| `waveform_compare` | ✓ | `/api/waveform/compare` | Compare system-level vs waveform-level |
| `waveform_beam_sweep` | ✓ | `/api/waveform/beam_sweep` | Per-angle SNR evaluation |
| `waveform_validate` | ✓ | `/api/waveform/validate` | Topology & physics validation |

**Example Usage:**

```bash
# CLI: Interactive setup and test
$ risnet
risnet> add ap AP1 0 0 0
risnet> add ris R1 5 0 0 8 2
risnet> add ue UE1 10 0 0
risnet> waveform_snr AP1 R1 UE1 20           # 20 OFDM symbols
risnet> waveform_beam_sweep AP1 R1 UE1 30 5  # ±30° sweep, 5° steps

# CLI: Direct command
$ risnet waveform_compare ap1 ris1 ue1

# Web: Access via browser
$ risnet --web
# Then POST to http://127.0.0.1:5000/api/waveform/snr
# with JSON: {"ap": "ap1", "ris": "ris1", "ue": "ue1", "num_symbols": 10}
```

### testall Command Example

```bash
$ risnet
Welcome to RISNet CLI. Type help or ? to list commands.
risnet> testall

============================================================
Testing Network Connectivity
============================================================

*** Setting up test network...
  Adding AP...
  Adding RIS...
  Adding UE...

*** Network nodes:
ap1        AccessPoint('ap1', pos=[0.0, 0.0, 0.0])
ris1       RIS('ris1', pos=[5.0, 0.0, 0.0])
ue1        UE('ue1', pos=[10.0, 3.0, 0.0])

*** Testing connectivity (AP -> RIS -> UE)...

✓ Connection successful!
  Path: ap1 -> ris1 -> ue1
  Distances:
    AP to RIS: 5.00 m
    RIS to UE: 5.83 m
    Total: 10.83 m
  SNR: 24.8 dB
  Power: -66.1 dBm
  Beam Angle: 31.0°

============================================================
```

### 4. Command Reference

```bash
# Show help
risnet --help

# Run CLI mode (default - interactive)
risnet
risnet --cli

# Run web interface
risnet --web

# Run with custom config
risnet --web --config config.yaml

# Use Python API
python -c "from risnet import RISnet; net = RISnet()"

# Run examples
python examples/run_all.py
```

## Quick Start

### Example 1: Basic Setup

```python
from core import RISNetwork, AccessPoint, RIS, UE
from controller import RISController

# Create network
net = RISNetwork()

# Add nodes
net.add_ap('ap1', x=0, y=0)
net.add_ris('ris1', x=5, y=0, N=16, bits=2)
net.add_ue('ue1', x=10, y=3)

# Create controller
controller = RISController(net)
net.set_controller(controller)

# Find paths
paths = controller.find_all_paths('ap1', 'ue1', algorithm='dijkstra')
print(f"Found {len(paths)} paths")
```

### Example 2: With Environment

```python
# Add walls
net.add_wall(start=[2, -2], end=[2, 2], attenuation_dB=20)

# Find paths (will avoid walls)
paths = controller.find_all_paths('ap1', 'ue1', algorithm='astar')
```

### Example 3: Beam Sweeping

```python
from controller.beamforming import BeamformingEngine
from controller.beamsweeping import compute_snr  # Shared calibrated helper
import numpy as np

# Perform greedy beam sweep (uses compute_snr by default, but passed here explicitly)
result = BeamformingEngine.greedy_beam_sweep(
    pos1=np.array([0, 0, 0]),
    pos2=np.array([10, 3, 0]),
    node1='ris1',
    node2='ue1',
    compute_snr_fn=compute_snr,
    ap_pos=np.array([-5, 0, 0]),
    max_angle_deg=60
)

print(f"Best angle: {result['best_angle']:.1f}°")
print(f"Best SNR: {result['best_snr_dB']:.1f} dB")
```
`compute_snr_fn` now defaults to `controller.beamsweeping.compute_snr`, so you can omit the argument unless you need a custom propagation model.

## API Reference

### REST API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/nodes` | GET | Get all nodes |
| `/api/add` | POST | Add node (AP/RIS/UE) |
| `/api/connect` | GET | Legacy AP→RIS→UE connection |
| `/api/sweep` | GET | Legacy beam sweep |
| `/api/find_paths` | GET | Find paths with algorithm |
| `/api/update_position` | POST | Update node position |
| `/api/walls/add` | POST | Add wall |
| `/api/walls/clear` | POST | Clear all walls |
| `/api/config` | GET/POST | Get/update configuration |

### Pathfinding Algorithms

#### Dijkstra (Optimal)
```python
result = PathfindingEngine.dijkstra(graph, source, target, node_positions)
```
- **Best for**: Optimal SNR paths
- **Complexity**: O(E log V)
- **Guarantees**: Optimal path

#### A* (Heuristic)
```python
result = PathfindingEngine.astar(graph, source, target, node_positions)
```
- **Best for**: Fast optimal search
- **Complexity**: O(E log V) with good heuristic
- **Guarantees**: Optimal with admissible heuristic

#### Greedy (Fast)
```python
result = PathfindingEngine.greedy(graph, source, target, node_positions)
```
- **Best for**: Quick approximations
- **Complexity**: O(V)
- **Guarantees**: None (may be suboptimal)

#### Exhaustive (All Paths)
```python
result = PathfindingEngine.exhaustive(graph, source, target, node_positions, max_hops=4)
```
- **Best for**: Small networks, comparison
- **Complexity**: O(V!)
- **Guarantees**: Finds all paths

### Configuration

```yaml
# config.yaml
controller:
  enabled: true
  algorithm: dijkstra  # dijkstra, astar, greedy, exhaustive
  strategy: max-snr    # max-snr, min-hops, min-loss
  use_beam_sweep: true

environment:
  frequency_GHz: 5.8
  bandwidth_MHz: 20
  tx_power_dBm: 20
  noise_figure_dB: 10

ris:
  default_N: 16
  default_bits: 2
  default_max_angle_deg: 60
  active_mode: false
  amplifier_gain: 1.0
```

## Module Documentation

### Core Modules

#### `core.physics.Physics`
Physical propagation models:
- `path_loss_dB(distance, freq)` - Free space path loss
- `atmospheric_loss_dB(distance, freq_GHz)` - Atmospheric absorption
- `rician_fading(K_factor_dB)` - Rician fading channel
- `quantization_loss_dB(phase_bits)` - Phase quantization loss
- `compute_snr_dB(...)` - SNR calculation

#### `core.nodes`
- `Node` - Base node class
- `AccessPoint` - AP with transmit power
- `RIS` - RIS surface with phase control
- `UE` - User equipment

#### `core.environment.Environment`
- `add_wall(start, end, attenuation_dB)` - Add obstacle
- `check_line_of_sight(pos1, pos2)` - LOS check
- `get_blocked_paths(pos1, pos2)` - Get blocking walls

### Algorithm Modules

#### `controller.pathfinding.PathfindingEngine`
- `dijkstra(graph, source, target, positions)` - Dijkstra's algorithm
- `astar(graph, source, target, positions)` - A* search
- `greedy(graph, source, target, positions)` - Greedy search
- `exhaustive(graph, source, target, positions)` - Exhaustive search

#### `controller.beamforming.BeamformingEngine`
- `greedy_beam_sweep(...)` - Adaptive beam search
- `cfar_detection(measurements, peak_idx)` - CFAR validation
- `simple_beam_sweep(...)` - Legacy uniform sweep

### Quantization Module

#### `core.quantization` (NEW - Modular Plugin System)
- `UniformQuantizer` - Standard uniform quantization (default)
- `LegacyQuantizer` - Original RISNet formula (backward compatible)
- `get_quantizer(name)` - Get quantizer by name
- `list_quantizers()` - List all available quantizers
- `load_quantizers_from_folder(path)` - Load custom quantizer plugins
- Plugin system allows easy addition of custom quantization methods

### Controller Module

#### `controller.RISController`
- `find_all_paths(ap, ue, algorithm)` - Find all viable paths
- `select_best_path(paths, strategy)` - Select optimal path
- Controller statistics tracking

## Performance

### Benchmarks (1 AP, 5 RIS, 1 UE)

| Algorithm | Time | Paths Found | Optimal? |
|-----------|------|-------------|----------|
| Dijkstra | 12 ms | 1 | ✓ |
| A* | 8 ms | 1 | ✓ |
| Greedy | 2 ms | 1 | ✗ |
| Exhaustive | 45 ms | 32 | ✓ |

## Comparison: HTML vs Python

| Feature | HTML Simulator | main-web-v2.py |
|---------|----------------|----------------|
| **Architecture** | Single-file JS | Modular Python |
| **Pathfinding** | ✓ | ✓ |
| **Beam Sweeping** | ✓ (CFAR) | ✓ (CFAR) |
| **Walls/Obstacles** | ✓ | ✓ |
| **Extensibility** | ✗ Limited | ✓ Easy |
| **ML Integration** | ✗ Hard | ✓ Easy |
| **Testing** | ✗ Hard | ✓ Easy (pytest) |
| **Scalability** | ✗ Browser-limited | ✓ Server-side |
| **API** | ✗ None | ✓ REST API |
| **Database** | ✗ None | ✓ Easy to add |

## Testing

```bash
# Run tests (when implemented)
pytest tests/

# With coverage
pytest --cov=core --cov=algorithms --cov=controller tests/
```

## Extending the Simulator

### Adding a Custom Quantizer (Plugin System)

**New modular approach - no core modification needed!**

```python
# File: core/quantization/plugins/my_quantizer/quantizer.py
import numpy as np
from core.quantization.base import BaseQuantizer

class Quantizer(BaseQuantizer):
    """My custom quantization strategy"""

    def __init__(self):
        super().__init__(
            name='my_quantizer',
            description='My custom quantization method'
        )

    def quantize(self, ideal_phases, bits):
        # Your quantization logic here
        num_levels = 2 ** bits
        phase_step = 2 * np.pi / num_levels

        quantized = np.round(ideal_phases / phase_step) * phase_step
        quantized = np.mod(quantized, 2 * np.pi)
        states = (quantized / phase_step).astype(int) % num_levels

        return quantized, states
```

Then load and use it:
```python
from core.quantization import load_quantizers_from_folder

load_quantizers_from_folder('core/quantization/plugins')
ris = RIS('R1', x=5, y=5, quantizer_name='my_quantizer')
```

### Adding a Custom Pathfinding Algorithm (Plugin System)

**New modular approach - controller plugin system!**

```python
# File: controller/pathfinding/plugins/my_algorithm/algorithm.py
from controller.pathfinding.base import PathfindingAlgorithm

class MyAlgorithm(PathfindingAlgorithm):
    """My custom pathfinding algorithm"""

    name = "my_algorithm"
    description = "My custom pathfinding method"

    @staticmethod
    def find_path(graph, source, target, node_positions):
        # Your algorithm implementation
        path = [source, ..., target]
        total_loss = ...
        total_length = ...

        return {
            'path': path,
            'totalLoss': total_loss,
            'totalLength': total_length
        }
```

### Adding Custom Physics Models

```python
# core/physics.py

class Physics:
    @staticmethod
    def custom_loss_model(distance, freq, ...):
        # Your model here
        return loss_dB
```

### Adding New Node Types

```python
# core/nodes.py

class Relay(Node):
    def __init__(self, name, x, y, z=0.0, gain_dB=10):
        super().__init__(name, x, y, z)
        self.gain_dB = gain_dB
```

## Troubleshooting

### Import Errors
```bash
# Make sure you're in the risimulator directory
cd /path/to/risimulator

# Install dependencies
pip install -r requirements.txt
```

### Port Already in Use
```python
# Change port in main-web-v2.py or:
python main-web-v2.py --web --port 8080  # (if implemented)
```

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new features
4. Submit pull request

## License

MIT License - see LICENSE file

## Citation

If you use this simulator in your research, please cite:

```bibtex
@software{risnet_v2,
  title = {RISNet v2.0: Advanced RIS Network Simulator},
  author = {Your Name},
  year = {2024},
  url = {https://github.com/yourusername/risimulator}
}
```

## Acknowledgments

- Original concept from RIS Simulator v1.5.0 (HTML version)
- Physics models based on ITU recommendations
- Pathfinding algorithms from computer science literature

## Waveform-Level Simulation

### Waveform Examples

Run comprehensive waveform-level examples demonstrating OFDM, multipath propagation, and RIS-assisted communication:

```bash
python examples/script/example_waveform_level.py
```

This script demonstrates:
1. **OFDM Signal Generation** - 256-subcarrier OFDM with QPSK modulation
2. **Multipath Channel Modeling** - AWGN, 3GPP-UMi, and custom models
3. **RIS Reflection with Coupling** - 8×8 array with 2-bit phase shifters
4. **Antenna Array Patterns** - ULA/UPA gain and beamwidth analysis
5. **System vs Waveform Comparison** - Reproducible cross-validation
6. **Beam Optimization** - Angle-dependent SNR sweeping
7. **Physics Validation** - Topology and propagation verification

### Key Improvements (Recent)

#### ✓ Reproducible Results
- Global random seed lock (`set_deterministic_seeds()`)
- Locks NumPy, Python `random`, and other RNG modules
- System SNR computed once and reused across examples (13.95 dB)

#### ✓ Physics Clarity
- **ULA 3dB Beamwidth**: Numeric array factor (~6.3°) documented vs. approximate formula (~6.8°)
- **Array Gain**: Clarifies per-element gain (~2.8 dBi) + directivity (~12 dB for 16 elements) = ~14.8 dBi
- **Quantization RMS**: Per-element (26.08°) distinguished from effective aperture RMS (32.93°)

#### ✓ Beam Sweep SNR Variation
- Fixed steering phase computation per angle
- Plausible variation observed: 39.10 dB (±15°) → 38.97 dB (±5°)
- Symmetric geometry produces symmetric SNR (e.g., -15° ≈ +15°)

#### ✓ Waveform Controller Enhancements
- Added `beam_angle_deg` parameter to `compute_waveform_snr()`
- Per-angle RIS phase shifts now applied in beam sweep
- Optional path vs. steering-based phase computation

### Example Output (Seed=42)

```
RISNet v2.0 - Waveform-Level Simulation Examples
(Random seed: 42 — results are reproducible across all modules)

EXAMPLE 3: RIS Reflection Model with Coupling
  RMS quantization error (per-element, uniform phases): 26.08°
    → Matches theory: Δφ/√12 = 90°/√12 ≈ 25.98°

EXAMPLE 4: Antenna Array Radiation Patterns
  ULA 3dB beamwidth (numeric from AF): ~6.3°
  Note: Numeric value from array factor ≈ 6.3°; approximate formula ≈ 6.8°

EXAMPLE 5: System-Level vs Waveform-Level Comparison
  System-level SNR: 13.95 dB (computed once, reused in Example 7)
  Quantization error RMS: 32.93° (effective aperture RMS with coupling)

EXAMPLE 6: RIS Beam Optimization
  Angle  -15.0°: SNR =   39.10 dB <-- BEST
  Angle   -5.0°: SNR =   38.97 dB
  Angle    5.0°: SNR =   38.97 dB
  Angle   15.0°: SNR =   39.10 dB

EXAMPLE 7: Validation and Reporting
  System-level SNR: 13.95 dB (matches Example 5 for consistency)
```

### Mathematical Notes

#### 3dB Beamwidth (HPBW)
For ULA with N elements and spacing d:
- **Approximate formula**: HPBW ≈ 0.886 × λ / L (where L = N × d × λ)
- **Numeric array factor**: Compute full AF and find −3 dB points (more accurate)
- **Example**: 16 elements, d = 0.5λ, L = 8λ → HPBW ≈ 6.8° (formula) vs 6.3° (numeric)

#### Quantization Error RMS
For uniform quantization with phase step Δφ = 2π / 2^b:
- **Per-element RMS**: σ = Δφ / √12 (treating each element independently)
- **Effective aperture RMS**: May be higher if including mutual coupling or phase weighting across optimal paths
- **Example (2-bit)**: Δφ = 90° → σ_theory ≈ 26.01°

## Roadmap

### v2.1 (Planned)
- [ ] 3D visualization
- [ ] Real-time collaboration
- [ ] Machine learning integration
- [ ] Performance optimization
- [ ] Comprehensive test suite
- [x] Waveform-level OFDM simulation
- [x] Reproducible random seeding
- [x] Physics validation and clarity

### v2.2 (Future)
- [ ] Multi-user support
- [ ] Experiment database
- [ ] Automated reporting
- [ ] Integration with SDR hardware

## Contact

- Issues: https://github.com/yourusername/risimulator/issues
- Email: your.email@example.com
