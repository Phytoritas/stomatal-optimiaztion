from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.tdgm.implements import implements


@implements("Eq_S2.12", "Eq_S2.16")
def turgor_driven_growth_rate(
    *,
    psi_s: np.ndarray | float,
    psi_rc: np.ndarray | float,
    phi: float,
    p_turgor_crit: float,
    u_sw: np.ndarray | float,
    c_sw: np.ndarray | float,
    c_hw: np.ndarray | float,
    rho_w: float,
    r_gas: float,
    t_a: np.ndarray | float,
    a: float,
    b: float,
) -> np.ndarray:
    """Whole-tree growth rate from turgor-driven tissue expansion."""

    psi_s = np.asarray(psi_s, dtype=float)
    psi_rc = np.asarray(psi_rc, dtype=float)
    u_sw = np.asarray(u_sw, dtype=float)
    c_sw = np.asarray(c_sw, dtype=float)
    c_hw = np.asarray(c_hw, dtype=float)
    t_a = np.asarray(t_a, dtype=float)

    c_w = c_sw + c_hw
    m_p = 0.48 - 0.13 * psi_s
    pi = -1e-6 * float(rho_w) * float(r_gas) * (t_a + 273.15) * (0.998 * m_p + 0.089 * m_p**2)

    with np.errstate(divide="ignore", invalid="ignore"):
        z_norm_plus = (pi + float(p_turgor_crit) - psi_s) / (psi_rc - psi_s)
    z_norm_plus = np.clip(z_norm_plus, 0.0, 1.0)

    int_p_minus_gamma = (psi_s - pi - float(p_turgor_crit)) * (1.0 - z_norm_plus) + (psi_rc - psi_s) / 2.0 * (
        1.0 - z_norm_plus**2
    )

    with np.errstate(divide="ignore", invalid="ignore"):
        g_growth = ((1.0 + 2.0 * float(a)) / float(a) / float(b)) * float(phi) * (c_w / u_sw) * int_p_minus_gamma
    return np.asarray(g_growth, dtype=float)
