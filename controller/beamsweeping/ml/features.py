"""Canonical feature definitions shared by ML training and inference.

Training scripts and predictor inference MUST build features from this module
so the two sides can never drift apart.

DESIGN: the predictor is UE-blind. In the real world the RIS does not know
the UE position - that is why a predictor is needed at all. The feature set
therefore contains NO UE-derived geometry. Instead it contains what a real
deployment can actually measure: SNR feedback reported by the UE for a small
set of coarse PROBE BEAMS fired at fixed signed deflections from the incident
(AP) direction. Probe SNRs are azimuth-informative (the profile peaks around
the true departure direction), so the best-beam angle becomes learnable
without ever reading ue.pos. AP/RIS geometry is included since both are fixed
infrastructure with known positions.

The regression target 'best_angle' is the SIGNED deflection from the incident
direction, wrapped to (-180, 180]. (It was unsigned before the probe-based
redesign; a UE-blind predictor cannot recover the sign from geometry, so the
sign must be predicted - the probe profile provides it.)

Historical note: earlier feature sets included snr_dB/rssi_dBm computed at the
perfectly steered beam. That is circular (measuring it requires already
knowing the answer) and carries no azimuth information, which made the target
provably unlearnable (test R^2 <= 0 for every model family). Those columns
remain in the dataset CSVs as diagnostics only.
"""

from __future__ import annotations

import math
from typing import Dict, List, Sequence

import numpy as np

from utils.lightris import build_lightris_config_from_nodes, evaluate_lightris_metrics

# Signed probe-beam deflections (degrees) relative to the incident azimuth.
# 8 beams spanning the full reachable range; 180 covers the -180 wrap.
PROBE_DEFLECTIONS_DEG: List[float] = [-135.0, -90.0, -45.0, 0.0, 45.0, 90.0, 135.0, 180.0]

PROBE_COLUMNS: List[str] = [f'probe_snr_{i}' for i in range(len(PROBE_DEFLECTIONS_DEG))]

# Canonical sklearn feature columns, in training/inference order.
# AP/RIS geometry (known infrastructure) + measured probe feedback. No UE terms.
SKLEARN_FEATURE_COLUMNS: List[str] = [
    'ap_x', 'ap_y', 'ap_z',
    'ris_x', 'ris_y', 'ris_z',
    'd_ap_ris',
    'aoa_sin', 'aoa_cos',
    'el_sin', 'el_cos',
    'dx', 'dy', 'dz',
] + PROBE_COLUMNS

# Regression target: SIGNED deflection from the incident direction, (-180, 180].
LABEL_COLUMN = 'best_angle'


def geometry_features(ap_pos: np.ndarray, ris_pos: np.ndarray) -> Dict[str, float]:
    """Compute the AP/RIS geometry-derived feature values (no UE terms).

    dx/dy/dz are the AP->RIS offset (ris - ap); elevation is the AP->RIS
    elevation angle; aoa is the RIS->AP azimuth.
    """
    d_ap_ris = float(np.linalg.norm(np.asarray(ap_pos) - np.asarray(ris_pos)))

    aoa_rad = math.atan2(ap_pos[1] - ris_pos[1], ap_pos[0] - ris_pos[0])

    dx = float(ris_pos[0] - ap_pos[0])
    dy = float(ris_pos[1] - ap_pos[1])
    dz = float(ris_pos[2] - ap_pos[2])
    el_rad = math.atan2(dz, math.hypot(dx, dy))

    return {
        'd_ap_ris': d_ap_ris,
        'aoa_sin': float(math.sin(aoa_rad)),
        'aoa_cos': float(math.cos(aoa_rad)),
        'el_sin': float(math.sin(el_rad)),
        'el_cos': float(math.cos(el_rad)),
        'dx': dx,
        'dy': dy,
        'dz': dz,
    }


def probe_snrs_lightris(ap_pos: np.ndarray, ris_pos: np.ndarray, ue_pos: np.ndarray,
                        physics_config: Dict[str, float],
                        deflections: Sequence[float] = PROBE_DEFLECTIONS_DEG) -> List[float]:
    """Simulate the UE's SNR feedback for each probe beam (LightRIS engine).

    The probe beam is fired at incident_azimuth + deflection; the SNR the UE
    would report is evaluated with the analytical engine. ue_pos is used ONLY
    to simulate what the real measurement would return - it never becomes a
    feature. Real deployments replace this with actual UE feedback.
    """
    ap_pos = np.asarray(ap_pos, dtype=float)
    ris_pos = np.asarray(ris_pos, dtype=float)
    ue_pos = np.asarray(ue_pos, dtype=float)

    aoa_deg = math.degrees(math.atan2(ap_pos[1] - ris_pos[1], ap_pos[0] - ris_pos[0]))
    snrs = []
    for defl in deflections:
        beam_deg = (aoa_deg + defl) % 360.0
        metrics = evaluate_lightris_metrics(ap_pos, ris_pos, ue_pos, beam_deg, physics_config)
        snrs.append(float(metrics['snr_dB']))
    return snrs


def assemble_features(ap_pos: np.ndarray, ris_pos: np.ndarray,
                      probe_snrs: Sequence[float]) -> List[float]:
    """Assemble the canonical feature vector from geometry + measured probes.

    Returns values in SKLEARN_FEATURE_COLUMNS order. Use this everywhere a
    feature vector is built so ordering can never drift.
    """
    if len(probe_snrs) != len(PROBE_DEFLECTIONS_DEG):
        raise ValueError(
            f"expected {len(PROBE_DEFLECTIONS_DEG)} probe SNRs, got {len(probe_snrs)}")

    ap_pos = np.asarray(ap_pos, dtype=float)
    ris_pos = np.asarray(ris_pos, dtype=float)

    values = {
        'ap_x': float(ap_pos[0]), 'ap_y': float(ap_pos[1]), 'ap_z': float(ap_pos[2]),
        'ris_x': float(ris_pos[0]), 'ris_y': float(ris_pos[1]), 'ris_z': float(ris_pos[2]),
    }
    values.update(geometry_features(ap_pos, ris_pos))
    for col, snr in zip(PROBE_COLUMNS, probe_snrs):
        values[col] = float(snr)

    return [values[col] for col in SKLEARN_FEATURE_COLUMNS]


def build_sklearn_features(ap, ris, ue) -> List[float]:
    """Build the canonical inference feature vector from network nodes.

    The UE node is used only to SIMULATE the probe-beam SNR feedback a real
    UE would report; no UE geometry enters the feature vector.
    """
    ap_pos = np.asarray(ap.pos, dtype=float)
    ris_pos = np.asarray(ris.pos, dtype=float)
    ue_pos = np.asarray(ue.pos, dtype=float)

    physics_config = build_lightris_config_from_nodes(ap, ris, ue)
    probes = probe_snrs_lightris(ap_pos, ris_pos, ue_pos, physics_config)
    return assemble_features(ap_pos, ris_pos, probes)
