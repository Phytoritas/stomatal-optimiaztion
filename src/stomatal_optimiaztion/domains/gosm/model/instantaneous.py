from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from stomatal_optimiaztion.domains.gosm.model.pipeline import rad_hydr_grow_temp_cassimilation
from stomatal_optimiaztion.domains.gosm.params.defaults import BaselineInputs
from stomatal_optimiaztion.domains.gosm.utils.traceability import implements


@dataclass(frozen=True)
class InstantaneousSolution:
    a_n: float
    e: float
    lambda_wue: float
    g0: float
    g_c: float
    psi_s: float
    psi_rc: float
    vpd: float


@implements("Eq.S2.4a", "Eq.S2.4b")
def update_carbon_assimilation_growth(
    *,
    eta: float,
    c_nsc: float,
    inputs: BaselineInputs,
    lambda_wue_vec: np.ndarray,
    g0_vec: np.ndarray,
    a_n_vec: np.ndarray,
    e_vec: np.ndarray,
    g_c_vec: np.ndarray,
    vpd_vec: np.ndarray,
    psi_s_vec: np.ndarray,
    psi_rc_vec: np.ndarray,
    d_g0_d_e_vec: np.ndarray,
) -> InstantaneousSolution:
    """Instantaneous optimum for fixed eta and NSC."""

    la = inputs.la
    f_c = inputs.f_c
    theta_g = inputs.theta_g

    lambda_wue_vec = np.asarray(lambda_wue_vec, dtype=float)
    g0_vec = np.asarray(g0_vec, dtype=float)
    a_n_vec = np.asarray(a_n_vec, dtype=float)
    e_vec = np.asarray(e_vec, dtype=float)
    g_c_vec = np.asarray(g_c_vec, dtype=float)
    vpd_vec = np.asarray(vpd_vec, dtype=float)
    psi_s_vec = np.asarray(psi_s_vec, dtype=float)
    psi_rc_vec = np.asarray(psi_rc_vec, dtype=float)
    d_g0_d_e_vec = np.asarray(d_g0_d_e_vec)

    chi_w_vec = (1 / (1 - f_c) - 1 / eta) * float(theta_g(c_nsc)) * np.real(d_g0_d_e_vec) / la

    ind_not_neg = np.where(g_c_vec >= 0)[0]
    a_n_vec = a_n_vec[ind_not_neg]
    e_vec = e_vec[ind_not_neg]
    lambda_wue_vec = lambda_wue_vec[ind_not_neg]
    chi_w_vec = chi_w_vec[ind_not_neg]
    g0_vec = g0_vec[ind_not_neg]
    g_c_vec = g_c_vec[ind_not_neg]
    psi_s_vec = psi_s_vec[ind_not_neg]
    psi_rc_vec = psi_rc_vec[ind_not_neg]
    vpd_vec = vpd_vec[ind_not_neg]

    if np.sum(np.isnan(chi_w_vec)) == chi_w_vec.size:
        nan = float("nan")
        return InstantaneousSolution(a_n=nan, e=nan, lambda_wue=nan, g0=nan, g_c=nan, psi_s=nan, psi_rc=nan, vpd=nan)

    if ind_not_neg.size == 0:
        nan = float("nan")
        return InstantaneousSolution(a_n=nan, e=nan, lambda_wue=nan, g0=nan, g_c=0.0, psi_s=nan, psi_rc=nan, vpd=nan)

    diff_chi_w_minus_lambda_wue_vec = chi_w_vec - lambda_wue_vec
    zero_diff_vec = np.concatenate((np.abs(np.diff(np.sign(diff_chi_w_minus_lambda_wue_vec))) / 2, [0]))
    num_zero = float(np.sum(zero_diff_vec))

    if float(chi_w_vec[0]) > float(lambda_wue_vec[0]):
        idx0_candidates = np.where(g_c_vec == 0)[0]
        idx0 = int(idx0_candidates[0]) if idx0_candidates.size else 0
        return InstantaneousSolution(
            a_n=float(a_n_vec[idx0]),
            e=float(e_vec[idx0]),
            lambda_wue=float(lambda_wue_vec[idx0]),
            g0=float(g0_vec[idx0]),
            g_c=0.0,
            psi_s=float(psi_s_vec[idx0]),
            psi_rc=float(psi_rc_vec[idx0]),
            vpd=float(vpd_vec[idx0]),
        )

    if num_zero >= 1:
        ind_zero = np.where(zero_diff_vec == 1)[0]
        ind = int(np.min(ind_zero))

        g_c_lb = float(g_c_vec[ind])
        g_c_ub = float(g_c_vec[ind + 1])
        if g_c_lb == float(np.max(g_c_vec)):
            g_c_ub = float(np.max(g_c_vec))

        diff_lb = float(diff_chi_w_minus_lambda_wue_vec[ind])
        diff_ub = float(diff_chi_w_minus_lambda_wue_vec[ind + 1])
        g_c = g_c_lb + (g_c_ub - g_c_lb) * (0 - diff_lb) / (diff_ub - diff_lb)

        def _interp(y_lb: float, y_ub: float) -> float:
            return y_lb + (y_ub - y_lb) * (g_c - g_c_lb) / (g_c_ub - g_c_lb)

        psi_s = _interp(float(psi_s_vec[ind]), float(psi_s_vec[ind + 1]))
        psi_rc = _interp(float(psi_rc_vec[ind]), float(psi_rc_vec[ind + 1]))
        e = _interp(float(e_vec[ind]), float(e_vec[ind + 1]))
        a_n = _interp(float(a_n_vec[ind]), float(a_n_vec[ind + 1]))
        lambda_wue = _interp(float(lambda_wue_vec[ind]), float(lambda_wue_vec[ind + 1]))
        if lambda_wue < 0:
            lambda_wue = 0.0
        g0 = _interp(float(g0_vec[ind]), float(g0_vec[ind + 1]))
        vpd = _interp(float(vpd_vec[ind]), float(vpd_vec[ind + 1]))

        return InstantaneousSolution(a_n=a_n, e=e, lambda_wue=lambda_wue, g0=g0, g_c=g_c, psi_s=psi_s, psi_rc=psi_rc, vpd=vpd)

    e_ub = 0.0
    d_e_ub = 1e-3
    for _ in range(100):
        (
            _e_vec,
            _a_n_vec,
            _r_d_vec,
            _g0_vec,
            _g_w_vec,
            _g_c_vec,
            _lambda_wue_vec,
            _dG_0dE_vec,
            _dG_0dg_c_vec,
            _psi_s_vec,
            _psi_rc_vec,
            _t_l_vec,
            _vpd_vec,
            _r_abs,
            *_,
        ) = rad_hydr_grow_temp_cassimilation(np.array([e_ub], dtype=float), inputs=inputs)
        lambda_wue_ub = float(_lambda_wue_vec[0])
        if lambda_wue_ub < 0:
            break
        e_ub += d_e_ub
    else:
        raise RuntimeError("UNREALISTIC: dA_n/dE never equals zero")

    e_lb = e_ub - d_e_ub

    for _ in range(100):
        e_mid = (e_lb + e_ub) / 2
        e_bisect = np.array([e_lb, e_mid, e_ub], dtype=float)

        (
            _e_vec,
            _a_n_vec,
            _r_d_vec,
            _g0_vec,
            _g_w_vec,
            _g_c_vec,
            lambda_wue_bisect,
            _dG_0dE_vec,
            _dG_0dg_c_vec,
            _psi_s_vec,
            _psi_rc_vec,
            _t_l_vec,
            _vpd_vec,
            _r_abs,
            *_,
        ) = rad_hydr_grow_temp_cassimilation(e_bisect, inputs=inputs)

        if np.all(lambda_wue_bisect > 0) or np.all(lambda_wue_bisect < 0):
            raise RuntimeError("Bisection bracket invalid for lambda_wue(e)")
        if np.any(np.abs(lambda_wue_bisect) < 1e-8):
            break

        lambda_wue_lb = float(np.min(lambda_wue_bisect[lambda_wue_bisect >= 0]))
        lambda_wue_ub = float(np.max(lambda_wue_bisect[lambda_wue_bisect < 0]))

        e_lb = float(e_bisect[lambda_wue_bisect == lambda_wue_lb][0])
        e_ub = float(e_bisect[lambda_wue_bisect == lambda_wue_ub][0])
    else:
        raise RuntimeError("Bisection exceeded 100 iterations")

    idx = int(np.argmin(np.abs(lambda_wue_bisect)))
    e = float(e_bisect[idx])

    (
        _e_vec,
        a_n_vec,
        _r_d_vec,
        g0_vec,
        _g_w_vec,
        g_c_vec,
        _lambda_wue_vec,
        _dG_0dE_vec,
        _dG_0dg_c_vec,
        psi_s_vec,
        psi_rc_vec,
        _t_l_vec,
        vpd_vec,
        _r_abs,
        *_,
    ) = rad_hydr_grow_temp_cassimilation(np.array([e], dtype=float), inputs=inputs)

    lambda_wue = 0.0
    return InstantaneousSolution(
        a_n=float(a_n_vec[0]),
        e=e,
        lambda_wue=lambda_wue,
        g0=float(g0_vec[0]),
        g_c=float(g_c_vec[0]),
        psi_s=float(psi_s_vec[0]),
        psi_rc=float(psi_rc_vec[0]),
        vpd=float(vpd_vec[0]),
    )
