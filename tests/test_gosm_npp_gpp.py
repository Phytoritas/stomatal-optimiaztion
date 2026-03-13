from __future__ import annotations

import numpy as np
import pytest

from stomatal_optimiaztion.domains.gosm import implemented_equations
from stomatal_optimiaztion.domains.gosm.model import (
    steady_state_npp_gpp_ratio,
    target_npp_gpp_ratio,
)
from stomatal_optimiaztion.domains.gosm.params import BaselineInputs


def test_target_npp_gpp_ratio_has_equation_tag_and_constant_value() -> None:
    assert implemented_equations(target_npp_gpp_ratio) == ("Eq.S8.1",)
    assert target_npp_gpp_ratio() == pytest.approx(0.45)


def test_steady_state_npp_gpp_ratio_has_equation_tag_and_matches_snapshot() -> None:
    defaults = BaselineInputs.matlab_default()

    result = steady_state_npp_gpp_ratio(G=1.0, R_M=0.5, f_c=defaults.f_c)

    assert implemented_equations(steady_state_npp_gpp_ratio) == ("Eq.S8.2",)
    assert result == pytest.approx(0.5294117647058824)


def test_steady_state_npp_gpp_ratio_supports_vector_inputs() -> None:
    result = steady_state_npp_gpp_ratio(G=np.array([1.0, 2.0]), R_M=np.array([0.5, 0.25]), f_c=0.2)

    assert np.allclose(result, np.array([0.5714285714285714, 0.7272727272727273]))


def test_steady_state_npp_gpp_ratio_handles_zero_growth_without_crashing() -> None:
    result = steady_state_npp_gpp_ratio(G=0.0, R_M=0.5, f_c=0.2)

    assert result == pytest.approx(0.0)
