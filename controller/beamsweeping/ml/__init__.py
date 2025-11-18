"""ML predictor registry for beam sweeping."""

from __future__ import annotations

import importlib
from typing import Dict, Tuple

from .base import SweepMLPredictor


class MLPredictorLoader:
    """Factory for ML-based beam sweep predictors."""

    PREDICTORS: Dict[str, Tuple[str, str]] = {
        'default': ('controller.beamsweeping.ml.gmf', 'GMFPredictor'),
        'xgb': ('controller.beamsweeping.ml.xgb', 'XGBPredictor'),
        'rf': ('controller.beamsweeping.ml.rf', 'RFPredictor'),
        'svr': ('controller.beamsweeping.ml.svr', 'SVRPredictor'),
        'knn': ('controller.beamsweeping.ml.knn', 'KNNPredictor'),
        'lr': ('controller.beamsweeping.ml.lr', 'LRPredictor'),
        'dt': ('controller.beamsweeping.ml.dt', 'DTPredictor'),
        'lgbm': ('controller.beamsweeping.ml.lgbm', 'LGBMPredictor'),
        'zero': ('controller.beamsweeping.ml.trivial', 'ZeroOffsetPredictor'),
        'gmf': ('controller.beamsweeping.ml.gmf', 'GMFPredictor'),
        'kgmf': ('controller.beamsweeping.ml.kgmf', 'KGMFPredictor'),
        'vgmf': ('controller.beamsweeping.ml.vgmf', 'VGMFPredictor'),
        'vxgb': ('controller.beamsweeping.ml.vxgb', 'VXGBPredictor'),
    }
    _CLASS_CACHE = {}

    @classmethod
    def get_predictor(cls, name: str, network):
        key = (name or 'default').lower()
        if key not in cls.PREDICTORS:
            available = ', '.join(cls.PREDICTORS.keys())
            raise ValueError(f"Unknown ML predictor '{name}'. Available: {available}")
        predictor_cls = cls._get_predictor_class(key)
        return predictor_cls(network)

    @classmethod
    def list_predictors(cls):
        info = {}
        for name, predictor_cls in cls.PREDICTORS.items():
            instance = cls._get_predictor_class(name)(None)
            info[name] = {
                'class_name': instance.name,
                'description': instance.description
            }
        return info

    @classmethod
    def _get_predictor_class(cls, key: str):
        if key in cls._CLASS_CACHE:
            return cls._CLASS_CACHE[key]
        module_name, class_name = cls.PREDICTORS[key]
        module = importlib.import_module(module_name)
        predictor_cls = getattr(module, class_name)
        cls._CLASS_CACHE[key] = predictor_cls
        return predictor_cls


__all__ = [
    'SweepMLPredictor',
    'MLPredictorLoader',
    'XGBPredictor',
    'RFPredictor',
    'SVRPredictor',
    'KNNPredictor',
    'LRPredictor',
    'DTPredictor',
    'LGBMPredictor',
    'ZeroOffsetPredictor',
    'GMFPredictor',
    'KGMFPredictor',
    'VGMFPredictor',
    'VXGBPredictor',
]


def __getattr__(name: str):
    """Lazily load predictor classes so heavy dependencies run only on demand."""
    key = _find_predictor_key_for_class(name)
    if key is None:
        raise AttributeError(f"module {__name__} has no attribute {name}")
    predictor_cls = MLPredictorLoader._get_predictor_class(key)
    globals()[name] = predictor_cls
    return predictor_cls


def __dir__():
    return sorted(set(__all__) | set(globals().keys()))


def _find_predictor_key_for_class(name: str):
    for key, (_, class_name) in MLPredictorLoader.PREDICTORS.items():
        if class_name == name:
            return key
    return None
