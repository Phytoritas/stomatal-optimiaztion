from __future__ import annotations

import math
from typing import Any, Mapping

import numpy as np
import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.constraints import (
    apply_tomato_constraints,
    normalize_allocation_fractions,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.contracts import (
    ORGAN_NAMES,
    PRIOR_FAMILIES,
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
    return float(min(max(float(value), low), high))


def _source_strength(row: Mapping[str, Any]) -> float:
    source = _finite(row.get("source_proxy_MJ_CO2_T"), default=np.nan)
    radiation = _finite(row.get("day_radiation_integral_MJ_m2"), default=np.nan)
    if math.isfinite(source) and source > 0:
        return _clip(source / (source + 10.0), 0.0, 1.0)
    if math.isfinite(radiation) and radiation > 0:
        return _clip(radiation / (radiation + 10.0), 0.0, 1.0)
    return 0.35


def _legacy_raw(row: Mapping[str, Any]) -> dict[str, float]:
    source = _source_strength(row)
    rzi = _clip(_finite(row.get("RZI_main"), default=0.0), 0.0, 1.0)
    lai_proxy = _finite(row.get("LAI_proxy_value"), default=np.nan)
    lai_low = math.isfinite(lai_proxy) and lai_proxy < 3.0

    fruit = 0.55 + 0.08 * (source - 0.5) - 0.05 * rzi
    if lai_low:
        fruit -= 0.03
    fruit = _clip(fruit, 0.45, 0.68)
    veg = max(1.0 - fruit, 0.0)
    leaf_share = 0.45 + (0.08 if lai_low else 0.0)
    stem_share = 0.35
    root_share = 0.20 + 0.15 * max(rzi - 0.15, 0.0)
    total = leaf_share + stem_share + root_share
    return normalize_allocation_fractions(
        {
            "fruit": fruit,
            "leaf": veg * leaf_share / total,
            "stem": veg * stem_share / total,
            "root": veg * root_share / total,
        }
    )


def legacy_tomato_prior(row: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    raw = _legacy_raw(row)
    constraint_row = dict(row)
    constraint_row.update({"legacy_prior_u_fruit": raw["fruit"], "legacy_prior_u_root": raw["root"]})
    constrained = apply_tomato_constraints(raw, constraint_row, config)
    return _prior_payload(
        "legacy_tomato_prior",
        constrained,
        status="ok",
        warning="",
        legacy_reference=constrained,
    )


def thorp_bounded_prior(row: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    latent_cfg = as_dict(config.get("latent_allocation"))
    thorp_cfg = as_dict(latent_cfg.get("thorp"))
    legacy = _legacy_raw(row)
    rzi = _clip(_finite(row.get("RZI_main"), default=0.0), 0.0, 1.0)
    max_correction = abs(_finite(thorp_cfg.get("root_hydraulic_correction_max_abs", 0.08), default=0.08))
    stress_gate = _clip((rzi - 0.15) / 0.85, 0.0, 1.0)
    root_correction = max_correction * stress_gate

    fruit = legacy["fruit"]
    veg = max(1.0 - fruit, 0.0)
    legacy_veg_root = legacy["root"] / max(veg, 1e-9)
    root_share = _clip(legacy_veg_root + root_correction, 0.0, 0.60)
    leaf_stem_share = max(1.0 - root_share, 0.0)
    leaf_fraction = 0.58 if bool(row.get("LAI_proxy_available", False)) else 0.56
    raw = normalize_allocation_fractions(
        {
            "fruit": fruit,
            "leaf": veg * leaf_stem_share * leaf_fraction,
            "stem": veg * leaf_stem_share * (1.0 - leaf_fraction),
            "root": veg * root_share,
        }
    )
    constraint_row = dict(row)
    constraint_row.update({"legacy_prior_u_fruit": legacy["fruit"], "legacy_prior_u_root": legacy["root"]})
    constrained = apply_tomato_constraints(raw, constraint_row, config)
    return _prior_payload(
        "thorp_bounded_prior",
        constrained,
        status="ok",
        warning="THORP used only as bounded vegetative hydraulic correction.",
        legacy_reference=legacy,
    )


def tomato_constrained_thorp_prior(row: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    legacy = _legacy_raw(row)
    bounded = thorp_bounded_prior(row, config)
    veg = max(1.0 - legacy["fruit"], 0.0)
    bounded_leaf = _finite(bounded["u_leaf_prior"])
    bounded_stem = _finite(bounded["u_stem_prior"])
    bounded_root = _finite(bounded["u_root_prior"])
    veg_total = max(bounded_leaf + bounded_stem + bounded_root, 1e-9)
    raw = normalize_allocation_fractions(
        {
            "fruit": legacy["fruit"],
            "leaf": veg * bounded_leaf / veg_total,
            "stem": veg * bounded_stem / veg_total,
            "root": veg * bounded_root / veg_total,
        }
    )
    constraint_row = dict(row)
    constraint_row.update({"legacy_prior_u_fruit": legacy["fruit"], "legacy_prior_u_root": legacy["root"]})
    constrained = apply_tomato_constraints(raw, constraint_row, config)
    return _prior_payload(
        "tomato_constrained_thorp_prior",
        constrained,
        status="ok",
        warning="Tomato fruit gate preserved; bounded THORP acts only inside residual vegetative split.",
        legacy_reference=legacy,
    )


def _prior_payload(
    family: str,
    values: Mapping[str, float],
    *,
    status: str,
    warning: str,
    legacy_reference: Mapping[str, float],
) -> dict[str, Any]:
    normalized = normalize_allocation_fractions(values)
    total = sum(normalized.values())
    payload: dict[str, Any] = {
        "prior_family": family,
        "prior_status": status,
        "prior_warning": warning,
        "prior_sum_error": abs(total - 1.0),
    }
    for organ in ORGAN_NAMES:
        payload[f"u_{organ}_prior"] = normalized[organ]
        payload[f"legacy_prior_u_{organ}"] = float(legacy_reference[organ])
    return payload


def validate_prior_families(requested: tuple[str, ...]) -> tuple[str, ...]:
    known = set(PRIOR_FAMILIES)
    requested_set = set(requested)
    unknown = sorted(requested_set - known)
    missing = [family for family in PRIOR_FAMILIES if family not in requested_set]
    if unknown or missing:
        parts = []
        if unknown:
            parts.append(f"unknown prior families: {unknown}")
        if missing:
            parts.append(f"missing required prior families: {missing}")
        raise ValueError("; ".join(parts))
    return tuple(family for family in PRIOR_FAMILIES if family in requested_set)


def build_latent_allocation_priors(
    input_state: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    latent_cfg = as_dict(config.get("latent_allocation"))
    requested = tuple(str(item) for item in latent_cfg.get("prior_families", PRIOR_FAMILIES))
    requested = validate_prior_families(requested)
    rows: list[dict[str, Any]] = []
    builders = {
        "legacy_tomato_prior": legacy_tomato_prior,
        "thorp_bounded_prior": thorp_bounded_prior,
        "tomato_constrained_thorp_prior": tomato_constrained_thorp_prior,
    }
    for _, state_row in input_state.iterrows():
        base = state_row.to_dict()
        legacy = _legacy_raw(base)
        base["legacy_prior_u_fruit"] = legacy["fruit"]
        base["legacy_prior_u_leaf"] = legacy["leaf"]
        base["legacy_prior_u_stem"] = legacy["stem"]
        base["legacy_prior_u_root"] = legacy["root"]
        for family in requested:
            builder = builders.get(family)
            if builder is None:
                continue
            rows.append(base | builder(base, config))
    return pd.DataFrame(rows)


__all__ = [
    "build_latent_allocation_priors",
    "legacy_tomato_prior",
    "thorp_bounded_prior",
    "tomato_constrained_thorp_prior",
    "validate_prior_families",
]
