# Beam Sweep Algorithms

Standardized modular beam sweeping implementation for RISNet. Each algorithm follows a consistent interface and output format.

## Quick Links

- **Creating a New Algorithm?** → Read [QUICK_START.md](QUICK_START.md)
- **Full Development Guide** → Read [ALGORITHM_TEMPLATE.md](ALGORITHM_TEMPLATE.md)
- **Template File** → Copy [template_algorithm.py](template_algorithm.py)

## Overview

The sweep algorithms framework provides multiple strategies for finding optimal beam directions:

- **Linear Brute-Force**: Tests all angles in equal steps (comprehensive, predictable)
- **Adaptive Center-Out**: Intelligent expansion from specular angle (~30% more efficient)
- **Random Search**: Random sampling for large search spaces (extensible)

## Available Algorithms

### Linear Brute-Force Sweep
**File**: `linear_brute_force.py`
**Aliases**: `linear`, `brute-force`

Tests all beam angles across the field of view in equal steps.

**Parameters**:
- `fov` (float): Field of view in degrees (default: 60)
- `step` (float): Coarse step size in degrees (default: 10)
- `fine_span` (float): Fine search span around best coarse angle (default: 10)
- `fine_res` (float): Fine resolution in degrees (default: 1)

**Strategy**:
1. Coarse Phase: Tests angles from -FOV to +FOV in equal steps
2. Fine Phase: Refines around best coarse angle with finer resolution

**Usage**:
```bash
sweep AP1 R1 UE1 60 10 --algo linear
sweep AP1 R1 UE1 60 10 --algo brute-force
```

**Output**:
- 13 coarse angles (at 10° steps for FOV=60)
- 21 fine angles (1° resolution around best)
- Best local angle and SNR

---

### Adaptive Center-Out Sweep
**File**: `adaptive_center_out.py`
**Aliases**: `adaptive`, `center-out`

Intelligent beam steering starting from specular reflection angle and expanding adaptively.

**Parameters**:
- `fov` (float): Field of view in degrees (default: 60)
- `step` (float): Coarse step size in degrees (default: 10)
- `fine_span` (float): Fine search span (default: 10)
- `fine_res` (float): Fine resolution in degrees (default: 1)

**Strategy**:
1. Calculate specular reflection angle from AP→RIS→UE geometry
2. Coarse Phase: Test center (specular) first, then expand outward
3. Fine Phase: Refine around best coarse angle

**Efficiency**: ~30% fewer measurements compared to exhaustive search

**Usage**:
```bash
sweep AP1 R1 UE1 60 10 --algo adaptive
sweep AP1 R1 UE1 60 10 --algo center-out
```

**Output**:
- 13 coarse angles (center-out order)
- 21 fine angles (1° resolution around best)
- Best local angle and SNR
- Specular angle reference

---

## How to Add a New Algorithm

### Step 1: Create Algorithm File

Create a new file in `controller/beamsweeping/algorithms/` (e.g., `random_search.py`):

```python
"""Random Search Beam Sweep Algorithm

Randomly samples beam angles from the FOV to find optimal direction.
Useful for exploring large search spaces efficiently.
"""

import numpy as np
from typing import Dict
from ..base import SweepAlgorithmBase
from ..registry import register_algorithm
from ..common import compute_specular_angle


@register_algorithm("random-search", aliases=("random",))
class RandomSearchSweep(SweepAlgorithmBase):
    """Random search beam sweep algorithm"""

    @property
    def name(self) -> str:
        return "Random Search Sweep"

    @property
    def description(self) -> str:
        return "Randomly samples angles from FOV. Good for large search spaces."

    def sweep(self, ap_name: str, ris_name: str, ue_name: str,
              fov: float = 60.0, step: float = 10.0,
              num_samples: int = 20,
              seed: int = 42) -> Dict:
        """Execute random search sweep

        Args:
            ap_name: Access Point name
            ris_name: RIS name
            ue_name: User Equipment name
            fov: Field of view in degrees
            step: Not used in random search
            num_samples: Number of random samples (default: 20)
            seed: Random seed

        Returns:
            Dictionary with sweep results
        """
        ap = self.network.get(ap_name)
        ris = self.network.get(ris_name)
        ue = self.network.get(ue_name)

        if ap is None or ris is None or ue is None:
            raise ValueError("Invalid node name in sweep")

        np.random.seed(seed)

        # Calculate base direction
        base_dir = compute_specular_angle(ris, ue)

        # Generate random angles
        local_angles = np.random.uniform(-fov, fov, num_samples)
        local_angles = np.sort(local_angles)
        abs_angles = base_dir + local_angles

        snr_values = []
        pwr_values = []

        # Test random angles
        for abs_a in abs_angles:
            res = self.network.connect(ap_name, ris_name, ue_name,
                                      beam_angle_deg=abs_a, seed=seed)
            snr_values.append(res['snr_dB'])
            pwr_values.append(res['pwr_dBm'])

        # Find best
        best_idx = int(np.argmax(snr_values))
        best_local = local_angles[best_idx]

        return {
            'local_coarse': local_angles.tolist(),
            'snr_coarse': snr_values,
            'pwr_coarse': pwr_values,
            'local_fine': [best_local],
            'snr_fine': [snr_values[best_idx]],
            'best_local_fine': float(best_local),
            'best_snr_fine': float(snr_values[best_idx])
        }
```

