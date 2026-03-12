from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from stomatal_optimiaztion.domains.tomato.tthorp.components.partitioning.fractions import (
    AllocationFractions,
)
from stomatal_optimiaztion.domains.tomato.tthorp.contracts import EnvStep


@runtime_checkable
class PartitionPolicy(Protocol):
    name: str

    def compute(
        self,
        *,
        env: EnvStep,
        state: object,
        sinks: Mapping[str, float],
        scheme: str,
        params: Mapping[str, object] | None = None,
    ) -> AllocationFractions:
        """Compute allocation fractions for one step."""


_SINK_BASED_ALIASES = {"sink_based", "sink-based", "sink", "legacy", "default"}
def build_partition_policy(name: str) -> PartitionPolicy:
    key = str(name).strip().lower()
    if key in _SINK_BASED_ALIASES:
        from stomatal_optimiaztion.domains.tomato.tthorp.components.partitioning.sink_based import (
            SinkBasedTomatoPolicy,
        )

        return SinkBasedTomatoPolicy()

    if key in {"thorp_veg", "thorp_vegetative", "thorp-opt", "thorp_opt"}:
        from stomatal_optimiaztion.domains.tomato.tthorp.components.partitioning.thorp_policies import (
            ThorpVegetativePolicy,
        )

        return ThorpVegetativePolicy()

    if key in {"thorp_fruit_veg", "thorp_fruitveg", "thorp_4pool"}:
        from stomatal_optimiaztion.domains.tomato.tthorp.components.partitioning.thorp_policies import (
            ThorpFruitVegPolicy,
        )

        return ThorpFruitVegPolicy()

    raise ValueError(f"Unknown partition policy name {name!r}.")


def coerce_partition_policy(policy: PartitionPolicy | str | None) -> PartitionPolicy:
    if policy is None:
        return build_partition_policy("sink_based")
    if isinstance(policy, str):
        return build_partition_policy(policy)
    if isinstance(policy, PartitionPolicy):
        return policy

    compute = getattr(policy, "compute", None)
    name = getattr(policy, "name", None)
    if callable(compute) and isinstance(name, str):
        return policy  # type: ignore[return-value]

    raise TypeError(
        "partition_policy must be a policy instance, a known policy name string, or None."
    )
