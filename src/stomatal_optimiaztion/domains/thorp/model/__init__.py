"""Legacy THORP grouped model namespace."""

from __future__ import annotations

from stomatal_optimiaztion.domains.thorp.allocation import (
    AllocationFractions,
    allocation_fractions,
)
from stomatal_optimiaztion.domains.thorp.growth import GrowthState, grow
from stomatal_optimiaztion.domains.thorp.hydraulics import (
    StomataResult,
    e_from_soil_to_root_collar,
    stomata,
)
from stomatal_optimiaztion.domains.thorp.radiation import RadiationResult, radiation
from stomatal_optimiaztion.domains.thorp.soil_dynamics import richards_equation, soil_moisture
from stomatal_optimiaztion.domains.thorp.soil_initialization import (
    InitialSoilAndRoots,
    SoilGrid,
    initial_soil_and_roots,
)

__all__ = [
    "AllocationFractions",
    "GrowthState",
    "InitialSoilAndRoots",
    "RadiationResult",
    "SoilGrid",
    "StomataResult",
    "allocation_fractions",
    "e_from_soil_to_root_collar",
    "grow",
    "initial_soil_and_roots",
    "radiation",
    "richards_equation",
    "soil_moisture",
    "stomata",
]
