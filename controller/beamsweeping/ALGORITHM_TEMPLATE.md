# Beam Sweep Algorithm Development Guide

This guide provides a standardized format for implementing new beam sweeping algorithms in RISNet.

## Overview

All beam sweep algorithms must inherit from `SweepAlgorithmBase` and implement a consistent interface. This ensures:
- Compatibility with the CLI and web interface
- Consistent output format for result analysis
- Easy integration with the algorithm loader

## Standard Algorithm Structure

### 1. File Organization

Each algorithm should be in its own file under `controller/beamsweeping/`:
```
controller/beamsweeping/
├── base.py                          # Abstract base class
├── linear_brute_force.py            # Algorithm 1
├── adaptive_center_out.py           # Algorithm 2
├── my_new_algorithm.py              # Your new algorithm
└── __init__.py                      # Loader registration
```

### 2. Class Structure Template

```python
"""Description of your beam sweep algorithm

Explain the algorithm strategy, phases, and efficiency characteristics.
Example:
- Phase 1: Coarse sweep with X° steps
- Phase 2: Fine refinement around best angle
- Efficiency: ~Y% measurement savings vs exhaustive search
"""

import numpy as np
from typing import Dict
from .base import SweepAlgorithmBase


class MyAlgorithmSweep(SweepAlgorithmBase):
    """Descriptive class name for the algorithm"""

    @property
    def name(self) -> str:
        """Return algorithm name (displayed to users)"""
        return "My Algorithm Name Sweep"

    @property
    def description(self) -> str:
        """Return algorithm description (displayed to users)"""
        return "Brief description of how the algorithm works and its benefits."

    def sweep(self, ap_name: str, ris_name: str, ue_name: str,
              fov: float = 60.0, step: float = 10.0,
              fine_span: float = 10.0, fine_res: float = 1.0,
              seed: int = 42) -> Dict:
        """Execute beam sweep

        Args:
            ap_name (str): Access Point name
            ris_name (str): RIS node name
            ue_name (str): User Equipment name
            fov (float): Field of view in degrees (default: 60)
            step (float): Coarse step size in degrees (default: 10)
            fine_span (float): Fine search span around best coarse angle (default: 10)
            fine_res (float): Fine resolution in degrees (default: 1)
            seed (int): Random seed for reproducibility (default: 42)

        Returns:
            Dict: Dictionary with the following required keys:
                - local_coarse (list): Local angles tested in coarse phase
                - snr_coarse (list): SNR values [dB] for coarse angles
                - pwr_coarse (list): Power values [dBm] for coarse angles
                - local_fine (list): Local angles tested in fine phase
                - snr_fine (list): SNR values [dB] for fine angles
                - best_local_fine (float): Best local angle [degrees]
                - best_snr_fine (float): Best SNR [dB]

                Optional keys:
                - algorithm_metadata (dict): Custom algorithm-specific data
                - measurement_count (int): Total measurements performed
                - efficiency_ratio (float): Measurement efficiency metric
                - specular_angle (float): Reference specular angle [degrees]
        """
        # Validate inputs
        ap = self.network.get(ap_name)
        ris = self.network.get(ris_name)
        ue = self.network.get(ue_name)

        if ap is None or ris is None or ue is None:
            raise ValueError("Invalid node name in sweep")

        # PHASE 1: Coarse sweep
        # ========================
        # Strategy: [Describe your coarse search strategy]

        # Calculate reference angle(s)
        # (e.g., specular reflection, geometric center, etc.)
        vec = ue.pos - ris.pos
        base_dir = np.degrees(np.arctan2(vec[1], vec[0]))

        # Generate coarse angles
        local_coarse = np.arange(-fov, fov + 1, step)
        abs_angles = base_dir + local_coarse

        snr_coarse = []
        pwr_coarse = []

        # Test each coarse angle
        for abs_a in abs_angles:
            res = self.network.connect(ap_name, ris_name, ue_name,
                                      beam_angle_deg=abs_a, seed=seed)
            snr_coarse.append(res['snr_dB'])
            pwr_coarse.append(res['pwr_dBm'])

        # Find best coarse angle
        best_idx = int(np.argmax(snr_coarse))
        best_local = local_coarse[best_idx]

        # PHASE 2: Fine refinement
        # ========================
        # Strategy: [Describe your fine refinement strategy]

        local_fine = np.arange(best_local - fine_span,
                              best_local + fine_span + fine_res,
                              fine_res)
        abs_angles_fine = base_dir + local_fine
        snr_fine = []

        for abs_a in abs_angles_fine:
            r = self.network.connect(ap_name, ris_name, ue_name,
                                    beam_angle_deg=abs_a, seed=seed)
            snr_fine.append(r['snr_dB'])

        best_fine_idx = int(np.argmax(snr_fine))
        best_local_fine = local_fine[best_fine_idx]

        # Prepare output
        return {
            'local_coarse': local_coarse.tolist(),
            'snr_coarse': np.array(snr_coarse).tolist(),
            'pwr_coarse': np.array(pwr_coarse).tolist(),
            'local_fine': local_fine.tolist(),
            'snr_fine': np.array(snr_fine).tolist(),
            'best_local_fine': float(best_local_fine),
            'best_snr_fine': float(np.max(snr_fine)),
        }
```

