# RISNet v2.0 - Quick Start Guide

## Installation (30 seconds)

```bash
cd /path/to/risimulator
pip install -r requirements.txt
```

## Run Web Interface (Recommended)

```bash
python main-web-v2.py --web
```

Then open browser to: **http://127.0.0.1:5000**

## Try the Examples

```bash
python example_usage.py
```

## Project Structure

```
risimulator/
├── core/               ← Physics, nodes, network, environment
├── algorithms/         ← Pathfinding & beamforming
├── controller/         ← RIS controller orchestration
├── config/             ← YAML configuration
├── main-web-v2.py      ← NEW! Main application
├── example_usage.py    ← Example code
└── README.md           ← Full documentation
```

## Key Features

### ✓ Completed & Working

1. **Multi-Algorithm Pathfinding**
   - Dijkstra (optimal)
   - A* (heuristic)
   - Greedy (fast)
   - Exhaustive (all paths)

2. **Advanced Beam Sweeping**
   - Greedy adaptive search
   - CFAR detection
   - Binary refinement

3. **Environment Modeling**
   - Walls/obstacles
   - Line-of-sight checking
   - Blockage detection

4. **Centralized Controller**
   - Intelligent path selection
   - Multi-strategy optimization
   - Performance tracking

5. **Modular Architecture**
   - Clean separation of concerns
   - Easy to extend
   - Testable components

## Web Interface Features

- **Interactive Visualization**: Drag & drop nodes
- **Real-time Metrics**: SNR, power, hops, path type
- **Path Visualization**: Direct, reflected, relay paths
- **Controller Panel**: Algorithm selection, statistics
- **Environment Tools**: Add walls, obstacles

## API Quick Reference

### Add Nodes
```bash
POST /api/add
{
  "type": "ap|ris|ue",
  "name": "node1",
  "x": 0,
  "y": 0,
  "N": 16,      # RIS only
  "bits": 2     # RIS only
}
```

### Find Paths
```bash
GET /api/find_paths?ap=ap1&ue=ue1&algorithm=dijkstra
```

### Connect (Legacy)
```bash
GET /api/connect?ap=ap1&ris=ris1&ue=ue1
```

## Python Quick Reference

### Basic Usage
```python
from core import RISNetwork
from controller import RISController

# Create network
net = RISNetwork()
net.add_ap('ap1', x=0, y=0)
net.add_ris('ris1', x=5, y=0, N=16, bits=2)
net.add_ue('ue1', x=10, y=3)

# Create controller
controller = RISController(net)
net.set_controller(controller)

# Find paths
paths = controller.find_all_paths('ap1', 'ue1', algorithm='dijkstra')
print(f"Best SNR: {paths[0]['snr_dB']:.1f} dB")
```

### With Walls
```python
# Add wall
net.add_wall(start=[2, -2], end=[2, 2], attenuation_dB=20)

# Find paths (will route around wall)
paths = controller.find_all_paths('ap1', 'ue1')
```

## Comparison: Old vs New

| Feature | main-web.py (Old) | main-web-v2.py (New) |
|---------|-------------------|---------------------|
| Architecture | Monolithic | ✓ Modular |
| Pathfinding | Basic sweep | ✓ Multi-algorithm |
| Walls/Obstacles | None | ✓ Full support |
| Beam Sweeping | Simple | ✓ Advanced CFAR |
| Extensibility | Hard | ✓ Easy |
| Testing | Hard | ✓ Easy |
| Code Size | 995 lines | 27k+ (well-organized) |

## Module Summary

### `core/physics.py`
All physics models in one place:
- Path loss, atmospheric loss
- Rician fading
- RIS array gain
- SNR calculation

### `algorithms/pathfinding.py`
All 4 algorithms:
- Dijkstra, A*, Greedy, Exhaustive
- Path validation

### `algorithms/beamforming.py`
Advanced beam control:
- Greedy beam sweep
- CFAR detection
- Codebook generation

### `controller/ris_controller.py`
Network orchestration:
- Multi-path finding
- Path selection strategies
- Performance stats

### `core/network.py`
Network management:
- Node management
- Legacy compatibility
- Environment integration

## Next Steps

1. **Explore the web interface**: `python main-web-v2.py --web`
2. **Run examples**: `python example_usage.py`
3. **Read full docs**: See `README.md`
4. **Extend**: Add your own algorithms to `algorithms/`

## Common Tasks

### Add a New Algorithm
```python
# algorithms/pathfinding.py
@staticmethod
def my_algorithm(graph, source, target, positions):
    # Your code
    return {'path': [...], 'totalLoss': ...}
```

### Add Custom Physics
```python
# core/physics.py
@staticmethod
def my_loss_model(distance, freq):
    # Your code
    return loss_dB
```

### Change Default Config
```python
# main-web-v2.py or use YAML
_config.set('controller.algorithm', 'astar')
_config.set('ris.default_N', 32)
```

## Performance Tips

1. **Dijkstra**: Best for optimal paths (recommended)
2. **A***: Faster than Dijkstra, still optimal
3. **Greedy**: Fast approximation
4. **Exhaustive**: Small networks only (<5 RIS)

## Troubleshooting

**Import Error?**
```bash
pip install -r requirements.txt
```

**Port in use?**
```bash
# Kill old process or change port in code
```

**Module not found?**
```bash
# Make sure you're in risimulator directory
cd /path/to/risimulator
```

## Support

- Examples: `example_usage.py`
- Full docs: `README.md`
- Issues: GitHub issues (if applicable)

---

**Ready to go!** Start with `python main-web-v2.py --web` 🚀
