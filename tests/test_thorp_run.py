from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
from numpy.testing import assert_allclose

import stomatal_optimiaztion.domains.thorp.simulation as simulation
from stomatal_optimiaztion.domains.thorp.growth import GrowthParams
from stomatal_optimiaztion.domains.thorp.hydraulics import StomataParams
from stomatal_optimiaztion.domains.thorp.params import (
    DEFAULT_RUN_NAME,
    THORPParams,
    thorp_params_from_defaults,
)
from stomatal_optimiaztion.domains.thorp.soil_dynamics import SoilMoistureParams
from stomatal_optimiaztion.domains.thorp.soil_initialization import (
    InitialSoilAndRoots,
    SoilGrid,
    SoilInitializationParams,
)


def _grid() -> SoilGrid:
    return SoilGrid(
        dz=np.array([0.2, 0.3], dtype=float),
        z_bttm=np.array([0.2, 0.5], dtype=float),
        z_mid=np.array([0.1, 0.35], dtype=float),
        dz_c=np.array([0.1, 0.25, 0.15], dtype=float),
    )


def _initialization_result() -> InitialSoilAndRoots:
    return InitialSoilAndRoots(
        grid=_grid(),
        psi_soil_by_layer=np.array([-0.3, -0.4], dtype=float),
        vwc=np.array([0.25, 0.20], dtype=float),
        c_r_h=np.array([1.0, 2.0], dtype=float),
        c_r_v=np.array([0.5, 1.5], dtype=float),
    )


def _forcing(t: np.ndarray) -> simulation.Forcing:
    t = np.asarray(t, dtype=float)
    return simulation.Forcing(
        t=t,
        t_a=np.full_like(t, 20.0, dtype=float),
        t_soil=np.full_like(t, 18.0, dtype=float),
        rh=np.full_like(t, 0.6, dtype=float),
        precip=np.zeros_like(t, dtype=float),
        u10=np.full_like(t, 1.5, dtype=float),
        r_incom=np.full_like(t, 300.0, dtype=float),
        z_a=np.zeros_like(t, dtype=float),
    )


def _install_stubbed_runtime(
    monkeypatch,
    *,
    captures: dict[str, object] | None = None,
) -> None:
    init = _initialization_result()

    def fake_initial_soil_and_roots(*, params, c_r_i, z_i):
        if captures is not None:
            captures.setdefault("soil_init_params", params)
            captures.setdefault("c_r_i", c_r_i)
            captures.setdefault("z_i", z_i)
        return init

    def fake_radiation(**kwargs):
        return SimpleNamespace(
            r_abs=100.0,
            d_r_abs_dh=1.0,
            d_r_abs_dw=2.0,
            d_r_abs_dla=3.0,
        )

    def fake_stomata(*, params, **kwargs):
        if captures is not None:
            captures.setdefault("stomata_params", params)
        return SimpleNamespace(
            psi_l=-1.0,
            psi_s=-0.8,
            psi_rc=-0.6,
            psi_rc0=-0.5,
            e=0.01,
            e_soil=np.array([0.001, 0.002], dtype=float),
            a_n=5.0,
            r_d=0.05,
            g_w=0.2,
            lambda_wue=0.1,
            d_a_n_d_r_abs=0.2,
            d_e_d_la=0.3,
            d_e_d_d=0.4,
            d_e_d_c_r_h=np.array([0.5, 0.6], dtype=float),
            d_e_d_c_r_v=np.array([0.7, 0.8], dtype=float),
        )

    def fake_allocation_fractions(**kwargs):
        return SimpleNamespace(
            u_l=0.1,
            u_r_h=np.array([0.1, 0.2], dtype=float),
            u_r_v=np.array([0.3, 0.4], dtype=float),
            u_sw=0.5,
        )

    def fake_soil_moisture(*, params, grid, psi_soil_by_layer, **kwargs):
        if captures is not None:
            captures.setdefault("soil_moisture_params", params)
        return np.asarray(psi_soil_by_layer, dtype=float), 0.05

    def fake_grow(*, params, **kwargs):
        if captures is not None:
            captures.setdefault("growth_params", params)
        return SimpleNamespace(
            c_l=11.0,
            c_r_h=np.array([1.0, 2.0], dtype=float),
            c_r_v=np.array([0.5, 1.5], dtype=float),
            c_sw=12.0,
            c_hw=13.0,
            c_nsc=14.0,
            h=2.0,
            w=3.0,
            d=0.4,
            d_hw=0.2,
            r_m=0.3,
            u=0.4,
        )

    monkeypatch.setattr(simulation, "initial_soil_and_roots", fake_initial_soil_and_roots)
    monkeypatch.setattr(simulation, "radiation", fake_radiation)
    monkeypatch.setattr(simulation, "stomata", fake_stomata)
    monkeypatch.setattr(simulation, "allocation_fractions", fake_allocation_fractions)
    monkeypatch.setattr(simulation, "soil_moisture", fake_soil_moisture)
    monkeypatch.setattr(simulation, "grow", fake_grow)