## Return Dictionary Specification

All algorithms MUST return a dictionary with these required keys:

| Key | Type | Description | Unit |
|-----|------|-------------|------|
| `local_coarse` | list[float] | Angles tested in coarse phase (relative to reference) | degrees |
| `snr_coarse` | list[float] | SNR values for coarse angles | dB |
| `pwr_coarse` | list[float] | Power values for coarse angles | dBm |
| `local_fine` | list[float] | Angles tested in fine phase (relative to reference) | degrees |
| `snr_fine` | list[float] | SNR values for fine angles | dB |
| `best_local_fine` | float | Best angle found (relative to reference) | degrees |
| `best_snr_fine` | float | Best SNR found | dB |

### Optional Keys

| Key | Type | Description |
|-----|------|-------------|
| `specular_angle` | float | Reference angle used (e.g., for specular reflection algorithms) |
| `algorithm_metadata` | dict | Custom algorithm-specific metadata |
| `measurement_count` | int | Total beams/angles tested |
| `efficiency_ratio` | float | Measurements used / Total possible measurements |

## Integration Checklist

To integrate a new algorithm:

### Step 1: Create Algorithm File
- [ ] Create `my_algorithm.py` in `controller/beamsweeping/`
- [ ] Inherit from `SweepAlgorithmBase`
- [ ] Implement `name` property
- [ ] Implement `description` property
- [ ] Implement `sweep()` method with correct signature
- [ ] Return dictionary with all required keys

### Step 2: Register Algorithm
Edit `controller/beamsweeping/__init__.py`:
```python
from .my_algorithm import MyAlgorithmSweep

class SweepAlgorithmLoader:
    ALGORITHMS = {
        'linear': LinearBruteForceSweep,
        'adaptive': AdaptiveCenterOutSweep,
        'my-algo': MyAlgorithmSweep,  # ADD THIS LINE
    }
```

### Step 3: Test Algorithm
```bash
# CLI test
python main.py --cli
risnet> add ap AP1
risnet> add ris R1
risnet> add ue UE1
risnet> sweep AP1 R1 UE1 60 10 --algo my-algo

# Web interface
python main.py --web
# Open browser, try algorithm in dropdown
```

### Step 4: Documentation
- [ ] Document algorithm strategy in module docstring
- [ ] Document parameters in `sweep()` docstring
- [ ] Add to algorithm comparison table (if applicable)

## Algorithm Design Patterns

### Pattern 1: Two-Phase Search
```
Phase 1 (Coarse):  Wide search, large step size
Phase 2 (Fine):    Narrow range, small step size around best coarse
```

### Pattern 2: Adaptive Direction Selection
```
Phase 1: Test symmetric (left and right)
Phase 2: Continue in direction showing better SNR
```

### Pattern 3: Specular Angle Reference
```
Calculate specular reflection angle as reference
Search is relative to specular angle
Return both relative and absolute angles
```

## Example: Add a New "Quadrant Search" Algorithm

