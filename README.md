# RISNet v2.0

Advanced Reconfigurable Intelligent Surface (RIS) network simulator with modular architecture, beam sweeping algorithms, spatial channel modeling, and ML-guided optimization.

## What is RISNet?

RISNet simulates wireless networks where passive RIS panels reflect signals from an Access Point (AP) to User Equipment (UE). It models the full link budget: path loss, RIS array gain, phase quantization, fading, and FOV constraints.

## Quick Start

```bash
git clone https://github.com/nqmn/risnet
cd risnet
pip install -e .
risnet
```

Full installation options and troubleshooting: **[INSTALL.md](INSTALL.md)**

Step-by-step tutorials from basic to advanced: **[TUTORIAL.md](TUTORIAL.md)**

## Features

| Category | Capability |
|---|---|
| Physics | FSPL, atmospheric loss, Rician fading, RIS array gain, phase quantization |
| Beam sweeping | Linear, adaptive, DE, ML-guided, hierarchical, PRIME |
| Pathfinding | Dijkstra, A\*, Greedy, Exhaustive |
| Channel | OFDM waveform, multipath, per-subcarrier SNR |
| ML | Random Forest, XGBoost, SVR, MLP beam predictors |
| Interface | Interactive CLI, REST API (Flask), Python API |
| Feedback | UE→AP SNR feedback loop with adaptive beam tracking |

## Project Structure

```
risnet/
├── core/               # Physics, nodes, network, waveform
├── controller/         # Beam sweeping, pathfinding, ML, RL controller
├── app/                # Flask REST API and web UI
├── cli/                # Interactive shell
├── config/             # Configuration management
├── utils/              # Link budget, SNR, RSSI helpers
├── risnet/             # Package root and high-level RISnet API
├── matlab_integration/ # MATLAB bridge and .m scripts
├── examples/
│   ├── script/         # Runnable Python examples
│   └── json/           # Topology fixture files
├── tests/              # Test suite
├── docs/               # Architecture notes and assets
├── INSTALL.md          # Installation guide
├── TUTORIAL.md         # Tutorials: basic to advanced
└── FUTURE.md           # v3 architecture roadmap
```

## Interfaces

### Interactive CLI

```bash
risnet
risnet> add ap ap1 0 0
risnet> add ris ris1 5 0 0 16 2
risnet> add ue ue1 10 3
risnet> connect ap1 ris1 ue1
risnet> sweep ap1 ris1 ue1 60 10 --algo de
risnet> help
```

### Python API (low-level)

```python
from core import RISNetwork

net = RISNetwork()
net.add_ap('ap1', 0, 0)
net.add_ris('ris1', 5, 0, N=16, bits=2, max_angle_deg=90)
net.add_ue('ue1', 10, 3)

result = net.connect('ap1', 'ris1', 'ue1', use_get_snr=False)
print(f"SNR: {result['snr_dB']:.1f} dB")
```

### Python API (high-level)

```python
from risnet import RISnet

net = RISnet()
ap  = net.addAP('ap1',  position=(0, 0))
ris = net.addRIS('ris1', position=(5, 0), N=16, bits=2)
ue  = net.addUE('ue1',  position=(10, 3))
net.start()

result = net.ping(ap, ue)
print(f"SNR: {result['snr_dB']:.1f} dB, hops: {result['hops']}")
```

### Web interface

```bash
risnet --web
# Open http://127.0.0.1:5000
```

## Beam Sweep Algorithms

```bash
# From CLI
risnet> sweep ap1 ris1 ue1 60 10 --algo linear
risnet> sweep ap1 ris1 ue1 60 10 --algo adaptive
risnet> sweep ap1 ris1 ue1 60 10 --algo de
risnet> sweep ap1 ris1 ue1 60 10 --algo ml-guided --ml-predictor rf
```

| Algorithm | Key | Notes |
|---|---|---|
| Linear brute-force | `linear` | Uniform steps, coarse→fine |
| Adaptive center-out | `adaptive` | ~30% faster than linear |
| Differential Evolution | `de` | Population-based global search |
| ML-guided | `ml-guided` | RF/XGBoost/SVR/MLP predictor + refinement |
| Hierarchical | `hierarchical` | Multi-resolution |
| PRIME localization | `prime` | Localization-assisted |

## Testing

```bash
# Compile check
python3 -m compileall core controller cli risnet app config utils

# Physics regression
PYTHONPATH=. python3 tests/test_physics_fixes.py

# Full suite (requires dev install)
pip install -e ".[dev]"
pytest tests/ -v
```

## Roadmap

See [FUTURE.md](FUTURE.md) for the full v3 architecture migration plan (phased arrays, spatial channels, runtime kernel, AI-native interfaces).

## License

MIT — see [LICENSE](LICENSE)
