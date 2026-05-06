"""Power-based RIS Inference for Multi-Angle Estimation (PRIME).

Adds a localization-oriented sweep that:
- Runs a coarse sweep to collect power/SNR vs angle.
- Computes a curvature metric to classify far-/near-field.
- Employs hybrid magnitude-only estimator (centroid + model fitting).
- Solves sparse recovery problem (cvxpy) for complex CSI when available.
- Returns a structured result matching the ANM/PRIME interface.
"""

from __future__ import annotations

import logging
import time
import math
from typing import Dict, Tuple, Optional

import numpy as np

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

logger = logging.getLogger(__name__)

try:
    from scipy.optimize import minimize
    _HAS_SCIPY = True
except Exception:
    _HAS_SCIPY = False

try:
    from scipy import stats as _scipy_stats
except Exception:
    _scipy_stats = None



def _wrap180_deg(x: float) -> float:
    """Wrap angle to [-180, 180] degrees."""
    return ((x + 180.0) % 360.0) - 180.0


def _snr_db_to_linear(snr_db):
    """Convert SNR from dB to linear scale."""
    return 10.0 ** (np.array(snr_db, dtype=float) / 10.0)


def _rssi_dbm_to_mw(rssi_dbm):
    """Convert RSSI from dBm to mW."""
    return 10.0 ** ((np.array(rssi_dbm, dtype=float) - 30.0) / 10.0)


def _centroid_angle_deg(codebook_angles_deg, power_linear):
    """Find angle at center of high-power region (robust to multi-modal distributions).

    Reverts to a peak-region selection: identify the top quartile of powers,
    then return the strongest angle inside that ROI. This keeps the centroid
    aligned with the actual measured peak instead of averaging across bins.
    """
    p = np.array(power_linear, dtype=float)
    codebook = np.array(codebook_angles_deg, dtype=float)

    if np.sum(p) == 0:
        return float(codebook[int(np.argmax(p))])

    threshold = np.percentile(p, 75)
    mask = p >= (threshold - 1e-9)
    if not np.any(mask):
        return float(codebook[int(np.argmax(p))])

    roi_angles = codebook[mask]
    roi_powers = p[mask]
    best_idx = int(np.argmax(roi_powers))
    return float(roi_angles[best_idx])


def _curvature_metric(power_linear):
    """Compute curvature metric from power vector (second-order differences)."""
    p = np.array(power_linear, dtype=float)
    if p.size < 3:
        return 0.0
    maxabs = np.max(np.abs(p))
    if maxabs < 1e-12:
        maxabs = 1.0
    sec = np.abs(np.diff(p, n=2))
    return float(np.mean(sec) / maxabs)


def _steering_vector(ris_xy: np.ndarray, theta_rad: float, wavelength: float) -> np.ndarray:
    """Return steering vector (complex) for RIS element positions (Nx2) at angle theta_rad."""
    k = 2.0 * np.pi / wavelength
    ux = math.cos(theta_rad)
    uy = math.sin(theta_rad)
    phases = -k * (ris_xy[:, 0] * ux + ris_xy[:, 1] * uy)
    return np.exp(1j * phases)


def _quantize_phases(phases: np.ndarray, bits: int) -> np.ndarray:
    """Quantize phases to discrete levels (phase-shift keying)."""
    if bits <= 0:
        return np.exp(1j * phases)
    levels = 2 ** bits
    idx = np.round((phases + np.pi) / (2.0 * np.pi) * levels) % levels
    quant = idx * (2.0 * np.pi / levels) - np.pi
    return np.exp(1j * quant)


