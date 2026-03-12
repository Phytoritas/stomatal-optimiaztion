from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Callable, Mapping, Protocol

from stomatal_optimiaztion.domains.tomato.tthorp.contracts import (
    Context,
    EnvStep,
    water_supply_stress_from_theta,
)
from stomatal_optimiaztion.domains.tomato.tthorp.interface import PipelineModel

PartitionPolicyLike = object | str | None


class TomatoLegacyModelProtocol(Protocol):
    fixed_lai: float | None
    partition_policy: PartitionPolicyLike
    allocation_scheme: str
    start_date: datetime
    current_date: date
    last_calc_time: datetime | None

    def reset_state(self) -> None: ...

    def update_inputs_from_row(self, row: dict[str, float]) -> None: ...

    def run_timestep_calculations(self, dt_s: float, t: datetime) -> None: ...

    def get_current_outputs(self, t: datetime) -> Mapping[str, object]: ...


ModelFactory = Callable[..., TomatoLegacyModelProtocol]


def _default_model_factory(
    *,
    fixed_lai: float | None,
    partition_policy: PartitionPolicyLike,
    allocation_scheme: str,
) -> TomatoLegacyModelProtocol:
    try:
        from stomatal_optimiaztion.domains.tomato.tthorp.models.tomato_legacy.tomato_model import TomatoModel
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "TomatoLegacyAdapter requires a migrated tomato_model or an explicit model_factory."
        ) from exc

    return TomatoModel(
        fixed_lai=fixed_lai,
        partition_policy=partition_policy,
        allocation_scheme=allocation_scheme,
    )


def _finite_float(raw: object, *, default: float) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(value):
        return float(default)
    return value


def _default_moisture_response(theta_substrate: float) -> float:
    return theta_substrate / 0.4


def _write_numeric_legacy_outputs(legacy: Mapping[str, object], out: dict[str, float]) -> None:
    for key, raw in legacy.items():
        if key == "datetime":
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if math.isfinite(value):
            out[key] = value


def _env_to_legacy_row(env: EnvStep) -> dict[str, float]:
    row: dict[str, float] = {
        "T_air_C": float(env.T_air_C),
        "PAR_umol": float(env.PAR_umol),
        "CO2_ppm": float(env.CO2_ppm),
        "RH_percent": float(env.RH_percent),
        "wind_speed_ms": float(env.wind_speed_ms),
        "n_fruits_per_truss": float(env.n_fruits_per_truss or 4),
    }
    if env.SW_in_Wm2 is not None:
        row["SW_in_Wm2"] = float(env.SW_in_Wm2)
    if env.T_rad_C is not None:
        row["T_rad_C"] = float(env.T_rad_C)
    return row


def _build_model(
    *,
    model_factory: ModelFactory | None,
    fixed_lai: float | None,
    partition_policy: PartitionPolicyLike,
    allocation_scheme: str,
) -> TomatoLegacyModelProtocol:
    factory = model_factory or _default_model_factory
    return factory(
        fixed_lai=fixed_lai,
        partition_policy=partition_policy,
        allocation_scheme=allocation_scheme,
    )


def _prime_model_clock(model: TomatoLegacyModelProtocol, env: EnvStep) -> None:
    model.start_date = env.t
    model.current_date = env.t.date()
    model.last_calc_time = env.t


@dataclass(slots=True)
class TomatoLegacyAdapter:
    """Stateful step adapter exposing the original TomatoModel step API."""

    model: TomatoLegacyModelProtocol | None = None
    fixed_lai: float | None = None
    partition_policy: PartitionPolicyLike = None
    allocation_scheme: str = "4pool"
    model_factory: ModelFactory | None = None
    _initialized: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        if self.model is None:
            self.model = _build_model(
                model_factory=self.model_factory,
                fixed_lai=self.fixed_lai,
                partition_policy=self.partition_policy,
                allocation_scheme=self.allocation_scheme,
            )
        elif self.fixed_lai is not None:
            self.model.fixed_lai = float(self.fixed_lai)
        self.model.partition_policy = self.partition_policy
        self.model.allocation_scheme = str(self.allocation_scheme)
        self.reset_state()

    def reset_state(self) -> None:
        if self.model is None:  # pragma: no cover - defensive guard
            self.model = _build_model(
                model_factory=self.model_factory,
                fixed_lai=self.fixed_lai,
                partition_policy=self.partition_policy,
                allocation_scheme=self.allocation_scheme,
            )
        self.model.reset_state()
        self._initialized = False

    def step(self, env: EnvStep) -> dict[str, object]:
        if env.dt_s <= 0:
            raise ValueError(f"TomatoLegacyAdapter.step: env.dt_s must be > 0, got {env.dt_s!r}.")

        model = self.model
        if model is None:  # pragma: no cover - defensive guard
            model = _build_model(
                model_factory=self.model_factory,
                fixed_lai=self.fixed_lai,
                partition_policy=self.partition_policy,
                allocation_scheme=self.allocation_scheme,
            )
            self.model = model

        if not self._initialized:
            _prime_model_clock(model, env)
            self._initialized = True

        model.update_inputs_from_row(_env_to_legacy_row(env))
        model.run_timestep_calculations(float(env.dt_s), env.t)
        model.last_calc_time = env.t
        return dict(model.get_current_outputs(env.t))


