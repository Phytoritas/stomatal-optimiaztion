from __future__ import annotations

import math
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.contracts import EnvStep

PAR_UMOL_PER_W_M2 = 4.6
_REQUIRED_COLUMNS: tuple[str, ...] = (
    "datetime",
    "T_air_C",
    "PAR_umol",
    "CO2_ppm",
    "RH_percent",
    "wind_speed_ms",
)
_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "datetime": ("Datetime", "timestamp", "time"),
    "T_air_C": ("t_air_c", "t_a"),
    "PAR_umol": ("par_umol",),
    "CO2_ppm": ("co2_ppm",),
    "RH_percent": ("rh_percent", "RH", "rh"),
    "wind_speed_ms": ("u10",),
    "SW_in_Wm2": ("r_incom_w_m2", "r_incom"),
    "T_rad_C": ("t_rad_c",),
    "n_fruits_per_truss": (),
}


def _validate_par_factor(par_umol_per_w_m2: float) -> float:
    factor = float(par_umol_per_w_m2)
    if not math.isfinite(factor) or factor <= 0:
        raise ValueError(f"par_umol_per_w_m2 must be a positive finite value, got {par_umol_per_w_m2!r}.")
    return factor


def _w_m2_to_par_umol(w_m2: float, *, par_umol_per_w_m2: float = PAR_UMOL_PER_W_M2) -> float:
    return float(w_m2) * _validate_par_factor(par_umol_per_w_m2)


def _finite_float(raw: object, *, default: float) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(value):
        return float(default)
    return value


def _read_float(row: pd.Series, names: tuple[str, ...], *, default: float) -> float:
    for name in names:
        if name in row.index:
            return _finite_float(row[name], default=default)
    return float(default)


def _read_optional_float(row: pd.Series, names: tuple[str, ...]) -> float | None:
    for name in names:
        if name not in row.index:
            continue
        try:
            value = float(row[name])
        except (TypeError, ValueError):
            continue
        if math.isfinite(value):
            return value
    return None


def _coalesce_aliases(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for canonical, aliases in _COLUMN_ALIASES.items():
        if canonical in out.columns:
            continue
        for alias in aliases:
            if alias in out.columns:
                out[canonical] = out[alias]
                break
    return out


def _prepare_forcing_dataframe(
    forcing: pd.DataFrame,
    *,
    start_datetime: datetime | None,
    default_dt_s: float,
    default_co2_ppm: float,
    default_n_fruits_per_truss: int,
) -> pd.DataFrame:
    prepared = _coalesce_aliases(forcing)

    if "datetime" not in prepared.columns:
        t0 = start_datetime or datetime(2025, 1, 1, 0, 0, 0)
        prepared["datetime"] = [t0 + timedelta(seconds=default_dt_s * index) for index in range(prepared.shape[0])]

    prepared["datetime"] = pd.to_datetime(prepared["datetime"], errors="coerce")
    if prepared["datetime"].isna().any():
        raise ValueError("Column 'datetime' contains unparsable values.")

    prepared = prepared.sort_values("datetime").reset_index(drop=True)

    if "PAR_umol" not in prepared.columns:
        if "SW_in_Wm2" not in prepared.columns:
            raise ValueError("Missing required columns: ['PAR_umol']")
        sw_in = pd.to_numeric(prepared["SW_in_Wm2"], errors="coerce").fillna(0.0).astype(float)
        prepared["PAR_umol"] = sw_in.map(_w_m2_to_par_umol)

    if "CO2_ppm" not in prepared.columns:
        prepared["CO2_ppm"] = float(default_co2_ppm)
    if "n_fruits_per_truss" not in prepared.columns:
        prepared["n_fruits_per_truss"] = int(default_n_fruits_per_truss)

    missing = [column for column in _REQUIRED_COLUMNS if column not in prepared.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    return prepared


def _default_dt_seconds(forcing: pd.DataFrame) -> float:
    if forcing.shape[0] < 2:
        return 3600.0

    dt0 = (forcing.loc[1, "datetime"] - forcing.loc[0, "datetime"]).total_seconds()
    if not math.isfinite(dt0):
        return 3600.0
    return float(min(max(dt0, 1.0), 6.0 * 3600.0))


def iter_forcing_csv(
    csv_path: str | Path,
    *,
    max_steps: int | None = None,
    start_datetime: datetime | None = None,
    default_dt_s: float = 6.0 * 3600.0,
    default_co2_ppm: float = 420.0,
    default_n_fruits_per_truss: int = 4,
) -> Iterator[EnvStep]:
    """Load CSV forcing and yield canonical EnvStep rows for the pipeline."""

    if default_dt_s <= 0:
        raise ValueError(f"default_dt_s must be > 0, got {default_dt_s!r}.")

    forcing = pd.read_csv(Path(csv_path))
    if forcing.empty:
        return

    forcing = _prepare_forcing_dataframe(
        forcing,
        start_datetime=start_datetime,
        default_dt_s=default_dt_s,
        default_co2_ppm=default_co2_ppm,
        default_n_fruits_per_truss=default_n_fruits_per_truss,
    )

    if max_steps is None:
        limit = forcing.shape[0]
    else:
        limit = min(forcing.shape[0], max(0, int(max_steps)))
    dt_default = _default_dt_seconds(forcing)
    last_calc_time: datetime | None = None

    for index in range(limit):
        row = forcing.iloc[index]
        t_step = pd.Timestamp(row["datetime"]).to_pydatetime()
        if index == 0:
            dt_s = dt_default
        elif last_calc_time is None:
            dt_s = dt_default
        else:
            dt_s = max(1.0, (t_step - last_calc_time).total_seconds())
        last_calc_time = t_step

        t_air_c = _read_float(row, ("T_air_C",), default=25.0)
        sw_in = _read_optional_float(row, ("SW_in_Wm2",))
        par_default = _w_m2_to_par_umol(sw_in) if sw_in is not None else 0.0
        par_umol = _read_float(row, ("PAR_umol",), default=par_default)
        co2_ppm = _read_float(row, ("CO2_ppm",), default=default_co2_ppm)

        rh_percent = _read_float(row, ("RH_percent",), default=70.0)
        if rh_percent <= 1.5:
            rh_percent *= 100.0
        rh_percent = min(max(rh_percent, 0.0), 100.0)

        wind_speed_ms = _read_float(row, ("wind_speed_ms",), default=1.0)
        t_rad_c = _read_optional_float(row, ("T_rad_C",))

        n_fruits_raw = _read_float(
            row,
            ("n_fruits_per_truss",),
            default=float(default_n_fruits_per_truss),
        )
        n_fruits = max(1, int(round(n_fruits_raw)))

        yield EnvStep(
            t=t_step,
            dt_s=dt_s,
            T_air_C=t_air_c,
            PAR_umol=par_umol,
            CO2_ppm=co2_ppm,
            RH_percent=rh_percent,
            wind_speed_ms=wind_speed_ms,
            SW_in_Wm2=sw_in,
            T_rad_C=t_rad_c,
            n_fruits_per_truss=n_fruits,
        )