def _predict_power_vector(ris_xy: np.ndarray, codebook_angles_deg, theta_rad: float, wavelength: float, quant_bits: int = 0) -> np.ndarray:
    """Predict normalized power vector (len M) for a given outgoing angle theta_rad."""
    code_rad = np.radians(np.asarray(codebook_angles_deg, dtype=float))
    a_theta = _steering_vector(ris_xy, theta_rad, wavelength)
    pred = np.zeros(len(code_rad), dtype=float)
    for i, b in enumerate(code_rad):
        w_phases = np.angle(_steering_vector(ris_xy, b, wavelength))
        w = np.conj(_quantize_phases(w_phases, quant_bits))
        val = np.vdot(w, a_theta)
        pred[i] = np.abs(val) ** 2
    m = pred.max()
    if m <= 0:
        return pred
    return pred / m


def _model_fit_angle_deg(ris_xy: np.ndarray, codebook_angles_deg, measured_power_norm, wavelength: float, grid_step_deg: float = 0.5, quant_bits: int = 0) -> Tuple[float, bool, float]:
    """Multi-scale grid search to find theta minimizing MSE (finds global optimum, avoids local minima).

    IMPROVED: Replaced scipy.optimize.minimize with hierarchical grid search.
    The old approach got stuck in local minima. This approach:
    1. Coarse grid (10° steps): Covers entire range, finds global region
    2. Fine grid (1° steps): Refines around coarse best, finds accurate minimum
    """
    # Stage 1: Coarse grid search (10 degree steps to find global region)
    coarse_step = 10.0
    coarse_grid = np.deg2rad(np.arange(-90.0, 90.0 + coarse_step, coarse_step))
    coarse_errs = np.zeros_like(coarse_grid)

    for i, th in enumerate(coarse_grid):
        pred = _predict_power_vector(ris_xy, codebook_angles_deg, th, wavelength, quant_bits)
        coarse_errs[i] = float(np.sum((pred - measured_power_norm) ** 2))

    coarse_best_idx = int(np.argmin(coarse_errs))
    coarse_best_angle_deg = float(np.degrees(coarse_grid[coarse_best_idx]))

    # Stage 2: Fine grid search (1 degree steps in ±10 degree window)
    fine_window_deg = 10.0
    fine_step = 1.0
    fine_grid_deg = np.arange(
        coarse_best_angle_deg - fine_window_deg,
        coarse_best_angle_deg + fine_window_deg,
        fine_step
    )
    fine_grid = np.deg2rad(fine_grid_deg)
    fine_errs = np.zeros_like(fine_grid)

    for i, th in enumerate(fine_grid):
        pred = _predict_power_vector(ris_xy, codebook_angles_deg, th, wavelength, quant_bits)
        fine_errs[i] = float(np.sum((pred - measured_power_norm) ** 2))

    fine_best_idx = int(np.argmin(fine_errs))
    final_angle_deg = float(fine_grid_deg[fine_best_idx])
    final_loss = float(fine_errs[fine_best_idx])

    return final_angle_deg, True, final_loss


def _model_match_score(measured_norm: np.ndarray, predicted_norm: np.ndarray, gamma: float = 25.0) -> Dict[str, float]:
    """Compare measured vs predicted normalized power and return diagnostics."""
    y = np.asarray(measured_norm, dtype=float)
    mu = np.asarray(predicted_norm, dtype=float)
    res = y - mu
    mse = float(np.mean(res ** 2))
    denom = np.mean(y ** 2) + 1e-12
    nmse = float(mse / denom)
    score = float(math.exp(-gamma * nmse))
    out = {"mse": mse, "nmse": nmse, "score": score}

    if _scipy_stats is not None:
        try:
            sigma2 = max(1e-12, float(np.var(res, ddof=1)))
            chi2 = float(np.sum((res ** 2) / sigma2))
            dof = max(1, y.size - 1)
            pval = 1.0 - float(_scipy_stats.chi2.cdf(chi2, dof))
            out.update({"sigma2": sigma2, "chi2": chi2, "p_value": pval, "dof": dof})
        except Exception:
            pass

    return out



