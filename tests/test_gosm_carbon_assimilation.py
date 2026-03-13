from __future__ import annotations

import numpy as np
import pytest

from stomatal_optimiaztion.domains.gosm import implemented_equations
from stomatal_optimiaztion.domains.gosm.model import (
    carbon_assimilation,
    conductances_and_temperature,
    radiation_absorbed,
)
from stomatal_optimiaztion.domains.gosm.params import BaselineInputs


def test_carbon_assimilation_has_equation_tags() -> None:
    assert implemented_equations(carbon_assimilation) == (
        "Eq.S4.1",
        "Eq.S4.2",
        "Eq.S4.2_quadratic",
        "Eq.S4.3",
        "Eq.S4.4",
        "Eq.S4.Rd_Q10",
        "Eq.S4.JI",
        "Eq.S4.5",
        "Eq.S4.6",
        "Eq.S4.7",
        "Eq.S4.8",
        "Eq.S4.9",
        "Eq.S4.10",
        "Eq.S4.11",
        "Eq.S4.12",
        "Eq.S4.13",
        "Eq.S4.14",
        "Eq.S4.15",
        "Eq.S4.16",
        "Eq.S4.17",
        "Eq.S4.18",
    )


def test_carbon_assimilation_matches_baseline_snapshot() -> None:
    inputs = BaselineInputs.matlab_default()
    r_abs = radiation_absorbed(
        r_incom=inputs.r_incom,
        z_a=inputs.z_a,
        la=inputs.la,
        w=inputs.w,
        kappa_l=inputs.kappa_l,
        phi_l=inputs.phi_l,
    )
    t_l_vec, _, g_c_vec, _, d_e_d_g_w_vec, d_g_w_d_g_c_vec, _, latent_heat = conductances_and_temperature(
        e_vec=np.array([1e-5, 2e-5]),
        d_g0_d_e_vec=np.array([0.1, 0.2]),
        inputs=inputs,
        r_abs=r_abs,
    )

    a_n_vec, r_d_vec, lambda_wue_vec = carbon_assimilation(
        g_c_vec,
        t_l_vec,
        inputs=inputs,
        r_abs=r_abs,
        L=latent_heat,
        d_e_d_g_w_vec=d_e_d_g_w_vec,
        d_g_w_d_g_c_vec=d_g_w_d_g_c_vec,
    )

    assert np.allclose(a_n_vec, np.array([2.04636045e-07, 4.07289305e-07]))
    assert np.allclose(r_d_vec, np.array([1.07655023e-06, 1.07611806e-06]))
    assert np.allclose(lambda_wue_vec, np.array([0.02036628, 0.02016294]))


def test_carbon_assimilation_handles_zero_conductance_without_nan() -> None:
    inputs = BaselineInputs.matlab_default()

    a_n_vec, r_d_vec, lambda_wue_vec = carbon_assimilation(
        np.array([0.0]),
        np.array([25.0]),
        inputs=inputs,
        r_abs=0.0,
        L=43964.056736813334,
        d_e_d_g_w_vec=np.array([1.0]),
        d_g_w_d_g_c_vec=np.array([1.0]),
    )

    assert a_n_vec[0] == pytest.approx(-r_d_vec[0])
    assert lambda_wue_vec[0] == pytest.approx(5.96794646e-05)
