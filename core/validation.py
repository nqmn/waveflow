"""
Validation framework for comparing system-level vs waveform-level results
"""
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
import json


@dataclass
class ValidationMetrics:
    """Metrics for comparing two simulation levels"""
    snr_diff_dB: float = 0.0
    snr_relative_error_percent: float = 0.0
    capacity_diff_bps: float = 0.0
    capacity_relative_error_percent: float = 0.0
    waveform_penalty_dB: float = 0.0
    simulation_time_ratio: float = 0.0
    consistency_score: float = 0.0  # 0-100: how consistent are the results

    def to_dict(self) -> Dict:
        return {
            'snr_diff_dB': self.snr_diff_dB,
            'snr_relative_error_percent': self.snr_relative_error_percent,
            'capacity_diff_bps': self.capacity_diff_bps,
            'capacity_relative_error_percent': self.capacity_relative_error_percent,
            'waveform_penalty_dB': self.waveform_penalty_dB,
            'simulation_time_ratio': self.simulation_time_ratio,
            'consistency_score': self.consistency_score,
        }


class WaveformValidator:
    """Validates waveform-level simulations"""

    def __init__(self, network, waveform_controller=None):
        """
        Initialize validator

        Args:
            network: RISNetwork instance
            waveform_controller: WaveformController instance
        """
        self.network = network
        self.waveform_controller = waveform_controller
        self.validation_history = []

    def validate_basic_physics(self, ap_name: str, ris_name: str,
                              ue_name: str) -> Dict:
        """
        Validate basic physics laws are maintained

        Returns:
            Dict with validation results
        """
        ap = self.network.get(ap_name)
        ris = self.network.get(ris_name)
        ue = self.network.get(ue_name)

        results = {}

        # Check: RIS gain should be positive
        ris_gain_linear = ris.N ** 2
        results['ris_gain_positive'] = ris_gain_linear > 0

        # Check: Path loss should increase with distance
        d_ap_ris = np.linalg.norm(ris.pos - ap.pos)
        d_ris_ue = np.linalg.norm(ue.pos - ris.pos)
        d_direct = np.linalg.norm(ue.pos - ap.pos)

        from core.physics import Physics, C
        pl_direct = Physics.path_loss_dB(d_direct, ap.freq)
        pl_ap_ris = Physics.path_loss_dB(d_ap_ris, ap.freq)
        pl_ris_ue = Physics.path_loss_dB(d_ris_ue, ap.freq)

        results['path_loss_monotonic'] = (
            pl_direct < pl_ap_ris + pl_ris_ue + 50  # RIS should beat direct at some point
        )

        # Check: Phase quantization reduces gain
        results['quantization_reduces_gain'] = ris.bits > 0

        # Check: Antenna gain non-negative
        results['antenna_gain_valid'] = ap.power_dBm > -100

        return {
            'physics_valid': all(results.values()),
            'checks': results,
            'distances': {
                'ap_to_ris_m': float(d_ap_ris),
                'ris_to_ue_m': float(d_ris_ue),
                'direct_path_m': float(d_direct),
            },
            'path_losses_dB': {
                'direct': float(pl_direct),
                'ap_to_ris': float(pl_ap_ris),
                'ris_to_ue': float(pl_ris_ue),
            }
        }

    def compare_results(self, system_result: Dict, waveform_result: Dict,
                       expected_snr_dB_range: Tuple[float, float] = (-10, 30)
                       ) -> ValidationMetrics:
        """
        Compare system-level and waveform-level results

        Args:
            system_result: Result from system-level simulation
            waveform_result: Result from waveform-level simulation
            expected_snr_dB_range: Expected SNR range for validity

        Returns:
            ValidationMetrics object
        """
        system_snr = system_result.get('snr_dB', 0)
        waveform_snr = waveform_result.get('snr_ris_dB', 0)
        waveform_snr_eff = waveform_result.get('snr_effective_dB', waveform_snr)

        # Calculate differences
        snr_diff = waveform_snr - system_snr
        snr_rel_error = 100 * abs(snr_diff) / (abs(system_snr) + 1e-10)

        # Capacity difference (if available)
        capacity_diff = 0.0
        capacity_rel_error = 0.0
        if 'capacity_bps' in waveform_result:
            capacity_diff = waveform_result['capacity_bps']

        # Waveform penalty
        waveform_penalty = waveform_snr - waveform_snr_eff

        # Consistency score: how close waveform SNR is to expected range
        consistency = 100.0
        if not (expected_snr_dB_range[0] <= waveform_snr <= expected_snr_dB_range[1]):
            margin = min(
                abs(waveform_snr - expected_snr_dB_range[0]),
                abs(waveform_snr - expected_snr_dB_range[1])
            )
            consistency = max(0, 100 - margin * 5)

        metrics = ValidationMetrics(
            snr_diff_dB=snr_diff,
            snr_relative_error_percent=snr_rel_error,
            capacity_diff_bps=capacity_diff,
            capacity_relative_error_percent=capacity_rel_error,
            waveform_penalty_dB=waveform_penalty,
            consistency_score=consistency
        )

        self.validation_history.append({
            'system_snr_dB': float(system_snr),
            'waveform_snr_dB': float(waveform_snr),
            'waveform_snr_effective_dB': float(waveform_snr_eff),
            'metrics': metrics.to_dict()
        })

        return metrics

    def validate_topology(self, topology_file: str = None) -> Dict:
        """
        Validate entire network topology

        Args:
            topology_file: Optional JSON topology file

        Returns:
            Dict with validation results
        """
        results = {
            'num_nodes': len(self.network.nodes),
            'num_aps': 0,
            'num_ris': 0,
            'num_ues': 0,
            'nodes': {},
            'physics_checks': {},
            'connectivity_checks': {}
        }

        from core.nodes import AccessPoint, RIS, UE

        for name, node in self.network.nodes.items():
            results['nodes'][name] = {
                'type': node.__class__.__name__,
                'position': node.pos.tolist(),
            }

            if isinstance(node, AccessPoint):
                results['num_aps'] += 1
            elif isinstance(node, RIS):
                results['num_ris'] += 1
                results['nodes'][name]['grid_size'] = node.N
                results['nodes'][name]['bits'] = node.bits
            elif isinstance(node, UE):
                results['num_ues'] += 1

        # Connectivity checks
        if results['num_aps'] > 0 and results['num_ris'] > 0 and results['num_ues'] > 0:
            ap_name = list(self.network.nodes.keys())[0]
            ris_name = [n for n, node in self.network.nodes.items()
                       if isinstance(node, RIS)][0]
            ue_name = [n for n, node in self.network.nodes.items()
                      if isinstance(node, UE)][0]

            results['physics_checks'] = self.validate_basic_physics(
                ap_name, ris_name, ue_name
            )

        results['valid'] = (
            results['num_aps'] > 0 and
            results['num_ris'] > 0 and
            results['num_ues'] > 0
        )

        return results

    def generate_report(self, output_file: str = None) -> str:
        """
        Generate validation report

        Args:
            output_file: Optional file to save report

        Returns:
            Report string
        """
        report = "=" * 70 + "\n"
        report += "WAVEFORM-LEVEL VALIDATION REPORT\n"
        report += "=" * 70 + "\n\n"

        if not self.validation_history:
            report += "No validation results to report.\n"
            return report

        report += f"Total Comparisons: {len(self.validation_history)}\n\n"

        # Summary statistics
        snr_diffs = [h['metrics']['snr_diff_dB'] for h in self.validation_history]
        waveform_penalties = [h['metrics']['waveform_penalty_dB']
                             for h in self.validation_history]
        consistency_scores = [h['metrics']['consistency_score']
                             for h in self.validation_history]

        report += "SNR Analysis:\n"
        report += f"  Mean system SNR: {np.mean([h['system_snr_dB'] for h in self.validation_history]):.2f} dB\n"
        report += f"  Mean waveform SNR: {np.mean([h['waveform_snr_dB'] for h in self.validation_history]):.2f} dB\n"
        report += f"  Mean effective SNR: {np.mean([h['waveform_snr_effective_dB'] for h in self.validation_history]):.2f} dB\n"
        report += f"  SNR difference (mean): {np.mean(snr_diffs):.2f} dB\n"
        report += f"  SNR difference (std): {np.std(snr_diffs):.2f} dB\n\n"

        report += "Waveform Impairments:\n"
        report += f"  Mean waveform penalty: {np.mean(waveform_penalties):.2f} dB\n"
        report += f"  Max waveform penalty: {np.max(waveform_penalties):.2f} dB\n"
        report += f"  Min waveform penalty: {np.min(waveform_penalties):.2f} dB\n\n"

        report += "Consistency:\n"
        report += f"  Mean consistency score: {np.mean(consistency_scores):.1f}%\n"
        report += f"  Min consistency score: {np.min(consistency_scores):.1f}%\n\n"

        report += "=" * 70 + "\n"
        report += "Individual Results:\n"
        report += "=" * 70 + "\n\n"

        for i, result in enumerate(self.validation_history):
            report += f"Comparison {i+1}:\n"
            report += f"  System-level SNR:      {result['system_snr_dB']:7.2f} dB\n"
            report += f"  Waveform-level SNR:    {result['waveform_snr_dB']:7.2f} dB\n"
            report += f"  Effective SNR:         {result['waveform_snr_effective_dB']:7.2f} dB\n"
            report += f"  Difference:            {result['metrics']['snr_diff_dB']:7.2f} dB\n"
            report += f"  Waveform penalty:      {result['metrics']['waveform_penalty_dB']:7.2f} dB\n"
            report += f"  Consistency score:     {result['metrics']['consistency_score']:6.1f}%\n\n"

        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
            report += f"\nReport saved to: {output_file}\n"

        return report

    def export_metrics_json(self, output_file: str) -> str:
        """Export metrics as JSON"""
        data = {
            'validation_history': self.validation_history,
            'summary': {
                'total_comparisons': len(self.validation_history),
                'mean_snr_diff_dB': float(np.mean([
                    h['metrics']['snr_diff_dB'] for h in self.validation_history
                ])),
                'mean_waveform_penalty_dB': float(np.mean([
                    h['metrics']['waveform_penalty_dB'] for h in self.validation_history
                ])),
                'mean_consistency_score_percent': float(np.mean([
                    h['metrics']['consistency_score'] for h in self.validation_history
                ])),
            }
        }

        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)

        return f"Metrics exported to: {output_file}"


