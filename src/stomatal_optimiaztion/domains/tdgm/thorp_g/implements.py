from __future__ import annotations

from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def implements(*equation_ids: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Attach equation ids implemented by this callable (THORP-G subpackage).

    Note: Unlike THORP/TDGM core, THORP-G v1.4 does not (yet) have a dedicated
    model_card in this repo, so these ids are not validated by tests.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        existing = getattr(func, "__thorp_g_equations__", ())
        merged = list(existing) if isinstance(existing, tuple) else []
        for eq in equation_ids:
            if eq not in merged:
                merged.append(eq)
        setattr(func, "__thorp_g_equations__", tuple(merged))
        return func

    return decorator


def implemented_equations(func: Callable[..., object]) -> tuple[str, ...]:
    ids = getattr(func, "__thorp_g_equations__", ())
    if not isinstance(ids, tuple):
        return ()
    return tuple(x for x in ids if isinstance(x, str) and x)


def qualname(func: Callable[..., object]) -> str:
    return f"{getattr(func, '__module__', '<unknown>')}.{getattr(func, '__qualname__', '<unknown>')}"

