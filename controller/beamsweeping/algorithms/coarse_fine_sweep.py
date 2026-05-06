"""Coarse-Fine Two-Phase Beam Sweep Algorithm

Implements an efficient two-phase beam sweeping strategy:
- Phase 1: Coarse center-out sweep (starts from specular angle, expands outward)
- Phase 2: Fine-resolution refinement around best coarse angle

Efficiency: ~30% measurement savings vs exhaustive search

Supports real signal-level emulation via use_waveform parameter.
"""
import numpy as np
from typing import Dict
from ..base import SweepAlgorithmBase
from ..common import (
    apply_waveform_realism,
    generate_codebook,
    local_angle_to_index,
    setup_waveform_simulator,
    validate_and_get_nodes,
    FeedbackCollector,
    clamp_to_ris_fov,
    clamp_local_deflection_to_ris_fov,
)
from ..registry import register_algorithm


@register_algorithm(
    "coarse-fine",
    aliases=("two-phase", "center-out", "adaptive"),
)
class CoarseFineSweep(SweepAlgorithmBase):
    """Coarse-fine two-phase beam sweep algorithm"""

    @property
    def name(self) -> str:
        return "Coarse-Fine Two-Phase Sweep"

    @property
    def description(self) -> str:
        return "Two-phase beam steering: coarse center-out search, then fine refinement. ~30% more efficient."

    def sweep(self, ap_name: str, ris_name: str, ue_name: str,
              fov: float = 60.0, step: float = 10.0,
              fine_span: float = 10.0, fine_res: float = 1.0,
              seed: int = 42, enable_feedback: bool = True,
              max_feedback_iterations: int = 3,
              ml_angles=None, use_waveform: bool = False,
              modulation: str = 'QPSK', num_symbols: int = 1000,
              metric_selector=None, **kwargs) -> Dict:
        """Execute coarse-fine two-phase sweep with optional closed-loop feedback

        Args:
            ap_name: Access Point name
            ris_name: RIS name
            ue_name: User Equipment name
            fov: Field of view in degrees (default: 60)
            step: Coarse step size in degrees (default: 10)
            fine_span: Fine search span around best coarse angle (default: 10)
            fine_res: Fine resolution in degrees (default: 1)
            seed: Random seed for reproducibility
            enable_feedback: If True, use closed-loop feedback for each angle (default: False)
            max_feedback_iterations: Max iterations for feedback loop (default: 3)
            use_waveform: If True, simulate real signal-level SNR/SER (default: False)
            modulation: Modulation type: QPSK, 16QAM, or 64QAM (default: QPSK)
            num_symbols: Number of symbols per measurement (default: 1000)

        Returns:
            Dictionary with sweep results including optional 'ser_coarse' and 'ser_fine' keys
        """
        # Validate nodes
        ap, ris, ue = validate_and_get_nodes(self.network, ap_name, ris_name, ue_name)

        # Calculate incident and reflected azimuths from 3D coordinates
        ap_vec = ap.pos - ris.pos
        ap_angle = np.degrees(np.arctan2(ap_vec[1], ap_vec[0]))

        ue_vec = ue.pos - ris.pos
        ue_angle = np.degrees(np.arctan2(ue_vec[1], ue_vec[0]))

        # Deflection angle is the magnitude of azimuth difference
        angle_diff = ue_angle - ap_angle
        # Wrap to [-180, 180]
        while angle_diff > 180:
            angle_diff -= 360
        while angle_diff < -180:
            angle_diff += 360

        # Base deflection angle (with sign for direction)
        base_deflection_angle = angle_diff

        # Also set base_angle for compatibility (incident direction)
        base_angle = ap_angle

        # Generate codebook centered on optimal RIS normal
        local_coarse, num_coarse = generate_codebook(fov, step)

        # Clamp local deflection angles to RIS FOV constraint (native RIS capability)
        ris_max_angle = getattr(ris, 'max_angle_deg', 60.0)
        clamped_local_coarse = clamp_local_deflection_to_ris_fov(local_coarse, ris_max_angle)

        # Convert deflection angles to absolute beam angles
        if angle_diff > 0:
            # UE is counterclockwise from AP, so add deflection to AP angle
            abs_angles = ap_angle + clamped_local_coarse
        else:
            # UE is clockwise from AP, so subtract deflection from AP angle
            abs_angles = ap_angle - clamped_local_coarse

        # Set specular_angle for result reporting (incident direction)
        specular_angle = ap_angle

        snr_coarse = []
        pwr_coarse = []
        ser_coarse = [None] * num_coarse if use_waveform else None
        feedback_collector = FeedbackCollector(enable_feedback)
        progress_callback = kwargs.get('progress_callback')

        # Setup signal simulator if waveform mode is enabled
        link_simulator = setup_waveform_simulator(use_waveform, modulation, num_symbols, pilot_ratio=0.1)

        # Coarse phase: test center first, then expand
        center_idx = len(local_coarse) // 2
        test_order = [center_idx]

        # Add indices in expanding pattern from center
        for offset in range(1, len(local_coarse)):
            if center_idx - offset >= 0:
                test_order.append(center_idx - offset)
            if center_idx + offset < len(local_coarse):
                test_order.append(center_idx + offset)

        # Test angles in center-out order
        snr_array = np.full(num_coarse, np.nan)
        pwr_array = np.full(num_coarse, np.nan)

        self._emit_progress(
            progress_callback,
            event='start',
            phase='coarse',
            total=num_coarse,
            completed=0,
            best_snr_dB=None,
            best_angle_deg=None,
        )

        def measure_idx(idx: int):
            if not np.isnan(snr_array[idx]):
                return
            with self._ap_state_guard(ap):
                res = self.network.connect(
                    ap_name, ris_name, ue_name,
                    beam_angle_deg=abs_angles[idx], seed=seed,
                    enable_feedback=enable_feedback,
                    max_feedback_iterations=max_feedback_iterations,
                    store_in_active_links=False,  # Don't store intermediate measurements
                    use_get_snr=self._should_use_get_snr()  # Use get_snr() if enabled
                )
            # Check if SNR measurement is valid
            # None indicates UE cannot receive from this angle (outside FOV)
            if res.get('snr_dB') is None:
                # UE cannot receive from this angle - leave as NaN
                snr_array[idx] = np.nan
                pwr_array[idx] = np.nan
                if ser_coarse is not None:
                    ser_coarse[idx] = np.nan
            else:
                snr_val, ser_val = apply_waveform_realism(
                    res,
                    link_simulator,
                    seed=seed + idx if seed else None,
                )
                snr_array[idx] = snr_val
                pwr_array[idx] = res['pwr_dBm']
                if ser_coarse is not None:
                    ser_coarse[idx] = ser_val

            if enable_feedback and 'feedback_info' in res:
                feedback_collector.add(float(abs_angles[idx]), float(local_coarse[idx]), res['feedback_info'], phase='coarse')

            best_snr_so_far = None
            best_angle_so_far = None
            if not np.all(np.isnan(snr_array)):
                best_so_far_idx = int(np.nanargmax(snr_array))
                best_snr_so_far = float(snr_array[best_so_far_idx])
                best_angle_so_far = float(local_coarse[best_so_far_idx])

            self._emit_progress(
                progress_callback,
                event='measurement',
                phase='coarse',
                total=num_coarse,
                completed=int(np.count_nonzero(~np.isnan(snr_array))),
                local_angle_deg=float(local_coarse[idx]),
                abs_angle_deg=float(abs_angles[idx]),
                snr_dB=None if np.isnan(snr_array[idx]) else float(snr_array[idx]),
                best_snr_dB=best_snr_so_far,
                best_angle_deg=best_angle_so_far,
            )

        # Measure ML suggestions ahead of center-out traversal
        if ml_angles:
            for suggested in ml_angles:
                idx = local_angle_to_index(float(suggested), fov, step, num_coarse)
                measure_idx(idx)

        for idx in test_order:
            measure_idx(idx)

        snr_coarse = snr_array.tolist()
        pwr_coarse = pwr_array.tolist()

        # Find best coarse angle using SNR
        # NOTE: metric_selector is no longer passed to sweep algorithms
        # Post-processing in connection_handler will override using correct metric
        best_idx = int(np.argmax(snr_array))
        best_local = local_coarse[best_idx]

        # Phase 2: Fine sweep (constrained within original FOV and RIS constraint)
        fine_start = max(best_local - fine_span, -fov)
        fine_end = min(best_local + fine_span, fov)
        local_fine = np.arange(fine_start, fine_end + fine_res, fine_res)

        # Clamp fine phase angles to RIS FOV constraint
        clamped_local_fine = clamp_local_deflection_to_ris_fov(local_fine, ris_max_angle)

        # Convert fine phase deflection angles to absolute beam angles
        if angle_diff > 0:
            abs_angles_fine = ap_angle + clamped_local_fine
        else:
            abs_angles_fine = ap_angle - clamped_local_fine
        snr_fine = []
        ser_fine = [None] * len(local_fine) if use_waveform else None

        self._emit_progress(
            progress_callback,
            event='start',
            phase='fine',
            total=len(local_fine),
            completed=0,
            best_snr_dB=float(np.nanmax(snr_array)) if not np.all(np.isnan(snr_array)) else None,
            best_angle_deg=float(best_local),
        )

        for i, abs_a in enumerate(abs_angles_fine):
            with self._ap_state_guard(ap):
                r = self.network.connect(
                    ap_name, ris_name, ue_name,
                    beam_angle_deg=abs_a, seed=seed,
                    enable_feedback=enable_feedback,
                    max_feedback_iterations=max_feedback_iterations,
                    store_in_active_links=False,  # Don't store intermediate measurements
                    use_get_snr=self._should_use_get_snr()  # Use get_snr() if enabled
                )
            # Check if SNR measurement is valid
            # None indicates UE cannot receive from this angle (outside FOV)
            if r.get('snr_dB') is None:
                # UE cannot receive from this angle
                snr_fine.append(np.nan)
                if ser_fine is not None:
                    ser_fine[i] = np.nan
            else:
                snr_val, ser_val = apply_waveform_realism(
                    r,
                    link_simulator,
                    seed=seed + i if seed else None,
                )
                snr_fine.append(snr_val)
                if ser_fine is not None:
                    ser_fine[i] = ser_val

            # Store feedback details if enabled
            if enable_feedback and 'feedback_info' in r:
                feedback_collector.add(float(abs_a), float(local_fine[i]), r['feedback_info'], phase='fine')

            best_fine_snr = None
            best_fine_angle = None
            if snr_fine:
                fine_values = np.array(snr_fine, dtype=float)
                if not np.all(np.isnan(fine_values)):
                    best_fine_idx_so_far = int(np.nanargmax(fine_values))
                    best_fine_snr = float(fine_values[best_fine_idx_so_far])
                    best_fine_angle = float(local_fine[best_fine_idx_so_far])

            self._emit_progress(
                progress_callback,
                event='measurement',
                phase='fine',
                total=len(local_fine),
                completed=i + 1,
                local_angle_deg=float(local_fine[i]),
                abs_angle_deg=float(abs_a),
                snr_dB=None if np.isnan(snr_fine[-1]) else float(snr_fine[-1]),
                best_snr_dB=best_fine_snr,
                best_angle_deg=best_fine_angle,
            )

        # Find best fine angle using SNR
        # NOTE: metric_selector is no longer passed to sweep algorithms
        # Post-processing in connection_handler will override using correct metric
        best_fine_idx = int(np.argmax(snr_fine))
        best_local_fine = local_fine[best_fine_idx]

        result = {
            'local_coarse': local_coarse.tolist(),
            'snr_coarse': snr_coarse,
            'pwr_coarse': pwr_coarse,
            'local_fine': local_fine.tolist(),
            'snr_fine': np.array(snr_fine).tolist(),
            'best_local_fine': float(best_local_fine),
            'best_snr_fine': float(np.max(snr_fine)),
            'specular_angle': float(specular_angle),
            'feedback_enabled': enable_feedback,
            'feedback_details': feedback_collector.get_details()
        }

        # Add SER if waveform simulation was used
        if use_waveform and ser_coarse:
            result['ser_coarse'] = ser_coarse
            result['ser_fine'] = ser_fine if ser_fine else []

        self._emit_progress(
            progress_callback,
            event='complete',
            phase='fine',
            total=len(local_fine),
            completed=len(local_fine),
            best_snr_dB=float(np.max(snr_fine)),
            best_angle_deg=float(best_local_fine),
        )

        return result
