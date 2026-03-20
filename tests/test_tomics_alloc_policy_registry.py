from __future__ import annotations

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning import (
    SinkBasedTomatoPolicy,
    ThorpFruitVegPolicy,
    ThorpVegetativePolicy,
    TomicsPolicy,
    build_partition_policy,
)


def test_policy_registry_preserves_existing_aliases_and_adds_tomics() -> None:
    assert isinstance(build_partition_policy("legacy"), SinkBasedTomatoPolicy)
    assert isinstance(build_partition_policy("default"), SinkBasedTomatoPolicy)
    assert isinstance(build_partition_policy("thorp_veg"), ThorpVegetativePolicy)
    assert isinstance(build_partition_policy("thorp_fruit_veg"), ThorpFruitVegPolicy)
    assert isinstance(build_partition_policy("thorp_4pool"), ThorpFruitVegPolicy)
    assert isinstance(build_partition_policy("tomics"), TomicsPolicy)
    assert isinstance(build_partition_policy("tomics_alloc"), TomicsPolicy)
    assert isinstance(build_partition_policy("tomics_hybrid"), TomicsPolicy)
