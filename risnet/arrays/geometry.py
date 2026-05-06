"""Array geometry helpers."""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np


def centered_planar_grid(
    rows: int,
    cols: int,
    spacing: float,
    center: Optional[Sequence[float]] = None,
) -> np.ndarray:
    """Return a centered planar grid in row-major ``(x, y, z)`` coordinates.

    The element ordering intentionally matches ``core.nodes.RIS.update_geometry``:
    the row index advances along ``x`` and the column index advances along ``y``.
    """
    if rows <= 0 or cols <= 0:
        raise ValueError("rows and cols must be positive")
    if spacing <= 0:
        raise ValueError("spacing must be positive")

    center_vec = np.zeros(3, dtype=float) if center is None else np.asarray(center, dtype=float)
    if center_vec.shape != (3,):
        raise ValueError("center must be a 3D coordinate")

    positions = np.zeros((rows * cols, 3), dtype=float)
    idx = 0
    for i in range(rows):
        for j in range(cols):
            x_off = (i - (rows - 1) / 2.0) * spacing
            y_off = (j - (cols - 1) / 2.0) * spacing
            positions[idx] = center_vec + np.array([x_off, y_off, 0.0])
            idx += 1

    return positions


def square_planar_grid(
    array_size: int,
    spacing: float,
    center: Optional[Sequence[float]] = None,
) -> np.ndarray:
    """Return a centered ``array_size`` by ``array_size`` planar grid."""
    return centered_planar_grid(array_size, array_size, spacing, center=center)
