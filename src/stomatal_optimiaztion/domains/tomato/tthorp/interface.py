from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from stomatal_optimiaztion.domains.tomato.tthorp.contracts import (
    Context,
    EnvStep,
    Module,
    MoistureResponseFn,
    coerce_finite_outputs,
    water_supply_stress_from_theta,
)


@runtime_checkable
class StepModel(Protocol):
    def step(self, env: EnvStep) -> Mapping[str, object]:
        """Run one timestep and return output mapping."""


@dataclass(slots=True)
class PipelineModel:
    name: str
    state: dict[str, object] = field(default_factory=dict)
    params: dict[str, object] = field(default_factory=dict)
    modules: tuple[Module, ...] = ()

    def __post_init__(self) -> None:
        self.modules = tuple(self.modules)

    def step(self, env: EnvStep) -> dict[str, float]:
        if env.dt_s <= 0:
            raise ValueError(f"{self.name}.step: env.dt_s must be > 0, got {env.dt_s!r}.")

        ctx = Context(env=env, state=self.state, params=self.params, out={})
        for module in self.modules:
            module(ctx)

        return coerce_finite_outputs(ctx.out, where=f"{self.name}.step")


def simulate(
    model: StepModel,
    forcing: Iterable[EnvStep],
    max_steps: int | None = None,
):
    """Run the pipeline model over forcing and return a tabular result."""
    if max_steps is not None and max_steps < 0:
        raise ValueError(f"simulate: max_steps must be >= 0, got {max_steps!r}.")

    rows: list[dict[str, object]] = []
    output_columns: tuple[str, ...] | None = None

    for step_index, env in enumerate(forcing):
        if max_steps is not None and step_index >= max_steps:
            break

        outputs = model.step(env)
        if not isinstance(outputs, Mapping):
            raise TypeError(
                f"simulate step {step_index}: model.step(env) must return a mapping, got {type(outputs).__name__}."
            )

        row_datetime = outputs.get("datetime", env.t)
        output_payload = {key: value for key, value in outputs.items() if key != "datetime"}

        if output_columns is None:
            output_columns = tuple(output_payload.keys())
        else:
            current_keys = tuple(output_payload.keys())
            if set(current_keys) != set(output_columns):
                raise ValueError(
                    "simulate step "
                    f"{step_index}: output columns changed; expected {list(output_columns)}, got {list(current_keys)}."
                )

        ordered_outputs = {key: output_payload[key] for key in output_columns}
        rows.append({"datetime": row_datetime, **ordered_outputs})

    try:
        import pandas as pd
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError("simulate() requires pandas to build a tabular result.") from exc

    if output_columns is None:
        return pd.DataFrame(columns=["datetime"])
    return pd.DataFrame(rows, columns=["datetime", *output_columns])


def run_flux_step(
    *,
    env: EnvStep,
    theta_substrate: float,
    moisture_response_fn: MoistureResponseFn,
) -> dict[str, float]:
    """tTHORP step contract placeholder until the full tomato physics lands."""

    stress = water_supply_stress_from_theta(theta_substrate, moisture_response_fn)
    par = max(float(env.PAR_umol), 0.0)
    co2_scale = max(float(env.CO2_ppm), 0.0) / 400.0
    vpd_like = max(100.0 - float(env.RH_percent), 0.0) / 100.0
    wind = max(float(env.wind_speed_ms), 0.0)

    a_n = stress * co2_scale * par * env.dt_s * 1e-6
    g_w = stress * (0.02 + 0.01 * wind)
    e = g_w * vpd_like * env.dt_s * 1e-4
    r_d = 0.1 * a_n
    return {
        "theta_substrate": float(theta_substrate),
        "water_supply_stress": stress,
        "e": e,
        "g_w": g_w,
        "a_n": a_n,
        "r_d": r_d,
    }
