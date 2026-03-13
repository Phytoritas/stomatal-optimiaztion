from __future__ import annotations

import importlib
from collections.abc import Callable, Iterable

from stomatal_optimiaztion.domains.thorp.traceability import (
    EquationMapping,
    build_mapping as _build_mapping,
    iter_annotated_callables as _iter_annotated_callables,
)

_MODULES = [
    importlib.import_module("stomatal_optimiaztion.domains.thorp.soil_hydraulics"),
    importlib.import_module("stomatal_optimiaztion.domains.thorp.soil_initialization"),
    importlib.import_module("stomatal_optimiaztion.domains.thorp.soil_dynamics"),
    importlib.import_module("stomatal_optimiaztion.domains.thorp.hydraulics"),
    importlib.import_module("stomatal_optimiaztion.domains.thorp.allocation"),
    importlib.import_module("stomatal_optimiaztion.domains.thorp.growth"),
    importlib.import_module("stomatal_optimiaztion.domains.thorp.radiation"),
]


def iter_annotated_callables() -> Iterable[Callable[..., object]]:
    for module in _MODULES:
        yield from _iter_annotated_callables(vars(module))


def build_mapping() -> EquationMapping:
    return _build_mapping(iter_annotated_callables())


__all__ = ["EquationMapping", "build_mapping", "iter_annotated_callables"]
