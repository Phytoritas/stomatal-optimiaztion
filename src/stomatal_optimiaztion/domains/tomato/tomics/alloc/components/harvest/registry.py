from __future__ import annotations

from collections.abc import Callable

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
    VegetativeUnitPruningPolicy,
    MaxLaiPruningFlowPolicy,
)


FRUIT_HARVEST_REGISTRY: dict[str, Callable[..., object]] = {
    "tomsim_truss": TomsimTrussHarvestPolicy,
    "tomgro_ageclass": TomgroAgeclassHarvestPolicy,
    "dekoning_fds": DeKoningFdsHarvestPolicy,
    "vanthoor_boxcar": VanthoorBoxcarHarvestPolicy,
}

LEAF_HARVEST_REGISTRY: dict[str, Callable[..., object]] = {
    "linked_truss_stage": LinkedTrussStageLeafHarvestPolicy,
    "vegetative_unit_pruning": VegetativeUnitPruningPolicy,
    "max_lai_pruning_flow": MaxLaiPruningFlowPolicy,
    "age_senescence_management": VegetativeUnitPruningPolicy,
}


def build_fruit_harvest_policy(name: str, **params: object) -> object:
    key = str(name).strip().lower()
    if key not in FRUIT_HARVEST_REGISTRY:
        raise KeyError(f"Unknown fruit harvest family: {name!r}")
    return FRUIT_HARVEST_REGISTRY[key](**params)


def build_leaf_harvest_policy(name: str, **params: object) -> object:
    key = str(name).strip().lower()
    if key not in LEAF_HARVEST_REGISTRY:
        raise KeyError(f"Unknown leaf harvest family: {name!r}")
    return LEAF_HARVEST_REGISTRY[key](**params)


def get_fruit_harvest_policy(name: str, params: dict[str, object] | None = None) -> object:
    return build_fruit_harvest_policy(name, **(params or {}))


def get_leaf_harvest_policy(name: str, params: dict[str, object] | None = None) -> object:
    return build_leaf_harvest_policy(name, **(params or {}))


__all__ = [
    "FRUIT_HARVEST_REGISTRY",
    "LEAF_HARVEST_REGISTRY",
    "build_fruit_harvest_policy",
    "build_leaf_harvest_policy",
    "get_fruit_harvest_policy",
    "get_leaf_harvest_policy",
]
