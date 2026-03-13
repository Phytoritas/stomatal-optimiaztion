from __future__ import annotations

import importlib
from collections.abc import Callable, Iterable

from stomatal_optimiaztion.domains.tdgm.traceability import (
    EquationMapping,
    build_mapping as _build_mapping,
    iter_annotated_callables as _iter_annotated_callables,
)

_MODULES = [
    importlib.import_module("stomatal_optimiaztion.domains.tdgm.ptm"),
    importlib.import_module("stomatal_optimiaztion.domains.tdgm.turgor_growth"),
    importlib.import_module("stomatal_optimiaztion.domains.tdgm.coupling"),
]


def iter_annotated_callables() -> Iterable[Callable[..., object]]:
    for module in _MODULES:
        yield from _iter_annotated_callables(vars(module))


def build_mapping() -> EquationMapping:
    return _build_mapping(iter_annotated_callables())


__all__ = ["EquationMapping", "build_mapping", "iter_annotated_callables"]
