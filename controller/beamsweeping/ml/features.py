"""Canonical feature definitions shared by ML training and inference.

Training scripts and predictor inference MUST build features from this module
so the two sides can never drift apart.

The set includes UE-side geometry (position, d_ris_ue, AoD). Every predictor
receives the UE node at inference time and already derives snr_dB/rssi_dBm
from ue.pos, so this information is legitimately available. Without the AoD
terms the deflection target |aod - aoa| is provably unlearnable: the only
UE-dependent signals left (snr/rssi) encode distance, not azimuth, and
retraining under that regime yields test R^2 <= 0 for every model family.

Historical note: earlier training scripts also used az_*/ap_az_*/ap_el_*/
spec_*/align_* columns. Those were exact duplicates or constants by
construction (the AP->RIS azimuth is anti-parallel to the RIS->AP AoA, which
makes align_cos = -1 and align_sin = 0 always, and reduces spec_* to copies of
aoa_*), so they were removed from the canonical set.
"""

from __future__ import annotations

import math
from typing import Dict, List

import numpy as np

from utils.lightris import build_lightris_config_from_nodes, evaluate_lightris_metrics

# Canonical sklearn feature columns, in training/inference order.
SKLEARN_FEATURE_COLUMNS: List[str] = [
    'ap_x', 'ap_y', 'ap_z',
    'ris_x', 'ris_y', 'ris_z',
    'ue_x', 'ue_y', 'ue_z',
    'd_ap_ris', 'd_ris_ue',
    'aoa_sin', 'aoa_cos',
    'aod_sin', 'aod_cos',
    'el_sin', 'el_cos',
    'dx', 'dy', 'dz',
    'snr_dB', 'rssi_dBm',
]

# Regression target: unsigned deflection from the incident direction,
# |aod - aoa| wrapped to [0, 180] degrees.
LABEL_COLUMN = 'best_angle'


def geometry_features(ap_pos: np.ndarray, ris_pos: np.ndarray, ue_pos: np.ndarray) -> Dict[str, float]:
    """Compute the geometry-derived feature values.

    dx/dy/dz are the AP->RIS offset (ris - ap); elevation is the AP->RIS
    elevation angle; aoa is the RIS->AP azimuth; aod is the RIS->UE azimuth.
    """
    d_ap_ris = float(np.linalg.norm(np.asarray(ap_pos) - np.asarray(ris_pos)))
    d_ris_ue = float(np.linalg.norm(np.asarray(ue_pos) - np.asarray(ris_pos)))

    aoa_rad = math.atan2(ap_pos[1] - ris_pos[1], ap_pos[0] - ris_pos[0])
    aod_rad = math.atan2(ue_pos[1] - ris_pos[1], ue_pos[0] - ris_pos[0])

    dx = float(ris_pos[0] - ap_pos[0])
    dy = float(ris_pos[1] - ap_pos[1])
    dz = float(ris_pos[2] - ap_pos[2])
    el_rad = math.atan2(dz, math.hypot(dx, dy))

    return {
        'd_ap_ris': d_ap_ris,
        'd_ris_ue': d_ris_ue,
        'aoa_sin': float(math.sin(aoa_rad)),
        'aoa_cos': float(math.cos(aoa_rad)),
        'aod_sin': float(math.sin(aod_rad)),
        'aod_cos': float(math.cos(aod_rad)),
        'el_sin': float(math.sin(el_rad)),
        'el_cos': float(math.cos(el_rad)),
        'dx': dx,
        'dy': dy,
        'dz': dz,
    }


def link_metrics_from_nodes(ap, ris, ue) -> Dict[str, float]:
    """Compute snr_dB/rssi_dBm exactly as the dataset builder does.

    Beam angle is the RIS->UE azimuth (perfect steering), so the metrics carry
    distance information without steering-mismatch loss.
    """
    ap_pos = np.asarray(ap.pos, dtype=float)
    ris_pos = np.asarray(ris.pos, dtype=float)
    ue_pos = np.asarray(ue.pos, dtype=float)

    aod_deg = float(np.degrees(math.atan2(ue_pos[1] - ris_pos[1], ue_pos[0] - ris_pos[0]))) % 360
    physics_config = build_lightris_config_from_nodes(ap, ris, ue)
    metrics = evaluate_lightris_metrics(ap_pos, ris_pos, ue_pos, aod_deg, physics_config)
    return {'snr_dB': float(metrics['snr_dB']), 'rssi_dBm': float(metrics['rssi_dBm'])}


def build_sklearn_features(ap, ris, ue) -> List[float]:
    """Build the canonical inference feature vector from network nodes.

    Returns values in SKLEARN_FEATURE_COLUMNS order.
    """
    ap_pos = np.asarray(ap.pos, dtype=float)
    ris_pos = np.asarray(ris.pos, dtype=float)
    ue_pos = np.asarray(ue.pos, dtype=float)

    values = {
        'ap_x': float(ap_pos[0]), 'ap_y': float(ap_pos[1]), 'ap_z': float(ap_pos[2]),
        'ris_x': float(ris_pos[0]), 'ris_y': float(ris_pos[1]), 'ris_z': float(ris_pos[2]),
        'ue_x': float(ue_pos[0]), 'ue_y': float(ue_pos[1]), 'ue_z': float(ue_pos[2]),
    }
    values.update(geometry_features(ap_pos, ris_pos, ue_pos))
    values.update(link_metrics_from_nodes(ap, ris, ue))

    return [values[col] for col in SKLEARN_FEATURE_COLUMNS]
