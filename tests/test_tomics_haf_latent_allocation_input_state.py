from tomics_haf_latent_fixtures import feature_frame, latent_config, observer_metadata

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.input_state import (
    LatentAllocationInputState,
    build_latent_allocation_input_state,
    check_production_preconditions,
)


def test_latent_input_state_precondition_passes_for_production_metadata() -> None:
    passed, details = check_production_preconditions(observer_metadata(), latent_config())

    assert passed is True
    assert details["production_observer_precondition_passed"] is True


def test_latent_input_state_fails_safely_when_row_cap_applied() -> None:
    frame, meta = build_latent_allocation_input_state(
        feature_frame(),
        observer_metadata(row_cap_applied=True),
        latent_config(),
    )

    assert frame.empty
    assert meta["latent_allocation_ready"] is False
    assert "row_cap_applied" in meta["precondition_failure_reasons"]


def test_latent_input_state_marks_fruit_diameter_diagnostic_only() -> None:
    frame, meta = build_latent_allocation_input_state(feature_frame(), observer_metadata(), latent_config())

    assert meta["latent_allocation_ready"] is True
    assert frame["fruit_diameter_diagnostic_only"].all()
    assert not frame["fruit_diameter_p_values_allowed"].any()
    assert not frame["fruit_diameter_allocation_calibration_target"].any()
    assert not frame["direct_partition_observation_available"].any()
    assert set(frame["allocation_validation_basis"]) == {"latent_inference_from_observer_features"}


def test_latent_allocation_input_state_contract_symbol_exists() -> None:
    state = LatentAllocationInputState(
        date="2025-12-14",
        loadcell_id=1,
        treatment="Control",
        threshold_w_m2=0.0,
        radiation_day_ET_g=120.0,
        radiation_night_ET_g=25.0,
        radiation_total_ET_g=145.0,
        day_fraction_ET=0.82,
        night_fraction_ET=0.18,
        day_radiation_integral_MJ_m2=12.0,
        day_radiation_mean_wm2=300.0,
        RZI_main=0.02,
        RZI_main_source="theta_group",
        RZI_theta_paired=0.0,
        RZI_theta_group=0.0,
        tensiometer_available=True,
        tensiometer_coverage_fraction=1.0,
        apparent_canopy_conductance=60.0,
        apparent_canopy_conductance_available=True,
        day_vpd_kpa_mean=2.0,
        source_proxy_MJ_CO2_T=12.0,
        source_proxy_MJ_CO2_T_available=True,
        LAI_available=False,
        LAI_proxy_available=True,
        LAI_proxy_value=3.0,
        direct_partition_observation_available=False,
        allocation_validation_basis="latent_inference_from_observer_features",
    )

    assert state.date == "2025-12-14"
    assert state.direct_partition_observation_available is False
