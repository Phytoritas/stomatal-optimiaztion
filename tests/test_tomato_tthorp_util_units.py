from __future__ import annotations

import math

import pytest

from stomatal_optimiaztion.domains.tomato.tthorp.core import (
    PAR_UMOL_PER_W_M2,
    PAR_UMOL_PER_WM2,
    par_umol_to_w_m2,
    w_m2_to_par_umol,
)


def test_par_conversion_alias_constants_match() -> None:
    assert PAR_UMOL_PER_WM2 == pytest.approx(4.6)
    assert PAR_UMOL_PER_W_M2 == PAR_UMOL_PER_WM2


def test_par_conversion_round_trip_is_stable() -> None:
    par_umol = 345.0

    w_m2 = par_umol_to_w_m2(par_umol)
    recovered = w_m2_to_par_umol(w_m2)

    assert math.isfinite(w_m2)
    assert recovered == pytest.approx(par_umol)


def test_par_conversion_rejects_invalid_factor() -> None:
    with pytest.raises(ValueError, match="positive finite value"):
        w_m2_to_par_umol(100.0, par_umol_per_w_m2=0.0)
