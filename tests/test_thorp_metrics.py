import numpy as np
from numpy.testing import assert_allclose

from stomatal_optimiaztion.domains.thorp.metrics import (
    BiomassFractionSeries,
    HuberValueParams,
    HuberValueSeries,
    RootingDepthSeries,
    biomass_fractions,
    huber_value,
    rooting_depth,
    soil_grid,
)
from stomatal_optimiaztion.domains.thorp.soil_hydraulics import SoilHydraulics
from stomatal_optimiaztion.domains.thorp.soil_initialization import (
    SoilGrid,
    SoilInitializationParams,
    initial_soil_and_roots,
)
from stomatal_optimiaztion.domains.thorp.vulnerability import WeibullVC


def _series() -> BiomassFractionSeries:
    return BiomassFractionSeries(
        c_l_ts=np.array([10.0, 20.0, 30.0]),
        c_sw_ts=np.array([50.0, 60.0, 70.0]),
        c_hw_ts=np.array([20.0, 30.0, 40.0]),
        c_r_h_by_layer_ts=np.array(
            [
                [5.0, 6.0, 7.0],
                [8.0, 9.0, 10.0],
            ]
        ),
        c_r_v_by_layer_ts=np.array(
            [
                [2.0, 3.0, 4.0],
                [1.0, 2.0, 3.0],
            ]
        ),
    )


def _rooting_grid() -> SoilGrid:
    return SoilGrid(
        dz=np.array([0.1, 0.2, 0.3, 0.4]),
        z_bttm=np.array([0.1, 0.3, 0.6, 1.0]),
        z_mid=np.array([0.05, 0.2, 0.45, 0.8]),
        dz_c=np.array([0.05, 0.15, 0.25, 0.35, 0.2]),
    )


def _rooting_series() -> RootingDepthSeries:
    return RootingDepthSeries(
        c_r_h_by_layer_ts=np.array(
            [
                [0.3, 0.90, 0.0, 0.10],
                [0.2, 0.01, 0.0, 0.20],
                [0.05, 0.005, 0.0, 0.25],
                [0.05, 0.005, 0.0, 0.00],
            ]
        ),
        c_r_v_by_layer_ts=np.array(
            [
                [0.2, 0.06, 0.0, 0.10],
                [0.1, 0.01, 0.0, 0.20],
                [0.05, 0.005, 0.0, 0.10],
                [0.05, 0.005, 0.0, 0.05],
            ]
        ),
    )


def _soil_params() -> SoilInitializationParams:
    return SoilInitializationParams(
        rho=998.0,
        g=9.81,
        z_wt=74.0,
        z_soil=30.0,
        n_soil=15,
        bc_bttm="FreeDrainage",
        soil=SoilHydraulics(
            n_vg=2.70,
            alpha_vg=1.4642,
            l_vg=0.5,
            e_z_n=13.6,
            e_z_k_s_sat=3.2,
        ),
        vc_r=WeibullVC(b=1.2949, c=2.6471),
        beta_r_h=3388.15038831676,
        beta_r_v=941.1528856435444,
    )


def test_biomass_fractions_matches_legacy_snapshot() -> None:
    res = biomass_fractions(series=_series())

    assert_allclose(
        res.lmf,
        np.array([0.1057692307692308, 0.1560283687943262, 0.1853932584269663]),
    )
    assert_allclose(
        res.smf,
        np.array([0.7403846153846154, 0.7021276595744681, 0.6797752808988764]),
    )
    assert_allclose(
        res.rmf,
        np.array([0.1538461538461538, 0.1418439716312057, 0.1348314606741573]),
    )


def test_biomass_fractions_zero_total_matches_legacy_behavior() -> None:
    res = biomass_fractions(
        series=BiomassFractionSeries(
            c_l_ts=np.zeros(2),
            c_sw_ts=np.zeros(2),
            c_hw_ts=np.zeros(2),
            c_r_h_by_layer_ts=np.zeros((2, 2)),
            c_r_v_by_layer_ts=np.zeros((2, 2)),
        )
    )

    assert np.isnan(res.lmf).all()
    assert np.isnan(res.smf).all()
    assert np.isnan(res.rmf).all()


def test_biomass_fractions_supports_custom_carbon_fractions() -> None:
    res = biomass_fractions(
        series=_series(),
        leaf_c_fraction=0.4,
        wood_c_fraction=0.45,
        root_c_fraction=0.6,
    )

    assert_allclose(
        res.lmf,
        np.array([0.1206434316353888, 0.1764705882352941, 0.2086553323029366]),
    )
    assert_allclose(
        res.smf,
        np.array([0.7506702412868633, 0.7058823529411765, 0.6800618238021637]),
    )
    assert_allclose(
        res.rmf,
        np.array([0.128686327077748, 0.1176470588235294, 0.1112828438948995]),
    )


