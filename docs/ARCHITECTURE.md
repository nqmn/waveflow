# RISNet v2.0 - Architecture Overview

## Design Principles

1. **Modularity**: Each module has a single, well-defined responsibility
2. **Stackability**: Modules can be composed and extended
3. **Testability**: Clean interfaces enable easy unit testing
4. **Extensibility**: New algorithms and models can be added easily

## Module Hierarchy

```
┌─────────────────────────────────────────┐
│         main-web-v2.py                  │
│      (Flask App + Frontend)             │
└──────────────┬──────────────────────────┘
               │
               ├──────────────┬──────────────────┬────────────────┐
               │              │                  │                │
               ▼              ▼                  ▼                ▼
         ┌─────────┐    ┌──────────┐      ┌──────────┐    ┌─────────┐
         │  core/  │    │algorithms│      │controller│    │ config/ │
         └────┬────┘    └────┬─────┘      └────┬─────┘    └─────────┘
              │              │                  │
              │              │                  │
    ┌─────────┼──────────────┼──────────────────┤
    │         │              │                  │
    ▼         ▼              ▼                  ▼
physics.py  nodes.py   pathfinding.py   ris_controller.py
network.py             beamforming.py
environment.py
```

## Module Responsibilities

### `core/` - Core Simulation Components

#### `physics.py`
**Purpose**: Centralized physics calculations

**Key Functions**:
- `path_loss_dB()` - Free space path loss
- `atmospheric_loss_dB()` - Atmospheric absorption
- `rician_fading()` - Channel fading model
- `quantization_loss_dB()` - Phase quantization effects
- `array_gain_dBi()` - RIS array gain
- `compute_snr_dB()` - SNR calculation

**Why separate**: Physics models are reused across all algorithms and components

#### `nodes.py`
**Purpose**: Node class hierarchy

**Classes**:
- `Node` - Base class
- `AccessPoint` - Transmitter with power control
- `RIS` - Reconfigurable surface with phase control
- `UE` - User equipment receiver

**Why separate**: Clean OOP design, easy to add new node types

#### `network.py`
**Purpose**: Network state management

**Responsibilities**:
- Node lifecycle (add, remove, update)
- Legacy compatibility (connect, sweep)
- Environment integration
- Controller interface

**Why separate**: Single source of truth for network state

#### `environment.py`
**Purpose**: Obstacle and propagation environment

**Classes**:
- `Wall` - Obstacle representation
- `Environment` - Environment manager

**Key Functions**:
- `check_line_of_sight()` - LOS validation
- `get_blocked_paths()` - Blockage detection

**Why separate**: Environment can be swapped/extended independently

### `algorithms/` - Optimization Algorithms

#### `pathfinding.py`
**Purpose**: Multi-hop routing algorithms

**Algorithms**:
1. `dijkstra()` - Optimal shortest path (O(E log V))
2. `astar()` - Heuristic-guided search (O(E log V))
3. `greedy()` - Fast local optimization (O(V))
4. `exhaustive()` - Brute force all paths (O(V!))

**Design Pattern**: Strategy pattern - algorithms are interchangeable

**Why separate**:
- Each algorithm is self-contained
- Easy to add new algorithms
- Can be tested independently
- Users can choose based on requirements

#### `beamforming.py`
**Purpose**: Beam steering optimization

**Algorithms**:
- `greedy_beam_sweep()` - Adaptive beam search
- `cfar_detection()` - Peak validation
- `simple_beam_sweep()` - Legacy uniform sweep

**Design Pattern**: Template method - common structure, variable details

**Why separate**:
- Beamforming is orthogonal to pathfinding
- Can be used independently
- Different optimization criteria

### `controller/` - Network Orchestration

#### `ris_controller.py`
**Purpose**: High-level network intelligence

**Responsibilities**:
- Multi-path discovery
- Path selection strategies
- Performance monitoring
- Graph construction

**Design Pattern**: Facade - simplifies complex subsystem interactions

**Why separate**:
- Centralized decision-making
- Decouples algorithms from network
- Enables network-wide optimization
- Maintains statistics

### `config/` - Configuration Management

#### `config.py`
**Purpose**: Application configuration

**Features**:
- YAML support
- Dot-notation access
- Default values
- Validation (future)

**Why separate**:
- Configuration is cross-cutting
- Enables different deployment configs
- Future: remote configuration

## Data Flow

### Pathfinding Flow

```
User Request
    │
    ▼
API Endpoint (/api/find_paths)
    │
    ▼
RISController.find_all_paths()
    │
    ├─► Build graph from network
    │   └─► Environment.check_line_of_sight()
    │
    ├─► Select algorithm
    │   └─► PathfindingEngine.dijkstra/astar/greedy/exhaustive()
    │
    ├─► Calculate SNR for each path
    │   └─► Physics.compute_snr_dB()
    │
    └─► Return sorted paths
```

### Beam Sweeping Flow

