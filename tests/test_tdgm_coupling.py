from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains import tdgm
from stomatal_optimiaztion.domains.tdgm import implemented_equations


def test_tdgm_coupling_equations_sanity() -> None:
    tree_volume = float(
        tdgm.tree_volume_from_carbon_pools(
            c_w=10.0,
            c_r=5.0,
            c_l=2.0,
            rho_c_s=2.0,
            rho_c_l=1.0,
        ).reshape(())
    )
    assert tree_volume == 9.5

    alpha = 1.0 / 12.0
    c_nsc_mobile = float(
        tdgm.mobile_nsc_from_phloem_concentration(
            c_p=120.0,
            tree_volume=tree_volume,
            alpha=alpha,
        ).reshape(())
    )
    assert np.isclose(c_nsc_mobile, (120.0 / alpha) * tree_volume)

    c_nsc_immobile = float(
        tdgm.immobile_nsc_from_total(c_nsc=20000.0, c_nsc_mobile=c_nsc_mobile).reshape(())
    )
    assert np.isclose(c_nsc_immobile, 20000.0 - c_nsc_mobile)

    k_mm = float(
        tdgm.michaelis_menten_coefficient_nsc(
            c_mm=60.0,
            tree_volume=tree_volume,
            alpha=alpha,
        ).reshape(())
    )
    assert np.isclose(k_mm, (60.0 / alpha) * tree_volume)

    theta_g = float(tdgm.nsc_limitation_growth(c_nsc_immobile=c_nsc_immobile, k_mm=k_mm).reshape(()))
    assert 0.0 <= theta_g <= 1.0

    g_rate = float(tdgm.realized_growth_rate(g_potential=1e-3, u_mod_t=0.9, theta_g=theta_g).reshape(()))
    assert np.isclose(g_rate, 1e-3 * 0.9 * theta_g)

    out = tdgm.compute_thorp_g_coupling_step(
        inputs=tdgm.ThorpGCouplingStepInputs(
            c_nsc=20000.0,
            c_p=120.0,
            g_potential=1e-3,
            u_mod_t=0.9,
            c_w=10.0,
            c_r=5.0,
            c_l=2.0,
            rho_c_s=2.0,
            rho_c_l=1.0,
            c_mm=60.0,
            alpha=alpha,
        )
    )
    assert np.isclose(out.tree_volume, tree_volume)
    assert np.isclose(out.g_rate, g_rate)


def test_allocation_fraction_from_history_constant_signal() -> None:
    v_i_ts = np.ones((5,), dtype=float)
    u_i_ts = tdgm.allocation_fraction_from_history(v_i_ts=v_i_ts, dt_s=86400.0, upsilon=3.8e-6)
    np.testing.assert_allclose(u_i_ts, v_i_ts, atol=0.0, rtol=0.0)


def test_initial_mean_allocation_fractions_match_matlab_biomass_partitioning() -> None:
    u_sw_mean, u_l_mean, u_r_h_mean, u_r_v_mean = tdgm.initial_mean_allocation_fractions(
        c_r_h=np.array([1.0, 3.0]),
        c_r_v=np.array([2.0, 4.0]),
    )

    assert np.isclose(u_sw_mean, 0.3)
    assert np.isclose(u_l_mean, 0.3)
    np.testing.assert_allclose(u_r_h_mean, np.array([0.04, 0.12]))
    np.testing.assert_allclose(u_r_v_mean, np.array([0.08, 0.16]))
    assert np.isclose(u_sw_mean + u_l_mean + np.sum(u_r_h_mean) + np.sum(u_r_v_mean), 1.0)


def test_tdgm_coupling_exports_equation_tags() -> None:
    assert implemented_equations(tdgm.tree_volume_from_carbon_pools) == ("Eq.S.3.3",)
    assert implemented_equations(tdgm.allocation_fraction_from_history) == ("Eq.S.3.7",)
