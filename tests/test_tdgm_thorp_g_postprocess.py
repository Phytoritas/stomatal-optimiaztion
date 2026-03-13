from __future__ import annotations

from pathlib import Path

import numpy as np
from netCDF4 import Dataset
from scipy.io import savemat

from stomatal_optimiaztion.domains import tdgm


def test_load_thorp_g_mat_outputs_reads_expected_arrays(tmp_path: Path) -> None:
    path = tmp_path / "thorp_g.mat"
    savemat(
        path,
        {
            "t_stor": np.array([[0.0, 21600.0, 43200.0]]),
            "c_NSC_stor": np.array([[100.0, 101.0, 102.0]]),
            "c_l_stor": np.array([[2.0, 2.1, 2.2]]),
            "c_sw_stor": np.array([[10.0, 10.0, 10.0]]),
            "c_hw_stor": np.array([[1.0, 1.0, 1.0]]),
            "c_r_H_stor": np.array([[1.0, 1.1, 1.2], [1.5, 1.6, 1.7]]),
            "c_r_V_stor": np.array([[0.5, 0.6, 0.7], [0.25, 0.3, 0.35]]),
            "u_l_stor": np.array([[0.1, 0.1, 0.1]]),
            "u_sw_stor": np.array([[0.2, 0.2, 0.2]]),
            "u_r_H_stor": np.array([[0.3, 0.3, 0.3]]),
            "u_r_V_stor": np.array([[0.4, 0.4, 0.4]]),
            "U_stor": np.array([[0.5, 0.6, 0.7]]),
            "P_x_s_stor": np.array([[-0.5, -0.6, -0.7]]),
            "P_x_r_stor": np.array([[-0.4, -0.5, -0.6]]),
        },
    )

    loaded = tdgm.load_thorp_g_mat_outputs(path=path)

    assert loaded.t_ts.shape == (3,)
    assert loaded.c_r_h_by_layer_ts.shape == (2, 3)
    np.testing.assert_allclose(loaded.psi_s_ts, np.array([-0.5, -0.6, -0.7]))


def test_forcing_t_a_at_times_tiles_and_aligns_indices(tmp_path: Path) -> None:
    forcing_path = tmp_path / "forcing.nc"
    with Dataset(forcing_path, "w") as ds:
        ds.createDimension("var", 6)
        ds.createDimension("time", 4)
        data = ds.createVariable("data", "f8", ("var", "time"))
        data[:] = np.array(
            [
                [10.0, 11.0, 12.0, 13.0],
                [5.0, 5.0, 5.0, 5.0],
                [0.0, 0.1, 0.2, 0.3],
                [0.4, 0.5, 0.6, 0.7],
                [0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0],
            ]
        )

    t_a_ts = tdgm.forcing_t_a_at_times(
        forcing_path=forcing_path,
        t_ts=np.array([0.0, 21600.0, 43200.0, 64800.0, 86400.0]),
        n_years_chunk=1,
    )

    np.testing.assert_allclose(t_a_ts, np.array([10.0, 11.0, 12.0, 13.0, 10.0]))


def test_temperature_and_phloem_helpers_preserve_threshold_branches() -> None:
    u_mod_t = tdgm.temperature_limitation_growth(t_a_c=np.array([6.0, 7.0, 20.0]))
    assert u_mod_t[0] == 0.0
    assert 0.0 < u_mod_t[1] < u_mod_t[2] < 1.0

    c_p = tdgm.phloem_sucrose_concentration_from_psi_s(psi_s=np.array([-0.5, -1.0]))
    assert c_p[1] > c_p[0] > 0.0


def test_postprocess_thorp_g_coupling_reconstructs_realized_growth() -> None:
    thorp = tdgm.ThorpGMatOutputs(
        t_ts=np.array([0.0, 21600.0, 43200.0]),
        c_nsc_ts=np.array([20000.0, 20010.0, 20020.0]),
        c_l_ts=np.array([2.0, 2.0, 2.0]),
        c_sw_ts=np.array([10.0, 10.0, 10.0]),
        c_hw_ts=np.array([1.0, 1.0, 1.0]),
        c_r_h_by_layer_ts=np.array([[1.0, 1.0, 1.0], [1.0, 1.0, 1.0]]),
        c_r_v_by_layer_ts=np.array([[0.5, 0.5, 0.5], [0.5, 0.5, 0.5]]),
        u_l_opt_ts=np.array([0.1, 0.1, 0.1]),
        u_sw_opt_ts=np.array([0.2, 0.2, 0.2]),
        u_r_h_opt_ts=np.array([0.3, 0.3, 0.3]),
        u_r_v_opt_ts=np.array([0.4, 0.4, 0.4]),
        u_unloading_ts=np.array([0.1, 0.2, 0.3]),
        psi_s_ts=np.array([-0.5, -0.6, -0.7]),
        psi_rc_ts=np.array([-0.4, -0.5, -0.6]),
    )

    outputs = tdgm.postprocess_thorp_g_coupling(thorp=thorp, t_a_ts=np.array([6.0, 10.0, 20.0]))

    assert outputs.tree_volume_ts.shape == thorp.t_ts.shape
    assert np.all(outputs.tree_volume_ts > 0.0)
    assert outputs.u_mod_t_ts[0] == 0.0
    assert outputs.g_potential_ts[0] == 0.0
    np.testing.assert_allclose(outputs.g_rate_from_eq_ts[1:], outputs.g_rate_ts[1:])
