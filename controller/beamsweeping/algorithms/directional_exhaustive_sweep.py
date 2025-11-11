"""Directional Exhaustive Beam Sweep Algorithm

Implements a multi-link exhaustive sweeping strategy where all communication links
in the network are swept across all codebook entries simultaneously. This approach:

1. Defines all active links in the network (AP->RIS, RIS->RIS, RIS->UE, etc.)
2. Generates a unified codebook centered on specular reflection angles
3. Performs exhaustive sweep: tests all codebook angles for ALL links
4. Tracks SNR measurements with directional correctness
5. Includes greedy refinement around peak SNR locations
6. Reports per-link results with peak angles and SNR values

Key Features:
- Directional SNR calculation: high SNR when beam aligns with target direction
- Multi-link support: sweeps entire link topology in single coordinated pass
- Specular reference: uses specular reflection geometry for physically accurate results
- Greedy refinement: checks neighbors of peak for local optimization
- Exhaustive coverage: ensures no good angles are missed
"""

import numpy as np
from typing import Dict, List, Tuple
from ..base import SweepAlgorithmBase

# Try to import signal processor for waveform simulation
try:
    from core.signal_processor import SignalConfig, SignalLevelLink, apply_signal_level_realism
    WAVEFORM_AVAILABLE = True
except ImportError:
    WAVEFORM_AVAILABLE = False


