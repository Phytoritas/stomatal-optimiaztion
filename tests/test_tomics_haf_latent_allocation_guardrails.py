import pandas as pd

from tomics_haf_latent_fixtures import latent_config

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.guardrails import (
    evaluate_latent_allocation_guardrails,
)


def _posterior(**overrides):
    base = {
        "date": "2025-12-14",
        "loadcell_id": 1,
        "treatment": "Control",
        "prior_family": "legacy_tomato_prior",
        "inferred_u_fruit": 0.55,
        "inferred_u_leaf": 0.20,
        "inferred_u_stem": 0.16,
        "inferred_u_root": 0.09,
        "legacy_prior_u_fruit": 0.55,
        "legacy_prior_u_root": 0.09,
        "RZI_main": 0.3,
        "LAI_proxy_available": False,
        "LAI_proxy_value": float("nan"),
        "allocation_sum_error": 0.0,
        "raw_THORP_allocator_used": False,
    }
    base.update(overrides)
    return pd.DataFrame([base])


def _status(guardrails: pd.DataFrame, name: str) -> bool:
    return bool(guardrails.loc[guardrails["guardrail_name"].eq(name), "pass_fail"].iloc[0])


def test_guardrails_detect_leaf_collapse() -> None:
    guardrails = evaluate_latent_allocation_guardrails(
        _posterior(inferred_u_leaf=0.05),
        {},
        latent_config(),
    )

    assert _status(guardrails, "no_leaf_collapse") is False


def test_guardrails_detect_wet_root_excess() -> None:
    guardrails = evaluate_latent_allocation_guardrails(
        _posterior(RZI_main=0.01, inferred_u_root=0.20),
        {},
        latent_config(),
    )

    assert _status(guardrails, "no_wet_root_excess") is False


def test_guardrails_detect_stress_gate_violation() -> None:
    guardrails = evaluate_latent_allocation_guardrails(
        _posterior(RZI_main=0.10, inferred_u_root=0.15, legacy_prior_u_root=0.09),
        {},
        latent_config(),
    )

    assert _status(guardrails, "stress_gated_root_increase") is False


def test_no_raw_thorp_and_no_fruit_calibration_pass_when_absent() -> None:
    guardrails = evaluate_latent_allocation_guardrails(_posterior(), {}, latent_config())

    assert _status(guardrails, "no_raw_THORP") is True
    assert _status(guardrails, "no_fruit_diameter_calibration") is True
