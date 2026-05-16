import pytest

from tomics_haf_latent_fixtures import feature_frame, latent_config, observer_metadata

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.contracts import (
    ORGAN_NAMES,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.input_state import (
    build_latent_allocation_input_state,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.priors import (
    build_latent_allocation_priors,
    validate_prior_families,
)


def test_prior_families_return_nonnegative_sum_to_one() -> None:
    state, _ = build_latent_allocation_input_state(feature_frame(), observer_metadata(), latent_config())
    priors = build_latent_allocation_priors(state, latent_config())

    assert set(priors["prior_family"]) == {
        "legacy_tomato_prior",
        "thorp_bounded_prior",
        "tomato_constrained_thorp_prior",
    }
    for _, row in priors.iterrows():
        values = [row[f"u_{organ}_prior"] for organ in ORGAN_NAMES]
        assert all(value >= 0.0 for value in values)
        assert sum(values) == pytest.approx(1.0)


def test_legacy_prior_preserves_tomato_fruit_gate() -> None:
    state, _ = build_latent_allocation_input_state(feature_frame(), observer_metadata(), latent_config())
    priors = build_latent_allocation_priors(state, latent_config())
    legacy = priors[priors["prior_family"].eq("legacy_tomato_prior")]

    assert (legacy["u_fruit_prior"] >= 0.45).all()


def test_thorp_bounded_prior_respects_root_cap_and_fruit_gate() -> None:
    state, _ = build_latent_allocation_input_state(feature_frame(), observer_metadata(), latent_config())
    priors = build_latent_allocation_priors(state, latent_config())
    thorp = priors[priors["prior_family"].eq("thorp_bounded_prior")]
    hybrid = priors[priors["prior_family"].eq("tomato_constrained_thorp_prior")]

    assert (thorp["u_root_prior"] <= 0.25 + 1e-9).all()
    assert (hybrid["u_fruit_prior"] >= hybrid["legacy_prior_u_fruit"] - 1e-9).all()


def test_prior_family_contract_rejects_missing_or_unknown_family() -> None:
    with pytest.raises(ValueError, match="unknown prior families"):
        validate_prior_families(("legacy_tomato_prior", "typo_prior"))
    with pytest.raises(ValueError, match="missing required prior families"):
        validate_prior_families(("legacy_tomato_prior",))
