from __future__ import annotations

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_operator import (
    model_floor_area_cumulative_total_fruit,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.observation_model import (
    compute_validation_bundle,
    validation_overlay_frame,
)


def test_harvest_observation_operator_uses_harvested_mass_not_latent_total() -> None:
    run_df = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2024-08-08", "2024-08-09", "2024-08-10"]),
            "fruit_dry_weight_g_m2": [4.0, 6.0, 7.0],
            "harvested_fruit_g_m2": [0.0, 5.0, 9.0],
        }
    )
    observed = model_floor_area_cumulative_total_fruit(run_df)
    assert observed["model_cumulative_total_fruit_dry_weight_floor_area"].tolist() == [0.0, 5.0, 9.0]
    assert observed["model_total_latent_fruit_dry_weight_floor_area"].tolist() == [4.0, 11.0, 16.0]
    assert pd.isna(observed["model_daily_increment_floor_area"].iloc[0])
    assert float(observed["model_daily_increment_floor_area"].iloc[1]) == 5.0
    assert float(observed["model_daily_increment_floor_area"].iloc[2]) == 4.0


def test_validation_bundle_preserves_split_boundary_daily_increment_when_series_is_precomputed() -> None:
    observed_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-08-08", "2024-08-09", "2024-08-10"]),
            "measured_cumulative_total_fruit_dry_weight_floor_area": [0.0, 5.0, 9.0],
            "measured_daily_increment_floor_area": [pd.NA, 5.0, 4.0],
        }
    )
    full_candidate = pd.Series([0.0, 4.0, 6.0], index=observed_df.index, dtype=float)
    window = observed_df.iloc[1:].copy()
    bundle = compute_validation_bundle(
        window,
        candidate_series=full_candidate.loc[window.index],
        candidate_daily_increment_series=full_candidate.diff().loc[window.index],
        candidate_label="model",
        unit_declared_in_observation_file="g/m^2",
    )
    assert float(bundle.merged_df["model_daily_increment_floor_area"].iloc[0]) == 4.0
    assert float(bundle.merged_df["model_daily_increment_floor_area"].iloc[1]) == 2.0


def test_validation_overlay_frame_uses_candidate_specific_columns() -> None:
    validation_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-08-08", "2024-08-09"]),
            "measured_cumulative_total_fruit_dry_weight_floor_area": [1.0, 2.0],
            "measured_offset_adjusted": [0.0, 1.0],
            "measured_daily_increment_floor_area": [pd.NA, 1.0],
            "estimated_cumulative_total_fruit_dry_weight_floor_area": [3.0, 4.0],
            "estimated_offset_adjusted": [0.0, 1.0],
            "estimated_daily_increment_floor_area": [pd.NA, 1.0],
            "model_cumulative_total_fruit_dry_weight_floor_area": [5.0, 7.0],
            "model_offset_adjusted": [0.0, 2.0],
            "model_daily_increment_floor_area": [pd.NA, 2.0],
        }
    )
    model_frame = validation_overlay_frame(validation_df, source_label="shipped_tomics")
    estimated_frame = validation_overlay_frame(validation_df, source_label="workbook_estimated")

    assert model_frame["cumulative_total_fruit_floor_area"].tolist() == [5.0, 7.0]
    assert estimated_frame["cumulative_total_fruit_floor_area"].tolist() == [3.0, 4.0]
