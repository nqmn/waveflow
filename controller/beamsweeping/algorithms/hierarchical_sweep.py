"""Hierarchical Beam Sweep Algorithm

Implements a multi-stage search that first probes sparse anchor angles and then
zooms in on the winning direction. This limits measurements to the most promising
sectors (±20/±40/±60°) before refining toward the optimal deflection angle.
"""
from __future__ import annotations

import numpy as np
from typing import Dict, List, Optional

from ..base import SweepAlgorithmBase
from ..common import (
    FeedbackCollector,
    apply_waveform_realism,
    clamp_local_deflection_to_ris_fov,
    generate_codebook,
    local_angle_to_index,
    setup_waveform_simulator,
    validate_and_get_nodes,
)
from ..registry import register_algorithm


@register_algorithm(
    "hierarchical",
    aliases=("hierarchical-sweep", "hierarchical-refinement"),
)
class HierarchicalSweep(SweepAlgorithmBase):
    """Hierarchical beam sweep: coarse anchors → neighboring refinement."""

    @property
    def name(self) -> str:
        return "Hierarchical Beam Sweep"

    @property
    def description(self) -> str:
        return "Hierarchical sweep that tests sparse anchors then focuses on winning angles."

    def sweep(self, ap_name: str, ris_name: str, ue_name: str,
              fov: float = 60.0, step: float = 10.0,
              seed: int = 42, enable_feedback: bool = True,
              max_feedback_iterations: int = 3,
              ml_angles=None, use_waveform: bool = False,
              modulation: str = 'QPSK', num_symbols: int = 1000,
              metric_selector=None, **kwargs) -> Dict:
        """Execute the hierarchical sweep across three stages.

        Args:
            ap_name: Access Point name
            ris_name: RIS name
            ue_name: User Equipment name
            fov: Field of view in degrees (default: 60)
            step: Step size in degrees (default: 10)
            seed: Random seed for reproducibility
            enable_feedback: Whether to use closed-loop feedback
            max_feedback_iterations: Feedback loop iterations
            ml_angles: Optional ML-suggested local deflections
            use_waveform: Enable waveform-based realism
            modulation: Waveform modulation scheme
            num_symbols: Symbols per waveform simulation

        Returns:
            Sweep summary dictionary with stage-by-stage measurements and best angle
        """
        ap, ris, ue = validate_and_get_nodes(self.network, ap_name, ris_name, ue_name)

        ap_vec = ap.pos - ris.pos
        ap_angle = np.degrees(np.arctan2(ap_vec[1], ap_vec[0]))

        ue_vec = ue.pos - ris.pos
        ue_angle = np.degrees(np.arctan2(ue_vec[1], ue_vec[0]))

        angle_diff = ue_angle - ap_angle
        while angle_diff > 180:
            angle_diff -= 360
        while angle_diff < -180:
            angle_diff += 360

        local_coarse, num_coarse = generate_codebook(fov, step)

        ris_max_angle = getattr(ris, 'max_angle_deg', 60.0)
        clamped_local_coarse = clamp_local_deflection_to_ris_fov(local_coarse, ris_max_angle)

        if angle_diff >= 0:
            abs_angles_all = ap_angle + clamped_local_coarse
        else:
            abs_angles_all = ap_angle - clamped_local_coarse

        rounded = np.round(clamped_local_coarse, 6)
        _, unique_indices = np.unique(rounded, return_index=True)
        unique_indices.sort()
        unique_local = clamped_local_coarse[unique_indices]
        unique_abs = abs_angles_all[unique_indices]

        if unique_local.size == 0:
            raise RuntimeError("No valid codebook angles available for hierarchical sweep.")

        local_to_abs = {
            float(local): float(abs_angle)
            for local, abs_angle in zip(unique_local.tolist(), unique_abs.tolist())
        }

        def snap_local(target: float) -> Optional[float]:
            if unique_local.size == 0:
                return None
            diffs = np.abs(unique_local - target)
            idx = int(np.argmin(diffs))
            return float(unique_local[idx])

        max_local = float(max(abs(unique_local[0]), abs(unique_local[-1])))

        link_simulator = setup_waveform_simulator(use_waveform, modulation, num_symbols, pilot_ratio=0.1)
        feedback_collector = FeedbackCollector(enable_feedback)

        measured: Dict[float, Dict] = {}
        measurement_counter = 0

        def measure_local(local_angle: float, phase: str) -> Dict:
            nonlocal measurement_counter
            local_angle = float(local_angle)
            if local_angle in measured:
                return measured[local_angle]

            abs_angle = local_to_abs[local_angle]
            with self._ap_state_guard(ap):
                res = self.network.connect(
                    ap_name, ris_name, ue_name,
                    beam_angle_deg=abs_angle,
                    seed=seed,
                    enable_feedback=enable_feedback,
                    max_feedback_iterations=max_feedback_iterations,
                    store_in_active_links=False,
                    use_get_snr=self._should_use_get_snr(),
                )

            waveform_seed = (seed + measurement_counter) if seed is not None else None
            snr_val, ser_val = apply_waveform_realism(
                res,
                link_simulator,
                seed=waveform_seed,
            )

            measurement = {
                'local_angle': local_angle,
                'abs_angle': abs_angle,
                'snr': float(snr_val),
                'pwr': float(res.get('pwr_dBm', float('nan'))),
                'ser': float(ser_val) if ser_val is not None else None,
            }
            measured[local_angle] = measurement
            measurement_counter += 1

            if enable_feedback and 'feedback_info' in res:
                feedback_collector.add(abs_angle, local_angle, res['feedback_info'], phase=phase)

            return measurement

        def format_entry(entry: Dict, phase: str) -> Dict:
            return {
                'phase': phase,
                'local_angle_deg': float(entry['local_angle']),
                'abs_angle_deg': float(entry['abs_angle']),
                'snr_db': float(entry['snr']),
                'pwr_dBm': float(entry['pwr']),
                'ser_percent': float(entry['ser']) if entry['ser'] is not None else None,
            }

        ml_measurements: List[Dict] = []
        ml_cli_results: List[Dict] = []
        ml_suggestions: List[float] = [float(angle) for angle in ml_angles] if ml_angles else []
        if ml_angles:
            for suggested in ml_angles:
                idx = local_angle_to_index(float(suggested), fov, step, num_coarse)
                target_local = clamped_local_coarse[idx]
                snapped = snap_local(target_local)
                if snapped is None:
                    continue
                entry = measure_local(snapped, phase='ml')
                formatted = format_entry(entry, phase='ml')
                ml_measurements.append(formatted)
                ml_cli_results.append({
                    'local_angle': formatted['local_angle_deg'],
                    'snr_dB': formatted['snr_db'],
                    'pwr_dBm': formatted['pwr_dBm'],
                })

        stage1_targets = np.array([-6, -4, -2, 2, 4, 6], dtype=float) * step
        tolerance = max(step, 1e-6)
        stage1_candidates: List[float] = []
        for target in stage1_targets:
            snapped = snap_local(target)
            if snapped is None:
                continue
            if abs(snapped - target) <= tolerance:
                stage1_candidates.append(snapped)

        if not stage1_candidates:
            center_idx = len(unique_local) // 2
            stage1_candidates = [float(unique_local[center_idx])]

        stage1_local = sorted(set(stage1_candidates))
        stage1_results: List[Dict] = []
        for local in stage1_local:
            entry = measure_local(local, phase='stage1')
            stage1_results.append(format_entry(entry, phase='stage1'))

        if not stage1_results:
            raise RuntimeError("Hierarchical sweep stage1 found no valid measurement angles.")

        best_stage1_local = stage1_results[0]['local_angle_deg']
        best_stage1_snr = stage1_results[0]['snr_db']
        for summary in stage1_results:
            if summary['snr_db'] > best_stage1_snr:
                best_stage1_local = summary['local_angle_deg']
                best_stage1_snr = summary['snr_db']

        def neighbor_angles(center: float) -> List[float]:
            neighbors = []
            for offset in (-step, 0.0, step):
                candidate = center + offset
                if abs(candidate) > max_local + 1e-6:
                    continue
                snapped = snap_local(candidate)
                if snapped is None or snapped in neighbors:
                    continue
                neighbors.append(snapped)
            return sorted(neighbors)

        stage2_local = neighbor_angles(best_stage1_local)
        stage2_results: List[Dict] = []
        for local in stage2_local:
            entry = measure_local(local, phase='stage2')
            stage2_results.append(format_entry(entry, phase='stage2'))

        if not stage2_results:
            stage2_results = stage1_results

        best_stage2_local = stage2_results[0]['local_angle_deg']
        best_stage2_snr = stage2_results[0]['snr_db']
        for summary in stage2_results:
            if summary['snr_db'] > best_stage2_snr:
                best_stage2_local = summary['local_angle_deg']
                best_stage2_snr = summary['snr_db']

        stage3_results: List[Dict] = []
        if np.isclose(abs(best_stage2_local), step, atol=1e-6):
            stage3_local = neighbor_angles(best_stage2_local)
            for local in stage3_local:
                entry = measure_local(local, phase='stage3')
                stage3_results.append(format_entry(entry, phase='stage3'))

        if not measured:
            raise RuntimeError("Hierarchical sweep could not record any measurements.")

        def entries_to_series(entries: List[Dict]) -> tuple[List[float], List[float], List[float], List[Optional[float]]]:
            return (
                [entry['local_angle_deg'] for entry in entries],
                [entry['snr_db'] for entry in entries],
                [entry['pwr_dBm'] for entry in entries],
                [entry['ser_percent'] for entry in entries],
            )

        coarse_local, coarse_snr, coarse_pwr, coarse_ser = entries_to_series(stage1_results)
        fine_entries = stage2_results + stage3_results
        if fine_entries:
            fine_local, fine_snr, fine_pwr, fine_ser = entries_to_series(fine_entries)
        else:
            fine_local, fine_snr, fine_pwr, fine_ser = [], [], [], []

        all_measurements = list(measured.values())
        if metric_selector is not None:
            # Use metric selector to find best measurement
            snr_values = [item['snr'] for item in all_measurements]
            best_idx = metric_selector.find_best_index(snr_values)
            best_measurement = all_measurements[best_idx]
        else:
            # Default: use SNR
            best_measurement = max(all_measurements, key=lambda item: item['snr'])
        result = {
            'algorithm': self.name,
            'specular_angle': float(ap_angle),
            'specular_angle_deg': float(ap_angle),
            'stage1': stage1_results,
            'stage2': stage2_results,
            'stage3': stage3_results,
            'ml_measurements': ml_measurements,
            'ml_results': ml_cli_results,
            'ml_suggestions': ml_suggestions,
            'best_local_angle_deg': float(best_measurement['local_angle']),
            'best_angle_deg': float(best_measurement['abs_angle']),
            'best_snr_db': float(best_measurement['snr']),
            'best_pwr_dBm': float(best_measurement['pwr']),
            'best_ser_percent': float(best_measurement['ser']) if best_measurement['ser'] is not None else None,
            'local_coarse': coarse_local,
            'snr_coarse': coarse_snr,
            'pwr_coarse': coarse_pwr,
            'ser_coarse': coarse_ser,
            'local_fine': fine_local,
            'snr_fine': fine_snr,
            'pwr_fine': fine_pwr,
            'ser_fine': fine_ser,
            'feedback': feedback_collector.get_details(),
        }

        return result
