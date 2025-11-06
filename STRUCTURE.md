# RISnet v2.0 - Project Structure

## 🎯 New Modular Organization

All algorithms and examples are now **auto-discovered** - just drop in a new file and it's automatically available!

## 📁 Directory Structure

```
risimulator/
├── core/                    # Core simulation components
│   ├── __init__.py
│   ├── physics.py           # Physics models (path loss, fading, etc.)
│   ├── nodes.py             # Node classes (AP, RIS, UE)
│   ├── network.py           # Network manager
│   └── environment.py       # Walls, obstacles, LOS checking
│
├── algorithms/              # ⭐ Auto-discovered algorithms
│   ├── __init__.py
│   ├── base.py              # Base class for all algorithms
│   ├── registry.py          # Auto-discovery engine
│   ├── dijkstra.py          # ✓ Dijkstra algorithm
│   ├── astar.py             # ✓ A* algorithm
│   ├── greedy.py            # ✓ Greedy algorithm
│   ├── exhaustive.py        # ✓ Exhaustive search
│   ├── beamforming.py       # Beam sweeping algorithms
│   └── [your_algo.py]       # 👈 Drop new algorithms here!
│
├── examples/                # ⭐ Auto-discovered examples
│   ├── __init__.py
│   ├── example_1_simple.py             # ✓ Simple network
│   ├── example_2_topology.py           # ✓ Predefined topology
│   ├── example_3_custom_topology.py    # ✓ Custom topology
│   ├── example_4_obstacles.py          # ✓ With obstacles
│   ├── example_5_context_manager.py    # ✓ Context manager
│   ├── example_6_batch_testing.py      # ✓ Batch testing
│   ├── run_all.py           # 👈 Run all examples
│   └── [your_example.py]    # 👈 Drop new examples here!
│
├── controller/              # Network orchestration
│   ├── __init__.py
│   └── ris_controller.py    # Auto-loads algorithms
│
├── config/                  # Configuration management
│   ├── __init__.py
│   └── config.py            # YAML config support
│
├── risnet.py                # Mininet-style API
├── main-web-v2.py           # Flask web application
├── example_usage.py         # Legacy examples
├── test_auto_discovery.py   # Test auto-discovery
└── requirements.txt         # Dependencies
```

## ⭐ Auto-Discovery Features

### 1. **Algorithm Auto-Discovery**

Just create a new file in `algorithms/`:

```python
# algorithms/my_algorithm.py

from .base import PathfindingAlgorithm

class MyAlgorithm(PathfindingAlgorithm):
    name = "my_algo"
    description = "My custom algorithm"

    @staticmethod
    def find_path(graph, source, target, node_positions):
        # Your implementation
        return {'path': [...], 'totalLoss': ..., 'totalLength': ...}
```

**That's it!** No need to register anywhere. Use immediately:

```python
net.findPaths(ap, ue, algorithm='my_algo')
```

### 2. **Example Auto-Discovery**

Create a new file in `examples/`:

```python
# examples/example_7_my_test.py

def run():
    """My custom example"""
    from risnet import RISnet

    net = RISnet()
    # Your test code
```

**Automatically included** when you run:

```bash
python examples/run_all.py
```

## 🚀 Usage

### Run Specific Example

```bash
# Run any example directly
python examples/example_1_simple.py
python examples/example_4_obstacles.py
```

### Run All Examples

```bash
# Auto-discovers and runs all examples
python examples/run_all.py
```

### Test Auto-Discovery

```bash
# Test that everything is discovered correctly
python test_auto_discovery.py
```

### Use in Your Code

```python
from risnet import RISnet
from algorithms import list_algorithms

# See all available algorithms
print("Available algorithms:", list_algorithms())
# Output: ['astar', 'dijkstra', 'exhaustive', 'greedy']

# Use any algorithm
net = RISnet()
ap = net.addAP('ap1', position=(0, 0))
ue = net.addUE('ue1', position=(10, 3))
net.start()

# Try each algorithm
for algo in list_algorithms():
    paths = net.findPaths(ap, ue, algorithm=algo)
    print(f"{algo}: {paths[0]['snr_dB']:.1f} dB")
```

## 📊 File Counts

| Category | Count | Auto-Discovered? |
|----------|-------|------------------|
| **Core modules** | 5 | No (base system) |
| **Algorithms** | 4 | ✅ Yes |
| **Examples** | 6 | ✅ Yes |
| **Controllers** | 1 | No (uses algorithms) |
| **Config** | 1 | No (base system) |

