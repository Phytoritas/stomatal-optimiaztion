from __future__ import annotations

from dataclasses import replace
from typing import Any, Literal

import numpy as np

from stomatal_optimiaztion.domains.gosm.examples.control import build_control_E_vec
from stomatal_optimiaztion.domains.gosm.model.instantaneous import (
    update_carbon_assimilation_growth,
)
from stomatal_optimiaztion.domains.gosm.model.pipeline import (
    rad_hydr_grow_temp_cassimilation,
)
from stomatal_optimiaztion.domains.gosm.model.steady_state import (
    steady_state_nsc_and_cue,
)
from stomatal_optimiaztion.domains.gosm.model.stomata_models import (
    stomata_anderegg_2018,
    stomata_cowan_and_farquhar_1977,
    stomata_dewar_2018,
    stomata_eller_2018,
    stomata_prentice_2014,
    stomata_sperry_2017,
    stomata_wang_2020,
)
from stomatal_optimiaztion.domains.gosm.params import BaselineInputs


STUDY_LEGEND = [
    "Cowan & Farquhar (1977)",
    "Prentice et al. (2014)",
    "Sperry et al. (2017)",
    "Anderegg et al. (2018)",
    "Dewar et al. (2018)",
    "Eller et al. (2018)",
    "Wang et al. (2020)",
]

__all__ = [
    "STUDY_LEGEND",
    "run_sensitivity_environmental_conditions",
    "run_sensitivity_p_soil_min_conductance_loss",
]


def _make_study_legend_matlab_cell() -> np.ndarray:
    # Match SciPy loadmat output: (7,1) object array, each element is a (1,) unicode array.
    out = np.empty((len(STUDY_LEGEND), 1), dtype=object)
    for i, s in enumerate(STUDY_LEGEND):
        out[i, 0] = np.array([s])
    return out


def _leaf_water_potential_vector(
    *,
    e_vec: np.ndarray,
    psi_s_vec: np.ndarray,
    alpha_l: float,
    beta_l: float,
    k_l: float,
) -> np.ndarray:
    log_arg_l = np.exp(-alpha_l * beta_l) + np.exp(-alpha_l * psi_s_vec) - np.exp(-alpha_l * psi_s_vec + alpha_l * e_vec / k_l)
    psi_l_complex = psi_s_vec - e_vec / k_l + beta_l + (1 / alpha_l) * np.log(log_arg_l.astype(complex))
    psi_l_vec = np.real(psi_l_complex)
    psi_l_vec[np.abs(np.imag(psi_l_complex)) > 0] = -np.inf
    return psi_l_vec


def _interp_vpd_at_g_c(*, g_c: float, g_c_vec: np.ndarray, vpd_vec: np.ndarray) -> float:
    if np.isnan(g_c):
        return float("nan")

    g_c_vec = np.asarray(g_c_vec, dtype=float)
    vpd_vec = np.asarray(vpd_vec, dtype=float)

    mask_le = g_c_vec <= g_c
    mask_gt = g_c_vec > g_c
    if not np.any(mask_le) or not np.any(mask_gt):
        return float("nan")

    g_c_LB = float(np.max(g_c_vec[mask_le]))
    g_c_UB = float(np.min(g_c_vec[mask_gt]))
    idx_LB = int(np.where(g_c_vec == g_c_LB)[0][0])
    idx_UB = int(np.where(g_c_vec == g_c_UB)[0][0])

    VPD_LB = float(vpd_vec[idx_LB])
    VPD_UB = float(vpd_vec[idx_UB])
    return VPD_LB + (VPD_UB - VPD_LB) * (g_c - g_c_LB) / (g_c_UB - g_c_LB)


def _interp_at_g_c(*, g_c: float, g_c_vec: np.ndarray, y_vec: np.ndarray) -> float:
    if np.isnan(g_c):
        return float("nan")

    g_c_vec = np.asarray(g_c_vec, dtype=float)
    y_vec = np.asarray(y_vec, dtype=float)

    mask_le = g_c_vec <= g_c
    mask_gt = g_c_vec > g_c
    if not np.any(mask_le) or not np.any(mask_gt):
        return float("nan")

    g_c_LB = float(np.max(g_c_vec[mask_le]))
    g_c_UB = float(np.min(g_c_vec[mask_gt]))
    idx_LB = int(np.where(g_c_vec == g_c_LB)[0][0])
    idx_UB = int(np.where(g_c_vec == g_c_UB)[0][0])

    y_LB = float(y_vec[idx_LB])
    y_UB = float(y_vec[idx_UB])
    return y_LB + (y_UB - y_LB) * (g_c - g_c_LB) / (g_c_UB - g_c_LB)


def _bracket_fraction(*, x_vec: np.ndarray, x_target: float) -> tuple[int, int, float]:
    if np.isnan(x_target):
        return 0, 0, float("nan")

    x_vec = np.asarray(x_vec, dtype=float)

    mask_le = x_vec <= x_target
    mask_gt = x_vec > x_target
    if (not np.any(mask_le)) or (not np.any(mask_gt)):
        return 0, 0, float("nan")

    x_LB = float(np.max(x_vec[mask_le]))
    x_UB = float(np.min(x_vec[mask_gt]))
    idx_LB = int(np.where(x_vec == x_LB)[0][0])
    idx_UB = int(np.where(x_vec == x_UB)[0][0])

    F = (x_target - x_LB) / (x_UB - x_LB)
    return idx_LB, idx_UB, float(F)


