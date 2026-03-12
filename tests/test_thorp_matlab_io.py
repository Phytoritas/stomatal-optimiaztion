from __future__ import annotations

import numpy as np
import pytest
from numpy.testing import assert_allclose

from stomatal_optimiaztion.domains.thorp.matlab_io import load_mat, save_mat


def test_save_mat_round_trips_legacy_like_payload(tmp_path) -> None:
    payload = {
        "t_stor": np.array([0.0, 1.0, 2.0], dtype=float),
        "A_n_stor": np.array([3.0, 4.0, 5.0], dtype=float),
        "scalar_value": 7.5,
    }
    path = tmp_path / "nested" / "thorp_data.mat"

    save_mat(path, payload)
    loaded = load_mat(path)

    assert path.exists()
    assert_allclose(np.asarray(loaded["t_stor"], dtype=float), payload["t_stor"])
    assert_allclose(np.asarray(loaded["A_n_stor"], dtype=float), payload["A_n_stor"])
    assert float(loaded["scalar_value"]) == pytest.approx(payload["scalar_value"])


def test_load_mat_raises_for_missing_file(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        load_mat(tmp_path / "missing.mat")