## 🎓 Adding New Components

### Add a New Algorithm

1. Create `algorithms/my_algo.py`
2. Inherit from `PathfindingAlgorithm`
3. Set `name` and `description`
4. Implement `find_path()` method
5. ✅ Done! Automatically available

### Add a New Example

1. Create `examples/example_X_name.py`
2. Add a `run()` function
3. ✅ Done! Included in `run_all.py`

### Add a New Topology

```python
# In your code or in risnet.py
from risnet import Topology

class MyTopology(Topology):
    def build(self):
        self.addAP('ap1', position=(0, 0))
        self.addRIS('ris1', position=(5, 0))
        self.addUE('ue1', position=(10, 3))
```

## 🔍 How Auto-Discovery Works

### Algorithm Discovery

1. **Registry pattern** (`algorithms/registry.py`)
2. Scans `algorithms/` package at import time
3. Finds all subclasses of `PathfindingAlgorithm`
4. Registers by `name` attribute
5. Available via `get_algorithm(name)`

### Example Discovery

1. **Module introspection** (`examples/run_all.py`)
2. Scans `examples/` package
3. Finds all `example_*.py` files
4. Imports and runs `run()` function

## 📈 Benefits

| Before | After |
|--------|-------|
| Edit pathfinding.py (300 lines) | Create new file (50 lines) |
| Manually register in dict | Automatic registration |
| Hardcoded algorithm names | Dynamic discovery |
| One big examples file | One file per example |
| Manual example execution | `run_all.py` |

## 🎯 Quick Start Examples

### 1. Simple Network
```bash
python examples/example_1_simple.py
```

### 2. With Obstacles
```bash
python examples/example_4_obstacles.py
```

### 3. All Algorithms
```python
from algorithms import list_algorithms, get_algorithm

for name in list_algorithms():
    algo = get_algorithm(name)
    print(f"{algo.name}: {algo.description}")
```

## 📝 Algorithm Template

Copy this template to create new algorithms:

```python
# algorithms/template.py

from .base import PathfindingAlgorithm
import numpy as np
from typing import Dict

class TemplateAlgorithm(PathfindingAlgorithm):
    """Template for new algorithms"""

    name = "template"  # Used in net.findPaths(algorithm='template')
    description = "Template algorithm description"

    @staticmethod
    def find_path(graph: Dict[str, Dict[str, float]],
                  source: str,
                  target: str,
                  node_positions: Dict[str, np.ndarray]) -> Dict:
        """Find path from source to target

        Args:
            graph: {node: {neighbor: weight}}
            source: Source node name
            target: Target node name
            node_positions: {node: np.array([x, y, z])}

        Returns:
            {
                'path': [source, ..., target],
                'totalLoss': float,
                'totalLength': float
            }
        """
        # Your algorithm here
        path = [source, target]

        return {
            'path': path,
            'totalLoss': 0.0,
            'totalLength': 0.0
        }
```

## 📝 Example Template

Copy this template to create new examples:

```python
# examples/example_X_description.py

"""
Example X: Description

Brief explanation of what this example demonstrates.
"""

from risnet import RISnet

def run():
    """Run Example X"""
    print("\n" + "="*60)
    print("Example X: Description")
    print("="*60)

    # Create network
    net = RISnet()

    # Your test code here
    ap = net.addAP('ap1', position=(0, 0))
    ue = net.addUE('ue1', position=(10, 3))

    net.start()

    # Run tests
    result = net.ping(ap, ue)
    print(f"Result: {result}")

    net.stop()

if __name__ == '__main__':
    run()
```

## 🔧 Troubleshooting

### Algorithm Not Discovered

1. Check file is in `algorithms/` folder
2. Check class inherits from `PathfindingAlgorithm`
3. Check `name` attribute is set
4. Run `python test_auto_discovery.py`

### Example Not Running

1. Check file starts with `example_`
2. Check file has `run()` function
3. Check file is in `examples/` folder
4. Run `python examples/run_all.py`

## 📚 Learn More

- **README.md** - Complete documentation
- **QUICKSTART.md** - Get started in 30 seconds
- **ARCHITECTURE.md** - Technical deep-dive
- **test_auto_discovery.py** - See auto-discovery in action

---

**The beauty of auto-discovery**: Just drop in new files and they work! 🎉
