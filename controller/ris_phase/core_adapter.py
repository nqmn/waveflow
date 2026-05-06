"""Controller-backed adapter for the core phase-engine abstraction."""

from __future__ import annotations

import numpy as np

from core.phase_engine import PhaseEngine, register_phase_engine_factory
from core.physics import C

from .phase_hybrid import HybridPhaseEngine
from .phase_manager import RISPhaseManager
from .phase_steering import PhaseSteeringEngine


class ControllerPhaseEngine(PhaseEngine):
    """Phase-engine implementation backed by the existing controller code."""

    def compute_ris_phases(self, ris, ap_pos: np.ndarray, ue_pos: np.ndarray):
        if ris.use_hybrid_engine:
            return HybridPhaseEngine.compute_hybrid_pattern(
                source_pos=ap_pos,
                ris_center_pos=ris.pos,
                target_pos=ue_pos,
                frequency=ris.freq,
                array_size=ris.N,
                plane_tx=ris.plane_tx,
                plane_rx=ris.plane_rx,
                max_angle_deg=ris.max_angle_deg,
                ris_normal_deg=ris.normal_angle_deg,
            )

        wavelength = C / ris.freq
        return PhaseSteeringEngine.phase_pattern_from_deflection(
            source_pos=ap_pos,
            ris_center_pos=ris.pos,
            target_pos=ue_pos,
            wavelength=wavelength,
            ris_array_size=ris.N,
            max_angle_deg=ris.max_angle_deg,
            ris_normal_deg=ris.normal_angle_deg,
        )

    def apply_tapering(self, rows: int, cols: int, window: str = "hamming") -> np.ndarray:
        return PhaseSteeringEngine.apply_tapering(rows, cols, window=window)

    def create_phase_manager(self, ris):
        return RISPhaseManager(ris)


register_phase_engine_factory(ControllerPhaseEngine)
