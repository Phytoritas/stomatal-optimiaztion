from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.gosm.params.defaults import BaselineInputs
from stomatal_optimiaztion.domains.gosm.utils.traceability import implements


@implements(
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
def carbon_assimilation(
    g_c_vec: np.ndarray,
    t_l_vec: np.ndarray,
    *,
    inputs: BaselineInputs,
    r_abs: float,
    L: float,
    d_e_d_g_w_vec: np.ndarray,
    d_g_w_d_g_c_vec: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Leaf or canopy carbon assimilation and marginal profit."""

    g_c_vec = np.asarray(g_c_vec, dtype=float)
    t_l_vec = np.asarray(t_l_vec, dtype=float)
    d_e_d_g_w_vec = np.asarray(d_e_d_g_w_vec, dtype=float)
    d_g_w_d_g_c_vec = np.asarray(d_g_w_d_g_c_vec, dtype=float)

    var_kappa = inputs.var_kappa
    theta_j = inputs.theta_j
    theta_c = inputs.theta_c
    c_a = inputs.c_a
    o_a = inputs.o_a
    c_p = inputs.c_p
    emiss = inputs.emiss
    sigma = inputs.sigma
    g_b = inputs.g_b

    v_cmax_vec = inputs.v_cmax(t_l_vec)
    j_max_vec = inputs.j_max(t_l_vec)
    j_phi = var_kappa * r_abs
    j_vec = (j_max_vec + j_phi) / (2 * theta_j) - np.sqrt(
        ((j_max_vec + j_phi) / (2 * theta_j)) ** 2 - j_max_vec * j_phi / theta_j
    )
    gamma_star_vec = inputs.gamma_star(t_l_vec)
    k_c_vec = inputs.k_c(t_l_vec)
    k_o_vec = inputs.k_o(t_l_vec)
    r_d_vec = inputs.r_d(t_l_vec)

    def a_c_func(
        g_c: float,
        a_n: np.ndarray,
        c_a_: float,
        v_cmax: float,
        gamma_star: float,
        r_d: float,
        k_c: float,
        k_o: float,
        o_a_: float,
    ) -> np.ndarray:
        return v_cmax * (c_a_ - a_n / g_c - gamma_star) / (
            c_a_ - a_n / g_c + k_c * (1 + o_a_ / k_o)
        ) - r_d

    def a_j_func(
        g_c: float,
        a_n: np.ndarray,
        c_a_: float,
        j: float,
        gamma_star: float,
        r_d: float,
    ) -> np.ndarray:
        return (j / 4) * (c_a_ - a_n / g_c - gamma_star) / (
            c_a_ - a_n / g_c + 2 * gamma_star
        ) - r_d

    a_n_vec = np.full(g_c_vec.size, np.nan, dtype=float)

    for idx in range(g_c_vec.size):
        g_c_i = float(g_c_vec[idx])
        v_cmax_i = float(v_cmax_vec[idx])
        j_i = float(j_vec[idx])
        gamma_star_i = float(gamma_star_vec[idx])
        r_d_i = float(r_d_vec[idx])
        k_c_i = float(k_c_vec[idx])
        k_o_i = float(k_o_vec[idx])

        if g_c_i == 0:
            a_n_vec[idx] = -r_d_i if j_i < 1e-16 else 0.0
            continue

        if g_c_i < 0:
            a_n_vec[idx] = np.nan
            continue

        if j_i < 1e-16:
            a_n_vec[idx] = -r_d_i
            continue

        a_n_max = min(max(v_cmax_i, j_i / 4), g_c_i * c_a)
        a_n_lb = -r_d_i
        a_n_ub = a_n_max
        a_n_mid = (a_n_lb + a_n_ub) / 2
        a_n_i = np.array([a_n_lb, a_n_mid, a_n_ub], dtype=float)

        iteration = 0
        while True:
            iteration += 1
            if iteration > 100:
                raise RuntimeError("Carbon assimilation solver exceeded 100 iterations")

            a_c_i = a_c_func(g_c_i, a_n_i, c_a, v_cmax_i, gamma_star_i, r_d_i, k_c_i, k_o_i, o_a)
            a_j_i = a_j_func(g_c_i, a_n_i, c_a, j_i, gamma_star_i, r_d_i)
            a_n_hypmin = (a_c_i + a_j_i) / (2 * theta_c) - np.sqrt(
                ((a_c_i + a_j_i) / (2 * theta_c)) ** 2 - a_c_i * a_j_i / theta_c
            )
            f_obj = (a_n_i - a_n_hypmin) / a_n_max

            if np.any(np.abs(f_obj) < 1e-4):
                break

            f_ub = np.min(f_obj[f_obj > 0])
            f_lb_values = f_obj[f_obj < 0]
            f_lb = np.max(f_lb_values) if f_lb_values.size else np.nan

            a_n_lb = np.min(a_n_i[f_obj == f_lb]) if np.isfinite(f_lb) else -r_d_i
            a_n_ub = np.max(a_n_i[f_obj == f_ub])

            if a_n_lb == a_n_ub:
                raise RuntimeError("Assimilation solver bracket collapsed")

            a_n_mid = (a_n_lb + a_n_ub) / 2
            a_n_i = np.array([a_n_lb, a_n_mid, a_n_ub], dtype=float)

        a_n_candidates = a_n_i[np.abs(f_obj) == np.min(np.abs(f_obj))]
        a_n_vec[idx] = float(a_n_candidates[0])

    with np.errstate(divide="ignore", invalid="ignore"):
        c_i_vec = c_a - a_n_vec / g_c_vec
    if np.any(c_i_vec[1:] < 0):
        raise RuntimeError("Negative internal CO2 encountered")

    c_i_min_vec = (
        r_d_vec * k_c_vec * (1 + o_a / k_o_vec) + v_cmax_vec * gamma_star_vec
    ) / (v_cmax_vec - r_d_vec)
    a_c_gross_0 = v_cmax_vec * (c_i_min_vec - gamma_star_vec) / (
        c_i_min_vec + k_c_vec * (1 + o_a / k_o_vec)
    )

    zero_mask = g_c_vec == 0
    if np.any(zero_mask):
        low_light_zero_mask = np.zeros_like(zero_mask, dtype=bool)
        low_light_zero_mask[zero_mask] = (j_vec[zero_mask] / 4) < a_c_gross_0[zero_mask]
        c_i_min_vec[low_light_zero_mask] = np.inf
        c_i_vec[zero_mask] = c_i_min_vec[zero_mask]

    with np.errstate(divide="ignore", invalid="ignore"):
        a_c_vec = v_cmax_vec * (c_a - a_n_vec / g_c_vec - gamma_star_vec) / (
            c_a - a_n_vec / g_c_vec + k_c_vec * (1 + o_a / k_o_vec)
        ) - r_d_vec
        a_j_vec = (j_vec / 4) * (c_a - a_n_vec / g_c_vec - gamma_star_vec) / (
            c_a - a_n_vec / g_c_vec + 2 * gamma_star_vec
        ) - r_d_vec

        d_a_n_d_a_c_vec = (
            1
            - (a_c_vec + (1 - 2 * theta_c) * a_j_vec)
            / np.sqrt((a_c_vec + a_j_vec) ** 2 - 4 * theta_c * a_c_vec * a_j_vec)
        ) / (2 * theta_c)
        d_a_n_d_a_j_vec = (
            1
            - (a_j_vec + (1 - 2 * theta_c) * a_c_vec)
            / np.sqrt((a_c_vec + a_j_vec) ** 2 - 4 * theta_c * a_c_vec * a_j_vec)
        ) / (2 * theta_c)

        d_a_c_d_c_i_vec = v_cmax_vec * (gamma_star_vec + k_c_vec * (1 + o_a / k_o_vec)) / (
            c_i_vec + k_c_vec * (1 + o_a / k_o_vec)
        ) ** 2
        d_a_j_d_c_i_vec = 0.75 * j_vec * gamma_star_vec / (c_i_vec + 2 * gamma_star_vec) ** 2

        k_ci_vec = d_a_n_d_a_c_vec * d_a_c_d_c_i_vec + d_a_n_d_a_j_vec * d_a_j_d_c_i_vec

        d_j_d_j_max_vec = (
            1
            - (j_max_vec + (1 - 2 * theta_j) * j_phi)
            / np.sqrt((j_max_vec + j_phi) ** 2 - 4 * theta_j * j_max_vec * j_phi)
        ) / (2 * theta_j)
        d_t_l = 0.01
        d_v_cmax_d_t_l_vec = (inputs.v_cmax(t_l_vec + d_t_l) - v_cmax_vec) / d_t_l
        d_j_max_d_t_l_vec = (inputs.j_max(t_l_vec + d_t_l) - j_max_vec) / d_t_l
        d_r_d_d_t_l_vec = (inputs.r_d(t_l_vec + d_t_l) - r_d_vec) / d_t_l
        d_a_c_d_v_cmax_vec = (a_c_vec + r_d_vec) / v_cmax_vec
        d_a_j_d_j_vec = 0.25 * (c_i_vec - gamma_star_vec) / (c_i_vec + 2 * gamma_star_vec)

        xi_vec = d_a_n_d_a_c_vec * (
            d_a_c_d_v_cmax_vec * d_v_cmax_d_t_l_vec - d_r_d_d_t_l_vec
        ) + d_a_n_d_a_j_vec * (
            d_a_j_d_j_vec * d_j_d_j_max_vec * d_j_max_d_t_l_vec - d_r_d_d_t_l_vec
        )

        t_l_k = t_l_vec + 273.15
        lambda_wue_vec = k_ci_vec / (k_ci_vec + g_c_vec) * (c_a - c_i_vec) / d_g_w_d_g_c_vec / d_e_d_g_w_vec - g_c_vec / (
            k_ci_vec + g_c_vec
        ) * xi_vec * L / (4 * emiss * sigma * t_l_k**3 + c_p * g_b)

    a_c_vec[g_c_vec == 0] = 0
    a_j_vec[g_c_vec == 0] = 0
    d_a_n_d_a_c_vec[g_c_vec == 0] = 0
    d_a_n_d_a_j_vec[g_c_vec == 0] = 1
    d_a_j_d_j_vec[c_i_vec == np.inf] = 0.25
    lambda_wue_vec[g_c_vec == 0] = (
        c_a - c_i_vec[g_c_vec == 0]
    ) / d_g_w_d_g_c_vec[g_c_vec == 0] / d_e_d_g_w_vec[g_c_vec == 0]
    lambda_wue_vec[j_vec < 1e-16] = d_r_d_d_t_l_vec[j_vec < 1e-16] * L / (
        4 * emiss * sigma * t_l_k[j_vec < 1e-16] ** 3 + c_p * g_b
    )

    if np.any(np.isnan(lambda_wue_vec[g_c_vec > 0])):
        raise RuntimeError("NaN encountered in lambda_wue where g_c > 0")

    return a_n_vec, r_d_vec, lambda_wue_vec
