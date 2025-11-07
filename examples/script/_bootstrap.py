"""
Utilities to make example scripts runnable without installing the package.
"""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_project_root() -> None:
    """Add the repository root to sys.path if it is missing."""
    root = Path(__file__).resolve().parents[2]
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
