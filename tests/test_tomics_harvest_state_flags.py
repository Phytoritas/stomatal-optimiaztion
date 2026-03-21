from __future__ import annotations

import math

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.contracts import HarvestState
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.fruit_harvest_vanthoor import (
    VanthoorBoxcarHarvestPolicy,
)


def test_partial_harvest_keeps_remaining_mass_on_plant() -> None:
    state = HarvestState(
        datetime=pd.Timestamp("2024-08-10"),
        dt_days=1.0,
        floor_area_basis=True,
        plants_per_m2=1.836091,
        lai=2.5,
        cbuf_g_m2=0.0,
        fruit_entities=pd.DataFrame(
            [
                {
                    "entity_id": "stage_5",
                    "stage_index": 5,
                    "fruit_dm_g_m2": 6.0,
                    "fruit_count": 2.0,
                    "sink_active_flag": False,
                    "mature_flag": True,
                    "harvest_ready_flag": True,
                    "onplant_flag": True,
                    "harvested_flag": False,
                    "maturity_basis": "stage_index",
                }
            ]
        ),
        leaf_entities=pd.DataFrame(),
        stem_root_state={"stem_dry_weight_g_m2": 1.0, "root_dry_weight_g_m2": 1.0},
        harvested_fruit_cumulative_g_m2=0.0,
        harvested_leaf_cumulative_g_m2=0.0,
        diagnostics={},
    )

    update = VanthoorBoxcarHarvestPolicy(n_dev=5, outflow_fraction_per_day=0.5).step(state, env={}, dt_days=1.0)

    fruit_row = update.updated_state.fruit_entities.iloc[0]
    assert math.isclose(update.fruit_harvest_flux_g_m2_d, 3.0)
    assert math.isclose(float(fruit_row["fruit_dm_g_m2"]), 3.0)
    assert bool(fruit_row["onplant_flag"]) is True
    assert bool(fruit_row["harvested_flag"]) is False
