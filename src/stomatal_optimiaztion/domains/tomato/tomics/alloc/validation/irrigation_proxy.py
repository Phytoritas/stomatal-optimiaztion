from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class IrrigationProxyConfig:
    morning_hours: tuple[int, ...] = (6, 7, 8)
    midday_hours: tuple[int, ...] = (12, 13, 14)
    par_threshold_umol: float = 50.0
    demand_threshold: float = 0.35


def infer_irrigation_proxy(
    forcing_df: pd.DataFrame,
    *,
    demand_column: str = "demand_index",
    config: IrrigationProxyConfig | None = None,
) -> pd.DataFrame:
    cfg = config or IrrigationProxyConfig()
    frame = forcing_df.copy()
    frame["datetime"] = pd.to_datetime(frame["datetime"], errors="coerce")
    hours = frame["datetime"].dt.hour.fillna(0).astype(int)
    demand = pd.to_numeric(frame.get(demand_column), errors="coerce").fillna(0.0)
    par = pd.to_numeric(frame.get("PAR_umol"), errors="coerce").fillna(0.0)
    within_window = hours.isin(cfg.morning_hours + cfg.midday_hours)
    recharge = within_window & (demand >= cfg.demand_threshold) & (par >= cfg.par_threshold_umol)
    frame["irrigation_proxy_flag"] = recharge.astype(int)
    return frame


__all__ = [
    "IrrigationProxyConfig",
    "infer_irrigation_proxy",
]
