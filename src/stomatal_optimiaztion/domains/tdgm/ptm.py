from __future__ import annotations

from collections.abc import Callable

import numpy as np
from scipy import special

from stomatal_optimiaztion.domains.tdgm.implements import implements


def mu_sucrose(c_p: np.ndarray | float, t_c: np.ndarray | float) -> np.ndarray:
    """Dynamic viscosity of a sucrose solution in MPa s."""

    c_p = np.asarray(c_p, dtype=float)
    t_c = np.asarray(t_c, dtype=float)

    rho_solution = 998.0
    molar_mass_sucrose = 342e-3

    c_mass = c_p * molar_mass_sucrose / rho_solution
    c_g_per_kg = 1000.0 * c_mass

    u_1 = c_g_per_kg / 900.0
    u_2 = t_c / 90.0

    v_1 = 1.0 / (1.0 + np.exp(-(-0.8232639 * u_1 + 0.1552180 * u_2 + 2.121665)))
    v_2 = 1.0 / (1.0 + np.exp(-(-6.263356 * u_1 + 3.655903 * u_2 + 9.890403)))
    v_3 = 1.0 / (1.0 + np.exp(-(0.9544210 * u_1 + 0.8726018 * u_2 + 3.996007)))
    v_4 = 1.0 / (1.0 + np.exp(-(-9.930766 * u_1 + 1.631972 * u_2 + 13.76070)))
    v_5 = 1.0 / (1.0 + np.exp(-(-46.32714 * u_1 + 14.32810 * u_2 + 44.07883)))

    w = 1.0 / (
        1.0
        + np.exp(
            -(
                -26.77806 * v_1
                - 85.06680 * v_2
                - 62.71757 * v_3
                - 225.7701 * v_4
                - 345.4294 * v_5
                + 740.5184
            )
        )
    )

    mu_mpa_s = 10.0 ** (5.6 * w - 1.0)
    return mu_mpa_s / 1e9


def _lower_incomplete_gamma(a: float, x: np.ndarray) -> np.ndarray:
    return special.gamma(a) * special.gammainc(a, x)


@implements("Eq_S1.26", "Eq_S1.30", "Eq_S1.35", "Eq_S1.36", "Eq_S1.38")
def phloem_transport_concentration(
    *,
    c_p_apex: float,
    h_tree: float,
    z: np.ndarray | float,
    psi_rc: float,
    psi_s: float,
    g_growth: float,
    u_r_h: float,
    u_r_v: float,
    sigma: float,
    kappa_p0: float,
    delta: float,
    kappa_p_height_exp: float,
    h_ref: float,
    a: float,
    b: float,
    r_gas: float,
    g_grav: float,
    k_s: float,
    rho_w: float,
    c_r: float,
    c_sw: float,
    f_c: float,
    r_m_r_func: Callable[[float], float],
    r_m_sw_func: Callable[[float], float],
    t_a: float,
    t_soil: float,
    m_p: float = 0.13,
    varpi: float = 1e-6,
) -> np.ndarray:
    """Compute PTM phloem sugar concentration along height."""

    h_tree = float(h_tree)
    c_p_apex = float(c_p_apex)
    psi_rc = float(psi_rc)
    psi_s = float(psi_s)
    g_growth = float(g_growth)
    u_r_h = float(u_r_h)
    u_r_v = float(u_r_v)
    sigma = float(sigma)
    kappa_p0 = float(kappa_p0)
    delta = float(delta)
    kappa_p_height_exp = float(kappa_p_height_exp)
    h_ref = float(h_ref)
    a = float(a)
    b = float(b)
    r_gas = float(r_gas)
    g_grav = float(g_grav)
    k_s = float(k_s)
    rho_w = float(rho_w)
    c_r = float(c_r)
    c_sw = float(c_sw)
    f_c = float(f_c)
    t_a = float(t_a)
    t_soil = float(t_soil)
    z = np.asarray(z, dtype=float)

    alpha = 1.0 / 12.0

    d_psi_dz = min((psi_rc - psi_s) / h_tree, float(varpi) * rho_w * g_grav)

    r_m_r = float(c_r) * float(r_m_r_func(t_soil))
    r_m_sw = float(c_sw) * float(r_m_sw_func(t_a))
    l_net = float(r_m_r + r_m_sw + g_growth / (1.0 - f_c))

    u_r = float(u_r_h + u_r_v)
    phi_s = c_p_apex**2 / 2.0
    z_norm = z / h_tree

    pi_apex = -varpi * r_gas * (t_a + 273.15) * c_p_apex
    psi_max = -d_psi_dz * h_tree
    p_max = psi_max - pi_apex
    if p_max <= 0:
        return np.full_like(z_norm, np.nan, dtype=float)

    mu = float(mu_sucrose(c_p_apex, t_a))
    one_minus_exp_neg_sigma = 1.0 - np.exp(-sigma)
    coef_a = -alpha * l_net / one_minus_exp_neg_sigma
    coef_b = -alpha * g_growth / (1.0 - f_c) * (1.0 - u_r)
    coef_c = -alpha * r_m_sw
    coef_d = alpha * l_net / one_minus_exp_neg_sigma

    beta = c_p_apex / 2.0 * (d_psi_dz - varpi * rho_w * g_grav)
    eta = 2.0 * varpi * g_grav * m_p * phi_s
    epsilon = varpi * k_s * r_gas * (t_a + 273.15) * phi_s / h_tree
    zeta = mu / kappa_p0 * (h_ref / h_tree) ** kappa_p_height_exp

    if beta >= eta:
        return np.full_like(z_norm, np.nan, dtype=float)

    denom1 = sigma * epsilon + eta - beta
    denom2 = eta - beta
    a1 = 1.0 - delta
    a2 = 2.0 - delta
    a3 = a * (b - 1.0) + 2.0 - delta

    x1 = (denom1 / epsilon) * z_norm
    x2 = (denom2 / epsilon) * z_norm

    theta = (
        coef_a * (epsilon / denom1) ** a1 * _lower_incomplete_gamma(a1, x1)
        + coef_b * (epsilon / denom2) ** a2 * _lower_incomplete_gamma(a2, x2)
        + coef_c * (epsilon / denom2) ** a3 * _lower_incomplete_gamma(a3, x2)
        + coef_d * (epsilon / denom2) ** a1 * _lower_incomplete_gamma(a1, x2)
    )

    phi_norm = np.exp((eta - beta) / epsilon * z_norm) * ((eta - 2.0 * beta) / (eta - beta) - (zeta / epsilon) * theta) + beta / (eta - beta)
    phi = phi_s * phi_norm

    c_p_complex = np.sqrt((2.0 * phi).astype(complex))
    imag_mask = np.abs(np.imag(c_p_complex)) > 0
    c_p = np.where(imag_mask, np.nan, np.real(c_p_complex))
    return np.asarray(c_p, dtype=float)
