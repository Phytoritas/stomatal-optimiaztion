from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from stomatal_optimiaztion.domains.thorp.defaults import (
    ThorpDefaultParams,
    default_params as default_bundle_params,
)
from stomatal_optimiaztion.domains.thorp.soil_hydraulics import SoilHydraulics
from stomatal_optimiaztion.domains.thorp.soil_initialization import BottomBoundaryCondition
from stomatal_optimiaztion.domains.thorp.vulnerability import WeibullVC

ResponseCurve = Callable[[NDArray[np.floating]], NDArray[np.floating]]
TemperatureResponse = Callable[[float | NDArray[np.floating]], float | NDArray[np.floating]]

DEFAULT_RUN_NAME = "0.6RH"
DEFAULT_DT_SAV_FILE = 60 * 24 * 3600.0
DEFAULT_DT_SAV_DATA = float((24 * 3600.0) * np.ceil((7 * 24 * 3600.0) / (24 * 3600.0)))
DEFAULT_SIGMA = 5.67e-8
DEFAULT_C_P = 29.3
DEFAULT_EPSILON_SOIL = 0.95
DEFAULT_KAPPA_L = 0.32
DEFAULT_PHI = 3.34
DEFAULT_H_N = 0.0
DEFAULT_LAI_N = 3.0
DEFAULT_FORCING_PATH = Path("data/forcing/Poblet_reserve_Prades_Mountains_NE_Spain_v2.nc")
DEFAULT_FORCING_LAT_RAD = float(np.pi / 180.0 * (41 + 19 / 60 + 58.05 / 3600))
DEFAULT_FORCING_REPEAT_Q = 15
DEFAULT_FORCING_RH_SCALE = 0.6
DEFAULT_FORCING_PRECIP_SCALE = 1.0


@dataclass(frozen=True, slots=True)
class THORPParams:
    run_name: str

    dt: float
    dt_sav_file: float
    dt_sav_data: float

    sigma: float
    r_gas: float
    g: float

    c_p: float
    rho: float
    m_h2o: float

    epsilon_soil: float
    g_wmin: float

    sla: float
    xi: float
    rho_cw: float

    kappa_l: float
    phi: float
    h_n: float
    lai_n: float
    kappa_n: float

    c_prime1: float
    c_prime2: float

    d_ref: float
    b0: float
    c0: float
    b1: float
    c1: float

    b2: float
    c2: float
    k_l: float

    vc_sw: WeibullVC
    vc_l: WeibullVC
    vc_r: WeibullVC
    beta_r_h: float
    beta_r_v: float

    v_cmax_func: ResponseCurve
    j_max_func: ResponseCurve
    gamma_star_func: ResponseCurve
    k_c_func: ResponseCurve
    k_o_func: ResponseCurve
    r_d_func: ResponseCurve

    var_kappa: float

    f_c: float
    r_m_sw_func: TemperatureResponse
    r_m_r_func: TemperatureResponse

    tau_l: float
    tau_sw: float
    tau_r: float

    c_a: float
    o_a: float

    soil: SoilHydraulics

    z_soil: float
    n_soil: int
    bc_bttm: BottomBoundaryCondition
    z_wt: float
    p_bttm: float

    forcing_path: Path
    forcing_lat_rad: float
    forcing_repeat_q: int
    forcing_rh_scale: float
    forcing_precip_scale: float


def thorp_params_from_defaults(
    defaults_bundle: ThorpDefaultParams | None = None,
    *,
    run_name: str = DEFAULT_RUN_NAME,
    forcing_path: Path | str = DEFAULT_FORCING_PATH,
    forcing_lat_rad: float = DEFAULT_FORCING_LAT_RAD,
    forcing_repeat_q: int = DEFAULT_FORCING_REPEAT_Q,
    forcing_rh_scale: float = DEFAULT_FORCING_RH_SCALE,
    forcing_precip_scale: float = DEFAULT_FORCING_PRECIP_SCALE,
) -> THORPParams:
    """Build a legacy-compatible THORP flat params bundle from migrated defaults."""

    bundle = defaults_bundle if defaults_bundle is not None else default_bundle_params()

    soil_initialization = bundle.soil_initialization
    richards = bundle.richards
    soil_moisture = bundle.soil_moisture
    root_uptake = bundle.root_uptake
    stomata = bundle.stomata
    allocation = bundle.allocation
    growth = bundle.growth

    h_n = DEFAULT_H_N
    lai_n = DEFAULT_LAI_N
    kappa_n = DEFAULT_KAPPA_L * lai_n / h_n if h_n != 0 else 0.0

    return THORPParams(
        run_name=run_name,
        dt=richards.dt,
        dt_sav_file=DEFAULT_DT_SAV_FILE,
        dt_sav_data=DEFAULT_DT_SAV_DATA,
        sigma=DEFAULT_SIGMA,
        r_gas=soil_moisture.r_gas,
        g=soil_initialization.g,
        c_p=DEFAULT_C_P,
        rho=soil_initialization.rho,
        m_h2o=soil_moisture.m_h2o,
        epsilon_soil=DEFAULT_EPSILON_SOIL,
        g_wmin=stomata.g_wmin,
        sla=allocation.sla,
        xi=growth.xi,
        rho_cw=growth.rho_cw,
        kappa_l=DEFAULT_KAPPA_L,
        phi=DEFAULT_PHI,
        h_n=h_n,
        lai_n=lai_n,
        kappa_n=kappa_n,
        c_prime1=stomata.c_prime1,
        c_prime2=stomata.c_prime2,
        d_ref=stomata.d_ref,
        b0=growth.b0,
        c0=stomata.c0,
        b1=growth.b1,
        c1=stomata.c1,
        b2=stomata.b2,
        c2=stomata.c2,
        k_l=stomata.k_l,
        vc_sw=stomata.vc_sw,
        vc_l=stomata.vc_l,
        vc_r=root_uptake.vc_r,
        beta_r_h=root_uptake.beta_r_h,
        beta_r_v=root_uptake.beta_r_v,
        v_cmax_func=stomata.v_cmax_func,
        j_max_func=stomata.j_max_func,
        gamma_star_func=stomata.gamma_star_func,
        k_c_func=stomata.k_c_func,
        k_o_func=stomata.k_o_func,
        r_d_func=stomata.r_d_func,
        var_kappa=stomata.var_kappa,
        f_c=growth.f_c,
        r_m_sw_func=allocation.r_m_sw_func,
        r_m_r_func=allocation.r_m_r_func,
        tau_l=allocation.tau_l,
        tau_sw=allocation.tau_sw,
        tau_r=allocation.tau_r,
        c_a=stomata.c_a,
        o_a=stomata.o_a,
        soil=soil_initialization.soil,
        z_soil=soil_initialization.z_soil,
        n_soil=soil_initialization.n_soil,
        bc_bttm=soil_initialization.bc_bttm,
        z_wt=soil_initialization.z_wt,
        p_bttm=richards.p_bttm,
        forcing_path=Path(forcing_path),
        forcing_lat_rad=float(forcing_lat_rad),
        forcing_repeat_q=int(forcing_repeat_q),
        forcing_rh_scale=float(forcing_rh_scale),
        forcing_precip_scale=float(forcing_precip_scale),
    )
