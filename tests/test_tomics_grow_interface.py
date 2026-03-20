from __future__ import annotations

import pytest

from stomatal_optimiaztion.domains.tomato.tomics.grow import (
    GrowthDrivers,
    OrganAllocationFractions,
    OrganCarbonPools,
    run_growth_step,
)


def test_run_growth_step_preserves_pools_and_exposes_fruit_channel() -> None:
    pools = OrganCarbonPools(
        c_leaf=1.0,
        c_stem=1.0,
        c_root=1.0,
        c_fruit=1.0,
        c_nsc=0.5,
    )

    output = run_growth_step(
        pools=pools,
        drivers=GrowthDrivers(
            water_supply_stress=0.8,
            e=0.0,
            g_w=0.0,
            a_n=0.0,
            r_d=0.0,
            t_air_c=24.0,
            theta_substrate=0.35,
        ),
        allocations=OrganAllocationFractions(0.25, 0.25, 0.25, 0.25),
    )

    assert output.pools is pools
    assert output.g_leaf == 0.0
    assert output.g_stem == 0.0
    assert output.g_root == 0.0
    assert output.g_fruit == 0.0
    assert output.pools.c_fruit == 1.0


def test_run_growth_step_rejects_invalid_allocations() -> None:
    pools = OrganCarbonPools(
        c_leaf=1.0,
        c_stem=1.0,
        c_root=1.0,
        c_fruit=1.0,
        c_nsc=0.5,
    )

    with pytest.raises(ValueError, match="sum to 1.0"):
        run_growth_step(
            pools=pools,
            drivers=GrowthDrivers(
                water_supply_stress=0.8,
                e=0.0,
                g_w=0.0,
                a_n=0.0,
                r_d=0.0,
                t_air_c=24.0,
                theta_substrate=0.35,
            ),
            allocations=OrganAllocationFractions(0.1, 0.1, 0.1, 0.1),
        )
