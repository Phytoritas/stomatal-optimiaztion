from __future__ import annotations

import math

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.contracts import (
    HarvestState,
)
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
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.leaf_harvest import (
    LinkedTrussStageLeafHarvestPolicy,
    MaxLaiPruningFlowPolicy,
    VegetativeUnitLeafHarvestPolicy,
)


def _make_state(
    *,
    fruit_rows: list[dict[str, object]] | None = None,
    leaf_rows: list[dict[str, object]] | None = None,
    lai: float = 2.5,
    harvested_fruit: float = 0.0,
    harvested_leaf: float = 0.0,
) -> HarvestState:
    return HarvestState(
        datetime=pd.Timestamp("2024-08-10"),
        dt_days=1.0,
        floor_area_basis=True,
        plants_per_m2=1.836091,
        lai=lai,
        cbuf_g_m2=0.0,
        fruit_entities=pd.DataFrame(fruit_rows or []),
        leaf_entities=pd.DataFrame(leaf_rows or []),
        stem_root_state={"stem_dry_weight_g_m2": 1.0, "root_dry_weight_g_m2": 1.0},
        harvested_fruit_cumulative_g_m2=harvested_fruit,
        harvested_leaf_cumulative_g_m2=harvested_leaf,
        diagnostics={},
    )


def _fruit_lookup(frame: pd.DataFrame, entity_id: str) -> pd.Series:
    row = frame.loc[frame["entity_id"].astype(str).eq(entity_id)]
    assert not row.empty
    return row.iloc[0]


def _leaf_lookup(frame: pd.DataFrame, entity_id: str) -> pd.Series:
    row = frame.loc[frame["entity_id"].astype(str).eq(entity_id)]
    assert not row.empty
    return row.iloc[0]


def assert_tomsim_harvest_waits_for_ready_truss_and_removes_whole_truss_mass() -> None:
    state = _make_state(
        fruit_rows=[
            {
                "entity_id": "truss_ready",
                "truss_id": 1,
                "tdvs": 1.02,
                "fruit_dm_g_m2": 3.0,
                "fruit_count": 4,
                "onplant_flag": True,
                "harvested_flag": False,
            },
            {
                "entity_id": "truss_waiting",
                "truss_id": 2,
                "tdvs": 0.84,
                "fruit_dm_g_m2": 2.0,
                "fruit_count": 4,
                "onplant_flag": True,
                "harvested_flag": False,
            },
        ]
    )

    update = TomsimTrussHarvestPolicy().step(state, env={}, dt_days=1.0)

    assert update.fruit_harvest_event_count == 1
    assert math.isclose(update.fruit_harvest_flux_g_m2_d, 3.0)
    ready_row = _fruit_lookup(update.updated_state.fruit_entities, "truss_ready")
    waiting_row = _fruit_lookup(update.updated_state.fruit_entities, "truss_waiting")
    assert math.isclose(float(ready_row["fruit_dm_g_m2"]), 0.0)
    assert bool(ready_row["harvested_flag"]) is True
    assert bool(waiting_row["onplant_flag"]) is True
    assert math.isclose(float(waiting_row["fruit_dm_g_m2"]), 2.0)


def assert_tomgro_harvest_uses_only_mature_age_classes_and_scales_to_mature_pool_delta() -> None:
    state = _make_state(
        fruit_rows=[
            {
                "entity_id": "immature",
                "age_class": 19,
                "fruit_dm_g_m2": 2.0,
                "fruit_count": 2,
                "onplant_flag": True,
                "harvested_flag": False,
            },
            {
                "entity_id": "mature_a",
                "age_class": 20,
                "fruit_dm_g_m2": 6.0,
                "fruit_count": 3,
                "onplant_flag": True,
                "harvested_flag": False,
            },
            {
                "entity_id": "mature_b",
                "age_class": 21,
                "fruit_dm_g_m2": 4.0,
                "fruit_count": 2,
                "onplant_flag": True,
                "harvested_flag": False,
            },
        ]
    )
    policy = TomgroAgeclassHarvestPolicy(mature_class_index=20, mature_pool_harvest_mode="mature_pool_delta")

    update = policy.step(state, env={"mature_pool_delta_g_m2": 5.0}, dt_days=1.0)

    assert update.fruit_harvest_event_count == 2
    assert math.isclose(update.fruit_harvest_flux_g_m2_d, 5.0)
    immature = _fruit_lookup(update.updated_state.fruit_entities, "immature")
    mature_a = _fruit_lookup(update.updated_state.fruit_entities, "mature_a")
    mature_b = _fruit_lookup(update.updated_state.fruit_entities, "mature_b")
    assert math.isclose(float(immature["fruit_dm_g_m2"]), 2.0)
    assert math.isclose(float(mature_a["fruit_dm_g_m2"]), 3.0)
    assert math.isclose(float(mature_b["fruit_dm_g_m2"]), 2.0)


