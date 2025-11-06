# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RISNet v2.0 is a modular Reconfigurable Intelligent Surface (RIS) network simulator with advanced pathfinding, beam sweeping, and physics modeling. It features a clean Python backend with a Flask web interface.

## File Organization

```
risnet/
├── main.py          ← Application entry point (web UI + CLI)
├── risnet.py        ← High-level Python API library
├── core/            ← Physics, nodes, networks, environment
├── algorithms/      ← Pathfinding and beam sweeping
├── controller/      ← Network orchestration
├── config/          ← Configuration management
├── examples/        ← Example scripts
├── tests/           ← Test suite
└── requirements.txt ← Dependencies
```

**Key Files:**
- `main.py` - Only entry point (runs Flask web server)
- `risnet.py` - Python library for programmatic use
- Everything else is modules imported by these two

## Common Development Commands

### Installation

```bash
# Install as command-line tool (one time)
pip install -e .
```

### Running the Application

```bash
# After installing: pip install -e .

# Interactive CLI (default)
risnet

# Direct commands (non-interactive)
risnet testall                  # Run test
risnet help                     # Show help
risnet add ap ap1 0 0           # Add node

# Web interface
risnet --web

# Alternative: run directly without installation
python main.py            # CLI (default)
python main.py --web      # Web interface
python main.py --cli      # CLI (same as default)
```

### CLI Commands

Available commands (works both interactively and directly):

```
testall                              Quick test: setup network and test
add <type> <name> <x> <y> [z]       Add nodes (type: ap, ris, ue)
list                                List all nodes
connect <ap> <ris> <ue> [angle]     Connect with beam sweep
sweep <ap> <ris> <ue> [fov step]    Perform beam sweeping
help [topic]                        Show help
exit / quit                         Exit interactive CLI
```

**Interactive Mode:**
```bash
risnet
risnet> testall
risnet> add ap ap1 0 0
risnet> list
risnet> quit
```

**Direct Mode:**
```bash
risnet testall
risnet add ap ap1 0 0
risnet help testall
```

### Running Examples

```bash
# Run a specific example
python examples/example_1_simple.py

# Run all examples (auto-discovered)
python examples/run_all.py
```

### Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_physics.py -v

# Run with coverage
pytest tests/ --cov=core --cov=algorithms --cov=controller

# Test auto-discovery of algorithms and examples
python tests/test_auto_discovery.py
```

### Installation & Dependencies

```bash
# Install dependencies
pip install -r requirements.txt

# Main dependencies: numpy, flask, pyyaml, waitress (production server)
```

## High-Level Architecture

### Module Hierarchy

```
main-web-v2.py (Flask Web App + API)
├── core/               ← Physics, nodes, network, environment
├── algorithms/         ← Pathfinding & beamforming
├── controller/         ← Network orchestration (RISController)
├── config/             ← Configuration management
└── risnet.py          ← High-level API
```

### Core Responsibilities

**`core/`** - Simulation foundations
- `physics.py`: Path loss, fading, RIS gain, SNR calculations (centralized)
- `nodes.py`: Node hierarchy (AccessPoint, RIS, UE)
- `network.py`: Network state management and node lifecycle
- `environment.py`: Walls/obstacles and line-of-sight checking

**`algorithms/`** - Optimization algorithms (auto-discovered)
- `base.py`: Abstract `PathfindingAlgorithm` class
- `registry.py`: Auto-discovery mechanism
- `dijkstra.py`, `astar.py`, `greedy.py`, `exhaustive.py`: Individual algorithm implementations
- `beamforming.py`: Beam steering with CFAR detection

**`controller/`** - Network intelligence
- `ris_controller.py`: Multi-path discovery, path selection strategies, statistics tracking
- Auto-loads algorithms via registry

**`config/`** - Configuration
- `config.py`: YAML-based configuration with dot-notation access

**`risnet.py`** - High-level API
- Alternative way to interact with the simulator

### Key Design Patterns

1. **Strategy Pattern** (Algorithms): Interchangeable pathfinding algorithms
2. **Facade Pattern** (Controller): Simplified interface to complex subsystems
3. **Registry Pattern** (Auto-discovery): Algorithms/examples discovered at import time
4. **Factory Pattern** (Network): Node creation via `add_ap()`, `add_ris()`, `add_ue()`
5. **Singleton** (Global state): `_net`, `_controller`, `_config` are global singletons

## Critical Code Flows

### Pathfinding Flow

```
API Request /api/find_paths?ap=ap1&ue=ue1&algorithm=dijkstra
  ↓
RISController.find_all_paths()
  ├─→ Build graph from network + LOS checking
  ├─→ Select algorithm from registry
  ├─→ Run algorithm (Dijkstra/A*/Greedy/Exhaustive)
  ├─→ Calculate SNR for each path using Physics.compute_snr_dB()
  └─→ Return sorted paths (best SNR first)