### Step 2: Register Using the Decorator

No manual edits to `__init__.py` are required. Simply decorate your class (as
shown above) with `@register_algorithm("primary-name", aliases=(...))`. The loader
discovers the algorithm automatically and exposes it through the CLI/APIs.

### Step 3: Use in CLI

```bash
sweep AP1 R1 UE1 60 10 --algo random
sweep AP1 R1 UE1 60 10 --algo random-search
```

---

## Algorithm Requirements

Every algorithm MUST:

1. **Inherit from `SweepAlgorithmBase`**
   ```python
   from .base import SweepAlgorithmBase

   class MyAlgorithm(SweepAlgorithmBase):
       pass
   ```

2. **Implement `name` property**
   ```python
   @property
   def name(self) -> str:
       return "My Algorithm Name"
   ```

3. **Implement `description` property**
   ```python
   @property
   def description(self) -> str:
       return "Brief description of algorithm"
   ```

4. **Implement `sweep()` method**
   ```python
   def sweep(self, ap_name: str, ris_name: str, ue_name: str,
             fov: float = 60.0, step: float = 10.0,
             seed: int = 42) -> Dict:
       # Implementation
       pass
   ```

5. **Return required dictionary keys**
   ```python
   return {
       'local_coarse': [...],      # List of coarse angles
       'snr_coarse': [...],        # List of SNR values for coarse angles
       'pwr_coarse': [...],        # List of power values for coarse angles
       'local_fine': [...],        # List of fine angles
       'snr_fine': [...],          # List of SNR values for fine angles
       'best_local_fine': float,   # Best local angle (degrees)
       'best_snr_fine': float,     # Best SNR (dB)
   }
   ```

---

## Base Class Reference

### `SweepAlgorithmBase`

**Location**: `base.py`

**Constructor**:
```python
def __init__(self, network):
    """
    Args:
        network: RISNetwork object
    """
```

**Required Properties**:
- `name`: Algorithm display name
- `description`: Short description

**Required Methods**:
- `sweep()`: Execute sweep and return results

**Optional Methods**:
- `get_info()`: Returns dict with 'name' and 'description'

**Available Attributes**:
- `self.network`: RISNetwork object for accessing nodes and executing connections

---

## CLI Usage

### Basic Sweep
```bash
# Use default (linear) algorithm
sweep AP1 R1 UE1

# Specify FOV and step
sweep AP1 R1 UE1 60 10
```

### With Algorithm Selection
```bash
# Linear algorithm
sweep AP1 R1 UE1 60 10 --algo linear

# Adaptive algorithm
sweep AP1 R1 UE1 60 10 --algo adaptive

# Custom algorithm
sweep AP1 R1 UE1 60 10 --algo random
```

### Error Handling
```bash
# Invalid algorithm
$ sweep AP1 R1 UE1 --algo invalid
Error: Unknown sweep algorithm: invalid
Available algorithms: linear, brute-force, adaptive, center-out

# Invalid nodes
$ sweep INVALID R1 UE1
Sweep failed: Invalid node name in sweep
```

