from __future__ import annotations

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_operator import (
    model_floor_area_cumulative_total_fruit,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.observation_model import (
    compute_validation_bundle,
    resolve_validation_series_columns,
)


def test_compute_validation_bundle_writes_explicit_harvested_candidate_columns() -> None:
    observed_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-08-08", "2024-08-09"]),
            "measured_cumulative_harvested_fruit_dry_weight_floor_area": [0.0, 5.0],
            "measured_daily_increment_floor_area": [pd.NA, 5.0],
        }
    )

    bundle = compute_validation_bundle(
        observed_df,
        candidate_series=pd.Series([0.0, 4.0], dtype=float),
        candidate_daily_increment_series=pd.Series([float("nan"), 4.0], dtype=float),
        candidate_label="model",
        unit_declared_in_observation_file="g/m^2",
    )

    assert "model_cumulative_harvested_fruit_dry_weight_floor_area" in bundle.merged_df.columns
    assert "model_daily_harvest_increment_floor_area" in bundle.merged_df.columns
    assert bundle.merged_df["model_cumulative_harvested_fruit_dry_weight_floor_area"].tolist() == [0.0, 4.0]


def test_validation_overlay_resolution_prefers_explicit_harvested_columns() -> None:
    validation_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-08-08", "2024-08-09"]),
            "model_cumulative_harvested_fruit_dry_weight_floor_area": [5.0, 7.0],
            "model_cumulative_total_fruit_dry_weight_floor_area": [50.0, 70.0],
            "model_offset_adjusted": [0.0, 2.0],
            "model_daily_harvest_increment_floor_area": [pd.NA, 2.0],
            "model_daily_increment_floor_area": [pd.NA, 20.0],
        }
    )

    cumulative_column, offset_column, increment_column = resolve_validation_series_columns(
        validation_df,
        source_label="model",
    )

    assert cumulative_column == "model_cumulative_harvested_fruit_dry_weight_floor_area"
    assert offset_column == "model_offset_adjusted"
    assert increment_column == "model_daily_harvest_increment_floor_area"


def test_deprecated_total_alias_tracks_total_system_mass_while_target_proxy_stays_harvested() -> None:
    run_df = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2024-08-08", "2024-08-09"]),
            "fruit_dry_weight_g_m2": [4.0, 6.0],
            "harvested_fruit_g_m2": [0.0, 5.0],
        }
    )

    model_df = model_floor_area_cumulative_total_fruit(run_df)

    assert model_df["model_observed_target_proxy_floor_area"].tolist() == [0.0, 5.0]
    assert model_df["model_total_system_fruit_dry_weight_floor_area"].tolist() == [4.0, 11.0]
    assert model_df["model_cumulative_total_fruit_dry_weight_floor_area"].tolist() == [4.0, 11.0]