def test_run_uses_default_params_and_loads_forcing_when_omitted(monkeypatch) -> None:
    captures: dict[str, object] = {}

    def fake_load_forcing(*, params):
        captures["loaded_params"] = params
        return _forcing(np.array([0.0, params.dt], dtype=float))

    monkeypatch.setattr(simulation, "load_forcing", fake_load_forcing)
    _install_stubbed_runtime(monkeypatch, captures=captures)

    outputs = simulation.run(max_steps=1)

    loaded_params = captures["loaded_params"]
    assert isinstance(loaded_params, THORPParams)
    assert loaded_params.run_name == DEFAULT_RUN_NAME

    soil_init_params = captures["soil_init_params"]
    stomata_params = captures["stomata_params"]
    soil_moisture_params = captures["soil_moisture_params"]
    growth_params = captures["growth_params"]

    assert isinstance(soil_init_params, SoilInitializationParams)
    assert soil_init_params.n_soil == loaded_params.n_soil
    assert isinstance(stomata_params, StomataParams)
    assert stomata_params.d_ref == loaded_params.d_ref
    assert isinstance(soil_moisture_params, SoilMoistureParams)
    assert soil_moisture_params.richards.dt == loaded_params.dt
    assert isinstance(growth_params, GrowthParams)
    assert growth_params.allocation.sla == loaded_params.sla

    assert_allclose(outputs.t_ts, np.array([0.0]))
    assert_allclose(outputs.a_n_ts, np.array([5.0]))
    assert_allclose(outputs.evap_ts, np.array([0.05]))
    assert_allclose(outputs.psi_soil_by_layer_ts[:, 0], np.array([-0.3, -0.4]))


def test_run_matches_legacy_storage_schedule_with_stubbed_runtime_seams(monkeypatch) -> None:
    params = thorp_params_from_defaults()
    scheduled_t = 12 * 3600.0 + params.dt_sav_data
    forcing = _forcing(np.arange(0.0, scheduled_t + 2 * params.dt, params.dt, dtype=float))

    def fake_load_forcing(*, params):
        raise AssertionError("load_forcing should not be called when forcing is provided")

    monkeypatch.setattr(simulation, "load_forcing", fake_load_forcing)
    _install_stubbed_runtime(monkeypatch)

    outputs = simulation.run(params=params, forcing=forcing)

    assert_allclose(outputs.t_ts, np.array([0.0, scheduled_t]))
    assert_allclose(outputs.u_l_ts, np.array([0.0, 0.1]))
    assert_allclose(outputs.u_sw_ts, np.array([0.0, 0.5]))
    assert_allclose(outputs.u_r_h_ts, np.array([0.0, 0.3]))
    assert_allclose(outputs.u_r_v_ts, np.array([0.0, 0.7]))
    assert_allclose(outputs.r_m_ts, np.array([0.3, 0.3]))
    assert_allclose(outputs.u_ts, np.array([0.4, 0.4]))


def test_run_forwards_save_callback_to_store(monkeypatch) -> None:
    params = thorp_params_from_defaults()
    forcing = _forcing(np.arange(0.0, params.dt_sav_data + 2 * params.dt, params.dt, dtype=float))
    captures: list[tuple[Path, dict[str, object]]] = []

    _install_stubbed_runtime(monkeypatch)

    outputs = simulation.run(
        params=params,
        forcing=forcing,
        save_mat_path="out.mat",
        save_mat_callback=lambda path, data: captures.append((path, data)),
    )

    assert outputs.t_ts.size == 1
    assert len(captures) == 1
    assert captures[0][0] == Path("out.mat")
    assert "t_stor" in captures[0][1]
    assert_allclose(captures[0][1]["t_stor"], np.array([0.0]))
