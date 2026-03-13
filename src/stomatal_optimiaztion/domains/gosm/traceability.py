from __future__ import annotations

import inspect
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass

from stomatal_optimiaztion.domains.gosm.implements import implemented_equations, qualname


@dataclass(frozen=True, slots=True)
class EquationMapping:
    equation_to_callables: dict[str, set[str]]
    callable_to_equations: dict[str, tuple[str, ...]]


def iter_annotated_callables(namespace: Mapping[str, object]) -> Iterator[Callable[..., object]]:
    """Yield annotated callables from a module-like namespace."""

    for obj in namespace.values():
        if callable(obj) and implemented_equations(obj):
            yield obj

        if inspect.isclass(obj):
            for member in vars(obj).values():
                if callable(member) and implemented_equations(member):
                    yield member


def build_mapping(callables: Iterable[Callable[..., object]]) -> EquationMapping:
    equation_to_callables: dict[str, set[str]] = defaultdict(set)
    callable_to_equations: dict[str, tuple[str, ...]] = {}

    for fn in callables:
        equation_ids = implemented_equations(fn)
        if not equation_ids:
            continue

        callable_name = qualname(fn)
        callable_to_equations[callable_name] = equation_ids
        for equation_id in equation_ids:
            equation_to_callables[equation_id].add(callable_name)

    return EquationMapping(
        equation_to_callables=dict(equation_to_callables),
        callable_to_equations=callable_to_equations,
    )

