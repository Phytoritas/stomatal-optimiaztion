from __future__ import annotations

import numpy as np
import pytest

from stomatal_optimiaztion.domains.gosm import implemented_equations
from stomatal_optimiaztion.domains.gosm.model import leaf_area_index
from stomatal_optimiaztion.domains.gosm.params import BaselineInputs


def test_leaf_area_index_has_equation_tag() -> None:
    assert implemented_equations(leaf_area_index) == ("Eq.S3.LAI",)


def test_leaf_area_index_matches_baseline_snapshot() -> None:
    defaults = BaselineInputs.matlab_default()

    result = leaf_area_index(la=defaults.la, phi_l=defaults.phi_l, w=defaults.w)

    assert result == pytest.approx(0.4)


def test_leaf_area_index_supports_vector_inputs() -> None:
    result = leaf_area_index(la=np.array([2.0, 4.0]), phi_l=0.25, w=2.0)

    assert np.allclose(result, np.array([2.0, 4.0]))
