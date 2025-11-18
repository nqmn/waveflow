"""Adaptive Directional Sweep Algorithm

Stage 1 tests a small set of representative deflections across each side of the RIS.
Stage 2 refines toward the RIS normal by following the winning direction.
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


@register_algorithm("adaptive-directional", aliases=("adaptive-refinement", "adaptive-direction"))
class AdaptiveDirectionalSweep(SweepAlgorithmBase):
    """Sweep that probes fixed offsets and then refines toward the RIS normal."""

    @property
    def name(self) -> str:
        return "Adaptive Directional Sweep"

    @property
    def description(self) -> str:
        return "Adaptive sweep that tests coarse offsets then refines toward the winning deflection."

    def sweep(self, ap_name: str, ris_name: str, ue_name: str,
              fov: float = 60.0, step: float = 10.0,
              seed: int = 42, enable_feedback: bool = True,
              max_feedback_iterations: int = 3,
              ml_angles=None, use_waveform: bool = False,
              modulation: str = 'QPSK', num_symbols: int = 1000,
              metric_selector=None, **kwargs) -> Dict:
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

        local_angles, _ = generate_codebook(fov, step)
        ris_max_angle = getattr(ris, 'max_angle_deg', fov)
        clamped_local = clamp_local_deflection_to_ris_fov(local_angles, ris_max_angle)

        if angle_diff >= 0:
            abs_angles_all = ap_angle + clamped_local
        else:
            abs_angles_all = ap_angle - clamped_local

        rounded = np.round(clamped_local, 6)
        _, unique_indices = np.unique(rounded, return_index=True)
        unique_indices.sort()
        unique_local = clamped_local[unique_indices]
        unique_abs = abs_angles_all[unique_indices]

        if unique_local.size == 0:
            raise RuntimeError("Adaptive sweep has no available deflection angles after clamping.")

        local_to_abs = {
            float(local): float(abs_angle)
            for local, abs_angle in zip(unique_local.tolist(), unique_abs.tolist())
        }

        def snap_local(target: float) -> Optional[float]:
            diffs = np.abs(unique_local - target)
            if diffs.size == 0:
                return None
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

            abs_angle = local_to_abs.get(local_angle)
            if abs_angle is None:
                raise RuntimeError(f"Requested angle {local_angle}° is outside allowed set.")

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
                idx = local_angle_to_index(float(suggested), fov, step, len(local_angles))
                target_local = clamped_local[idx]
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

        stage1_targets = [-60, 60, -40, 40, -20, 20]
        stage1_local: List[float] = []
        for target in stage1_targets:
            if abs(target) > fov + 1e-6:
                continue
            candidate = float(np.clip(target, -ris_max_angle, ris_max_angle))
            snapped = snap_local(candidate)
            if snapped is None or snapped in stage1_local:
                continue
            stage1_local.append(snapped)

        if not stage1_local:
            center = snap_local(0.0)
            if center is None:
                raise RuntimeError("Adaptive sweep cannot determine any initial coarse angles.")
            stage1_local = [center]

        stage1_results: List[Dict] = []
        for local in stage1_local:
            entry = measure_local(local, phase='stage1')
            stage1_results.append(format_entry(entry, phase='stage1'))

        best_stage1_local = stage1_results[0]['local_angle_deg']
        best_stage1_snr = stage1_results[0]['snr_db']
        for summary in stage1_results:
            if summary['snr_db'] > best_stage1_snr:
                best_stage1_local = summary['local_angle_deg']
                best_stage1_snr = summary['snr_db']

        def stage2_candidates(center: float) -> List[float]:
            refinement_step = max(step / 2, 5.0)
            if refinement_step <= 0:
                refinement_step = 5.0

            local_targets: List[float] = []
            if abs(center) < 1e-6:
                local_targets = [0.0, refinement_step, -refinement_step]
            else:
                direction_to_zero = 1 if center < 0 else -1
                for multiplier in (0, 1, 2):
                    local_targets.append(center + direction_to_zero * refinement_step * multiplier)

            refined: List[float] = []
            for target in local_targets:
                if abs(target) > max_local + 1e-6:
                    continue
                snapped = snap_local(target)
                if snapped is None or snapped in refined:
                    continue
                refined.append(snapped)
            if not refined:
                return [center]
            return refined

        stage2_local = stage2_candidates(best_stage1_local)
        stage2_results: List[Dict] = []
        for local in stage2_local:
            entry = measure_local(local, phase='stage2')
            stage2_results.append(format_entry(entry, phase='stage2'))

        # Aggregate measurements for CLI friendliness
        def entries_to_series(entries: List[Dict]) -> tuple[List[float], List[float], List[float], List[Optional[float]]]:
            return (
                [entry['local_angle_deg'] for entry in entries],
                [entry['snr_db'] for entry in entries],
                [entry['pwr_dBm'] for entry in entries],
                [entry['ser_percent'] for entry in entries],
            )

        coarse_local, coarse_snr, coarse_pwr, coarse_ser = entries_to_series(stage1_results)
        fine_local, fine_snr, fine_pwr, fine_ser = entries_to_series(stage2_results) if stage2_results else ([], [], [], [])

        if not measured:
            raise RuntimeError("Adaptive sweep could not record any measurements.")

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
