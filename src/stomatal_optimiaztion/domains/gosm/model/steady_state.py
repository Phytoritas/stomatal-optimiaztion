from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.gosm.params.defaults import BaselineInputs
from stomatal_optimiaztion.domains.gosm.utils.traceability import implements


@implements("Eq.S1.9", "Eq.S2.4b")
def steady_state_nsc_and_cue(
    *,
    inputs: BaselineInputs,
    lambda_wue_vec: np.ndarray,
    g0_vec: np.ndarray,
    d_g0_d_e_vec: np.ndarray,
    a_n_vec: np.ndarray,
    e_vec: np.ndarray,
    g_c_vec: np.ndarray,
    vpd_vec: np.ndarray,
    psi_s_vec: np.ndarray,
    psi_rc_vec: np.ndarray,
    use_quadratic_nsc: bool = False,
) -> tuple[
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    np.ndarray,
    np.ndarray,
    float,
    float,
    float,
    float,
    np.ndarray,
]:
    """Compute steady-state NSC, CUE, and operating-point outputs."""

    la = inputs.la
    c_w = inputs.c_w
    c_r = inputs.c_r
    theta_g = inputs.theta_g
    theta_r = inputs.theta_r
    f_c = inputs.f_c
    r_m_w = inputs.r_m_w
    r_m_r = inputs.r_m_r
    t_a = inputs.t_a

    lambda_wue_vec = np.asarray(lambda_wue_vec, dtype=float)
    g0_vec = np.asarray(g0_vec, dtype=float)
    d_g0_d_e_vec = np.asarray(d_g0_d_e_vec, dtype=float)
    a_n_vec = np.asarray(a_n_vec, dtype=float)
    e_vec = np.asarray(e_vec, dtype=float)
    g_c_vec = np.asarray(g_c_vec, dtype=float)
    vpd_vec = np.asarray(vpd_vec, dtype=float)
    psi_s_vec = np.asarray(psi_s_vec, dtype=float)
    psi_rc_vec = np.asarray(psi_rc_vec, dtype=float)

    n = a_n_vec.size
    c_nsc_ss_vec = np.full(n, np.nan, dtype=float)
    d_c_nsc = 1e-3

    def dtheta_gdc(c_nsc: np.ndarray | float) -> np.ndarray:
        c_nsc = np.asarray(c_nsc, dtype=float)
        return (theta_g(c_nsc + d_c_nsc) - theta_g(c_nsc)) / d_c_nsc

    def dtheta_rdc(c_nsc: np.ndarray | float) -> np.ndarray:
        c_nsc = np.asarray(c_nsc, dtype=float)
        return (theta_r(c_nsc + d_c_nsc) - theta_r(c_nsc)) / d_c_nsc

    r_m_w_0 = float(r_m_w(t_a) * c_w)
    r_m_r_0 = float(r_m_r(t_a) * c_r)
    r_m_0 = float(r_m_w_0 + r_m_r_0)

    if use_quadratic_nsc:
        k_g = float(inputs.gamma_g) * float(inputs.c_struct)
        k_r = float(inputs.gamma_r) * float(inputs.c_struct)

        a_term = la * a_n_vec
        g_term = g0_vec / (1 - f_c)

        mask_a0 = a_n_vec == 0
        mask_nan = np.isnan(a_n_vec)
        mask_inf = (a_term - r_m_0 - g_term) > 0
        mask_solve = ~(mask_a0 | mask_nan | mask_inf)

        c_nsc_ss_vec[mask_a0] = 0.0
        c_nsc_ss_vec[mask_nan] = np.nan
        c_nsc_ss_vec[mask_inf] = np.inf

        if np.any(mask_solve):
            a_s = a_term[mask_solve]
            g_s = g_term[mask_solve]

            quad_a = (r_m_0 + g_s) - a_s
            quad_b = (r_m_0 * k_g + g_s * k_r) - a_s * (k_r + k_g)
            quad_c = -a_s * k_r * k_g

            out = np.full_like(a_s, np.nan, dtype=float)

            mask_linear = quad_a == 0
            if np.any(mask_linear):
                with np.errstate(divide="ignore", invalid="ignore"):
                    out[mask_linear] = -quad_c[mask_linear] / quad_b[mask_linear]

            mask_quad = ~mask_linear
            if np.any(mask_quad):
                a_q = quad_a[mask_quad]
                b_q = quad_b[mask_quad]
                c_q = quad_c[mask_quad]
                disc = np.maximum(b_q**2 - 4 * a_q * c_q, 0.0)
                sqrt_disc = np.sqrt(disc)
                root1 = (-b_q + sqrt_disc) / (2 * a_q)
                root2 = (-b_q - sqrt_disc) / (2 * a_q)

                root = np.where((root1 >= 0) & np.isfinite(root1), root1, root2)
                root = np.where((root >= 0) & np.isfinite(root), root, np.nan)
                out[mask_quad] = root

            c_nsc_ss_vec[mask_solve] = out
    else:
        mask_a0 = a_n_vec == 0
        mask_nan = np.isnan(a_n_vec)
        with np.errstate(divide="ignore", invalid="ignore"):
            mask_inf = (la * a_n_vec - r_m_0 - g0_vec / (1 - f_c)) > 0
        mask_solve = ~(mask_a0 | mask_nan | mask_inf)

        c_nsc_ss_vec[mask_a0] = 0.0
        c_nsc_ss_vec[mask_nan] = np.nan
        c_nsc_ss_vec[mask_inf] = np.inf

        if np.any(mask_solve):
            c_nsc = np.full(n, 1.0, dtype=float)
            threshold = np.abs(la * a_n_vec / 1e3)

            for _ in range(200):
                if not np.any(mask_solve):
                    break

                idx = np.where(mask_solve)[0]
                c_i = c_nsc[idx]
                a_n_i = a_n_vec[idx]
                g0_i = g0_vec[idx]

                f_term = la * a_n_i - theta_r(c_i) * r_m_0 - theta_g(c_i) * g0_i / (1 - f_c)
                df_dc = -dtheta_rdc(c_i) * r_m_0 - dtheta_gdc(c_i) * g0_i / (1 - f_c)

                c_nsc[idx] = c_i - 0.3 * f_term / df_dc
                converged = np.abs(f_term) <= threshold[idx]
                mask_solve[idx[converged]] = False
            else:
                raise RuntimeError("Steady-state NSC Newton solver exceeded 200 iterations")

            if np.any(mask_solve):
                raise RuntimeError("Steady-state NSC Newton solver exceeded 200 iterations")

            valid_mask = ~(mask_a0 | mask_nan | mask_inf)
            c_nsc_ss_vec[valid_mask] = c_nsc[valid_mask]

    eta_ss_vec = (1 - f_c) * dtheta_gdc(c_nsc_ss_vec) * g0_vec / (
        dtheta_gdc(c_nsc_ss_vec) * g0_vec + (1 - f_c) * dtheta_rdc(c_nsc_ss_vec) * r_m_0
    )

    with np.errstate(divide="ignore", invalid="ignore"):
        lambda_wue_ss_vec = (
            -theta_g(c_nsc_ss_vec)
            / la
            * d_g0_d_e_vec
            * r_m_0
            / g0_vec
            * dtheta_rdc(c_nsc_ss_vec)
            / dtheta_gdc(c_nsc_ss_vec)
        )
    lambda_wue_ss_vec[c_nsc_ss_vec == np.inf] = np.inf
    lambda_wue_ss_vec[g0_vec == 0] = np.inf

    f_vec = lambda_wue_vec - lambda_wue_ss_vec
    idx0_candidates = np.where(g_c_vec == 0)[0]
    if idx0_candidates.size == 0:
        raise RuntimeError("Expected at least one element with g_c == 0")
    idx0 = int(idx0_candidates[0])

    if float(lambda_wue_ss_vec[idx0]) > float(lambda_wue_vec[idx0]):
        return (
            float(a_n_vec[idx0]),
            float(e_vec[idx0]),
            float(lambda_wue_vec[idx0]),
            float(g0_vec[idx0]),
            0.0,
            float(psi_s_vec[idx0]),
            float(psi_rc_vec[idx0]),
            eta_ss_vec,
            lambda_wue_ss_vec,
            float(c_nsc_ss_vec[idx0]),
            r_m_0,
            float(vpd_vec[idx0]),
            float(eta_ss_vec[idx0]),
            c_nsc_ss_vec,
        )

    if (np.nanmin(f_vec) > 0) or (np.nanmax(f_vec) < 0):
        nan = float("nan")
        return (
            nan,
            nan,
            nan,
            nan,
            nan,
            nan,
            nan,
            eta_ss_vec,
            lambda_wue_ss_vec,
            nan,
            r_m_0,
            nan,
            nan,
            c_nsc_ss_vec,
        )

    if float(f_vec[0]) == 0:
        return (
            float(a_n_vec[0]),
            float(e_vec[0]),
            float(lambda_wue_vec[0]),
            float(g0_vec[0]),
            float(g_c_vec[0]),
            float(psi_s_vec[0]),
            float(psi_rc_vec[0]),
            eta_ss_vec,
            lambda_wue_ss_vec,
            float(c_nsc_ss_vec[0]),
            r_m_0,
            float(vpd_vec[0]),
            float(eta_ss_vec[0]),
            c_nsc_ss_vec,
        )

    zero_diff_vec = np.concatenate((np.abs(np.diff(np.sign(f_vec))) / 2, [0]))
    ind_zero = np.where(zero_diff_vec == 1)[0]
    ind = int(np.min(ind_zero)) if ind_zero.size else None
    if ind is None:
        nan = float("nan")
        return (
            nan,
            nan,
            nan,
            nan,
            nan,
            nan,
            nan,
            eta_ss_vec,
            lambda_wue_ss_vec,
            nan,
            r_m_0,
            nan,
            nan,
            c_nsc_ss_vec,
        )

    f_lb = float(f_vec[ind])
    f_ub = float(f_vec[ind + 1])
    if abs(f_ub) == np.inf:
        g_c = float(g_c_vec[f_vec == f_lb][0])
        idx = np.where(g_c_vec == g_c)[0][0]
        return (
            float(a_n_vec[idx]),
            float(e_vec[idx]),
            float(lambda_wue_vec[idx]),
            float(g0_vec[idx]),
            g_c,
            float(psi_s_vec[idx]),
            float(psi_rc_vec[idx]),
            eta_ss_vec,
            lambda_wue_ss_vec,
            float(c_nsc_ss_vec[idx]),
            r_m_0,
            float(vpd_vec[idx]),
            float(eta_ss_vec[idx]),
            c_nsc_ss_vec,
        )

    g_c_lb = float(g_c_vec[f_vec == f_lb][0])
    g_c_ub = float(g_c_vec[f_vec == f_ub][0])
    g_c = g_c_lb + (g_c_ub - g_c_lb) * (0 - f_lb) / (f_ub - f_lb)

    def _interp(y_lb: float, y_ub: float) -> float:
        return y_lb + (y_ub - y_lb) * (g_c - g_c_lb) / (g_c_ub - g_c_lb)

    eta_ss = _interp(float(eta_ss_vec[g_c_vec == g_c_lb][0]), float(eta_ss_vec[g_c_vec == g_c_ub][0]))
    psi_s = _interp(float(psi_s_vec[g_c_vec == g_c_lb][0]), float(psi_s_vec[g_c_vec == g_c_ub][0]))
    psi_rc = _interp(float(psi_rc_vec[g_c_vec == g_c_lb][0]), float(psi_rc_vec[g_c_vec == g_c_ub][0]))
    e = _interp(float(e_vec[g_c_vec == g_c_lb][0]), float(e_vec[g_c_vec == g_c_ub][0]))
    a_n = _interp(float(a_n_vec[g_c_vec == g_c_lb][0]), float(a_n_vec[g_c_vec == g_c_ub][0]))
    lambda_wue = _interp(float(lambda_wue_vec[g_c_vec == g_c_lb][0]), float(lambda_wue_vec[g_c_vec == g_c_ub][0]))
    g0 = _interp(float(g0_vec[g_c_vec == g_c_lb][0]), float(g0_vec[g_c_vec == g_c_ub][0]))
    c_nsc_ss = _interp(float(c_nsc_ss_vec[g_c_vec == g_c_lb][0]), float(c_nsc_ss_vec[g_c_vec == g_c_ub][0]))
    vpd = _interp(float(vpd_vec[g_c_vec == g_c_lb][0]), float(vpd_vec[g_c_vec == g_c_ub][0]))

    return (
        a_n,
        e,
        lambda_wue,
        g0,
        g_c,
        psi_s,
        psi_rc,
        eta_ss_vec,
        lambda_wue_ss_vec,
        c_nsc_ss,
        r_m_0,
        vpd,
        eta_ss,
        c_nsc_ss_vec,
    )