---

## Output Format

All sweep results display in a consistent format:

```
============================================================
BEAM SWEEP RESULTS
============================================================

Algorithm: Linear Brute-Force Sweep
  Tests all beam angles across FOV in equal steps. Two-phase: coarse + fine refinement.
  FOV: 60.0°, Step: 10.0°

Coarse Search (13 angles):
  Local angles: [-60.0, -50.0, ..., 50.0, 60.0]
  SNR values:   [32.89, 34.49, ..., 34.49, 32.89]

Refined Results (21 angles):
  Best local angle: 0.00 degrees
  Best SNR:         42.49 dB
============================================================
```

---

## Architecture

### File Structure
```
controller/beamsweeping/
├── base.py                          # Base class for all algorithms
├── registry.py                      # Registration + lookup
├── common.py                        # Shared math + waveform helpers
├── algorithms/
│   ├── __init__.py                  # Imports concrete algorithms
│   ├── linear_brute_force.py        # Linear brute-force sweep
│   ├── coarse_fine_sweep.py         # Adaptive center-out sweep
│   ├── directional_exhaustive_sweep.py # Directional exhaustive sweep
│   └── ...                          # Your custom algorithms
├── template_algorithm.py            # Copy helper
└── README.md                        # This file
```

### Class Hierarchy
```
SweepAlgorithmBase (abstract base class)
├── LinearBruteForceSweep
├── AdaptiveCenterOutSweep
└── RandomSearchSweep
    (extends with your custom algorithms)
```

### Algorithm Factory Pattern
```python
# Loader handles algorithm selection transparently
SweepAlgorithmLoader.get_algorithm('linear', network)
  → Returns: LinearBruteForceSweep(network)

SweepAlgorithmLoader.get_algorithm('adaptive', network)
  → Returns: AdaptiveCenterOutSweep(network)

SweepAlgorithmLoader.list_algorithms()
  → Returns: Dict of available algorithms with info
```

---

## Best Practices

1. **Always validate inputs**
   ```python
   if ap is None or ris is None or ue is None:
       raise ValueError("Invalid node name in sweep")
   ```

2. **Use consistent naming**
   - Algorithm file: `lowercase_with_underscores.py`
   - Class name: `PascalCaseSweep`
   - CLI alias: `lowercase-with-dashes`

3. **Add docstrings**
   ```python
   def sweep(self, ...) -> Dict:
       """Detailed docstring with Args and Returns"""
   ```

4. **Return consistent dictionary**
   - Always include all required keys
   - Use float for angle values
   - Use list for angle/SNR arrays

5. **Document your algorithm**
   - Add class-level docstring
   - Document all parameters
   - Explain the strategy

6. **Test thoroughly**
   - Test with various node configurations
   - Test edge cases (FOV bounds, etc.)
   - Verify output format is correct

---

## Extension Examples

### Genetic Algorithm
```python
class GeneticAlgorithmSweep(SweepAlgorithmBase):
    """Uses genetic algorithms to optimize beam angle"""
    # Implement population-based search
```

### Particle Swarm Optimization
```python
class PSOSweep(SweepAlgorithmBase):
    """Uses PSO to find optimal beam angle"""
    # Implement swarm-based search
```

### Machine Learning
```python
class MLPredictorSweep(SweepAlgorithmBase):
    """Uses ML model to predict optimal angle"""
    # Implement model-based prediction
```

---

## Testing

To test a new algorithm:

```bash
# In CLI
risnet> add ap
risnet> add ris
risnet> add ue
risnet> sweep AP1 R1 UE1 60 10 --algo your-algo

# In Python
from controller.beamsweeping import SweepAlgorithmLoader
algo = SweepAlgorithmLoader.get_algorithm('your-algo', network)
result = algo.sweep('AP1', 'R1', 'UE1')
print(f"Best SNR: {result['best_snr_fine']:.2f} dB")
```

---

## Contributing

To contribute a new algorithm:

1. Create algorithm file following the template
2. Decorate the class with `@register_algorithm(...)`
3. Add documentation in this README
4. Test thoroughly with various configurations
5. Submit with examples and performance metrics

