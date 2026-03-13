from __future__ import annotations

import numpy as np
import pytest

from stomatal_optimiaztion.domains.gosm import implemented_equations
from stomatal_optimiaztion.domains.gosm.model import (
    conductances_and_temperature,
    radiation_absorbed,
)
from stomatal_optimiaztion.domains.gosm.params import BaselineInputs


def test_conductances_and_temperature_has_equation_tags() -> None:
    assert implemented_equations(conductances_and_temperature) == (
        "Eq.S3.1",
        "Eq.S3.3",
        "Eq.S3.4",
        "Eq.S3.5",
        "Eq.S3.6",
        "Eq.S3.7",
        "Eq.S3.8",
        "Eq.S3.9",
        "Eq.S3.10",
    )


def test_conductances_and_temperature_matches_baseline_snapshot() -> None:
    inputs = BaselineInputs.matlab_default()
    r_abs = radiation_absorbed(
        r_incom=inputs.r_incom,
        z_a=inputs.z_a,
        la=inputs.la,
        w=inputs.w,
        kappa_l=inputs.kappa_l,
        phi_l=inputs.phi_l,
    )

    result = conductances_and_temperature(
        e_vec=np.array([1e-5, 2e-5]),
        d_g0_d_e_vec=np.array([0.1, 0.2]),
        inputs=inputs,
        r_abs=r_abs,
    )

    t_l_vec, g_w_vec, g_c_vec, vpd_vec, d_e_d_g_w_vec, d_g_w_d_g_c_vec, d_g0_d_g_c_vec, latent_heat = result

    assert np.allclose(t_l_vec, np.array([20.34864434, 20.34285155]))
    assert np.allclose(g_w_vec, np.array([0.00090335, 0.00180876]))
    assert np.allclose(g_c_vec, np.array([0.00056441, 0.00112975]))
    assert np.allclose(vpd_vec, np.array([1.12207713, 1.12122285]))
    assert np.allclose(d_e_d_g_w_vec, np.array([0.01105726, 0.01103208]))
    assert np.allclose(d_g_w_d_g_c_vec, np.array([1.60103149, 1.60206567]))
    assert np.allclose(d_g0_d_g_c_vec, np.array([0.0017703, 0.00353482]))
    assert latent_heat == pytest.approx(43964.056736813334)


def test_conductances_and_temperature_preserves_vector_shapes() -> None:
    inputs = BaselineInputs.matlab_default()
    r_abs = radiation_absorbed(
        r_incom=inputs.r_incom,
        z_a=inputs.z_a,
        la=inputs.la,
        w=inputs.w,
        kappa_l=inputs.kappa_l,
        phi_l=inputs.phi_l,
    )

    result = conductances_and_temperature(
        e_vec=np.array([1e-5, 2e-5, 3e-5]),
        d_g0_d_e_vec=np.array([0.1, 0.2, 0.3]),
        inputs=inputs,
        r_abs=r_abs,
    )

    for array_result in result[:-1]:
        assert array_result.shape == (3,)
    assert result[-1] > 0.0
