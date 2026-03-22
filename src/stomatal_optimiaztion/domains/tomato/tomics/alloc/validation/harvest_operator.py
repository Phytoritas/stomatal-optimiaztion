from __future__ import annotations

import pandas as pd


def daily_last(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work = work.dropna(subset=["datetime"]).sort_values("datetime")
    work["date"] = work["datetime"].dt.normalize()
    return work.groupby("date", as_index=False).last()


def _daily_increment_from_cumulative(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.diff()


def model_floor_area_cumulative_total_fruit(model_df: pd.DataFrame) -> pd.DataFrame:
    daily = daily_last(model_df)
    fruit = pd.to_numeric(daily.get("fruit_dry_weight_g_m2"), errors="coerce").fillna(0.0)
    harvested = pd.to_numeric(daily.get("harvested_fruit_g_m2"), errors="coerce").fillna(0.0)
    total_system = fruit + harvested
    out = pd.DataFrame(
        {
            "date": daily["date"],
            "model_onplant_fruit_dry_weight_floor_area": fruit,
            "model_harvested_fruit_floor_area": harvested,
            "model_cumulative_harvested_fruit_dry_weight_floor_area": harvested,
            "model_observed_target_proxy_floor_area": harvested,
            "model_total_system_fruit_dry_weight_floor_area": total_system,
            "model_cumulative_total_fruit_dry_weight_floor_area": harvested,
            "model_total_latent_fruit_dry_weight_floor_area": total_system,
        }
    )
    out["model_daily_increment_floor_area"] = _daily_increment_from_cumulative(
        out["model_cumulative_harvested_fruit_dry_weight_floor_area"]
    )
    return out


def observed_floor_area_yield(
    yield_df: pd.DataFrame,
    *,
    measured_column: str,
    estimated_column: str,
) -> pd.DataFrame:
    observed = pd.DataFrame(
        {
            "date": pd.to_datetime(yield_df.iloc[:, 0], errors="coerce").dt.normalize(),
            "measured_cumulative_harvested_fruit_dry_weight_floor_area": pd.to_numeric(
                yield_df[measured_column],
                errors="coerce",
            ),
            "estimated_cumulative_harvested_fruit_dry_weight_floor_area": pd.to_numeric(
                yield_df[estimated_column],
                errors="coerce",
            ),
        }
    ).dropna(subset=["date"])
    observed["measured_cumulative_total_fruit_dry_weight_floor_area"] = observed[
        "measured_cumulative_harvested_fruit_dry_weight_floor_area"
    ]
    observed["estimated_cumulative_total_fruit_dry_weight_floor_area"] = observed[
        "estimated_cumulative_harvested_fruit_dry_weight_floor_area"
    ]
    observed["measured_daily_increment_floor_area"] = _daily_increment_from_cumulative(
        observed["measured_cumulative_harvested_fruit_dry_weight_floor_area"]
    )
    observed["estimated_daily_increment_floor_area"] = _daily_increment_from_cumulative(
        observed["estimated_cumulative_harvested_fruit_dry_weight_floor_area"]
    )
    return observed.reset_index(drop=True)


__all__ = [
    "daily_last",
    "model_floor_area_cumulative_total_fruit",
    "observed_floor_area_yield",
]
