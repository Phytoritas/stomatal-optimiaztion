from __future__ import annotations

from stomatal_optimiaztion.domains.tomato.ttdgm.contracts import (
    GrowthDrivers,
    GrowthStepOutput,
    OrganAllocationFractions,
    OrganCarbonPools,
    validate_allocations,
)


def run_growth_step(
    *,
    pools: OrganCarbonPools,
    drivers: GrowthDrivers,
    allocations: OrganAllocationFractions,
) -> GrowthStepOutput:
    """tTDGM step contract.

    Placeholder implementation that preserves pool values and exposes explicit
    organ growth channels (leaf/stem/root/fruit) for tomato.
    """

    if not validate_allocations(allocations):
        raise ValueError("Organ allocations must sum to 1.0.")

    return GrowthStepOutput(
        pools=pools,
        g_leaf=0.0,
        g_stem=0.0,
        g_root=0.0,
        g_fruit=0.0,
    )
