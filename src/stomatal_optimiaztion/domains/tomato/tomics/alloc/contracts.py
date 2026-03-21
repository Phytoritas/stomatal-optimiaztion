from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Mapping, MutableMapping, Protocol, runtime_checkable

MoistureResponseFn = Callable[[float], float]
Params = Mapping[str, object]
StateStore = MutableMapping[str, object]
StepOutputs = Mapping[str, float | int]
_MAX_DEFAULT_DT_S = 6.0 * 3600.0


def _read_required_value(row: Mapping[str, object], key: str) -> object:
    if key not in row:
        raise KeyError(f"EnvStep.from_row: missing required field '{key}'.")
    return row[key]


def _read_datetime(value: object, *, field_name: str) -> datetime:
    if isinstance(value, datetime):
        return value

    to_pydatetime = getattr(value, "to_pydatetime", None)
    if callable(to_pydatetime):
        dt = to_pydatetime()
        if isinstance(dt, datetime):
            return dt

    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                f"EnvStep.from_row: field '{field_name}' must be a datetime-like value, got {value!r}."
            ) from exc

    raise TypeError(
        f"EnvStep.from_row: field '{field_name}' must be a datetime-like value, got {type(value).__name__}."
    )


def _read_required_float(row: Mapping[str, object], key: str) -> float:
    raw = _read_required_value(row, key)
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"EnvStep.from_row: required field '{key}' must be numeric.") from exc
    if not math.isfinite(value):
        raise ValueError(f"EnvStep.from_row: required field '{key}' must be finite, got {value!r}.")
    return value


def _read_optional_float(row: Mapping[str, object], key: str) -> float | None:
    if key not in row:
        return None

    raw = row[key]
    if raw is None:
        return None

    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return value


def _read_optional_int(row: Mapping[str, object], key: str) -> int | None:
    value = _read_optional_float(row, key)
    if value is None:
        return None
    return int(round(value))


@dataclass(frozen=True, slots=True)
class EnvStep:
    t: datetime
    dt_s: float
    T_air_C: float
    PAR_umol: float
    CO2_ppm: float
    RH_percent: float
    wind_speed_ms: float
    SW_in_Wm2: float | None = None
    T_rad_C: float | None = None
    n_fruits_per_truss: int | None = None
    theta_substrate: float | None = None
    rootzone_multistress: float | None = None
    rootzone_saturation: float | None = None

    @classmethod
    def from_row(
        cls,
        row: Mapping[str, object],
        prev_datetime: datetime | None,
        dt_default: float,
    ) -> "EnvStep":
        t = _read_datetime(_read_required_value(row, "datetime"), field_name="datetime")

        try:
            dt_default_s = float(dt_default)
        except (TypeError, ValueError) as exc:
            raise TypeError(f"EnvStep.from_row: dt_default must be numeric, got {dt_default!r}.") from exc
        if not math.isfinite(dt_default_s):
            raise ValueError(f"EnvStep.from_row: dt_default must be finite, got {dt_default_s!r}.")
        dt_default_s = min(max(dt_default_s, 1.0), _MAX_DEFAULT_DT_S)

        if prev_datetime is None:
            dt_s = dt_default_s
        else:
            prev_t = _read_datetime(prev_datetime, field_name="prev_datetime")
            dt_s = max(1.0, (t - prev_t).total_seconds())

        return cls(
            t=t,
            dt_s=float(dt_s),
            T_air_C=_read_required_float(row, "T_air_C"),
            PAR_umol=_read_required_float(row, "PAR_umol"),
            CO2_ppm=_read_required_float(row, "CO2_ppm"),
            RH_percent=_read_required_float(row, "RH_percent"),
            wind_speed_ms=_read_required_float(row, "wind_speed_ms"),
            SW_in_Wm2=_read_optional_float(row, "SW_in_Wm2"),
            T_rad_C=_read_optional_float(row, "T_rad_C"),
            n_fruits_per_truss=_read_optional_int(row, "n_fruits_per_truss"),
            theta_substrate=_read_optional_float(row, "theta_substrate"),
            rootzone_multistress=_read_optional_float(row, "rootzone_multistress"),
            rootzone_saturation=_read_optional_float(row, "rootzone_saturation"),
        )


@dataclass(slots=True)
class Context:
    env: EnvStep
    state: StateStore
    params: Params
    out: dict[str, float]


@runtime_checkable
class Module(Protocol):
    def __call__(self, ctx: Context) -> None:
        """Mutate context state/output for one simulation step."""


def clamp_unit_interval(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return value


def coerce_finite_outputs(outputs: StepOutputs, *, where: str) -> dict[str, float]:
    """Validate run-step outputs and convert values to plain finite floats."""

    out: dict[str, float] = {}
    for key, raw in outputs.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{where}: output keys must be non-empty strings.")
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise TypeError(f"{where}: output '{key}' must be numeric, got {type(raw).__name__}.") from exc
        if not math.isfinite(value):
            raise ValueError(f"{where}: output '{key}' must be finite, got {value!r}.")
        out[key] = value
    return out


def water_supply_stress_from_theta(theta_substrate: float, moisture_response_fn: MoistureResponseFn) -> float:
    return clamp_unit_interval(float(moisture_response_fn(theta_substrate)))
