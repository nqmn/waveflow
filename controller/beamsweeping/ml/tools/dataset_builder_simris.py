"""Generate ML training data with SimRIS-measured best-beam labels.

Unlike dataset_builder.py, whose label is the pure geometric deflection
|aod - aoa|, this builder labels each topology with the deflection of the
MEASURED-BEST beam under the SimRIS stochastic channel (3GPP-style indoor
path loss, LOS blocking probability, tx-side scatterer clusters, shadow
fading). When the channel is LOS-dominated the two labels agree; when
multipath or blocking dominates they differ - which is exactly the regime
where a learned predictor can beat the geometric formula.

Feature columns are identical to dataset_builder.py (positions, geometry
trig, and the LightRIS-computed snr_dB/rssi_dBm), so the shared inference
builder in ml/features.py and every training script work unchanged; only
the label source differs. Extra diagnostic columns are appended after
best_angle and are ignored by the training scripts:
  - geo_angle:     SIGNED geometric deflection wrap(aod - aoa) (degrees)
  - oracle_gain_dB: channel gain of the measured-best beam
  - geo_gain_dB:    channel gain when steering at the geometric aim

Beam measurement model: with SimRIS channels H (AP->RIS) and G (RIS->UE)
and per-element phases theta_n, the effective SISO channel is
    e(phi) = sum_n G_n * exp(j*theta_n) * H_n
Steering toward candidate azimuth phi uses theta_n = -arg(H_n) - arg(a_n(phi)),
i.e. compensate the measured incident channel phase and add the departure
steering profile, giving e(phi) = sum_n |H_n| * G_n * conj(a_n(phi)).
The label is the (unsigned) deflection of argmax_phi |e(phi)| from the
incident azimuth. The direct path is excluded (classic blocked-direct RIS
use case) so the label reflects the RIS beam alone.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import random
import sys
import time
from pathlib import Path

import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..', '..'))
sys.path.insert(0, project_root)

from risnet.channels.simris import (
    simulate_simris_channels,
    _angles_ris_rx_los,
    _wavelength_m,
)
from controller.beamsweeping.ml.tools.dataset_builder import (
    FIELDNAMES as BASE_FIELDNAMES,
    compute_angles,
    compute_distances,
    compute_theta_rcv,
    random_position,
    _add_angle_trigs,
    _add_ap_ris_orientation,
    _add_physics_metrics,
    _add_probe_metrics,
    flatten_sample,
)
from utils.lightris import build_lightris_config
from controller.beamsweeping.ml.features import PROBE_DEFLECTIONS_DEG

FIELDNAMES = BASE_FIELDNAMES + ['geo_angle', 'oracle_gain_dB', 'geo_gain_dB']


def scan_beam_gains(ris_pos: np.ndarray, ue_pos: np.ndarray, H: np.ndarray, G: np.ndarray,
                    ris_side: int, frequency_GHz: float, scenario: int,
                    phi_grid: np.ndarray) -> np.ndarray:
    """Return |e(phi)| in dB for every candidate world azimuth in phi_grid."""
    wavelength = _wavelength_m(frequency_GHz)
    k = 2.0 * np.pi / wavelength
    spacing = wavelength / 2.0
    d_ue = float(np.linalg.norm(ue_pos - ris_pos))

    x_idx = np.repeat(np.arange(ris_side), ris_side).astype(float)
    y_idx = np.tile(np.arange(ris_side), ris_side).astype(float)

    # Steering with theta_n = -arg(H_n) - arg(a_n(phi)) leaves |H_n|*G_n*conj(a_n)
    w = np.abs(H) * G

    a_coef = np.empty(len(phi_grid))
    b_coef = np.empty(len(phi_grid))
    for i, phi in enumerate(phi_grid):
        virt = ris_pos + d_ue * np.array([math.cos(math.radians(phi)),
                                          math.sin(math.radians(phi)), 0.0])
        virt[2] = ue_pos[2]
        phi_ris, theta_ris, _, _ = _angles_ris_rx_los(ris_pos, virt, scenario)
        a_coef[i] = math.sin(math.radians(theta_ris))
        b_coef[i] = math.sin(math.radians(phi_ris)) * math.cos(math.radians(theta_ris))

    # a_n(phi) = exp(j*k*s*(x_idx*sin(theta) + y_idx*sin(phi)*cos(theta)))
    phases = k * spacing * (np.outer(a_coef, x_idx) + np.outer(b_coef, y_idx))
    A = np.exp(1j * phases)
    e = A.conj() @ w
    return 20.0 * np.log10(np.abs(e) + 1e-30)


def probe_beam_gains(ris_pos: np.ndarray, ue_pos: np.ndarray, H: np.ndarray, G: np.ndarray,
                     ris_side: int, frequency_GHz: float, scenario: int,
                     probe_phis: np.ndarray, subarray_side: int = 4) -> np.ndarray:
    """Measure probe beams with a WIDE beam formed by a subarray.

    A full 16x16 panel has a ~6 deg beamwidth, so a handful of probes spaced
    tens of degrees apart would only ever measure sidelobe noise. Real beam
    management probes with wide beams instead; here the probe uses only the
    top-left subarray (subarray_side x subarray_side), giving a ~25 deg
    beamwidth for 4x4, so 8 probes cover the whole azimuth informatively.
    """
    wavelength = _wavelength_m(frequency_GHz)
    k = 2.0 * np.pi / wavelength
    spacing = wavelength / 2.0
    d_ue = float(np.linalg.norm(ue_pos - ris_pos))

    x_idx = np.repeat(np.arange(ris_side), ris_side).astype(float)
    y_idx = np.tile(np.arange(ris_side), ris_side).astype(float)
    mask = (x_idx < subarray_side) & (y_idx < subarray_side)

    w = (np.abs(H) * G)[mask]
    xs, ys = x_idx[mask], y_idx[mask]

    a_coef = np.empty(len(probe_phis))
    b_coef = np.empty(len(probe_phis))
    for i, phi in enumerate(probe_phis):
        virt = ris_pos + d_ue * np.array([math.cos(math.radians(phi)),
                                          math.sin(math.radians(phi)), 0.0])
        virt[2] = ue_pos[2]
        phi_ris, theta_ris, _, _ = _angles_ris_rx_los(ris_pos, virt, scenario)
        a_coef[i] = math.sin(math.radians(theta_ris))
        b_coef[i] = math.sin(math.radians(phi_ris)) * math.cos(math.radians(theta_ris))

    phases = k * spacing * (np.outer(a_coef, xs) + np.outer(b_coef, ys))
    e = np.exp(1j * phases).conj() @ w
    return 20.0 * np.log10(np.abs(e) + 1e-30)


def build_simris_sample(bounds, physics_config, ris_side, frequency_GHz, scenario,
                        channel_seed, phi_grid, max_deflection):
    """Sample one topology and label it with the SimRIS measured-best beam."""
    for _ in range(200):
        ap_pos = random_position(bounds['ap'])
        ris_pos = random_position(bounds['ris'])
        ue_pos = random_position(bounds['ue'])
        if compute_theta_rcv(ap_pos, ris_pos, ue_pos) <= max_deflection:
            break

    res = simulate_simris_channels(
        tx_xyz=ap_pos, ris_xyz=ris_pos, rx_xyz=ue_pos,
        ris_side=ris_side, frequency_GHz=frequency_GHz,
        environment='indoor', scenario=scenario,
        num_realizations=1, seed=channel_seed,
        include_direct_path=False,
    )
    H = res['H'][:, 0, 0]
    G = res['G'][0, :, 0]

    gains = scan_beam_gains(ris_pos, ue_pos, H, G, ris_side, frequency_GHz, scenario, phi_grid)

    aoa, aod = compute_angles(ap_pos, ris_pos, ue_pos)
    geo_deflection = compute_theta_rcv(ap_pos, ris_pos, ue_pos)
    geo_signed = (aod - aoa + 180.0) % 360.0 - 180.0

    # The UPA response is mirror-ambiguous: two azimuths can achieve identical
    # gain. Among angles within 0.5 dB of the measured max (physically
    # equivalent beams), label with the one closest to the geometric aim so the
    # regression target stays unimodal; residual deviations then reflect real
    # channel physics (scatterers, blocking), not parameterization artifacts.
    # The label is SIGNED (UE-blind predictors must recover the sign).
    near_max = np.flatnonzero(gains >= float(np.max(gains)) - 0.5)
    signed_cands = (phi_grid[near_max] - aoa + 180.0) % 360.0 - 180.0
    pick = int(np.argmin(np.abs((signed_cands - geo_signed + 180.0) % 360.0 - 180.0)))
    best_deflection = float(signed_cands[pick])
    geo_gain = float(gains[int(np.argmin(np.abs((phi_grid - aod + 180.0) % 360.0 - 180.0)))])

    d_ap_ris, d_ris_ue = compute_distances(ap_pos, ris_pos, ue_pos)
    sample = {
        'ap_pos': ap_pos.tolist(),
        'ris_pos': ris_pos.tolist(),
        'ue_pos': ue_pos.tolist(),
        'd_ap_ris': d_ap_ris,
        'd_ris_ue': d_ris_ue,
        'aoa': aoa,
        'aod': aod,
        'best_angle': float(best_deflection),
    }
    _add_angle_trigs(sample, aoa, aod)
    _add_ap_ris_orientation(sample)
    _add_physics_metrics(sample, physics_config)
    _add_probe_metrics(sample, physics_config)
    row = flatten_sample(sample)

    # Replace the LightRIS-simulated probe feedback with MEASURED wide-beam
    # probes from the SimRIS channel (4x4 subarray, ~25 deg beamwidth),
    # converted to the SNR scale used by the budget:
    # tx 20 dBm + 6 dBi antennas - (-94.99 dBm) noise floor.
    snr_offset = 20.0 + 6.0 + 94.99
    probe_phis = np.array([(aoa + d + 180.0) % 360.0 - 180.0 for d in PROBE_DEFLECTIONS_DEG])
    probe_gains = probe_beam_gains(ris_pos, ue_pos, H, G, ris_side, frequency_GHz,
                                   scenario, probe_phis)
    for i in range(len(PROBE_DEFLECTIONS_DEG)):
        row[f'probe_snr_{i}'] = float(probe_gains[i] + snr_offset)

    row['geo_angle'] = float(geo_signed)
    row['oracle_gain_dB'] = float(np.max(gains))
    row['geo_gain_dB'] = geo_gain
    return row


def main():
    parser = argparse.ArgumentParser(description="Generate SimRIS-labelled beam dataset")
    parser.add_argument('--samples', type=int, default=6000)
    parser.add_argument('--output', type=Path,
                        default=Path('controller/beamsweeping/ml/data/beam_dataset_simris.csv'))
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--ris-elements', type=int, default=16, help='Elements per side')
    parser.add_argument('--frequency', type=float, default=5.8, help='GHz')
    parser.add_argument('--scenario', type=int, default=1)
    parser.add_argument('--scan-step', type=float, default=1.0, help='Azimuth scan step (deg)')
    parser.add_argument('--max-deflection', type=float, default=180.0)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    # SimRIS indoor assumes a 75 x 50 x 3.5 m room; keep nodes inside it
    # (z above 3.5 m breaks scatterer generation).
    bounds = {
        'ap':  {'x_min': 0, 'x_max': 20, 'y_min': 0, 'y_max': 20, 'z_min': 0.5, 'z_max': 3.0},
        'ris': {'x_min': 0, 'x_max': 20, 'y_min': 0, 'y_max': 20, 'z_min': 0.5, 'z_max': 3.0},
        'ue':  {'x_min': 0, 'x_max': 20, 'y_min': 0, 'y_max': 20, 'z_min': 0.5, 'z_max': 3.0},
    }
    physics_config = build_lightris_config({
        'tx_power_dBm': 20.0, 'ap_antenna_gain_dBi': 3.0, 'ue_antenna_gain_dBi': 3.0,
        'bandwidth_mhz': 20.0, 'phase_bits': 2, 'element_efficiency': 0.95,
        'frequency_ghz': args.frequency, 'ris_elements_per_side': args.ris_elements,
    })
    phi_grid = np.arange(-180.0, 180.0, args.scan_step)

    start = time.time()
    rows = []
    for i in range(args.samples):
        rows.append(build_simris_sample(
            bounds, physics_config, args.ris_elements, args.frequency,
            args.scenario, channel_seed=args.seed * 1_000_003 + i,
            phi_grid=phi_grid, max_deflection=args.max_deflection,
        ))
        if (i + 1) % 500 == 0:
            print(f"Generated {i + 1}/{args.samples} samples...")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    label = np.array([r['best_angle'] for r in rows])
    geo = np.array([r['geo_angle'] for r in rows])
    # both signed: compare with wrap
    label, geo = (label - geo + 180) % 360 - 180 + geo, geo
    gap = np.array([r['oracle_gain_dB'] - r['geo_gain_dB'] for r in rows])
    print(f"Wrote {len(rows)} samples to {args.output} in {time.time()-start:.1f}s")
    print(f"label vs geometric deflection: MAE {np.abs(label-geo).mean():.2f} deg, "
          f"median {np.median(np.abs(label-geo)):.2f} deg")
    print(f"SNR left on table by geometric aim: mean {gap.mean():.2f} dB, p90 {np.percentile(gap, 90):.2f} dB")


if __name__ == "__main__":
    main()
