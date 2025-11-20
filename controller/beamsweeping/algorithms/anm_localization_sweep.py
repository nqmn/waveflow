"""Atomic Norm Minimization (ANM) Localization Sweep.

Adds a localization-oriented sweep that:
- Runs a coarse sweep to collect SNR vs angle.
- Computes a curvature metric to classify far-/near-field.
- Solves a sparse recovery problem (cvxpy) using RIS geometry
  to estimate direction (far) or location (near, separable heuristic).
- Returns a structured result matching the ANM doc interface.
"""

from __future__ import annotations

import time
from typing import Dict, Tuple, Optional

import numpy as np
import cvxpy as cp

from ..base import SweepAlgorithmBase
from ..common import (
    clamp_local_deflection_to_ris_fov,
    clamp_offset_to_fov,
    compute_offset_from_normal,
    generate_codebook,
    validate_and_get_nodes,
    compute_optimal_ris_normal,
)
from ..registry import register_algorithm
from controller.ris_phase.phase_hybrid import HybridPhaseEngine
from core.physics import C


def _compute_curvature_metric(values: np.ndarray) -> float:
    """Second-order difference curvature metric normalized to signal scale."""
    if values.size < 3:
        return 0.0

    finite = np.nan_to_num(values, nan=np.nanmean(values) if not np.isnan(np.nanmean(values)) else 0.0)
    norm = np.max(np.abs(finite))
    norm = norm if norm > 1e-9 else 1.0

    second_diff = np.diff(finite, n=2)
    curvature = float(np.mean(np.abs(second_diff)) / norm)
    return curvature


def _build_plane_steering(rel_positions: np.ndarray, angles_rad: np.ndarray, wavelength: float) -> np.ndarray:
    """Construct plane-wave steering matrix using RIS geometry."""
    k = 2 * np.pi / wavelength
    x_rel = rel_positions[:, 0]
    y_rel = rel_positions[:, 1]
    design = []
    for theta in angles_rad:
        u_x = np.cos(theta)
        u_y = np.sin(theta)
        phase = -k * (x_rel * u_x + y_rel * u_y)
        design.append(np.exp(1j * phase))
    return np.array(design, dtype=np.complex128)


def _solve_sparse_recovery(design: np.ndarray, y: np.ndarray, lambda_reg: float) -> Tuple[Optional[np.ndarray], str, float]:
    """L1-regularized least squares via CVXPY; returns (weights, status, solve_time)."""
    if design.shape[0] == 0 or design.shape[1] == 0:
        return None, "empty_design", 0.0

    Phi = cp.Constant(design)
    x = cp.Variable(design.shape[1], complex=True)

    objective = cp.Minimize(lambda_reg * cp.norm1(x) + 0.5 * cp.sum_squares(Phi @ x - y))
    prob = cp.Problem(objective)

    start = time.time()
    try:
        prob.solve(solver=cp.SCS, verbose=False)
    except Exception:
        prob.solve(verbose=False)
    solve_time = time.time() - start

    return x.value, prob.status, solve_time


