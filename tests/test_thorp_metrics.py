import numpy as np
from numpy.testing import assert_allclose

from stomatal_optimiaztion.domains.thorp.metrics import (
    BiomassFractionSeries,
    biomass_fractions,
)


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
