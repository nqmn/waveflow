# Waveflow v2.0

[![PyPI version](https://img.shields.io/pypi/v/waveflow-sim)](https://pypi.org/project/waveflow-sim)
[![Python](https://img.shields.io/pypi/pyversions/waveflow-sim)](https://pypi.org/project/waveflow-sim)
[![License](https://img.shields.io/badge/License-Apache_2.0-green.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-nqmn%2Fwaveflow-lightgrey?logo=github)](https://github.com/nqmn/waveflow)

Waveflow is a Python simulator for wireless networks assisted by Reconfigurable Intelligent Surfaces (RIS). It lets researchers and engineers model how passive reflective panels can improve signal coverage, optimize beam angles, and evaluate link quality — without physical hardware.

Use it to prototype RIS-assisted network topologies, benchmark beam sweeping algorithms, and study propagation physics through a scriptable Python API or interactive CLI.

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
| Physics | FSPL, atmospheric loss, Rician fading, RIS array gain, phase quantization |
| Beam sweeping | Linear, coarse-fine, DE, ML-guided, hierarchical, PRIME |
| Pathfinding | Dijkstra, A\*, Greedy, Exhaustive |
| Channel | OFDM waveform, multipath, per-subcarrier SNR |
| ML | Random Forest, XGBoost, SVR, KNN, LGBM beam predictors |
| Interface | Interactive CLI, Python API |
| Feedback | UE→AP SNR feedback loop with adaptive beam tracking |

## Usage

### Interactive CLI

```bash
waveflow
waveflow> add ap ap1 0 0
waveflow> add ris ris1 5 0 0 16 2
waveflow> add ue ue1 10 3
waveflow> connect ap1 ris1 ue1
SNR: 29.9 dB
waveflow> sweep ap1 ris1 ue1 60 10 --algo de
waveflow> help
```

### Python API

```python
from waveflow import RISnet

net = RISnet()
ap  = net.addAP('ap1',  position=(0, 0))
ris = net.addRIS('ris1', position=(5, 0), N=16, bits=2)
ue  = net.addUE('ue1',  position=(10, 3))
net.start()

result = net.ping(ap, ue)
print(f"SNR: {result['snr_dB']:.1f} dB, hops: {result['hops']}")
```

```python
# Low-level API
from core import RISNetwork

net = RISNetwork()
net.add_ap('ap1', 0, 0)
net.add_ris('ris1', 5, 0, N=16, bits=2, max_angle_deg=90)
net.add_ue('ue1', 10, 3)

result = net.connect('ap1', 'ris1', 'ue1', use_get_snr=False)
print(f"SNR: {result['snr_dB']:.1f} dB")
```

## Beam Sweep Algorithms

```bash
waveflow> sweep ap1 ris1 ue1 60 10 --algo linear
waveflow> sweep ap1 ris1 ue1 60 10 --algo coarse-fine
waveflow> sweep ap1 ris1 ue1 60 10 --algo de
waveflow> sweep ap1 ris1 ue1 60 10 --algo ml-guided --ml-predictor rf
```

| Algorithm | Key | Notes |
|---|---|---|
| Linear brute-force | `linear` | Uniform steps, coarse→fine |
| Coarse-fine | `coarse-fine` | Two-phase, ~30% faster than linear |
| Differential Evolution | `de` | Population-based global search |
| ML-guided | `ml-guided` | RF/XGBoost/SVR/KNN/LGBM predictor + refinement |
| Hierarchical | `hierarchical` | Multi-resolution sweep |
| PRIME localization | `prime` | Localization-assisted |

## Project Structure

```
waveflow/
├── core/               # Physics, nodes, network, waveform
├── controller/         # Beam sweeping, pathfinding, ML, phase control
├── cli/                # Interactive shell
├── config/             # Configuration management
├── utils/              # Link budget, SNR, RSSI helpers
├── waveflow/           # Public package (forward-looking name)
├── risnet/             # Backward-compatible package and high-level API
├── matlab_integration/ # Optional MATLAB bridge
├── examples/
│   ├── script/         # Runnable Python examples
│   └── json/           # Topology fixture files
├── tests/              # Test suite
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

# Full suite
pip install -e ".[dev]"
pytest tests/ -v
```

## Roadmap

See [FUTURE.md](FUTURE.md) for the full v3 architecture migration plan — phased arrays, spatial channels, runtime kernel, AI-native interfaces, and web interface.

## Contributing

Contributions are welcome. Please open an issue to discuss significant changes before submitting a pull request.

## Citation

If you use Waveflow in your research, please cite:

```bibtex
@software{waveflow2024,
  title  = {Waveflow: Wireless Propagation, Waveform, and RIS-Assisted Network Simulator},
  author = {Waveflow Contributors},
  year   = {2024},
  url    = {https://github.com/nqmn/waveflow}
}
```

## License

Apache 2.0 — see [LICENSE](LICENSE)
