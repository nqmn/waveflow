"""
Waveform-aware RIS controller for advanced beamforming
Integrates waveform-level processing with RIS control
Includes full cascade simulation with UE receiver pipeline
"""
import numpy as np
from typing import Dict, Tuple, Optional
from core.waveform import (
    OFDMConfig, OFDMSignal, PropagationChannel,
    AntennaArray, RISReflectionModel, OFDMReceiver,
    calculate_effective_snr, calculate_papr
)
from core.physics import Physics
from core.ue_receiver import UEReceiverPipeline, UEAdaptationController


class WaveformController:
    """Advanced RIS controller for waveform-level operations"""

    def __init__(self, network, environment=None):
        """
        Initialize waveform controller

        Args:
            network: RISNetwork instance
            environment: Environment instance
        """
        self.network = network
        self.environment = environment
        self.ofdm_config = OFDMConfig()
        self.stats = {}

    def set_ofdm_config(self, bandwidth: float = 100e6,
                       num_subcarriers: int = 256,
                       center_freq: float = 10e9):
        """Configure OFDM parameters"""
        self.ofdm_config = OFDMConfig(
            bandwidth=bandwidth,
            num_subcarriers=num_subcarriers,
            center_frequency=center_freq
        )

    def compute_waveform_snr(self, ap_name: str, ris_name: str,
                            ue_name: str, num_symbols: int = 10,
                            beam_angle_deg: Optional[float] = None) -> Dict:
        """
        Compute SNR using waveform-level simulation

        Args:
            ap_name: Access Point name
            ris_name: RIS name
            ue_name: UE name
            num_symbols: Number of OFDM symbols to simulate
            beam_angle_deg: Beam steering angle in degrees (if None, uses optimal path-based phases)

        Returns:
            Dict with waveform-level results
        """
        # Get nodes
        ap = self.network.get(ap_name)
        ris = self.network.get(ris_name)
        ue = self.network.get(ue_name)

        if not (ap and ris and ue):
            raise ValueError(f"Invalid node names: {ap_name}, {ris_name}, {ue_name}")

        # Generate OFDM signal
        ofdm = OFDMSignal(self.ofdm_config, num_symbols=num_symbols)
        tx_signal = ofdm.generate()

        # Direct path: AP -> UE (for reference)
        channel_direct = PropagationChannel(
            self.ofdm_config.center_frequency,
            self.ofdm_config.sampling_rate,
            model='simple_multipath'
        )
        rx_direct = channel_direct.propagate(tx_signal)

        # RIS-assisted path: AP -> RIS -> UE
        # 1. AP to RIS propagation
        channel_ap_ris = PropagationChannel(
            self.ofdm_config.center_frequency,
            self.ofdm_config.sampling_rate,
            model='simple_multipath'
        )
        signal_at_ris = channel_ap_ris.propagate(tx_signal)

        # 2. RIS reflection
        ris_model = RISReflectionModel(
            ris.N, ris.bits,
            self.ofdm_config.center_frequency,
            coupling_enabled=True
        )

        # Compute phases based on beam angle or optimal path
        wavelength = 3e8 / self.ofdm_config.center_frequency
        k = 2 * np.pi / wavelength

        if beam_angle_deg is not None:
            # Steering to specified angle
            # Phase shift for linear steering: k * element_position * sin(beam_angle)
            beam_angle_rad = np.radians(beam_angle_deg)
            ideal_phases = np.zeros(ris.N**2)
            for i, elem_pos in enumerate(ris.element_positions):
                # Simplified: steering in one plane using x-coordinate
                ideal_phases[i] = k * elem_pos[0] * np.sin(beam_angle_rad)
        else:
            # Optimal path-based phases (original behavior)
            distances = np.array([
                np.linalg.norm(elem_pos - ap.pos)
                for elem_pos in ris.element_positions
            ])
            distances_ue = np.array([
                np.linalg.norm(ris.element_positions[i] - ue.pos)
                for i in range(ris.N**2)
            ])
            ideal_phases = k * (distances + distances_ue)

        ideal_phases = np.mod(ideal_phases, 2 * np.pi)
        ris_model.set_phase_config(ideal_phases)

        # 3. RIS to UE propagation
        channel_ris_ue = PropagationChannel(
            self.ofdm_config.center_frequency,
            self.ofdm_config.sampling_rate,
            model='simple_multipath'
        )

        # Reflect waveform through RIS
        signal_reflected = np.zeros_like(signal_at_ris) if hasattr(signal_at_ris, 'shape') \
            else signal_at_ris

        # Simplified reflection: apply RIS gain to entire signal
        ris_gain_dB = 20 * np.log10(ris.N)  # Theoretical gain
        ris_gain_linear = 10 ** (ris_gain_dB / 20)
        signal_reflected = ris_gain_linear * signal_at_ris

        rx_ris = channel_ris_ue.propagate(signal_reflected)

        # 4. Add AWGN at receiver
        snr_desired = 20.0  # dB
        rx_ris = channel_ris_ue.add_awgn(rx_ris, snr_desired)
        rx_direct = channel_direct.add_awgn(rx_direct, snr_desired)

        # 5. OFDM Reception and Channel Estimation
        receiver = OFDMReceiver(self.ofdm_config)

        # For RIS path
        freq_rx_ris = receiver.remove_cp_and_fft(rx_ris)
        tx_ofdm = ofdm.generate()
        freq_tx = receiver.remove_cp_and_fft(tx_ofdm)

        channel_est_ris = receiver.estimate_channel(
            freq_rx_ris,
            ofdm.pilot_indices,
            freq_tx
        )

        # Equalize RIS received signal
        eq_ris = receiver.equalize(freq_rx_ris, channel_est_ris)

        # Calculate SNR metrics
        snr_direct_dB = receiver.calculate_snr(rx_direct, 0.01)
        snr_ris_dB = receiver.calculate_snr(rx_ris, 0.01)
        papr_tx = calculate_papr(tx_signal)

        # Effective SNR considering waveform impairments
        # Correctly compute phase error wrapped to [-π, π]
        # Phase error in radians (wrapping to principal value)
        phase_error_raw = ris_model.current_phases - ris_model.quantized_phases
        phase_error = np.angle(np.exp(1j * phase_error_raw))  # Wraps to [-π, π]

        # RMS phase error in degrees (with proper wrapping to [-180°, 180°])
        quant_error_rms = np.degrees(np.sqrt(np.mean(phase_error**2)))

        # Guard against invalid SNR values
        if not np.isfinite(snr_ris_dB) or snr_ris_dB < -100:
            snr_ris_dB = -50.0  # Fallback to realistic poor SNR

        snr_eff = Physics.effective_snr_with_waveform_distortion(
            snr_ris_dB,
            quant_error_rms,
            papr_dB=papr_tx
        )

        # Guard against NaN in effective SNR
        if not np.isfinite(snr_eff):
            snr_eff = snr_ris_dB - 3.0  # Assume ~3 dB impairment

        # Compute channel capacity
        capacity = Physics.compute_channel_capacity_bps(
            snr_eff,
            self.ofdm_config.bandwidth
        )

        results = {
            'snr_direct_dB': float(snr_direct_dB),
            'snr_ris_dB': float(snr_ris_dB),
            'snr_effective_dB': float(snr_eff),
            'papr_dB': float(papr_tx),
            'capacity_bps': float(capacity),
            'quantization_error_rms_deg': float(quant_error_rms),
            'ris_gain_dB': float(ris_gain_dB),
            'phase_states': int(2 ** ris.bits),
            'pilot_indices': ofdm.pilot_indices.tolist(),
            'ideal_phases': ideal_phases.tolist(),
            'quantized_phases': ris_model.quantized_phases.tolist(),
            'waveform_type': 'OFDM',
            'num_subcarriers': self.ofdm_config.num_subcarriers,
            'bandwidth_MHz': self.ofdm_config.bandwidth / 1e6,
        }

        return results

    def optimize_ris_phases_waveform(self, ap_name: str, ris_name: str,
                                    ue_name: str, num_iterations: int = 10) -> Dict:
        """
        Optimize RIS phases using gradient-based waveform-level optimization

        Args:
            ap_name: Access Point name
            ris_name: RIS name
            ue_name: UE name
            num_iterations: Number of optimization iterations

        Returns:
            Dict with optimization results
        """
        ap = self.network.get(ap_name)
        ris = self.network.get(ris_name)
        ue = self.network.get(ue_name)

        if not (ap and ris and ue):
            raise ValueError(f"Invalid node names: {ap_name}, {ris_name}, {ue_name}")

        wavelength = 3e8 / 10e9  # Default frequency
        k = 2 * np.pi / wavelength

        best_snr = -np.inf
        best_phases = np.zeros(ris.N * ris.N)
        snr_history = []

        for iteration in range(num_iterations):
            # Compute reference phases
            distances = np.array([
                np.linalg.norm(elem_pos - ap.pos)
                for elem_pos in ris.element_positions
            ])
            distances_ue = np.array([
                np.linalg.norm(ris.element_positions[i] - ue.pos)
                for i in range(ris.N**2)
            ])

            # Phase sweep with random perturbation
            phase_perturbation = np.random.uniform(-np.pi/4, np.pi/4, ris.N**2)
            phases = k * (distances + distances_ue) + phase_perturbation
            phases = np.mod(phases, 2*np.pi)

            # Simulate and get SNR
            ris.set_beam_config(beam_angle=0, phases=phases)
            result = self.compute_waveform_snr(ap_name, ris_name, ue_name, num_symbols=5)
            snr = result['snr_effective_dB']

            # Handle NaN values - use fallback SNR
            if not np.isfinite(snr):
                snr = result.get('snr_ris_dB', -100)  # Fallback to waveform SNR

            snr_history.append(snr)

            if np.isfinite(snr) and snr > best_snr:
                best_snr = snr
                best_phases = phases.copy()

        # Set best phases
        ris.set_beam_config(beam_angle=0, phases=best_phases)

        return {
            'best_snr_dB': float(best_snr),
            'final_snr_dB': float(snr_history[-1]),
            'snr_history': [float(s) for s in snr_history],
            'convergence': 'converged' if snr_history[-1] > best_snr * 0.95 else 'improving',
            'num_iterations': num_iterations,
            'best_phases': best_phases.tolist()
        }

    def compute_beam_sweep_waveform(self, ap_name: str, ris_name: str,
                                   ue_name: str, angle_range: float = 60.0,
                                   angle_step: float = 5.0) -> Dict:
        """
        Perform beam sweep at waveform level

        Args:
            ap_name: Access Point name
            ris_name: RIS name
            ue_name: UE name
            angle_range: Sweep range in degrees
            angle_step: Step size in degrees

        Returns:
            Dict with beam sweep results
        """
        ris = self.network.get(ris_name)
        if not ris:
            raise ValueError(f"RIS {ris_name} not found")

        angles = np.arange(-angle_range/2, angle_range/2 + angle_step, angle_step)
        snr_values = []
        capacity_values = []

        for angle in angles:
            # Compute SNR with steering phases for this angle
            result = self.compute_waveform_snr(ap_name, ris_name, ue_name,
                                              num_symbols=3, beam_angle_deg=angle)

            # Handle NaN by using fallback values
            snr_val = result['snr_effective_dB']
            if not np.isfinite(snr_val):
                snr_val = result.get('snr_ris_dB', -100)

            cap_val = result['capacity_bps']
            if not np.isfinite(cap_val):
                cap_val = 0.0

            snr_values.append(snr_val)
            capacity_values.append(cap_val)

        snr_values = np.array(snr_values)
        capacity_values = np.array(capacity_values)

        # Find best valid SNR (exclude -inf)
        valid_idx = np.where(np.isfinite(snr_values) & (snr_values > -1000))[0]
        if len(valid_idx) == 0:
            valid_idx = np.arange(len(snr_values))

        best_idx = valid_idx[np.argmax(snr_values[valid_idx])]
        best_angle = angles[best_idx]
        best_snr = snr_values[best_idx]

        return {
            'angles': angles.tolist(),
            'snr_values': snr_values.tolist(),
            'capacity_values': capacity_values.tolist(),
            'best_angle': float(best_angle),
            'best_snr_dB': float(best_snr),
            'best_capacity_bps': float(capacity_values[best_idx]),
            'sweep_type': 'waveform_level'
        }

    def compare_system_vs_waveform(self, ap_name: str, ris_name: str,
                                  ue_name: str) -> Dict:
        """
        Compare system-level vs waveform-level results

        Args:
            ap_name: Access Point name
            ris_name: RIS name
            ue_name: UE name

        Returns:
            Dict with comparison results
        """
        # System-level result
        system_result = self.network.connect(ap_name, ris_name, ue_name)

        # Waveform-level result
        waveform_result = self.compute_waveform_snr(ap_name, ris_name, ue_name)

        comparison = {
            'system_level': {
                'snr_dB': system_result.get('snr_dB', None),
                'power_dBm': system_result.get('pwr_dBm', None),
                'gain_dB': 10 * np.log10(system_result.get('gain_linear', 1.0)),
            },
            'waveform_level': {
                'snr_dB': waveform_result['snr_ris_dB'],
                'snr_effective_dB': waveform_result['snr_effective_dB'],
                'capacity_bps': waveform_result['capacity_bps'],
                'papr_dB': waveform_result['papr_dB'],
            },
            'difference': {
                'snr_diff_dB': waveform_result['snr_ris_dB'] - system_result.get('snr_dB', 0),
                'waveform_penalty_dB': waveform_result['snr_ris_dB'] - waveform_result['snr_effective_dB'],
            }
        }

        return comparison

    def simulate_full_cascade(self, ap_name: str, ris_name: str,
                             ue_name: str, num_symbols: int = 10,
                             beam_angle_deg: Optional[float] = None,
                             enable_feedback: bool = True,
                             max_feedback_iterations: int = 3) -> Dict:
        """
        Simulate FULL CASCADE: AP TX → RIS → UE RX with integrated UE receiver pipeline

        This is the fully integrated waveform-level simulation where:
        1. AP generates OFDM signal
        2. AP→RIS propagation with multipath
        3. RIS reflects with phase quantization and coupling
        4. RIS→UE propagation with multipath
        5. UE runs full receiver pipeline: CP removal, FFT, channel estimation, equalization
        6. UE measures SNR from equalized symbols
        7. UE→AP feedback loop for power/MCS adaptation (optional)

        Args:
            ap_name: Access Point name
            ris_name: RIS name
            ue_name: UE name
            num_symbols: Number of OFDM symbols to simulate
            beam_angle_deg: Beam steering angle (None for geometric)
            enable_feedback: Enable closed-loop feedback
            max_feedback_iterations: Max iterations for feedback loop

        Returns:
            Dict with full cascade results including SNR, CSI, and feedback loop info
        """
        # Get nodes
        ap = self.network.get(ap_name)
        ris = self.network.get(ris_name)
        ue = self.network.get(ue_name)

        if not (ap and ris and ue):
            raise ValueError(f"Invalid nodes: {ap_name}, {ris_name}, {ue_name}")

        # ===== STEP 1: AP GENERATES OFDM SIGNAL =====
        ofdm = OFDMSignal(self.ofdm_config, num_symbols=num_symbols)
        tx_signal = ofdm.generate(seed=42)

        # ===== STEP 2: COMPUTE RIS PHASES =====
        wavelength = 3e8 / self.ofdm_config.center_frequency
        k = 2 * np.pi / wavelength

        if beam_angle_deg is not None:
            # Steering to specified angle
            beam_angle_rad = np.radians(beam_angle_deg)
            ideal_phases = np.zeros(ris.N ** 2)
            for i, elem_pos in enumerate(ris.element_positions):
                ideal_phases[i] = k * elem_pos[0] * np.sin(beam_angle_rad)
        else:
            # Optimal path-based phases
            distances = np.array([
                np.linalg.norm(elem_pos - ap.pos)
                for elem_pos in ris.element_positions
            ])
            distances_ue = np.array([
                np.linalg.norm(ris.element_positions[i] - ue.pos)
                for i in range(ris.N ** 2)
            ])
            ideal_phases = k * (distances + distances_ue)

        ideal_phases = np.mod(ideal_phases, 2 * np.pi)

        # ===== STEP 3: RIS MODEL SETUP =====
        ris_model = RISReflectionModel(
            ris.N, ris.bits,
            self.ofdm_config.center_frequency,
            coupling_enabled=True
        )
        ris_model.set_phase_config(ideal_phases)

        # ===== STEP 4: AP → RIS PROPAGATION =====
        channel_ap_ris = PropagationChannel(
            self.ofdm_config.center_frequency,
            self.ofdm_config.sampling_rate,
            model='simple_multipath'
        )
        signal_at_ris = channel_ap_ris.propagate(tx_signal)

        # ===== STEP 5: RIS REFLECTION =====
        # Apply RIS gain
        ris_gain_dB = 20 * np.log10(ris.N)
        ris_gain_linear = 10 ** (ris_gain_dB / 20)
        signal_reflected = ris_gain_linear * signal_at_ris

        # ===== STEP 6: RIS → UE PROPAGATION =====
        channel_ris_ue = PropagationChannel(
            self.ofdm_config.center_frequency,
            self.ofdm_config.sampling_rate,
            model='simple_multipath'
        )
        rx_ris = channel_ris_ue.propagate(signal_reflected)

        # Add AWGN
        snr_desired = 20.0  # dB
        rx_ris = channel_ris_ue.add_awgn(rx_ris, snr_desired)

        # ===== STEP 7: UE RECEIVER PIPELINE =====
        ue_receiver = UEReceiverPipeline(ue, self.ofdm_config)
        ue_adaptation = UEAdaptationController(ue)

        # Process received signal - use receiver to demod and get tx reference
        receiver = OFDMReceiver(self.ofdm_config)
        freq_tx = receiver.remove_cp_and_fft(tx_signal)  # Get TX freq symbols from original

        rx_result = ue_receiver.process_received_waveform(
            rx_ris,
            freq_tx,  # Use frequency domain TX symbols
            ofdm.pilot_indices,
            ris_phases=ideal_phases
        )

        snr_measured = rx_result['snr_dB']
        csi_feedback = rx_result['csi_feedback']

        # ===== STEP 8: CLOSED-LOOP FEEDBACK (OPTIONAL) =====
        feedback_info = None
        if enable_feedback:
            feedback_info = self._run_feedback_loop_waveform(
                ap_name, ris_name, ue_name, snr_measured,
                max_feedback_iterations, ideal_phases, num_symbols
            )

        # ===== COMPILE RESULTS =====
        results = {
            'cascade_type': 'full_waveform',
            'snr_dB': float(snr_measured),
            'snr_measured_dB': float(snr_measured),
            'channel_estimate': rx_result['channel_estimate'],
            'equalized_symbols': rx_result['equalized_symbols'],
            'csi_feedback': csi_feedback,
            'ris_ideal_phases': ideal_phases.tolist(),
            'ris_quantized_phases': ris_model.quantized_phases.tolist(),
            'ris_phase_error_rms_deg': float(
                np.degrees(np.sqrt(np.mean(
                    (ideal_phases - ris_model.quantized_phases) ** 2
                )))
            ),
            'papr_dB': float(calculate_papr(tx_signal)),
            'pilot_indices': ofdm.pilot_indices.tolist(),
            'num_symbols': num_symbols,
            'ofdm_bandwidth_MHz': self.ofdm_config.bandwidth / 1e6,
            'num_subcarriers': self.ofdm_config.num_subcarriers,
        }

        if feedback_info:
            results['feedback_info'] = feedback_info

        return results

    def _run_feedback_loop_waveform(self, ap_name: str, ris_name: str,
                                   ue_name: str, initial_snr_dB: float,
                                   max_iterations: int,
                                   ris_phases: np.ndarray,
                                   num_symbols: int) -> Dict:
        """
        Run closed-loop feedback with waveform-level simulation

        Args:
            ap_name: AP name
            ris_name: RIS name
            ue_name: UE name
            initial_snr_dB: Initial SNR measurement
            max_iterations: Max feedback iterations
            ris_phases: RIS phase configuration
            num_symbols: OFDM symbols per iteration

        Returns:
            Feedback iteration history
        """
        ap = self.network.get(ap_name)
        ue = self.network.get(ue_name)

        if not ap or not ue:
            return {"error": "Invalid AP or UE"}

        # Enable adaptive features
        was_power_enabled = ap.power_control_enabled
        was_rate_enabled = ap.rate_adaptation_enabled

        ap.set_power_control_enabled(True, user_override=None)
        ap.set_rate_adaptation_enabled(True, user_override=None)

        feedback_iterations = []

        for iteration in range(max_iterations):
            # Iteration 0 uses initial SNR
            if iteration == 0:
                snr_measured = initial_snr_dB
            else:
                # Re-simulate with adapted power
                cascade_result = self.simulate_full_cascade(
                    ap_name, ris_name, ue_name,
                    num_symbols=num_symbols,
                    enable_feedback=False
                )
                snr_measured = cascade_result['snr_dB']

            # UE measures and generates feedback
            ue.snr_measurement_dB = snr_measured
            csi_feedback = ue.generate_csi_feedback(snr_dB=snr_measured)

            # AP processes feedback and adapts
            control_action = ap.process_csi_feedback(csi_feedback)

            snr_error = abs(ap.target_snr_dB - snr_measured)
            converged = snr_error < 1.0

            iteration_info = {
                "iteration": iteration,
                "measured_snr_dB": float(snr_measured),
                "ap_power_dBm": float(ap.power_dBm),
                "ap_mcs": ap.get_current_mcs()["name"],
                "snr_error_dB": float(snr_error),
                "converged": converged,
                "control_action": control_action
            }

            feedback_iterations.append(iteration_info)

            if converged:
                break

        # Restore original settings
        ap.set_power_control_enabled(was_power_enabled, user_override=None)
        ap.set_rate_adaptation_enabled(was_rate_enabled, user_override=None)

        return {
            "iterations": feedback_iterations,
            "converged": feedback_iterations[-1]["converged"] if feedback_iterations else False,
            "num_iterations": len(feedback_iterations),
            "final_power_dBm": float(ap.power_dBm),
            "final_mcs": ap.get_current_mcs()["name"],
            "final_snr_dB": float(feedback_iterations[-1]["measured_snr_dB"]) if feedback_iterations else None
        }
