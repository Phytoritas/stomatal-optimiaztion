from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .adapters import build_harvest_update
from .contracts import FruitHarvestEvent, HarvestState
from .readiness import ready_tomsim_truss


@dataclass(slots=True)
class TomsimHarvestConfig:
    tdvs_harvest_threshold: float = 1.0
    harvest_delay_days: float = 0.0
    tdvs_delay_per_day: float = 0.03


class TomsimTrussHarvestPolicy:
    family = "tomsim_truss"

    def __init__(self, config: TomsimHarvestConfig | None = None, **params: object) -> None:
        self.config = config or TomsimHarvestConfig(**params)

    def step(self, state: HarvestState, env: dict[str, float], dt_days: float):
        threshold = self.config.tdvs_harvest_threshold + self.config.harvest_delay_days * self.config.tdvs_delay_per_day
        frame = state.fruit_entities.copy()
        if frame.empty:
            return build_harvest_update(state, extra_diagnostics={"fruit_harvest_family": self.family})
        frame["tdvs"] = pd.to_numeric(frame.get("tdvs"), errors="coerce").fillna(0.0)
        frame["fruit_dm_g_m2"] = pd.to_numeric(frame.get("fruit_dm_g_m2"), errors="coerce").fillna(0.0)
        frame["fruit_count"] = pd.to_numeric(frame.get("fruit_count"), errors="coerce").fillna(0.0)
        events: list[FruitHarvestEvent] = []
        for row in frame.itertuples(index=False):
            if not bool(getattr(row, "onplant_flag", True)):
                continue
            if not ready_tomsim_truss(getattr(row, "tdvs", 0.0), threshold=threshold):
                continue
            dry_weight = max(float(getattr(row, "fruit_dm_g_m2", 0.0)), 0.0)
            if dry_weight <= 0.0:
                continue
            events.append(
                FruitHarvestEvent(
                    date=state.datetime,
                    entity_id=str(row.entity_id),
                    family=self.family,
                    harvest_flux_g_m2=dry_weight,
                    harvest_count=float(getattr(row, "fruit_count", 0.0)),
                    harvest_ready_score=float(getattr(row, "tdvs", 0.0)),
                    fdmc_used=None,
                    fresh_weight_equivalent_g_m2=None,
                    dry_weight_g_m2=dry_weight,
                    notes="Whole ready truss harvest.",
                )
            )
        return build_harvest_update(state, fruit_events=events, extra_diagnostics={"fruit_harvest_family": self.family})


__all__ = ["TomsimHarvestConfig", "TomsimTrussHarvestPolicy"]
