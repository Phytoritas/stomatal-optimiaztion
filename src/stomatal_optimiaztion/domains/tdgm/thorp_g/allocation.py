from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from stomatal_optimiaztion.domains.tdgm.coupling import (
    initial_mean_allocation_fractions,
    update_mean_allocation_fractions,
)
from stomatal_optimiaztion.domains.tdgm.thorp_g.config import ThorpGParams

__all__ = [
    "AllocationFractions",
    "allocation_fractions",
    "initial_mean_allocation_fractions",
    "update_mean_allocation_fractions",
]


@dataclass(frozen=True, slots=True)
class AllocationFractions:
    u_l: float
    u_r_h: NDArray[np.floating]
    u_r_v: NDArray[np.floating]
    u_sw: float


def allocation_fractions(
    *,
    params: ThorpGParams,
    a_n: float,
    lambda_wue: float,
    d_a_n_d_r_abs: float,
    d_e_d_la: float,
    d_e_d_d: float,
    d_e_d_c_r_h: NDArray[np.floating],
    d_e_d_c_r_v: NDArray[np.floating],
    d_r_abs_d_h: float,
    d_r_abs_d_w: float,
    d_r_abs_d_la: float,
    h: float,
    w: float,
    d: float,
    c_w: float,
    c_l: float,
    c0: float,
    c1: float,
    t_a: float,
    t_soil: float,
) -> AllocationFractions:
    """Optimal allocation fractions (shared with THORP baseline)."""

    if c_l == 0:
        return AllocationFractions(
            u_l=1.0,
            u_r_h=np.zeros_like(d_e_d_c_r_h, dtype=float),
            u_r_v=np.zeros_like(d_e_d_c_r_v, dtype=float),
            u_sw=0.0,
        )

    la = c_l * params.sla

    d_h_d_d = c0 * h / d
    d_w_d_d = c1 * w / d
    d_d_d_c_w = d / c_w / (2 + c0)

    r_m_sw = float(params.r_m_sw_func(t_a))
    r_m_r = float(params.r_m_r_func(t_soil))

    d_gain_d_c_l = params.sla * (a_n + la * (lambda_wue * d_e_d_la + d_a_n_d_r_abs * d_r_abs_d_la))
    d_gain_d_c_l = float(max(0.0, d_gain_d_c_l))

    d_gain_d_c_r_h = la * lambda_wue * d_e_d_c_r_h - r_m_r
    d_gain_d_c_r_h = np.maximum(0.0, d_gain_d_c_r_h)

    d_gain_d_c_r_v = la * lambda_wue * d_e_d_c_r_v - r_m_r
    d_gain_d_c_r_v = np.maximum(0.0, d_gain_d_c_r_v)

    d_gain_d_c_sw = (
        la
        * (lambda_wue * d_e_d_d + (d_r_abs_d_h * d_h_d_d + d_r_abs_d_w * d_w_d_d) * d_a_n_d_r_abs)
        * d_d_d_c_w
        - r_m_sw
    )
    d_gain_d_c_sw = float(max(0.0, d_gain_d_c_sw))

    d_cost_d_c_l = 1.0 / params.tau_l
    d_cost_d_c_r = 1.0 / params.tau_r
    d_cost_d_c_sw = 1.0 / params.tau_sw

    u_l_raw = d_gain_d_c_l / d_cost_d_c_l
    u_r_h_raw = d_gain_d_c_r_h / d_cost_d_c_r
    u_r_v_raw = d_gain_d_c_r_v / d_cost_d_c_r
    u_sw_raw = d_gain_d_c_sw / d_cost_d_c_sw

    sum_u = float(u_l_raw + u_sw_raw + np.sum(u_r_h_raw + u_r_v_raw))
    if sum_u > 0:
        return AllocationFractions(
            u_l=float(u_l_raw / sum_u),
            u_r_h=(u_r_h_raw / sum_u).astype(float),
            u_r_v=(u_r_v_raw / sum_u).astype(float),
            u_sw=float(u_sw_raw / sum_u),
        )
    if sum_u == 0:
        return AllocationFractions(
            u_l=float("nan"),
            u_r_h=np.full_like(d_e_d_c_r_h, np.nan, dtype=float),
            u_r_v=np.full_like(d_e_d_c_r_v, np.nan, dtype=float),
            u_sw=float("nan"),
        )
    raise RuntimeError("Unexpected allocation sum")