def test_huber_value_matches_legacy_snapshot() -> None:
    res = huber_value(
        series=HuberValueSeries(
            c_l_ts=np.array([10.0, 20.0, 25.0]),
            d_ts=np.array([0.30, 0.45, 0.50]),
            d_hw_ts=np.array([0.10, 0.20, 0.25]),
        ),
        params=HuberValueParams(sla=0.08, xi=0.5),
    )

    assert_allclose(res, np.array([0.05, 0.05078125, 0.046875]))


def test_huber_value_zero_leaf_area_matches_legacy_behavior() -> None:
    res = huber_value(
        series=HuberValueSeries(
            c_l_ts=np.array([0.0, 5.0, 0.0]),
            d_ts=np.array([0.2, 0.3, 0.0]),
            d_hw_ts=np.array([0.0, 0.1, 0.0]),
        ),
        params=HuberValueParams(sla=0.08, xi=0.5),
    )

    assert np.isinf(res[0])
    assert_allclose(res[1], 0.1)
    assert np.isnan(res[2])


def test_rooting_depth_matches_legacy_snapshot() -> None:
    res = rooting_depth(
        series=_rooting_series(),
        grid=_rooting_grid(),
        percentile=0.95,
    )

    assert_allclose(res[:2], np.array([1.0, 0.1]))
    assert np.isnan(res[2])
    assert_allclose(res[3:], np.array([0.6]))


def test_rooting_depth_supports_alternate_percentile() -> None:
    res = rooting_depth(
        series=_rooting_series(),
        grid=_rooting_grid(),
        percentile=0.5,
    )

    assert_allclose(res[:2], np.array([0.1, 0.1]))
    assert np.isnan(res[2])
    assert_allclose(res[3:], np.array([0.3]))


def test_rooting_depth_zero_total_matches_legacy_behavior() -> None:
    res = rooting_depth(
        series=RootingDepthSeries(
            c_r_h_by_layer_ts=np.zeros((3, 2)),
            c_r_v_by_layer_ts=np.zeros((3, 2)),
        ),
        grid=SoilGrid(
            dz=np.array([0.2, 0.3, 0.5]),
            z_bttm=np.array([0.2, 0.5, 1.0]),
            z_mid=np.array([0.1, 0.35, 0.75]),
            dz_c=np.array([0.1, 0.25, 0.4, 0.25]),
        ),
        percentile=0.95,
    )

    assert np.isnan(res).all()


def test_rooting_depth_invalid_percentile_raises() -> None:
    try:
        rooting_depth(
            series=_rooting_series(),
            grid=_rooting_grid(),
            percentile=0.0,
        )
    except ValueError as exc:
        assert "percentile" in str(exc)
    else:
        raise AssertionError("rooting_depth should reject percentile <= 0")


def test_soil_grid_matches_legacy_snapshot() -> None:
    grid = soil_grid(params=_soil_params())

    assert_allclose(
        grid.dz,
        np.array(
            [
                0.09966816,
                0.13654095,
                0.18705502,
                0.25625706,
                0.35106077,
                0.48093763,
                0.65886316,
                0.90261322,
                1.23653995,
                1.69400471,
                2.32071109,
                3.17927095,
                4.35545976,
                5.96678609,
                8.17423149,
            ]
        ),
        rtol=1e-7,
    )
    assert_allclose(
        grid.z_bttm,
        np.array(
            [
                0.09966816,
                0.23620911,
                0.42326413,
                0.67952119,
                1.03058196,
                1.51151959,
                2.17038275,
                3.07299597,
                4.30953592,
                6.00354063,
                8.32425172,
                11.50352267,
                15.85898243,
                21.82576851,
                30.0,
            ]
        ),
        rtol=1e-7,
    )
    assert grid.n_soil == 15


def test_soil_grid_matches_migrated_initialization_behavior() -> None:
    grid = soil_grid(params=_soil_params())
    init = initial_soil_and_roots(params=_soil_params(), c_r_i=5.0, z_i=3.0)

    assert_allclose(grid.dz, init.grid.dz)
    assert_allclose(grid.z_bttm, init.grid.z_bttm)
    assert_allclose(grid.z_mid, init.grid.z_mid)
    assert_allclose(grid.dz_c, init.grid.dz_c)
