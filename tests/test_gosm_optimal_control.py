from __future__ import annotations

import numpy as np
import pytest

from stomatal_optimiaztion.domains.gosm import implemented_equations
from stomatal_optimiaztion.domains.gosm.model import (
    chi_w,
    eta_dot,
    eta_from_marginals,
    lagrangian,
    objective_total_growth,
    theta_cost,
)


def test_objective_total_growth_has_equation_tag_and_matches_snapshot() -> None:
    result = objective_total_growth(G=np.array([1.0, 2.0, 3.0]), dt=0.5)

    assert implemented_equations(objective_total_growth) == ("Eq.S2.1",)
    assert result == pytest.approx(3.0)


def test_lagrangian_has_equation_tag_and_matches_snapshot() -> None:
    result = lagrangian(G=2.0, C_dot=1.0, F_C=0.25, eta=0.5)

    assert implemented_equations(lagrangian) == ("Eq.S2.2",)
    assert result == pytest.approx(1.625)


def test_eta_from_marginals_supports_vector_inputs() -> None:
    result = eta_from_marginals(dGdE=np.array([-2.0, -4.0]), lambda_wue=np.array([0.5, 1.0]), a_L=2.0, f_c=0.25)

    assert implemented_equations(eta_from_marginals) == ("Eq.S2.3",)
    assert np.allclose(result, np.array([0.5454545454545454, 0.5454545454545454]))


def test_chi_w_and_theta_cost_match_snapshots() -> None:
    chi = chi_w(eta=0.6, dGdE=np.array([-2.0, -1.0]), a_L=2.0, f_c=0.25)
    theta = theta_cost(eta=0.6, G=np.array([1.5, 0.5]), a_L=2.0, f_c=0.25)

    assert implemented_equations(chi_w) == ("Eq.S2.4a",)
    assert implemented_equations(theta_cost) == ("Eq.S2.5",)
    assert np.allclose(chi, np.array([0.33333333333333337, 0.16666666666666669]))
    assert np.allclose(theta, np.array([-0.25, -0.08333333333333333]))


def test_eta_dot_supports_vector_inputs() -> None:
    result = eta_dot(eta=0.6, dR_MdC=np.array([0.1, 0.2]), dGdC=np.array([0.4, 0.5]), f_c=0.25)

    assert implemented_equations(eta_dot) == ("Eq.S2.6",)
    assert np.allclose(result, np.array([-0.02, 0.02]))
