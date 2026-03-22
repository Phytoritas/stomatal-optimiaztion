from __future__ import annotations

import math

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.contracts import HarvestState
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.fruit_harvest_tomgro import (
    TomgroAgeclassHarvestPolicy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.fruit_harvest_vanthoor import (
    VanthoorBoxcarHarvestPolicy,
)


def _make_state(fruit_row: dict[str, object]) -> HarvestState:
    return HarvestState(
        datetime=pd.Timestamp("2024-08-10"),
        dt_days=1.0,
        floor_area_basis=True,
        plants_per_m2=1.836091,
        lai=2.0,
        cbuf_g_m2=0.0,
        fruit_entities=pd.DataFrame([fruit_row]),
        leaf_entities=pd.DataFrame(),
        stem_root_state={"stem_dry_weight_g_m2": 1.0, "root_dry_weight_g_m2": 1.0},
        harvested_fruit_cumulative_g_m2=0.0,
        harvested_leaf_cumulative_g_m2=0.0,
        diagnostics={},
    )


def test_vanthoor_partial_outflow_keeps_residual_mass_on_plant() -> None:
    state = _make_state(
        {
            "entity_id": "final_stage_fruit",
            "stage_index": 5.0,
            "final_stage_flag": True,
            "final_stage_residence_days": 1.0,
            "fruit_dm_g_m2": 8.0,
            "fruit_count": 2.0,
            "onplant_flag": True,
            "harvested_flag": False,
        }
    )
    update = VanthoorBoxcarHarvestPolicy(n_dev=5, outflow_fraction_per_day=0.5).step(state, env={}, dt_days=1.0)

    row = update.updated_state.fruit_entities.iloc[0]
    event = update.diagnostics["fruit_events"][0]

    assert update.fruit_harvest_event_count == 1
    assert 0.0 < float(row["fruit_dm_g_m2"]) < 8.0
    assert bool(row["onplant_flag"]) is True
    assert bool(row["harvested_flag"]) is False
    assert event.partial_outflow_flag is True
    assert event.removes_entity is False
    assert bool(update.diagnostics["partial_fruit_outflow_flag"]) is True


def test_tomgro_mature_pool_delta_can_harvest_partially_across_multiple_days() -> None:
    policy = TomgroAgeclassHarvestPolicy(mature_class_index=20, mature_pool_harvest_mode="mature_pool_delta")
    state = _make_state(
        {
            "entity_id": "mature_pool",
            "age_class": 20.0,
            "mature_pool_flag": True,
            "mature_pool_residence_days": 1.0,
            "fruit_dm_g_m2": 6.0,
            "fruit_count": 2.0,
            "onplant_flag": True,
            "harvested_flag": False,
        }
    )

    first = policy.step(state, env={"mature_pool_delta_g_m2": 2.0}, dt_days=1.0)
    second = policy.step(first.updated_state, env={"mature_pool_delta_g_m2": 2.0}, dt_days=1.0)

    first_row = first.updated_state.fruit_entities.iloc[0]
    second_row = second.updated_state.fruit_entities.iloc[0]

    assert math.isclose(first.fruit_harvest_flux_g_m2_d, 2.0)
    assert math.isclose(float(first_row["fruit_dm_g_m2"]), 4.0)
    assert bool(first_row["onplant_flag"]) is True
    assert bool(first_row["harvested_flag"]) is False

    assert math.isclose(second.fruit_harvest_flux_g_m2_d, 2.0)
    assert math.isclose(float(second_row["fruit_dm_g_m2"]), 2.0)
    assert bool(second_row["onplant_flag"]) is True
    assert bool(second_row["harvested_flag"]) is False
