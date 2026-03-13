from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from stomatal_optimiaztion.domains.thorp.implements import implements
from stomatal_optimiaztion.domains.thorp.vulnerability import WeibullVC

_ROOT_INTEGRATION_N = 20
_ROOT_INTEGRATION_FRACTIONS = np.linspace(0.0, 1.0, _ROOT_INTEGRATION_N, dtype=float)


def _reverse_cumsum(x: NDArray[np.floating], axis: int = 0) -> NDArray[np.floating]:
    return np.flip(np.cumsum(np.flip(x, axis=axis), axis=axis), axis=axis)


def _safe_div(num: float, den: float) -> float:
    if den == 0.0:
        if num == 0.0:
            return float("nan")
        return float(np.copysign(float("inf"), num))
    return num / den


@dataclass(frozen=True, slots=True)
class RootUptakeParams:
    beta_r_h: float
    beta_r_v: float
    vc_r: WeibullVC
    rho: float
    g: float


@dataclass(frozen=True, slots=True)
class RootUptakeResult:
    e: float
    e_soil: NDArray[np.floating]
    r_r_h: NDArray[np.floating]
    r_r_v: NDArray[np.floating]
    f_r: NDArray[np.floating]


ResponseCurve = Callable[[NDArray[np.floating]], NDArray[np.floating]]


@implements("E_S2_2", "E_S3_1", "E_S3_2", "E_S3_3", "E_S3_4", "E_S3_5")
def e_from_soil_to_root_collar(
    *,
    params: RootUptakeParams,
    psi_rc: float,
    psi_soil_by_layer: NDArray[np.floating],
    z_soil_mid: NDArray[np.floating],
    dz: NDArray[np.floating],
    la: float,
    c_r_h: NDArray[np.floating],
    c_r_v: NDArray[np.floating],
) -> RootUptakeResult:
    c_r = c_r_h + c_r_v
    vc_r_at_zero = float(params.vc_r(0.0))
    hydro_head = params.rho * params.g * z_soil_mid / 1e6
    r_r_h_min = np.divide(
        params.beta_r_h,
        c_r_h,
        out=np.full_like(c_r_h, np.inf, dtype=float),
        where=c_r_h != 0,
    )
    r_r_v = np.divide(
        params.beta_r_v * dz**2,
        c_r_v,
        out=np.full_like(c_r_v, np.inf, dtype=float),
        where=c_r_v != 0,
    )
    r_r_v_sum = np.cumsum(r_r_v)

    e_soil = np.full_like(psi_soil_by_layer, np.nan, dtype=float)
    f_r = np.full_like(psi_soil_by_layer, np.nan, dtype=float)
    active = c_r > 0
    inactive = ~active
    if np.any(inactive):
        e_soil[inactive] = 0.0
        psi_inactive = np.minimum(psi_soil_by_layer[inactive], 0.0)
        f_r[inactive] = np.asarray(params.vc_r(psi_inactive), dtype=float)

    if np.any(active):
        psi_active = psi_soil_by_layer[active]
        r_r_h_min_active = r_r_h_min[active]
        r_r_v_sum_active = r_r_v_sum[active]
        hydro_head_active = hydro_head[active]

        equal_mask = psi_active == psi_rc
        zero_mask = (psi_active - psi_rc) == hydro_head_active
        other_mask = ~(equal_mask | zero_mask)

        f_active = np.empty_like(psi_active, dtype=float)
        e_active = np.empty_like(psi_active, dtype=float)

        if np.any(equal_mask):
            psi_src_min = np.minimum(psi_active[equal_mask], psi_rc)
            f_eq = np.asarray(params.vc_r(psi_src_min), dtype=float)
            f_eq = np.where(psi_src_min > 0, vc_r_at_zero, f_eq)
            r_r_h_eq = np.divide(
                r_r_h_min_active[equal_mask],
                f_eq,
                out=np.full_like(f_eq, np.inf, dtype=float),
                where=f_eq != 0,
            )
            r_r_eq = r_r_h_eq + r_r_v_sum_active[equal_mask]
            e_active[equal_mask] = -hydro_head_active[equal_mask] / r_r_eq / la
            f_active[equal_mask] = f_eq

        if np.any(zero_mask):
            psi_src_min = np.minimum(psi_active[zero_mask], psi_rc)
            f_zero = np.asarray(params.vc_r(psi_src_min), dtype=float)
            f_zero = np.where(psi_src_min > 0, vc_r_at_zero, f_zero)
            e_active[zero_mask] = 0.0
            f_active[zero_mask] = f_zero

        if np.any(other_mask):
            psi_src_min = np.minimum(psi_active[other_mask], psi_rc)
            psi_src_max = np.maximum(psi_active[other_mask], psi_rc)
            psi_src = psi_src_min[:, None] + (psi_src_max - psi_src_min)[:, None] * _ROOT_INTEGRATION_FRACTIONS
            f_vals = np.asarray(params.vc_r(psi_src), dtype=float)
            f_vals = np.where(psi_src > 0, vc_r_at_zero, f_vals)
            f_other = np.mean(f_vals, axis=1)
            r_r_h_other = np.divide(
                r_r_h_min_active[other_mask],
                f_other,
                out=np.full_like(f_other, np.inf, dtype=float),
                where=f_other != 0,
            )
            r_r_other = r_r_h_other + r_r_v_sum_active[other_mask]
            e_active[other_mask] = (
                psi_active[other_mask] - psi_rc - hydro_head_active[other_mask]
            ) / r_r_other / la
            f_active[other_mask] = f_other

        e_soil[active] = e_active
        f_r[active] = f_active

    e = float(np.sum(e_soil))

    z_ref = float(z_soil_mid[-1])
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        r_r = (psi_soil_by_layer - psi_rc - params.rho * params.g * z_ref / 1e6) / e_soil / la
        r_r_h = r_r - r_r_v_sum
    r_r_h = np.maximum(r_r_h, r_r_h_min)

    if np.isnan(e):
        raise RuntimeError("Error calculating E (NaN)")

    return RootUptakeResult(
        e=e,
        e_soil=e_soil.astype(float),
        r_r_h=r_r_h.astype(float),
        r_r_v=r_r_v.astype(float),
        f_r=f_r.astype(float),
    )


