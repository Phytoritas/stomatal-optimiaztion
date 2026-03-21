from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import write_json


def _finite(row: pd.Series, key: str, default: float) -> float:
    value = pd.to_numeric(pd.Series([row.get(key, default)]), errors="coerce").iloc[0]
    if pd.isna(value):
        return float(default)
    return float(value)


def score_harvest_row(row: pd.Series) -> float:
    if int(row.get("invalid_run_flag", 0)) or int(row.get("nonfinite_flag", 0)):
        return -1_000_000.0
    return float(
        -1.4 * _finite(row, "rmse_cumulative_offset", 1_000.0)
        -0.9 * _finite(row, "rmse_daily_increment", 1_000.0)
        -0.6 * abs(_finite(row, "final_cumulative_bias", 1_000.0))
        -0.4 * _finite(row, "harvest_timing_mae_days", 100.0)
        -1.0 * _finite(row, "harvest_mass_balance_error", 100.0)
        -0.4 * _finite(row, "leaf_harvest_mass_balance_error", 100.0)
        -10.0 * _finite(row, "canopy_collapse_days", 10.0)
        -20.0 * _finite(row, "wet_condition_root_excess_penalty", 1.0)
    )


def rank_harvest_candidates(
    metrics_df: pd.DataFrame,
    *,
    candidate_columns: list[str] | None = None,
    stages: list[str] | None = None,
) -> pd.DataFrame:
    frame = metrics_df.copy()
    if frame.empty:
        return pd.DataFrame()
    if "score" not in frame.columns:
        frame["score"] = frame.apply(score_harvest_row, axis=1)
    if stages:
        frame = frame[frame["stage"].isin(stages)].copy()
    candidate_columns = candidate_columns or [
        "allocator_family",
        "fruit_harvest_family",
        "leaf_harvest_family",
        "fdmc_mode",
    ]
    grouped = (
        frame.groupby(candidate_columns, dropna=False, as_index=False)
        .agg(
            mean_score=("score", "mean"),
            mean_rmse_cumulative_offset=("rmse_cumulative_offset", "mean"),
            mean_rmse_daily_increment=("rmse_daily_increment", "mean"),
            max_harvest_mass_balance_error=("harvest_mass_balance_error", "max"),
            max_canopy_collapse_days=("canopy_collapse_days", "max"),
            run_count=("score", "count"),
        )
        .sort_values(["mean_score", "mean_rmse_cumulative_offset"], ascending=[False, True])
        .reset_index(drop=True)
    )
    return grouped


def write_selected_harvest_family(
    *,
    output_path: Path,
    selected_payload: dict[str, Any],
) -> None:
    write_json(output_path, selected_payload)


__all__ = ["rank_harvest_candidates", "score_harvest_row", "write_selected_harvest_family"]