@register_algorithm("anm", aliases=("anm-localization", "atomic-norm"))
class ANMLocalizationSweep(SweepAlgorithmBase):
    """ANM-driven localization sweep leveraging existing hybrid phase engine."""

    @property
    def name(self) -> str:
        return "ANM Localization Sweep"

    @property
    def description(self) -> str:
        return "Atomic norm-inspired localization with near/far classification and RIS geometry steering."

    def sweep(
        self,
        ap_name: str,
        ris_name: str,
        ue_name: str,
        fov: float = 120.0,
        step: float = 2.0,
        curvature_threshold: float = 0.1,
        K_est: int = 1,
        lambda_reg: float = 0.1,
        seed: int = 42,
        enable_nearfield: bool = False,
        **kwargs,
    ) -> Dict:
        """Run ANM localization sweep.

        Args:
            ap_name: AP node name
            ris_name: RIS node name
            ue_name: UE node name
            fov: Field of view in degrees
            step: Angular resolution in degrees
            curvature_threshold: Threshold for near/far classification
            K_est: Estimated number of paths (kept for API completeness)
            lambda_reg: Regularization for ANM/L1 solver
            seed: Random seed forwarded to per-measurement connect calls
            enable_nearfield: If True, attempt near-field branch; otherwise force far-field output
        """
        ap, ris, ue = validate_and_get_nodes(self.network, ap_name, ris_name, ue_name)

        wavelength = C / ris.freq
        fraunhofer_boundary = HybridPhaseEngine.fraunhofer_boundary(ris.N, ris.spacing, wavelength)
        dist_ap_ris = float(np.linalg.norm(ap.pos - ris.pos))
        dist_ris_ue = float(np.linalg.norm(ue.pos - ris.pos))

        # Geometry setup
        ap_vec = ap.pos - ris.pos
        ue_vec = ue.pos - ris.pos
        ap_angle = np.degrees(np.arctan2(ap_vec[1], ap_vec[0]))
        ue_angle = np.degrees(np.arctan2(ue_vec[1], ue_vec[0]))
        ris_normal = compute_optimal_ris_normal(ap_angle, ue_angle)

        local_angles, num_angles = generate_codebook(fov, step)
        ris_max_angle = getattr(ris, "max_angle_deg", 60.0)
        clamped_local = clamp_local_deflection_to_ris_fov(local_angles, ris_max_angle)
        abs_angles = ap_angle + clamped_local  # convert local deflection to absolute boresight angles

        snr_values = np.full(num_angles, np.nan, dtype=float)
        pwr_values = np.full(num_angles, np.nan, dtype=float)

        tapering = kwargs.get("tapering", "uniform")

        # Measurement loop
        for idx, abs_angle in enumerate(abs_angles):
            with self._ap_state_guard(ap):
                res = self.network.connect(
                    ap_name,
                    ris_name,
                    ue_name,
                    beam_angle_deg=float(abs_angle),
                    seed=seed + idx if seed is not None else None,
                    enable_feedback=False,
                    max_feedback_iterations=1,
                    store_in_active_links=False,
                    use_get_snr=self._should_use_get_snr(),
                    tapering=tapering,
                    fixed_ris_normal=ris_normal,
                )

            snr_values[idx] = res.get("snr_dB", np.nan)
            pwr_values[idx] = res.get("pwr_dBm", np.nan)

        # Handle empty/invalid sweeps gracefully
        finite_mask = np.isfinite(snr_values)
        if not np.any(finite_mask):
            return {
                "mode": "unknown",
                "location": {},
                "confidence": 0.0,
                "curvature": 0.0,
                "curvature_threshold": curvature_threshold,
                "measurements": {
                    "angles_tested": abs_angles.tolist(),
                    "snr_values": snr_values.tolist(),
                    "num_measurements": int(num_angles),
                    "best_angle": None,
                    "best_snr_dB": None,
                },
                "metadata": {
                    "algorithm": "ANMLocalizationSweep",
                    "solver_status": "no_measurements",
                },
            }

        best_idx = int(np.nanargmax(snr_values))
        best_abs_angle = float(abs_angles[best_idx])
        best_local_angle = float(clamped_local[best_idx])
        best_snr = float(snr_values[best_idx])

        curvature = _compute_curvature_metric(snr_values)
        prelim_mode = "near-field" if (curvature > curvature_threshold) else "far-field"
        mode = prelim_mode if enable_nearfield else "far-field"
        confidence = self._compute_confidence(curvature, curvature_threshold, mode)

        angles_rad = np.radians(abs_angles)
        rel_positions = ris.element_positions - ris.pos
        y_vector = 10 ** (snr_values / 20.0)
        y_vector = np.nan_to_num(y_vector, nan=0.0).astype(np.complex128)

        solver_status = "not_run"
        solver_time = 0.0
        atomic_norm_value = None
        steering_angles = None
        separable_estimates = None
        mode_note = None
        recommended_source = "sweep_peak"
        recommended_local_angle = best_local_angle
        recommended_abs_angle = best_abs_angle
        anm_est_az_deg = None

        if not enable_nearfield and prelim_mode == "near-field":
            mode_note = "Near-field classification suppressed; forcing far-field output."

        if mode == "far-field":
            design = _build_plane_steering(rel_positions, angles_rad, wavelength)
            weights, solver_status, solver_time = _solve_sparse_recovery(design, y_vector, lambda_reg)
            if weights is not None:
                predicted = design @ weights
                est_idx = int(np.argmax(np.abs(predicted)))
                est_theta = float(angles_rad[est_idx])
                steering_angles = {"azimuth_rad": est_theta, "elevation_rad": 0.0}
                atomic_norm_value = float(np.sum(np.abs(weights)))
                # Map ANM azimuth to local deflection relative to RIS normal
                est_az_deg = np.degrees(est_theta)
                anm_est_az_deg = est_az_deg
                ris_max_angle = getattr(ris, "max_angle_deg", 60.0)
                offset = compute_offset_from_normal(est_az_deg, ris_normal)
                offset = clamp_offset_to_fov(offset, ris_max_angle)
                recommended_local_angle = float(offset)
                recommended_abs_angle = float(ris_normal + offset)
                recommended_source = "anm_estimate"
            else:
                steering_angles = {"azimuth_rad": np.radians(best_abs_angle), "elevation_rad": 0.0}
        else:
            # Near-field 3D solver not implemented with scalar SNR measurements.
            solver_status = "skipped_nearfield_not_implemented"
            separable_estimates = None

        location = self._build_location_output(mode, recommended_abs_angle, ris, ue)

        return {
            "mode": mode,
            "location": location,
            "confidence": confidence,
            "curvature": curvature,
            "curvature_threshold": curvature_threshold,
            # Legacy keys for CLI sweep printer
            "algo_object": self,
            "suppress_tables": True,
            "local_coarse": clamped_local.tolist(),
            "snr_coarse": snr_values.tolist(),
            "pwr_coarse": pwr_values.tolist(),
            "specular_angle": ap_angle,
            "best_angle": recommended_local_angle,
            "measurements": {
                "angles_tested": abs_angles.tolist(),
                "snr_values": snr_values.tolist(),
                "num_measurements": int(num_angles),
                "best_angle": recommended_abs_angle,
                "best_snr_dB": best_snr,
            },
            "metadata": {
                "algorithm": "ANMLocalizationSweep",
                "K_est": int(K_est),
                "lambda_reg": float(lambda_reg),
                "fraunhofer_boundary_m": float(fraunhofer_boundary),
                "dist_ap_to_ris_m": dist_ap_ris,
                "dist_ris_to_ue_m": dist_ris_ue,
                "steering_angles": steering_angles,
                "separable_estimates": separable_estimates,
                "solver_status": solver_status,
                "solver_time_sec": solver_time,
                "atomic_norm_value": atomic_norm_value,
                "nearfield_position_estimated": False if mode == "near-field" else True,
                "nearfield_enabled": bool(enable_nearfield),
                "mode_note": mode_note,
                "mode_decision": prelim_mode,
                "angle_recommendation_source": recommended_source,
                "original_best_angle_local": best_local_angle,
                "original_best_angle_abs": best_abs_angle,
                "recommended_local_angle": recommended_local_angle,
                "recommended_abs_angle": recommended_abs_angle,
                "anm_estimated_az_deg": anm_est_az_deg,
                "angles_tested_count": int(num_angles),
                "ap_angle_deg": ap_angle,
                "ue_angle_deg": ue_angle,
                "ris_normal_deg": ris_normal,
                "fov_deg": fov,
                "step_deg": step,
            },
        }

    @staticmethod
    def _build_location_output(mode: str, best_angle: float, ris, ue) -> Dict:
        """Create location dictionary depending on classification."""
        if mode == "far-field":
            return {
                "azimuth": best_angle,
                "type": "direction-only",
            }

        # Near-field position estimation requires richer measurements; return direction-only placeholder.
        return {
            "azimuth": best_angle,
            "type": "direction-only",
            "note": "Near-field 3D position estimation not implemented; provides direction only.",
        }

    @staticmethod
    def _compute_confidence(curvature: float, threshold: float, mode: str) -> float:
        """Map curvature to a 0-1 confidence score."""
        eps = 1e-6
        if mode == "far-field":
            return max(0.0, min(1.0, 1.0 - curvature / (threshold + eps)))
        return max(0.0, min(1.0, curvature / (curvature + threshold + eps)))