```

### Physics Calculation

All physics is centralized in `core/physics.py:Physics.compute_snr_dB()`:
- Free space path loss + atmospheric loss
- Rician fading with K-factor
- RIS array gain (antenna pattern + quantization loss)
- Beam steering angle loss
- Mutual coupling effects

### Auto-Discovery System

**Algorithms**: `algorithms/registry.py` scans at import time, finds all `PathfindingAlgorithm` subclasses, registers by `name` attribute

**Examples**: `examples/run_all.py` uses module introspection to find all `example_*.py` files with `run()` function

## Important Implementation Details

### Adding a New Pathfinding Algorithm

Create `algorithms/my_algorithm.py`:
```python
from .base import PathfindingAlgorithm

class MyAlgorithm(PathfindingAlgorithm):
    name = "my_algo"
    description = "My description"

    @staticmethod
    def find_path(graph, source, target, node_positions):
        # Your implementation
        return {'path': [...], 'totalLoss': float, 'totalLength': float}
```

Automatically available: `controller.find_all_paths(..., algorithm='my_algo')`

### Adding Physics Models

Add to `core/physics.py:Physics` class and use in `compute_snr_dB()`. All path loss calculations flow through this single function.

### Environment Integration

`core/environment.py` provides:
- `add_wall(start, end, attenuation_dB)` - Add obstacles
- `check_line_of_sight(pos1, pos2)` - LOS validation
- `get_blocked_paths(pos1, pos2)` - Blockage detection

Graph construction in `RISController.find_all_paths()` filters edges based on LOS.

### Configuration

YAML support in `config/config.py`. Key sections:
- `controller.algorithm` - Pathfinding algorithm selection
- `controller.strategy` - Selection strategy (max-snr, min-hops, min-loss)
- `environment` - Frequency, power, noise figure
- `ris` - RIS parameters (N elements, phase bits, max angle)

## REST API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/nodes` | GET | List all nodes |
| `/api/add` | POST | Add node (AP/RIS/UE) |
| `/api/find_paths` | GET | Find paths: `?ap=ap1&ue=ue1&algorithm=dijkstra` |
| `/api/update_position` | POST | Move node to new position |
| `/api/walls/add` | POST | Add wall obstacle |
| `/api/walls/clear` | POST | Clear all walls |
| `/api/config` | GET/POST | Get/update configuration |
| `/api/connect` | GET | Legacy single-hop (AP→RIS→UE) |
| `/api/sweep` | GET | Legacy beam sweep |

## Testing Strategy

Tests should cover:
1. **Unit Tests** (individual modules): physics calculations, node creation, algorithm correctness
2. **Integration Tests**: full pathfinding with different algorithms, SNR calculations with walls
3. **Regression Tests**: ensure algorithm performance stays consistent

Key test areas:
- `core/physics.py`: Math correctness (path loss, fading, SNR)
- `algorithms/`: Correctness and optimality of each algorithm
- `controller/`: Path sorting, strategy selection
- `environment.py`: LOS checking with walls

## Performance Characteristics

| Component | Complexity | Notes |
|-----------|-----------|-------|
| Dijkstra | O(E log V) | Optimal, V=nodes, E=edges |
| A* | O(E log V) | With good heuristic |
| Greedy | O(V) | Fast but suboptimal |
| Exhaustive | O(V!) | Small networks only |
| Beam Sweep | O(N) | N=codebook size |
| LOS Check | O(W) | W=number of walls |

For networks with >5 RIS nodes, use Dijkstra or A*. Greedy for quick approximations.

## Extending the Codebase

### To Add a New Node Type

1. Create class in `core/nodes.py` (inherit from `Node`)
2. Add factory method to `core/network.py` (e.g., `add_relay()`)
3. Update physics as needed in `compute_snr_dB()`

### To Add a New Beam Sweeping Algorithm

Add to `algorithms/beamforming.py:BeamformingEngine` as static method, similar to `greedy_beam_sweep()`

### To Add a New Example

Create `examples/example_X_description.py` with:
```python
def run():
    """Description"""
    # Your test code
    pass

if __name__ == '__main__':
    run()
```

Auto-discovered by `examples/run_all.py`

## Running the Application

```bash
python main.py --web    # Start web interface on http://127.0.0.1:5000
```

## Web Interface Features

- **Visualization**: Drag-drop nodes, draw walls, see paths
- **Real-time Metrics**: SNR, power, hops, path type
- **Algorithm Selection**: Choose pathfinding algorithm
- **Path Comparison**: View multiple paths from different algorithms

## Known Limitations

1. **2D Only**: Z-coordinate exists but visualization is 2D
2. **Static Network**: No mobile nodes (yet)
3. **No Interference**: Multi-user interference not modeled
4. **Exhaustive Algorithm**: O(V!) complexity - only for small networks

## Future Extensions (from ARCHITECTURE.md)

Planned (v2.1):
- 3D visualization
- Real-time collaboration
- Machine learning integration
- Comprehensive test suite

Possible (v2.2+):
- Distributed simulation
- GPU acceleration
- Hardware-in-the-loop
