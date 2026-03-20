from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from stomatal_optimiaztion.domains.tomato.tomics.flux import (
    MODEL_NAME,
    OptimizationRequest,
    OptimizationResult,
    clamp_nonnegative,
)


def test_tomics_flux_import_surface_exposes_model_name() -> None:
    assert MODEL_NAME == "TOMICS-Flux"


def test_optimization_request_and_result_store_values() -> None:
    request = OptimizationRequest(
        theta_substrate=0.3,
        water_supply_stress=0.7,
        vpd_kpa=1.3,
        co2_air_ppm=420.0,
        fruit_sink_strength=0.6,
        vegetative_sink_strength=0.4,
        current_g_w=0.3,
    )
    result = OptimizationResult(g_w_opt=0.2, lambda_wue=1.0, objective_value=0.0)

    assert request.theta_substrate == 0.3
    assert request.current_g_w == 0.3
    assert result.g_w_opt == 0.2
    assert result.lambda_wue == 1.0


def test_tomics_flux_contracts_are_frozen_dataclasses() -> None:
    request = OptimizationRequest(
        theta_substrate=0.3,
        water_supply_stress=0.7,
        vpd_kpa=1.3,
        co2_air_ppm=420.0,
        fruit_sink_strength=0.6,
        vegetative_sink_strength=0.4,
        current_g_w=0.3,
    )

    with pytest.raises(FrozenInstanceError):
        request.current_g_w = 0.4  # type: ignore[misc]


def test_clamp_nonnegative() -> None:
    assert clamp_nonnegative(-1.0) == 0.0
    assert clamp_nonnegative(0.2) == 0.2
