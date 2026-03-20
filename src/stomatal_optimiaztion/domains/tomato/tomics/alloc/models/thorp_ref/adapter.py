from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace

import numpy as np
import pandas as pd

from stomatal_optimiaztion.domains.thorp import Forcing, default_params, run, thorp_params_from_defaults
from stomatal_optimiaztion.domains.thorp.params import THORPParams

ParamsFactory = Callable[[], THORPParams]
RunModel = Callable[..., object]


def _default_params_factory() -> THORPParams:
    return thorp_params_from_defaults(default_params())


def _default_run_model(*, params: THORPParams, forcing: Forcing, max_steps: int | None) -> object:
    return run(params=params, forcing=forcing, max_steps=max_steps)


def _numeric_series(df: pd.DataFrame, candidates: tuple[str, ...], *, default: float, length: int) -> np.ndarray:
    for name in candidates:
        if name in df.columns:
            values = pd.to_numeric(df[name], errors="coerce").to_numpy(dtype=float)
            break
    else:
        values = np.full(df.shape[0], default, dtype=float)

    finite = np.isfinite(values)
    values = np.where(finite, values, default).astype(float, copy=False)
    if values.size < length:
        pad_value = float(values[-1]) if values.size else float(default)
        values = np.concatenate([values, np.full(length - values.size, pad_value, dtype=float)])
    elif values.size > length:
        values = values[:length]
    return values


def _datetime_seconds(df: pd.DataFrame, *, length: int, default_dt_s: float = 6.0 * 3600.0) -> tuple[np.ndarray, pd.Timestamp]:
    if "datetime" in df.columns:
        dt = pd.to_datetime(df["datetime"], errors="coerce")
        if dt.notna().all():
            t0 = dt.iloc[0]
            seconds = (dt - t0).dt.total_seconds().to_numpy(dtype=float)
            positive_deltas = np.diff(seconds)
            positive_deltas = positive_deltas[positive_deltas > 0]
            dt_s = float(np.median(positive_deltas)) if positive_deltas.size else default_dt_s
            if seconds.size < length:
                extension = seconds[-1] + dt_s * np.arange(1, length - seconds.size + 1, dtype=float)
                seconds = np.concatenate([seconds, extension])
            elif seconds.size > length:
                seconds = seconds[:length]
            return seconds, t0

    seconds = np.arange(length, dtype=float) * float(default_dt_s)
    t0 = pd.Timestamp("1970-01-01T00:00:00")
    return seconds, t0


def _build_forcing(df: pd.DataFrame, *, max_steps: int | None) -> tuple[Forcing, pd.Timestamp, np.ndarray]:
    if df.empty:
        raise ValueError("forcing DataFrame must contain at least one row")

    requested_steps = max(int(max_steps), 1) if max_steps is not None else max(df.shape[0] - 1, 1)
    length = max(df.shape[0], requested_steps + 1)

    t, t0 = _datetime_seconds(df, length=length)
    t_a = _numeric_series(df, ("t_air_c", "T_air_C", "t_a"), default=25.0, length=length)
    t_soil = _numeric_series(
        df,
        ("t_soil_c", "T_soil_C", "t_soil", "root_zone_temp_c"),
        default=22.0,
        length=length,
    )
    rh = _numeric_series(df, ("rh", "RH_percent"), default=0.6, length=length)
    if np.nanmax(rh) > 1.0:
        rh = rh / 100.0
    rh = np.clip(rh, 0.0, 1.0)

    forcing = Forcing(
        t=t,
        t_a=t_a,
        t_soil=t_soil,
        rh=rh,
        precip=_numeric_series(df, ("precip", "precip_mm"), default=0.0, length=length),
        u10=_numeric_series(df, ("u10", "wind_speed_m_s", "wind_speed_ms"), default=1.0, length=length),
        r_incom=_numeric_series(df, ("r_incom_w_m2", "r_incom", "SW_in_Wm2"), default=400.0, length=length),
        z_a=_numeric_series(df, ("z_a",), default=0.8, length=length),
    )
    theta = _numeric_series(df, ("theta_substrate",), default=0.35, length=length)
    return forcing, t0, theta


def _as_runtime_outputs(candidate: object) -> SimpleNamespace:
    return SimpleNamespace(
        t_ts=np.asarray(getattr(candidate, "t_ts"), dtype=float),
        e_ts=np.asarray(getattr(candidate, "e_ts"), dtype=float),
        g_w_ts=np.asarray(getattr(candidate, "g_w_ts"), dtype=float),
        a_n_ts=np.asarray(getattr(candidate, "a_n_ts"), dtype=float),
        r_d_ts=np.asarray(getattr(candidate, "r_d_ts"), dtype=float),
    )


class THORPReferenceAdapter:
    """Expose migrated THORP outputs through the TOMICS-Alloc DataFrame contract."""

    def __init__(
        self,
        *,
        params_factory: ParamsFactory | None = None,
        run_model: RunModel | None = None,
    ) -> None:
        self._params_factory = params_factory or _default_params_factory
        self._run_model = run_model or _default_run_model

    def simulate(self, forcing: pd.DataFrame, *, max_steps: int | None = None) -> pd.DataFrame:
        forcing_obj, t0, theta = _build_forcing(forcing, max_steps=max_steps)
        out = _as_runtime_outputs(
            self._run_model(
                params=self._params_factory(),
                forcing=forcing_obj,
                max_steps=max_steps,
            )
        )

        t_seconds = out.t_ts
        if t_seconds.size == 0:
            return pd.DataFrame(
                columns=["datetime", "theta_substrate", "water_supply_stress", "e", "g_w", "a_n", "r_d"]
            )

        idx = np.searchsorted(forcing_obj.t, t_seconds, side="left")
        idx = np.clip(idx, 0, forcing_obj.t.size - 1)

        g_w = out.g_w_ts
        finite_g_w = np.abs(g_w[np.isfinite(g_w)])
        g_w_scale = float(np.nanmax(finite_g_w)) if finite_g_w.size else 0.0
        g_w_scale = max(g_w_scale, 1e-12)
        stress = np.clip(np.abs(g_w) / g_w_scale, 0.0, 1.0)

        return pd.DataFrame(
            {
                "datetime": t0 + pd.to_timedelta(t_seconds, unit="s"),
                "theta_substrate": theta[idx],
                "water_supply_stress": stress,
                "e": out.e_ts,
                "g_w": g_w,
                "a_n": out.a_n_ts,
                "r_d": out.r_d_ts,
            }
        )
