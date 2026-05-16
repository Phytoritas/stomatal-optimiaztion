import pytest

from tomics_haf_latent_fixtures import feature_frame, latent_config, observer_metadata

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.input_state import (
    build_latent_allocation_input_state,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.inference import (
    infer_latent_allocation,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.priors import (
    build_latent_allocation_priors,
)


def _posteriors():
    state, _ = build_latent_allocation_input_state(feature_frame(), observer_metadata(), latent_config())
    priors = build_latent_allocation_priors(state, latent_config())
    return infer_latent_allocation(priors, latent_config())


def test_prior_weighted_softmax_returns_valid_allocations() -> None:
    posteriors = _posteriors()

    assert not posteriors.empty
    assert (posteriors["allocation_sum_error"] < 1e-6).all()
    for column in ["inferred_u_fruit", "inferred_u_leaf", "inferred_u_stem", "inferred_u_root"]:
        assert ((posteriors[column] >= 0.0) & (posteriors[column] <= 1.0)).all()


def test_low_pass_memory_applies_by_loadcell_without_leakage() -> None:
    posteriors = _posteriors()
    legacy_lc1 = posteriors[
        posteriors["prior_family"].eq("legacy_tomato_prior") & posteriors["loadcell_id"].eq(1)
    ].sort_values("date")
    legacy_lc4 = posteriors[
        posteriors["prior_family"].eq("legacy_tomato_prior") & posteriors["loadcell_id"].eq(4)
    ].sort_values("date")

    assert legacy_lc1.iloc[0]["low_pass_u_root"] == pytest.approx(legacy_lc1.iloc[0]["constrained_u_root"])
    assert legacy_lc4.iloc[0]["low_pass_u_root"] == pytest.approx(legacy_lc4.iloc[0]["constrained_u_root"])
    assert legacy_lc1.iloc[0]["low_pass_u_root"] != pytest.approx(legacy_lc4.iloc[0]["low_pass_u_root"])


def test_constraints_hold_after_low_pass() -> None:
    posteriors = _posteriors()

    assert (posteriors["inferred_u_leaf"] >= 0.12 - 1e-9).all()
    assert (posteriors["inferred_u_root"] <= 0.25 + 1e-9).all()
