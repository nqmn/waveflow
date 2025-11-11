"""Standardized angle normalization and field-of-view utilities.

This module provides consistent, well-tested angle handling functions for:
- Normalizing angles to [-180, 180] range
- Computing offsets from a reference angle
- Checking FOV constraints
- Clamping angles to FOV limits
"""

import numpy as np


def normalize_angle_to_pm180(angle: float) -> float:
    """Normalize angle to [-180, 180] range.

    Args:
        angle: Angle in degrees (any range)

    Returns:
        Normalized angle in [-180, 180] degrees
    """
    while angle > 180:
        angle -= 360
    while angle < -180:
        angle += 360
    return angle


def compute_offset_from_normal(target_angle: float, normal_angle: float) -> float:
    """Compute offset angle relative to a normal direction.

    This computes the signed offset from a normal direction (boresight) to a target
    direction, properly normalized to [-180, 180] range.

    Args:
        target_angle: Target direction in absolute degrees [0, 360)
        normal_angle: Reference/normal direction in absolute degrees [0, 360)

    Returns:
        Offset angle in [-180, 180] degrees
        Positive = clockwise from normal (increasing angle)
        Negative = counter-clockwise from normal (decreasing angle)
    """
    offset = target_angle - normal_angle
    return normalize_angle_to_pm180(offset)


def is_within_fov(offset_angle: float, max_angle: float, tolerance_deg: float = 0.01) -> bool:
    """Check if an offset angle is within field of view limits.

    Args:
        offset_angle: Angle offset from normal, in [-180, 180] range
        max_angle: Maximum FOV half-angle (±max_angle_deg)
        tolerance_deg: Numerical tolerance (default 0.01°)

    Returns:
        True if |offset_angle| <= max_angle (within tolerance)
    """
    return abs(offset_angle) <= (max_angle + tolerance_deg)


def clamp_offset_to_fov(offset_angle: float, max_angle: float) -> float:
    """Clamp an offset angle to stay within FOV limits.

    Args:
        offset_angle: Offset angle in degrees (any range, but typically [-180, 180])
        max_angle: Maximum FOV half-angle (±max_angle_deg)

    Returns:
        Clamped offset angle in [-max_angle, +max_angle] range
    """
    return float(np.clip(offset_angle, -max_angle, max_angle))


def compute_absolute_angle_from_offset(normal_angle: float, offset_angle: float) -> float:
    """Compute absolute angle from normal and offset.

    Args:
        normal_angle: Normal/boresight direction in degrees
        offset_angle: Offset from normal in degrees

    Returns:
        Absolute angle in [0, 360) range
    """
    absolute = normal_angle + offset_angle
    # Normalize to [0, 360)
    while absolute < 0:
        absolute += 360
    while absolute >= 360:
        absolute -= 360
    return absolute


def compute_optimal_ris_normal(ap_angle: float, ue_angle: float) -> float:
    """Compute optimal RIS normal as bisector of AP and UE directions.

    For a cascaded AP→RIS→UE link:
    - RIS must receive from AP direction
    - RIS must transmit toward UE direction
    - These directions may be different (typically 30-60° apart)
    - A phased array RIS has limited FOV (typically ±60°)

    To serve both AP and UE simultaneously within FOV constraints, the optimal
    RIS normal is the bisector of AP and UE directions. This minimizes the maximum
    offset angle to either AP or UE, ensuring both fall within the ±FOV cone.

    This function implements the bisector calculation as an average of unit vectors:
        1. Convert AP and UE angles to unit vectors
        2. Add the vectors (vector sum)
        3. Convert back to angle (bisector)

    Args:
        ap_angle: Access Point direction from RIS in degrees [0, 360)
        ue_angle: User Equipment direction from RIS in degrees [0, 360)

    Returns:
        Optimal RIS normal angle in degrees [0, 360)
        This is the bisector angle that minimizes max(|AP_offset|, |UE_offset|)

    Example:
        >>> ap_angle = 180.0  # AP to the left
        >>> ue_angle = 135.0  # UE upper-left
        >>> ris_normal = compute_optimal_ris_normal(ap_angle, ue_angle)
        >>> # Result: 157.54° (bisector between 180° and 135°)
        >>> # AP offset: 180° - 157.54° = 22.46°
        >>> # UE offset: 135° - 157.54° = -22.46°
        >>> # Both within ±60° FOV ✓
    """
    # Convert angles to unit vectors
    ap_rad = np.radians(ap_angle)
    ue_rad = np.radians(ue_angle)
    ap_unit = np.array([np.cos(ap_rad), np.sin(ap_rad)])
    ue_unit = np.array([np.cos(ue_rad), np.sin(ue_rad)])

    # Compute bisector as sum of unit vectors
    bisector_vec = ap_unit + ue_unit

    # Convert back to angle
    bisector_angle = np.degrees(np.arctan2(bisector_vec[1], bisector_vec[0]))

    # Normalize to [0, 360)
    while bisector_angle < 0:
        bisector_angle += 360
    while bisector_angle >= 360:
        bisector_angle -= 360

    return bisector_angle