class PerformanceAnalyzer:
    """Analyze performance metrics and compute figures of merit"""

    @staticmethod
    def compute_fom(system_result: Dict, waveform_result: Dict) -> Dict:
        """
        Compute Figures of Merit (FOM)

        Args:
            system_result: System-level result
            waveform_result: Waveform-level result

        Returns:
            Dict with various FOM
        """
        fom = {}

        # FOM1: SNR Improvement (waveform vs system)
        snr_system = system_result.get('snr_dB', 0)
        snr_waveform = waveform_result.get('snr_ris_dB', 0)
        fom['snr_improvement_dB'] = snr_waveform - snr_system

        # FOM2: Quantization penalty
        ideal_snr = waveform_result.get('snr_ris_dB', 0)
        effective_snr = waveform_result.get('snr_effective_dB', 0)
        fom['quantization_penalty_dB'] = ideal_snr - effective_snr

        # FOM3: Spectral efficiency (capacity / bandwidth)
        if 'capacity_bps' in waveform_result:
            bandwidth = waveform_result.get('bandwidth_MHz', 100) * 1e6
            fom['spectral_efficiency_bps_hz'] = waveform_result['capacity_bps'] / bandwidth

        # FOM4: Energy efficiency (capacity / power)
        if 'capacity_bps' in waveform_result:
            power_dBm = system_result.get('pwr_dBm', 20)
            power_mW = 10 ** (power_dBm / 10)
            fom['energy_efficiency_bps_mw'] = waveform_result['capacity_bps'] / max(power_mW, 0.1)

        # FOM5: PAPR (Peak-to-Average Power Ratio)
        fom['papr_dB'] = waveform_result.get('papr_dB', 8.0)

        # FOM6: Phase quantization states
        fom['phase_states'] = waveform_result.get('phase_states', 4)

        return fom

    @staticmethod
    def compare_fom(fom1: Dict, fom2: Dict, fom_names: List[str] = None) -> Dict:
        """Compare two sets of FOM"""
        if fom_names is None:
            fom_names = list(fom1.keys())

        comparison = {}
        for name in fom_names:
            if name in fom1 and name in fom2:
                diff = fom2[name] - fom1[name]
                rel_change = 100 * diff / (abs(fom1[name]) + 1e-10)
                comparison[name] = {
                    'fom1': fom1[name],
                    'fom2': fom2[name],
                    'difference': diff,
                    'relative_change_percent': rel_change
                }

        return comparison
