"""ML predictor registry for beam sweeping."""

from .base import SweepMLPredictor
from .trivial import ZeroOffsetPredictor
from .xgb import XGBPredictor
from .rf import RFPredictor
from .svr import SVRPredictor
from .mlp import MLPPredictor


class MLPredictorLoader:
    """Factory for ML-based beam sweep predictors."""

    PREDICTORS = {
        'default': XGBPredictor,
        'xgb': XGBPredictor,
        'rf': RFPredictor,
        'svr': SVRPredictor,
        'mlp': MLPPredictor,
        'zero': ZeroOffsetPredictor,
    }

    @classmethod
    def get_predictor(cls, name: str, network):
        key = (name or 'default').lower()
        if key not in cls.PREDICTORS:
            available = ', '.join(cls.PREDICTORS.keys())
            raise ValueError(f"Unknown ML predictor '{name}'. Available: {available}")
        return cls.PREDICTORS[key](network)

    @classmethod
    def list_predictors(cls):
        info = {}
        for name, predictor_cls in cls.PREDICTORS.items():
            instance = predictor_cls(None)
            info[name] = {
                'class_name': instance.name,
                'description': instance.description
            }
        return info


__all__ = [
    'SweepMLPredictor',
    'MLPredictorLoader',
    'XGBPredictor',
    'RFPredictor',
    'SVRPredictor',
    'MLPPredictor',
]