def _confidence_score(power_linear, curvature_k):
    """Compute confidence score based on peak-to-mean ratio and curvature."""
    p = np.array(power_linear, dtype=float)
    if p.size == 0:
        return 0.0
    peak_to_mean = (np.max(p) + 1e-12) / (np.mean(p) + 1e-12)
    s = 0.5 * (peak_to_mean - 1.0) - 5.0 * curvature_k
    conf = 1.0 / (1.0 + math.exp(-s))
    return float(max(0.0, min(1.0, conf)))


def estimate_outgoing_from_snr(
    codebook_angles_deg,
    snr_db,
    ris_xy_abs,
    ris_center_xy,
    ap_pos_xy,
    freq_hz,
    quant_bits: int = 0,
    beta: float = 10.0,
    grid_step_deg: float = 0.5,
    match_gamma: float = 25.0,
):
    """Hybrid magnitude-only estimator entrypoint.

    All angles returned are in LOCAL DEFLECTION SPACE (relative to RIS normal).
    The caller must add the RIS normal to convert to absolute angles.

    Returns dict with theta_cent, theta_model, theta_est (all local deflections),
    plus curvature, confidence, model_ok, model_loss.

    Args:
        codebook_angles_deg: Local deflection angles tested (degrees, relative to RIS normal).
        snr_db: SNR measurements (dB).
        ris_xy_abs: Nx2 array of RIS element positions (absolute coordinates).
        ris_center_xy: (x, y) RIS center position.
        ap_pos_xy: (x, y) AP position (only used for reference, not for frame conversion).
        freq_hz: Frequency in Hz.
        quant_bits: Phase quantization bits (0 = continuous).
        beta: Exponential weighting parameter for alpha.
        grid_step_deg: Grid refinement step size.
    """
    c = 299792458.0
    wavelength = c / float(freq_hz)

    P = _snr_db_to_linear(snr_db)
    Pnorm = P / (np.max(P) + 1e-12)

    ris_xy = np.array(ris_xy_abs, dtype=float)
    rc = np.array(ris_center_xy, dtype=float)
    if ris_xy.shape[1] == 2 and (not np.allclose(ris_xy.mean(axis=0), 0.0)):
        ris_xy_rel = ris_xy - rc.reshape(1, 2)
    else:
        ris_xy_rel = ris_xy.copy()

    theta_cent = _centroid_angle_deg(codebook_angles_deg, P)
    curvature = _curvature_metric(P)

    theta_model, ok, loss = _model_fit_angle_deg(ris_xy_rel, codebook_angles_deg, Pnorm, wavelength, grid_step_deg, quant_bits)
    model_theta_rad = math.radians(theta_model)
    pred_norm = _predict_power_vector(ris_xy_rel, codebook_angles_deg, model_theta_rad, wavelength, quant_bits)
    model_match = _model_match_score(Pnorm, pred_norm, gamma=match_gamma)

    # If model-fit loss is too high, it's unreliable - use centroid only
    loss_threshold = 0.05  # Model validity threshold (tuned to trust good-but-not-perfect fits)
    if loss > loss_threshold:
        alpha = 1.0  # Use centroid only
        theta_est = theta_cent
    else:
        alpha = float(math.exp(-beta * curvature))
        alpha = max(alpha, 0.5)  # Clamp to minimum 0.5 - always trust centroid at least 50%
        c1 = complex(math.cos(math.radians(theta_cent)), math.sin(math.radians(theta_cent)))
        c2 = complex(math.cos(math.radians(theta_model)), math.sin(math.radians(theta_model)))
        combined = alpha * c1 + (1.0 - alpha) * c2
        theta_est = float(_wrap180_deg(math.degrees(math.atan2(combined.imag, combined.real))))

    confidence = _confidence_score(P, curvature)

    return {
        "theta_cent_deg": theta_cent,
        "theta_model_deg": theta_model,
        "theta_est_deg": theta_est,
        "alpha_centroid": alpha,
        "curvature": curvature,
        "confidence": confidence,
        "model_fit_ok": ok,
        "model_fit_loss": loss,
        "model_rejected": loss > loss_threshold,
        "loss_threshold": loss_threshold,
        "model_match": model_match,
        "predicted_power_norm": pred_norm.tolist(),
    }


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
    import cvxpy as cp

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


