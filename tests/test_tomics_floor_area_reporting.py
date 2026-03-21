from __future__ import annotations

import pandas as pd
import pytest

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation import (
    PLANTS_PER_M2,
    compute_validation_bundle,
    observed_floor_area_yield,
    to_floor_area_value,
)


def test_floor_area_conversion_respects_basis() -> None:
    assert to_floor_area_value(10.0, basis="floor_area_g_m2") == pytest.approx(10.0)
    assert to_floor_area_value(10.0, basis="g/plant") == pytest.approx(10.0 * PLANTS_PER_M2)


def test_offset_adjusted_validation_metric_is_flagged_when_observed_starts_nonzero() -> None:
    observed = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-08-08", "2024-08-09", "2024-08-10"]),
            "Measured_Cumulative_Total_Fruit_DW (g/m^2)": [5.0, 7.0, 10.0],
            "Estimated_Cumulative_Total_Fruit_DW (g/m^2)": [4.0, 7.5, 11.0],
        }
    )
    observed_floor = observed_floor_area_yield(
        observed,
        measured_column="Measured_Cumulative_Total_Fruit_DW (g/m^2)",
        estimated_column="Estimated_Cumulative_Total_Fruit_DW (g/m^2)",
    )
    bundle = compute_validation_bundle(
        observed_floor,
        candidate_series=pd.Series([4.0, 6.0, 9.0]),
        candidate_label="model",
        unit_declared_in_observation_file="g/m^2",
    )

    assert bundle.metrics["reporting_basis"] == "floor_area_g_m2"
    assert bundle.metrics["offset_adjustment_applied"] is True
    assert bundle.merged_df["measured_offset_adjusted"].iloc[0] == pytest.approx(0.0)
    assert bundle.merged_df["model_offset_adjusted"].iloc[0] == pytest.approx(0.0)
