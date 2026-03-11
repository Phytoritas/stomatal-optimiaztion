from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from stomatal_optimiaztion.domains.thorp.soil_hydraulics import SoilHydraulics
from stomatal_optimiaztion.domains.thorp.vulnerability import WeibullVC

BottomBoundaryCondition = Literal["ConstantPressure", "FreeDrainage", "GroundwaterTable"]


@dataclass(frozen=True, slots=True)
class SoilInitializationParams:
    rho: float
    g: float
    z_wt: float
    z_soil: float
    n_soil: int
    bc_bttm: BottomBoundaryCondition
    soil: SoilHydraulics
    vc_r: WeibullVC
    beta_r_h: float
    beta_r_v: float


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
    params: SoilInitializationParams,
    c_r_i: float,
    z_i: float,
) -> InitialSoilAndRoots:
    z_wt = float(params.z_wt)
    z_soil = float(params.z_soil)
    n_soil = int(params.n_soil)

    dz_top = z_soil if n_soil == 1 else 0.1
    if dz_top > z_soil:
        dz_top = z_soil * 0.1 / 30.0

    if (z_soil / dz_top) < 1:
        raise ValueError("Cannot discretize soil column")

    if n_soil > 1:
        r_min = 1.0
        r_max = (z_soil / dz_top) ** (1 / (n_soil - 1))

        err = float("inf")
        iteration = 0
        while err > 1e-4:
            iteration += 1
            if iteration > 100:
                raise RuntimeError("Soil column discretization not converging")

            r_half = 0.5 * (r_min + r_max)
            ratio_grid = np.array([r_min, r_half, r_max], dtype=float)
            exponents = np.arange(1, n_soil, dtype=float)[:, None]
            closure = np.sum(ratio_grid[None, :] ** exponents, axis=0) - z_soil / dz_top
            err = float(np.abs(closure[1]))

            lt = ratio_grid[closure < 0]
            gt = ratio_grid[closure > 0]
            if lt.size == 0 or gt.size == 0:
                raise RuntimeError("Soil column discretization not converging")

            r_min = float(np.max(lt))
            r_max = float(np.min(gt))

        ratio = 0.5 * (r_min + r_max)
        dz = ratio ** np.arange(0, n_soil, dtype=float)
        dz = dz * z_soil / float(np.sum(dz))
        z_bttm = np.cumsum(dz)
        z_bttm[-1] = z_soil
        n_soil_true = n_soil

        if params.bc_bttm == "GroundwaterTable":
            while z_bttm[-1] < z_wt:
                n_soil += 1
                dz = ratio ** np.arange(0, n_soil, dtype=float)
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

    grid = SoilGrid(
        dz=dz.astype(float),
        z_bttm=z_bttm.astype(float),
        z_mid=z_mid.astype(float),
        dz_c=dz_c.astype(float),
    )

    m_max = 0.995
    if z_i <= 0:
        raise ValueError("Initial rooting depth Z_i must be > 0")
    root_decay_base = (1 - m_max) ** (1 / z_i)
    root_biomass_fraction = (root_decay_base**z_top) - (root_decay_base**z_bttm)
    c_r = c_r_i * root_biomass_fraction

    psi_soil_by_layer = params.rho * params.g * (z_mid - z_wt) / 1e6
    vwc = params.soil.vwc(psi_soil_by_layer, z_mid)

    c_r_h = np.full_like(c_r, np.nan, dtype=float)
    c_r_v = np.full_like(c_r, np.nan, dtype=float)

    for layer_idx in range(grid.n_soil):
        vc_r_i = float(params.vc_r(min(0.0, float(psi_soil_by_layer[layer_idx]))))
        if layer_idx == 0:
            split_ratio = params.beta_r_h / params.beta_r_v / (float(dz[layer_idx]) ** 2) / vc_r_i
            c_r_v[layer_idx] = c_r[layer_idx] / (1 + split_ratio)
            c_r_h[layer_idx] = c_r[layer_idx] - c_r_v[layer_idx]
        else:
            a_coef = params.beta_r_v * float(np.sum(dz[:layer_idx] ** 2 / c_r_v[:layer_idx]))
            b_coef = (
                -a_coef * c_r[layer_idx]
                - params.beta_r_h / vc_r_i
                - params.beta_r_v * float(dz[layer_idx]) ** 2
            )
            c_coef = c_r[layer_idx] * params.beta_r_h / vc_r_i
            discriminant = float(b_coef**2 - 4 * a_coef * c_coef)
            c_r_h_i = -(b_coef + np.sqrt(discriminant)) / (2 * a_coef)
            c_r_h_i = max(float(c_r_h_i), 1e-4 * float(c_r[layer_idx]))
            c_r_h[layer_idx] = c_r_h_i
            c_r_v[layer_idx] = c_r[layer_idx] - c_r_h[layer_idx]

    if np.any(c_r_h < 0) or np.any(c_r_v < 0):
        raise RuntimeError("Negative root carbon upon initialization")

    return InitialSoilAndRoots(
        grid=grid,
        psi_soil_by_layer=psi_soil_by_layer.astype(float),
        vwc=vwc.astype(float),
        c_r_h=c_r_h.astype(float),
        c_r_v=c_r_v.astype(float),
    )
