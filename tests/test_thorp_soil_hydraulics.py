from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.thorp.implements import implemented_equations
from stomatal_optimiaztion.domains.thorp.soil_hydraulics import SoilHydraulics


def test_soil_hydraulics_methods_expose_expected_equation_ids() -> None:
    assert implemented_equations(SoilHydraulics.vwc_sat) == ("E_S2_8",)
    assert implemented_equations(SoilHydraulics.k_s_sat) == ("E_S2_7",)
    assert implemented_equations(SoilHydraulics.s_e) == ("E_S2_6",)
    assert implemented_equations(SoilHydraulics.vwc) == ("E_S2_5",)
    assert implemented_equations(SoilHydraulics.k_s) == ("E_S2_4",)


def test_soil_hydraulics_matches_legacy_snapshot() -> None:
    soil = SoilHydraulics(
        n_vg=2.70,
        alpha_vg=1.4642,
        l_vg=0.5,
        e_z_n=13.6,
        e_z_k_s_sat=3.2,
    )
    z = np.array([0.5, 2.0, 5.0], dtype=float)
    psi_soil = np.array([-0.2, -0.8, -1.5], dtype=float)

    np.testing.assert_allclose(
        soil.vwc_sat(z),
        np.array([0.38556116, 0.34529728, 0.2769446], dtype=float),
        rtol=1e-8,
    )
    np.testing.assert_allclose(
        soil.k_s_sat(z),
        np.array([5.13207196e-07, 3.21156857e-07, 1.25766832e-07], dtype=float),
        rtol=1e-8,
    )
    np.testing.assert_allclose(
        soil.s_e(psi_soil),
        np.array([0.97779986, 0.55704347, 0.24448533], dtype=float),
        rtol=1e-8,
    )
    np.testing.assert_allclose(
        soil.vwc(psi_soil, z),
        np.array([0.37700165, 0.19234559, 0.06770889], dtype=float),
        rtol=1e-7,
    )
    np.testing.assert_allclose(
        soil.k_s(psi_soil, z),
        np.array([3.91915618e-07, 1.76176814e-08, 2.92783857e-10], dtype=float),
        rtol=1e-7,
    )


def test_soil_hydraulics_k_soil_alias_matches_k_s() -> None:
    soil = SoilHydraulics(
        n_vg=2.70,
        alpha_vg=1.4642,
        l_vg=0.5,
        e_z_n=13.6,
        e_z_k_s_sat=3.2,
    )
    z = np.array([0.5, 2.0, 5.0], dtype=float)
    psi_soil_by_layer = np.array([-0.2, -0.8, -1.5], dtype=float)

    np.testing.assert_allclose(soil.k_soil(psi_soil_by_layer, z), soil.k_s(psi_soil_by_layer, z))
