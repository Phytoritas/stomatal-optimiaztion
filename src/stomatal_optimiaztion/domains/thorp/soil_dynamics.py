from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from stomatal_optimiaztion.domains.thorp.implements import implements
from stomatal_optimiaztion.domains.thorp.soil_hydraulics import SoilHydraulics
from stomatal_optimiaztion.domains.thorp.soil_initialization import (
    BottomBoundaryCondition,
    SoilGrid,
)


@dataclass(frozen=True, slots=True)
class RichardsEquationParams:
    dt: float
    rho: float
    g: float
    bc_bttm: BottomBoundaryCondition
    z_wt: float
    p_bttm: float
    soil: SoilHydraulics


@implements(
    "E_S2_1",
    "E_S2_10",
    "E_S2_13",
    "E_S2_14",
    "E_S2_15",
    "E_S2_16",
    "E_S2_17",
    "E_S2_18",
    "E_S2_19",
    "E_S2_20",
    "E_S2_21",
    "E_S2_22",
    "E_S2_23",
    "E_S2_24",
    "E_S2_25",
    "E_S2_26",
)
def richards_equation(
    *,
    params: RichardsEquationParams,
    grid: SoilGrid,
    q_top: float,
    f: NDArray[np.floating],
    psi_soil_by_layer: NDArray[np.floating],
) -> tuple[NDArray[np.floating], float]:
    dz = grid.dz
    dz_c = grid.dz_c
    z_mid = grid.z_mid
    z_bttm = grid.z_bttm
    n_soil_true = grid.n_soil
    z_mid_true = z_mid

    bc_bttm = params.bc_bttm
    psi_bttm = float(params.p_bttm)
    z_wt = float(params.z_wt)

    if bc_bttm == "GroundwaterTable":
        idx = int(np.argmin(np.abs(z_bttm - z_wt)))
        n_soil = idx + 1

        dz = dz[:n_soil]
        dz_c = dz_c[: n_soil + 1]
        z_mid = z_mid[:n_soil]
        z_bttm = z_bttm[:n_soil]
        f = f[:n_soil]
        psi_soil_by_layer = psi_soil_by_layer[:n_soil]

        psi_bttm = params.rho * params.g * (float(z_bttm[n_soil - 1]) - z_wt) / 1e6
        bc_bttm = "ConstantPressure"

    dhd_p = 1e6 / params.rho / params.g

    k_soil = params.soil.k_soil(psi_soil_by_layer, z_mid)
    k_soil_sat = params.soil.k_soil_sat(z_mid)
    k_soil = np.where(psi_soil_by_layer > 0, k_soil_sat, k_soil)

    # Match legacy THORP behavior when intermediate arrays contain inf values.
    with np.errstate(invalid="ignore", divide="ignore"):
        d_k_soil_dz = np.concatenate([-(np.diff(k_soil) / dz_c[1:-1]), np.array([0.0])])
        d_k_soil_sat_dz = np.concatenate([-(np.diff(k_soil_sat) / dz_c[1:-1]), np.array([0.0])])

    d_p = 1e-3
    d_k_d_p = (k_soil - params.soil.k_soil(psi_soil_by_layer - d_p, z_mid)) / d_p
    d_k_d_p = np.where(psi_soil_by_layer > 0, 0.0, d_k_d_p)

    d_vwc_d_p = (params.soil.vwc(psi_soil_by_layer, z_mid) - params.soil.vwc(psi_soil_by_layer - d_p, z_mid)) / d_p
    d_vwc_d_p = np.where(psi_soil_by_layer > 0, 0.0, d_vwc_d_p)

    a = 1 / dz_c[:-1] * (dhd_p * (k_soil / dz + d_k_soil_dz) + d_k_d_p)
    c = dhd_p * k_soil / dz / dz_c[1:]
    b = -a - c - d_vwc_d_p / params.dt
    d = -f - d_vwc_d_p * psi_soil_by_layer / params.dt - k_soil / k_soil_sat * d_k_soil_sat_dz

    a[0] = 0.0
    c[0] = dhd_p * k_soil[0] / dz_c[0] / dz_c[1]
    b[0] = -c[0] - d_vwc_d_p[0] / params.dt
    d[0] = d[0] + (q_top + k_soil[0]) / dz_c[0]

    q_bttm = float("nan")
    if bc_bttm == "ConstantPressure":
        d[-1] = d[-1] - c[-1] * psi_bttm
        c[-1] = 0.0
    elif bc_bttm == "FreeDrainage":
        q_bttm_bc = -float(k_soil[-1])
        d[-1] = d[-1] - (q_bttm_bc + k_soil[-1]) / dz_c[-1]
        a[-1] = 1 / dz_c[-2] * dhd_p * k_soil[-1] / dz[-1]
        b[-1] = -a[-1] - d_vwc_d_p[-1] / params.dt
        c[-1] = 0.0
    else:
        raise ValueError("Bottom boundary condition not correctly specified")

    matrix = np.diag(b) + np.diag(a[1:], k=-1) + np.diag(c[:-1], k=1)
    psi_new = np.linalg.solve(matrix, d)
    if np.any(np.isnan(psi_new)):
        raise RuntimeError("Richards equation not converging to a solution")

    with np.errstate(invalid="ignore", divide="ignore"):
        d_p_dz = np.concatenate(
            [-(np.diff(psi_new) / dz_c[1:-1]), np.array([(psi_new[-1] - psi_bttm) / dz_c[-1]])]
        )
    q = -k_soil * (dhd_p * d_p_dz + 1)
    q_bttm = float(q[-1])

    if n_soil_true > psi_new.size:
        extra = params.rho * params.g * (z_mid_true[psi_new.size:n_soil_true] - z_wt) / 1e6
        psi_new = np.concatenate([psi_new, extra])
        q_bttm = -float(params.soil.k_soil_sat(np.array([z_mid_true[n_soil_true - 1]]))[0])

    return psi_new.astype(float), q_bttm
