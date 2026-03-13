from __future__ import annotations

from importlib import import_module

from stomatal_optimiaztion.domains.thorp.params import THORPParams, default_params

params_module = import_module("stomatal_optimiaztion.domains.thorp.params")
soil_hydraulics_module = import_module("stomatal_optimiaztion.domains.thorp.soil_hydraulics")
soil_initialization_module = import_module(
    "stomatal_optimiaztion.domains.thorp.soil_initialization"
)
vulnerability_module = import_module("stomatal_optimiaztion.domains.thorp.vulnerability")


def test_params_module_reexports_legacy_types() -> None:
    assert params_module.SoilHydraulics is soil_hydraulics_module.SoilHydraulics
    assert params_module.BottomBoundaryCondition is soil_initialization_module.BottomBoundaryCondition
    assert params_module.WeibullVC is vulnerability_module.WeibullVC


def test_params_default_params_returns_flat_legacy_bundle() -> None:
    params = default_params()

    assert isinstance(params, THORPParams)
    assert params.run_name == "0.6RH"
    assert params.forcing_repeat_q == 15