def assert_dekoning_harvest_requires_fds_threshold_and_records_fdmc_outputs() -> None:
    state = _make_state(
        fruit_rows=[
            {
                "entity_id": "ripe_fruit",
                "truss_id": 1,
                "fds": 1.03,
                "fruit_dm_g_m2": 1.8,
                "fruit_count": 1,
                "onplant_flag": True,
                "harvested_flag": False,
            },
            {
                "entity_id": "green_fruit",
                "truss_id": 1,
                "fds": 0.72,
                "fruit_dm_g_m2": 2.4,
                "fruit_count": 1,
                "onplant_flag": True,
                "harvested_flag": False,
            },
        ]
    )

    update = DeKoningFdsHarvestPolicy(fdmc_mode="dekoning_fds").step(state, env={"T_air_C": 24.0}, dt_days=1.0)

    assert update.fruit_harvest_event_count == 1
    assert math.isclose(update.fruit_harvest_flux_g_m2_d, 1.8)
    event = update.diagnostics["fruit_events"][0]
    assert event.fdmc_used is not None
    assert event.fresh_weight_equivalent_g_m2 is not None
    assert event.fresh_weight_equivalent_g_m2 > event.dry_weight_g_m2
    green = _fruit_lookup(update.updated_state.fruit_entities, "green_fruit")
    assert math.isclose(float(green["fruit_dm_g_m2"]), 2.4)


def assert_vanthoor_harvest_uses_last_stage_when_no_explicit_outflow_is_supplied() -> None:
    state = _make_state(
        fruit_rows=[
            {
                "entity_id": "stage_4",
                "stage_index": 4,
                "fruit_dm_g_m2": 3.0,
                "fruit_count": 1,
                "onplant_flag": True,
                "harvested_flag": False,
            },
            {
                "entity_id": "stage_5_a",
                "stage_index": 5,
                "fruit_dm_g_m2": 6.0,
                "fruit_count": 2,
                "onplant_flag": True,
                "harvested_flag": False,
            },
            {
                "entity_id": "stage_5_b",
                "stage_index": 5,
                "fruit_dm_g_m2": 2.0,
                "fruit_count": 1,
                "onplant_flag": True,
                "harvested_flag": False,
            },
        ]
    )

    update = VanthoorBoxcarHarvestPolicy(n_dev=5, outflow_fraction_per_day=0.5).step(state, env={}, dt_days=1.0)

    assert update.fruit_harvest_event_count == 2
    assert math.isclose(update.fruit_harvest_flux_g_m2_d, 4.0)
    stage_4 = _fruit_lookup(update.updated_state.fruit_entities, "stage_4")
    stage_5_a = _fruit_lookup(update.updated_state.fruit_entities, "stage_5_a")
    stage_5_b = _fruit_lookup(update.updated_state.fruit_entities, "stage_5_b")
    assert math.isclose(float(stage_4["fruit_dm_g_m2"]), 3.0)
    assert math.isclose(float(stage_5_a["fruit_dm_g_m2"]), 3.0)
    assert math.isclose(float(stage_5_b["fruit_dm_g_m2"]), 1.0)


