from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import numpy as np
import pandas as pd
from numpy.testing import assert_allclose

from stomatal_optimiaztion.domains.tomato.tomics.alloc.models.thorp_ref import THORPReferenceAdapter


def test_thorp_reference_adapter_normalizes_forcing_and_maps_outputs() -> None:
    captures: dict[str, object] = {}
    sentinel_params = object()

    def params_factory() -> object:
        return sentinel_params

    def run_model(*, params: object, forcing: object, max_steps: int | None) -> object:
        captures["params"] = params
        captures["forcing"] = forcing
        captures["max_steps"] = max_steps
        return SimpleNamespace(
            t_ts=np.array([0.0, 6.0 * 3600.0, 12.0 * 3600.0], dtype=float),
            e_ts=np.array([0.1, 0.2, 0.3], dtype=float),
            g_w_ts=np.array([0.0, 0.2, -0.4], dtype=float),
            a_n_ts=np.array([1.0, 2.0, 3.0], dtype=float),
            r_d_ts=np.array([0.01, 0.02, 0.03], dtype=float),
        )

    forcing = pd.DataFrame(
        {
            "datetime": [datetime(2026, 1, 1, 0, 0, 0), datetime(2026, 1, 1, 6, 0, 0)],
            "t_air_c": [24.0, 26.0],
            "t_soil_c": [20.0, 21.0],
            "rh": [60.0, 70.0],
            "precip_mm": [0.0, 1.5],
            "wind_speed_ms": [1.2, 1.4],
            "SW_in_Wm2": [100.0, 120.0],
            "theta_substrate": [0.30, 0.31],
        }
    )

    adapter = THORPReferenceAdapter(params_factory=params_factory, run_model=run_model)
    out = adapter.simulate(forcing, max_steps=3)

    forcing_obj = captures["forcing"]
    assert captures["params"] is sentinel_params
    assert captures["max_steps"] == 3

    assert_allclose(getattr(forcing_obj, "t"), np.array([0.0, 21600.0, 43200.0, 64800.0]))
    assert_allclose(getattr(forcing_obj, "t_a"), np.array([24.0, 26.0, 26.0, 26.0]))
    assert_allclose(getattr(forcing_obj, "t_soil"), np.array([20.0, 21.0, 21.0, 21.0]))
    assert_allclose(getattr(forcing_obj, "rh"), np.array([0.6, 0.7, 0.7, 0.7]))
    assert_allclose(getattr(forcing_obj, "precip"), np.array([0.0, 1.5, 1.5, 1.5]))
    assert_allclose(getattr(forcing_obj, "u10"), np.array([1.2, 1.4, 1.4, 1.4]))
    assert_allclose(getattr(forcing_obj, "r_incom"), np.array([100.0, 120.0, 120.0, 120.0]))
    assert_allclose(getattr(forcing_obj, "z_a"), np.array([0.8, 0.8, 0.8, 0.8]))

    assert list(out.columns) == [
        "datetime",
        "theta_substrate",
        "water_supply_stress",
        "e",
        "g_w",
        "a_n",
        "r_d",
    ]
    assert out["datetime"].tolist() == [
        pd.Timestamp("2026-01-01 00:00:00"),
        pd.Timestamp("2026-01-01 06:00:00"),
        pd.Timestamp("2026-01-01 12:00:00"),
    ]
    assert_allclose(out["theta_substrate"].to_numpy(dtype=float), np.array([0.30, 0.31, 0.31]))
    assert_allclose(out["water_supply_stress"].to_numpy(dtype=float), np.array([0.0, 0.5, 1.0]))
    assert_allclose(out["e"].to_numpy(dtype=float), np.array([0.1, 0.2, 0.3]))
    assert_allclose(out["g_w"].to_numpy(dtype=float), np.array([0.0, 0.2, -0.4]))
    assert_allclose(out["a_n"].to_numpy(dtype=float), np.array([1.0, 2.0, 3.0]))
    assert_allclose(out["r_d"].to_numpy(dtype=float), np.array([0.01, 0.02, 0.03]))


def test_thorp_reference_adapter_returns_empty_frame_when_runtime_outputs_empty() -> None:
    adapter = THORPReferenceAdapter(
        params_factory=lambda: object(),
        run_model=lambda **_: SimpleNamespace(
            t_ts=np.array([], dtype=float),
            e_ts=np.array([], dtype=float),
            g_w_ts=np.array([], dtype=float),
            a_n_ts=np.array([], dtype=float),
            r_d_ts=np.array([], dtype=float),
        ),
    )

    out = adapter.simulate(pd.DataFrame({"datetime": [datetime(2026, 1, 1, 0, 0, 0)]}))

    assert out.empty
    assert list(out.columns) == [
        "datetime",
        "theta_substrate",
        "water_supply_stress",
        "e",
        "g_w",
        "a_n",
        "r_d",
    ]


def test_thorp_reference_adapter_smoke_with_migrated_runtime() -> None:
    start = datetime(2026, 1, 1, 0, 0, 0)
    steps = 20
    forcing = pd.DataFrame(
        {
            "datetime": [start + i * timedelta(hours=6) for i in range(steps)],
            "theta_substrate": np.full(steps, 0.33),
            "t_air_c": np.full(steps, 25.0),
            "t_soil_c": np.full(steps, 22.0),
            "rh": np.full(steps, 0.60),
            "r_incom_w_m2": np.full(steps, 400.0),
            "u10": np.full(steps, 1.0),
            "precip": np.zeros(steps),
            "z_a": np.full(steps, 0.8),
        }
    )

    model = THORPReferenceAdapter()
    out = model.simulate(forcing, max_steps=steps)

    expected_columns = {
        "datetime",
        "theta_substrate",
        "water_supply_stress",
        "e",
        "g_w",
        "a_n",
        "r_d",
    }
    assert expected_columns.issubset(out.columns)
    assert not out.empty
    assert out["datetime"].is_monotonic_increasing

    numeric = out[["theta_substrate", "water_supply_stress", "e", "g_w", "a_n", "r_d"]].to_numpy(dtype=float)
    assert np.isfinite(numeric).all()