```python
"""Quadrant Search Beam Sweep Algorithm

Divides FOV into 4 quadrants, searches quadrant with best SNR first.
- Phase 1: Test one angle in each quadrant
- Phase 2: Fine search in best quadrant
Efficiency: ~50% savings vs linear sweep
"""

import numpy as np
from typing import Dict
from .base import SweepAlgorithmBase


class QuadrantSearchSweep(SweepAlgorithmBase):
    """Quadrant-based beam search algorithm"""

    @property
    def name(self) -> str:
        return "Quadrant Search Sweep"

    @property
    def description(self) -> str:
        return "Divides FOV into 4 quadrants, refines best. ~50% measurement savings."

    def sweep(self, ap_name: str, ris_name: str, ue_name: str,
              fov: float = 60.0, step: float = 10.0,
              fine_span: float = 10.0, fine_res: float = 1.0,
              seed: int = 42) -> Dict:
        ap = self.network.get(ap_name)
        ris = self.network.get(ris_name)
        ue = self.network.get(ue_name)

        if ap is None or ris is None or ue is None:
            raise ValueError("Invalid node name in sweep")

        # Calculate base direction
        vec = ue.pos - ris.pos
        base_dir = np.degrees(np.arctan2(vec[1], vec[0]))

        # Phase 1: Test 4 quadrants
        quadrant_angles = np.array([-fov/2, -fov/4, fov/4, fov/2])
        abs_angles_q = base_dir + quadrant_angles
        snr_q = []
        pwr_q = []

        for abs_a in abs_angles_q:
            res = self.network.connect(ap_name, ris_name, ue_name,
                                      beam_angle_deg=abs_a, seed=seed)
            snr_q.append(res['snr_dB'])
            pwr_q.append(res['pwr_dBm'])

        # Find best quadrant
        best_q_idx = int(np.argmax(snr_q))
        best_q_angle = quadrant_angles[best_q_idx]

        # Phase 2: Fine search in best quadrant
        local_fine = np.arange(best_q_angle - fov/4,
                              best_q_angle + fov/4 + fine_res,
                              fine_res)
        abs_angles_fine = base_dir + local_fine
        snr_fine = []

        for abs_a in abs_angles_fine:
            r = self.network.connect(ap_name, ris_name, ue_name,
                                    beam_angle_deg=abs_a, seed=seed)
            snr_fine.append(r['snr_dB'])

        best_fine_idx = int(np.argmax(snr_fine))
        best_local_fine = local_fine[best_fine_idx]

        # Prepare output (note: coarse angles are quadrant sample points)
        return {
            'local_coarse': quadrant_angles.tolist(),
            'snr_coarse': snr_q,
            'pwr_coarse': pwr_q,
            'local_fine': local_fine.tolist(),
            'snr_fine': snr_fine,
            'best_local_fine': float(best_local_fine),
            'best_snr_fine': float(np.max(snr_fine)),
        }
```

Then register in `__init__.py`:
```python
from .quadrant_search import QuadrantSearchSweep

ALGORITHMS = {
    'linear': LinearBruteForceSweep,
    'adaptive': AdaptiveCenterOutSweep,
    'quadrant': QuadrantSearchSweep,
}
```

## Performance Metrics

When implementing a new algorithm, measure:

1. **Measurement Count**: Total angles tested
2. **Efficiency Ratio**: `tested_angles / total_possible_angles`
3. **SNR Quality**: How close to optimal SNR
4. **Convergence Speed**: Steps to find best angle
5. **Robustness**: Performance across different geometries

## Output Format

The detailed CLI sweep output displays:

```
BEAM SWEEP INITIALIZATION
  Algorithm: [name]
  Description: [description]
  Parameters: AP, RIS, UE, FOV, Step

EXECUTING SWEEP...

[PHASE 1] COARSE SEARCH
  Angle (°)  SNR (dB)  Power (dBm)
  [table of results]
  Best coarse angle: X° with SNR = Y dB

[PHASE 2] FINE REFINEMENT
  Angle (°)  SNR (dB)
  [table of results]

SWEEP RESULTS SUMMARY
  Optimal Beam Configuration:
    Local Angle: X°
    Maximum SNR: Y dB
    Total Angles: N tested
    Efficiency: X% refined
```

## Testing Your Algorithm

Create a test script:

```python
from core import RISNetwork
from controller.beamsweeping import SweepAlgorithmLoader

net = RISNetwork()
net.add_ap('AP1', 0, 0, 0)
net.add_ris('R1', 5, 5, 0, N=16, bits=2)
net.add_ue('UE1', 10, 10, 0)

algo = SweepAlgorithmLoader.get_algorithm('my-algo', net)
result = algo.sweep('AP1', 'R1', 'UE1', fov=60, step=10)

assert 'local_coarse' in result
assert 'best_snr_fine' in result
print(f"Best SNR: {result['best_snr_fine']} dB")
print(f"Angles tested: {len(result['local_coarse']) + len(result['local_fine'])}")
```

## Best Practices

1. **Validation**: Always validate input node names
2. **Error Handling**: Raise `ValueError` with clear messages
3. **Documentation**: Document algorithm strategy in docstring
4. **Consistent Units**: Always use degrees for angles, dB for SNR, dBm for power
5. **Return Format**: Always return required dictionary keys
6. **Efficiency**: Consider measurement count when designing algorithm
7. **Testing**: Test with various FOV and step sizes
8. **Reproducibility**: Use `seed` parameter for deterministic results

## Common Issues

### Issue: "Algorithm not found"
**Solution**: Ensure algorithm is registered in `__init__.py` ALGORITHMS dictionary

### Issue: Output format mismatch
**Solution**: Verify all required dictionary keys are present and correct type

### Issue: Different SNR values than other algorithms
**Solution**: Ensure using same `self.network.connect()` function for consistency

### Issue: CLI sweep output doesn't show data
**Solution**: Check that coarse/fine lists have matching SNR lists
