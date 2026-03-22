from __future__ import annotations

import json
from dataclasses import replace

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.contracts import HarvestState
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.fruit_harvest_dekoning import (
    DeKoningFdsHarvestPolicy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.fruit_harvest_tomgro import (
    TomgroAgeclassHarvestPolicy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.fruit_harvest_tomsim import (
    TomsimTrussHarvestPolicy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.fruit_harvest_vanthoor import (
    VanthoorBoxcarHarvestPolicy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.state_normalizer import (
    normalize_harvest_state,
)


def _current_row_from_payload(payload: list[dict[str, object]], *, semantics: str = "native_family") -> pd.Series:
    return pd.Series(
        {
            "datetime": pd.Timestamp("2024-08-10"),
            "fruit_dry_weight_g_m2": sum(float(row.get("fruit_dm_g_m2", 0.0)) for row in payload),
            "leaf_dry_weight_g_m2": 1.0,
            "LAI": 2.0,
            "truss_cohorts_json": json.dumps(payload),
            "harvest_family_semantics": semantics,
            "mean_truss_tdvs": 0.7,
            "n_fruits_per_truss": 4,
            "harvested_fruit_g_m2": 0.0,
        }
    )


def _make_state(row: dict[str, object]) -> HarvestState:
    return HarvestState(
        datetime=pd.Timestamp("2024-08-10"),
        dt_days=1.0,
        floor_area_basis=True,
        plants_per_m2=1.836091,
        lai=2.0,
        cbuf_g_m2=0.0,
        fruit_entities=pd.DataFrame([row]),
        leaf_entities=pd.DataFrame(),
        stem_root_state={"stem_dry_weight_g_m2": 1.0, "root_dry_weight_g_m2": 1.0},
        harvested_fruit_cumulative_g_m2=0.0,
        harvested_leaf_cumulative_g_m2=0.0,
        diagnostics={},
    )


def _advance_state_one_day(state: HarvestState) -> HarvestState:
    fruit_entities = state.fruit_entities.copy()
    for column in ("days_since_maturity", "mature_pool_residence_days", "final_stage_residence_days"):
        if column in fruit_entities.columns:
            fruit_entities[column] = pd.to_numeric(fruit_entities[column], errors="coerce").fillna(0.0) + 1.0
    return replace(
        state,
        datetime=state.datetime + pd.Timedelta(days=1),
        dt_days=1.0,
        fruit_entities=fruit_entities,
    )


def test_state_normalizer_preserves_native_runtime_axes_when_payload_is_available() -> None:
    current = _current_row_from_payload(
        [
            {
                "entity_id": "fruit_1",
                "tdvs": 0.65,
                "fds": 1.05,
                "fruit_dm_g_m2": 5.0,
                "fruit_count": 2.0,
                "sink_active_flag": False,
                "mature_flag": True,
                "harvest_ready_flag": True,
                "onplant_flag": True,
                "harvested_flag": False,
                "matured_at": "2024-08-08T00:00:00",
                "days_since_maturity": 2.0,
                "mature_pool_flag": True,
                "mature_pool_residence_days": 2.0,
                "final_stage_flag": True,
                "final_stage_residence_days": 2.0,
                "explicit_outflow_capacity_g_m2_d": 0.5,
                "proxy_state_flag": False,
            }
        ],
        semantics="dekoning_fds",
    )

    state = normalize_harvest_state(current, allow_bulk_proxy=False)
    row = state.fruit_entities.iloc[0]

    assert float(row["fds"]) == 1.05
    assert float(row["tdvs"]) == 0.65
    assert float(row["days_since_maturity"]) == 2.0
    assert bool(row["proxy_state_flag"]) is False
    assert state.diagnostics["family_state_mode"] == "native_payload"
    assert bool(state.diagnostics["native_family_state_available"]) is True
    assert bool(state.diagnostics["synthetic_fruit_state_flag"]) is False


def test_state_normalizer_marks_shared_tdvs_proxy_when_bulk_fallback_is_used() -> None:
    current = pd.Series(
        {
            "datetime": pd.Timestamp("2024-08-10"),
            "fruit_dry_weight_g_m2": 4.0,
            "leaf_dry_weight_g_m2": 1.0,
            "LAI": 2.0,
            "harvest_family_semantics": "vanthoor_boxcar",
            "mean_truss_tdvs": 0.8,
            "n_fruits_per_truss": 4,
            "harvested_fruit_g_m2": 0.0,
        }
    )

    state = normalize_harvest_state(current, allow_bulk_proxy=False)
    row = state.fruit_entities.iloc[0]

    assert bool(row["proxy_state_flag"]) is True
    assert state.diagnostics["family_state_mode"] == "shared_tdvs_proxy"
    assert bool(state.diagnostics["synthetic_fruit_state_flag"]) is True
    assert bool(state.diagnostics["native_family_state_available"]) is False


def test_harvest_family_runtime_axes_make_daily_series_distinguishable() -> None:
    tomsim_policy = TomsimTrussHarvestPolicy(tdvs_harvest_threshold=1.0, harvest_delay_days=1.0)
    dekoning_policy = DeKoningFdsHarvestPolicy(fds_harvest_threshold=1.0, harvest_delay_days=1.0)
    tomgro_policy = TomgroAgeclassHarvestPolicy(mature_class_index=20, mature_pool_harvest_mode="mature_pool_delta")
    vanthoor_policy = VanthoorBoxcarHarvestPolicy(n_dev=5, outflow_fraction_per_day=0.5)

    tomsim_state = _make_state(
        {
            "entity_id": "tomsim",
            "tdvs": 1.0,
            "days_since_maturity": 1.0,
            "fruit_dm_g_m2": 6.0,
            "fruit_count": 4.0,
            "onplant_flag": True,
            "harvested_flag": False,
        }
    )
    dekoning_state = _make_state(
        {
            "entity_id": "dekoning",
            "fds": 1.0,
            "days_since_maturity": 0.0,
            "fruit_dm_g_m2": 6.0,
            "fruit_count": 1.0,
            "onplant_flag": True,
            "harvested_flag": False,
        }
    )
    tomgro_state = _make_state(
        {
            "entity_id": "tomgro",
            "age_class": 20.0,
            "mature_pool_flag": True,
            "mature_pool_residence_days": 1.0,
            "fruit_dm_g_m2": 6.0,
            "fruit_count": 2.0,
            "onplant_flag": True,
            "harvested_flag": False,
        }
    )
    vanthoor_state = _make_state(
        {
            "entity_id": "vanthoor",
            "stage_index": 5.0,
            "final_stage_flag": True,
            "final_stage_residence_days": 1.0,
            "fruit_dm_g_m2": 6.0,
            "fruit_count": 2.0,
            "onplant_flag": True,
            "harvested_flag": False,
        }
    )

    series = {}
    current_state = tomsim_state
    series["tomsim"] = []
    for _ in range(2):
        update = tomsim_policy.step(current_state, env={}, dt_days=1.0)
        series["tomsim"].append(round(update.fruit_harvest_flux_g_m2_d, 6))
        current_state = _advance_state_one_day(update.updated_state)

    current_state = dekoning_state
    series["dekoning"] = []
    for _ in range(2):
        update = dekoning_policy.step(current_state, env={"T_air_C": 24.0}, dt_days=1.0)
        series["dekoning"].append(round(update.fruit_harvest_flux_g_m2_d, 6))
        current_state = _advance_state_one_day(update.updated_state)

    current_state = tomgro_state
    series["tomgro"] = []
    for _ in range(2):
        update = tomgro_policy.step(current_state, env={"mature_pool_delta_g_m2": 2.0}, dt_days=1.0)
        series["tomgro"].append(round(update.fruit_harvest_flux_g_m2_d, 6))
        current_state = _advance_state_one_day(update.updated_state)

    current_state = vanthoor_state
    series["vanthoor"] = []
    for _ in range(2):
        update = vanthoor_policy.step(current_state, env={}, dt_days=1.0)
        series["vanthoor"].append(round(update.fruit_harvest_flux_g_m2_d, 6))
        current_state = _advance_state_one_day(update.updated_state)

    unique_series = {tuple(values) for values in series.values()}
    assert len(unique_series) == 4
