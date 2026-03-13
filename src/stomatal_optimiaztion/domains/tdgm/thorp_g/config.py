from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

import numpy as np
from numpy.typing import NDArray

REPO_ROOT = Path(__file__).resolve().parents[5]
WORKSPACE_ROOT = REPO_ROOT.parents[1]
DEFAULT_LEGACY_TDGM_THORP_G_ROOT = (
    WORKSPACE_ROOT
    / "00. Stomatal Optimization"
    / "TDGM"
    / "example"
    / "Supplementary Code __THORP_code_v1.4"
)

BottomBoundaryCondition = Literal["ConstantPressure", "FreeDrainage", "GroundwaterTable"]


@dataclass(frozen=True, slots=True)
class SoilHydraulics:
    """Soil parameterization used by THORP/THORP-G (van Genuchten-style)."""

    n_vg: float
    alpha_vg: float
    l_vg: float
    e_z_n: float
    e_z_k_s_sat: float
    vwc_res: float = 0.0

    def vwc_sat(self, z: NDArray[np.floating]) -> NDArray[np.floating]:
        return 0.4 * np.exp(-z / self.e_z_n)

    def k_s_sat(self, z: NDArray[np.floating]) -> NDArray[np.floating]:
        return 6e-7 * np.exp(-z / self.e_z_k_s_sat)

    def k_soil_sat(self, z: NDArray[np.floating]) -> NDArray[np.floating]:
        return self.k_s_sat(z)

    def s_e(self, psi_soil: NDArray[np.floating]) -> NDArray[np.floating]:
        return (1 + np.abs(self.alpha_vg * psi_soil) ** self.n_vg) ** -(1 - 1 / self.n_vg)

    def vwc(self, psi_soil: NDArray[np.floating], z: NDArray[np.floating]) -> NDArray[np.floating]:
        return self.vwc_res + (self.vwc_sat(z) - self.vwc_res) * self.s_e(psi_soil)

    def k_s(self, psi_soil: NDArray[np.floating], z: NDArray[np.floating]) -> NDArray[np.floating]:
        s_e = self.s_e(psi_soil)
        term = (1 - (1 - s_e ** (1 / (1 - 1 / self.n_vg))) ** (1 - 1 / self.n_vg)) ** 2
        return self.k_s_sat(z) * s_e**self.l_vg * term

    def k_soil(self, psi_soil_by_layer: NDArray[np.floating], z: NDArray[np.floating]) -> NDArray[np.floating]:
        return self.k_s(psi_soil_by_layer, z)


@dataclass(frozen=True, slots=True)
class WeibullVC:
    b: float
    c: float

    def __call__(self, p: NDArray[np.floating] | float) -> NDArray[np.floating] | float:
        if np.isscalar(p):
            p_scalar = float(p)
            if p_scalar > 0.0:
                p_scalar = 0.0
            with np.errstate(over="ignore", invalid="ignore"):
                return float(np.exp(-(-p_scalar / self.b) ** self.c))

        p_arr = np.asarray(p, dtype=float)
        p_arr = np.minimum(p_arr, 0.0)
        with np.errstate(over="ignore", invalid="ignore"):
            out = np.exp(-(-p_arr / self.b) ** self.c)
        return out


@dataclass(frozen=True, slots=True)
class ThorpGParams:
    """Parameter container matching the MATLAB v1.4 THORP-G reference.

    Sources (MATLAB):
    - `TDGM/example/Supplementary Code __THORP_code_v1.4/INPUTS_0_Constants.m`
    - `TDGM/example/Supplementary Code __THORP_code_v1.4/INPUTS_1_Initial_Allometry.m`
    - `TDGM/example/Supplementary Code __THORP_code_v1.4/INPUTS_2_Environmental_Conditions.m`
    - `TDGM/example/Supplementary Code __THORP_code_v1.4/FUNCTION_Turgor_driven_growth_THORP.m`
    """

    run_name: str

    dt: float
    dt_allocate: float
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
    rho_cl: float

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

    v_cmax_func: Callable[[NDArray[np.floating]], NDArray[np.floating]]
    j_max_func: Callable[[NDArray[np.floating]], NDArray[np.floating]]
    gamma_star_func: Callable[[NDArray[np.floating]], NDArray[np.floating]]
    k_c_func: Callable[[NDArray[np.floating]], NDArray[np.floating]]
    k_o_func: Callable[[NDArray[np.floating]], NDArray[np.floating]]
    r_d_func: Callable[[NDArray[np.floating]], NDArray[np.floating]]

    var_kappa: float

    f_c: float
    r_m_sw_func: Callable[[float | NDArray[np.floating]], float | NDArray[np.floating]]
    r_m_r_func: Callable[[float | NDArray[np.floating]], float | NDArray[np.floating]]

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

    # THORP-G extras (turgor-limited growth)
    rho_cl_init: float
    c_sucrose_p_init: float
    c_mm_sucrose: float

    v_sucrose: float
    phi_wall: float
    gamma_turgor_crit: float
    gamma_turgor_shift: float


