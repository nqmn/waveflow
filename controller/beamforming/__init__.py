"""
Beamforming algorithms for RIS optimization

Available engines:
- BeamformingEngine: Main beamforming optimization

Usage:
    from controller.beamforming import BeamformingEngine
    engine = BeamformingEngine()
    result = engine.optimize_beamforming(...)
"""

from .engine import BeamformingEngine

__all__ = ['BeamformingEngine']
