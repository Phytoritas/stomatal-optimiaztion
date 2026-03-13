from __future__ import annotations

import math

import pytest

from stomatal_optimiaztion.domains.gosm import implemented_equations
from stomatal_optimiaztion.domains.gosm.model import radiation_absorbed
from stomatal_optimiaztion.domains.gosm.params import BaselineInputs


def test_radiation_absorbed_has_equation_tag() -> None:
    assert implemented_equations(radiation_absorbed) == ("Eq.S3.2",)


def test_radiation_absorbed_matches_baseline_snapshot() -> None:
    defaults = BaselineInputs.matlab_default()

    result = radiation_absorbed(
        r_incom=defaults.r_incom,
        z_a=defaults.z_a,
        la=defaults.la,
        w=defaults.w,
        kappa_l=defaults.kappa_l,
        phi_l=defaults.phi_l,
    )

    assert result == pytest.approx(81.40834442605605)


def test_radiation_absorbed_clamps_zenith_angle() -> None:
    defaults = BaselineInputs.matlab_default()

    clamped = radiation_absorbed(
        r_incom=defaults.r_incom,
        z_a=math.pi,
        la=defaults.la,
        w=defaults.w,
        kappa_l=defaults.kappa_l,
        phi_l=defaults.phi_l,
    )
    edge = radiation_absorbed(
        r_incom=defaults.r_incom,
        z_a=math.pi / 2,
        la=defaults.la,
        w=defaults.w,
        kappa_l=defaults.kappa_l,
        phi_l=defaults.phi_l,
    )

    assert clamped == pytest.approx(edge)


def test_radiation_absorbed_rejects_negative_leaf_absorbed_radiation() -> None:
    defaults = BaselineInputs.matlab_default()

    with pytest.raises(ValueError, match="NEGATIVE LEAF-ABSORBED RADIATION"):
        radiation_absorbed(
            r_incom=-100.0,
            z_a=defaults.z_a,
            la=defaults.la,
            w=defaults.w,
            kappa_l=defaults.kappa_l,
            phi_l=defaults.phi_l,
        )
