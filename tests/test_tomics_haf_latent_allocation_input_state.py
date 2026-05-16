from tomics_haf_latent_fixtures import feature_frame, latent_config, observer_metadata

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.input_state import (
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
