from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from stomatal_optimiaztion.domains.tdgm.thorp_g.config import (
    BottomBoundaryCondition,
    ThorpGParams,
)


@dataclass(frozen=True, slots=True)
class SoilGrid:
    dz: NDArray[np.floating]
    z_bttm: NDArray[np.floating]
    z_mid: NDArray[np.floating]
    dz_c: NDArray[np.floating]

    @property
    def n_soil(self) -> int:
        return int(self.z_mid.size)


@dataclass(frozen=True, slots=True)
class InitialSoilAndRoots:
    grid: SoilGrid
    psi_soil_by_layer: NDArray[np.floating]
    vwc: NDArray[np.floating]
    c_r_h: NDArray[np.floating]
    c_r_v: NDArray[np.floating]


def initial_soil_and_roots(
    *,
    params: ThorpGParams,
    c_r_i: float,
    z_i: float,
) -> InitialSoilAndRoots:
    z_wt = float(params.z_wt)
    z_soil = float(params.z_soil)
    n_soil = int(params.n_soil)

    dz_top = 0.1
    if n_soil == 1:
        dz_top = z_soil
    dz_top = dz_top if dz_top <= z_soil else z_soil * 0.1 / 30.0

    if (z_soil / dz_top) < 1:
        raise ValueError("Cannot discretize soil column")

    if n_soil > 1:
        r_min = 1.0
        r_max = (z_soil / dz_top) ** (1 / (n_soil - 1))

        err = float("inf")
        it = 0
        while err > 1e-4:
            it += 1
            if it > 100:
                raise RuntimeError("Soil column discretization not converging")

            r_half = 0.5 * (r_min + r_max)
            r = np.array([r_min, r_half, r_max], dtype=float)
            exponents = np.arange(1, n_soil, dtype=float)[:, None]
            check_0 = np.sum(r[None, :] ** exponents, axis=0) - z_soil / dz_top
            err = float(np.abs(check_0[1]))

            lt = r[check_0 < 0]
            gt = r[check_0 > 0]
            if lt.size == 0 or gt.size == 0:
                raise RuntimeError("Soil column discretization not converging")

            r_min = float(np.max(lt))
            r_max = float(np.min(gt))

        r = 0.5 * (r_min + r_max)
        dz = r ** np.arange(0, n_soil, dtype=float)
        dz = dz * z_soil / float(np.sum(dz))
        z_bttm = np.cumsum(dz)
        z_bttm[-1] = z_soil
        n_soil_true = n_soil

        if params.bc_bttm == "GroundwaterTable":
            while z_bttm[-1] < z_wt:
                n_soil += 1
                dz = r ** np.arange(0, n_soil, dtype=float)
                dz = dz * z_soil / float(np.sum(dz[:n_soil_true]))
                z_bttm = np.cumsum(dz)
                z_bttm[n_soil_true - 1] = z_soil

    elif n_soil == 1:
        dz = np.array([max(z_soil, z_wt)], dtype=float)
        z_bttm = dz.copy()
    else:
        raise ValueError("Invalid n_soil")

    z_top = np.concatenate([np.array([0.0]), z_bttm[:-1]])
    z_mid = (z_bttm + z_top) / 2.0

    dz_c = 0.5 * (dz[:-1] + dz[1:])
    dz_c = np.concatenate([np.array([dz[0] / 2.0]), dz_c, np.array([dz[-1] / 2.0])])

    grid = SoilGrid(dz=dz.astype(float), z_bttm=z_bttm.astype(float), z_mid=z_mid.astype(float), dz_c=dz_c)

    m_max = 0.995
    if z_i <= 0:
        raise ValueError("Initial rooting depth z_i must be > 0")
    b = (1 - m_max) ** (1 / z_i)
    root_biomass_fract = (b**z_top) - (b**z_bttm)
    c_r = c_r_i * root_biomass_fract

    psi_soil_by_layer = params.rho * params.g * (z_mid - z_wt) / 1e6
    vwc = params.soil.vwc(psi_soil_by_layer, z_mid)

    c_r_h = np.full_like(c_r, np.nan, dtype=float)
    c_r_v = np.full_like(c_r, np.nan, dtype=float)

    for i in range(grid.n_soil):
        vc_r_i = float(params.vc_r(min(0.0, float(psi_soil_by_layer[i]))))
        if i == 0:
            x = params.beta_r_h / params.beta_r_v / (float(dz[i]) ** 2) / vc_r_i
            c_r_v[i] = c_r[i] / (1 + x)
            c_r_h[i] = c_r[i] - c_r_v[i]
        else:
            aq = params.beta_r_v * float(np.sum(dz[:i] ** 2 / c_r_v[:i]))
            bq = -aq * c_r[i] - params.beta_r_h / vc_r_i - params.beta_r_v * float(dz[i]) ** 2
            cq = c_r[i] * params.beta_r_h / vc_r_i
            disc = float(bq**2 - 4 * aq * cq)
            c_r_h_i = (-bq - disc**0.5) / (2 * aq)
            c_r_v[i] = c_r[i] - c_r_h_i
            c_r_h[i] = c_r_h_i

    if np.any(c_r_h < 0) or np.any(c_r_v < 0):
        raise RuntimeError("Negative root carbon upon initialization")

    return InitialSoilAndRoots(
        grid=grid,
        psi_soil_by_layer=psi_soil_by_layer.astype(float),
        vwc=vwc.astype(float),
        c_r_h=c_r_h.astype(float),
        c_r_v=c_r_v.astype(float),
    )


