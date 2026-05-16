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


def _evidence_deltas(row: Mapping[str, Any]) -> dict[str, float]:
    source = _finite(row.get("source_proxy_MJ_CO2_T"), default=np.nan)
    radiation = _finite(row.get("day_radiation_integral_MJ_m2"), default=np.nan)
    source_strength = 0.0
    if math.isfinite(source):
        source_strength = _clip(source / (source + 10.0) - 0.5, -0.5, 0.5)
    elif math.isfinite(radiation):
        source_strength = _clip(radiation / (radiation + 10.0) - 0.5, -0.5, 0.5)

    rzi = _clip(_finite(row.get("RZI_main"), default=0.0), 0.0, 1.0)
    conductance_available = bool(row.get("apparent_canopy_conductance_available", False))
    conductance = _finite(row.get("apparent_canopy_conductance"), default=np.nan)
    conductance_signal = 0.0
    if conductance_available and math.isfinite(conductance):
        conductance_signal = _clip(conductance / (abs(conductance) + 100.0), -0.3, 0.3)
    day_fraction_et = _clip(_finite(row.get("day_fraction_ET"), default=0.5), 0.0, 1.0) - 0.5

    lai_proxy_value = _finite(row.get("LAI_proxy_value"), default=np.nan)
    lai_deficit = 0.0
    if bool(row.get("LAI_proxy_available", False)) and math.isfinite(lai_proxy_value):
        lai_deficit = _clip((3.0 - lai_proxy_value) / 3.0, 0.0, 1.0)

    dataset3_support = 0.05 if str(row.get("Dataset3_mapping_confidence", "")).startswith("direct_loadcell") else 0.0
    return {
        "fruit": 0.20 * source_strength + 0.08 * day_fraction_et - 0.08 * rzi,
        "leaf": 0.12 * lai_deficit + 0.04 * conductance_signal,
        "stem": dataset3_support + 0.03 * source_strength,
        "root": 0.22 * max(rzi - 0.15, 0.0) - 0.05 * max(0.05 - rzi, 0.0),
    }


def _softmax_from_prior(prior: Mapping[str, float], deltas: Mapping[str, float], beta: float) -> dict[str, float]:
    weighted: dict[str, float] = {}
    safe_beta = max(float(beta), 0.0)
    for organ in ORGAN_NAMES:
        base = max(_finite(prior.get(organ), default=0.0), 1e-9)
        weighted[organ] = base * math.exp(safe_beta * _finite(deltas.get(organ), default=0.0))
    return normalize_allocation_fractions(weighted)


def infer_latent_allocation(priors: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    if priors.empty:
        return pd.DataFrame()
    latent_cfg = as_dict(config.get("latent_allocation"))
    alpha = _clip(_finite(latent_cfg.get("low_pass_alpha", 0.35), default=0.35), 0.0, 1.0)
    low_pass_enabled = bool(latent_cfg.get("low_pass_memory_enabled", True))
    beta = _finite(latent_cfg.get("softmax_beta", 1.0), default=1.0)

    rows: list[dict[str, Any]] = []
    memory: dict[tuple[object, object, object], dict[str, float]] = {}
    sort_columns = [column for column in ("prior_family", "loadcell_id", "treatment", "date") if column in priors.columns]
    ordered = priors.sort_values(sort_columns).reset_index(drop=True)
    for _, row in ordered.iterrows():
        base = row.to_dict()
        prior = {organ: _finite(base.get(f"u_{organ}_prior"), default=0.0) for organ in ORGAN_NAMES}
        raw = _softmax_from_prior(prior, _evidence_deltas(base), beta=beta)
        constrained = apply_tomato_constraints(raw, base, config)

        group_key = (
            base.get("loadcell_id"),
            base.get("treatment"),
            base.get("prior_family"),
        )
        previous = memory.get(group_key)
        if low_pass_enabled and previous is not None:
            low_pass = normalize_allocation_fractions(
                {
                    organ: alpha * constrained[organ] + (1.0 - alpha) * previous[organ]
                    for organ in ORGAN_NAMES
                }
            )
            low_pass = apply_tomato_constraints(low_pass, base, config)
        else:
            low_pass = constrained
        memory[group_key] = dict(low_pass)

        out = {
            key: base.get(key)
            for key in (
                "date",
                "loadcell_id",
                "treatment",
                "threshold_w_m2",
                "prior_family",
                "RZI_main",
                "apparent_canopy_conductance",
                "source_proxy_MJ_CO2_T",
                "LAI_available",
                "LAI_proxy_available",
                "LAI_proxy_value",
                "direct_partition_observation_available",
                "allocation_validation_basis",
            )
        }
        for organ in ORGAN_NAMES:
            out[f"raw_u_{organ}_before_constraints"] = raw[organ]
            out[f"constrained_u_{organ}"] = constrained[organ]
            out[f"low_pass_u_{organ}"] = low_pass[organ]
            out[f"inferred_u_{organ}"] = low_pass[organ]
            out[f"u_{organ}_prior"] = prior[organ]
            out[f"legacy_prior_u_{organ}"] = _finite(base.get(f"legacy_prior_u_{organ}"), default=prior[organ])
        allocation_sum = sum(low_pass.values())
        out["allocation_sum"] = allocation_sum
        out["allocation_sum_error"] = abs(allocation_sum - 1.0)
        out["latent_allocation_directly_validated"] = False
        out["promotable_by_latent_allocation_alone"] = False
        out["raw_THORP_allocator_used"] = False
        rows.append(out)
    return pd.DataFrame(rows).sort_values(
        [column for column in ("date", "loadcell_id", "prior_family") if column in priors.columns]
    ).reset_index(drop=True)


__all__ = ["infer_latent_allocation"]
