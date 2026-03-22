from __future__ import annotations

import json

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.state_normalizer import (
    normalize_harvest_state,
)


def _row_from_payload(
    payload: list[dict[str, object]],
    *,
    fruit_harvest_g_m2_step: float = 0.0,
) -> pd.Series:
    return pd.Series(
        {
            "datetime": pd.Timestamp("2024-08-10"),
            "fruit_dry_weight_g_m2": sum(float(row.get("fruit_dm_g_m2", 0.0)) for row in payload),
            "leaf_dry_weight_g_m2": 1.0,
            "LAI": 2.0,
            "truss_cohorts_json": json.dumps(payload),
            "harvest_family_semantics": "tomsim_truss",
            "mean_truss_tdvs": 0.7,
            "fruit_harvest_g_m2_step": fruit_harvest_g_m2_step,
            "harvested_fruit_g_m2": 0.0,
        }
    )


def test_dekoning_runtime_reconstruction_uses_clock_backed_fds() -> None:
    current = _row_from_payload(
        [
            {
                "entity_id": "fruit_1",
                "tdvs": 0.82,
                "fds": 0.82,
                "fruit_dm_g_m2": 5.0,
                "fruit_count": 2.0,
                "days_since_anthesis": 15.0,
                "days_since_maturity": 2.0,
                "mature_flag": True,
                "onplant_flag": True,
                "harvested_flag": False,
                "proxy_state_flag": True,
            }
        ]
    )

    state = normalize_harvest_state(current, allow_bulk_proxy=False, fruit_harvest_family="dekoning_fds")
    row = state.fruit_entities.iloc[0]

    assert float(row["fds"]) > 0.82
    assert bool(row["proxy_state_flag"]) is False
    assert state.diagnostics["family_state_mode"] == "dekoning_runtime_reconstruction"


def test_tomgro_runtime_reconstruction_uses_mature_pool_clock() -> None:
    current = _row_from_payload(
        [
            {
                "entity_id": "fruit_1",
                "tdvs": 0.40,
                "age_class": None,
                "fruit_dm_g_m2": 4.0,
                "fruit_count": 2.0,
                "days_since_anthesis": 18.0,
                "days_since_maturity": 2.0,
                "mature_flag": True,
                "onplant_flag": True,
                "harvested_flag": False,
                "proxy_state_flag": True,
            }
        ]
    )

    state = normalize_harvest_state(current, allow_bulk_proxy=False, fruit_harvest_family="tomgro_ageclass")
    row = state.fruit_entities.iloc[0]

    assert float(row["age_class"]) >= 11.0
    assert bool(row["mature_pool_flag"]) is True
    assert float(row["mature_pool_residence_days"]) == 2.0
    assert bool(row["proxy_state_flag"]) is False
    assert state.diagnostics["family_state_mode"] == "tomgro_mature_pool_reconstruction"


def test_vanthoor_runtime_reconstruction_uses_final_stage_clock() -> None:
    current = _row_from_payload(
        [
            {
                "entity_id": "fruit_1",
                "tdvs": 0.55,
                "stage_index": None,
                "fruit_dm_g_m2": 4.0,
                "fruit_count": 2.0,
                "days_since_anthesis": 22.0,
                "days_since_maturity": 3.0,
                "mature_flag": True,
                "onplant_flag": True,
                "harvested_flag": False,
                "proxy_state_flag": True,
            }
        ],
        fruit_harvest_g_m2_step=1.2,
    )

    state = normalize_harvest_state(current, allow_bulk_proxy=False, fruit_harvest_family="vanthoor_boxcar")
    row = state.fruit_entities.iloc[0]

    assert float(row["stage_index"]) == 5.0
    assert bool(row["final_stage_flag"]) is True
    assert float(row["final_stage_residence_days"]) == 3.0
    assert float(row["explicit_outflow_capacity_g_m2_d"]) >= 1.2
    assert bool(row["proxy_state_flag"]) is False
    assert state.diagnostics["family_state_mode"] == "vanthoor_final_stage_reconstruction"
