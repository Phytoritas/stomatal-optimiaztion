from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from stomatal_optimiaztion.domains.tomato import ttdgm
from stomatal_optimiaztion.domains.tomato.ttdgm import (
    MODEL_NAME,
    GrowthDrivers,
    GrowthStepOutput,
    OrganAllocationFractions,
    OrganCarbonPools,
    validate_allocations,
)


def test_ttdgm_import_surface_exposes_model_name() -> None:
    assert MODEL_NAME == "tTDGM"
    assert ttdgm.MODEL_NAME == "tTDGM"


def test_ttdgm_contracts_store_values() -> None:
    pools = OrganCarbonPools(
        c_leaf=1.0,
        c_stem=2.0,
        c_root=3.0,
        c_fruit=4.0,
        c_nsc=0.5,
    )
    drivers = GrowthDrivers(
        water_supply_stress=0.8,
        e=0.02,
        g_w=0.3,
        a_n=1.5,
        r_d=0.1,
        t_air_c=24.0,
        theta_substrate=0.35,
    )
    output = GrowthStepOutput(
        pools=pools,
        g_leaf=0.0,
        g_stem=0.0,
        g_root=0.0,
        g_fruit=0.0,
    )

    assert pools.c_fruit == 4.0
    assert drivers.t_air_c == 24.0
    assert output.pools.c_nsc == 0.5
    assert output.g_fruit == 0.0


def test_ttdgm_contracts_are_frozen_dataclasses() -> None:
    pools = OrganCarbonPools(
        c_leaf=1.0,
        c_stem=2.0,
        c_root=3.0,
        c_fruit=4.0,
        c_nsc=0.5,
    )

    with pytest.raises(FrozenInstanceError):
        pools.c_leaf = 2.0  # type: ignore[misc]


def test_validate_allocations_requires_positive_unity_sum() -> None:
    assert validate_allocations(
        OrganAllocationFractions(0.25, 0.25, 0.25, 0.25)
    )
    assert not validate_allocations(
        OrganAllocationFractions(0.1, 0.1, 0.1, 0.1)
    )
    assert not validate_allocations(
        OrganAllocationFractions(0.0, 0.0, 0.0, 0.0)
    )
