from __future__ import annotations

import math

import numpy as np
import pytest

from stomatal_optimiaztion.domains.gosm.utils import polylog2


def test_polylog2_matches_known_scalar_values() -> None:
    assert polylog2(0.0) == pytest.approx(0.0)
    assert polylog2(1.0) == pytest.approx(math.pi**2 / 6)
    assert polylog2(-1.0) == pytest.approx(-(math.pi**2) / 12)


def test_polylog2_supports_vector_inputs() -> None:
    result = polylog2(np.array([0.0, 1.0]))

    assert np.allclose(result, np.array([0.0, math.pi**2 / 6]))
