from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from numpy.testing import assert_allclose

from stomatal_optimiaztion.domains.thorp.params import thorp_params_from_defaults
from stomatal_optimiaztion.domains.thorp.simulation import _Store
from stomatal_optimiaztion.domains.thorp.soil_initialization import SoilGrid


def _grid() -> SoilGrid:
    return SoilGrid(
        dz=np.array([0.2, 0.3], dtype=float),
        z_bttm=np.array([0.2, 0.5], dtype=float),
        z_mid=np.array([0.1, 0.35], dtype=float),
        dz_c=np.array([0.1, 0.25, 0.15], dtype=float),
    )


def _base_state(*, t: float, offset: float = 0.0) -> dict[str, object]:
    return {
        "t": t,
        "c_nsc": 10.0 + offset,
        "c_l": 20.0 + offset,
        "c_sw": 30.0 + offset,
        "c_hw": 40.0 + offset,
        "c_r_h": np.array([1.0 + offset, 2.0 + offset], dtype=float),
        "c_r_v": np.array([0.5 + offset, 1.5 + offset], dtype=float),
        "u_l": 50.0 + offset,
        "u_sw": 60.0 + offset,
        "u_r_h": np.array([3.0 + offset, 4.0 + offset], dtype=float),
        "u_r_v": np.array([5.0 + offset, 6.0 + offset], dtype=float),
        "d": 0.10 + offset,
        "d_hw": 0.01 + offset,
        "h": 1.0 + offset,
        "w": 0.4 + offset,
        "psi_l": -1.0 - offset,
        "psi_s": -0.8 - offset,
        "psi_rc": -0.6 - offset,
        "psi_rc0": -0.5 - offset,
        "psi_soil_by_layer": np.array([-0.3 - offset, -0.4 - offset], dtype=float),
        "r_abs": 100.0 + offset,
        "e": 0.001 + offset,
        "evap": 0.01 + offset,
        "g_w": 0.2 + offset,
        "a_n": 5.0 + offset,
        "r_d": 0.05 + offset,
        "r_m": 0.15 + offset,
        "u": 6.0 + offset,
    }


def _init_kwargs(*, t: float, offset: float = 0.0) -> dict[str, object]:
    state = _base_state(t=t, offset=offset)
    for key in ("u_l", "u_sw", "u_r_h", "u_r_v"):
        state.pop(key)
    return state


def _store_kwargs(*, t: float, offset: float = 0.0) -> dict[str, object]:
    state = _base_state(t=t, offset=offset)
    state["save_mat_path"] = None
    return state


def test_store_requires_initialize_before_maybe_store() -> None:
    params = thorp_params_from_defaults()
    store = _Store(params=params, grid=_grid(), t_bgn=0.0, t_end=float(params.dt))

    with pytest.raises(RuntimeError, match="Store not initialized"):
        store.maybe_store(**_store_kwargs(t=float(params.dt)))


def test_store_initialize_matches_legacy_zero_allocation_behavior() -> None:
    params = thorp_params_from_defaults()
    store = _Store(params=params, grid=_grid(), t_bgn=0.0, t_end=700000.0)

    store.initialize(**_init_kwargs(t=0.0))
    outputs = store.to_outputs()

    assert_allclose(outputs.t_ts, np.array([0.0]))
    assert_allclose(outputs.u_l_ts, np.array([0.0]))
    assert_allclose(outputs.u_sw_ts, np.array([0.0]))
    assert_allclose(outputs.u_r_h_ts, np.array([0.0]))
    assert_allclose(outputs.u_r_v_ts, np.array([0.0]))
    assert_allclose(outputs.c_r_h_by_layer_ts[:, 0], np.array([1.0, 2.0]))
    assert_allclose(outputs.c_r_v_by_layer_ts[:, 0], np.array([0.5, 1.5]))
    assert_allclose(outputs.psi_soil_by_layer_ts[:, 0], np.array([-0.3, -0.4]))


def test_store_maybe_store_matches_legacy_data_schedule() -> None:
    params = thorp_params_from_defaults()
    scheduled_t = 12 * 3600.0 + params.dt_sav_data
    store = _Store(params=params, grid=_grid(), t_bgn=0.0, t_end=scheduled_t + params.dt)

    store.initialize(**_init_kwargs(t=0.0))
    store.maybe_store(**_store_kwargs(t=scheduled_t, offset=1.0))
    outputs = store.to_outputs()

    assert_allclose(outputs.t_ts, np.array([0.0, scheduled_t]))
    assert_allclose(outputs.u_l_ts, np.array([0.0, 51.0]))
    assert_allclose(outputs.u_sw_ts, np.array([0.0, 61.0]))
    assert_allclose(outputs.u_r_h_ts, np.array([0.0, 9.0]))
    assert_allclose(outputs.u_r_v_ts, np.array([0.0, 13.0]))
    assert_allclose(outputs.c_r_h_by_layer_ts[:, 1], np.array([2.0, 3.0]))
    assert_allclose(outputs.psi_soil_by_layer_ts[:, 1], np.array([-1.3, -1.4]))


def test_store_preserves_legacy_first_file_save_cadence() -> None:
    params = thorp_params_from_defaults()
    captures: list[tuple[Path, dict[str, object]]] = []
    store = _Store(
        params=params,
        grid=_grid(),
        t_bgn=0.0,
        t_end=params.dt_sav_file + params.dt,
        save_mat_callback=lambda path, data: captures.append((path, data)),
    )

    store.initialize(**_init_kwargs(t=0.0))
    store.maybe_store(
        **{
            **_store_kwargs(t=params.dt_sav_data, offset=2.0),
            "save_mat_path": Path("out.mat"),
        }
    )
    outputs = store.to_outputs()

    assert outputs.t_ts.size == 1
    assert len(captures) == 1
    assert captures[0][0] == Path("out.mat")
    assert "t_stor" in captures[0][1]
    assert_allclose(captures[0][1]["t_stor"], np.array([0.0]))


def test_store_requires_noon_for_scheduled_data_store() -> None:
    params = thorp_params_from_defaults()
    t_bgn = 3600.0
    scheduled_t = t_bgn + 12 * 3600.0 + params.dt_sav_data
    store = _Store(params=params, grid=_grid(), t_bgn=t_bgn, t_end=scheduled_t + params.dt)

    store.initialize(**_init_kwargs(t=t_bgn))

    with pytest.raises(RuntimeError, match="Not noon"):
        store.maybe_store(**_store_kwargs(t=scheduled_t))


def test_store_requires_save_callback_when_path_is_provided() -> None:
    params = thorp_params_from_defaults()
    store = _Store(params=params, grid=_grid(), t_bgn=0.0, t_end=params.dt_sav_file + params.dt)

    store.initialize(**_init_kwargs(t=0.0))

    with pytest.raises(RuntimeError, match="save callback"):
        store.maybe_store(
            **{
                **_store_kwargs(t=params.dt_sav_data, offset=1.0),
                "save_mat_path": Path("out.mat"),
            }
        )
