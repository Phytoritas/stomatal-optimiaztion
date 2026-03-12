from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from netCDF4 import Dataset
from numpy.testing import assert_allclose

from stomatal_optimiaztion.domains.thorp.forcing import Forcing, load_forcing
from stomatal_optimiaztion.domains.thorp.params import thorp_params_from_defaults


def _write_forcing_file(tmp_path: Path, raw: np.ndarray) -> Path:
    path = tmp_path / "forcing.nc"
    with Dataset(path, "w") as ds:
        ds.createDimension("row", raw.shape[0])
        ds.createDimension("col", raw.shape[1])
        data = ds.createVariable("data", "f8", ("row", "col"))
        data[:] = raw
    return path


def test_load_forcing_matches_legacy_scaling_and_angle_snapshot(tmp_path: Path) -> None:
    raw = np.array(
        [
            [10.0, 11.0, 0.1, -0.2, 100.0, 1.0],
            [20.0, 21.0, 0.2, 0.5, 200.0, 2.0],
            [30.0, 31.0, 0.3, 1.2, 300.0, 3.0],
            [40.0, 41.0, 0.4, 0.75, 400.0, 4.0],
        ],
        dtype=float,
    )
    path = _write_forcing_file(tmp_path, raw)
    params = thorp_params_from_defaults(
        forcing_path=path,
        forcing_repeat_q=2,
        forcing_rh_scale=0.5,
        forcing_precip_scale=10.0,
    )

    forcing = load_forcing(params=params)

    assert isinstance(forcing, Forcing)
    assert_allclose(forcing.t, np.arange(8, dtype=float) * params.dt)
    assert forcing.t_end == 7 * params.dt
    assert_allclose(forcing.t_a, np.array([10.0, 20.0, 30.0, 40.0, 10.0, 20.0, 30.0, 40.0]))
    assert_allclose(forcing.t_soil, np.array([11.0, 21.0, 31.0, 41.0, 11.0, 21.0, 31.0, 41.0]))
    assert_allclose(forcing.precip, np.array([1.0, 2.0, 3.0, 4.0, 1.0, 2.0, 3.0, 4.0]))
    assert_allclose(forcing.rh, np.array([0.0, 0.25, 0.5, 0.375, 0.0, 0.25, 0.5, 0.375]))
    assert_allclose(forcing.r_incom, np.array([100.0, 200.0, 300.0, 400.0, 100.0, 200.0, 300.0, 400.0]))
    assert_allclose(forcing.u10, np.array([1.0, 2.0, 3.0, 4.0, 1.0, 2.0, 3.0, 4.0]))
    assert_allclose(
        forcing.z_a,
        np.array(
            [
                -0.84421881,
                0.23168149,
                0.23194362,
                -0.84365458,
                -0.84345739,
                0.23276741,
                0.23305446,
                -0.84283848,
            ]
        ),
        rtol=1e-7,
        atol=1e-8,
    )


def test_load_forcing_accepts_transposed_legacy_shape(tmp_path: Path) -> None:
    raw = np.array(
        [
            [10.0, 11.0, 0.1, 0.2, 100.0, 1.0],
            [20.0, 21.0, 0.2, 0.3, 200.0, 2.0],
            [30.0, 31.0, 0.3, 0.4, 300.0, 3.0],
            [40.0, 41.0, 0.4, 0.5, 400.0, 4.0],
        ],
        dtype=float,
    )
    path = _write_forcing_file(tmp_path, raw.T)
    params = thorp_params_from_defaults(forcing_path=path, forcing_repeat_q=1)

    forcing = load_forcing(params=params)

    assert_allclose(forcing.t_a, raw[:, 0])
    assert_allclose(forcing.t_soil, raw[:, 1])
    assert_allclose(forcing.precip, raw[:, 2])
    assert_allclose(forcing.rh, raw[:, 3] * params.forcing_rh_scale)
    assert_allclose(forcing.r_incom, raw[:, 4])
    assert_allclose(forcing.u10, raw[:, 5])


def test_load_forcing_truncates_before_repeat(tmp_path: Path) -> None:
    n = 14605
    idx = np.arange(n, dtype=float)
    raw = np.column_stack(
        [
            idx,
            idx + 0.1,
            idx + 0.2,
            np.full(n, 0.5, dtype=float),
            idx + 0.4,
            idx + 0.5,
        ]
    )
    path = _write_forcing_file(tmp_path, raw)
    params = thorp_params_from_defaults(forcing_path=path, forcing_repeat_q=2, forcing_rh_scale=1.0)

    forcing = load_forcing(params=params)

    assert forcing.t.size == 29200
    assert_allclose(forcing.t_a[:3], np.array([0.0, 1.0, 2.0]))
    assert_allclose(forcing.t_a[14598:14602], np.array([14598.0, 14599.0, 0.0, 1.0]))
    assert_allclose(forcing.t_a[-2:], np.array([14598.0, 14599.0]))


def test_load_forcing_missing_file_raises() -> None:
    params = thorp_params_from_defaults(forcing_path=Path("does-not-exist.nc"))

    with pytest.raises(FileNotFoundError, match="Forcing netCDF file not found"):
        load_forcing(params=params)


def test_load_forcing_rejects_invalid_shape(tmp_path: Path) -> None:
    raw = np.arange(36, dtype=float).reshape(6, 6)
    path = _write_forcing_file(tmp_path, raw)
    params = thorp_params_from_defaults(forcing_path=path)

    with pytest.raises(ValueError, match="Expected forcing with 6 variables"):
        load_forcing(params=params)
