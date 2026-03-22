from __future__ import annotations

import math

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.common_structure import (
    build_common_structure_snapshot,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.models.tomato_legacy.tomato_model import TomatoModel


def test_common_structure_snapshot_uses_step_harvest_flux_arguments() -> None:
    snapshot = build_common_structure_snapshot(
        assimilate_buffer_g=1.0,
        leaf_biomass_g=2.0,
        stem_root_biomass_g=3.0,
        fruit_biomass_g=4.0,
        photosynthesis_g=5.0,
        growth_respiration_g=0.5,
        growth_g=1.5,
        maintenance_g=0.25,
        fruit_harvest_g=2.5,
        leaf_harvest_g=0.75,
    )

    assert math.isclose(snapshot["h1_fruit_harvest_g_m2_step"], 2.5)
    assert math.isclose(snapshot["h2_leaf_harvest_g_m2_step"], 0.75)


def test_tomato_model_common_structure_uses_step_flux_not_cumulative_harvest_pool() -> None:
    model = TomatoModel(internal_harvest_enabled=False)
    model.W_fr_harvested = 42.0
    forcing_row = pd.Series(
        {
            "datetime": pd.Timestamp("2024-08-10 00:00:00"),
            "T_air_C": 24.0,
            "PAR_umol": 0.0,
            "CO2_ppm": 400.0,
            "RH_percent": 70.0,
            "wind_speed_ms": 0.3,
            "n_fruits_per_truss": 4,
        }
    )

    model.update_inputs_from_row(forcing_row)
    model.run_timestep_calculations(3600.0, pd.Timestamp(forcing_row["datetime"]).to_pydatetime())

    assert math.isclose(model.W_fr_harvested, 42.0)
    assert math.isclose(model.common_structure_snapshot["h1_fruit_harvest_g_m2_step"], 0.0)
