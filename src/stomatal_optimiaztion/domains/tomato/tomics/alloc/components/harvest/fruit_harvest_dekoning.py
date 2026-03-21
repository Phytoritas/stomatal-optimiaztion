from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .adapters import build_harvest_update
from .contracts import FruitHarvestEvent, HarvestState
from .fdmc import fdmc_family_dispatch
from .readiness import ready_dekoning_fds


@dataclass(slots=True)
class DeKoningHarvestConfig:
    fds_harvest_threshold: float = 1.0
    harvest_delay_days: float = 0.0
    fds_delay_per_day: float = 0.03
    fdmc_mode: str = "dekoning_fds"
    r_fdmc: float = 1.0
    ec: float = 0.3


class DeKoningFdsHarvestPolicy:
    family = "dekoning_fds"

    def __init__(self, config: DeKoningHarvestConfig | None = None, **params: object) -> None:
        self.config = config or DeKoningHarvestConfig(**params)

    def step(self, state: HarvestState, env: dict[str, float], dt_days: float):
        frame = state.fruit_entities.copy()
        if frame.empty:
            return build_harvest_update(state, extra_diagnostics={"fruit_harvest_family": self.family})
        threshold = self.config.fds_harvest_threshold + self.config.harvest_delay_days * self.config.fds_delay_per_day
        frame["fds"] = pd.to_numeric(frame.get("fds"), errors="coerce").fillna(0.0)
        frame["fruit_dm_g_m2"] = pd.to_numeric(frame.get("fruit_dm_g_m2"), errors="coerce").fillna(0.0)
        frame["fruit_count"] = pd.to_numeric(frame.get("fruit_count"), errors="coerce").fillna(0.0)
        events: list[FruitHarvestEvent] = []
        dayno = float(pd.Timestamp(state.datetime).dayofyear)
        tf = float(env.get("T_air_C", env.get("TF", 23.0)))
        for row in frame.itertuples(index=False):
            if bool(getattr(row, "harvested_flag", False)):
                continue
            if not bool(getattr(row, "onplant_flag", True)):
                continue
            fds_value = float(getattr(row, "fds", 0.0))
            if not ready_dekoning_fds(fds_value, threshold=threshold):
                continue
            dry_weight = max(float(getattr(row, "fruit_dm_g_m2", 0.0)), 0.0)
            if dry_weight <= 0.0:
                continue
            fdmc_used = fdmc_family_dispatch(
                self.config.fdmc_mode,
                fds=fds_value,
                dayno=dayno,
                ec=float(env.get("EC", self.config.ec)),
                tf=tf,
                r_fdmc=float(env.get("r_fdmc", self.config.r_fdmc)),
            )
            fresh_weight = dry_weight * 100.0 / fdmc_used if fdmc_used > 0.0 else None
            events.append(
                FruitHarvestEvent(
                    date=state.datetime,
                    entity_id=str(row.entity_id),
                    family=self.family,
                    harvest_flux_g_m2=dry_weight,
                    harvest_count=float(getattr(row, "fruit_count", 0.0)),
                    harvest_ready_score=fds_value,
                    fdmc_used=fdmc_used,
                    fresh_weight_equivalent_g_m2=fresh_weight,
                    dry_weight_g_m2=dry_weight,
                    notes="FDS-based research harvest with De Koning FDMC helpers.",
                )
            )
        return build_harvest_update(state, fruit_events=events, extra_diagnostics={"fruit_harvest_family": self.family})


DeKoningFruitHarvestPolicy = DeKoningFdsHarvestPolicy


__all__ = [
    "DeKoningFdsHarvestPolicy",
    "DeKoningFruitHarvestPolicy",
    "DeKoningHarvestConfig",
]
