from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OrganCarbonPools:
    c_leaf: float
    c_stem: float
    c_root: float
    c_fruit: float
    c_nsc: float


@dataclass(frozen=True, slots=True)
class GrowthDrivers:
    water_supply_stress: float
    e: float
    g_w: float
    a_n: float
    r_d: float
    t_air_c: float
    theta_substrate: float


@dataclass(frozen=True, slots=True)
class OrganAllocationFractions:
    u_leaf: float
    u_stem: float
    u_root: float
    u_fruit: float


@dataclass(frozen=True, slots=True)
class GrowthStepOutput:
    pools: OrganCarbonPools
    g_leaf: float
    g_stem: float
    g_root: float
    g_fruit: float


def validate_allocations(alloc: OrganAllocationFractions) -> bool:
    total = alloc.u_leaf + alloc.u_stem + alloc.u_root + alloc.u_fruit
    if total <= 0:
        return False
    return abs(total - 1.0) <= 1e-8
