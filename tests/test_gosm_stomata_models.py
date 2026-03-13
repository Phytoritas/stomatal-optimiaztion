from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.gosm import implemented_equations
from stomatal_optimiaztion.domains.gosm.model import (
    rad_hydr_grow_temp_cassimilation,
    stomata_anderegg_2018,
    stomata_cowan_and_farquhar_1977,
    stomata_maximize_assimilation,
    stomata_prentice_2014,
    stomata_wang_2020,
)
from stomatal_optimiaztion.domains.gosm.params import BaselineInputs


def _baseline_runtime_sweep() -> dict[str, np.ndarray]:
    inputs = BaselineInputs.matlab_default()
    result = rad_hydr_grow_temp_cassimilation(np.linspace(1e-6, 4e-4, 9), inputs=inputs)
    return {
        "inputs": inputs,
        "e_vec": result[0],
        "a_n_vec": result[1],
        "g_c_vec": result[5],
        "lambda_wue_vec": result[6],
        "psi_s_vec": result[9],
        "psi_rc_vec": result[10],
        "t_l_vec": result[11],
    }


def test_gosm_stomata_models_have_equation_tags() -> None:
    assert implemented_equations(stomata_cowan_and_farquhar_1977) == ("Eq.S2.4b", "Eq.S7.1")
    assert implemented_equations(stomata_prentice_2014) == ("Eq.S2.4b", "Eq.S7.2", "Eq.S7.3", "Eq.S7.4")
    assert implemented_equations(stomata_anderegg_2018) == ("Eq.S2.4b", "Eq.S7.12b", "Eq.S7.13")
    assert implemented_equations(stomata_wang_2020) == ("Eq.S2.4b", "Eq.S7.17", "Eq.S7.18")
    assert implemented_equations(stomata_maximize_assimilation) == ("Eq.S7.14",)


def test_cowan_model_interpolates_zero_crossing() -> None:
    solution = stomata_cowan_and_farquhar_1977(
        e_vec=np.array([0.0, 1.0, 2.0]),
        g_c_vec=np.array([0.0, 0.5, 1.0]),
        lambda_wue_vec=np.array([0.0020, 0.0008, 0.0004]),
    )

    assert np.isclose(solution.g_c, 0.4166666666666667)
    assert np.isclose(solution.lambda_wue, 0.001)
    assert np.allclose(solution.hc_vec, np.array([0.0, 0.001, 0.002]))


def test_prentice_model_supports_legacy_v_cmax_alias() -> None:
    solution = stomata_prentice_2014(
        a_n_vec=np.array([0.0, 0.001, 0.002]),
        e_vec=np.array([0.0, 1.0, 2.0]),
        g_c_vec=np.array([0.0, 0.5, 1.0]),
        lambda_wue_vec=np.array([0.0010, 0.0005, 0.0001]),
        V_cmax_func=lambda t_l_vec: np.full_like(t_l_vec, 0.005, dtype=float),
        t_l_vec=np.array([20.0, 20.0, 20.0]),
    )

    assert np.isfinite(solution.g_c)
    assert np.isclose(solution.lambda_wue, 0.0005369127516778524)
    assert solution.HC_vec is solution.hc_vec
    assert solution.lambda_wue_model_vec is not None


def test_wang_model_matches_baseline_runtime_snapshot() -> None:
    sweep = _baseline_runtime_sweep()
    inputs = sweep["inputs"]
    solution = stomata_wang_2020(
        a_n_vec=sweep["a_n_vec"],
        e_vec=sweep["e_vec"],
        g_c_vec=sweep["g_c_vec"],
        lambda_wue_vec=sweep["lambda_wue_vec"],
        psi_s_vec=sweep["psi_s_vec"],
        alpha_l=inputs.alpha_l,
        beta_l=inputs.beta_l,
        k_l=inputs.k_l,
    )

    assert np.isclose(solution.g_c, 0.010564629244768786)
    assert np.isclose(solution.lambda_wue, 0.015529963244502077)
    assert solution.hc_vec is not None
    assert solution.lambda_wue_model_vec is not None


def test_anderegg_model_preserves_no_crossing_nan_contract() -> None:
    sweep = _baseline_runtime_sweep()
    inputs = sweep["inputs"]
    solution = stomata_anderegg_2018(
        e_vec=sweep["e_vec"],
        g_c_vec=sweep["g_c_vec"],
        lambda_wue_vec=sweep["lambda_wue_vec"],
        psi_rc_vec=sweep["psi_rc_vec"],
        psi_s_vec=sweep["psi_s_vec"],
        alpha_r=inputs.alpha_r,
        beta_r=inputs.beta_r,
        k_r=inputs.k_r,
        alpha_sw=inputs.alpha_sw,
        beta_sw=inputs.beta_sw,
        k_sw=inputs.k_sw,
        alpha_l=inputs.alpha_l,
        beta_l=inputs.beta_l,
        k_l=inputs.k_l,
        la=inputs.la,
        h=inputs.h,
        z=inputs.z,
        rho=inputs.rho,
        g=inputs.g,
    )

    assert np.isnan(solution.g_c)
    assert np.isnan(solution.lambda_wue)
    assert solution.hc_vec is not None
    assert solution.lambda_wue_model_vec is not None


def test_maximize_assimilation_picks_argmax() -> None:
    solution = stomata_maximize_assimilation(
        a_n_vec=np.array([np.nan, 1.0, 3.0, 2.0]),
        g_c_vec=np.array([-1.0, 0.1, 0.3, 0.2]),
        lambda_wue_vec=np.array([0.0, 0.01, 0.03, 0.02]),
    )

    assert np.isclose(solution.g_c, 0.3)
    assert np.isclose(solution.lambda_wue, 0.03)
