from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
import pytest

from stomatal_optimiaztion.domains.tomato.tthorp import simulate
from stomatal_optimiaztion.domains.tomato.tthorp.contracts import Context, EnvStep
from stomatal_optimiaztion.domains.tomato.tthorp.models.tomato_legacy import (
    TomatoLegacyAdapter,
    TomatoLegacyModule,
    make_tomato_legacy_model,
)


@dataclass
class _FakeTomatoModel:
    fixed_lai: float | None = None
    partition_policy: object | None = None
    allocation_scheme: str = "4pool"
    start_date: datetime = field(default_factory=lambda: datetime(2000, 1, 1, 0, 0, 0))
    current_date: object = None
    last_calc_time: datetime | None = None
    reset_calls: int = 0
    last_row: dict[str, float] | None = None
    run_calls: list[tuple[float, datetime]] = field(default_factory=list)

    def reset_state(self) -> None:
        self.reset_calls += 1

    def update_inputs_from_row(self, row: dict[str, float]) -> None:
        self.last_row = dict(row)

    def run_timestep_calculations(self, dt_s: float, t: datetime) -> None:
        self.run_calls.append((dt_s, t))

    def get_current_outputs(self, t: datetime) -> dict[str, object]:
        return {
            "datetime": t,
            "LAI": 2.5,
            "co2_flux_g_m2_s": 0.12,
            "latent_heat_W_m2": 250.0,
            "transpiration_rate_g_s_m2": 3.5,
            "status_text": "ignore-me",
        }


def _make_env(*, t: datetime, dt_s: float, n_fruits_per_truss: int | None = None) -> EnvStep:
    return EnvStep(
        t=t,
        dt_s=dt_s,
        T_air_C=24.0,
        PAR_umol=500.0,
        CO2_ppm=420.0,
        RH_percent=60.0,
        wind_speed_ms=1.5,
        SW_in_Wm2=120.0,
        T_rad_C=26.0,
        n_fruits_per_truss=n_fruits_per_truss,
    )


def test_tomato_legacy_adapter_primes_model_and_maps_rows() -> None:
    model = _FakeTomatoModel()
    adapter = TomatoLegacyAdapter(
        model=model,
        fixed_lai=1.8,
        partition_policy="sink-based",
        allocation_scheme="3pool",
    )
    env = _make_env(t=datetime(2026, 1, 1, 12, 0, 0), dt_s=3600.0, n_fruits_per_truss=None)

    out = adapter.step(env)

    assert model.reset_calls == 1
    assert model.fixed_lai == 1.8
    assert model.partition_policy == "sink-based"
    assert model.allocation_scheme == "3pool"
    assert model.start_date == env.t
    assert model.current_date == env.t.date()
    assert model.last_calc_time == env.t
    assert model.last_row == {
        "T_air_C": 24.0,
        "PAR_umol": 500.0,
        "CO2_ppm": 420.0,
        "RH_percent": 60.0,
        "wind_speed_ms": 1.5,
        "n_fruits_per_truss": 4.0,
        "SW_in_Wm2": 120.0,
        "T_rad_C": 26.0,
    }
    assert model.run_calls == [(3600.0, env.t)]
    assert out["LAI"] == 2.5


def test_tomato_legacy_adapter_rejects_non_positive_timestep() -> None:
    adapter = TomatoLegacyAdapter(model=_FakeTomatoModel())

    with pytest.raises(ValueError, match="env.dt_s must be > 0"):
        adapter.step(_make_env(t=datetime(2026, 1, 1, 0, 0, 0), dt_s=0.0))


def test_tomato_legacy_module_writes_outputs_and_reuses_cached_model() -> None:
    created: list[_FakeTomatoModel] = []

    def factory(**kwargs: object) -> _FakeTomatoModel:
        model = _FakeTomatoModel(
            fixed_lai=kwargs.get("fixed_lai"),  # type: ignore[arg-type]
            partition_policy=kwargs.get("partition_policy"),
            allocation_scheme=str(kwargs.get("allocation_scheme", "4pool")),
        )
        created.append(model)
        return model

    module = TomatoLegacyModule(model_factory=factory)
    env = _make_env(t=datetime(2026, 1, 1, 6, 0, 0), dt_s=1800.0)
    ctx = Context(
        env=env,
        state={},
        params={"theta_substrate": 0.2, "moisture_response_fn": lambda theta: theta / 0.5},
        out={},
    )

    module(ctx)

    assert len(created) == 1
    assert ctx.state["_tomato_legacy_model"] is created[0]
    assert ctx.state["theta_substrate"] == 0.2
    assert ctx.out["LAI"] == 2.5
    assert ctx.out["e"] == 3.5
    assert ctx.out["g_w"] == pytest.approx(0.0035)
    assert ctx.out["a_n"] == 0.12
    assert ctx.out["r_d"] == pytest.approx(0.025)
    assert ctx.out["water_supply_stress"] == pytest.approx(0.4)
    assert "status_text" not in ctx.out

    ctx.out = {}
    ctx.env = _make_env(t=datetime(2026, 1, 1, 6, 30, 0), dt_s=1800.0)
    module(ctx)
    assert len(created) == 1
    assert created[0].run_calls[-1] == (1800.0, ctx.env.t)


def test_make_tomato_legacy_model_runs_with_injected_factory() -> None:
    def factory(**kwargs: object) -> _FakeTomatoModel:
        return _FakeTomatoModel(
            fixed_lai=kwargs.get("fixed_lai"),  # type: ignore[arg-type]
            partition_policy=kwargs.get("partition_policy"),
            allocation_scheme=str(kwargs.get("allocation_scheme", "4pool")),
        )

    model = make_tomato_legacy_model(
        fixed_lai=2.2,
        partition_policy="thorp-opt",
        allocation_scheme="3pool",
        model_factory=factory,
    )
    forcing = [
        _make_env(t=datetime(2026, 1, 1, 0, 0, 0), dt_s=3600.0),
        _make_env(t=datetime(2026, 1, 1, 1, 0, 0), dt_s=3600.0),
    ]

    out = simulate(model=model, forcing=forcing)

    assert isinstance(out, pd.DataFrame)
    assert list(out.columns) == [
        "datetime",
        "LAI",
        "co2_flux_g_m2_s",
        "latent_heat_W_m2",
        "transpiration_rate_g_s_m2",
        "theta_substrate",
        "water_supply_stress",
        "e",
        "g_w",
        "a_n",
        "r_d",
    ]
    assert out["theta_substrate"].tolist() == [0.33, 0.33]


def test_make_tomato_legacy_model_runs_with_default_tomato_model() -> None:
    model = make_tomato_legacy_model()
    forcing = [
        _make_env(t=datetime(2026, 1, 1, 0, 0, 0), dt_s=3600.0),
        _make_env(t=datetime(2026, 1, 1, 1, 0, 0), dt_s=3600.0),
    ]

    out = simulate(model=model, forcing=forcing)

    assert isinstance(out, pd.DataFrame)
    assert len(out) == 2
    for column in [
        "datetime",
        "LAI",
        "total_dry_weight_g_m2",
        "co2_flux_g_m2_s",
        "theta_substrate",
        "water_supply_stress",
        "e",
        "g_w",
        "a_n",
        "r_d",
    ]:
        assert column in out.columns
