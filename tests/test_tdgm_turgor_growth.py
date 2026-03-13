from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.tdgm import implemented_equations
from stomatal_optimiaztion.domains.tdgm import turgor_driven_growth_rate


def test_tdgm_turgor_growth_has_equation_tags() -> None:
    assert implemented_equations(turgor_driven_growth_rate) == ("Eq_S2.12", "Eq_S2.16")


def test_tdgm_turgor_growth_matches_scalar_snapshot() -> None:
    result = turgor_driven_growth_rate(
        psi_s=-0.2,
        psi_rc=-0.05,
        phi=2e-6,
        p_turgor_crit=0.4,
        u_sw=0.7,
        c_sw=12.0,
        c_hw=4.0,
        rho_w=998.0,
        r_gas=8.314,
        t_a=20.0,
        a=0.75,
        b=2.0,
    )

    assert np.isclose(float(result.reshape(())), 5.780929536528866e-05)


def test_tdgm_turgor_growth_vectorizes() -> None:
    result = turgor_driven_growth_rate(
        psi_s=np.array([-0.2, -0.25]),
        psi_rc=np.array([-0.05, -0.1]),
        phi=2e-6,
        p_turgor_crit=0.4,
        u_sw=np.array([0.7, 0.8]),
        c_sw=np.array([12.0, 10.0]),
        c_hw=np.array([4.0, 5.0]),
        rho_w=998.0,
        r_gas=8.314,
        t_a=np.array([20.0, 22.0]),
        a=0.75,
        b=2.0,
    )

    assert result.shape == (2,)
    assert np.all(result > 0)
