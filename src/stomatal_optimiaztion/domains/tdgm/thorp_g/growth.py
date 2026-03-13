from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from stomatal_optimiaztion.domains.tdgm.thorp_g.config import ThorpGParams


def _safe_div(num: float, den: float) -> float:
    if den == 0.0:
        if num == 0.0:
            return float("nan")
        return float(np.copysign(float("inf"), num))
    return num / den


@dataclass(frozen=True, slots=True)
class GrowthState:
    c_l: float
    c_r_h: NDArray[np.floating]
    c_r_v: NDArray[np.floating]
    c_sw: float
    c_hw: float
    c_nsc: float
    r_m: float
    u: float
    la: float
    h: float
    w: float
    d: float
    d_hw: float

    @property
    def c_w(self) -> float:
        return float(self.c_sw + self.c_hw)


def _temperature_limitation_growth(*, t_a: float) -> float:
    g_mod_t = 1.0 / (1.0 + np.exp(-0.185 * (t_a - 18.4)))
    if t_a < 7:
        g_mod_t = 0.0
    return float(g_mod_t)


def turgor_driven_growth_thorp(
    *,
    params: ThorpGParams,
    psi_s: float,
    psi_rc: float,
    u_sw: float,
    c_w: float,
    t_a: float,
) -> tuple[float, float]:
    """Return `(g_max, c_sucrose_p)` per MATLAB v1.4.

    Baseline:
    - `TDGM/example/Supplementary Code __THORP_code_v1.4/FUNCTION_Turgor_driven_growth_THORP.m`
    """

    a = 3.0 / 2.0
    b = 2.0 / 3.0

    v_s = float(params.v_sucrose)
    phi = float(params.phi_wall)
    gamma = float(params.gamma_turgor_crit + params.gamma_turgor_shift)

    m_p = 0.48 - 0.13 * float(psi_s)
    c_sucrose_p = float(m_p * params.rho / (1.0 - m_p * params.rho * v_s))
    pi = float(
        -1e-6
        * params.rho
        * params.r_gas
        * (float(t_a) + 273.15)
        * (0.998 * m_p + 0.089 * m_p**2)
    )

    z_norm_plus = _safe_div(pi + gamma - float(psi_s), float(psi_rc) - float(psi_s))
    z_norm_plus = float(np.clip(z_norm_plus, 0.0, 1.0))

    int_p_minus_gamma_dz_norm = (float(psi_s) - pi - gamma) * (1 - z_norm_plus) + (
        (float(psi_rc) - float(psi_s)) / 2.0
    ) * (1 - z_norm_plus**2)

    g_max = (1 + 2 * a) / a / b * phi * float(c_w) * _safe_div(int_p_minus_gamma_dz_norm, float(u_sw))
    return float(g_max), float(c_sucrose_p)


def grow(
    *,
    params: ThorpGParams,
    u_l: float,
    u_r_h: NDArray[np.floating],
    u_r_v: NDArray[np.floating],
    u_sw: float,
    a_n: float,
    r_d: float,
    c_l: float,
    c_r_h: NDArray[np.floating],
    c_r_v: NDArray[np.floating],
    c_sw: float,
    c_hw: float,
    c_nsc: float,
    t_a: float,
    t_soil: float,
    psi_s: float,
    psi_rc: float,
) -> GrowthState:
    """THORP-G growth update (turgor-limited + NSC-limited), matching MATLAB v1.4."""

    s_l = c_l / params.tau_l
    s_r_h = c_r_h / params.tau_r
    s_r_v = c_r_v / params.tau_r
    s_sw = c_sw / params.tau_sw

    la = params.sla * c_l
    c_r = float(np.sum(c_r_h + c_r_v))

    r_r = c_r * float(params.r_m_r_func(t_soil))
    r_sw = c_sw * float(params.r_m_sw_func(t_a))
    r_m = la * r_d + r_r + r_sw
    a_g = a_n + r_d

    c_w = float(c_sw + c_hw)
    if not np.isnan(u_sw):
        g_max, c_sucrose_p = turgor_driven_growth_thorp(
            params=params, psi_s=float(psi_s), psi_rc=float(psi_rc), u_sw=float(u_sw), c_w=c_w, t_a=float(t_a)
        )
    elif u_sw == 0:
        g_max = 0.0
        c_sucrose_p = float("nan")
    else:
        raise RuntimeError("Invalid u_sw")

    g_mod_t = _temperature_limitation_growth(t_a=float(t_a))

    v = float((c_w + c_r) / params.rho_cw + c_l / params.rho_cl)
    c_nsc_mob = float(12.0 * c_sucrose_p * v)
    c_nsc_immob = float(c_nsc - c_nsc_mob)
    if c_nsc_immob < 0:
        raise RuntimeError("negative NSC")

    k_mm = float(12.0 * params.c_mm_sucrose * v)
    g_mod_nsc = float(c_nsc_immob / (c_nsc_immob + k_mm))

    g_rate = float(g_max * g_mod_t * g_mod_nsc)

    nan_count = int(np.sum(np.isnan(np.concatenate([[u_l, u_sw], (u_r_h + u_r_v)]))))
    if nan_count == (u_r_h.size + 2):
        g_rate = 0.0
        u_l = 0.0
        u_r_h = np.zeros_like(u_r_h, dtype=float)
        u_r_v = np.zeros_like(u_r_v, dtype=float)
        u_sw = 0.0
    elif nan_count > 0:
        raise RuntimeError("Invalid allocation fractions (partial NaNs)")

    # Growth plus construction respiration.
    u = float(_safe_div(g_rate, 1.0 - params.f_c))

    c_l = c_l + params.dt * (u_l * g_rate - s_l)
    c_r_h = c_r_h + params.dt * (u_r_h * g_rate - s_r_h)
    c_r_v = c_r_v + params.dt * (u_r_v * g_rate - s_r_v)
    c_sw = c_sw + params.dt * (u_sw * g_rate - s_sw)
    c_hw = c_hw + params.dt * s_sw
    c_nsc = c_nsc + params.dt * (la * a_g - r_m - u)

    if c_l < 0:
        raise RuntimeError("negative leaf carbon")
    if np.any(c_r_h < 0):
        raise RuntimeError("negative lateral root carbon")
    if np.any(c_r_v < 0):
        raise RuntimeError("negative vertical root carbon")
    if c_sw < 0:
        raise RuntimeError("negative sapwood carbon")
    if c_nsc < 0:
        raise RuntimeError("negative NSC")
    if np.any(np.isnan(np.concatenate([[c_l, c_sw, c_nsc], c_r_h, c_r_v]))):
        raise RuntimeError("NaNs in growth state")

    c_w = c_sw + c_hw
    d = float((c_w / (params.rho_cw * params.xi * params.b0 * (params.d_ref ** (-params.c0)))) ** (1 / (2 + params.c0)))
    h = float(params.b0 * (d / params.d_ref) ** params.c0)
    w = float(params.b1 * (d / params.d_ref) ** params.c1)
    d_hw = float((c_hw / (params.rho_cw * params.xi * h)) ** 0.5)
    la = float(params.sla * c_l)

    return GrowthState(
        c_l=float(c_l),
        c_r_h=c_r_h.astype(float),
        c_r_v=c_r_v.astype(float),
        c_sw=float(c_sw),
        c_hw=float(c_hw),
        c_nsc=float(c_nsc),
        r_m=float(r_m),
        u=float(u),
        la=la,
        h=h,
        w=w,
        d=d,
        d_hw=d_hw,
    )