```
User Request
    │
    ▼
API Endpoint (/api/sweep)
    │
    ▼
Network.sweep()
    │
    ▼
BeamformingEngine.greedy_beam_sweep()
    │
    ├─► Generate codebook
    │
    ├─► Adaptive search
    │   └─► compute_snr_fn() for each angle
    │       └─► Physics calculations
    │
    ├─► Binary refinement
    │
    └─► CFAR validation
        └─► BeamformingEngine.cfar_detection()
```

## Extension Points

### Adding a New Algorithm

1. Add to `algorithms/pathfinding.py`:
```python
@staticmethod
def my_algorithm(graph, source, target, positions):
    # Implementation
    return {'path': [...], 'totalLoss': ..., 'totalLength': ...}
```

2. Register in `PathfindingEngine.get_algorithm()`:
```python
algorithms = {
    ...
    'my_algo': PathfindingEngine.my_algorithm
}
```

3. Use it:
```python
paths = controller.find_all_paths('ap1', 'ue1', algorithm='my_algo')
```

### Adding a New Node Type

1. Create class in `core/nodes.py`:
```python
class Relay(Node):
    def __init__(self, name, x, y, z=0.0, gain_dB=10):
        super().__init__(name, x, y, z)
        self.gain_dB = gain_dB
```

2. Add to network in `core/network.py`:
```python
def add_relay(self, name, x, y, z=0.0, gain_dB=10):
    self.nodes[name] = Relay(name, x, y, z, gain_dB)
```

3. Update physics calculations as needed

### Adding a New Physics Model

1. Add to `core/physics.py`:
```python
@staticmethod
def my_loss_model(distance, freq, ...):
    # Implementation
    return loss_dB
```

2. Use in SNR calculation:
```python
my_loss = Physics.my_loss_model(...)
snr = Physics.compute_snr_dB(..., custom_loss=my_loss)
```

## Design Patterns Used

1. **Strategy Pattern** (Algorithms)
   - Interchangeable pathfinding algorithms
   - Runtime algorithm selection

2. **Facade Pattern** (Controller)
   - Simplified interface to complex subsystems
   - Hides graph construction, SNR calculation

3. **Template Method** (Beamforming)
   - Common beam sweep structure
   - Variable search strategies

4. **Factory Pattern** (Nodes)
   - `add_ap()`, `add_ris()`, `add_ue()`
   - Centralized node creation

5. **Singleton** (Global state)
   - `_net`, `_controller`, `_config`
   - Single source of truth

## Testing Strategy

### Unit Tests (Planned)

```
tests/
├── test_physics.py         # Physics calculations
├── test_nodes.py           # Node classes
├── test_pathfinding.py     # Algorithms
├── test_beamforming.py     # Beam sweeping
├── test_controller.py      # Controller logic
└── test_environment.py     # Wall/LOS checking
```

### Integration Tests

- Full path finding with multiple algorithms
- End-to-end SNR calculation
- Environment with walls

### Performance Tests

- Algorithm complexity verification
- Large network scalability
- Memory usage profiling

## Comparison with HTML Version

| Aspect | HTML (Monolithic) | Python v2.0 (Modular) |
|--------|-------------------|----------------------|
| **Files** | 1 (57k lines) | 15+ modules |
| **Testing** | Difficult | Easy (pytest) |
| **Extension** | Modify giant file | Add new module |
| **Debugging** | Hard to isolate | Module-level |
| **Reuse** | Copy-paste | Import module |
| **Documentation** | Inline comments | Module docstrings |
| **Version Control** | Merge conflicts | Clean diffs |

## Performance Characteristics

| Component | Complexity | Notes |
|-----------|------------|-------|
| Dijkstra | O(E log V) | V=nodes, E=edges |
| A* | O(E log V) | With good heuristic |
| Greedy | O(V) | Fast but suboptimal |
| Exhaustive | O(V!) | Small networks only |
| Beam Sweep | O(N) | N=codebook size |
| LOS Check | O(W) | W=number of walls |

## Future Enhancements

### Planned (v2.1)
- [ ] 3D visualization
- [ ] Real-time collaboration
- [ ] Machine learning integration
- [ ] Comprehensive test suite

### Possible (v2.2+)
- [ ] Distributed simulation
- [ ] GPU acceleration
- [ ] Hardware-in-the-loop
- [ ] Automated experiment management

## Summary

**Key Achievement**: Transformed monolithic HTML/JS simulator into modular, testable, extensible Python architecture while maintaining all features and adding new capabilities.

**Main Benefits**:
1. **Maintainability**: Clear module boundaries
2. **Extensibility**: Easy to add algorithms/models
3. **Testability**: Each module can be tested independently
4. **Reusability**: Modules can be imported elsewhere
5. **Scalability**: Backend can handle large simulations

**Trade-offs**:
- More files to navigate (but better organized)
- Requires Python environment (but enables ML/optimization libraries)
- Slightly more boilerplate (but much more maintainable)