def default_params(
    *,
    forcing_path: str | Path | None = None,
    run_name: str = "Control_Turgor_Gamma_minus_0.1MPa",
    forcing_rh_scale: float = 1.0,
    forcing_precip_scale: float = 1.0,
    forcing_repeat_q: int = 15,
) -> ThorpGParams:
    """Defaults intended to match the shipped MATLAB v1.4 reference code."""

    dt = 6 * 3600.0
    dt_allocate = 24 * 3600.0
    dt_sav_file = 60 * 24 * 3600.0
    dt_sav_data = 7 * 24 * 3600.0
    dt_sav_data = (24 * 3600.0) * np.ceil(dt_sav_data / (24 * 3600.0))

    sigma = 5.67e-8
    r_gas = 8.314
    g = 9.81

    c_p = 29.3
    rho = 998.0
    m_h2o = 18.01528e-3

    epsilon_soil = 0.95
    g_wmin = 0.0

    sla = 0.08
    xi = 0.5
    rho_cw = 1.4e4
    rho_cl = 2e4

    kappa_l = 0.32
    phi = 3.34
    h_n = 0.0
    lai_n = 3.0
    kappa_n = kappa_l * lai_n / h_n if h_n != 0 else 0.0

    c_prime1 = 0.98
    c_prime2 = 0.90

    d_ref = 1.0
    b0 = 64.6
    c0 = 0.6411
    b1 = 8.5
    c1 = 0.625

    b2 = 0.9253
    c2 = 0.9296

    k_l = 1.6e-2

    vc_sw = WeibullVC(b=5.3151, c=0.7951)
    vc_l = WeibullVC(b=0.8521, c=0.8067)
    vc_r = WeibullVC(b=1.2949, c=2.6471)

    e_md = 0.0016
    res_fract_root = 0.45
    psi_l_md = -1.50
    psi_l_pd = -0.72
    f_r = 0.8
    lai = 0.4
    rmf = 0.2
    smf = 0.7
    h_cal = 14.0
    z_cal = 3.0

    d_cal = d_ref * (h_cal / b0) ** (1 / c0)
    w_cal = b1 * (d_cal / d_ref) ** c1
    la_cal = lai * phi * w_cal**2
    c_w_cal = rho_cw * xi * d_cal**2 * h_cal
    c_r_cal = rmf * (c_w_cal / smf)

    mass_fract_root_vert = 1 / 3
    c_r_h_cal = (1 - mass_fract_root_vert) * c_r_cal
    c_r_v_cal = mass_fract_root_vert * c_r_cal

    psi_soil_avg = psi_l_pd + rho * g * (h_cal + z_cal / 2) / 1e6
    psi_rc_md = psi_soil_avg - res_fract_root * (psi_soil_avg - psi_l_md)
    r_r = (psi_soil_avg - psi_rc_md) / la_cal / e_md

    res_fract_root_vert = 1 / 2
    r_r_h = (1 - res_fract_root_vert) * r_r
    r_r_v = res_fract_root_vert * r_r
    beta_r_h = f_r * r_r_h * c_r_h_cal
    beta_r_v = r_r_v * c_r_v_cal / (z_cal / 2) ** 2

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

    var_kappa = 6.9e-7

    f_c = 0.28

    # NOTE: MATLAB v1.4 differs from THORP baseline here.
    r_m_sw_15 = 6.6e-11
    r_m_r_15 = 7.0e-9

    def r_m_sw_func(t: float | NDArray[np.floating]) -> float | NDArray[np.floating]:
        return r_m_sw_15 * 1.8 ** ((np.asarray(t) - 15.0) / 10.0)

    def r_m_r_func(t: float | NDArray[np.floating]) -> float | NDArray[np.floating]:
        return r_m_r_15 * 1.98 ** ((np.asarray(t) - 15.0) / 10.0)

    tau_l = 9.5e7
    tau_sw = 1.2e9
    tau_r = 9.6e7

    c_a = 410e-6 * 101.325
    o_a = 21.0

    soil = SoilHydraulics(n_vg=2.70, alpha_vg=1.4642, l_vg=0.5, e_z_n=13.6, e_z_k_s_sat=3.2)

    z_soil = 30.0
    n_soil = 15
    bc_bttm: BottomBoundaryCondition = "FreeDrainage"
    z_wt = 74.0
    p_bttm = rho * g * (z_soil - z_wt) / 1e6

    if forcing_path is None:
        forcing_path = (
            DEFAULT_LEGACY_TDGM_THORP_G_ROOT
            / "Poblet_reserve_Prades_Mountains_NE_Spain_v2.nc"
        )
    forcing_path = Path(forcing_path)

    forcing_lat_rad = np.pi / 180.0 * (41 + 19 / 60 + 58.05 / 3600)

    # THORP-G extras (MATLAB v1.4)
    rho_cl_init = rho_cl
    c_sucrose_p_init = 600.0
    c_mm_sucrose = 300.0

    v_sucrose = 2.155e-4
    phi_wall = 2.3e-7
    gamma_turgor_crit = 0.75
    gamma_turgor_shift = -0.10

    return ThorpGParams(
        run_name=run_name,
        dt=dt,
        dt_allocate=dt_allocate,
        dt_sav_file=dt_sav_file,
        dt_sav_data=float(dt_sav_data),
        sigma=sigma,
        r_gas=r_gas,
        g=g,
        c_p=c_p,
        rho=rho,
        m_h2o=m_h2o,
        epsilon_soil=epsilon_soil,
        g_wmin=g_wmin,
        sla=sla,
        xi=xi,
        rho_cw=rho_cw,
        rho_cl=rho_cl,
        kappa_l=kappa_l,
        phi=phi,
        h_n=h_n,
        lai_n=lai_n,
        kappa_n=kappa_n,
        c_prime1=c_prime1,
        c_prime2=c_prime2,
        d_ref=d_ref,
        b0=b0,
        c0=c0,
        b1=b1,
        c1=c1,
        b2=b2,
        c2=c2,
        k_l=k_l,
        vc_sw=vc_sw,
        vc_l=vc_l,
        vc_r=vc_r,
        beta_r_h=float(beta_r_h),
        beta_r_v=float(beta_r_v),
        v_cmax_func=v_cmax_func,
        j_max_func=j_max_func,
        gamma_star_func=gamma_star_func,
        k_c_func=k_c_func,
        k_o_func=k_o_func,
        r_d_func=r_d_func,
        var_kappa=var_kappa,
        f_c=f_c,
        r_m_sw_func=r_m_sw_func,
        r_m_r_func=r_m_r_func,
        tau_l=tau_l,
        tau_sw=tau_sw,
        tau_r=tau_r,
        c_a=c_a,
        o_a=o_a,
        soil=soil,
        z_soil=z_soil,
        n_soil=n_soil,
        bc_bttm=bc_bttm,
        z_wt=z_wt,
        p_bttm=p_bttm,
        forcing_path=forcing_path,
        forcing_lat_rad=float(forcing_lat_rad),
        forcing_repeat_q=int(forcing_repeat_q),
        forcing_rh_scale=float(forcing_rh_scale),
        forcing_precip_scale=float(forcing_precip_scale),
        rho_cl_init=rho_cl_init,
        c_sucrose_p_init=c_sucrose_p_init,
        c_mm_sucrose=c_mm_sucrose,
        v_sucrose=v_sucrose,
        phi_wall=phi_wall,
        gamma_turgor_crit=gamma_turgor_crit,
        gamma_turgor_shift=gamma_turgor_shift,
    )
