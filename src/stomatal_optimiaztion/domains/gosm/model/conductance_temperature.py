from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.gosm.params.defaults import BaselineInputs
from stomatal_optimiaztion.domains.gosm.utils.traceability import implements


@implements(
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
def conductances_and_temperature(
    e_vec: np.ndarray,
    d_g0_d_e_vec: np.ndarray,
    *,
    inputs: BaselineInputs,
    r_abs: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    """Leaf temperature and conductances matching the MATLAB baseline."""

    e_vec = np.asarray(e_vec, dtype=float)
    d_g0_d_e_vec = np.asarray(d_g0_d_e_vec, dtype=float)

    p_atm = inputs.p_atm
    t_a = inputs.t_a
    rh = inputs.rh
    g_b = inputs.g_b
    m = inputs.m
    c_p = inputs.c_p
    emiss = inputs.emiss
    sigma = inputs.sigma

    t_a_k = t_a + 273.15

    latent_heat = 1.91846e6 * (t_a_k / (t_a_k - 33.91)) ** 2
    latent_heat = float(m * latent_heat)

    n = e_vec.size
    t_l_k = np.full(n, np.nan, dtype=float)
    for idx in range(n):
        t_l_i = t_a_k
        e_i = float(e_vec[idx])

        iteration = 0
        while True:
            iteration += 1
            if iteration > 100:
                raise RuntimeError("Leaf temperature Newton solver exceeded 100 iterations")

            residual = emiss * sigma * t_l_i**4 + latent_heat * e_i + c_p * g_b * (t_l_i - t_a_k) - r_abs
            residual_slope = 4 * emiss * sigma * t_l_i**3 + c_p * g_b

            t_l_i = t_l_i - 0.3 * residual / residual_slope

            if abs(residual) < abs((latent_heat * e_i - c_p * g_b * t_a_k - r_abs) / 1e4):
                break

            if abs(latent_heat * e_i - c_p * g_b * t_a_k - r_abs) < 1e-6:
                if abs(residual) < abs(c_p * g_b * t_a_k / 1e6):
                    break

        t_l_k[idx] = t_l_i

    t_l_c = t_l_k - 273.15
    t_a_c = t_a_k - 273.15

    e_l_vec = 0.61078 * np.exp(17.27 * t_l_c / (t_l_c + 237.3))
    e_a = rh * 0.61078 * np.exp(17.27 * t_a_c / (t_a_c + 237.3))
    vpd_vec = e_l_vec - e_a

    g_w_vec = 1.0 / (vpd_vec / p_atm / e_vec - 1.0 / g_b)
    g_c_vec = 1.0 / (1.6 / g_w_vec + 1.37 / g_b)

    s_vec = 17.27 * 237.3 * e_l_vec / (t_l_c + 237.3) ** 2

    d_e_d_g_w_vec = e_vec / g_w_vec**2 / (
        1.0 / g_w_vec + 1.0 / g_b + s_vec * latent_heat / p_atm / (4 * emiss * sigma * t_l_k**3 + c_p * g_b)
    )
    d_e_d_g_w_vec[g_w_vec == 0] = vpd_vec[g_w_vec == 0] / p_atm

    d_g_w_d_g_c_vec = (1.6 + 1.37 * g_w_vec / g_b) ** 2 / 1.6
    d_g0_d_g_c_vec = d_g0_d_e_vec * d_e_d_g_w_vec * d_g_w_d_g_c_vec

    return (
        t_l_c,
        g_w_vec,
        g_c_vec,
        vpd_vec,
        d_e_d_g_w_vec,
        d_g_w_d_g_c_vec,
        d_g0_d_g_c_vec,
        latent_heat,
    )
