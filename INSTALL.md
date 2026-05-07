# Waveflow Installation Guide

## Requirements

- Python 3.7 or later
- pip
- Git (for source install)

## Option A — Install from PyPI

The fastest way to get started:

```bash
pip install waveflow-sim
```

Includes: physics models, beam sweeping, pathfinding, CLI, and Python API.  
Excludes: terminal UI, web interface, ML predictors, plots, computer vision.

## Option B — Install from Source (Recommended for Development)

```bash
git clone https://github.com/nqmn/waveflow
cd waveflow
pip install -e .
```

Editable mode (`-e`) means changes to source files take effect immediately without reinstalling.

## Virtual Environment (Recommended)

Isolates Waveflow from your system Python:

```bash
python3 -m venv .venv
source .venv/bin/activate      # Linux / macOS
.venv\Scripts\activate         # Windows

pip install -e .
```

## Optional Extras

Install additional capabilities as needed:

| Extra | Command | Adds |
|---|---|---|
| Terminal UI | `pip install -e ".[terminal]"` | `waveflow ui` commands (Typer + Rich) |
| Plots | `pip install -e ".[plot]"` | `plot` command, charts (Matplotlib) |
| ML predictors | `pip install -e ".[ml]"` | ML beam angle predictors (scikit-learn + PyTorch) |
| Vision | `pip install -e ".[vision]"` | ArUco / HOG sweep modes (OpenCV) |
| Web interface | `pip install -e ".[web]"` | `waveflow --web` (Flask + Waitress) |
| Optimization | `pip install -e ".[optimization]"` | Phase optimization (CVXPY + SCS) |
| Development | `pip install -e ".[dev]"` | pytest, black, flake8, mypy, matplotlib |
| Everything | `pip install -e ".[all]"` | All of the above |

Most users only need core + terminal:

```bash
pip install -e ".[terminal]"
```

## Verify the Installation

Run this after installing to confirm everything works:

```bash
# 1. Check the CLI entry point
waveflow --help
```

```
usage: waveflow [-h] [--web] [--cli] [--terminal] ...
Waveflow v2.0 Advanced Wireless and RIS Simulator
```

```bash
# 2. Quick simulation check
python3 - <<'PY'
from core import RISNetwork
net = RISNetwork(enable_messaging=False)
net.add_ap('ap1', 0, 2)
net.add_ris('ris1', 5, 2, max_angle_deg=90)
net.add_ue('ue1', 10, 5)
result = net.connect('ap1', 'ris1', 'ue1', use_get_snr=False)
print('OK — snr_dB:', round(result['snr_dB'], 2))
PY
```

```
OK — snr_dB: 29.9
```

```bash
# 3. Run the physics validation suite
waveflow ui testphysics

# 4. Run the compile check
python3 -m compileall core controller cli risnet waveflow config utils
```

## Running Tests

```bash
# After pip install -e ".[dev]"
pytest tests/ -v

# Without pytest (fallback)
PYTHONPATH=. python3 tests/test_physics_fixes.py
PYTHONPATH=. python3 tests/test_smoke.py
```

Known: `tests/test_fixes.py` TEST 3 (RMS Phase Error with Angle Wrapping) has
a stale expected value and will report one failure. All other tests pass.

## Troubleshooting

**`ModuleNotFoundError: No module named 'core'`**

Run scripts from the repository root, or set `PYTHONPATH`:

```bash
cd /path/to/waveflow
PYTHONPATH=. python3 your_script.py
```

Or install in editable mode: `pip install -e .`

**`externally-managed-environment` error from pip**

Your system Python is protected. Use a virtual environment:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

**`waveflow` command not found after install**

```bash
pip install -e .
which waveflow    # Linux/macOS
where waveflow    # Windows
```

The legacy `risnet` command is also installed for backward compatibility.

**`ValueError: AP outside RIS FOV`**

The RIS has a default ±60° field of view. Place the AP and UE within the RIS
boresight range, or widen the FOV:

```python
net.add_ris('ris1', 5, 0, max_angle_deg=90)  # ±90° FOV
```

**ML predictor not found**

ML predictors require pre-trained model files in
`controller/beamsweeping/ml/models/`. Generate a dataset and train models first:

```bash
PYTHONPATH=. python3 controller/beamsweeping/ml/tools/dataset_builder.py
PYTHONPATH=. python3 controller/beamsweeping/ml/tools/train_rf.py
```

**MATLAB integration errors**

MATLAB integration is optional and lazy-loaded. If MATLAB is not installed,
`MatlabBridge` will fail gracefully and all non-MATLAB functionality remains
available.
