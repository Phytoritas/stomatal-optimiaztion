from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from stomatal_optimiaztion.domains.thorp.implements import implements
from stomatal_optimiaztion.domains.thorp.vulnerability import WeibullVC


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
    n = 20

    c_r = c_r_h + c_r_v
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

    for layer_idx in range(psi_soil_by_layer.size):
        if c_r[layer_idx] > 0:
            psi_soil_i = float(psi_soil_by_layer[layer_idx])
            z_soil_i = float(z_soil_mid[layer_idx])
            psi_src_min = float(min(psi_soil_i, psi_rc))
            psi_src_max = float(max(psi_soil_i, psi_rc))

            if psi_rc == psi_soil_i:
                f_ri = float(params.vc_r(psi_src_min))
                if psi_src_min > 0:
                    f_ri = float(params.vc_r(0.0))
                r_r_h = _safe_div(float(r_r_h_min[layer_idx]), f_ri)
                r_r = r_r_h + float(r_r_v_sum[layer_idx])
                e_i = -(params.rho * params.g * z_soil_i / 1e6) / r_r / la
            elif (psi_soil_i - psi_rc) == (params.rho * params.g * z_soil_i / 1e6):
                e_i = 0.0
                f_ri = float(params.vc_r(psi_src_min if psi_src_min <= 0 else 0.0))
            else:
                psi_src = np.linspace(psi_src_min, psi_src_max, n)
                f_vals = np.asarray(params.vc_r(psi_src), dtype=float)
                f_vals = np.where(psi_src > 0, float(params.vc_r(0.0)), f_vals)
                f_ri = float(np.sum(f_vals) / n)
                r_r_h = _safe_div(float(r_r_h_min[layer_idx]), f_ri)
                r_r = r_r_h + float(r_r_v_sum[layer_idx])
                e_i = (psi_soil_i - psi_rc - params.rho * params.g * z_soil_i / 1e6) / r_r / la

            e_soil[layer_idx] = e_i
            f_r[layer_idx] = f_ri
        else:
            e_soil[layer_idx] = 0.0
            f_r[layer_idx] = float(params.vc_r(float(psi_soil_by_layer[layer_idx])))

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
