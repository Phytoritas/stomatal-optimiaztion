from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.thorp.defaults import default_params
from stomatal_optimiaztion.domains.thorp.hydraulics import (
    RootUptakeParams,
    StomataParams,
    stomata,
)
from stomatal_optimiaztion.domains.thorp.implements import implemented_equations
from stomatal_optimiaztion.domains.thorp.soil_initialization import (
    SoilInitializationParams,
    initial_soil_and_roots,
)


def _legacy_default_like_initialization_params() -> SoilInitializationParams:
    return default_params().soil_initialization


def _root_uptake_params() -> RootUptakeParams:
    return default_params().root_uptake


def _stomata_params() -> StomataParams:
    return default_params().stomata


def test_stomata_exposes_expected_equation_ids() -> None:
    assert implemented_equations(stomata) == (
        "E_S3_6",
        "E_S3_7",
        "E_S3_10",
        "E_S3_8",
        "E_S3_9",
        "E_S3_25",
        "E_S3_26",
        "E_S3_27",
        "E_S3_32",
        "E_S3_33",
        "E_S3_34",
        "E_S3_42",
        "E_S3_49_to_55_raw",
        "E_S4_7",
        "E_S4_8",
        "E_S6_1",
        "E_S6_2",
        "E_S6_3",
        "E_S6_4",
        "E_S6_5",
        "E_S6_6",
        "E_S6_7",
        "E_S6_8",
        "E_S6_9",
        "E_S6_10",
        "E_S6_11",
        "E_S6_12",
        "E_S6_13",
        "E_S6_14",
        "E_S6_15",
        "E_S6_16",
    )


def test_stomata_matches_legacy_snapshot() -> None:
    init = initial_soil_and_roots(
        params=_legacy_default_like_initialization_params(),
        c_r_i=1.0,
        z_i=3.0,
    )

    res = stomata(
        params=_stomata_params(),
        psi_soil_by_layer=init.psi_soil_by_layer,
        n_soil=init.grid.n_soil,
        dz=init.grid.dz,
        z_soil_mid=init.grid.z_mid,
        t_a=23.0,
        rh=0.58,
        r_abs=290.0e-6,
        la=2.8,
        c_r_h=init.c_r_h,
        c_r_v=init.c_r_v,
        h=10.5,
        w=3.535976267996335,
        d=0.7842320847301608,
        d_hw=0.64,
        d_r_abs_d_h=1.1e-5,
        d_r_abs_d_w=-8.2e-6,
        d_r_abs_d_la=2.6e-5,
    )

    assert np.isclose(res.psi_l, -0.8274980142031351, rtol=1e-9)
    assert np.isclose(res.psi_s, -0.827496735626728, rtol=1e-9)
    assert np.isclose(res.psi_rc, -0.7246973862303405, rtol=1e-9)
    assert np.isclose(res.psi_rc0, -0.7246973862303405, rtol=1e-9)
    assert np.isclose(res.e, 7.703644892834487e-09, rtol=1e-9)
    assert np.isclose(res.a_n, -1.219418508959284e-06, rtol=1e-9)
    assert np.isclose(res.r_d, 1.195083222945812e-06, rtol=1e-9)
    assert np.isclose(res.t_l, 23.0, rtol=1e-9)
    assert np.isclose(res.g_w, 6.541808390458893e-09, rtol=1e-9)
    assert np.isclose(res.lambda_wue, 0.0, rtol=1e-9)
    assert np.isclose(res.d_a_n_d_r_abs, 2.2817941489360647e-11, rtol=1e-9)
    assert np.isclose(res.d_e_d_la, -2.7445713912098153e-09, rtol=1e-9)
    assert np.isclose(res.d_e_d_d, -3.397358164138639e-06, rtol=1e-9)
    np.testing.assert_allclose(
        res.e_soil,
        np.array(
            [
                1.432971136938e-09,
                1.392441640715e-09,
                1.344244541986e-09,
                1.255507471463e-09,
                1.057259277751e-09,
                7.150174988668e-10,
                3.576286164287e-10,
                1.214402756633e-10,
                2.456715289698e-11,
                2.468889989690e-12,
                9.727299340486e-14,
                1.114614399939e-15,
                2.526855860153e-18,
                6.692746635160e-22,
                9.881711826538e-27,
            ],
            dtype=float,
        ),
        rtol=1e-9,
    )
    np.testing.assert_allclose(
        res.d_e_d_c_r_h,
        np.array(
            [
                7.878613638396e-09,
                7.887221289823e-09,
                7.898989164590e-09,
                7.915065047779e-09,
                7.937002447692e-09,
                7.966897118722e-09,
                8.007542246888e-09,
                8.062645841691e-09,
                8.137038074135e-09,
                8.236864632324e-09,
                8.369638552822e-09,
                8.543907276974e-09,
                8.768029978072e-09,
                9.047107191441e-09,
                9.705827166129e-09,
            ],
            dtype=float,
        ),
        rtol=1e-9,
    )
    np.testing.assert_allclose(
        res.d_e_d_c_r_v,
        np.array(
            [
                6.960067286759e-06,
                3.960978855595e-08,
                2.548304961295e-08,
                2.619226573405e-08,
                3.541508668020e-08,
                4.314971183106e-08,
                3.883815009087e-08,
                2.917278094764e-08,
                1.981111453478e-08,
                1.242192501561e-08,
                7.250790690462e-09,
                3.997758129529e-09,
                2.127873356901e-09,
                1.113954269321e-09,
                5.252315315750e-10,
            ],
            dtype=float,
        ),
        rtol=1e-9,
    )


def test_stomata_low_radiation_matches_legacy_snapshot() -> None:
    init = initial_soil_and_roots(
        params=_legacy_default_like_initialization_params(),
        c_r_i=1.0,
        z_i=3.0,
    )

    res = stomata(
        params=_stomata_params(),
        psi_soil_by_layer=init.psi_soil_by_layer,
        n_soil=init.grid.n_soil,
        dz=init.grid.dz,
        z_soil_mid=init.grid.z_mid,
        t_a=18.0,
        rh=0.99,
        r_abs=1.0e-9,
        la=2.8,
        c_r_h=init.c_r_h,
        c_r_v=init.c_r_v,
        h=10.5,
        w=3.535976267996335,
        d=0.7842320847301608,
        d_hw=0.64,
        d_r_abs_d_h=0.0,
        d_r_abs_d_w=0.0,
        d_r_abs_d_la=0.0,
    )

    assert np.isclose(res.g_w, 3.7401253245854565e-07, rtol=1e-9)
    assert np.isclose(res.a_n, -6.978034670863326e-07, rtol=1e-9)
    assert np.isclose(res.lambda_wue, 0.0, rtol=1e-9)
    assert np.isclose(res.psi_l, -0.8274980142031351, rtol=1e-9)
    assert np.isclose(res.d_a_n_d_r_abs, 2.242118058507526e-09, rtol=1e-9)
