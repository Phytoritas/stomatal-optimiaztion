from __future__ import annotations

import numpy as np
from numpy.testing import assert_allclose

from stomatal_optimiaztion.domains.thorp.defaults import ThorpDefaultParams, default_params
from stomatal_optimiaztion.domains.thorp.soil_initialization import SoilInitializationParams


def test_default_params_returns_expected_bundle_types() -> None:
    params = default_params()

    assert isinstance(params, ThorpDefaultParams)
    assert isinstance(params.soil_initialization, SoilInitializationParams)
    assert params.growth.allocation is params.allocation
    assert params.stomata.root_uptake is params.root_uptake
    assert params.soil_moisture.richards is params.richards


def test_default_params_matches_legacy_value_snapshot() -> None:
    params = default_params()

    assert params.soil_initialization.rho == 998.0
    assert params.soil_initialization.g == 9.81
    assert params.soil_initialization.z_wt == 74.0
    assert params.soil_initialization.z_soil == 30.0
    assert params.soil_initialization.n_soil == 15
    assert params.soil_initialization.bc_bttm == "FreeDrainage"
    assert params.soil_initialization.beta_r_h == 3388.15038831676
    assert params.soil_initialization.beta_r_v == 941.1528856435444
    assert params.soil_initialization.soil.n_vg == 2.70
    assert params.soil_initialization.soil.alpha_vg == 1.4642
    assert params.soil_initialization.vc_r.b == 1.2949
    assert params.soil_initialization.vc_r.c == 2.6471

    assert params.richards.dt == 6 * 3600.0
    assert np.isclose(params.richards.p_bttm, -0.43077672000000006)
    assert params.soil_moisture.m_h2o == 18.01528e-3
    assert params.soil_moisture.r_gas == 8.314

    assert params.root_uptake.beta_r_h == 3388.15038831676
    assert params.root_uptake.beta_r_v == 941.1528856435444
    assert params.stomata.g_wmin == 0.0
    assert params.stomata.c_prime1 == 0.98
    assert params.stomata.c_prime2 == 0.90
    assert params.stomata.k_l == 1.6e-2
    assert params.stomata.var_kappa == 6.9e-7
    assert params.stomata.c_a == 0.04154325
    assert params.stomata.o_a == 21.0

    assert params.allocation.sla == 0.08
    assert params.allocation.tau_l == 9.5e7
    assert params.allocation.tau_sw == 1.2e9
    assert params.allocation.tau_r == 9.6e7

    assert params.growth.dt == 6 * 3600.0
    assert params.growth.f_c == 0.28
    assert params.growth.rho_cw == 1.4e4
    assert params.growth.xi == 0.5
    assert params.growth.b0 == 64.6
    assert params.growth.d_ref == 1.0
    assert params.growth.c0 == 0.6411
    assert params.growth.b1 == 8.5
    assert params.growth.c1 == 0.625

    assert params.huber_value.sla == 0.08
    assert params.huber_value.xi == 0.5


def test_default_params_matches_legacy_function_outputs() -> None:
    params = default_params()
    t_l = np.array([15.0, 25.0], dtype=float)

    assert_allclose(
        params.stomata.v_cmax_func(t_l),
        np.array([4.8488048999784482e-05, 1.4861206096092956e-04]),
    )
    assert_allclose(
        params.stomata.j_max_func(t_l),
        np.array([8.889475649960488e-05, 2.724554450950375e-04]),
    )
    assert_allclose(
        params.stomata.gamma_star_func(t_l),
        np.array([0.0036477, 0.0036477]),
    )
    assert_allclose(
        params.stomata.k_c_func(t_l),
        np.array([0.027864375, 0.027864375]),
    )
    assert_allclose(
        params.stomata.k_o_func(t_l),
        np.array([42.5565, 42.5565]),
    )
    assert_allclose(
        params.stomata.r_d_func(t_l),
        np.array([4.8488048999784479e-07, 1.4861206096092957e-06]),
    )
    assert_allclose(
        params.allocation.r_m_sw_func(t_l),
        np.array([2.20e-12, 3.96e-12]),
    )
    assert_allclose(
        params.allocation.r_m_r_func(t_l),
        np.array([7.000e-09, 1.386e-08]),
    )
