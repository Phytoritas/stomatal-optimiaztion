from __future__ import annotations

import warnings

import numpy as np

from stomatal_optimiaztion.domains.gosm import implemented_equations
from stomatal_optimiaztion.domains.gosm.model import (
    InstantaneousSolution,
    rad_hydr_grow_temp_cassimilation,
    update_carbon_assimilation_growth,
)
from stomatal_optimiaztion.domains.gosm.params import BaselineInputs


def test_gosm_instantaneous_has_equation_tags() -> None:
    assert implemented_equations(update_carbon_assimilation_growth) == ("Eq.S2.4a", "Eq.S2.4b")


def test_gosm_instantaneous_interpolates_zero_crossing() -> None:
    inputs = BaselineInputs.matlab_default()
    solution = update_carbon_assimilation_growth(
        eta=0.6,
        c_nsc=1.0,
        inputs=inputs,
        lambda_wue_vec=np.array([0.03, 0.0001, 0.0]),
        g0_vec=np.array([0.1, 0.2, 0.3]),
        a_n_vec=np.array([1.0, 2.0, 3.0]),
        e_vec=np.array([0.1, 0.2, 0.3]),
        g_c_vec=np.array([0.0, 0.5, 1.0]),
        vpd_vec=np.array([1.0, 1.1, 1.2]),
        psi_s_vec=np.array([-0.1, -0.2, -0.3]),
        psi_rc_vec=np.array([-0.01, -0.02, -0.03]),
        d_g0_d_e_vec=np.array([-100.0, -1.0, -0.1]),
    )

    assert isinstance(solution, InstantaneousSolution)
    assert np.isclose(solution.g_c, 0.49572584454497526)
    assert np.isclose(solution.lambda_wue, 0.0003555944962104797)
    assert np.isclose(solution.a_n, 1.9914516890899505)


def test_gosm_instantaneous_handles_all_negative_g_c() -> None:
    inputs = BaselineInputs.matlab_default()
    solution = update_carbon_assimilation_growth(
        eta=0.6,
        c_nsc=1.0,
        inputs=inputs,
        lambda_wue_vec=np.array([0.03, 0.02]),
        g0_vec=np.array([0.1, 0.2]),
        a_n_vec=np.array([1.0, 2.0]),
        e_vec=np.array([0.1, 0.2]),
        g_c_vec=np.array([-0.5, -0.1]),
        vpd_vec=np.array([1.0, 1.1]),
        psi_s_vec=np.array([-0.1, -0.2]),
        psi_rc_vec=np.array([-0.01, -0.02]),
        d_g0_d_e_vec=np.array([-1.0, -0.5]),
    )

    assert np.isnan(solution.g_c)
    assert np.isnan(solution.a_n)
    assert np.isnan(solution.lambda_wue)


def test_gosm_instantaneous_bisects_lambda_zero_runtime_path() -> None:
    inputs = BaselineInputs.matlab_default()
    runtime = rad_hydr_grow_temp_cassimilation(np.linspace(1e-6, 4e-4, 9), inputs=inputs)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        solution = update_carbon_assimilation_growth(
            eta=0.8,
            c_nsc=1.0,
            inputs=inputs,
            lambda_wue_vec=runtime[6],
            g0_vec=runtime[3],
            a_n_vec=runtime[1],
            e_vec=runtime[0],
            g_c_vec=runtime[5],
            vpd_vec=runtime[12],
            psi_s_vec=runtime[9],
            psi_rc_vec=runtime[10],
            d_g0_d_e_vec=runtime[7],
        )

    assert solution.lambda_wue == 0.0
    assert np.isclose(solution.e, 0.004752929687500001)
    assert np.isclose(solution.g_c, 0.42066894207445893)
    assert np.isclose(solution.psi_s, -1.904133865563872)
