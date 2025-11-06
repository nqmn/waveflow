# RISNet CLI - Quick Reference

## Start Interactive CLI

```bash
python3 examples/example_interactive_cli.py
```

## Node Creation (Auto-Named - Easiest!)

| Command | Auto Names | Example |
|---------|-----------|---------|
| `add ap <x> <y> [z]` | AP1, AP2, AP3... | `add ap 0 0` |
| `add ris <x> <y> [z] [N] [bits]` | R1, R2, R3... | `add ris 5 0` |
| `add ue <x> <y> [z]` | UE1, UE2, UE3... | `add ue 10 3` |

## Node Creation (Custom Names)

| Command | Description | Example |
|---------|-------------|---------|
| `add ap <name> <x> <y> [z]` | Custom AP name | `add ap myap 0 0` |
| `add ris <name> <x> <y> [z] [N] [bits]` | Custom RIS name | `add ris myris 5 0 0 16 2` |
| `add ue <name> <x> <y> [z]` | Custom UE name | `add ue myue 10 3` |

## Node Access (By Name)

| Command | Description | Example |
|---------|-------------|---------|
| `<node> info` | Show node details | `AP1 info` |
| `<node> ping <target>` | Test connectivity | `AP1 ping UE1` |
| `<node> iperf <target>` | Test throughput | `AP1 iperf UE1` |
| `<node> findpaths <target> [algo]` | Find all paths | `AP1 findpaths UE1 dijkstra` |
| `<ap> connect <ris> <ue>` | RIS-assisted connection | `AP1 connect R1 UE1` |
| `<node> position <x> <y> [z]` | Update position | `AP1 position 2 1` |

## Network Management

| Command | Description |
|---------|-------------|
| `list` | List all nodes |
| `list ap` | List APs only |
| `list ris` | List RIS only |
| `list ue` | List UEs only |
| `start` | Start network |
| `stop` | Stop network |
| `clear` | Remove all nodes |
| `help` | Show help |

## Path Finding Algorithms

| Algorithm | Speed | Optimality | Notes |
|-----------|-------|-----------|-------|
| `dijkstra` | Medium | Optimal | Default, best choice |
| `astar` | Fast | Optimal | Heuristic-based |
| `greedy` | Very Fast | Suboptimal | Nearest neighbor |
| `exhaustive` | Slow | All paths | Comprehensive |

## Example: Quick Network

```
# Create a simple 3-node network with auto-names
risnet> add ap 0 0          # AP1
risnet> add ris 5 0         # R1
risnet> add ue 10 3         # UE1

# Test connectivity
risnet> list
risnet> AP1 info
risnet> AP1 ping UE1
risnet> AP1 iperf UE1

# Find best path
risnet> AP1 findpaths UE1

# Setup RIS-assisted connection
risnet> AP1 connect R1 UE1

# Clean up
risnet> clear
```

## Example: Multi-Hop Network

```
# Create a chain of nodes
risnet> add ap 0 0          # AP1
risnet> add ris 4 0         # R1
risnet> add ris 8 0         # R2
risnet> add ue 12 0         # UE1

# Analyze paths
risnet> AP1 findpaths UE1   # Shows direct + relay paths
risnet> AP1 iperf UE1       # Compare throughput
```

## Output Legend

| Symbol | Meaning |
|--------|---------|
| ✓ | Success |
| ✗ | Failed |
| 📌 | Node information |
| 🔌 | Ping/connectivity |
| 📊 | Performance (iPerf) |
| 🗺️  | Paths |
| 🔗 | Connection |
| 📍 | Access Points |
| 📡 | RIS surfaces |
| 📱 | User Equipment |

## Tips

1. **Auto-naming is easiest**: Just use `add ap 0 0` instead of `add ap ap1 0 0`
2. **Node names are case-sensitive**: `AP1` and `ap1` are different
3. **Just type node name for info**: `AP1` shows node details (same as `AP1 info`)
4. **Default RIS parameters**: N=16, bits=2 (can override with `add ris 5 0 0 32 3`)
5. **Combine commands**: Add nodes, then immediately ping them

## Common Tasks

### Test if nodes can reach each other
```
AP1 ping UE1
```

### Find best path between two nodes
```
AP1 findpaths UE1 dijkstra
```

### Compare different routing algorithms
```
AP1 findpaths UE1 dijkstra
AP1 findpaths UE1 astar
AP1 findpaths UE1 greedy
```

### Setup RIS-assisted connection
```
AP1 connect R1 UE1
```

### Estimate network capacity
```
AP1 iperf UE1
```

### Move a node
```
AP1 position 2 1 0.5
```

### Add multiple nodes quickly
```
add ap 0 0
add ap 3 0
add ap 6 0
add ris 1.5 0
add ris 4.5 0
add ue 9 3
```

## Getting More Help

- Type `help` in CLI for full command documentation
- Check `GETTING_STARTED_CLI.md` for detailed guide
- See `risnet_cli.py` for implementation details

## Exit

```
risnet> exit
```

or

```
risnet> quit
```
