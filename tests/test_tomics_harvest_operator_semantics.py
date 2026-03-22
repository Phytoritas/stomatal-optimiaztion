from __future__ import annotations

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_operator import (
    model_floor_area_cumulative_total_fruit,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.observation_model import (
    compute_validation_bundle,
    resolve_validation_series_columns,
)


def test_harvest_operator_exports_explicit_harvested_and_total_system_columns() -> None:
    run_df = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2024-08-08", "2024-08-09", "2024-08-10"]),
            "fruit_dry_weight_g_m2": [4.0, 6.0, 7.0],
            "harvested_fruit_g_m2": [0.0, 5.0, 9.0],
        }
    )

    observed = model_floor_area_cumulative_total_fruit(run_df)

    assert observed["model_cumulative_harvested_fruit_dry_weight_floor_area"].tolist() == [0.0, 5.0, 9.0]
    assert observed["model_total_system_fruit_dry_weight_floor_area"].tolist() == [4.0, 11.0, 16.0]
    assert observed["model_observed_target_proxy_floor_area"].tolist() == [0.0, 5.0, 9.0]
    assert observed["model_cumulative_total_fruit_dry_weight_floor_area"].tolist() == [0.0, 5.0, 9.0]


def test_validation_bundle_prefers_explicit_harvested_cumulative_column() -> None:
    observed_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-08-08", "2024-08-09", "2024-08-10"]),
            "measured_cumulative_total_fruit_dry_weight_floor_area": [0.0, 3.0, 5.0],
            "measured_daily_increment_floor_area": [pd.NA, 3.0, 2.0],
        }
    )

    bundle = compute_validation_bundle(
        observed_df,
        candidate_series=pd.Series([0.0, 2.5, 5.5], dtype=float),
        candidate_daily_increment_series=pd.Series([float("nan"), 2.5, 3.0], dtype=float),
        candidate_label="model",
        unit_declared_in_observation_file="g/m^2",
    )

    cumulative_column, _, _ = resolve_validation_series_columns(bundle.merged_df, source_label="model")

    assert cumulative_column == "model_cumulative_harvested_fruit_dry_weight_floor_area"
    assert "model_cumulative_harvested_fruit_dry_weight_floor_area" in bundle.merged_df.columns
