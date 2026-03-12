from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from stomatal_optimiaztion.domains.thorp.allocation import AllocationParams
from stomatal_optimiaztion.domains.thorp.implements import implements


@dataclass(frozen=True, slots=True)
class GrowthParams:
    allocation: AllocationParams
    dt: float
    f_c: float
    rho_cw: float
    xi: float
    b0: float
    d_ref: float
    c0: float
    b1: float
    c1: float

    @property
    def sla(self) -> float:
        return self.allocation.sla

    @property
    def tau_l(self) -> float:
        return self.allocation.tau_l

    @property
    def tau_r(self) -> float:
        return self.allocation.tau_r

    @property
    def tau_sw(self) -> float:
        return self.allocation.tau_sw

    def r_m_sw(self, t_a: float) -> float:
        return float(self.allocation.r_m_sw_func(t_a))

    def r_m_r(self, t_soil: float) -> float:
        return float(self.allocation.r_m_r_func(t_soil))


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


@implements(
    "E_S7_1",
    "E_S7_2",
    "E_S7_3",
    "E_S7_4",
    "E_S7_5",
    "E_S9_1",
    "E_S9_2",
    "E_S9_3",
    "E_S9_4",
    "E_S9_5",
    "E_S9_6",
    "E_S9_7",
    "E_S9_8",
    "E_S9_9",
)
def grow(
    *,
    params: GrowthParams,
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
) -> GrowthState:
    s_l = c_l / params.tau_l
    s_r_h = c_r_h / params.tau_r
    s_r_v = c_r_v / params.tau_r
    s_sw = c_sw / params.tau_sw

    la = params.sla * c_l
    c_r = c_r_h + c_r_v

    r_m = la * r_d + float(np.sum(c_r)) * params.r_m_r(t_soil) + c_sw * params.r_m_sw(t_a)
    a_g = a_n + r_d

    u = 1e-7 * c_nsc
    u_mod_t = 1.0 / (1.0 + np.exp(-0.185 * (t_a - 18.4)))
    if t_a < 0:
        u_mod_t = 0.0
    u = float(u * u_mod_t)

    nan_count = int(np.sum(np.isnan(np.concatenate([[u_l, u_sw], (u_r_h + u_r_v)]))))
    if nan_count == (u_r_h.size + 2):
        u = 0.0
        u_l = 0.0
        u_r_h = np.zeros_like(u_r_h, dtype=float)
        u_r_v = np.zeros_like(u_r_v, dtype=float)
        u_sw = 0.0
    elif nan_count > 0:
        raise RuntimeError("Invalid allocation fractions (partial NaNs)")

    g_rate = u * (1 - params.f_c)

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
    if np.any(np.isnan(np.concatenate([[c_l, c_sw, c_nsc], c_r_h]))):
        raise RuntimeError("NaNs in growth state")

    c_w = c_sw + c_hw
    d = float(
        (
            c_w
            / (params.rho_cw * params.xi * params.b0 * (params.d_ref ** (-params.c0)))
        )
        ** (1 / (2 + params.c0))
    )
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