def assert_linked_truss_stage_leaf_harvest_follows_linked_tdvs_threshold() -> None:
    state = _make_state(
        fruit_rows=[
            {"entity_id": "fruit_1", "truss_id": 1, "tdvs": 0.95, "fruit_dm_g_m2": 1.0, "onplant_flag": True},
            {"entity_id": "fruit_2", "truss_id": 2, "tdvs": 0.60, "fruit_dm_g_m2": 1.0, "onplant_flag": True},
        ],
        leaf_rows=[
            {
                "entity_id": "leaf_1",
                "linked_truss_id": 1,
                "vpos": 1,
                "vds": 0.0,
                "leaf_dm_g_m2": 1.5,
                "leaf_area_m2_m2": 0.5,
                "onplant_flag": True,
                "harvested_flag": False,
            },
            {
                "entity_id": "leaf_2",
                "linked_truss_id": 2,
                "vpos": 2,
                "vds": 0.0,
                "leaf_dm_g_m2": 1.0,
                "leaf_area_m2_m2": 0.4,
                "onplant_flag": True,
                "harvested_flag": False,
            },
        ],
        lai=2.4,
    )

    update = LinkedTrussStageLeafHarvestPolicy(linked_leaf_stage=0.9).step(state, env={}, dt_days=1.0)

    assert update.leaf_harvest_event_count == 1
    harvested_leaf = _leaf_lookup(update.updated_state.leaf_entities, "leaf_1")
    retained_leaf = _leaf_lookup(update.updated_state.leaf_entities, "leaf_2")
    assert math.isclose(float(harvested_leaf["leaf_dm_g_m2"]), 0.0)
    assert math.isclose(float(retained_leaf["leaf_dm_g_m2"]), 1.0)
    assert math.isclose(float(update.updated_state.lai), 1.9)


def assert_vegetative_unit_leaf_harvest_uses_corresponding_truss_colour_proxy() -> None:
    state = _make_state(
        fruit_rows=[
            {"entity_id": "fruit_a", "truss_id": 1, "fds": 0.92, "fruit_dm_g_m2": 1.0, "onplant_flag": True},
            {"entity_id": "fruit_b", "truss_id": 2, "fds": 0.70, "fruit_dm_g_m2": 1.0, "onplant_flag": True},
        ],
        leaf_rows=[
            {
                "entity_id": "veg_1",
                "linked_truss_id": 1,
                "vpos": 1,
                "vds": 0.0,
                "leaf_dm_g_m2": 1.2,
                "leaf_area_m2_m2": 0.45,
                "onplant_flag": True,
                "harvested_flag": False,
            },
            {
                "entity_id": "veg_2",
                "linked_truss_id": 2,
                "vpos": 2,
                "vds": 0.0,
                "leaf_dm_g_m2": 1.1,
                "leaf_area_m2_m2": 0.40,
                "onplant_flag": True,
                "harvested_flag": False,
            },
        ],
        lai=2.2,
    )

    update = VegetativeUnitLeafHarvestPolicy(colour_threshold=0.9).step(state, env={}, dt_days=1.0)

    assert update.leaf_harvest_event_count == 1
    assert math.isclose(update.leaf_harvest_flux_g_m2_d, 1.2)
    retained_leaf = _leaf_lookup(update.updated_state.leaf_entities, "veg_2")
    assert math.isclose(float(retained_leaf["leaf_dm_g_m2"]), 1.1)


def assert_max_lai_pruning_flow_can_partially_remove_leaf_mass_to_hit_target_lai() -> None:
    state = _make_state(
        fruit_rows=[{"entity_id": "fruit", "truss_id": 1, "tdvs": 0.5, "fruit_dm_g_m2": 1.0, "onplant_flag": True}],
        leaf_rows=[
            {
                "entity_id": "top_leaf",
                "linked_truss_id": 2,
                "vpos": 2,
                "vds": 0.0,
                "leaf_dm_g_m2": 2.0,
                "leaf_area_m2_m2": 1.0,
                "onplant_flag": True,
                "harvested_flag": False,
            },
            {
                "entity_id": "lower_leaf",
                "linked_truss_id": 1,
                "vpos": 1,
                "vds": 0.0,
                "leaf_dm_g_m2": 1.0,
                "leaf_area_m2_m2": 0.3,
                "onplant_flag": True,
                "harvested_flag": False,
            },
        ],
        lai=3.6,
    )

    update = MaxLaiPruningFlowPolicy(max_lai=3.0).step(state, env={}, dt_days=1.0)

    assert update.leaf_harvest_event_count == 1
    assert math.isclose(update.leaf_harvest_flux_g_m2_d, 1.2)
    top_leaf = _leaf_lookup(update.updated_state.leaf_entities, "top_leaf")
    lower_leaf = _leaf_lookup(update.updated_state.leaf_entities, "lower_leaf")
    assert math.isclose(float(top_leaf["leaf_dm_g_m2"]), 0.8)
    assert math.isclose(float(lower_leaf["leaf_dm_g_m2"]), 1.0)
    assert math.isclose(float(update.updated_state.lai), 3.0)
