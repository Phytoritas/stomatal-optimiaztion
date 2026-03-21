from __future__ import annotations

import math
from typing import Iterable


def normalize_prior(weights: Iterable[float]) -> tuple[float, float, float]:
    values = [max(float(weight), 0.0) for weight in weights]
    total = sum(values)
    if total <= 1e-12:
        return 0.70, 0.20, 0.10
    return tuple(value / total for value in values)  # type: ignore[return-value]


def prior_weighted_softmax(
    *,
    prior: tuple[float, float, float],
    deltas: tuple[float, float, float],
    beta: float,
) -> tuple[float, float, float]:
    safe_beta = max(float(beta), 0.0)
    weighted = []
    for base, delta in zip(prior, deltas, strict=True):
        weighted.append(max(base, 1e-9) * math.exp(safe_beta * float(delta)))
    total = sum(weighted)
    if total <= 1e-12:
        return prior
    return tuple(value / total for value in weighted)  # type: ignore[return-value]


def lowpass_allocation(
    *,
    current: tuple[float, float, float],
    target: tuple[float, float, float],
    dt_days: float,
    tau_days: float,
) -> tuple[float, float, float]:
    if tau_days <= 1e-12:
        return target
    alpha = 1.0 - math.exp(-max(float(dt_days), 0.0) / max(float(tau_days), 1e-12))
    mixed = tuple(
        float(cur) + alpha * (float(tgt) - float(cur))
        for cur, tgt in zip(current, target, strict=True)
    )
    return normalize_prior(mixed)


__all__ = ["lowpass_allocation", "normalize_prior", "prior_weighted_softmax"]
