from __future__ import annotations

from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def implements(*equation_ids: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Attach model-card equation ids implemented by a callable."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        merged = list(implemented_equations(func))
        for equation_id in equation_ids:
            if equation_id and equation_id not in merged:
                merged.append(equation_id)
        setattr(func, "__gosm_equations__", tuple(merged))
        return func

    return decorator


def implemented_equations(func: Callable[..., object]) -> tuple[str, ...]:
    equation_ids = getattr(func, "__gosm_equations__", ())
    if not isinstance(equation_ids, tuple):
        return ()
    return tuple(
        equation_id
        for equation_id in equation_ids
        if isinstance(equation_id, str) and equation_id
    )


def qualname(func: Callable[..., object]) -> str:
    module_name = getattr(func, "__module__", "<unknown>")
    callable_name = getattr(func, "__qualname__", "<unknown>")
    return f"{module_name}.{callable_name}"

