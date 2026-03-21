from __future__ import annotations

import math
from datetime import datetime

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest import (
    run_harvest_step,
    snapshot_to_harvest_state,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.fruit_harvest_tomsim import (
    TomsimTrussHarvestPolicy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.leaf_harvest import (
    LinkedTrussStageLeafHarvestPolicy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.contracts import EnvStep
from stomatal_optimiaztion.domains.tomato.tomics.alloc.models.tomato_legacy import TomatoLegacyAdapter
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_family_eval import (
    _apply_harvest_update_to_model,
)


def _make_env() -> EnvStep:
    return EnvStep(
        t=datetime(2024, 8, 10, 0, 0, 0),
        dt_s=86400.0,
        T_air_C=23.0,
        PAR_umol=300.0,
        CO2_ppm=420.0,
        RH_percent=70.0,
        wind_speed_ms=0.3,
        n_fruits_per_truss=4,
    )


def _make_adapter(*, tdvs: float = 1.0, fruit_mass: float = 5.0) -> TomatoLegacyAdapter:
    return TomatoLegacyAdapter(
        fixed_lai=2.5,
        initial_state_overrides={
            "W_lv": 8.0,
            "W_st": 5.0,
            "W_rt": 4.0,
            "LAI": 2.5,
            "truss_cohorts": [
                {
                    "entity_id": "truss_0001",
                    "tdvs": tdvs,
                    "n_fruits": 4,
                    "w_fr_cohort": fruit_mass,
                    "active": True,
                }
            ],
        },
        internal_harvest_enabled=False,
    )


def _mature_state(*, tdvs: float = 1.0, fruit_mass: float = 5.0):
    adapter = _make_adapter(tdvs=tdvs, fruit_mass=fruit_mass)
    row = adapter.step(_make_env())
    state = snapshot_to_harvest_state(row, plants_per_m2=1.836091, floor_area_basis=True)
    return adapter, row, state


def test_mature_truss_remains_on_plant_under_external_harvest_replay() -> None:
    _adapter, _row, state = _mature_state(tdvs=1.0, fruit_mass=5.0)

    fruit_row = state.fruit_entities.iloc[0]

    assert bool(fruit_row["sink_active_flag"]) is False
    assert bool(fruit_row["mature_flag"]) is True
    assert bool(fruit_row["harvest_ready_flag"]) is True
    assert bool(fruit_row["onplant_flag"]) is True
    assert bool(fruit_row["harvested_flag"]) is False


def test_external_tomsim_replay_harvests_mature_onplant_truss() -> None:
    _adapter, _row, state = _mature_state(tdvs=1.0, fruit_mass=5.0)

    result = run_harvest_step(
        fruit_policy=TomsimTrussHarvestPolicy(),
        leaf_policy=LinkedTrussStageLeafHarvestPolicy(),
        state=state,
        env={},
        dt_days=1.0,
    )

    assert result.final_update.fruit_harvest_event_count == 1
    assert math.isclose(result.final_update.fruit_harvest_flux_g_m2_d, 5.0)
    updated_row = result.final_update.updated_state.fruit_entities.iloc[0]
    assert math.isclose(float(updated_row["fruit_dm_g_m2"]), 0.0)
    assert bool(updated_row["onplant_flag"]) is False
    assert bool(updated_row["harvested_flag"]) is True


def test_writeback_does_not_drop_mature_mass_when_pick_is_delayed() -> None:
    adapter, _row, state = _mature_state(tdvs=1.0, fruit_mass=5.0)

    delayed_pick = run_harvest_step(
        fruit_policy=TomsimTrussHarvestPolicy(tdvs_harvest_threshold=1.2),
        leaf_policy=LinkedTrussStageLeafHarvestPolicy(),
        state=state,
        env={},
        dt_days=1.0,
    )

    assert delayed_pick.final_update.fruit_harvest_event_count == 0
    _apply_harvest_update_to_model(adapter=adapter, update=delayed_pick.final_update)

    model = adapter.model
    assert model is not None
    assert math.isclose(float(model.W_fr), 5.0)
    assert math.isclose(float(model.W_fr_harvested), 0.0)
    assert len(model.truss_cohorts) == 1
