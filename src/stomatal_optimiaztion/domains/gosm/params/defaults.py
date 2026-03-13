from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np


@dataclass(frozen=True)
class BaselineInputs:
    """Baseline parameters mirroring `example/INPUTS_0_Constants.m`."""

    # Physical constants
    sigma: float
    r_gas: float
    g: float

    # Properties of water and air
    rho: float
    m: float
    c_p: float
    emiss: float
    p_atm: float
    g_b: float

    # Canopy/light
    phi_l: float
    kappa_l: float

    # Geometry/biomass pools
    la: float
    h: float
    w: float
    z: float
    c_w: float
    c_r: float
    c_struct: float

    # Growth / NSC
    p_turgor_crit: float
    u_w: float
    f_c: float
    gamma_g: float
    gamma_r: float

    # Hydraulic conductances and vulnerability
    k_l: float
    k_sw: float
    alpha_sw: float
    beta_sw: float
    k_r: float
    alpha_r: float
    beta_r: float
    alpha_l: float
    beta_l: float

    # Phloem sap osmotic potential
    c_m1: float
    c_m2: float
    c_pi1: float
    c_pi2: float

    # Farquhar parameters
    var_kappa: float
    theta_j: float
    theta_c: float
    c_a: float
    o_a: float

    # Default environment
    t_a: float
    rh: float
    r_incom: float
    z_a: float
    psi_soil: float

    # Function handles (vectorized over numpy arrays where applicable)
    theta_g: Callable[[np.ndarray | float], np.ndarray]
    theta_r: Callable[[np.ndarray | float], np.ndarray]
    phi_extens_effective: Callable[[np.ndarray | float], np.ndarray]
    v_cmax: Callable[[np.ndarray | float], np.ndarray]
    j_max: Callable[[np.ndarray | float], np.ndarray]
    gamma_star: Callable[[np.ndarray | float], np.ndarray]
    k_c: Callable[[np.ndarray | float], np.ndarray]
    k_o: Callable[[np.ndarray | float], np.ndarray]
    r_d: Callable[[np.ndarray | float], np.ndarray]
    r_m_w: Callable[[np.ndarray | float], np.ndarray]
    r_m_r: Callable[[np.ndarray | float], np.ndarray]

    # Baseline NSC state (used by example scripts)
    c_nsc: float

    # ------------------------------------------------------------------
    # Legacy aliases (MATLAB-style naming)
    @property
    def R(self) -> float:  # noqa: N802 (legacy alias)
        return self.r_gas

    @property
    def C_p(self) -> float:  # noqa: N802 (legacy alias)
        return self.c_p

    @property
    def P_atm(self) -> float:  # noqa: N802 (legacy alias)
        return self.p_atm

    @property
    def c_NSC(self) -> float:  # noqa: N802 (legacy alias)
        return self.c_nsc

    @property
    def Gamma(self) -> float:  # noqa: N802 (legacy alias)
        return self.p_turgor_crit

    @property
    def c_Pi1(self) -> float:  # noqa: N802 (legacy alias)
        return self.c_pi1

    @property
    def c_Pi2(self) -> float:  # noqa: N802 (legacy alias)
        return self.c_pi2

    @property
    def theta_J(self) -> float:  # noqa: N802 (legacy alias)
        return self.theta_j

    @property
    def V_cmax(self) -> Callable[[np.ndarray | float], np.ndarray]:  # noqa: N802 (legacy alias)
        return self.v_cmax

    @property
    def J_max(self) -> Callable[[np.ndarray | float], np.ndarray]:  # noqa: N802 (legacy alias)
        return self.j_max

    @property
    def Gamma_star(self) -> Callable[[np.ndarray | float], np.ndarray]:  # noqa: N802 (legacy alias)
        return self.gamma_star

    @property
    def K_c(self) -> Callable[[np.ndarray | float], np.ndarray]:  # noqa: N802 (legacy alias)
        return self.k_c

    @property
    def K_o(self) -> Callable[[np.ndarray | float], np.ndarray]:  # noqa: N802 (legacy alias)
        return self.k_o

    @property
    def R_d(self) -> Callable[[np.ndarray | float], np.ndarray]:  # noqa: N802 (legacy alias)
        return self.r_d

    @property
    def T_a(self) -> float:  # noqa: N802 (legacy alias)
        return self.t_a

    @property
    def RH(self) -> float:  # noqa: N802 (legacy alias)
        return self.rh

    @property
    def R_incom(self) -> float:  # noqa: N802 (legacy alias)
        return self.r_incom

    @property
    def Z_a(self) -> float:  # noqa: N802 (legacy alias)
        return self.z_a

    @property
    def P_soil(self) -> float:  # noqa: N802 (legacy alias)
        return self.psi_soil

    @staticmethod
    def matlab_default() -> "BaselineInputs":
        """Recreate MATLAB baseline constants from `example/INPUTS_0_Constants.m`."""

        # Physical constants
        sigma = 5.67e-8
        r_gas = 8.314
        g = 9.81

        # Properties of water and air
        rho = 998.0
        m = 18e-3
        c_p = 29.2
        emiss = 0.97
        p_atm = 101.325
        g_b = 2.4

        # Power-law scaling relationships
        D_ref = 1.0
        b0 = 64.6
        c0 = 0.6411
        b1 = 8.5
        c1 = 0.625

        phi_l = 3.34
        kappa_l = 0.5
        SLA = 0.08

        xi = 0.5
        rho_cw = 1.4e4

        # turgor-driven growth parameters
        p_turgor_crit = 0.75

        # temperature formulation for extensibility
        dH_A = 8.168016723036066e04
        dH_D = 3.096128959045594e05
        dS_D = 1.012945432894354e03
        T_a_thresh = 5.0
        A = 1 / (
            298.15
            * np.exp(-dH_A / r_gas / 298.15)
            / (1 + np.exp(dS_D / r_gas - dH_D / r_gas / 298.15))
            - (T_a_thresh + 273.15)
            * np.exp(-dH_A / r_gas / (T_a_thresh + 273.15))
            / (1 + np.exp(dS_D / r_gas - dH_D / r_gas / (T_a_thresh + 273.15)))
        )

        def g_T(t_a: np.ndarray | float) -> np.ndarray:
            t_a = np.asarray(t_a, dtype=float)
            term = (t_a + 273.15) * np.exp(-dH_A / r_gas / (t_a + 273.15)) / (
                1 + np.exp(dS_D / r_gas - dH_D / r_gas / (t_a + 273.15))
            )
            term_thresh = (T_a_thresh + 273.15) * np.exp(-dH_A / r_gas / (T_a_thresh + 273.15)) / (
                1 + np.exp(dS_D / r_gas - dH_D / r_gas / (T_a_thresh + 273.15))
            )
            return np.maximum(0.0, A * (term - term_thresh))

        phi_extens_effective_25C = 4.573214191984838e-08

        def phi_extens_effective(t_a: np.ndarray | float) -> np.ndarray:
            return phi_extens_effective_25C * g_T(t_a)

        u_w = 0.25

        # phloem sap molality and osmotic potential
        c_m1 = 0.48
        c_m2 = 0.13
        c_pi1 = 0.998
        c_pi2 = 0.089

        def m_p_func(psi_s: np.ndarray | float) -> np.ndarray:
            return c_m1 - c_m2 * np.asarray(psi_s, dtype=float)

        def Pi_func(m_p: np.ndarray | float, t_a: np.ndarray | float) -> np.ndarray:
            m_p = np.asarray(m_p, dtype=float)
            t_a = np.asarray(t_a, dtype=float)
            return -1e-6 * rho * r_gas * (t_a + 273.15) * (c_pi1 * m_p + c_pi2 * m_p**2)

        # Hydraulic Conductances
        b2 = 0.9253
        c2 = 0.9296
        k_l = 1.6e-2

        E_MD = 0.0016
        res_fract_root = 0.45
        psi_l_md = -1.50
        psi_l_pd = -0.72
        f_r = 0.8
        LAI = 0.4
        RMF = 0.2
        SMF = 0.7
        h = 14.0
        z = 3.0

        D = D_ref * (h / b0) ** (1 / c0)
        w = b1 * (D / D_ref) ** c1
        la = LAI * phi_l * w**2
        c_w = rho_cw * xi * D**2 * h
        c_r = RMF * (c_w / SMF)
        c_l = la / SLA

        psi_soil_avg = psi_l_pd + rho * g * (h + z) / 1e6
        psi_rc_md = psi_soil_avg - res_fract_root * (psi_soil_avg - psi_l_md)
        r_R = (psi_soil_avg - psi_rc_md) / la / E_MD
        k_r = 1 / r_R / f_r

        c_sw = 0.94 * c_w
        c_hw = c_w - c_sw
        D_hw = (c_hw / (rho_cw * xi * h)) ** 0.5
        k_sw = b2 * (D / D_ref) ** c2 * (1 - (D_hw / D) ** (c2 / c0 + 1))

        c_struct = c_w + c_r + c_l

        # NSC storage
        c_nsc = 175.0
        gamma_g = 0.26
        gamma_r = 0.38

        def theta_g(c_nsc_val: np.ndarray | float) -> np.ndarray:
            c_nsc_val = np.asarray(c_nsc_val, dtype=float)
            return c_nsc_val / (c_nsc_val + gamma_g * c_struct)

        def theta_r(c_nsc_val: np.ndarray | float) -> np.ndarray:
            c_nsc_val = np.asarray(c_nsc_val, dtype=float)
            return c_nsc_val / (c_nsc_val + gamma_r * c_struct)

        # Vulnerability curve parameters
        alpha_sw = 0.8
        beta_sw = -3.3

        alpha_l = 1.5
        beta_l = -0.75

        alpha_r = 3.5
        beta_r = -1.1

        # Farquhar photosynthesis parameters
        def v_cmax(t_l: np.ndarray | float) -> np.ndarray:
            t_l = np.asarray(t_l, dtype=float)
            return 60e-6 * np.exp(8e4 * (t_l + 273.15 - 290) / 290 / r_gas / (t_l + 273.15))

        def j_max(t_l: np.ndarray | float) -> np.ndarray:
            t_l = np.asarray(t_l, dtype=float)
            return 110e-6 * np.exp(8e4 * (t_l + 273.15 - 290) / 290 / r_gas / (t_l + 273.15))

        def gamma_star(t_l: np.ndarray | float) -> np.ndarray:
            t_l = np.asarray(t_l, dtype=float)
            return 36e-6 * np.ones_like(t_l, dtype=float)

        def k_c(t_l: np.ndarray | float) -> np.ndarray:
            t_l = np.asarray(t_l, dtype=float)
            return 275e-6 * np.ones_like(t_l, dtype=float)

        def k_o(t_l: np.ndarray | float) -> np.ndarray:
            t_l = np.asarray(t_l, dtype=float)
            return 420000e-6 * np.ones_like(t_l, dtype=float)

        def r_d(t_l: np.ndarray | float) -> np.ndarray:
            t_l = np.asarray(t_l, dtype=float)
            return 0.01 * float(v_cmax(25.0)) * 2.0 ** ((t_l - 25.0) / 10.0)

        var_kappa = 6.9e-7
        theta_c = 0.98
        theta_j = 0.90

        # Base respiration parameters
        f_c = 0.28
        r_m_w_15 = 3.412162425647622 * 6.6e-11
        r_m_r_15 = 3.412162425647622 * 3.1e-8

        def r_m_w(T: np.ndarray | float) -> np.ndarray:
            T = np.asarray(T, dtype=float)
            return r_m_w_15 * 1.8 ** ((T - 15.0) / 10.0)

        def r_m_r(T: np.ndarray | float) -> np.ndarray:
            T = np.asarray(T, dtype=float)
            return r_m_r_15 * 1.98 ** ((T - 15.0) / 10.0)

        # Atmospheric conditions (default)
        c_a = 410e-6
        o_a = 21 / 101.325
        t_a = 25.0
        rh = 0.4
        r_incom = 600.0
        z_a = 0.0

        # Soil conditions (default)
        psi_soil = -0.0

        # NOTE: Pi_func is defined above but currently unused by the Python port directly;
        # the hydraulics module re-implements the exact expression inline for fidelity.
        _ = m_p_func, Pi_func

        return BaselineInputs(
            sigma=sigma,
            r_gas=r_gas,
            g=g,
            rho=rho,
            m=m,
            c_p=c_p,
            emiss=emiss,
            p_atm=p_atm,
            g_b=g_b,
            phi_l=phi_l,
            kappa_l=kappa_l,
            la=la,
            h=h,
            w=w,
            z=z,
            c_w=c_w,
            c_r=c_r,
            c_struct=c_struct,
            p_turgor_crit=p_turgor_crit,
            u_w=u_w,
            f_c=f_c,
            gamma_g=gamma_g,
            gamma_r=gamma_r,
            k_l=k_l,
            k_sw=k_sw,
            alpha_sw=alpha_sw,
            beta_sw=beta_sw,
            k_r=k_r,
            alpha_r=alpha_r,
            beta_r=beta_r,
            alpha_l=alpha_l,
            beta_l=beta_l,
            c_m1=c_m1,
            c_m2=c_m2,
            c_pi1=c_pi1,
            c_pi2=c_pi2,
            var_kappa=var_kappa,
            theta_j=theta_j,
            theta_c=theta_c,
            c_a=c_a,
            o_a=o_a,
            t_a=t_a,
            rh=rh,
            r_incom=r_incom,
            z_a=z_a,
            psi_soil=psi_soil,
            theta_g=theta_g,
            theta_r=theta_r,
            phi_extens_effective=phi_extens_effective,
            v_cmax=v_cmax,
            j_max=j_max,
            gamma_star=gamma_star,
            k_c=k_c,
            k_o=k_o,
            r_d=r_d,
            r_m_w=r_m_w,
            r_m_r=r_m_r,
            c_nsc=c_nsc,
        )
