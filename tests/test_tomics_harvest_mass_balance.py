from __future__ import annotations

import math

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.contracts import (
    FruitHarvestEvent,
    HarvestState,
    LeafHarvestEvent,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.mass_balance import (
    cumulative_monotonic_flag,
    duplicate_harvest_flag,
    harvest_mass_balance_error,
    mass_balance_metrics,
    negative_mass_flag,
)


def _make_state(
    *,
    fruit_mass: float,
    leaf_mass: float,
    leaf_area: float = 0.5,
) -> HarvestState:
    return HarvestState(
        datetime=pd.Timestamp("2024-08-10"),
        dt_days=1.0,
        floor_area_basis=True,
        plants_per_m2=1.836091,
        lai=1.5,
        cbuf_g_m2=0.0,
        fruit_entities=pd.DataFrame(
            [
                {
                    "entity_id": "fruit_1",
                    "truss_id": 1,
                    "fruit_dm_g_m2": fruit_mass,
                    "onplant_flag": True,
                    "harvested_flag": False,
                }
            ]
        ),
        leaf_entities=pd.DataFrame(
            [
                {
                    "entity_id": "leaf_1",
                    "linked_truss_id": 1,
                    "leaf_dm_g_m2": leaf_mass,
                    "leaf_area_m2_m2": leaf_area,
                    "onplant_flag": True,
                    "harvested_flag": False,
                }
            ]
        ),
        stem_root_state={"stem_dry_weight_g_m2": 1.0, "root_dry_weight_g_m2": 1.0},
        harvested_fruit_cumulative_g_m2=0.0,
        harvested_leaf_cumulative_g_m2=0.0,
        diagnostics={},
    )


def test_mass_balance_metrics_close_cleanly_when_latent_and_harvested_flux_match() -> None:
    before = _make_state(fruit_mass=5.0, leaf_mass=2.0)
    after = before.with_updates(
        fruit_entities=pd.DataFrame(
            [
                {
                    "entity_id": "fruit_1",
                    "truss_id": 1,
                    "fruit_dm_g_m2": 3.0,
                    "onplant_flag": False,
                    "harvested_flag": True,
                }
            ]
        ),
        leaf_entities=pd.DataFrame(
            [
                {
                    "entity_id": "leaf_1",
                    "linked_truss_id": 1,
                    "leaf_dm_g_m2": 1.5,
                    "leaf_area_m2_m2": 0.375,
                    "onplant_flag": True,
                    "harvested_flag": False,
                }
            ]
        ),
        harvested_fruit_cumulative_g_m2=2.0,
        harvested_leaf_cumulative_g_m2=0.5,
        lai=1.375,
    )
    fruit_events = [
        FruitHarvestEvent(
            date=before.datetime,
            entity_id="fruit_1",
            family="tomsim_truss",
            harvest_flux_g_m2=2.0,
            harvest_count=1.0,
            harvest_ready_score=1.0,
            fdmc_used=None,
            fresh_weight_equivalent_g_m2=None,
            dry_weight_g_m2=2.0,
        )
    ]
    leaf_events = [
        LeafHarvestEvent(
            date=before.datetime,
            entity_id="leaf_1",
            family="linked_truss_stage",
            leaf_harvest_flux_g_m2=0.5,
            reason="linked_truss_stage",
            linked_truss_id="1",
        )
    ]

    metrics = mass_balance_metrics(before, after, fruit_events=fruit_events, leaf_events=leaf_events)

    assert math.isclose(harvest_mass_balance_error(before, after, fruit_events, leaf_events), 0.0)
    assert math.isclose(float(metrics["harvest_mass_balance_error"]), 0.0)
    assert math.isclose(float(metrics["leaf_harvest_mass_balance_error"]), 0.0)
    assert math.isclose(float(metrics["latent_fruit_residual_end"]), 3.0)
    assert bool(metrics["duplicate_harvest_flag"]) is False
    assert bool(metrics["negative_mass_flag"]) is False


def test_duplicate_and_negative_mass_flags_detect_inconsistent_states() -> None:
    duplicate_events = [
        FruitHarvestEvent(
            date=pd.Timestamp("2024-08-10"),
            entity_id="fruit_1",
            family="tomsim_truss",
            harvest_flux_g_m2=1.0,
            harvest_count=1.0,
            harvest_ready_score=1.0,
            fdmc_used=None,
            fresh_weight_equivalent_g_m2=None,
            dry_weight_g_m2=1.0,
        ),
        FruitHarvestEvent(
            date=pd.Timestamp("2024-08-10"),
            entity_id="fruit_1",
            family="tomsim_truss",
            harvest_flux_g_m2=0.5,
            harvest_count=1.0,
            harvest_ready_score=1.0,
            fdmc_used=None,
            fresh_weight_equivalent_g_m2=None,
            dry_weight_g_m2=0.5,
        ),
    ]
    negative_state = _make_state(fruit_mass=-0.1, leaf_mass=1.0)

    assert duplicate_harvest_flag(duplicate_events) is True
    assert negative_mass_flag(negative_state) is True


def test_cumulative_monotonic_flag_rejects_backtracking_series() -> None:
    assert cumulative_monotonic_flag(pd.Series([0.0, 1.0, 1.5, 1.5, 2.0])) is True
    assert cumulative_monotonic_flag(pd.Series([0.0, 1.0, 0.8, 1.2])) is False
