from __future__ import annotations

import math

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.contracts import HarvestState
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.fruit_harvest_dekoning import (
    DeKoningFdsHarvestPolicy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.fruit_harvest_tomsim import (
    TomsimTrussHarvestPolicy,
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


def test_tomsim_positive_delay_uses_post_maturity_residence_clock() -> None:
    policy = TomsimTrussHarvestPolicy(tdvs_harvest_threshold=1.0, harvest_delay_days=1.0)
    waiting_state = _make_state(
        {
            "entity_id": "truss_waiting",
            "tdvs": 1.0,
            "days_since_maturity": 0.5,
            "fruit_dm_g_m2": 6.0,
            "fruit_count": 4.0,
            "onplant_flag": True,
            "harvested_flag": False,
        }
    )
    ready_state = _make_state(
        {
            "entity_id": "truss_ready",
            "tdvs": 1.0,
            "days_since_maturity": 1.1,
            "fruit_dm_g_m2": 6.0,
            "fruit_count": 4.0,
            "onplant_flag": True,
            "harvested_flag": False,
        }
    )

    waiting_update = policy.step(waiting_state, env={}, dt_days=1.0)
    ready_update = policy.step(ready_state, env={}, dt_days=1.0)

    assert waiting_update.fruit_harvest_event_count == 0
    assert ready_update.fruit_harvest_event_count == 1
    assert math.isclose(ready_update.fruit_harvest_flux_g_m2_d, 6.0)
    assert ready_update.diagnostics["delay_mode"] == "residence_clock"


def test_dekoning_positive_delay_uses_post_maturity_residence_clock() -> None:
    policy = DeKoningFdsHarvestPolicy(fds_harvest_threshold=1.0, harvest_delay_days=2.0)
    waiting_state = _make_state(
        {
            "entity_id": "fruit_waiting",
            "fds": 1.02,
            "days_since_maturity": 1.5,
            "fruit_dm_g_m2": 3.5,
            "fruit_count": 1.0,
            "onplant_flag": True,
            "harvested_flag": False,
        }
    )
    ready_state = _make_state(
        {
            "entity_id": "fruit_ready",
            "fds": 1.02,
            "days_since_maturity": 2.1,
            "fruit_dm_g_m2": 3.5,
            "fruit_count": 1.0,
            "onplant_flag": True,
            "harvested_flag": False,
        }
    )

    waiting_update = policy.step(waiting_state, env={"T_air_C": 24.0}, dt_days=1.0)
    ready_update = policy.step(ready_state, env={"T_air_C": 24.0}, dt_days=1.0)

    assert waiting_update.fruit_harvest_event_count == 0
    assert ready_update.fruit_harvest_event_count == 1
    assert math.isclose(ready_update.fruit_harvest_flux_g_m2_d, 3.5)
    assert ready_update.diagnostics["delay_mode"] == "residence_clock"
