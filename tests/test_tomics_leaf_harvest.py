from __future__ import annotations

from .test_tomics_harvest_policies import (
    assert_linked_truss_stage_leaf_harvest_follows_linked_tdvs_threshold,
    assert_max_lai_pruning_flow_can_partially_remove_leaf_mass_to_hit_target_lai,
    assert_vegetative_unit_leaf_harvest_uses_corresponding_truss_colour_proxy,
)


def test_linked_truss_stage_leaf_harvest_follows_linked_tdvs_threshold() -> None:
    assert_linked_truss_stage_leaf_harvest_follows_linked_tdvs_threshold()


def test_vegetative_unit_leaf_harvest_uses_corresponding_truss_colour_proxy() -> None:
    assert_vegetative_unit_leaf_harvest_uses_corresponding_truss_colour_proxy()


def test_max_lai_pruning_flow_can_partially_remove_leaf_mass_to_hit_target_lai() -> None:
    assert_max_lai_pruning_flow_can_partially_remove_leaf_mass_to_hit_target_lai()
