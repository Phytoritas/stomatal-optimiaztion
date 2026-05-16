from __future__ import annotations

import math
from typing import Any, Mapping

import numpy as np
import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.contracts import (
    ORGAN_NAMES,
    allocation_bounds,
    as_dict,
)


def _finite(value: object, *, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(result):
        return float(default)
    return result


def _clip(value: float, low: float, high: float) -> float:
    return float(min(max(float(value), float(low)), float(high)))


def normalize_allocation_fractions(values: Mapping[str, float]) -> dict[str, float]:
    cleaned = {organ: max(_finite(values.get(organ), default=0.0), 0.0) for organ in ORGAN_NAMES}
    total = sum(cleaned.values())
    if total <= 1e-12:
        cleaned = {"fruit": 0.55, "leaf": 0.20, "stem": 0.16, "root": 0.09}
        total = 1.0
    return {organ: value / total for organ, value in cleaned.items()}


def apply_wet_root_cap(values: Mapping[str, float], row: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, float]:
    bounds = allocation_bounds(config)
    latent_cfg = as_dict(config.get("latent_allocation"))
    stress_cfg = as_dict(latent_cfg.get("stress_gates"))
    wet_threshold = _finite(stress_cfg.get("wet_rzi_threshold", 0.05), default=0.05)
    rzi = _finite(row.get("RZI_main"), default=0.0)
    capped = dict(values)
    cap = bounds.wet_root_cap if rzi <= wet_threshold else bounds.root_cap
    capped["root"] = min(_finite(capped.get("root"), default=0.0), cap)
    return normalize_allocation_fractions(capped)


def apply_root_stress_gate(
    values: Mapping[str, float],
    row: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, float]:
    latent_cfg = as_dict(config.get("latent_allocation"))
    stress_cfg = as_dict(latent_cfg.get("stress_gates"))
    activation = _finite(stress_cfg.get("rzi_activation_threshold", 0.15), default=0.15)
    rzi = _finite(row.get("RZI_main"), default=0.0)
    legacy_root = _finite(row.get("legacy_prior_u_root"), default=_finite(values.get("root"), default=0.0))
    gated = dict(values)
    if rzi < activation:
        gated["root"] = min(_finite(gated.get("root"), default=0.0), legacy_root)
    return normalize_allocation_fractions(gated)


def apply_lai_protection(
    values: Mapping[str, float],
    row: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, float]:
    bounds = allocation_bounds(config)
    latent_cfg = as_dict(config.get("latent_allocation"))
    lai_cfg = as_dict(latent_cfg.get("lai"))
    if not bool(lai_cfg.get("lai_protection_enabled", True)):
        return dict(values)
    target = _finite(lai_cfg.get("target_lai", 3.0), default=3.0)
    lai_available = bool(row.get("LAI_available", False))
    proxy_available = bool(row.get("LAI_proxy_available", False))
    lai_value = _finite(row.get("LAI_proxy_value"), default=np.nan)
    protected = dict(values)
    if (not lai_available) and proxy_available and math.isfinite(lai_value) and lai_value < target:
        protected["leaf"] = max(_finite(protected.get("leaf"), default=0.0), bounds.leaf_floor)
    elif not lai_available and not proxy_available:
        protected["leaf"] = max(_finite(protected.get("leaf"), default=0.0), bounds.leaf_floor)
    return normalize_allocation_fractions(protected)


def apply_tomato_constraints(
    values: Mapping[str, float],
    row: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, float]:
    bounds = allocation_bounds(config)
    constrained = normalize_allocation_fractions(values)

    legacy_fruit = _finite(row.get("legacy_prior_u_fruit"), default=0.55)
    constrained["fruit"] = max(constrained["fruit"], min(legacy_fruit, bounds.fruit_cap))
    constrained["leaf"] = max(constrained["leaf"], bounds.leaf_floor)
    constrained["stem"] = max(constrained["stem"], bounds.stem_floor)
    constrained["root"] = max(constrained["root"], bounds.root_floor)
    constrained = normalize_allocation_fractions(constrained)

    constrained["fruit"] = _clip(constrained["fruit"], bounds.fruit_floor, bounds.fruit_cap)
    constrained["leaf"] = _clip(constrained["leaf"], bounds.leaf_floor, bounds.leaf_cap)
    constrained["stem"] = _clip(constrained["stem"], bounds.stem_floor, bounds.stem_cap)
    constrained["root"] = _clip(constrained["root"], bounds.root_floor, bounds.root_cap)
    constrained = apply_wet_root_cap(constrained, row, config)
    constrained = apply_root_stress_gate(constrained, row, config)
    constrained = apply_lai_protection(constrained, row, config)

    constrained["fruit"] = max(constrained["fruit"], min(legacy_fruit, bounds.fruit_cap))
    constrained["leaf"] = max(constrained["leaf"], bounds.leaf_floor)
    constrained["stem"] = max(constrained["stem"], bounds.stem_floor)
    constrained["root"] = min(max(constrained["root"], bounds.root_floor), bounds.root_cap)
    stress_cfg = as_dict(as_dict(config.get("latent_allocation")).get("stress_gates"))
    wet_threshold = _finite(stress_cfg.get("wet_rzi_threshold", 0.05), default=0.05)
    activation_threshold = _finite(stress_cfg.get("rzi_activation_threshold", 0.15), default=0.15)
    rzi = _finite(row.get("RZI_main"), default=0.0)
    if rzi <= wet_threshold:
        constrained["root"] = min(constrained["root"], bounds.wet_root_cap)
    final = _bounded_normalize(constrained, bounds)
    root_ceiling = bounds.root_cap
    if rzi <= wet_threshold:
        root_ceiling = min(root_ceiling, bounds.wet_root_cap)
    if rzi < activation_threshold:
        root_ceiling = min(root_ceiling, _finite(row.get("legacy_prior_u_root"), default=final["root"]))
    if final["root"] > root_ceiling:
        final = _cap_root_preserve_sum(final, bounds=bounds, root_ceiling=root_ceiling)
    fruit_floor = min(max(legacy_fruit, bounds.fruit_floor), bounds.fruit_cap)
    if final["fruit"] < fruit_floor:
        final = _floor_fruit_preserve_sum(final, bounds=bounds, fruit_floor=fruit_floor)
    return final


def _cap_root_preserve_sum(values: Mapping[str, float], *, bounds: Any, root_ceiling: float) -> dict[str, float]:
    capped = dict(values)
    excess = max(capped["root"] - root_ceiling, 0.0)
    capped["root"] = min(capped["root"], root_ceiling)
    capacities = {
        "fruit": max(bounds.fruit_cap - capped["fruit"], 0.0),
        "leaf": max(bounds.leaf_cap - capped["leaf"], 0.0),
        "stem": max(bounds.stem_cap - capped["stem"], 0.0),
    }
    total_capacity = sum(capacities.values())
    if excess > 0.0 and total_capacity > 1e-12:
        for organ in ("fruit", "leaf", "stem"):
            capped[organ] += excess * capacities[organ] / total_capacity
    total = sum(capped.values())
    if total <= 1e-12:
        return normalize_allocation_fractions(capped)
    return {organ: value / total for organ, value in capped.items()}


def _floor_fruit_preserve_sum(values: Mapping[str, float], *, bounds: Any, fruit_floor: float) -> dict[str, float]:
    floored = dict(values)
    deficit = max(fruit_floor - floored["fruit"], 0.0)
    floored["fruit"] = max(floored["fruit"], fruit_floor)
    reducible = {
        "leaf": max(floored["leaf"] - bounds.leaf_floor, 0.0),
        "stem": max(floored["stem"] - bounds.stem_floor, 0.0),
        "root": max(floored["root"] - bounds.root_floor, 0.0),
    }
    total_reducible = sum(reducible.values())
    if deficit > 0.0 and total_reducible > 1e-12:
        for organ in ("leaf", "stem", "root"):
            floored[organ] -= deficit * reducible[organ] / total_reducible
    total = sum(floored.values())
    if total <= 1e-12:
        return normalize_allocation_fractions(floored)
    return {organ: value / total for organ, value in floored.items()}


def _bounded_normalize(values: Mapping[str, float], bounds: Any) -> dict[str, float]:
    lower = {
        "fruit": bounds.fruit_floor,
        "leaf": bounds.leaf_floor,
        "stem": bounds.stem_floor,
        "root": bounds.root_floor,
    }
    upper = {
        "fruit": bounds.fruit_cap,
        "leaf": bounds.leaf_cap,
        "stem": bounds.stem_cap,
        "root": bounds.root_cap,
    }
    clipped = {organ: _clip(_finite(values.get(organ), default=0.0), lower[organ], upper[organ]) for organ in ORGAN_NAMES}
    total = sum(clipped.values())
    if total <= 1e-12:
        return dict(lower)
    normalized = {organ: value / total for organ, value in clipped.items()}
    for _ in range(8):
        changed = False
        fixed = 0.0
        flexible: list[str] = []
        for organ, value in normalized.items():
            if value < lower[organ]:
                normalized[organ] = lower[organ]
                fixed += lower[organ]
                changed = True
            elif value > upper[organ]:
                normalized[organ] = upper[organ]
                fixed += upper[organ]
                changed = True
            else:
                flexible.append(organ)
        if not changed:
            break
        remainder = max(1.0 - fixed, 0.0)
        flex_total = sum(max(_finite(values.get(organ), default=0.0), 0.0) for organ in flexible)
        if flexible and flex_total > 1e-12:
            for organ in flexible:
                normalized[organ] = remainder * max(_finite(values.get(organ), default=0.0), 0.0) / flex_total
        elif flexible:
            even = remainder / len(flexible)
            for organ in flexible:
                normalized[organ] = even
    total = sum(normalized.values())
    return {organ: value / total for organ, value in normalized.items()}


def allocation_sum_error(frame: pd.DataFrame, prefix: str = "inferred_u_") -> pd.Series:
    total = sum(pd.to_numeric(frame[f"{prefix}{organ}"], errors="coerce").fillna(0.0) for organ in ORGAN_NAMES)
    return (total - 1.0).abs()


__all__ = [
    "allocation_sum_error",
    "apply_lai_protection",
    "apply_root_stress_gate",
    "apply_tomato_constraints",
    "apply_wet_root_cap",
    "normalize_allocation_fractions",
]
