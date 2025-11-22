"""
MATLAB Integration for RISNet.

This module provides a bridge between RISNet Python and MATLAB Engine,
enabling advanced visualization and computation capabilities.

All imports are lazy-loaded to avoid importing matlab.engine until needed.

Usage:
    from risnet.matlab import MatlabBridge, MatlabIntegration

    # Direct bridge access
    bridge = MatlabBridge.get_instance()
    bridge.plot_ris_geometry(...)

    # High-level integration with RISNetwork
    from risnet.core.network import RISNetwork
    net = RISNetwork()
    matlab = MatlabIntegration(net)
    matlab.plot_ris("RIS1")
"""

__all__ = [
    'MatlabBridge',
    'MatlabIntegration',
    'numpy_to_matlab',
    'matlab_to_numpy',
]


def __getattr__(name: str):
    """Lazy load module components only when accessed."""
    if name == 'MatlabBridge':
        from .bridge import MatlabBridge
        return MatlabBridge
    elif name == 'MatlabIntegration':
        from .integration import MatlabIntegration
        return MatlabIntegration
    elif name == 'numpy_to_matlab':
        from .converters import numpy_to_matlab
        return numpy_to_matlab
    elif name == 'matlab_to_numpy':
        from .converters import matlab_to_numpy
        return matlab_to_numpy
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
