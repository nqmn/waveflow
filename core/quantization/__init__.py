"""
Phase quantization strategies for RIS simulation

This package provides modular, loadable quantization strategies for RIS phase shifters.

Built-in quantizers:
- UniformQuantizer: Standard uniform quantization (2π / 2^bits levels)
- LegacyQuantizer: Original RISNet formula (backward compatible)

Custom quantizers can be loaded from plugin folders via the registry.

Example:
    from core.quantization import get_registry, get_quantizer

    # Get a specific quantizer
    quantizer = get_quantizer('uniform')
    quantized, states = quantizer.quantize(ideal_phases, bits=2)

    # List available quantizers
    from core.quantization import list_quantizers
    print(list_quantizers())

    # Load custom quantizers from folder
    from core.quantization import load_quantizers_from_folder
    load_quantizers_from_folder('path/to/plugins')
"""

from .base import BaseQuantizer
from .uniform import UniformQuantizer
from .legacy import LegacyQuantizer
from .registry import (
    QuantizerRegistry,
    get_registry,
    register_quantizer,
    get_quantizer,
    list_quantizers,
    load_quantizers_from_folder
)

__all__ = [
    'BaseQuantizer',
    'UniformQuantizer',
    'LegacyQuantizer',
    'QuantizerRegistry',
    'get_registry',
    'register_quantizer',
    'get_quantizer',
    'list_quantizers',
    'load_quantizers_from_folder',
]
