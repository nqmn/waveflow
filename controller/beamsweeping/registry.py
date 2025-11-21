"""Runtime registry for beam sweep algorithms."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Type

from .base import SweepAlgorithmBase


@dataclass
class AlgorithmRegistration:
    """Metadata stored for each registered algorithm."""

    primary_name: str
    cls: Type[SweepAlgorithmBase]
    aliases: List[str] = field(default_factory=list)


_registrations_by_class: Dict[Type[SweepAlgorithmBase], AlgorithmRegistration] = {}
_name_lookup: Dict[str, Type[SweepAlgorithmBase]] = {}
_registration_order: "OrderedDict[Type[SweepAlgorithmBase], None]" = OrderedDict()


def register_algorithm(
    name: str,
    *,
    aliases: Iterable[str] = (),
) -> Callable[[Type[SweepAlgorithmBase]], Type[SweepAlgorithmBase]]:
    """Decorator used by sweep algorithms to self-register."""

    def decorator(cls: Type[SweepAlgorithmBase]):
        if not issubclass(cls, SweepAlgorithmBase):
            raise TypeError(
                f"{cls.__name__} must inherit from SweepAlgorithmBase to register"
            )

        normalized_primary = name.lower()
        _store_name_mapping(normalized_primary, cls)

        registration = _registrations_by_class.get(cls)
        if registration is None:
            registration = AlgorithmRegistration(primary_name=name, cls=cls)
            _registrations_by_class[cls] = registration
            _registration_order[cls] = None
        else:
            registration.primary_name = name

        for alias in aliases:
            alias_norm = alias.lower()
            _store_name_mapping(alias_norm, cls)
            if alias not in registration.aliases:
                registration.aliases.append(alias)

        return cls

    return decorator


def _store_name_mapping(name: str, cls: Type[SweepAlgorithmBase]) -> None:
    """Store a normalized name mapping, ensuring no conflicts."""
    existing = _name_lookup.get(name)
    if existing and existing is not cls:
        raise ValueError(
            f"Beam sweep alias '{name}' already registered to "
            f"{existing.__name__}. Cannot register for {cls.__name__}"
        )
    _name_lookup[name] = cls


def get_algorithm_class(name: str) -> Type[SweepAlgorithmBase]:
    """Return the algorithm class for the provided name or alias."""
    key = name.lower()
    if key not in _name_lookup:
        if key == "anm" or key == "anm-localization" or key == "atomic-norm":
            try:
                from .algorithms.anm_localization_sweep import ANMLocalizationSweep
                if key in _name_lookup:
                    return _name_lookup[key]
            except ImportError:
                pass
        available = ", ".join(list_available_names())
        raise ValueError(
            f"Unknown sweep algorithm '{name}'. "
            f"Available algorithms: {available}"
        )
    return _name_lookup[key]


def list_registered_algorithms() -> List[AlgorithmRegistration]:
    """Return registration metadata in insertion order."""
    return [_registrations_by_class[cls] for cls in _registration_order.keys()]


def list_available_names() -> List[str]:
    """Return the set of user-facing algorithm keys (primary names)."""
    return [registration.primary_name for registration in list_registered_algorithms()]
