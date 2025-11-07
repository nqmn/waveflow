# Phase Quantization System

Modular, extensible phase quantization strategies for RIS simulation.

## Overview

The phase quantization system provides pluggable strategies for quantizing ideal RIS phases to discrete levels based on available bits. This allows for:

- **Built-in strategies**: Uniform and Legacy quantization
- **Custom plugins**: Easily add new quantization methods
- **Runtime switching**: Change quantization strategy on-the-fly
- **Configuration**: Store and load quantizer settings

## Built-in Quantizers

### Uniform Quantizer
Standard uniform quantization where phases are rounded to the nearest of 2^bits discrete levels uniformly spaced from 0 to 2π.

```python
from core.quantization import get_quantizer

quantizer = get_quantizer('uniform')
quantized, states = quantizer.quantize(ideal_phases, bits=2)
```

### Legacy Quantizer
Original RISNet quantization formula for backward compatibility with existing simulations.

```python
quantizer = get_quantizer('legacy')
quantized, states = quantizer.quantize(ideal_phases, bits=2)
```

## Using Quantizers in RIS

### Default (Uniform)
```python
from core import RIS

ris = RIS('R1', x=5, y=5, N=8, bits=2)  # Uses 'uniform' by default
```

### Specify Quantizer
```python
ris = RIS('R1', x=5, y=5, N=8, bits=2, quantizer_name='legacy')
```

### Change Quantizer at Runtime
```python
ris.set_quantizer('legacy')  # Switch to legacy quantization
ris.quantize_phases()  # Re-quantize with new strategy
```

## Creating Custom Quantizers

Create a new quantizer by implementing the `BaseQuantizer` interface:

### 1. Create Plugin Folder
```
core/quantization/plugins/
└── my_quantizer/
    ├── quantizer.py      # Main quantizer class
    └── config.json       # Optional metadata
```

### 2. Implement Quantizer Class
```python
# my_quantizer/quantizer.py
import numpy as np
from core.quantization.base import BaseQuantizer

class Quantizer(BaseQuantizer):
    """Your custom quantization strategy"""

    def __init__(self):
        super().__init__(
            name='my_quantizer',
            description='Custom quantization description'
        )

    def quantize(self, ideal_phases, bits):
        """
        Args:
            ideal_phases: numpy array of phases in radians
            bits: number of quantization bits

        Returns:
            (quantized_phases, phase_states) tuple
        """
        if bits == 0:
            return ideal_phases, np.zeros_like(ideal_phases, dtype=int)

        # Your quantization logic here
        num_levels = 2 ** bits
        phase_step = 2 * np.pi / num_levels

        quantized = np.round(ideal_phases / phase_step) * phase_step
        quantized = np.mod(quantized, 2 * np.pi)
        states = (quantized / phase_step).astype(int) % num_levels

        return quantized, states
```

### 3. Add Config (Optional)
```json
{
  "name": "my_quantizer",
  "description": "Custom quantization description",
  "version": "1.0",
  "author": "Your Name",
  "parameters": {}
}
```

### 4. Load and Use Plugin
```python
from core.quantization import load_quantizers_from_folder, get_quantizer

# Load plugins from folder
load_quantizers_from_folder('core/quantization/plugins')

# Use your custom quantizer
quantizer = get_quantizer('my_quantizer')
quantized, states = quantizer.quantize(ideal_phases, bits=2)

# Or with RIS
ris = RIS('R1', x=5, y=5, quantizer_name='my_quantizer')
```

## API Reference

### Registry Functions

```python
from core.quantization import (
    get_registry,
    register_quantizer,
    get_quantizer,
    list_quantizers,
    load_quantizers_from_folder
)

# Get global registry
registry = get_registry()

# List available quantizers
quantizers = list_quantizers()
for name, desc in quantizers:
    print(f"{name}: {desc}")

# Get specific quantizer
q = get_quantizer('uniform')

# Register new quantizer
register_quantizer(my_quantizer_instance)

# Load plugins from folder
load_quantizers_from_folder('path/to/plugins')
```

### Quantizer Interface

All quantizers inherit from `BaseQuantizer`:

```python
from core.quantization import BaseQuantizer

class MyQuantizer(BaseQuantizer):
    def __init__(self):
        super().__init__(name='my_name', description='...')

    def quantize(self, ideal_phases, bits):
        """Main quantization method"""
        pass

    def get_phase_step(self, bits):
        """Get phase step size"""
        return 2 * np.pi / (2 ** bits)

    def get_num_levels(self, bits):
        """Get number of quantization levels"""
        return 2 ** bits
```

## Example Plugin: Adaptive Quantization

See `plugins/adaptive_quantizer/` for a complete example that adapts quantization levels based on phase magnitude.

## Directory Structure

```
quantization/
├── __init__.py              # Package init, exports main API
├── base.py                  # BaseQuantizer abstract class
├── uniform.py               # UniformQuantizer
├── legacy.py                # LegacyQuantizer
├── registry.py              # QuantizerRegistry and loader
├── README.md                # This file
└── plugins/                 # Custom quantizer plugins
    └── adaptive_quantizer/
        ├── quantizer.py
        └── config.json
```

## Best Practices

1. **Always inherit from BaseQuantizer** - Ensures compatibility
2. **Implement quantize() method** - Core quantization logic
3. **Return (quantized, states) tuple** - Expected return format
4. **Handle edge cases** - bits=0 (no quantization), empty arrays
5. **Use descriptive names** - Clear plugin folder and quantizer names
6. **Document parameters** - Use config.json for metadata
7. **Test thoroughly** - Verify quantization across phase ranges

## Notes

- Quantizers are loaded once at registry initialization
- Default quantizer is 'uniform'
- Missing quantizers fallback to 'uniform'
- Plugin discovery is one-time at `load_quantizers_from_folder()` call
