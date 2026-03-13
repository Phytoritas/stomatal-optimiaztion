from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.gosm import BaselineInputs


def test_matlab_default_exposes_expected_scalar_defaults() -> None:
    defaults = BaselineInputs.matlab_default()

    assert defaults.sigma == 5.67e-8
    assert defaults.r_gas == 8.314
    assert defaults.c_a == 410e-6
    assert defaults.psi_soil == -0.0
    assert defaults.c_nsc == 175.0


def test_matlab_default_legacy_alias_properties_round_trip() -> None:
    defaults = BaselineInputs.matlab_default()

    assert defaults.R == defaults.r_gas
    assert defaults.C_p == defaults.c_p
    assert defaults.P_atm == defaults.p_atm
    assert defaults.c_NSC == defaults.c_nsc
    assert defaults.Gamma == defaults.p_turgor_crit
    assert defaults.P_soil == defaults.psi_soil


def test_matlab_default_callable_parameters_are_vectorized() -> None:
    defaults = BaselineInputs.matlab_default()
    temperature_vec = np.array([15.0, 25.0, 35.0])

    assert defaults.theta_g(np.array([0.0, defaults.c_nsc])).shape == (2,)
    assert defaults.theta_r(np.array([0.0, defaults.c_nsc])).shape == (2,)
    assert defaults.phi_extens_effective(temperature_vec).shape == (3,)
    assert defaults.v_cmax(temperature_vec).shape == (3,)
    assert defaults.j_max(temperature_vec).shape == (3,)
    assert defaults.gamma_star(temperature_vec).shape == (3,)
    assert defaults.k_c(temperature_vec).shape == (3,)
    assert defaults.k_o(temperature_vec).shape == (3,)
    assert defaults.r_d(temperature_vec).shape == (3,)
    assert defaults.r_m_w(temperature_vec).shape == (3,)
    assert defaults.r_m_r(temperature_vec).shape == (3,)

