"""
Backward compatibility shim for the legacy `risnet_cli` module path.

The actual implementation now lives in `risnet.cli`.
"""

from risnet.cli import RISnetCLI

__all__ = ["RISnetCLI"]
