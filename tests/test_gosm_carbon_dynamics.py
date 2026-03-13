from __future__ import annotations

import numpy as np
import pytest

from stomatal_optimiaztion.domains.gosm import implemented_equations
from stomatal_optimiaztion.domains.gosm.model import (
    growth_rate,
    growth_respiration,
    maintenance_respiration,
    maintenance_respiration_potential,
    nsc_rate_of_change,
    nsc_rate_of_change_full,
    sigma_nsc_limitation,
    total_respiration,
)
from stomatal_optimiaztion.domains.gosm.params import BaselineInputs


def test_sigma_nsc_limitation_has_equation_tags_and_supports_vectors() -> None:
    result = sigma_nsc_limitation(c_nsc=np.array([0.0, 10.0]), gamma=0.5, c_struct=20.0)

    assert implemented_equations(sigma_nsc_limitation) == ("Eq.S1.4", "Eq.S1.8")
    assert np.allclose(result, np.array([0.0, 0.5]))


def test_maintenance_respiration_helpers_match_baseline_snapshots() -> None:
    inputs = BaselineInputs.matlab_default()

    r_m_0 = maintenance_respiration_potential(inputs=inputs)
    r_m = maintenance_respiration(c_nsc=inputs.c_nsc, R_M_0=r_m_0, inputs=inputs)

    assert implemented_equations(maintenance_respiration_potential) == ("Eq.S1.5",)
    assert implemented_equations(maintenance_respiration) == ("Eq.S1.3",)
    assert r_m_0 == pytest.approx(5.0047343076847656e-05)
    assert r_m == pytest.approx(1.4497478364621335e-05)


def test_growth_and_respiration_helpers_match_snapshots() -> None:
    inputs = BaselineInputs.matlab_default()

    g = growth_rate(c_nsc=inputs.c_nsc, g0=0.01, inputs=inputs)
    r_g = growth_respiration(G=g, f_c=inputs.f_c)
    total = total_respiration(a_L=inputs.la, R_d=1e-6, R_M=0.001, R_G=r_g)

    assert implemented_equations(growth_rate) == ("Eq.S1.7",)
    assert implemented_equations(growth_respiration) == ("Eq.S1.6",)
    assert implemented_equations(total_respiration) == ("Eq.S1.2",)
    assert g == pytest.approx(0.003734435542593449)
    assert r_g == pytest.approx(0.0014522804887863415)
    assert total == pytest.approx(0.0024571759179647305)


def test_nsc_rate_of_change_helpers_match_snapshots() -> None:
    inputs = BaselineInputs.matlab_default()

    explicit = nsc_rate_of_change_full(a_L=inputs.la, a_n=5e-6, R_d=1e-6, G=0.002, R=0.003)
    compact = nsc_rate_of_change(inputs=inputs, c_nsc=inputs.c_nsc, a_n=5e-6, g0=0.01, R_M_0=0.0012)

    assert implemented_equations(nsc_rate_of_change_full) == ("Eq.S1.1",)
    assert implemented_equations(nsc_rate_of_change) == ("Eq.S1.9",)
    assert explicit == pytest.approx(-0.004970627424929666)
    assert compact == pytest.approx(-0.005509849227376176)