@dataclass(frozen=True, slots=True)
class StomataParams:
    root_uptake: RootUptakeParams
    g_wmin: float
    c_prime1: float
    c_prime2: float
    d_ref: float
    c0: float
    c1: float
    b2: float
    c2: float
    k_l: float
    vc_sw: WeibullVC
    vc_l: WeibullVC
    v_cmax_func: ResponseCurve
    j_max_func: ResponseCurve
    gamma_star_func: ResponseCurve
    k_c_func: ResponseCurve
    k_o_func: ResponseCurve
    r_d_func: ResponseCurve
    var_kappa: float
    c_a: float
    o_a: float

    @property
    def rho(self) -> float:
        return self.root_uptake.rho

    @property
    def g(self) -> float:
        return self.root_uptake.g

    @property
    def vc_r(self) -> WeibullVC:
        return self.root_uptake.vc_r


@dataclass(frozen=True, slots=True)
class StomataResult:
    psi_l: float
    psi_s: float
    psi_rc: float
    psi_rc0: float
    e: float
    e_soil: NDArray[np.floating]
    a_n: float
    r_d: float
    t_l: float
    g_w: float
    lambda_wue: float
    d_a_n_d_r_abs: float
    d_e_d_la: float
    d_e_d_d: float
    d_e_d_c_r_h: NDArray[np.floating]
    d_e_d_c_r_v: NDArray[np.floating]