def richards_equation(
    *,
    params: ThorpGParams,
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

    bc_bttm: BottomBoundaryCondition = params.bc_bttm
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

    # Rare intermediate arrays can contain +/-inf and trigger inf-inf warnings; suppress for MATLAB parity.
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

    mtx = np.diag(b) + np.diag(a[1:], k=-1) + np.diag(c[:-1], k=1)
    psi_new = np.linalg.solve(mtx, d)
    if np.any(np.isnan(psi_new)):
        raise RuntimeError("Richards equation not converging to a solution")

    with np.errstate(invalid="ignore", divide="ignore"):
        d_p_dz = np.concatenate([-(np.diff(psi_new) / dz_c[1:-1]), np.array([(psi_new[-1] - psi_bttm) / dz_c[-1]])])
    q = -k_soil * (dhd_p * d_p_dz + 1)
    q_bttm = float(q[-1])

    if n_soil_true > psi_new.size:
        extra = params.rho * params.g * (z_mid_true[psi_new.size : n_soil_true] - z_wt) / 1e6
        psi_new = np.concatenate([psi_new, extra])
        q_bttm = -float(params.soil.k_soil_sat(np.array([z_mid_true[n_soil_true - 1]]))[0])

    return psi_new.astype(float), q_bttm


def soil_moisture(
    *,
    params: ThorpGParams,
    grid: SoilGrid,
    psi_soil_by_layer: NDArray[np.floating],
    t_a: float,
    t_soil: float,
    rh: float,
    u10: float,
    precip: float,
    e_soil: NDArray[np.floating],
    la: float,
    w: float,
) -> tuple[NDArray[np.floating], float]:
    dz = grid.dz
    z_mid = grid.z_mid

    f = -la * e_soil * params.m_h2o / params.rho / w**2 / dz

    dhd_p = 1e6 / params.g / params.rho
    with np.errstate(over="ignore", invalid="ignore"):
        rh_soil = float(
            np.exp(dhd_p * float(psi_soil_by_layer[0]) * params.g * params.m_h2o / params.r_gas / (t_soil + 273.15))
        )
    rh_soil = min(1.0, rh_soil)

    e_vsat = 0.61094 * np.exp(17.625 * t_a / (t_a + 243.04))
    e_vsat_soil = 0.61094 * np.exp(17.625 * t_soil / (t_soil + 243.04))
    e_v = rh * e_vsat
    e_v_soil = rh_soil * e_vsat_soil
    vpd_soil = e_v_soil - e_v

    g_a = 0.147 * (u10 / 10.0) ** 0.5
    evap = g_a * vpd_soil / 101.325
    evap = params.m_h2o / params.rho * evap
    evap = max(0.0, float(evap))

    vwc_min = float(params.soil.vwc(np.array([-np.inf]), np.array([z_mid[0]]))[0]) + 0.1 * (
        float(params.soil.vwc(np.array([0.0]), np.array([z_mid[0]]))[0])
        - float(params.soil.vwc(np.array([-np.inf]), np.array([z_mid[0]]))[0])
    )
    evap_max = (
        (float(params.soil.vwc(np.array([psi_soil_by_layer[0]]), np.array([z_mid[0]]))[0]) - vwc_min) / params.dt
        - float(f[0])
    ) * float(dz[0])
    evap_max = max(0.0, 0.95 * float(evap_max))
    evap = min(evap, evap_max)

    q_top = evap
    if precip > 0:
        q_top = -precip
        evap = float("nan")

    psi_new, _ = richards_equation(
        params=params, grid=grid, q_top=float(q_top), f=f, psi_soil_by_layer=psi_soil_by_layer
    )
    return psi_new, float(evap)
