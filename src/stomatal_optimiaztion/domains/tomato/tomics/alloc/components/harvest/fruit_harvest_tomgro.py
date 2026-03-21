from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .adapters import build_harvest_update
from .contracts import FruitHarvestEvent, HarvestState
from .readiness import ready_tomgro_ageclass


@dataclass(slots=True)
class TomgroHarvestConfig:
    mature_class_index: int = 20
    mature_pool_harvest_mode: str = "whole_mature_class"


class TomgroAgeclassHarvestPolicy:
    family = "tomgro_ageclass"

    def __init__(self, config: TomgroHarvestConfig | None = None, **params: object) -> None:
        self.config = config or TomgroHarvestConfig(**params)

    def step(self, state: HarvestState, env: dict[str, float], dt_days: float):
        frame = state.fruit_entities.copy()
        if frame.empty:
            return build_harvest_update(state, extra_diagnostics={"fruit_harvest_family": self.family})
        frame["age_class"] = pd.to_numeric(frame.get("age_class"), errors="coerce").fillna(0.0)
        frame["fruit_dm_g_m2"] = pd.to_numeric(frame.get("fruit_dm_g_m2"), errors="coerce").fillna(0.0)
        total_proxy_outflow = max(float(env.get("mature_pool_delta_g_m2", 0.0)), 0.0)
        mature_frame = frame.loc[frame["age_class"].apply(lambda value: ready_tomgro_ageclass(value, self.config.mature_class_index))]
        mature_total = float(mature_frame["fruit_dm_g_m2"].sum())
        events: list[FruitHarvestEvent] = []
        for row in mature_frame.itertuples(index=False):
            dry_weight = max(float(getattr(row, "fruit_dm_g_m2", 0.0)), 0.0)
            if dry_weight <= 0.0:
                continue
            if self.config.mature_pool_harvest_mode == "mature_pool_delta" and total_proxy_outflow > 0.0 and mature_total > 0.0:
                dry_weight = min(dry_weight, total_proxy_outflow * (dry_weight / mature_total))
            events.append(
                FruitHarvestEvent(
                    date=state.datetime,
                    entity_id=str(row.entity_id),
                    family=self.family,
                    harvest_flux_g_m2=dry_weight,
                    harvest_count=float(getattr(row, "fruit_count", 0.0)),
                    harvest_ready_score=float(getattr(row, "age_class", 0.0)),
                    fdmc_used=None,
                    fresh_weight_equivalent_g_m2=None,
                    dry_weight_g_m2=dry_weight,
                    notes="Research proxy: mature age class or mature-pool outflow harvest.",
                )
            )
        return build_harvest_update(state, fruit_events=events, extra_diagnostics={"fruit_harvest_family": self.family})


__all__ = ["TomgroAgeclassHarvestPolicy", "TomgroHarvestConfig"]