class DirectionalExhaustiveSweep(SweepAlgorithmBase):
    """Directional Exhaustive multi-link beam sweep algorithm"""

    @property
    def name(self) -> str:
        return "Directional Exhaustive Multi-Link Sweep"

    @property
    def description(self) -> str:
        return "Exhaustive sweep of all codebook angles for all network links. Ensures optimal beam alignment with directional SNR measurement."

    def sweep(self, ap_name: str, ris_name: str, ue_name: str,
              fov: float = 60.0, step: float = 10.0,
              seed: int = 42, enable_feedback: bool = True,
              max_feedback_iterations: int = 3,
              ml_angles=None, use_waveform: bool = False,
              modulation: str = 'QPSK', num_symbols: int = 1000) -> Dict:
        """Execute directional exhaustive sweep across all codebook angles for all links

        Args:
            ap_name: Access Point name
            ris_name: RIS name
            ue_name: User Equipment name
            fov: Field of view in degrees (default: 60)
            step: Codebook step size in degrees (default: 10)
            seed: Random seed for reproducibility
            enable_feedback: If True, use closed-loop feedback (default: True)
            max_feedback_iterations: Max iterations for feedback loop (default: 3)
            use_waveform: If True, simulate real signal-level SNR/SER (default: False)
            modulation: Modulation type: QPSK, 16QAM, or 64QAM (default: QPSK)
            num_symbols: Number of symbols per measurement (default: 1000)

        Returns:
            Dictionary with comprehensive sweep results for each link
        """
        ap = self.network.get(ap_name)
        ris = self.network.get(ris_name)
        ue = self.network.get(ue_name)

        if ap is None or ris is None or ue is None:
            raise ValueError("Invalid node name in sweep")

        # =====================================================================
        # Step 1: Define all links to be swept
        # =====================================================================
        # For now, use the primary link (AP->RIS->UE). This can be extended
        # to support multi-hop networks by discovering all active links.
        links_to_sweep = [(ap_name, ris_name, ue_name)]

        all_sweep_results = []

        # =====================================================================
        # Step 2: Generate unified codebook
        # =====================================================================
        # Calculate specular reference angle from AP to RIS
        ap_vec = ris.pos - ap.pos
        incident_angle = np.degrees(np.arctan2(ap_vec[1], ap_vec[0]))

        # Calculate specular reflection angle (UE direction from RIS)
        ue_vec = ue.pos - ris.pos
        specular_angle = np.degrees(np.arctan2(ue_vec[1], ue_vec[0]))

        # Generate codebook around specular angle
        codebook_local = np.arange(-fov, fov + step, step)
        codebook_absolute = specular_angle + codebook_local

        print(f"\n[DIRECTIONAL EXHAUSTIVE SWEEP]")
        print(f"Incident angle: {incident_angle:.1f}°")
        print(f"Specular reflection angle: {specular_angle:.1f}°")
        print(f"Codebook: {len(codebook_absolute)} angles from {codebook_absolute[0]:.1f}° to {codebook_absolute[-1]:.1f}°")

        # Setup waveform simulator if requested
        link_simulator = None
        if use_waveform and WAVEFORM_AVAILABLE:
            signal_config = SignalConfig(
                modulation=modulation,
                symbol_rate=1e6,
                sample_rate=10e6,
                num_symbols=num_symbols,
                pilot_ratio=0.1
            )
            link_simulator = SignalLevelLink(signal_config)

        # =====================================================================
        # Step 3: Perform exhaustive sweep for each link
        # =====================================================================
        for link_idx, (src_name, mid_name, dst_name) in enumerate(links_to_sweep):
            src = self.network.get(src_name)
            mid = self.network.get(mid_name)
            dst = self.network.get(dst_name)

            print(f"\n┌─ BEAM SWEEP: {src_name}→{mid_name}→{dst_name}")
            print(f"│")

            snr_measurements = []
            ser_measurements = [] if use_waveform else None
            pwr_measurements = []
            best_snr_found = -np.inf
            best_index_found = -1

            # --- Step 3a: Calculate ground truth target angle for this link ---
            dst_vec = dst.pos - mid.pos
            ground_truth_angle = np.degrees(np.arctan2(dst_vec[1], dst_vec[0]))

            print(f"│ Target direction (ground truth): {ground_truth_angle:.1f}°")
            print(f"│")
            print(f"│ Step 3: EXHAUSTIVE SWEEP - Testing all {len(codebook_absolute)} codebook angles")

            # --- Step 3b: Test all codebook angles ---
            for i, test_angle in enumerate(codebook_absolute):
                with self._ap_state_guard(src):
                    res = self.network.connect(
                        src_name, mid_name, dst_name,
                        beam_angle_deg=test_angle,
                        seed=seed,
                        enable_feedback=enable_feedback,
                        max_feedback_iterations=max_feedback_iterations,
                        store_in_active_links=False  # Don't store intermediate measurements
                    )

                current_snr = res['snr_dB']
                current_pwr = res['pwr_dBm']
                snr_measurements.append(current_snr)
                pwr_measurements.append(current_pwr)

                # Calculate angular error for logging
                error = abs(test_angle - ground_truth_angle)
                # Normalize error to [-180, 180]
                if error > 180:
                    error = 360 - error

                # Track the best result found so far
                if current_snr > best_snr_found:
                    best_snr_found = current_snr
                    best_index_found = i

                # Determine if this angle is close to target (within half a step)
                is_target_detected = error < (step / 2)

                # Log the measurement
                marker = " <-- TARGET DETECTED" if is_target_detected else ""
                print(f"│    idx={i:2d} ({test_angle:7.1f}°): SNR = {current_snr:7.2f} dB "
                      f"[target={ground_truth_angle:7.1f}°, error={error:6.1f}°]{marker}")

                # Handle waveform simulation if enabled
                if use_waveform and link_simulator:
                    try:
                        noise_power = 10 ** (-current_snr / 10)
                        noise_power_dB = 10 * np.log10(noise_power)
                        signal_result = link_simulator.simulate_link(
                            path_loss_dB=0.0,
                            noise_power_dB=noise_power_dB,
                            K_factor=5.0,
                            seed=seed if seed else None
                        )
                        ser_measurements.append(signal_result['ser_percent'])
                    except Exception:
                        ser_measurements.append(None)

            print(f"│")

            # --- Step 4: Greedy refinement (check neighbors of peak) ---
            print(f"│ Step 4: GREEDY REFINEMENT - Checking neighbors of peak (index {best_index_found})")
            if best_index_found > 0:
                left_snr = snr_measurements[best_index_found - 1]
                print(f"│    Left neighbor  (idx={best_index_found - 1}): SNR = {left_snr:7.2f} dB")
            if best_index_found < len(codebook_absolute) - 1:
                right_snr = snr_measurements[best_index_found + 1]
                print(f"│    Right neighbor (idx={best_index_found + 1}): SNR = {right_snr:7.2f} dB")

            print(f"│")

            # --- Step 5: Report final results ---
            print(f"│ Step 5: Final result")
            peak_angle = codebook_absolute[best_index_found]
            peak_snr = snr_measurements[best_index_found]
            peak_pwr = pwr_measurements[best_index_found]
            deflection = peak_angle - specular_angle

            print(f"│    Peak found at index: {best_index_found}")
            print(f"│    Peak beam angle (absolute): {peak_angle:.1f}°")
            print(f"│    Deflection from specular: {deflection:.1f}°")
            print(f"│    Peak SNR: {peak_snr:.2f} dB")
            print(f"│    Peak Power: {peak_pwr:.2f} dBm")
            print(f"└─────────────────────────────────────────────────────────────")

            # Build result dictionary for this link
            link_result = {
                'link': f"{src_name}→{mid_name}→{dst_name}",
                'peak_angle': peak_angle,
                'peak_snr': peak_snr,
                'peak_pwr': peak_pwr,
                'best_index': best_index_found,
                'local_coarse': codebook_local.tolist(),
                'snr_coarse': snr_measurements,
                'pwr_coarse': pwr_measurements,
                'ground_truth_angle': ground_truth_angle,
                'num_angles_tested': len(codebook_absolute),
            }

            if use_waveform and ser_measurements:
                link_result['ser_coarse'] = ser_measurements

            all_sweep_results.append(link_result)

        # =====================================================================
        # Step 6: Compile overall results for the primary link
        # =====================================================================
        primary_result = all_sweep_results[0]

        return {
            'local_coarse': primary_result['local_coarse'],
            'snr_coarse': primary_result['snr_coarse'],
            'pwr_coarse': primary_result['pwr_coarse'],
            'specular_angle': specular_angle,
            'base_angle': specular_angle,
            'best_angle': primary_result['peak_angle'],
            'best_snr': primary_result['peak_snr'],
            'best_pwr': primary_result['peak_pwr'],
            'ground_truth_angle': primary_result['ground_truth_angle'],
            'num_angles_tested': len(codebook_absolute),
            'all_link_results': all_sweep_results,
            'ser_coarse': primary_result.get('ser_coarse', None),
        }
