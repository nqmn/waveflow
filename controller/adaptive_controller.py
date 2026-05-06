"""
Adaptive link control for AP power and rate adaptation
Implements closed-loop feedback system with CSI-based optimization
"""
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
import time

logger = logging.getLogger(__name__)


class AdaptiveController:
    """Manages closed-loop adaptive control for AP-UE links"""

    def __init__(self, network):
        """
        Initialize adaptive controller

        Args:
            network: RISNetwork instance
        """
        self.network = network
        self.active_links = {}
        self.control_history = {}
        self.max_history_size = 100

    def enable_adaptation(self, ap_name: str, power_control: bool = True,
                         rate_adaptation: bool = True,
                         target_snr_dB: float = 20.0):
        """Enable adaptive control for an AP

        Args:
            ap_name: AP name
            power_control: Enable closed-loop power control
            rate_adaptation: Enable rate adaptation
            target_snr_dB: Target SNR setpoint
        """
        ap = self.network.get(ap_name)
        if ap is None or not hasattr(ap, 'power_control_enabled'):
            raise ValueError(f"Invalid AP: {ap_name}")

        ap.power_control_enabled = power_control
        ap.rate_adaptation_enabled = rate_adaptation
        ap.target_snr_dB = target_snr_dB

        self.active_links[ap_name] = {
            'enabled': True,
            'start_time': time.time(),
            'iterations': 0,
            'converged': False
        }

        if ap_name not in self.control_history:
            self.control_history[ap_name] = []

    def disable_adaptation(self, ap_name: str):
        """Disable adaptive control for an AP"""
        ap = self.network.get(ap_name)
        if ap and hasattr(ap, 'power_control_enabled'):
            ap.power_control_enabled = False
            ap.rate_adaptation_enabled = False

        if ap_name in self.active_links:
            self.active_links[ap_name]['enabled'] = False

    def control_iteration(self, ap_name: str, ris_name: str, ue_name: str,
                         snr_measurement_dB: Optional[float] = None) -> Dict:
        """Execute one adaptive control iteration

        Args:
            ap_name: Access Point name
            ris_name: RIS name (for link context)
            ue_name: UE name
            snr_measurement_dB: Measured SNR if available

        Returns:
            Control iteration results
        """
        ap = self.network.get(ap_name)
        ue = self.network.get(ue_name)

        if ap is None or ue is None:
            raise ValueError(f"Invalid nodes: AP={ap_name}, UE={ue_name}")

        if not hasattr(ap, 'power_control_enabled'):
            raise ValueError(f"{ap_name} does not support adaptive control")

        if not self.active_links.get(ap_name, {}).get('enabled'):
            return {'status': 'disabled'}

        link_status = self.active_links[ap_name]

        iteration_result = {
            'iteration': link_status['iterations'],
            'timestamp': time.time(),
            'ap_name': ap_name,
            'ue_name': ue_name,
            'ris_name': ris_name,
            'pre_control': {
                'power_dBm': ap.power_dBm,
                'mcs': ap.get_current_mcs()['name']
            }
        }

        if snr_measurement_dB is None:
            if ue.snr_measurement_dB is not None:
                snr_measurement_dB = ue.snr_measurement_dB
            else:
                iteration_result['status'] = 'no_snr_measurement'
                return iteration_result

        iteration_result['measured_snr_dB'] = snr_measurement_dB

        csi_feedback = ue.generate_csi_feedback(snr_dB=snr_measurement_dB)

        control_actions = ap.process_csi_feedback(csi_feedback)
        iteration_result['control_actions'] = control_actions

        iteration_result['post_control'] = {
            'power_dBm': ap.power_dBm,
            'mcs': ap.get_current_mcs()['name']
        }

        snr_error = abs(ap.target_snr_dB - snr_measurement_dB)
        iteration_result['snr_error_dB'] = snr_error

        convergence_threshold = 1.0
        if snr_error < convergence_threshold:
            link_status['converged'] = True
            iteration_result['convergence_status'] = 'converged'
        else:
            iteration_result['convergence_status'] = 'adapting'

        link_status['iterations'] += 1

        self.control_history[ap_name].append(iteration_result)
        if len(self.control_history[ap_name]) > self.max_history_size:
            self.control_history[ap_name].pop(0)

        return iteration_result

    def full_control_loop(self, ap_name: str, ris_name: str, ue_name: str,
                         max_iterations: int = 20,
                         measure_snr_callback=None) -> Dict:
        """Execute full adaptive control loop until convergence

        Args:
            ap_name: Access Point name
            ris_name: RIS name
            ue_name: UE name
            max_iterations: Maximum iterations before stopping
            measure_snr_callback: Function that measures SNR (args: ap, ris, ue)
                                 Returns SNR in dB

        Returns:
            Full control loop summary
        """
        ap = self.network.get(ap_name)
        ue = self.network.get(ue_name)

        if ap is None or ue is None:
            return {'error': f'Invalid nodes'}

        self.enable_adaptation(ap_name)

        loop_results = {
            'ap_name': ap_name,
            'ue_name': ue_name,
            'ris_name': ris_name,
            'iterations': [],
            'start_time': time.time(),
            'convergence_time': None
        }

        for iteration in range(max_iterations):
            snr_dB = None

            if measure_snr_callback:
                try:
                    result = measure_snr_callback(ap_name, ris_name, ue_name)
                    if isinstance(result, dict):
                        snr_dB = result.get('snr_dB')
                    elif isinstance(result, (int, float)):
                        snr_dB = float(result)
                except Exception as e:
                    snr_dB = None

            iter_result = self.control_iteration(ap_name, ris_name, ue_name,
                                                snr_dB)

            loop_results['iterations'].append(iter_result)

            if iter_result.get('convergence_status') == 'converged':
                loop_results['convergence_time'] = (
                    time.time() - loop_results['start_time']
                )
                break

        loop_results['end_time'] = time.time()
        loop_results['total_time'] = (
            loop_results['end_time'] - loop_results['start_time']
        )
        loop_results['converged'] = (
            loop_results['iterations'][-1].get('convergence_status')
            == 'converged'
        )

        final_mcs = ap.get_current_mcs()
        loop_results['final_state'] = {
            'power_dBm': ap.power_dBm,
            'mcs': final_mcs['name'],
            'efficiency_bps_hz': final_mcs['efficiency_bps_hz'],
            'snr_dB': (loop_results['iterations'][-1].get('measured_snr_dB')
                      if loop_results['iterations'] else None)
        }

        return loop_results

    def get_link_status(self, ap_name: str) -> Dict:
        """Get current status of adaptive link"""
        if ap_name not in self.active_links:
            return {'status': 'inactive'}

        ap = self.network.get(ap_name)
        link = self.active_links[ap_name]

        return {
            'ap_name': ap_name,
            'enabled': link['enabled'],
            'iterations': link['iterations'],
            'converged': link['converged'],
            'elapsed_time': time.time() - link['start_time'],
            'current_power_dBm': ap.power_dBm if ap else None,
            'current_mcs': ap.get_current_mcs()['name'] if ap else None,
            'history_size': len(self.control_history.get(ap_name, []))
        }

    def get_history(self, ap_name: str, last_n: Optional[int] = None) -> List[Dict]:
        """Get control history for an AP

        Args:
            ap_name: AP name
            last_n: Return only last N iterations (None = all)

        Returns:
            List of control iteration results
        """
        history = self.control_history.get(ap_name, [])
        if last_n is not None:
            return history[-last_n:]
        return history

    def print_summary(self, ap_name: str):
        """Log control loop summary."""
        status = self.get_link_status(ap_name)
        history = self.get_history(ap_name)

        if not history:
            logger.info("No history for %s", ap_name)
            return

        lines = [
            "",
            "=" * 70,
            f"ADAPTIVE CONTROL SUMMARY: {ap_name}",
            "=" * 70,
            "",
            f"Status:        {status['enabled'] and 'Enabled' or 'Disabled'}",
            f"Iterations:    {status['iterations']}",
            f"Converged:     {status['converged']}",
            f"Elapsed Time:  {status['elapsed_time']:.2f} seconds",
            "",
            "Final State:",
            f"  Power:       {status['current_power_dBm']:.1f} dBm",
            f"  MCS:         {status['current_mcs']}",
            "",
            "Iteration Details:",
            f"{'Iter':<5} {'SNR(dB)':<10} {'Power(dBm)':<12} {'MCS':<15} "
            f"{'Error(dB)':<10} {'Status':<12}",
            "-" * 70,
        ]

        for h in history[-10:]:
            snr = h.get('measured_snr_dB', '-')
            power = h.get('post_control', {}).get('power_dBm', '-')
            mcs = h.get('post_control', {}).get('mcs', '-')
            error = h.get('snr_error_dB', '-')
            status = h.get('convergence_status', '-')

            snr_str = f"{snr:.1f}" if isinstance(snr, (int, float)) else str(snr)
            power_str = f"{power:.1f}" if isinstance(power, (int, float)) else str(power)
            error_str = f"{error:.1f}" if isinstance(error, (int, float)) else str(error)

            lines.append(
                f"{h['iteration']:<5} {snr_str:<10} {power_str:<12} {mcs:<15} "
                f"{error_str:<10} {status:<12}"
            )

        lines.extend(["", "=" * 70, ""])
        logger.info("\n%s", "\n".join(lines))

    def reset(self, ap_name: Optional[str] = None):
        """Reset adaptation state

        Args:
            ap_name: Specific AP to reset, or None for all
        """
        if ap_name:
            ap = self.network.get(ap_name)
            if ap and hasattr(ap, 'reset_adaptation'):
                ap.reset_adaptation()
            if ap_name in self.control_history:
                self.control_history[ap_name].clear()
            if ap_name in self.active_links:
                del self.active_links[ap_name]
        else:
            for ap_name_iter in list(self.active_links.keys()):
                self.reset(ap_name_iter)
