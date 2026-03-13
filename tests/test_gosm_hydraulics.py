from __future__ import annotations

import numpy as np
import pytest

from stomatal_optimiaztion.domains.gosm import implemented_equations
from stomatal_optimiaztion.domains.gosm.model import hydraulics
from stomatal_optimiaztion.domains.gosm.params import BaselineInputs


def test_hydraulics_has_equation_tags() -> None:
    assert implemented_equations(hydraulics) == (
        "Eq.S5.1",
        "Eq.S5.2",
        "Eq.S5.3",
        "Eq.S5.4",
        "Eq.S5.5",
        "Eq.S5.6",
        "Eq.S5.7",
        "Eq.S5.8",
        "Eq.S5.9",
        "Eq.S5.10",
        "Eq.S5.11",
        "Eq.S5.12",
        "Eq.S6.1",
        "Eq.S6.2",
        "Eq.S6.3",
        "Eq.S6.4",
        "Eq.S6.5",
        "Eq.S6.6",
        "Eq.S6.7",
        "Eq.S6.8",
        "Eq.S6.9",
        "Eq.S6.10",
        "Eq.S6.11",
        "Eq.S6.12",
        "Eq.S6.13",
        "Eq.S6.14",
        "Eq.S6.15",
    )


def test_hydraulics_matches_baseline_snapshot() -> None:
    inputs = BaselineInputs.matlab_default()

    result = hydraulics(np.array([1e-5, 2e-5]), inputs=inputs)
    e_vec, psi_rc_vec, psi_s_vec, g0_vec, d_g0_d_e_vec, inf_nsc_turgor_ave_vec, z_norm_plus_vec, turgor_turgid = result

    assert np.allclose(e_vec, np.array([1.0e-05, 2.0e-05]))
    assert np.allclose(psi_rc_vec, np.array([-0.03154853, -0.0337263]))
    assert np.allclose(psi_s_vec, np.array([-0.16915447, -0.171873]))
    assert np.allclose(g0_vec, np.array([6.75484201e-05, 6.73209135e-05]))
    assert np.allclose(d_g0_d_e_vec, np.array([-0.02274908, -0.02275223]))
    assert np.allclose(inf_nsc_turgor_ave_vec, np.array([1.19450152, 1.19300441]))
    assert np.allclose(z_norm_plus_vec, np.array([0.0, 0.0]))
    assert turgor_turgid == pytest.approx(1.2358066082517578)


def test_hydraulics_preserves_vector_shapes() -> None:
    inputs = BaselineInputs.matlab_default()
    result = hydraulics(np.array([1e-5, 2e-5, 3e-5]), inputs=inputs)

    for array_result in result[:-1]:
        assert array_result.shape == (3,)
    assert result[-1] > 0.0
