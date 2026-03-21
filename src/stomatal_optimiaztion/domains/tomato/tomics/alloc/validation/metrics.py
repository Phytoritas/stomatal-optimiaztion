from __future__ import annotations

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_operator import (
    daily_last,
    model_floor_area_cumulative_total_fruit,
    observed_floor_area_yield,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.knu_data import PLANTS_PER_M2
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.observation_model import (
    REPORTING_BASIS_FLOOR_AREA,
    ValidationSeriesBundle,
    compute_validation_bundle,
    harvest_timing_mae_days,
    merge_validation_series,
)


def to_floor_area_value(value: float, *, basis: str, plants_per_m2: float = PLANTS_PER_M2) -> float:
    key = str(basis).strip().lower()
    if key in {"floor_area", "floor_area_g_m2", "g/m^2", "g m^-2", "g/m2"}:
        return float(value)
    if key in {"per_plant", "g/plant"}:
        return float(value) * float(plants_per_m2)
    raise ValueError(f"Unsupported reporting basis {basis!r}.")


def canopy_collapse_days(
    df: pd.DataFrame,
    *,
    lai_floor: float = 2.0,
    leaf_floor: float = 0.18,
) -> int:
    if df.empty:
        return 0
    work = df.copy()
    work["date"] = pd.to_datetime(work["datetime"]).dt.normalize()
    active = (pd.to_numeric(work.get("active_trusses"), errors="coerce").fillna(0.0) > 0.0) | (
        pd.to_numeric(work.get("fruit_dry_weight_g_m2"), errors="coerce").fillna(0.0) > 0.0
    )
    collapse = active & (
        (pd.to_numeric(work.get("LAI"), errors="coerce").fillna(0.0) < lai_floor)
        | (pd.to_numeric(work.get("alloc_frac_leaf"), errors="coerce").fillna(0.0) < leaf_floor)
    )
    return int(collapse.groupby(work["date"]).any().sum())


__all__ = [
    "REPORTING_BASIS_FLOOR_AREA",
    "ValidationSeriesBundle",
    "canopy_collapse_days",
    "compute_validation_bundle",
    "daily_last",
    "harvest_timing_mae_days",
    "merge_validation_series",
    "model_floor_area_cumulative_total_fruit",
    "observed_floor_area_yield",
    "to_floor_area_value",
]
