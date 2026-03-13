from __future__ import annotations

from importlib import import_module

import stomatal_optimiaztion.domains.thorp.model as model_pkg

allocation_module = import_module("stomatal_optimiaztion.domains.thorp.allocation")
growth_module = import_module("stomatal_optimiaztion.domains.thorp.growth")
hydraulics_module = import_module("stomatal_optimiaztion.domains.thorp.hydraulics")
radiation_module = import_module("stomatal_optimiaztion.domains.thorp.radiation")
soil_dynamics_module = import_module("stomatal_optimiaztion.domains.thorp.soil_dynamics")
soil_initialization_module = import_module(
    "stomatal_optimiaztion.domains.thorp.soil_initialization"
)


def test_model_package_reexports_grouped_helpers() -> None:
    assert model_pkg.AllocationFractions is allocation_module.AllocationFractions
    assert model_pkg.allocation_fractions is allocation_module.allocation_fractions
    assert model_pkg.GrowthState is growth_module.GrowthState
    assert model_pkg.grow is growth_module.grow
    assert model_pkg.StomataResult is hydraulics_module.StomataResult
    assert model_pkg.e_from_soil_to_root_collar is hydraulics_module.e_from_soil_to_root_collar
    assert model_pkg.stomata is hydraulics_module.stomata
    assert model_pkg.RadiationResult is radiation_module.RadiationResult
    assert model_pkg.radiation is radiation_module.radiation
    assert model_pkg.InitialSoilAndRoots is soil_initialization_module.InitialSoilAndRoots
    assert model_pkg.SoilGrid is soil_initialization_module.SoilGrid
    assert model_pkg.initial_soil_and_roots is soil_initialization_module.initial_soil_and_roots
    assert model_pkg.richards_equation is soil_dynamics_module.richards_equation
    assert model_pkg.soil_moisture is soil_dynamics_module.soil_moisture
