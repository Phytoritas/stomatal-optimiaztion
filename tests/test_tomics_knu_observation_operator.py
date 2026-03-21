from __future__ import annotations

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_operator import (
    model_floor_area_cumulative_total_fruit,
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
