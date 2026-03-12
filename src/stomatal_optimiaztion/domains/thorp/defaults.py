from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from stomatal_optimiaztion.domains.thorp.allocation import AllocationParams
from stomatal_optimiaztion.domains.thorp.growth import GrowthParams
from stomatal_optimiaztion.domains.thorp.hydraulics import RootUptakeParams, StomataParams
from stomatal_optimiaztion.domains.thorp.metrics import HuberValueParams
from stomatal_optimiaztion.domains.thorp.soil_dynamics import (
    RichardsEquationParams,
    SoilMoistureParams,
)
from stomatal_optimiaztion.domains.thorp.soil_hydraulics import SoilHydraulics
from stomatal_optimiaztion.domains.thorp.soil_initialization import SoilInitializationParams
from stomatal_optimiaztion.domains.thorp.vulnerability import WeibullVC


@dataclass(frozen=True, slots=True)
class ThorpDefaultParams:
    soil_initialization: SoilInitializationParams
    richards: RichardsEquationParams
    soil_moisture: SoilMoistureParams
    root_uptake: RootUptakeParams
    stomata: StomataParams
    allocation: AllocationParams
    growth: GrowthParams
    huber_value: HuberValueParams


def default_params() -> ThorpDefaultParams:
    """Return canonical legacy-like defaults for already migrated THORP seams."""

    rho = 998.0
    g = 9.81
    r_gas = 8.314
    m_h2o = 18.01528e-3

    sla = 0.08
    xi = 0.5
    rho_cw = 1.4e4

    d_ref = 1.0
    b0 = 64.6
    c0 = 0.6411
    b1 = 8.5
    c1 = 0.625

    soil = SoilHydraulics(
        n_vg=2.70,
        alpha_vg=1.4642,
        l_vg=0.5,
        e_z_n=13.6,
        e_z_k_s_sat=3.2,
    )
    vc_r = WeibullVC(b=1.2949, c=2.6471)
    beta_r_h = 3388.15038831676
    beta_r_v = 941.1528856435444

    soil_initialization = SoilInitializationParams(
        rho=rho,
        g=g,
        z_wt=74.0,
        z_soil=30.0,
        n_soil=15,
        bc_bttm="FreeDrainage",
        soil=soil,
        vc_r=vc_r,
        beta_r_h=beta_r_h,
        beta_r_v=beta_r_v,
    )

    richards = RichardsEquationParams(
        dt=6 * 3600.0,
        rho=rho,
        g=g,
        bc_bttm=soil_initialization.bc_bttm,
        z_wt=soil_initialization.z_wt,
        p_bttm=rho * g * (soil_initialization.z_soil - soil_initialization.z_wt) / 1e6,
        soil=soil,
    )

    soil_moisture = SoilMoistureParams(
        richards=richards,
        m_h2o=m_h2o,
        r_gas=r_gas,
    )

    root_uptake = RootUptakeParams(
        beta_r_h=beta_r_h,
        beta_r_v=beta_r_v,
        vc_r=vc_r,
        rho=rho,
        g=g,
    )

    def v_cmax_func(t_l: NDArray[np.floating]) -> NDArray[np.floating]:
        return 60e-6 * np.exp(8e4 * (t_l + 273.15 - 290) / 290 / r_gas / (t_l + 273.15))

    def j_max_func(t_l: NDArray[np.floating]) -> NDArray[np.floating]:
        return 110e-6 * np.exp(8e4 * (t_l + 273.15 - 290) / 290 / r_gas / (t_l + 273.15))

    def gamma_star_func(t_l: NDArray[np.floating]) -> NDArray[np.floating]:
        return 36e-6 * 101.325 * np.ones_like(t_l)

    def k_c_func(t_l: NDArray[np.floating]) -> NDArray[np.floating]:
        return 275e-6 * 101.325 * np.ones_like(t_l)

    def k_o_func(t_l: NDArray[np.floating]) -> NDArray[np.floating]:
        return 420000e-6 * 101.325 * np.ones_like(t_l)

    def r_d_func(t_l: NDArray[np.floating]) -> NDArray[np.floating]:
        return 0.01 * v_cmax_func(t_l)

    stomata = StomataParams(
        root_uptake=root_uptake,
        g_wmin=0.0,
        c_prime1=0.98,
        c_prime2=0.90,
        d_ref=d_ref,
        c0=c0,
        c1=c1,
        b2=0.9253,
        c2=0.9296,
        k_l=1.6e-2,
        vc_sw=WeibullVC(b=5.3151, c=0.7951),
        vc_l=WeibullVC(b=0.8521, c=0.8067),
        v_cmax_func=v_cmax_func,
        j_max_func=j_max_func,
        gamma_star_func=gamma_star_func,
        k_c_func=k_c_func,
        k_o_func=k_o_func,
        r_d_func=r_d_func,
        var_kappa=6.9e-7,
        c_a=410e-6 * 101.325,
        o_a=21.0,
    )

    def r_m_sw_func(t: float | NDArray[np.floating]) -> float | NDArray[np.floating]:
        return 2.2e-12 * 1.8 ** ((np.asarray(t) - 15.0) / 10.0)

    def r_m_r_func(t: float | NDArray[np.floating]) -> float | NDArray[np.floating]:
        return 7.0e-9 * 1.98 ** ((np.asarray(t) - 15.0) / 10.0)

    allocation = AllocationParams(
        sla=sla,
        r_m_sw_func=r_m_sw_func,
        r_m_r_func=r_m_r_func,
        tau_l=9.5e7,
        tau_sw=1.2e9,
        tau_r=9.6e7,
    )

    growth = GrowthParams(
        allocation=allocation,
        dt=richards.dt,
        f_c=0.28,
        rho_cw=rho_cw,
        xi=xi,
        b0=b0,
        d_ref=d_ref,
        c0=c0,
        b1=b1,
        c1=c1,
    )

    huber_value = HuberValueParams(sla=sla, xi=xi)

    return ThorpDefaultParams(
        soil_initialization=soil_initialization,
        richards=richards,
        soil_moisture=soil_moisture,
        root_uptake=root_uptake,
        stomata=stomata,
        allocation=allocation,
        growth=growth,
        huber_value=huber_value,
    )
