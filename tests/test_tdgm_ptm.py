from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.tdgm import implemented_equations
from stomatal_optimiaztion.domains.tdgm import mu_sucrose
from stomatal_optimiaztion.domains.tdgm import phloem_transport_concentration


def test_tdgm_ptm_has_equation_tags() -> None:
    assert implemented_equations(phloem_transport_concentration) == (
        "Eq_S1.26",
        "Eq_S1.30",
        "Eq_S1.35",
        "Eq_S1.36",
        "Eq_S1.38",
    )


def test_mu_sucrose_increases_with_concentration() -> None:
    result = mu_sucrose(np.array([100.0, 200.0]), 20.0)
    assert np.all(result > 0)
    assert result[1] > result[0]


def test_tdgm_ptm_preserves_apex_concentration_at_z_zero() -> None:
    result = phloem_transport_concentration(
        c_p_apex=50.0,
        h_tree=10.0,
        z=np.array([0.0]),
        psi_rc=-0.2,
        psi_s=-0.4,
        g_growth=1e-5,
        u_r_h=0.2,
        u_r_v=0.1,
        sigma=0.5,
        kappa_p0=1e-12,
        delta=0.2,
        kappa_p_height_exp=0.5,
        h_ref=5.0,
        a=0.75,
        b=2.0,
        r_gas=8.314,
        g_grav=9.81,
        k_s=1e-12,
        rho_w=998.0,
        c_r=5.0,
        c_sw=12.0,
        f_c=0.28,
        r_m_r_func=lambda t: 1e-6,
        r_m_sw_func=lambda t: 2e-6,
        t_a=20.0,
        t_soil=18.0,
    )

    assert np.allclose(result, np.array([50.0]))


def test_tdgm_ptm_returns_nan_when_physiological_guard_fails() -> None:
    result = phloem_transport_concentration(
        c_p_apex=1.0,
        h_tree=10.0,
        z=np.array([0.0, 5.0, 10.0]),
        psi_rc=0.0,
        psi_s=-0.5,
        g_growth=1e-5,
        u_r_h=0.2,
        u_r_v=0.1,
        sigma=0.5,
        kappa_p0=1e-12,
        delta=0.2,
        kappa_p_height_exp=0.5,
        h_ref=5.0,
        a=0.75,
        b=2.0,
        r_gas=8.314,
        g_grav=9.81,
        k_s=1e-12,
        rho_w=998.0,
        c_r=5.0,
        c_sw=12.0,
        f_c=0.28,
        r_m_r_func=lambda t: 1e-6,
        r_m_sw_func=lambda t: 2e-6,
        t_a=20.0,
        t_soil=18.0,
    )

    assert np.all(np.isnan(result))