def run_sensitivity_environmental_conditions(
    *,
    param: str,
    param_test: np.ndarray,
    eta_test: np.ndarray | None = None,
    inputs: BaselineInputs | None = None,
) -> dict[str, Any]:
    """Reproduce sensitivity .mat outputs for RH/c_a/P_soil.

    Baseline generator: `example/Growth_Opt_Stomata__test_sensitivity_environmental_conditions.m` (non P_soil_min branch)
    """

    inputs0 = inputs or BaselineInputs.matlab_default()
    E_vect_grid = build_control_E_vec()

    param_test = np.asarray(param_test, dtype=float).reshape(1, -1)
    N = param_test.size

    if eta_test is None:
        eta_test = (1 - inputs0.f_c) * np.arange(0.3, 0.8 + 1e-12, 0.1)
    eta_test = np.asarray(eta_test, dtype=float).reshape(1, -1)
    M = eta_test.size

    # gamma_r_test in the baseline files is a scalar (default gamma_r)
    gamma_r_test = np.array([[inputs0.gamma_r]], dtype=float)
    Q = 1

    g_c_test = np.full((M, N), np.nan, dtype=float)
    lambda_wue_test = np.full((M, N), np.nan, dtype=float)
    G_test = np.full((M, N), np.nan, dtype=float)
    VPD_test = np.full((M, N), np.nan, dtype=float)
    E_test = np.full((M, N), np.nan, dtype=float)

    g_c_ss_test = np.full((Q, N), np.nan, dtype=float)
    lambda_wue_ss_test = np.full((Q, N), np.nan, dtype=float)
    VPD_ss_test = np.full((Q, N), np.nan, dtype=float)
    c_NSC_ss_test = np.full((Q, N), np.nan, dtype=float)
    G_ss_test = np.full((Q, N), np.nan, dtype=float)
    E_ss_test = np.full((Q, N), np.nan, dtype=float)

    study_g_c = np.full((len(STUDY_LEGEND), N), np.nan, dtype=float)
    study_lambda_wue = np.full((len(STUDY_LEGEND), N), np.nan, dtype=float)
    study_VPD = np.full((len(STUDY_LEGEND), N), np.nan, dtype=float)

    for i in range(N):
        val = float(param_test.flat[i])

        if param == "RH":
            inputs_i = replace(inputs0, rh=val)
        elif param == "c_a":
            inputs_i = replace(inputs0, c_a=val)
        elif param == "P_soil":
            inputs_i = replace(inputs0, psi_soil=val)
        else:
            raise ValueError(f"Unsupported param={param!r} (expected 'RH', 'c_a', or 'P_soil')")

        (
            e_vec,
            a_n_vec,
            _R_d_vec,
            g0_vec,
            _g_w_vec,
            g_c_vec,
            lambda_wue_vec,
            d_g0_d_e_vec,
            _dG_0dg_c_vec,
            psi_s_vec,
            psi_rc_vec,
            t_l_vec,
            vpd_vec,
            _R_abs,
            *_,
        ) = rad_hydr_grow_temp_cassimilation(E_vect_grid, inputs=inputs_i)

        # instantaneous (fixed CUE eta, fixed NSC storage)
        for j in range(M):
            eta = float(eta_test.flat[j])
            sol = update_carbon_assimilation_growth(
                eta=eta,
                c_nsc=inputs_i.c_nsc,
                inputs=inputs_i,
                lambda_wue_vec=lambda_wue_vec,
                g0_vec=g0_vec,
                a_n_vec=a_n_vec,
                e_vec=e_vec,
                g_c_vec=g_c_vec,
                vpd_vec=vpd_vec,
                psi_s_vec=psi_s_vec,
                psi_rc_vec=psi_rc_vec,
                d_g0_d_e_vec=d_g0_d_e_vec,
            )
            g_c_test[j, i] = sol.g_c
            lambda_wue_test[j, i] = sol.lambda_wue
            VPD_test[j, i] = sol.vpd
            G_test[j, i] = sol.g0 * float(inputs_i.theta_g(inputs_i.c_nsc))
            E_test[j, i] = sol.e

        # steady-state (single gamma_r = default)
        (
            _A_n,
            E_ss,
            lambda_wue_ss,
            G_0_ss,
            g_c_ss,
            _psi_s,
            _psi_rc,
            _eta_ss_vec,
            _lambda_ss_vec,
            c_NSC_ss,
            _R_M_0,
            VPD_ss,
            _eta_ss,
            _c_NSC_ss_vec,
        ) = steady_state_nsc_and_cue(
            inputs=inputs_i,
            lambda_wue_vec=lambda_wue_vec,
            g0_vec=g0_vec,
            d_g0_d_e_vec=d_g0_d_e_vec,
            a_n_vec=a_n_vec,
            e_vec=e_vec,
            g_c_vec=g_c_vec,
            vpd_vec=vpd_vec,
            psi_s_vec=psi_s_vec,
            psi_rc_vec=psi_rc_vec,
        )
        g_c_ss_test[0, i] = g_c_ss
        lambda_wue_ss_test[0, i] = lambda_wue_ss
        VPD_ss_test[0, i] = VPD_ss
        c_NSC_ss_test[0, i] = c_NSC_ss
        G_ss_test[0, i] = G_0_ss * float(inputs_i.theta_g(c_NSC_ss))
        E_ss_test[0, i] = E_ss

        # other models (study_)
        cowan = stomata_cowan_and_farquhar_1977(e_vec=e_vec, g_c_vec=g_c_vec, lambda_wue_vec=lambda_wue_vec)
        prentice = stomata_prentice_2014(
            a_n_vec=a_n_vec,
            e_vec=e_vec,
            g_c_vec=g_c_vec,
            lambda_wue_vec=lambda_wue_vec,
            v_cmax_func=inputs_i.v_cmax,
            t_l_vec=t_l_vec,
        )
        sperry = stomata_sperry_2017(
            a_n_vec=a_n_vec,
            e_vec=e_vec,
            g_c_vec=g_c_vec,
            lambda_wue_vec=lambda_wue_vec,
            psi_rc_vec=psi_rc_vec,
            psi_s_vec=psi_s_vec,
            alpha_r=inputs_i.alpha_r,
            beta_r=inputs_i.beta_r,
            k_r=inputs_i.k_r,
            alpha_sw=inputs_i.alpha_sw,
            beta_sw=inputs_i.beta_sw,
            k_sw=inputs_i.k_sw,
            alpha_l=inputs_i.alpha_l,
            beta_l=inputs_i.beta_l,
            k_l=inputs_i.k_l,
            la=inputs_i.la,
            h=inputs_i.h,
            z=inputs_i.z,
            rho=inputs_i.rho,
            g=inputs_i.g,
        )
        anderegg = stomata_anderegg_2018(
            e_vec=e_vec,
            g_c_vec=g_c_vec,
            lambda_wue_vec=lambda_wue_vec,
            psi_rc_vec=psi_rc_vec,
            psi_s_vec=psi_s_vec,
            alpha_r=inputs_i.alpha_r,
            beta_r=inputs_i.beta_r,
            k_r=inputs_i.k_r,
            alpha_sw=inputs_i.alpha_sw,
            beta_sw=inputs_i.beta_sw,
            k_sw=inputs_i.k_sw,
            alpha_l=inputs_i.alpha_l,
            beta_l=inputs_i.beta_l,
            k_l=inputs_i.k_l,
            la=inputs_i.la,
            h=inputs_i.h,
            z=inputs_i.z,
            rho=inputs_i.rho,
            g=inputs_i.g,
        )
        dewar = stomata_dewar_2018(
            a_n_vec=a_n_vec,
            e_vec=e_vec,
            g_c_vec=g_c_vec,
            lambda_wue_vec=lambda_wue_vec,
            psi_rc_vec=psi_rc_vec,
            psi_s_vec=psi_s_vec,
            alpha_r=inputs_i.alpha_r,
            beta_r=inputs_i.beta_r,
            k_r=inputs_i.k_r,
            alpha_sw=inputs_i.alpha_sw,
            beta_sw=inputs_i.beta_sw,
            k_sw=inputs_i.k_sw,
            alpha_l=inputs_i.alpha_l,
            beta_l=inputs_i.beta_l,
            k_l=inputs_i.k_l,
            la=inputs_i.la,
            h=inputs_i.h,
            z=inputs_i.z,
            rho=inputs_i.rho,
            g=inputs_i.g,
        )
        eller = stomata_eller_2018(
            a_n_vec=a_n_vec,
            e_vec=e_vec,
            g_c_vec=g_c_vec,
            lambda_wue_vec=lambda_wue_vec,
            psi_rc_vec=psi_rc_vec,
            psi_s_vec=psi_s_vec,
            alpha_r=inputs_i.alpha_r,
            beta_r=inputs_i.beta_r,
            k_r=inputs_i.k_r,
            alpha_sw=inputs_i.alpha_sw,
            beta_sw=inputs_i.beta_sw,
            k_sw=inputs_i.k_sw,
            alpha_l=inputs_i.alpha_l,
            beta_l=inputs_i.beta_l,
            k_l=inputs_i.k_l,
            la=inputs_i.la,
            h=inputs_i.h,
            z=inputs_i.z,
            rho=inputs_i.rho,
            g=inputs_i.g,
        )
        wang = stomata_wang_2020(
            a_n_vec=a_n_vec,
            e_vec=e_vec,
            g_c_vec=g_c_vec,
            lambda_wue_vec=lambda_wue_vec,
            psi_s_vec=psi_s_vec,
            alpha_l=inputs_i.alpha_l,
            beta_l=inputs_i.beta_l,
            k_l=inputs_i.k_l,
        )

        models = [cowan, prentice, sperry, anderegg, dewar, eller, wang]
        for model_idx, m in enumerate(models):
            study_g_c[model_idx, i] = m.g_c
            study_lambda_wue[model_idx, i] = m.lambda_wue
            study_VPD[model_idx, i] = _interp_vpd_at_g_c(g_c=m.g_c, g_c_vec=g_c_vec, vpd_vec=vpd_vec)

    # derived study_E (as in MATLAB script)
    with np.errstate(divide="ignore", invalid="ignore"):
        study_g_w = 1.6 / (1 / study_g_c - 1.37 / inputs0.g_b)
        study_E = study_VPD / inputs0.p_atm / (1 / study_g_w + 1 / inputs0.g_b)

    return {
        "PARAM": np.array([param]),
        "PARAM_TEST": param_test,
        "eta_test": eta_test,
        "gamma_r_test": gamma_r_test,
        "g_c_test": g_c_test,
        "lambda_test": lambda_wue_test,
        "G_test": G_test,
        "VPD_test": VPD_test,
        "E_test": E_test,
        "g_c_ss_test": g_c_ss_test,
        "lambda_ss_test": lambda_wue_ss_test,
        "VPD_ss_test": VPD_ss_test,
        "c_NSC_ss_test": c_NSC_ss_test,
        "G_ss_test": G_ss_test,
        "E_ss_test": E_ss_test,
        "study_legend": _make_study_legend_matlab_cell(),
        "study_g_c": study_g_c,
        "study_lambda": study_lambda_wue,
        "study_VPD": study_VPD,
        "study_E": study_E,
    }


