from __future__ import annotations

import numpy as np
import pytest

from stomatal_optimiaztion.domains.gosm import implemented_equations
from stomatal_optimiaztion.domains.gosm.model import (
    augmented_lagrangian,
    growth_from_turgor_profile,
)


def test_gosm_future_work_helpers_have_equation_tags() -> None:
    assert implemented_equations(growth_from_turgor_profile) == ("Eq.S10.1",)
    assert implemented_equations(augmented_lagrangian) == ("Eq.S10.2",)


def test_growth_from_turgor_profile_supports_legacy_alias() -> None:
    result = growth_from_turgor_profile(
        p_turgor=np.array([1.0, 2.0]),
        z_norm=np.array([0.0, 1.0]),
        phi_tilde=2.0,
        c_w=3.0,
        u_s=4.0,
        Gamma=1.5,
    )

    assert np.isclose(result, 0.375)


def test_growth_from_turgor_profile_validates_shape() -> None:
    with pytest.raises(ValueError, match="same shape"):
        growth_from_turgor_profile(
            p_turgor=np.array([1.0, 2.0]),
            z_norm=np.array([0.0]),
            phi_tilde=2.0,
            c_w=3.0,
            u_s=4.0,
            p_turgor_crit=1.5,
        )


def test_augmented_lagrangian_matches_baseline_formula() -> None:
    result = augmented_lagrangian(
        G=10.0,
        etas=np.array([0.5, 1.5]),
        X_dot=np.array([2.0, 4.0]),
        F=np.array([1.0, 1.0]),
    )

    assert np.isclose(result, 5.0)
