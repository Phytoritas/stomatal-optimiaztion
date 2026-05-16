from __future__ import annotations

from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.contracts import (
    DIRECT_VALIDATION_STATEMENT,
)


def _available(frame: pd.DataFrame, columns: tuple[str, ...]) -> bool:
    return all(column in frame.columns for column in columns) and frame[list(columns)].notna().any().any()


def compute_observer_support_scores(input_state: pd.DataFrame, metadata: dict[str, Any]) -> dict[str, Any]:
    radiation_available = _available(input_state, ("radiation_day_ET_g", "radiation_night_ET_g"))
    rootzone_available = _available(input_state, ("RZI_main",))
    conductance_available = bool(input_state.get("apparent_canopy_conductance_available", pd.Series(dtype=bool)).any())
    fruit_available = _available(input_state, ("radiation_day_net_mm",)) or "sensor_column" in input_state.columns
    leaf_available = _available(input_state, ("leaf_temp_lc4_radiation_day_mean_c",)) or _available(
        input_state,
        ("delta_leaf_temp_lc4_minus_lc1_radiation_day_mean_c",),
    )
    dataset3_available = str(metadata.get("Dataset3_mapping_confidence", "")).startswith("direct_loadcell") or _available(
        input_state,
        ("stem_diameter_mean",),
    )
    lai_available = bool(input_state.get("LAI_available", pd.Series(dtype=bool)).any())
    lai_proxy_available = bool(input_state.get("LAI_proxy_available", pd.Series(dtype=bool)).any())
    harvest_yield_available = bool(metadata.get("harvest_yield_available", False))
    direct_partition = bool(metadata.get("direct_partition_observation_available", False))

    observer_group_count = sum(
        bool(value)
        for value in (
            radiation_available,
            rootzone_available,
            conductance_available,
            fruit_available,
            leaf_available,
            dataset3_available,
            lai_available or lai_proxy_available,
        )
    )
    if direct_partition:
        score = "high"
    elif radiation_available and rootzone_available and conductance_available:
        score = "medium"
    elif observer_group_count >= 2:
        score = "low"
    else:
        score = "low"
    return {
        "allocation_identifiability_score": score,
        "direct_partition_observation_available": direct_partition,
        "observer_group_count": int(observer_group_count),
        "radiation_daynight_et_available": radiation_available,
        "rootzone_rzi_available": rootzone_available,
        "apparent_conductance_available": conductance_available,
        "fruit_observer_available": fruit_available,
        "leaf_temp_observer_available": leaf_available,
        "dataset3_structural_observer_available": dataset3_available,
        "LAI_available": lai_available,
        "LAI_proxy_available": lai_proxy_available,
        "harvest_yield_available": harvest_yield_available,
        "latent_allocation_directly_validated": False,
        "identifiability_interpretation": "not_direct_validation",
        "diagnostic_statement": DIRECT_VALIDATION_STATEMENT,
    }


def compute_allocation_identifiability(input_state: pd.DataFrame, metadata: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame([compute_observer_support_scores(input_state, metadata)])


def compute_prior_family_diagnostics(priors: pd.DataFrame, posteriors: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for family, group in posteriors.groupby("prior_family", dropna=False):
        prior_group = priors[priors["prior_family"].eq(family)] if "prior_family" in priors.columns else pd.DataFrame()
        rows.append(
            {
                "prior_family": family,
                "row_count": int(group.shape[0]),
                "max_allocation_sum_error": float(group["allocation_sum_error"].abs().max()) if not group.empty else 0.0,
                "mean_inferred_u_fruit": float(group["inferred_u_fruit"].mean()) if not group.empty else 0.0,
                "mean_inferred_u_leaf": float(group["inferred_u_leaf"].mean()) if not group.empty else 0.0,
                "mean_inferred_u_stem": float(group["inferred_u_stem"].mean()) if not group.empty else 0.0,
                "mean_inferred_u_root": float(group["inferred_u_root"].mean()) if not group.empty else 0.0,
                "prior_status": ";".join(sorted(set(prior_group.get("prior_status", pd.Series(dtype=str)).astype(str)))),
                "diagnostic_statement": DIRECT_VALIDATION_STATEMENT,
            }
        )
    return pd.DataFrame(rows)


__all__ = [
    "compute_allocation_identifiability",
    "compute_observer_support_scores",
    "compute_prior_family_diagnostics",
]