@dataclass(slots=True)
class TomatoLegacyModule:
    """Bridge legacy tomato step logic into the migrated pipeline Module contract."""

    model_state_key: str = "_tomato_legacy_model"
    model_factory: ModelFactory | None = None

    def __call__(self, ctx: Context) -> None:
        model = self._get_or_create_model(ctx)
        row = _env_to_legacy_row(ctx.env)

        model.update_inputs_from_row(row)
        model.run_timestep_calculations(float(ctx.env.dt_s), ctx.env.t)
        legacy = dict(model.get_current_outputs(ctx.env.t))

        theta = self._resolve_theta_substrate(ctx)
        moisture_response_fn = self._resolve_moisture_response_fn(ctx)
        stress = water_supply_stress_from_theta(theta, moisture_response_fn)

        _write_numeric_legacy_outputs(legacy, ctx.out)

        e = _finite_float(legacy.get("transpiration_rate_g_s_m2"), default=0.0)
        g_w = max(e * 1.0e-3, 0.0)
        a_n = _finite_float(legacy.get("co2_flux_g_m2_s"), default=0.0)
        r_d = max(_finite_float(legacy.get("latent_heat_W_m2"), default=0.0) * 1.0e-4, 0.0)

        ctx.out["theta_substrate"] = theta
        ctx.out["water_supply_stress"] = stress
        ctx.out["e"] = e
        ctx.out["g_w"] = g_w
        ctx.out["a_n"] = a_n
        ctx.out["r_d"] = r_d

    def _get_or_create_model(self, ctx: Context) -> TomatoLegacyModelProtocol:
        cached = ctx.state.get(self.model_state_key)
        if _looks_like_tomato_model(cached):
            return cached

        fixed_lai_raw = ctx.params.get("fixed_lai")
        fixed_lai = _finite_float(fixed_lai_raw, default=float("nan")) if fixed_lai_raw is not None else None
        if fixed_lai is not None and not math.isfinite(fixed_lai):
            fixed_lai = None

        model_factory = self.model_factory
        ctx_factory = ctx.params.get("model_factory")
        if callable(ctx_factory):
            model_factory = ctx_factory
        elif ctx_factory is not None:
            raise TypeError("model_factory must be callable when provided in pipeline params.")

        allocation_scheme = str(ctx.params.get("allocation_scheme", "4pool"))
        model = _build_model(
            model_factory=model_factory,
            fixed_lai=fixed_lai,
            partition_policy=ctx.params.get("partition_policy"),
            allocation_scheme=allocation_scheme,
        )
        _prime_model_clock(model, ctx.env)
        ctx.state[self.model_state_key] = model
        return model

    def _resolve_theta_substrate(self, ctx: Context) -> float:
        raw = ctx.params.get("theta_substrate", ctx.state.get("theta_substrate", 0.33))
        theta = _finite_float(raw, default=0.33)
        theta = min(max(theta, 0.0), 1.0)
        ctx.state["theta_substrate"] = theta
        return theta

    def _resolve_moisture_response_fn(self, ctx: Context) -> Callable[[float], float]:
        candidate = ctx.params.get("moisture_response_fn")
        if callable(candidate):
            return candidate
        return _default_moisture_response


def _looks_like_tomato_model(candidate: object) -> bool:
    required_attrs = ("fixed_lai", "partition_policy", "allocation_scheme", "start_date", "current_date", "last_calc_time")
    required_methods = ("reset_state", "update_inputs_from_row", "run_timestep_calculations", "get_current_outputs")
    if candidate is None:
        return False
    if not all(hasattr(candidate, name) for name in required_attrs):
        return False
    return all(callable(getattr(candidate, name, None)) for name in required_methods)


def make_tomato_legacy_model(
    *,
    name: str = "tomato_legacy",
    theta_substrate: float = 0.33,
    fixed_lai: float | None = None,
    partition_policy: PartitionPolicyLike = None,
    allocation_scheme: str = "4pool",
    moisture_response_fn: Callable[[float], float] | None = None,
    model_factory: ModelFactory | None = None,
) -> PipelineModel:
    """Factory for a PipelineModel running the legacy tomato bridge module."""

    params: dict[str, object] = {"theta_substrate": float(theta_substrate)}
    if fixed_lai is not None:
        params["fixed_lai"] = float(fixed_lai)
    if partition_policy is not None:
        params["partition_policy"] = partition_policy
    params["allocation_scheme"] = str(allocation_scheme)
    if moisture_response_fn is not None:
        params["moisture_response_fn"] = moisture_response_fn
    if model_factory is not None:
        params["model_factory"] = model_factory

    return PipelineModel(name=name, params=params, modules=(TomatoLegacyModule(model_factory=model_factory),))