@register_algorithm("prime", aliases=("prime-inference", "power-ris-estimation", "anm"))
class PRIMELocalizationSweep(SweepAlgorithmBase):
    """Power-based RIS Inference for Multi-Angle Estimation (PRIME) sweep.

    Leverages hybrid magnitude-only estimator (centroid + model fitting) as default,
    with optional complex ANM/L1 sparse recovery for richer measurements.
    """

    @property
    def name(self) -> str:
        return "PRIME Localization Sweep"

    @property
    def description(self) -> str:
        return "Power-based RIS inference with hybrid magnitude-only estimator and optional complex ANM solver."

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

        # Align the absolute beam grid with the linear sweep: offsets are taken from the AP direction.
        abs_angles = ap_angle + clamped_local

        # Track the same beams relative to the RIS normal for estimation/metadata.
        clamped_local_ris = np.array(
            [compute_offset_from_normal(float(abs_angle), ris_normal) for abs_angle in abs_angles],
            dtype=float,
        )

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
        best_local_angle_ap = float(clamped_local[best_idx])
        best_local_angle_ris = float(clamped_local_ris[best_idx])
        best_snr = float(snr_values[best_idx])

        P_linear = _snr_db_to_linear(snr_values)
        if np.max(P_linear) > 0:
            P_norm_for_curv = P_linear / np.max(P_linear)
        else:
            P_norm_for_curv = P_linear

        curvature = _compute_curvature_metric(P_norm_for_curv)
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
        recommended_source = "pending"
        recommended_local_angle_ap = None
        recommended_local_angle_ris = None
        recommended_abs_angle = None
        recommendation_status = "not_available"
        anm_est_az_deg = None

        if not enable_nearfield and prelim_mode == "near-field":
            mode_note = "Near-field classification suppressed; forcing far-field output."

        if mode == "far-field":
            has_complex = False

            if not has_complex:
                ris_xy_abs = getattr(ris, "element_positions", None)
                if ris_xy_abs is None:
                    try:
                        Nx = getattr(ris, "Nx", None) or getattr(ris, "N", 16)
                        Ny = getattr(ris, "Ny", None) or getattr(ris, "N", 16)
                        spacing = getattr(ris, "spacing", None) or getattr(ris, "element_spacing", 0.028)
                        xs = (np.arange(Nx) - (Nx-1)/2.0) * spacing + ris.pos[0]
                        ys = (np.arange(Ny) - (Ny-1)/2.0) * spacing + ris.pos[1]
                        ris_xy_abs = np.array([[x, y] for y in ys for x in xs])
                    except Exception:
                        ris_xy_abs = np.array([[float(ris.pos[0]), float(ris.pos[1])]])
                ris_xy_abs = np.asarray(ris_xy_abs, dtype=float)
                center_vec = np.zeros(ris_xy_abs.shape[1], dtype=float)
                pos_arr = np.asarray(ris.pos, dtype=float)
                take = min(center_vec.shape[0], pos_arr.shape[0])
                center_vec[:take] = pos_arr[:take]
                ris_xy_rel = ris_xy_abs - center_vec.reshape(1, -1)

                codebook_angles_deg = clamped_local_ris.tolist()

                est = estimate_outgoing_from_snr(
                    codebook_angles_deg=codebook_angles_deg,
                    snr_db=snr_values.tolist(),
                    ris_xy_abs=ris_xy_abs,
                    ris_center_xy=(float(ris.pos[0]), float(ris.pos[1])),
                    ap_pos_xy=(float(ap.pos[0]), float(ap.pos[1])),
                    freq_hz=float(ris.freq),
                    quant_bits=kwargs.get("quant_bits", 0),
                    beta=kwargs.get("beta", 10.0),
                    grid_step_deg=kwargs.get("grid_step_deg", 0.5),
                    match_gamma=kwargs.get("match_gamma", 25.0),
                )

                # DEBUG: Print what estimator returned
                peak_idx = int(np.nanargmax(snr_values))
                peak_local_angle_ap = float(clamped_local[peak_idx])
                peak_local_angle_ris = float(clamped_local_ris[peak_idx])
                logger.debug(
                    "\nDEBUG PRIME Estimator:\n"
                    "  Peak (measured): %.2f° (local vs RIS normal)\n"
                    "  Centroid result: %.2f° (local)\n"
                    "  Model-fit result: %.2f° (local)\n"
                    "  Hybrid result: %.2f° (local)\n"
                    "  Model rejected: %s, Loss: %.4f",
                    peak_local_angle_ris,
                    est['theta_cent_deg'],
                    est['theta_model_deg'],
                    est['theta_est_deg'],
                    est['model_rejected'],
                    est['model_fit_loss'],
                )

                theta_cent_local = float(est["theta_cent_deg"])
                theta_model_local = float(est["theta_model_deg"])
                theta_hybrid_local = float(est["theta_est_deg"])

                cent_abs_angle = ris_normal + theta_cent_local
                model_abs_angle = ris_normal + theta_model_local
                hybrid_abs_angle = ris_normal + theta_hybrid_local

                model_theta_rad = math.radians(theta_model_local)
                predicted_power_norm = _predict_power_vector(
                    ris_xy_rel,
                    codebook_angles_deg,
                    model_theta_rad,
                    wavelength,
                    kwargs.get("quant_bits", 0),
                ).tolist()

                solver_status = "magnitude_hybrid_enhanced"
                solver_time = 0.0
                atomic_norm_value = None

                if not est["model_rejected"]:
                    recommended_local_angle_ris = theta_model_local
                    recommended_abs_angle = model_abs_angle
                    recommended_source = "model_fit"
                    recommendation_status = "model_fit"
                    anm_est_az_deg = recommended_abs_angle
                    steering_angles = {"azimuth_rad": np.radians(recommended_abs_angle), "elevation_rad": 0.0}
                else:
                    recommended_local_angle_ris = None
                    recommended_abs_angle = None
                    recommended_source = "no_reliable_estimate"
                    recommendation_status = "no_reliable_estimate"
                    anm_est_az_deg = None
                    steering_angles = None

                metadata_local = {
                    "hybrid_theta_cent_deg": theta_cent_local,
                    "hybrid_theta_model_deg": theta_model_local,
                    "hybrid_theta_est_deg": theta_hybrid_local,
                    "hybrid_alpha_centroid": est["alpha_centroid"],
                    "hybrid_curvature": est["curvature"],
                    "hybrid_confidence": est["confidence"],
                    "hybrid_model_fit_ok": est["model_fit_ok"],
                    "hybrid_model_fit_loss": est["model_fit_loss"],
                    "loss_threshold": est["loss_threshold"],
                    "peak_local_angle_deg": peak_local_angle_ap,
                    "peak_local_angle_deg_ris": peak_local_angle_ris,
                    "model_predicted_power_norm": predicted_power_norm,
                    "model_match_score": est.get("model_match"),
                    "recommendation_status": recommendation_status,
                    "diagnostic_suggestions": "Increase sweep resolution or enable near-field ANM/CSI.",
                    "note": "PRIME strict mode: accept model-fit only when loss is below threshold.",
                }

                if recommended_abs_angle is not None:
                    recommended_local_angle_ap = compute_offset_from_normal(recommended_abs_angle, ap_angle)
            else:
                design = _build_plane_steering(rel_positions, angles_rad, wavelength)
                weights, solver_status, solver_time = _solve_sparse_recovery(design, y_vector, lambda_reg)
                if weights is not None:
                    predicted = design @ weights
                    est_idx = int(np.argmax(np.abs(predicted)))
                    est_theta = float(angles_rad[est_idx])
                    steering_angles = {"azimuth_rad": est_theta, "elevation_rad": 0.0}
                    atomic_norm_value = float(np.sum(np.abs(weights)))
                    est_az_deg = np.degrees(est_theta)
                    anm_est_az_deg = est_az_deg
                    ris_max_angle = getattr(ris, "max_angle_deg", 60.0)
                    offset = compute_offset_from_normal(est_az_deg, ris_normal)
                    offset = clamp_offset_to_fov(offset, ris_max_angle)
                    recommended_local_angle_ris = float(offset)
                    recommended_abs_angle = float(ris_normal + offset)
                    recommended_source = "anm_estimate"
                    recommendation_status = "anm_estimate"
                else:
                    steering_angles = {"azimuth_rad": np.radians(best_abs_angle), "elevation_rad": 0.0}

                recommended_local_angle_ap = compute_offset_from_normal(recommended_abs_angle, ap_angle)
        else:
            solver_status = "skipped_nearfield_not_implemented"
            separable_estimates = None
            if recommendation_status == "not_available":
                recommendation_status = "not_applicable"


        location = self._build_location_output(mode, recommended_abs_angle, ris, ue)

        metadata = {
            "algorithm": "PRIMELocalizationSweep",
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
            "recommendation_status": recommendation_status,
            "original_best_angle_local": best_local_angle_ap,
            "original_best_angle_local_ris": best_local_angle_ris,
            "original_best_angle_abs": best_abs_angle,
            "recommended_local_angle": recommended_local_angle_ap,
            "recommended_local_angle_ris": recommended_local_angle_ris,
            "recommended_abs_angle": recommended_abs_angle,
            "anm_estimated_az_deg": anm_est_az_deg,
            "angles_tested_count": int(num_angles),
            "ap_angle_deg": ap_angle,
            "ue_angle_deg": ue_angle,
            "ris_normal_deg": ris_normal,
            "ap_offset_from_ris_deg": compute_offset_from_normal(ap_angle, ris_normal),
            "fov_deg": fov,
            "step_deg": step,
        }

        if 'metadata_local' in locals():
            metadata.update(metadata_local)

        return {
            "mode": mode,
            "location": location,
            "confidence": confidence,
            "curvature": curvature,
            "curvature_threshold": curvature_threshold,
            "algo_object": self,
            "suppress_tables": True,
            "local_coarse": clamped_local.tolist(),
            "snr_coarse": snr_values.tolist(),
            "pwr_coarse": pwr_values.tolist(),
            "specular_angle": ap_angle,
            "best_angle": recommended_local_angle_ap,
            "measurements": {
                "angles_tested": abs_angles.tolist(),
                "snr_values": snr_values.tolist(),
                "num_measurements": int(num_angles),
                "best_angle": recommended_abs_angle,
                "best_snr_dB": best_snr,
            },
            "metadata": metadata,
        }

    @staticmethod
    def _build_location_output(mode: str, best_angle: float, ris, ue) -> Dict:
        """Create location dictionary depending on classification."""
        if best_angle is None:
            return {
                "type": "direction-only",
                "note": "No reliable estimate produced by PRIME model-fit.",
            }

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
        """Map curvature to a 0-1 confidence score.

        Uses a softer sigmoid-like formula instead of hard threshold.
        - Low curvature (< threshold) = high confidence
        - High curvature (> threshold) = moderate confidence
        - Never returns 0.0 for valid measurements
        """
        eps = 1e-6
        if mode == "far-field":
            # For far-field: confidence decreases as curvature increases
            # Use sigmoid-like formula: 1 / (1 + curvature/threshold)
            ratio = curvature / (threshold + eps)
            return float(1.0 / (1.0 + ratio))  # Returns 0.5 at ratio=1.0 (curvature=threshold)
        else:
            # For near-field: higher curvature is expected, so higher confidence when curv > threshold
            ratio = (threshold + eps) / (curvature + eps)
            return float(min(1.0, 1.0 / (1.0 + ratio)))
