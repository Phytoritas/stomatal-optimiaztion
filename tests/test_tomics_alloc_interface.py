from datetime import datetime, timedelta

import pytest

from stomatal_optimiaztion.domains.tomato.tomics.alloc import PipelineModel, run_flux_step, simulate
from stomatal_optimiaztion.domains.tomato.tomics.alloc.contracts import Context, EnvStep


def _make_env_step(
    *,
    t: datetime,
    dt_s: float,
    par_umol: float = 400.0,
    rh_percent: float = 60.0,
    wind_speed_ms: float = 1.0,
) -> EnvStep:
    return EnvStep(
        t=t,
        dt_s=dt_s,
        T_air_C=25.0,
        PAR_umol=par_umol,
        CO2_ppm=420.0,
        RH_percent=rh_percent,
        wind_speed_ms=wind_speed_ms,
    )


class _AccumulatorModule:
    def __call__(self, ctx: Context) -> None:
        prev = float(ctx.state.get("signal", 0.0))
        gain = float(ctx.params.get("gain", 1.0))
        signal = prev + gain * ctx.env.dt_s
        ctx.state["signal"] = signal
        ctx.out["signal"] = signal


def test_pipeline_model_step_runs_modules() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, 0)
    model = PipelineModel(name="accumulator", params={"gain": 0.5}, modules=(_AccumulatorModule(),))

    out1 = model.step(_make_env_step(t=t0, dt_s=2.0))
    out2 = model.step(_make_env_step(t=t0 + timedelta(seconds=2), dt_s=4.0))

    assert out1 == {"signal": 1.0}
    assert out2 == {"signal": 3.0}


def test_simulate_runs_pipeline_with_stable_columns_and_max_steps() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, 0)
    model = PipelineModel(name="accumulator", params={"gain": 1.0}, modules=(_AccumulatorModule(),))
    forcing = [_make_env_step(t=t0 + timedelta(hours=i), dt_s=1.0) for i in range(3)]

    out = simulate(model=model, forcing=forcing, max_steps=2)

    assert list(out.columns) == ["datetime", "signal"]
    assert out["signal"].tolist() == [1.0, 2.0]


def test_simulate_uses_output_datetime_without_duplicate_columns() -> None:
    class _DatetimeOutputModel:
        def step(self, env: EnvStep) -> dict[str, object]:
            return {"datetime": env.t + timedelta(seconds=5), "signal": env.dt_s}

    t0 = datetime(2026, 1, 1, 0, 0, 0)
    forcing = [_make_env_step(t=t0 + timedelta(seconds=i), dt_s=1.0) for i in range(2)]

    out = simulate(model=_DatetimeOutputModel(), forcing=forcing)

    assert list(out.columns) == ["datetime", "signal"]
    assert out["datetime"].tolist() == [t0 + timedelta(seconds=5), t0 + timedelta(seconds=6)]


def test_simulate_rejects_changed_output_columns() -> None:
    class _UnstableModule:
        def __call__(self, ctx: Context) -> None:
            step = int(ctx.state.get("step", 0))
            ctx.state["step"] = step + 1
            if step == 0:
                ctx.out["a"] = 1.0
            else:
                ctx.out["b"] = 1.0

    t0 = datetime(2026, 1, 1, 0, 0, 0)
    model = PipelineModel(name="unstable", modules=(_UnstableModule(),))
    forcing = [_make_env_step(t=t0, dt_s=1.0), _make_env_step(t=t0 + timedelta(hours=1), dt_s=1.0)]

    with pytest.raises(ValueError, match="output columns changed"):
        simulate(model=model, forcing=forcing)


def test_simulate_rejects_negative_max_steps() -> None:
    model = PipelineModel(name="accumulator", modules=(_AccumulatorModule(),))

    with pytest.raises(ValueError, match="max_steps"):
        simulate(model=model, forcing=[], max_steps=-1)


def test_flux_step_uses_timestep_from_env() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, 0)

    out_short = run_flux_step(
        env=_make_env_step(t=t0, dt_s=60.0, rh_percent=45.0),
        theta_substrate=0.33,
        moisture_response_fn=lambda theta: theta,
    )
    out_long = run_flux_step(
        env=_make_env_step(t=t0 + timedelta(minutes=1), dt_s=600.0, rh_percent=45.0),
        theta_substrate=0.33,
        moisture_response_fn=lambda theta: theta,
    )

    assert out_short["theta_substrate"] == 0.33
    assert 0.0 <= out_short["water_supply_stress"] <= 1.0
    assert out_long["e"] > out_short["e"]
