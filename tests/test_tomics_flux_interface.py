from __future__ import annotations

from stomatal_optimiaztion.domains.tomato.tomics.flux import OptimizationRequest, run_stomatal_optimization


def test_run_stomatal_optimization_returns_nonnegative_target() -> None:
    out = run_stomatal_optimization(
        OptimizationRequest(
            theta_substrate=0.3,
            water_supply_stress=0.7,
            vpd_kpa=1.3,
            co2_air_ppm=420.0,
            fruit_sink_strength=0.6,
            vegetative_sink_strength=0.4,
            current_g_w=0.3,
        )
    )

    assert out.g_w_opt == 0.21
    assert out.lambda_wue == 1.0
    assert out.objective_value == 0.0


def test_run_stomatal_optimization_clamps_negative_target() -> None:
    out = run_stomatal_optimization(
        OptimizationRequest(
            theta_substrate=0.3,
            water_supply_stress=0.8,
            vpd_kpa=1.3,
            co2_air_ppm=420.0,
            fruit_sink_strength=0.6,
            vegetative_sink_strength=0.4,
            current_g_w=-0.3,
        )
    )

    assert out.g_w_opt == 0.0


def test_run_stomatal_optimization_clips_stress_gain_to_unit_interval() -> None:
    high = run_stomatal_optimization(
        OptimizationRequest(
            theta_substrate=0.3,
            water_supply_stress=1.5,
            vpd_kpa=1.3,
            co2_air_ppm=420.0,
            fruit_sink_strength=0.6,
            vegetative_sink_strength=0.4,
            current_g_w=0.3,
        )
    )
    low = run_stomatal_optimization(
        OptimizationRequest(
            theta_substrate=0.3,
            water_supply_stress=-0.2,
            vpd_kpa=1.3,
            co2_air_ppm=420.0,
            fruit_sink_strength=0.6,
            vegetative_sink_strength=0.4,
            current_g_w=0.3,
        )
    )

    assert high.g_w_opt == 0.3
    assert low.g_w_opt == 0.0