@implements(
    "E_S3_6",
    "E_S3_7",
    "E_S3_10",
    "E_S3_8",
    "E_S3_9",
    "E_S3_25",
    "E_S3_26",
    "E_S3_27",
    "E_S3_32",
    "E_S3_33",
    "E_S3_34",
    "E_S3_42",
    "E_S3_49_to_55_raw",
    "E_S4_7",
    "E_S4_8",
    "E_S6_1",
    "E_S6_2",
    "E_S6_3",
    "E_S6_4",
    "E_S6_5",
    "E_S6_6",
    "E_S6_7",
    "E_S6_8",
    "E_S6_9",
    "E_S6_10",
    "E_S6_11",
    "E_S6_12",
    "E_S6_13",
    "E_S6_14",
    "E_S6_15",
    "E_S6_16",
)
def stomata(
    *,
    params: StomataParams,
    psi_soil_by_layer: NDArray[np.floating],
    n_soil: int,
    dz: NDArray[np.floating],
    z_soil_mid: NDArray[np.floating],
    t_a: float,
    rh: float,
    r_abs: float,
    la: float,
    c_r_h: NDArray[np.floating],
    c_r_v: NDArray[np.floating],
    h: float,
    w: float,
    d: float,
    d_hw: float,
    d_r_abs_d_h: float,
    d_r_abs_d_w: float,
    d_r_abs_d_la: float,
) -> StomataResult:
    c_r = c_r_h + c_r_v
    n = 20

    k_sw_max = params.b2 * (d / params.d_ref) ** params.c2 * (
        1 - (d_hw / d) ** (params.c2 / params.c0 + 1)
    )
    dk_sw_max_d_d = (
        k_sw_max
        / d
        * (
            params.c2
            + (params.c2 / params.c0 + 1 - params.c2)
            * (d_hw / d) ** (params.c2 / params.c0 + 1)
        )
        / (1 - (d_hw / d) ** (params.c2 / params.c0 + 1))
    )

    d_h_d_d = params.c0 * h / d
    d_w_d_d = params.c1 * w / d

    psi_soil_min = float(np.min(psi_soil_by_layer[c_r > 0]))
    z_psi_soil_min = float(np.max(z_soil_mid[psi_soil_by_layer == psi_soil_min]))
    psi_soil_max = float(np.max(psi_soil_by_layer[c_r > 0]))

    psi_rc_ub_0 = psi_soil_max
    psi_rc_lb_0 = psi_soil_min - params.rho * params.g * z_psi_soil_min / 1e6
    if abs(psi_rc_lb_0 - psi_rc_ub_0) < 1:
        psi_rc_lb_0 = psi_rc_ub_0 - 1

    psi_rc_3_0 = np.array(
        [psi_rc_ub_0, 0.5 * (psi_rc_ub_0 + psi_rc_lb_0), psi_rc_lb_0],
        dtype=float,
    )
    e_3_0 = np.array([np.nan, np.nan, np.nan], dtype=float)

    while (np.sum(e_3_0 < 0) == 0) or (np.sum(e_3_0 > 0) == 0):
        for layer_idx in range(3):
            res = e_from_soil_to_root_collar(
                params=params.root_uptake,
                psi_rc=float(psi_rc_3_0[layer_idx]),
                psi_soil_by_layer=psi_soil_by_layer,
                z_soil_mid=z_soil_mid,
                dz=dz,
                la=la,
                c_r_h=c_r_h,
                c_r_v=c_r_v,
            )
            e_3_0[layer_idx] = res.e

        if np.sum(e_3_0 < 0) == 0:
            psi_rc_3_0[0] = psi_rc_3_0[0] + 0.1
        if np.sum(e_3_0 > 0) == 0:
            psi_rc_3_0[2] = psi_rc_3_0[2] - 0.1
        psi_rc_3_0[1] = 0.5 * (psi_rc_3_0[0] + psi_rc_3_0[2])

    iteration = 0
    while float(np.max(psi_rc_3_0) - np.min(psi_rc_3_0)) > 1e-3:
        iteration += 1
        if iteration > 100:
            raise RuntimeError("Stomata bisection (E=0) did not converge")
        if (np.sum(e_3_0 < 0) == 0) or (np.sum(e_3_0 > 0) == 0):
            raise RuntimeError("Invalid bisection bounds for E=0")

        e_ub_0 = float(np.max(e_3_0[e_3_0 < 0]))
        e_lb_0 = float(np.min(e_3_0[e_3_0 > 0]))

        psi_rc_ub_0 = float(np.max(psi_rc_3_0[e_3_0 == e_ub_0]))
        psi_rc_lb_0 = float(np.min(psi_rc_3_0[e_3_0 == e_lb_0]))
        psi_rc_m_0 = 0.5 * (psi_rc_ub_0 + psi_rc_lb_0)

        psi_new = np.array([psi_rc_ub_0, psi_rc_m_0, psi_rc_lb_0], dtype=float)
        if np.all(psi_new == psi_rc_3_0):
            raise RuntimeError("Stomata bisection stalled")
        psi_rc_3_0 = psi_new
        e_3_0 = np.array([e_ub_0, np.nan, e_lb_0], dtype=float)

        res_mid = e_from_soil_to_root_collar(
            params=params.root_uptake,
            psi_rc=float(psi_rc_3_0[1]),
            psi_soil_by_layer=psi_soil_by_layer,
            z_soil_mid=z_soil_mid,
            dz=dz,
            la=la,
            c_r_h=c_r_h,
            c_r_v=c_r_v,
        )
        e_3_0[1] = res_mid.e

    e_0 = float(np.min(e_3_0[e_3_0 > 0]))
    psi_rc_0 = float(np.min(psi_rc_3_0[e_3_0 == e_0]))

    psi_l_crit = -1.0
    while float(params.vc_l(psi_l_crit)) > (1 - 0.999):
        psi_l_crit -= 0.1

    psi_rc_3_crit = np.array(
        [psi_rc_0, 0.5 * (psi_l_crit + psi_rc_0), psi_l_crit],
        dtype=float,
    )
    psi_l_3_crit = np.full(3, np.nan, dtype=float)

    for layer_idx in range(3):
        psi_rc_i = float(psi_rc_3_crit[layer_idx])
        res_e = e_from_soil_to_root_collar(
            params=params.root_uptake,
            psi_rc=psi_rc_i,
            psi_soil_by_layer=psi_soil_by_layer,
            z_soil_mid=z_soil_mid,
            dz=dz,
            la=la,
            c_r_h=c_r_h,
            c_r_v=c_r_v,
        )
        e_i = res_e.e

        psi_l_i = psi_rc_i
        for _ in range(n):
            vc = float(params.vc_sw(min(0.0, psi_l_i)))
            psi_l_i = (
                psi_l_i
                - params.rho * params.g * (h / n) / 1e6
                - _safe_div((e_i * la), (n * k_sw_max * vc))
            )
        for _ in range(n):
            vc = float(params.vc_l(min(0.0, psi_l_i)))
            psi_l_i = psi_l_i - _safe_div(e_i, (n * params.k_l * vc))
        psi_l_3_crit[layer_idx] = psi_l_i

    iteration = 0
    while float(np.max(psi_rc_3_crit) - np.min(psi_rc_3_crit)) > 1e-3:
        iteration += 1
        if iteration > 100:
            raise RuntimeError("Stomata bisection (critical) did not converge")

        f_obj = psi_l_crit - psi_l_3_crit
        f_ub = float(np.max(f_obj[f_obj < 0]))
        f_lb = float(np.min(f_obj[f_obj > 0]))
        psi_rc_ub_crit = float(psi_rc_3_crit[f_obj == f_ub][0])
        psi_rc_lb_crit = float(psi_rc_3_crit[f_obj == f_lb][0])
        psi_rc_m_crit = 0.5 * (psi_rc_lb_crit + psi_rc_ub_crit)

        psi_l_ub = float(psi_l_3_crit[psi_rc_3_crit == psi_rc_ub_crit][0])
        psi_l_lb = float(psi_l_3_crit[psi_rc_3_crit == psi_rc_lb_crit][0])
        psi_rc_3_crit = np.array(
            [psi_rc_ub_crit, psi_rc_m_crit, psi_rc_lb_crit],
            dtype=float,
        )
        psi_l_3_crit = np.array([psi_l_ub, np.nan, psi_l_lb], dtype=float)

        psi_rc_i = float(psi_rc_3_crit[1])
        res_e = e_from_soil_to_root_collar(
            params=params.root_uptake,
            psi_rc=psi_rc_i,
            psi_soil_by_layer=psi_soil_by_layer,
            z_soil_mid=z_soil_mid,
            dz=dz,
            la=la,
            c_r_h=c_r_h,
            c_r_v=c_r_v,
        )
        e_i = res_e.e

        psi_l_i = psi_rc_i
        for _ in range(n):
            vc = float(params.vc_sw(min(0.0, psi_l_i)))
            psi_l_i = (
                psi_l_i
                - params.rho * params.g * (h / n) / 1e6
                - _safe_div((e_i * la), (n * k_sw_max * vc))
            )
        for _ in range(n):
            vc = float(params.vc_l(min(0.0, psi_l_i)))
            psi_l_i = psi_l_i - _safe_div(e_i, (n * params.k_l * vc))
        psi_l_3_crit[1] = psi_l_i

    psi_rc_crit = float(np.min(psi_rc_3_crit[psi_l_3_crit > -np.inf]))
    if np.isnan(psi_rc_crit):
        raise RuntimeError("Failed to determine critical psi_rc")

    psi_rc_curve = np.linspace(psi_rc_0, psi_rc_crit, 50)
    psi_s_curve = np.full_like(psi_rc_curve, np.nan, dtype=float)
    psi_l_curve = np.full_like(psi_rc_curve, np.nan, dtype=float)
    e_curve = np.full_like(psi_rc_curve, np.nan, dtype=float)
    e_soil_curve = np.full((n_soil, psi_rc_curve.size), np.nan, dtype=float)
    r_r_h_curve = np.full((n_soil, psi_rc_curve.size), np.nan, dtype=float)
    r_r_v_curve = np.full((n_soil, psi_rc_curve.size), np.nan, dtype=float)
    f_r_curve = np.full((n_soil, psi_rc_curve.size), np.nan, dtype=float)

    psi_l_i = float(psi_l_3_crit[1])
    for curve_idx, psi_rc_i in enumerate(psi_rc_curve):
        res_uptake = e_from_soil_to_root_collar(
            params=params.root_uptake,
            psi_rc=float(psi_rc_i),
            psi_soil_by_layer=psi_soil_by_layer,
            z_soil_mid=z_soil_mid,
            dz=dz,
            la=la,
            c_r_h=c_r_h,
            c_r_v=c_r_v,
        )

        e_i = float(res_uptake.e)
        e_curve[curve_idx] = e_i
        e_soil_curve[:, curve_idx] = res_uptake.e_soil
        r_r_h_curve[:, curve_idx] = res_uptake.r_r_h
        r_r_v_curve[:, curve_idx] = res_uptake.r_r_v
        f_r_curve[:, curve_idx] = res_uptake.f_r

        psi_s_i = float(psi_rc_i)
        for _ in range(n):
            vc = float(params.vc_sw(min(0.0, psi_l_i)))
            psi_s_i = (
                psi_s_i
                - params.rho * params.g * (h / n) / 1e6
                - _safe_div((e_i * la), (n * k_sw_max * vc))
            )
        psi_s_curve[curve_idx] = psi_s_i

        psi_l_i = psi_s_i
        for _ in range(n):
            vc = float(params.vc_l(min(0.0, psi_l_i)))
            psi_l_i = psi_l_i - _safe_div(e_i, (n * params.k_l * vc))
        psi_l_curve[curve_idx] = psi_l_i

    t_l_curve = np.full_like(psi_l_curve, float(t_a), dtype=float)

    satur_mf_air = -0.0043 + 0.01 * np.exp(0.0511 * t_a)
    satur_mf_leaf = -0.0043 + 0.01 * np.exp(0.0511 * t_l_curve)
    rh_use = min(rh, 0.99)
    vpd_air = (1 - rh_use) * 0.61094 * np.exp(17.625 * t_a / (t_a + 243.04))
    vpd_l = satur_mf_leaf - satur_mf_air + vpd_air
    vpd_l = np.maximum(0.0, vpd_l)

    g_w_curve = np.abs(e_curve / vpd_l)
    g_w_curve = np.where(e_curve == 0, 0.0, g_w_curve)
    g_w_curve = np.maximum(0.0, g_w_curve)
    g_c_curve = g_w_curve / 1.6

    v_cmax = params.v_cmax_func(t_l_curve)
    j_max = params.j_max_func(t_l_curve)
    j_phi = params.var_kappa * r_abs
    j = (
        j_max
        + j_phi
        - np.sqrt((j_max + j_phi) ** 2 - 4 * params.c_prime2 * j_max * j_phi)
    ) / (2 * params.c_prime2)
    gamma_star = params.gamma_star_func(t_l_curve)
    k_c = params.k_c_func(t_l_curve)
    k_o = params.k_o_func(t_l_curve)
    r_d_curve = params.r_d_func(t_l_curve)

    a_c = v_cmax
    a_j = j / 4
    b_c = k_c * (1 + params.o_a / k_o)
    b_j = 2 * gamma_star
    beta_c = (r_d_curve - a_c) - g_c_curve * (params.c_a + b_c)
    beta_j = (r_d_curve - a_j) - g_c_curve * (params.c_a + b_j)
    gamma_c = a_c * (params.c_a - gamma_star) - r_d_curve * (params.c_a + b_c)
    gamma_j = a_j * (params.c_a - gamma_star) - r_d_curve * (params.c_a + b_j)

    a_c_rate = -beta_c / 2 - np.sqrt((beta_c / 2) ** 2 - gamma_c * g_c_curve)
    a_c_rate = np.real(a_c_rate)
    a_j_rate = -beta_j / 2 - np.sqrt((beta_j / 2) ** 2 - gamma_j * g_c_curve)
    a_j_rate = np.real(a_j_rate)

    inf_mask = np.isinf(g_c_curve)
    if np.any(inf_mask):
        a_c_rate[inf_mask] = (
            a_c[inf_mask] * (params.c_a - gamma_star[inf_mask]) / (params.c_a + b_c[inf_mask])
            - r_d_curve[inf_mask]
        )
        a_j_rate[inf_mask] = (
            a_j[inf_mask] * (params.c_a - gamma_star[inf_mask]) / (params.c_a + b_j[inf_mask])
            - r_d_curve[inf_mask]
        )

    a_n_curve = (
        a_c_rate
        + a_j_rate
        - np.sqrt((a_c_rate + a_j_rate) ** 2 - 4 * params.c_prime1 * a_c_rate * a_j_rate)
    ) / (2 * params.c_prime1)

    d_a_n_d_a_c = (
        1
        - (
            a_c_rate + (1 - 2 * params.c_prime1) * a_j_rate
        )
        / np.sqrt((a_c_rate + a_j_rate) ** 2 - 4 * params.c_prime1 * a_c_rate * a_j_rate)
    ) / (2 * params.c_prime1)
    d_a_n_d_a_j = (
        1
        - (
            a_j_rate + (1 - 2 * params.c_prime1) * a_c_rate
        )
        / np.sqrt((a_c_rate + a_j_rate) ** 2 - 4 * params.c_prime1 * a_c_rate * a_j_rate)
    ) / (2 * params.c_prime1)

    var_h = (j / 4 + g_c_curve * (params.c_a + 2 * gamma_star) - r_d_curve) / 2
    d_a_j_d_j = (1 / 8) * (g_c_curve * (params.c_a - gamma_star)) / (var_h - a_j_rate)
    d_a_j_d_j = np.where(
        inf_mask,
        1 / 4 * (params.c_a - gamma_star) / (params.c_a + b_j),
        d_a_j_d_j,
    )

    d_j_d_j_phi = (
        1
        - (
            j_phi + (1 - 2 * params.c_prime2) * j_max
        )
        / np.sqrt((j_max + j_phi) ** 2 - 4 * params.c_prime2 * j_max * j_phi)
    ) / (2 * params.c_prime2)
    d_a_n_d_r_abs_curve = d_a_n_d_a_j * d_a_j_d_j * d_j_d_j_phi * params.var_kappa

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        c_i = params.c_a - a_n_curve / g_c_curve
        d_a_c_d_c_i = a_c * (gamma_star + b_c) / (c_i + b_c) ** 2
        d_a_j_d_c_i = a_j * (gamma_star + b_j) / (c_i + b_j) ** 2
        x_var = d_a_n_d_a_c * d_a_c_d_c_i + d_a_n_d_a_j * d_a_j_d_c_i
        lambda_wue_curve = a_n_curve / e_curve * x_var / (x_var + g_c_curve)

        f_sw = (
            la
            * e_curve
            / (psi_rc_curve - psi_s_curve - params.rho * params.g * h / 1e6)
            / k_sw_max
        )
        f_sw[0] = float(
            np.mean(
                np.minimum(
                    1.0,
                    params.vc_sw(
                        np.linspace(float(psi_rc_curve[0]), float(psi_s_curve[0]), 10)
                    ),
                )
            )
        )
        f_l = e_curve / (psi_s_curve - psi_l_curve) / params.k_l
        f_l[0] = float(min(1.0, params.vc_l(min(0.0, float(psi_s_curve[0])))))

    d_p = 1e-2
    d_vc_r_d_psi_rc = (
        params.vc_r(np.minimum(0.0, psi_rc_curve + d_p))
        - params.vc_r(np.minimum(0.0, psi_rc_curve))
    ) / d_p
    d_vc_r_d_psi_soil = (
        params.vc_r(np.minimum(0.0, psi_soil_by_layer + d_p))
        - params.vc_r(np.minimum(0.0, psi_soil_by_layer))
    ) / d_p
    d_vc_r_d_psi_soil = np.repeat(d_vc_r_d_psi_soil[:, None], psi_rc_curve.size, axis=1)
    d2_vc_r_d_psi_soil2 = (
        params.vc_r(np.minimum(0.0, psi_soil_by_layer + d_p))
        + params.vc_r(np.minimum(0.0, psi_soil_by_layer - d_p))
        - 2 * params.vc_r(np.minimum(0.0, psi_soil_by_layer))
    ) / d_p**2
    d2_vc_r_d_psi_soil2 = np.repeat(
        d2_vc_r_d_psi_soil2[:, None],
        psi_rc_curve.size,
        axis=1,
    )

    df_r_d_psi_rc = (
        f_r_curve - params.vc_r(np.minimum(0.0, psi_rc_curve))
    ) / (psi_soil_by_layer[:, None] - psi_rc_curve[None, :])
    close_mask = np.abs(psi_rc_curve[None, :] - psi_soil_by_layer[:, None]) < 1e-2
    df_r_d_psi_rc = np.where(close_mask, 0.5 * d_vc_r_d_psi_soil, df_r_d_psi_rc)

    d2f_r_d_psi_rc2 = (2 * df_r_d_psi_rc - d_vc_r_d_psi_rc[None, :]) / (
        psi_soil_by_layer[:, None] - psi_rc_curve[None, :]
    )
    close_mask2 = np.abs(psi_rc_curve[None, :] - psi_soil_by_layer[:, None]) < 1e-1
    d2f_r_d_psi_rc2 = np.where(
        close_mask2,
        (1 / 3) * d2_vc_r_d_psi_soil2,
        d2f_r_d_psi_rc2,
    )

    df_sw_d_psi_s = (f_sw - params.vc_sw(np.minimum(0.0, psi_s_curve))) / (
        psi_rc_curve - psi_s_curve
    )
    df_sw_d_psi_rc = (params.vc_sw(np.minimum(0.0, psi_rc_curve)) - f_sw) / (
        psi_rc_curve - psi_s_curve
    )

    r_r_v_sum = np.cumsum(r_r_v_curve, axis=0)
    r_r = r_r_h_curve + r_r_v_sum

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        a_var = 1 - la * e_curve / (f_sw**2) / k_sw_max * df_sw_d_psi_s
        b_var = 1 + la * e_curve / (f_sw**2) / k_sw_max * df_sw_d_psi_rc
        c_var = np.sum(
            (1 / la - e_soil_curve * r_r_h_curve / f_r_curve * df_r_d_psi_rc) / r_r,
            axis=0,
        )
        d_var = params.vc_l(np.minimum(0.0, psi_s_curve)) / f_l
        e_var = params.vc_l(np.minimum(0.0, psi_l_curve)) / f_l

        k_canopy_curve = e_var / (
            1 / f_l / params.k_l
            + d_var / a_var * (b_var / c_var + la / f_sw / k_sw_max)
        )

    c0_var = float(c_var[0])
    idx0 = int(np.argmin(np.abs(c_var - c0_var)))
    psi_rc0 = float(psi_rc_curve[idx0])
    f_sw0 = float(f_sw[idx0])
    f_r0 = f_r_curve[:, idx0]
    df_r0_d_psi_rc0 = df_r_d_psi_rc[:, idx0]
    d2f_r0_d_psi_rc0 = d2f_r_d_psi_rc2[:, idx0]

    psi_l0 = psi_rc0 - params.rho * params.g * h / 1e6
    f_l0 = float(params.vc_l(min(0.0, psi_l0)))

    e_soil0 = e_soil_curve[:, idx0]
    r_r0 = r_r[:, idx0]
    r_r_h0 = r_r_h_curve[:, idx0]
    r_r_v0 = r_r_v_curve[:, idx0]

    d_psi_rc0_d_c_r_h = 1 / c0_var / c_r_h * e_soil0 * r_r_h0 / r_r0
    d_psi_rc0_d_c_r_v = (
        1 / c0_var / c_r_v * _reverse_cumsum(e_soil0 * r_r_v0 / r_r0, axis=0)
    )

    k_canopy_max = 1 / (
        1 / params.k_l / f_l0 + 1 / c0_var + la / f_sw0 / k_sw_max
    )
    if k_canopy_max < 0:
        raise RuntimeError("Negative k_cmax")

    df_l0_d_psi_rc0 = (
        params.vc_l(min(0.0, psi_l0 + d_p)) - params.vc_l(min(0.0, psi_l0))
    ) / d_p
    df_l0_d_h = -params.rho * params.g / 1e6 * float(df_l0_d_psi_rc0)
    df_sw0_d_psi_rc0 = (
        params.vc_sw(min(0.0, psi_rc0)) - params.vc_sw(min(0.0, psi_l0))
    ) / (params.rho * params.g * h / 1e6)
    df_sw0_d_h = (params.vc_sw(min(0.0, psi_l0)) - f_sw0) / h

    dk_canopy_max_d_d = k_canopy_max**2 * (
        (
            df_l0_d_h / params.k_l / (f_l0**2)
            + la * df_sw0_d_h / k_sw_max / (f_sw0**2)
        )
        * d_h_d_d
        + la / (k_sw_max**2) / f_sw0 * dk_sw_max_d_d
    )
    dk_canopy_max_d_la = k_canopy_max**2 * (
        1 / k_sw_max / f_sw0 - 1 / (c0_var**2 * la**2) * float(np.sum(1 / r_r0))
    )

    dk_canopy_max_d_c_r_h = k_canopy_max**2 * (
        (
            df_l0_d_psi_rc0 / params.k_l / (f_l0**2)
            + la * df_sw0_d_psi_rc0 / k_sw_max / (f_sw0**2)
            + 1
            / (c0_var**2)
            * float(
                np.sum(
                    (
                        (
                            2
                            * e_soil0
                            / f_r0**2
                            * r_r_h0
                            / r_r0
                            * df_r0_d_psi_rc0
                        )
                        + (
                            r_r_h0
                            / f_r0
                            / r_r0**2
                            * (
                                1 / la
                                - e_soil0 * r_r_h0 / f_r0 * df_r0_d_psi_rc0
                            )
                        )
                    )
                    * df_r0_d_psi_rc0
                    - e_soil0
                    / f_r0
                    * r_r_h0
                    / r_r0
                    * d2f_r0_d_psi_rc0
                )
            )
        )
        * d_psi_rc0_d_c_r_h
        + 1
        / (c0_var**2)
        / c_r_h
        * (
            r_r_h0
            / (r_r0**2)
            * (
                e_soil0 * (r_r0 - r_r_h0) * df_r0_d_psi_rc0 / f_r0 + 1 / la
            )
        )
    )

    dk_canopy_max_d_c_r_v = k_canopy_max**2 * (
        (
            df_l0_d_psi_rc0 / params.k_l / (f_l0**2)
            + la * df_sw0_d_psi_rc0 / k_sw_max / (f_sw0**2)
            + 1
            / (c0_var**2)
            * float(
                np.sum(
                    (
                        (
                            2
                            * e_soil0
                            / f_r0**2
                            * r_r_h0
                            / r_r0
                            * df_r0_d_psi_rc0
                        )
                        + (
                            r_r_h0
                            / f_r0
                            / r_r0**2
                            * (
                                1 / la
                                - e_soil0 * r_r_h0 / f_r0 * df_r0_d_psi_rc0
                            )
                        )
                    )
                    * df_r0_d_psi_rc0
                    - e_soil0
                    / f_r0
                    * r_r_h0
                    / r_r0
                    * d2f_r0_d_psi_rc0
                )
            )
        )
        * d_psi_rc0_d_c_r_v
        + 1
        / (c0_var**2)
        / c_r_v
        * _reverse_cumsum(
            r_r_v0
            / (r_r0**2)
            * (-e_soil0 * r_r_h0 * df_r0_d_psi_rc0 / f_r0 + 1 / la),
            axis=0,
        )
    )

    psi_lcrit = float(np.min(psi_l_curve[psi_l_curve > -np.inf]))
    a_n_max = float(a_n_curve[psi_l_curve == psi_lcrit][0])
    e_max = float(e_curve[psi_l_curve == psi_lcrit][0])
    lambda_wue_crit = float(lambda_wue_curve[psi_l_curve == psi_lcrit][0])
    d_a_n_d_r_abs_crit = float(d_a_n_d_r_abs_curve[psi_l_curve == psi_lcrit][0])

    if a_n_max > 0:
        f_obj = a_n_curve / a_n_max + k_canopy_curve / k_canopy_max
        with np.errstate(invalid="ignore", divide="ignore"):
            d_f_d_psi_l = np.diff(f_obj) / np.diff(psi_l_curve)
        idx = 0
        while True:
            idx += 1
            if idx >= d_f_d_psi_l.size:
                raise RuntimeError("Failed to find stomatal optimum")
            if d_f_d_psi_l[idx] >= 0 and g_w_curve[idx] >= params.g_wmin:
                break
    else:
        idx = int(np.argmin(np.abs(g_w_curve - params.g_wmin)))

    psi_l = float(psi_l_curve[idx])
    psi_s = float(psi_s_curve[idx])
    psi_rc = float(psi_rc_curve[idx])
    a_n = float(a_n_curve[idx])
    e = float(e_curve[idx])
    g_w = float(g_w_curve[idx])
    e_soil = e_soil_curve[:, idx]
    k_canopy = float(k_canopy_curve[idx])
    lambda_wue = float(lambda_wue_curve[idx])
    d_a_n_d_r_abs = float(d_a_n_d_r_abs_curve[idx])
    t_l = float(t_l_curve[idx])
    r_d = float(r_d_curve[idx])
    f_sw_opt = float(f_sw[idx])
    f_l_opt = float(f_l[idx])
    a_opt = float(a_var[idx])
    b_opt = float(b_var[idx])
    c_opt = float(c_var[idx])
    d_opt = float(d_var[idx])
    e_opt = float(e_var[idx])
    r_r_opt = r_r[:, idx]
    r_r_h_opt = r_r_h_curve[:, idx]
    r_r_v_opt = r_r_v_curve[:, idx]

    if lambda_wue < 0:
        lambda_wue = 0.0

    g_var = (
        lambda_wue_crit
        * k_canopy_max
        * a_n
        / (a_n_max**2)
        * (psi_l0 - psi_l)
        / (
            1
            + lambda_wue_crit
            * k_canopy_max
            * a_n
            / (a_n_max**2)
            * (psi_l - psi_lcrit)
        )
    )
    h_var = (
        k_canopy_max / k_canopy * a_n / a_n_max
        - g_var * (1 + k_canopy_max / k_canopy * (1 - a_n / a_n_max))
    )
    i_var = e / k_canopy_max + a_n / a_n_max * (psi_l0 - psi_l) - g_var * (
        (e_max - e) / k_canopy_max + a_n / a_n_max * (psi_l - psi_lcrit)
    )

    denom = (
        1
        / d_opt
        * (
            1 / f_l_opt / params.k_l
            + e_opt / k_canopy * (1 + g_var) / (h_var - 1)
        )
        + 1 / a_opt * (b_opt / c_opt + la / f_sw_opt / k_sw_max)
    )

    d_e_d_d = (
        (
            -(1 / a_opt + e_opt / d_opt * k_canopy_max / k_canopy / (h_var - 1))
            * params.rho
            * params.g
            / 1e6
            * d_h_d_d
            + e_opt
            / d_opt
            / (h_var - 1)
            / k_canopy
            * (
                i_var * dk_canopy_max_d_d
                - g_var
                * d_a_n_d_r_abs_crit
                / lambda_wue_crit
                * (d_r_abs_d_h * d_h_d_d + d_r_abs_d_w * d_w_d_d)
            )
            + 1 / a_opt * la * e / f_sw_opt / (k_sw_max**2) * dk_sw_max_d_d
        )
        / denom
    )

    d_e_d_la = (
        (
            -e / a_opt * (b_opt / la / c_opt + 1 / f_sw_opt / k_sw_max)
            + e_opt
            / d_opt
            / (h_var - 1)
            / k_canopy
            * (
                i_var * dk_canopy_max_d_la
                - g_var * d_a_n_d_r_abs_crit / lambda_wue_crit * d_r_abs_d_la
            )
        )
        / denom
    )

    d_e_d_c_r_h = (
        (
            e_opt
            / d_opt
            / (h_var - 1)
            / k_canopy
            * (
                i_var * dk_canopy_max_d_c_r_h + k_canopy_max * d_psi_rc0_d_c_r_h
            )
            + b_opt / a_opt / c_opt / c_r_h * e_soil * r_r_h_opt / r_r_opt
        )
        / denom
    )
    d_e_d_c_r_h = np.where(psi_soil_by_layer >= 0, 0.0, d_e_d_c_r_h)

    d_e_d_c_r_v = (
        (
            e_opt
            / d_opt
            / (h_var - 1)
            / k_canopy
            * (
                i_var * dk_canopy_max_d_c_r_v + k_canopy_max * d_psi_rc0_d_c_r_v
            )
            + b_opt
            / a_opt
            / c_opt
            / c_r_v
            * _reverse_cumsum(e_soil * r_r_v_opt / r_r_opt, axis=0)
        )
        / denom
    )
    d_e_d_c_r_v = np.where(psi_soil_by_layer >= 0, 0.0, d_e_d_c_r_v)

    return StomataResult(
        psi_l=psi_l,
        psi_s=psi_s,
        psi_rc=psi_rc,
        psi_rc0=psi_rc0,
        e=e,
        e_soil=e_soil.astype(float),
        a_n=a_n,
        r_d=r_d,
        t_l=t_l,
        g_w=g_w,
        lambda_wue=lambda_wue,
        d_a_n_d_r_abs=d_a_n_d_r_abs,
        d_e_d_la=float(d_e_d_la),
        d_e_d_d=float(d_e_d_d),
        d_e_d_c_r_h=d_e_d_c_r_h.astype(float),
        d_e_d_c_r_v=d_e_d_c_r_v.astype(float),
    )
