from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from stomatal_optimiaztion.domains.tomato.tthorp import MODEL_NAME
from stomatal_optimiaztion.domains.tomato.tthorp.contracts import (
    Context,
    EnvStep,
    clamp_unit_interval,
    coerce_finite_outputs,
    water_supply_stress_from_theta,
)


def _forcing_row(
    *,
    t: datetime,
    t_air_c: float = 25.0,
    par_umol: float = 400.0,
    co2_ppm: float = 420.0,
    rh_percent: float = 60.0,
    wind_speed_ms: float = 1.0,
) -> dict[str, object]:
    return {
        "datetime": t,
        "T_air_C": t_air_c,
        "PAR_umol": par_umol,
        "CO2_ppm": co2_ppm,
        "RH_percent": rh_percent,
        "wind_speed_ms": wind_speed_ms,
    }


def test_tthorp_import_surface_exposes_model_name() -> None:
    assert MODEL_NAME == "tTHORP"


def test_envstep_from_row_uses_clipped_default_then_elapsed_seconds() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, 0)
    first = EnvStep.from_row(_forcing_row(t=t0), prev_datetime=None, dt_default=10.0 * 3600.0)
    assert first.dt_s == 6.0 * 3600.0

    t1 = t0 + timedelta(minutes=30)
    second = EnvStep.from_row(_forcing_row(t=t1), prev_datetime=t0, dt_default=5.0)
    assert second.dt_s == 1800.0

    earlier = EnvStep.from_row(_forcing_row(t=t0 - timedelta(minutes=5)), prev_datetime=t0, dt_default=5.0)
    assert earlier.dt_s == 1.0


def test_envstep_from_row_rejects_missing_required_field() -> None:
    row = _forcing_row(t=datetime(2026, 1, 1, 0, 0, 0))
    row.pop("PAR_umol")

    with pytest.raises(KeyError, match="missing required field 'PAR_umol'"):
        EnvStep.from_row(row, prev_datetime=None, dt_default=3600.0)


def test_coerce_finite_outputs_rejects_non_finite_values() -> None:
    with pytest.raises(ValueError):
        coerce_finite_outputs({"e": float("nan")}, where="unit-test")


def test_water_supply_stress_clamps_to_unit_interval() -> None:
    assert clamp_unit_interval(-0.2) == 0.0
    assert clamp_unit_interval(0.4) == 0.4
    assert clamp_unit_interval(1.2) == 1.0
    assert water_supply_stress_from_theta(0.2, lambda _: -0.1) == 0.0
    assert water_supply_stress_from_theta(0.2, lambda _: 1.2) == 1.0


def test_context_holds_env_state_and_outputs() -> None:
    env = EnvStep.from_row(
        _forcing_row(t=datetime(2026, 1, 1, 0, 0, 0)),
        prev_datetime=None,
        dt_default=3600.0,
    )
    ctx = Context(env=env, state={"signal": 1.0}, params={"gain": 2.0}, out={"e": 0.3})

    assert ctx.env is env
    assert ctx.state["signal"] == 1.0
    assert ctx.params["gain"] == 2.0
    assert ctx.out["e"] == 0.3
