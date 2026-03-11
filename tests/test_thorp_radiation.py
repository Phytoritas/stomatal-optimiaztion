from __future__ import annotations

import math

from stomatal_optimiaztion.domains.thorp.implements import implemented_equations
from stomatal_optimiaztion.domains.thorp.radiation import radiation


def test_radiation_exposes_expected_equation_ids() -> None:
    assert implemented_equations(radiation) == (
        "E_S5_1",
        "E_S5_2",
        "E_S5_3",
        "E_S5_4",
        "E_S5_5",
    )


def test_radiation_matches_legacy_snapshot() -> None:
    result = radiation(
        r_incom=800.0,
        z_a=0.3,
        la=2.4,
        w=1.8,
        h=8.0,
        h_n=10.5,
        kappa_l=0.32,
        kappa_n=0.1,
        phi=3.34,
    )

    assert math.isclose(result.r_abs, 56.86073993568384, rel_tol=1e-12)
    assert math.isclose(result.r_soil, 546.1780798310609, rel_tol=1e-12)
    assert math.isclose(result.d_r_abs_dh, 5.951907059231765, rel_tol=1e-12)
    assert math.isclose(result.d_r_abs_dw, 2.317625366923824, rel_tol=1e-12)
    assert math.isclose(result.d_r_abs_dla, -0.869109512596434, rel_tol=1e-12)


def test_radiation_handles_extreme_solar_angles() -> None:
    result = radiation(
        r_incom=500.0,
        z_a=10.0,
        la=1.0,
        w=1.0,
        h=10.0,
        h_n=0.0,
        kappa_l=0.32,
        kappa_n=0.1,
        phi=3.34,
    )

    assert math.isfinite(result.r_abs)
    assert math.isfinite(result.r_soil)
    assert result.r_abs >= 0.0
    assert result.r_soil >= 0.0
    assert result.d_r_abs_dh == 0.0
