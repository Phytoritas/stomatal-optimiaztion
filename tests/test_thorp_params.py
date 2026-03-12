from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.testing import assert_allclose

from stomatal_optimiaztion.domains.thorp.defaults import default_params
from stomatal_optimiaztion.domains.thorp.params import THORPParams, thorp_params_from_defaults


def test_thorp_params_from_defaults_returns_legacy_compatible_bundle() -> None:
    params = thorp_params_from_defaults()

    assert isinstance(params, THORPParams)
    assert params.run_name == "0.6RH"
    assert params.dt == 6 * 3600.0
    assert params.dt_sav_file == 60 * 24 * 3600.0
    assert params.dt_sav_data == 7 * 24 * 3600.0
    assert params.sigma == 5.67e-8
    assert params.r_gas == 8.314
    assert params.g == 9.81
    assert params.c_p == 29.3
    assert params.rho == 998.0
    assert params.m_h2o == 18.01528e-3
    assert params.epsilon_soil == 0.95
    assert params.g_wmin == 0.0
    assert params.sla == 0.08
    assert params.xi == 0.5
    assert params.rho_cw == 1.4e4
    assert params.kappa_l == 0.32
    assert params.phi == 3.34
    assert params.h_n == 0.0
    assert params.lai_n == 3.0
    assert params.kappa_n == 0.0
    assert params.c_prime1 == 0.98
    assert params.c_prime2 == 0.90
    assert params.d_ref == 1.0
    assert params.b0 == 64.6
    assert params.c0 == 0.6411
    assert params.b1 == 8.5
    assert params.c1 == 0.625
    assert params.b2 == 0.9253
    assert params.c2 == 0.9296
    assert params.k_l == 1.6e-2
    assert params.beta_r_h == 3388.15038831676
    assert params.beta_r_v == 941.1528856435444
    assert params.var_kappa == 6.9e-7
    assert params.f_c == 0.28
    assert params.tau_l == 9.5e7
    assert params.tau_sw == 1.2e9
    assert params.tau_r == 9.6e7
    assert params.c_a == 0.04154325
    assert params.o_a == 21.0
    assert params.z_soil == 30.0
    assert params.n_soil == 15
    assert params.bc_bttm == "FreeDrainage"
    assert params.z_wt == 74.0
    assert params.p_bttm == -0.43077672000000006
    assert params.forcing_path == Path("data/forcing/Poblet_reserve_Prades_Mountains_NE_Spain_v2.nc")
    assert params.forcing_repeat_q == 15
    assert params.forcing_rh_scale == 0.6
    assert params.forcing_precip_scale == 1.0
    assert_allclose(params.forcing_lat_rad, 0.7213933036242081)


def test_thorp_params_from_defaults_matches_legacy_function_outputs() -> None:
    params = thorp_params_from_defaults()
    t_l = np.array([15.0, 25.0], dtype=float)

    assert_allclose(
        params.v_cmax_func(t_l),
        np.array([4.8488048999784482e-05, 1.4861206096092956e-04]),
    )
    assert_allclose(
        params.j_max_func(t_l),
        np.array([8.889475649960488e-05, 2.724554450950375e-04]),
    )
    assert_allclose(
        params.gamma_star_func(t_l),
        np.array([0.0036477, 0.0036477]),
    )
    assert_allclose(
        params.k_c_func(t_l),
        np.array([0.027864375, 0.027864375]),
    )
    assert_allclose(
        params.k_o_func(t_l),
        np.array([42.5565, 42.5565]),
    )
    assert_allclose(
        params.r_d_func(t_l),
        np.array([4.8488048999784479e-07, 1.4861206096092957e-06]),
    )
    assert_allclose(
        params.r_m_sw_func(t_l),
        np.array([2.20e-12, 3.96e-12]),
    )
    assert_allclose(
        params.r_m_r_func(t_l),
        np.array([7.000e-09, 1.386e-08]),
    )


def test_thorp_params_from_defaults_reuses_migrated_bundle_objects() -> None:
    defaults_bundle = default_params()
    params = thorp_params_from_defaults(defaults_bundle)

    assert params.soil is defaults_bundle.soil_initialization.soil
    assert params.vc_r is defaults_bundle.root_uptake.vc_r
    assert params.vc_sw is defaults_bundle.stomata.vc_sw
    assert params.vc_l is defaults_bundle.stomata.vc_l
    assert params.v_cmax_func is defaults_bundle.stomata.v_cmax_func
    assert params.r_m_sw_func is defaults_bundle.allocation.r_m_sw_func
    assert params.dt == defaults_bundle.richards.dt
    assert params.r_gas == defaults_bundle.soil_moisture.r_gas
    assert params.g == defaults_bundle.soil_initialization.g
    assert params.g_wmin == defaults_bundle.stomata.g_wmin
    assert params.beta_r_h == defaults_bundle.root_uptake.beta_r_h
    assert params.sla == defaults_bundle.allocation.sla
    assert params.xi == defaults_bundle.growth.xi
    assert params.p_bttm == defaults_bundle.richards.p_bttm
