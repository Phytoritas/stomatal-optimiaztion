from __future__ import annotations

import pytest

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
    VegetativeUnitPruningPolicy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.registry import (
    build_fruit_harvest_policy,
    build_leaf_harvest_policy,
)


@pytest.mark.parametrize(
    ("family", "expected_type"),
    [
        ("tomsim_truss", TomsimTrussHarvestPolicy),
        ("tomgro_ageclass", TomgroAgeclassHarvestPolicy),
        ("dekoning_fds", DeKoningFdsHarvestPolicy),
        ("vanthoor_boxcar", VanthoorBoxcarHarvestPolicy),
    ],
)
def test_fruit_harvest_registry_resolves_canonical_families(
    family: str,
    expected_type: type[object],
) -> None:
    policy = build_fruit_harvest_policy(family)
    assert isinstance(policy, expected_type)


@pytest.mark.parametrize(
    ("family", "expected_type"),
    [
        ("linked_truss_stage", LinkedTrussStageLeafHarvestPolicy),
        ("vegetative_unit_pruning", VegetativeUnitPruningPolicy),
        ("max_lai_pruning_flow", MaxLaiPruningFlowPolicy),
        ("age_senescence_management", VegetativeUnitPruningPolicy),
    ],
)
def test_leaf_harvest_registry_resolves_canonical_families(
    family: str,
    expected_type: type[object],
) -> None:
    policy = build_leaf_harvest_policy(family)
    assert isinstance(policy, expected_type)


def test_harvest_registry_rejects_unknown_families() -> None:
    with pytest.raises(KeyError, match="Unknown fruit harvest family"):
        build_fruit_harvest_policy("unknown_fruit_family")
    with pytest.raises(KeyError, match="Unknown leaf harvest family"):
        build_leaf_harvest_policy("unknown_leaf_family")