def run_sensitivity_p_soil_min_conductance_loss(
    *,
    param_test: np.ndarray,
    eta_test: np.ndarray | None = None,
    conductance_loss: Literal["true", "imag"],
    inputs: BaselineInputs | None = None,
) -> dict[str, Any]:
    """Reproduce sensitivity .mat outputs for P_soil_min conductance loss analyses.

    Baseline generator: `example/Growth_Opt_Stomata__test_sensitivity_environmental_conditions.m` (P_soil_min section)

    Notes:
    - Matches MATLAB behavior that leaves `E_test` and `study_E` from the *pre-loss* run unchanged, while updating
      `g_c_test`, `lambda_wue_test`, `VPD_test`, `G_test`, and the steady-state arrays for the post-loss run.
    """

    inputs0 = inputs or BaselineInputs.matlab_default()
    E_vect_grid = build_control_E_vec()

    param_test = np.asarray(param_test, dtype=float).reshape(1, -1)
    N = param_test.size

    if eta_test is None:
        eta_test = (1 - inputs0.f_c) * np.arange(0.3, 0.8 + 1e-12, 0.1)
    eta_test = np.asarray(eta_test, dtype=float).reshape(1, -1)
    M = eta_test.size

    gamma_r_test = np.array([[inputs0.gamma_r]], dtype=float)
    Q = 1

    # ------------------------------------------------------------------
    # (Stage 1) Baseline "during drought" run (immediate refilling; default conductance parameters).
    # This stage provides:
    # - E_test and study_E that are later *not updated* (MATLAB behavior)
    # - psi_rc_ss / psi_s_ss / e_ss needed to infer permanent conductance loss parameters (MATLAB keys: 'P_x_r_ss' / 'P_x_s_ss' / 'E_ss')

    g_c_test = np.full((M, N), np.nan, dtype=float)
    lambda_wue_test = np.full((M, N), np.nan, dtype=float)
    G_test = np.full((M, N), np.nan, dtype=float)
    VPD_test = np.full((M, N), np.nan, dtype=float)
    E_test = np.full((M, N), np.nan, dtype=float)
    psi_s_test = np.full((M, N), np.nan, dtype=float)

    g_c_ss_drought = np.full((Q, N), np.nan, dtype=float)
    lambda_wue_ss_drought = np.full((Q, N), np.nan, dtype=float)
    VPD_ss_drought = np.full((Q, N), np.nan, dtype=float)
    c_NSC_ss_drought = np.full((Q, N), np.nan, dtype=float)
    G_ss_drought = np.full((Q, N), np.nan, dtype=float)
    E_ss_drought = np.full((Q, N), np.nan, dtype=float)
    psi_rc_ss_drought = np.full((Q, N), np.nan, dtype=float)
    psi_s_ss_drought = np.full((Q, N), np.nan, dtype=float)

    study_g_c = np.full((len(STUDY_LEGEND), N), np.nan, dtype=float)
    study_lambda_wue = np.full((len(STUDY_LEGEND), N), np.nan, dtype=float)
    study_VPD = np.full((len(STUDY_LEGEND), N), np.nan, dtype=float)
    study_psi_l = np.full((len(STUDY_LEGEND), N), np.nan, dtype=float)

    for i in range(N):
        P_soil_i = float(param_test.flat[i])
        inputs_i = replace(inputs0, psi_soil=P_soil_i)

        (
            e_vec,
            a_n_vec,
            _R_d_vec,
            g0_vec,
            _g_w_vec,
            g_c_vec,
            lambda_wue_vec,
            d_g0_d_e_vec,
            _dG_0dg_c_vec,
            psi_s_vec,
            psi_rc_vec,
            t_l_vec,
            vpd_vec,
            _R_abs,
            *_,
        ) = rad_hydr_grow_temp_cassimilation(E_vect_grid, inputs=inputs_i)

        psi_l_vec = _leaf_water_potential_vector(
            e_vec=e_vec,
            psi_s_vec=psi_s_vec,
            alpha_l=inputs0.alpha_l,
            beta_l=inputs0.beta_l,
            k_l=inputs0.k_l,
        )

        for j in range(M):
            eta = float(eta_test.flat[j])
            sol = update_carbon_assimilation_growth(
                eta=eta,
                c_nsc=inputs_i.c_nsc,
                inputs=inputs_i,
                lambda_wue_vec=lambda_wue_vec,
                g0_vec=g0_vec,
                a_n_vec=a_n_vec,
                e_vec=e_vec,
                g_c_vec=g_c_vec,
                vpd_vec=vpd_vec,
                psi_s_vec=psi_s_vec,
                psi_rc_vec=psi_rc_vec,
                d_g0_d_e_vec=d_g0_d_e_vec,
            )
            g_c_test[j, i] = sol.g_c
            lambda_wue_test[j, i] = sol.lambda_wue
            VPD_test[j, i] = sol.vpd
            G_test[j, i] = sol.g0 * float(inputs_i.theta_g(inputs_i.c_nsc))
            E_test[j, i] = sol.e
            psi_s_test[j, i] = sol.psi_s

        (
            _A_n,
            E_ss,
            lambda_wue_ss,
            G_0_ss,
            g_c_ss,
            psi_s_ss,
            psi_rc_ss,
            _eta_ss_vec,
            _lambda_ss_vec,
            c_NSC_ss,
            _R_M_0,
            VPD_ss,
            _eta_ss,
            _c_NSC_ss_vec,
        ) = steady_state_nsc_and_cue(
            inputs=inputs_i,
            lambda_wue_vec=lambda_wue_vec,
            g0_vec=g0_vec,
            d_g0_d_e_vec=d_g0_d_e_vec,
            a_n_vec=a_n_vec,
            e_vec=e_vec,
            g_c_vec=g_c_vec,
            vpd_vec=vpd_vec,
            psi_s_vec=psi_s_vec,
            psi_rc_vec=psi_rc_vec,
        )
        g_c_ss_drought[0, i] = g_c_ss
        lambda_wue_ss_drought[0, i] = lambda_wue_ss
        VPD_ss_drought[0, i] = VPD_ss
        c_NSC_ss_drought[0, i] = c_NSC_ss
        G_ss_drought[0, i] = G_0_ss * float(inputs_i.theta_g(c_NSC_ss))
        E_ss_drought[0, i] = E_ss
        psi_rc_ss_drought[0, i] = psi_rc_ss
        psi_s_ss_drought[0, i] = psi_s_ss

        cowan = stomata_cowan_and_farquhar_1977(e_vec=e_vec, g_c_vec=g_c_vec, lambda_wue_vec=lambda_wue_vec)
        prentice = stomata_prentice_2014(
            a_n_vec=a_n_vec,
            e_vec=e_vec,
            g_c_vec=g_c_vec,
            lambda_wue_vec=lambda_wue_vec,
            v_cmax_func=inputs_i.v_cmax,
            t_l_vec=t_l_vec,
        )
        sperry = stomata_sperry_2017(
            a_n_vec=a_n_vec,
            e_vec=e_vec,
            g_c_vec=g_c_vec,
            lambda_wue_vec=lambda_wue_vec,
            psi_rc_vec=psi_rc_vec,
            psi_s_vec=psi_s_vec,
            alpha_r=inputs_i.alpha_r,
            beta_r=inputs_i.beta_r,
            k_r=inputs_i.k_r,
            alpha_sw=inputs_i.alpha_sw,
            beta_sw=inputs_i.beta_sw,
            k_sw=inputs_i.k_sw,
            alpha_l=inputs_i.alpha_l,
            beta_l=inputs_i.beta_l,
            k_l=inputs_i.k_l,
            la=inputs_i.la,
            h=inputs_i.h,
            z=inputs_i.z,
            rho=inputs_i.rho,
            g=inputs_i.g,
        )
        anderegg = stomata_anderegg_2018(
            e_vec=e_vec,
            g_c_vec=g_c_vec,
            lambda_wue_vec=lambda_wue_vec,
            psi_rc_vec=psi_rc_vec,
            psi_s_vec=psi_s_vec,
            alpha_r=inputs_i.alpha_r,
            beta_r=inputs_i.beta_r,
            k_r=inputs_i.k_r,
            alpha_sw=inputs_i.alpha_sw,
            beta_sw=inputs_i.beta_sw,
            k_sw=inputs_i.k_sw,
            alpha_l=inputs_i.alpha_l,
            beta_l=inputs_i.beta_l,
            k_l=inputs_i.k_l,
            la=inputs_i.la,
            h=inputs_i.h,
            z=inputs_i.z,
            rho=inputs_i.rho,
            g=inputs_i.g,
        )
        dewar = stomata_dewar_2018(
            a_n_vec=a_n_vec,
            e_vec=e_vec,
            g_c_vec=g_c_vec,
            lambda_wue_vec=lambda_wue_vec,
            psi_rc_vec=psi_rc_vec,
            psi_s_vec=psi_s_vec,
            alpha_r=inputs_i.alpha_r,
            beta_r=inputs_i.beta_r,
            k_r=inputs_i.k_r,
            alpha_sw=inputs_i.alpha_sw,
            beta_sw=inputs_i.beta_sw,
            k_sw=inputs_i.k_sw,
            alpha_l=inputs_i.alpha_l,
            beta_l=inputs_i.beta_l,
            k_l=inputs_i.k_l,
            la=inputs_i.la,
            h=inputs_i.h,
            z=inputs_i.z,
            rho=inputs_i.rho,
            g=inputs_i.g,
        )
        eller = stomata_eller_2018(
            a_n_vec=a_n_vec,
            e_vec=e_vec,
            g_c_vec=g_c_vec,
            lambda_wue_vec=lambda_wue_vec,
            psi_rc_vec=psi_rc_vec,
            psi_s_vec=psi_s_vec,
            alpha_r=inputs_i.alpha_r,
            beta_r=inputs_i.beta_r,
            k_r=inputs_i.k_r,
            alpha_sw=inputs_i.alpha_sw,
            beta_sw=inputs_i.beta_sw,
            k_sw=inputs_i.k_sw,
            alpha_l=inputs_i.alpha_l,
            beta_l=inputs_i.beta_l,
            k_l=inputs_i.k_l,
            la=inputs_i.la,
            h=inputs_i.h,
            z=inputs_i.z,
            rho=inputs_i.rho,
            g=inputs_i.g,
        )
        wang = stomata_wang_2020(
            a_n_vec=a_n_vec,
            e_vec=e_vec,
            g_c_vec=g_c_vec,
            lambda_wue_vec=lambda_wue_vec,
            psi_s_vec=psi_s_vec,
            alpha_l=inputs_i.alpha_l,
            beta_l=inputs_i.beta_l,
            k_l=inputs_i.k_l,
        )

        models = [cowan, prentice, sperry, anderegg, dewar, eller, wang]
        for model_idx, m in enumerate(models):
            study_g_c[model_idx, i] = m.g_c
            study_lambda_wue[model_idx, i] = m.lambda_wue
            study_VPD[model_idx, i] = _interp_vpd_at_g_c(g_c=m.g_c, g_c_vec=g_c_vec, vpd_vec=vpd_vec)
            study_psi_l[model_idx, i] = _interp_at_g_c(g_c=m.g_c, g_c_vec=g_c_vec, y_vec=psi_l_vec)

    with np.errstate(divide="ignore", invalid="ignore"):
        study_g_w = 1.6 / (1 / study_g_c - 1.37 / inputs0.g_b)
        study_E = study_VPD / inputs0.p_atm / (1 / study_g_w + 1 / inputs0.g_b)

    # ------------------------------------------------------------------
    # Infer permanent conductance loss from drought steady-state xylem potentials
    psi_l_ss_drought = _leaf_water_potential_vector(
        e_vec=E_ss_drought,
        psi_s_vec=psi_s_ss_drought,
        alpha_l=inputs0.alpha_l,
        beta_l=inputs0.beta_l,
        k_l=inputs0.k_l,
    )

    delta_psi_sw_ss_drought = psi_rc_ss_drought - psi_s_ss_drought
    delta_psi_root_ss_drought = param_test - psi_rc_ss_drought

    with np.errstate(divide="ignore", invalid="ignore"):
        k_sw_loss = inputs0.la * E_ss_drought / (delta_psi_sw_ss_drought - 1e-6 * inputs0.rho * inputs0.g * inputs0.h)
        k_r_loss = inputs0.la * E_ss_drought / (delta_psi_root_ss_drought - 1e-6 * inputs0.rho * inputs0.g * inputs0.z)
        k_l_loss = E_ss_drought / (psi_s_ss_drought - psi_l_ss_drought)

    mask0 = E_ss_drought == 0
    if np.any(mask0):
        delta_psi_sw = delta_psi_sw_ss_drought[mask0]
        delta_psi_root = delta_psi_root_ss_drought[mask0]

        k_sw_loss[mask0] = inputs0.k_sw / (
            1
            + (np.exp(inputs0.alpha_sw * delta_psi_sw) - 1)
            / (inputs0.alpha_sw * delta_psi_sw)
            * np.exp(-inputs0.alpha_sw * (psi_s_ss_drought[mask0] + delta_psi_sw - inputs0.beta_sw))
        )
        k_r_loss[mask0] = inputs0.k_r / (
            1
            + (np.exp(inputs0.alpha_r * delta_psi_root) - 1)
            / (inputs0.alpha_r * delta_psi_root)
            * np.exp(-inputs0.alpha_r * (psi_rc_ss_drought[mask0] + delta_psi_root - inputs0.beta_r))
        )
        k_l_loss[mask0] = inputs0.k_l / (1 + np.exp(-inputs0.alpha_l * (psi_l_ss_drought[mask0] - inputs0.beta_l)))

    with np.errstate(divide="ignore", invalid="ignore"):
        beta_sw_loss = inputs0.beta_sw - np.log(2 * inputs0.k_sw / k_sw_loss - 1) / inputs0.alpha_sw
        beta_r_loss = inputs0.beta_r - np.log(2 * inputs0.k_r / k_r_loss - 1) / inputs0.alpha_r
        beta_l_loss = inputs0.beta_l - np.log(2 * inputs0.k_l / k_l_loss - 1) / inputs0.alpha_l

        alpha_sw_loss = inputs0.alpha_sw * k_sw_loss / inputs0.k_sw * np.exp(-inputs0.alpha_sw * (beta_sw_loss - inputs0.beta_sw))
        alpha_r_loss = inputs0.alpha_r * k_r_loss / inputs0.k_r * np.exp(-inputs0.alpha_r * (beta_r_loss - inputs0.beta_r))
        alpha_l_loss = inputs0.alpha_l * k_l_loss / inputs0.k_l * np.exp(-inputs0.alpha_l * (beta_l_loss - inputs0.beta_l))

    # Squeeze to 1-D for indexing by i
    k_sw_loss = np.asarray(k_sw_loss, dtype=float).reshape(-1)
    k_r_loss = np.asarray(k_r_loss, dtype=float).reshape(-1)
    k_l_loss = np.asarray(k_l_loss, dtype=float).reshape(-1)
    alpha_sw_loss = np.asarray(alpha_sw_loss, dtype=float).reshape(-1)
    alpha_r_loss = np.asarray(alpha_r_loss, dtype=float).reshape(-1)
    alpha_l_loss = np.asarray(alpha_l_loss, dtype=float).reshape(-1)
    beta_sw_loss = np.asarray(beta_sw_loss, dtype=float).reshape(-1)
    beta_r_loss = np.asarray(beta_r_loss, dtype=float).reshape(-1)
    beta_l_loss = np.asarray(beta_l_loss, dtype=float).reshape(-1)

    # Targets for the Venturas et al. (2018) approach
    ind_default_candidates = np.where(np.abs(param_test.reshape(-1) - inputs0.psi_soil) < 1e-14)[0]
    if ind_default_candidates.size == 0:
        raise RuntimeError("Expected P_soil_default to be present in PARAM_TEST")
    ind_default = int(ind_default_candidates[0])

    psi_l_opt = _leaf_water_potential_vector(
        e_vec=E_test[:, ind_default],
        psi_s_vec=psi_s_test[:, ind_default],
        alpha_l=inputs0.alpha_l,
        beta_l=inputs0.beta_l,
        k_l=inputs0.k_l,
    )
    psi_l_ss_opt = psi_l_ss_drought[:, ind_default]
    study_psi_l_opt = study_psi_l[:, ind_default]

    # ------------------------------------------------------------------
    # (Stage 2) Post-loss run at default environment with modified hydraulic parameters.
    g_c_ss_test = np.full((Q, N), np.nan, dtype=float)
    lambda_wue_ss_test = np.full((Q, N), np.nan, dtype=float)
    VPD_ss_test = np.full((Q, N), np.nan, dtype=float)
    c_NSC_ss_test = np.full((Q, N), np.nan, dtype=float)
    G_ss_test = np.full((Q, N), np.nan, dtype=float)
    E_ss_test = np.full((Q, N), np.nan, dtype=float)

    for i in range(N):
        inputs_i = replace(
            inputs0,
            psi_soil=inputs0.psi_soil,
            k_sw=float(k_sw_loss[i]),
            alpha_sw=float(alpha_sw_loss[i]),
            beta_sw=float(beta_sw_loss[i]),
            k_r=float(k_r_loss[i]),
            alpha_r=float(alpha_r_loss[i]),
            beta_r=float(beta_r_loss[i]),
            k_l=float(k_l_loss[i]),
            alpha_l=float(alpha_l_loss[i]),
            beta_l=float(beta_l_loss[i]),
        )

        (
            e_vec,
            a_n_vec,
            _R_d_vec,
            g0_vec,
            _g_w_vec,
            g_c_vec,
            lambda_wue_vec,
            d_g0_d_e_vec,
            _dG_0dg_c_vec,
            psi_s_vec,
            psi_rc_vec,
            t_l_vec,
            vpd_vec,
            _R_abs,
            *_,
        ) = rad_hydr_grow_temp_cassimilation(E_vect_grid, inputs=inputs_i)

        if conductance_loss == "true":
            for j in range(M):
                eta = float(eta_test.flat[j])
                sol = update_carbon_assimilation_growth(
                    eta=eta,
                    c_nsc=inputs_i.c_nsc,
                    inputs=inputs_i,
                    lambda_wue_vec=lambda_wue_vec,
                    g0_vec=g0_vec,
                    a_n_vec=a_n_vec,
                    e_vec=e_vec,
                    g_c_vec=g_c_vec,
                    vpd_vec=vpd_vec,
                    psi_s_vec=psi_s_vec,
                    psi_rc_vec=psi_rc_vec,
                    d_g0_d_e_vec=d_g0_d_e_vec,
                )
                g_c_test[j, i] = sol.g_c
                lambda_wue_test[j, i] = sol.lambda_wue
                VPD_test[j, i] = sol.vpd
                G_test[j, i] = sol.g0 * float(inputs_i.theta_g(inputs_i.c_nsc))

            (
                _A_n,
                E_ss,
                lambda_wue_ss,
                G_0_ss,
                g_c_ss,
                _psi_s,
                _psi_rc,
                _eta_ss_vec,
                _lambda_ss_vec,
                c_NSC_ss,
                _R_M_0,
                VPD_ss,
                _eta_ss,
                _c_NSC_ss_vec,
            ) = steady_state_nsc_and_cue(
                inputs=inputs_i,
                lambda_wue_vec=lambda_wue_vec,
                g0_vec=g0_vec,
                d_g0_d_e_vec=d_g0_d_e_vec,
                a_n_vec=a_n_vec,
                e_vec=e_vec,
                g_c_vec=g_c_vec,
                vpd_vec=vpd_vec,
                psi_s_vec=psi_s_vec,
                psi_rc_vec=psi_rc_vec,
            )
            g_c_ss_test[0, i] = g_c_ss
            lambda_wue_ss_test[0, i] = lambda_wue_ss
            VPD_ss_test[0, i] = VPD_ss
            c_NSC_ss_test[0, i] = c_NSC_ss
            G_ss_test[0, i] = G_0_ss * float(inputs_i.theta_g(c_NSC_ss))
            E_ss_test[0, i] = E_ss

            cowan = stomata_cowan_and_farquhar_1977(e_vec=e_vec, g_c_vec=g_c_vec, lambda_wue_vec=lambda_wue_vec)
            prentice = stomata_prentice_2014(
                a_n_vec=a_n_vec,
                e_vec=e_vec,
                g_c_vec=g_c_vec,
                lambda_wue_vec=lambda_wue_vec,
                v_cmax_func=inputs_i.v_cmax,
                t_l_vec=t_l_vec,
            )
            sperry = stomata_sperry_2017(
                a_n_vec=a_n_vec,
                e_vec=e_vec,
                g_c_vec=g_c_vec,
                lambda_wue_vec=lambda_wue_vec,
                psi_rc_vec=psi_rc_vec,
                psi_s_vec=psi_s_vec,
                alpha_r=inputs_i.alpha_r,
                beta_r=inputs_i.beta_r,
                k_r=inputs_i.k_r,
                alpha_sw=inputs_i.alpha_sw,
                beta_sw=inputs_i.beta_sw,
                k_sw=inputs_i.k_sw,
                alpha_l=inputs_i.alpha_l,
                beta_l=inputs_i.beta_l,
                k_l=inputs_i.k_l,
                la=inputs_i.la,
                h=inputs_i.h,
                z=inputs_i.z,
                rho=inputs_i.rho,
                g=inputs_i.g,
            )
            anderegg = stomata_anderegg_2018(
                e_vec=e_vec,
                g_c_vec=g_c_vec,
                lambda_wue_vec=lambda_wue_vec,
                psi_rc_vec=psi_rc_vec,
                psi_s_vec=psi_s_vec,
                alpha_r=inputs_i.alpha_r,
                beta_r=inputs_i.beta_r,
                k_r=inputs_i.k_r,
                alpha_sw=inputs_i.alpha_sw,
                beta_sw=inputs_i.beta_sw,
                k_sw=inputs_i.k_sw,
                alpha_l=inputs_i.alpha_l,
                beta_l=inputs_i.beta_l,
                k_l=inputs_i.k_l,
                la=inputs_i.la,
                h=inputs_i.h,
                z=inputs_i.z,
                rho=inputs_i.rho,
                g=inputs_i.g,
            )
            dewar = stomata_dewar_2018(
                a_n_vec=a_n_vec,
                e_vec=e_vec,
                g_c_vec=g_c_vec,
                lambda_wue_vec=lambda_wue_vec,
                psi_rc_vec=psi_rc_vec,
                psi_s_vec=psi_s_vec,
                alpha_r=inputs_i.alpha_r,
                beta_r=inputs_i.beta_r,
                k_r=inputs_i.k_r,
                alpha_sw=inputs_i.alpha_sw,
                beta_sw=inputs_i.beta_sw,
                k_sw=inputs_i.k_sw,
                alpha_l=inputs_i.alpha_l,
                beta_l=inputs_i.beta_l,
                k_l=inputs_i.k_l,
                la=inputs_i.la,
                h=inputs_i.h,
                z=inputs_i.z,
                rho=inputs_i.rho,
                g=inputs_i.g,
            )
            eller = stomata_eller_2018(
                a_n_vec=a_n_vec,
                e_vec=e_vec,
                g_c_vec=g_c_vec,
                lambda_wue_vec=lambda_wue_vec,
                psi_rc_vec=psi_rc_vec,
                psi_s_vec=psi_s_vec,
                alpha_r=inputs_i.alpha_r,
                beta_r=inputs_i.beta_r,
                k_r=inputs_i.k_r,
                alpha_sw=inputs_i.alpha_sw,
                beta_sw=inputs_i.beta_sw,
                k_sw=inputs_i.k_sw,
                alpha_l=inputs_i.alpha_l,
                beta_l=inputs_i.beta_l,
                k_l=inputs_i.k_l,
                la=inputs_i.la,
                h=inputs_i.h,
                z=inputs_i.z,
                rho=inputs_i.rho,
                g=inputs_i.g,
            )
            wang = stomata_wang_2020(
                a_n_vec=a_n_vec,
                e_vec=e_vec,
                g_c_vec=g_c_vec,
                lambda_wue_vec=lambda_wue_vec,
                psi_s_vec=psi_s_vec,
                alpha_l=inputs_i.alpha_l,
                beta_l=inputs_i.beta_l,
                k_l=inputs_i.k_l,
            )

            models = [cowan, prentice, sperry, anderegg, dewar, eller, wang]
            for model_idx, m in enumerate(models):
                study_g_c[model_idx, i] = m.g_c
                study_lambda_wue[model_idx, i] = m.lambda_wue
                study_VPD[model_idx, i] = _interp_vpd_at_g_c(g_c=m.g_c, g_c_vec=g_c_vec, vpd_vec=vpd_vec)
        else:
            # Venturas et al. (2018) approach: maintain the (pre-loss) optimal leaf water potential.
            psi_l_vec = _leaf_water_potential_vector(
                e_vec=e_vec,
                psi_s_vec=psi_s_vec,
                alpha_l=inputs0.alpha_l,
                beta_l=inputs0.beta_l,
                k_l=inputs0.k_l,
            )

            for j in range(M):
                ind_LB, ind_UB, F = _bracket_fraction(x_vec=psi_l_vec, x_target=float(psi_l_opt[j]))
                g_c_test[j, i] = float(g_c_vec[ind_LB] + (g_c_vec[ind_UB] - g_c_vec[ind_LB]) * F)
                lambda_wue_test[j, i] = float(lambda_wue_vec[ind_LB] + (lambda_wue_vec[ind_UB] - lambda_wue_vec[ind_LB]) * F)
                VPD_test[j, i] = float(vpd_vec[ind_LB] + (vpd_vec[ind_UB] - vpd_vec[ind_LB]) * F)
                g0 = float(g0_vec[ind_LB] + (g0_vec[ind_UB] - g0_vec[ind_LB]) * F)
                G_test[j, i] = g0 * float(inputs_i.theta_g(inputs_i.c_nsc))

            (
                _A_n,
                _E,
                _lambda,
                _G_0,
                _g_c,
                _psi_s,
                _psi_rc,
                _eta_ss_vec,
                _lambda_ss_vec,
                _c_NSC_ss,
                _R_M_0,
                _VPD,
                _eta_ss,
                c_NSC_ss_vec,
            ) = steady_state_nsc_and_cue(
                inputs=inputs_i,
                lambda_wue_vec=lambda_wue_vec,
                g0_vec=g0_vec,
                d_g0_d_e_vec=d_g0_d_e_vec,
                a_n_vec=a_n_vec,
                e_vec=e_vec,
                g_c_vec=g_c_vec,
                vpd_vec=vpd_vec,
                psi_s_vec=psi_s_vec,
                psi_rc_vec=psi_rc_vec,
            )

            ind_LB, ind_UB, F = _bracket_fraction(x_vec=psi_l_vec, x_target=float(psi_l_ss_opt[0]))
            g_c_ss_test[0, i] = float(g_c_vec[ind_LB] + (g_c_vec[ind_UB] - g_c_vec[ind_LB]) * F)
            lambda_wue_ss_test[0, i] = float(lambda_wue_vec[ind_LB] + (lambda_wue_vec[ind_UB] - lambda_wue_vec[ind_LB]) * F)
            VPD_ss_test[0, i] = float(vpd_vec[ind_LB] + (vpd_vec[ind_UB] - vpd_vec[ind_LB]) * F)
            c_NSC_ss = float(c_NSC_ss_vec[ind_LB] + (c_NSC_ss_vec[ind_UB] - c_NSC_ss_vec[ind_LB]) * F)
            c_NSC_ss_test[0, i] = c_NSC_ss
            g0 = float(g0_vec[ind_LB] + (g0_vec[ind_UB] - g0_vec[ind_LB]) * F)
            G_ss_test[0, i] = g0 * float(inputs_i.theta_g(c_NSC_ss))
            E_ss_test[0, i] = float(e_vec[ind_LB] + (e_vec[ind_UB] - e_vec[ind_LB]) * F)

            for study_idx in range(len(STUDY_LEGEND)):
                ind_LB, ind_UB, F = _bracket_fraction(x_vec=psi_l_vec, x_target=float(study_psi_l_opt[study_idx]))
                study_g_c[study_idx, i] = float(g_c_vec[ind_LB] + (g_c_vec[ind_UB] - g_c_vec[ind_LB]) * F)
                study_lambda_wue[study_idx, i] = float(lambda_wue_vec[ind_LB] + (lambda_wue_vec[ind_UB] - lambda_wue_vec[ind_LB]) * F)
                study_VPD[study_idx, i] = float(vpd_vec[ind_LB] + (vpd_vec[ind_UB] - vpd_vec[ind_LB]) * F)

    return {
        "PARAM": np.array(["P_soil_min"]),
        "PARAM_TEST": param_test,
        "eta_test": eta_test,
        "gamma_r_test": gamma_r_test,
        "g_c_test": g_c_test,
        "lambda_test": lambda_wue_test,
        "G_test": G_test,
        "VPD_test": VPD_test,
        "E_test": E_test,
        "g_c_ss_test": g_c_ss_test,
        "lambda_ss_test": lambda_wue_ss_test,
        "VPD_ss_test": VPD_ss_test,
        "c_NSC_ss_test": c_NSC_ss_test,
        "G_ss_test": G_ss_test,
        "E_ss_test": E_ss_test,
        "study_legend": _make_study_legend_matlab_cell(),
        "study_g_c": study_g_c,
        "study_lambda": study_lambda_wue,
        "study_VPD": study_VPD,
        "study_E": study_E,
    }
