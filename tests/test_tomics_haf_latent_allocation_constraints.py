import pytest

from tomics_haf_latent_fixtures import latent_config

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.constraints import (
    apply_tomato_constraints,
    normalize_allocation_fractions,
)


def test_leaf_floor_prevents_collapse_and_sum_normalizes() -> None:
    row = {"RZI_main": 0.3, "legacy_prior_u_fruit": 0.55, "legacy_prior_u_root": 0.09}
    constrained = apply_tomato_constraints(
        {"fruit": 0.80, "leaf": 0.01, "stem": 0.12, "root": 0.07},
        row,
        latent_config(),
    )

    assert constrained["leaf"] >= 0.12
    assert sum(constrained.values()) == pytest.approx(1.0)


def test_wet_root_cap_applies_when_rzi_low() -> None:
    row = {"RZI_main": 0.01, "legacy_prior_u_fruit": 0.55, "legacy_prior_u_root": 0.20}
    constrained = apply_tomato_constraints(
        {"fruit": 0.55, "leaf": 0.15, "stem": 0.10, "root": 0.20},
        row,
        latent_config(),
    )

    assert constrained["root"] <= 0.12 + 1e-9


def test_root_increase_clipped_when_stress_below_activation() -> None:
    row = {"RZI_main": 0.10, "legacy_prior_u_fruit": 0.55, "legacy_prior_u_root": 0.08}
    constrained = apply_tomato_constraints(
        {"fruit": 0.55, "leaf": 0.14, "stem": 0.11, "root": 0.20},
        row,
        latent_config(),
    )

    assert constrained["root"] <= 0.08 + 1e-9


def test_normalize_allocation_fractions_handles_zero_input() -> None:
    normalized = normalize_allocation_fractions({"fruit": 0, "leaf": 0, "stem": 0, "root": 0})

    assert sum(normalized.values()) == pytest.approx(1.0)
    assert all(value >= 0 for value in normalized.values())
