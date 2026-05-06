# Installation Guide

## Requirements

- Python 3.7 or later
- pip

## 1. Clone the Repository

```bash
git clone https://github.com/nqmn/risnet
cd risnet
```

## 2. Choose an Install Profile

### Minimal — core simulation only (NumPy, SciPy, PyYAML)

```bash
pip install -e .
```

Includes: physics models, beam sweeping, pathfinding, CLI, Python API.  
Excludes: web interface, ML predictors, computer vision, visualization.

### With web interface

```bash
pip install -e ".[web]"
```

Adds Flask and Waitress. Enables `risnet --web`.

### With ML beam predictors

```bash
pip install -e ".[ml]"
```

Adds PyTorch and scikit-learn. Enables `--algo ml-guided --ml-predictor rf/xgb/svr/knn/lgbm`.

### With convex optimization

```bash
pip install -e ".[optimization]"
```

Adds CVXPY and SCS. Used by phase optimization routines.

### With computer vision (ArUco / HOG sweep modes)

```bash
pip install -e ".[vision]"
```

Adds OpenCV.

### With terminal UI extras

```bash
pip install -e ".[terminal]"
```

Adds Typer and Rich.

### Development (all tools + tests)

```bash
pip install -e ".[dev]"
```

Adds pytest, black, flake8, mypy, matplotlib.

### Everything

```bash
pip install -e ".[all]"
```

## 3. Verify Installation

```bash
# Check the CLI entry point
risnet --help

# Run a compile check
python3 -m compileall core controller cli risnet app config utils

# Run the physics regression test
PYTHONPATH=. python3 tests/test_physics_fixes.py

# Baseline simulation check
python3 - <<'PY'
from core import RISNetwork
from risnet import RISnet
net = RISNetwork(enable_messaging=False)
net.add_ap("ap1", 0, 2)
net.add_ris("ris1", 5, 2, max_angle_deg=90)
net.add_ue("ue1", 10, 5)
result = net.connect("ap1", "ris1", "ue1", use_get_snr=False)
assert "snr_dB" in result
print("OK — snr_dB:", round(result["snr_dB"], 2))
PY
```

## 4. Virtual Environment (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate      # Linux / macOS
.venv\Scripts\activate         # Windows

pip install -e ".[dev]"
risnet --help
```

## 5. Running Tests

```bash
# After pip install -e ".[dev]"
pytest tests/ -v

# Without pytest (fallback)
PYTHONPATH=. python3 tests/test_physics_fixes.py
PYTHONPATH=. python3 tests/test_smoke.py
```

Known: `tests/test_fixes.py` TEST 3 (RMS Phase Error with Angle Wrapping) has
a stale expected value and will report one failure. All other tests pass.

## 6. Running the Web Interface

```bash
pip install -e ".[web]"
risnet --web
# Open http://127.0.0.1:5000
```

## Troubleshooting

**`ModuleNotFoundError: No module named 'core'`**

Run from the repository root, or set `PYTHONPATH`:

```bash
cd /path/to/risnet
PYTHONPATH=. python3 your_script.py
```

Or install in editable mode: `pip install -e .`

**`externally-managed-environment` error from pip**

Use a virtual environment:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

**`ValueError: AP outside RIS FOV`**

The RIS has a default ±60° field of view. Place the AP and UE within the RIS
boresight range, or widen the FOV:

```python
net.add_ris('ris1', 5, 0, max_angle_deg=90)  # ±90° FOV
```

**`risnet` command not found after install**

Confirm editable install completed without errors:

```bash
pip install -e .
which risnet       # Linux/macOS
where risnet       # Windows
```

**MATLAB integration errors**

MATLAB integration is optional and lazy-loaded. If MATLAB is not installed,
`MatlabBridge` will fail gracefully and all non-MATLAB functionality remains
available.

**ML predictor not found**

ML predictors require pre-trained model files in
`controller/beamsweeping/ml/models/`. If the directory is empty, generate a
dataset and train models first (run from the repository root):

```bash
PYTHONPATH=. python3 controller/beamsweeping/ml/tools/dataset_builder.py
PYTHONPATH=. python3 controller/beamsweeping/ml/tools/train_rf.py
```

See `TUTORIAL.md` Part 8 for full training workflow details.
