from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .adapters import build_harvest_update
from .contracts import FruitHarvestEvent, HarvestState
from .readiness import ready_vanthoor_stage


@dataclass(slots=True)
class VanthoorHarvestConfig:
    n_dev: int = 5
    outflow_fraction_per_day: float = 1.0
    harvest_outflow_mode: str = "explicit_last_stage_outflow"


class VanthoorBoxcarHarvestPolicy:
    family = "vanthoor_boxcar"

    def __init__(self, config: VanthoorHarvestConfig | None = None, **params: object) -> None:
        self.config = config or VanthoorHarvestConfig(**params)

    def step(self, state: HarvestState, env: dict[str, float], dt_days: float):
        frame = state.fruit_entities.copy()
        if frame.empty:
            return build_harvest_update(state, extra_diagnostics={"fruit_harvest_family": self.family})
        frame["stage_index"] = pd.to_numeric(frame.get("stage_index"), errors="coerce").fillna(0.0)
        frame["fruit_dm_g_m2"] = pd.to_numeric(frame.get("fruit_dm_g_m2"), errors="coerce").fillna(0.0)
        if "harvested_flag" not in frame.columns:
            frame["harvested_flag"] = False
        if "onplant_flag" not in frame.columns:
            frame["onplant_flag"] = True
        final_stage = frame.loc[
            frame["stage_index"].apply(
                lambda value: ready_vanthoor_stage(value, self.config.n_dev, env.get("MCFruitHar_g_m2_d"))
            )
        ].copy()
        final_stage = final_stage.loc[
            (~final_stage["harvested_flag"].fillna(False).astype(bool))
            & final_stage["onplant_flag"].fillna(True).astype(bool)
        ]
        total_final_mass = float(final_stage["fruit_dm_g_m2"].sum())
        explicit_outflow = max(float(env.get("MCFruitHar_g_m2_d", env.get("DMHar_g_m2_d", 0.0))), 0.0)
        events: list[FruitHarvestEvent] = []
        for row in final_stage.itertuples(index=False):
            available = max(float(getattr(row, "fruit_dm_g_m2", 0.0)), 0.0)
            if available <= 0.0:
                continue
            if explicit_outflow > 0.0 and total_final_mass > 0.0:
                dry_weight = explicit_outflow * (available / total_final_mass) * max(float(dt_days), 1.0)
            else:
                dry_weight = available * max(min(self.config.outflow_fraction_per_day * max(float(dt_days), 1.0), 1.0), 0.0)
            dry_weight = min(dry_weight, available)
            if dry_weight <= 0.0:
                continue
            events.append(
                FruitHarvestEvent(
                    date=state.datetime,
                    entity_id=str(row.entity_id),
                    family=self.family,
                    harvest_flux_g_m2=dry_weight,
                    harvest_count=float(getattr(row, "fruit_count", 0.0)),
                    harvest_ready_score=float(getattr(row, "stage_index", 0.0)),
                    fdmc_used=None,
                    fresh_weight_equivalent_g_m2=None,
                    dry_weight_g_m2=dry_weight,
                    notes="Explicit last-stage harvest outflow proxy for Vanthoor boxcar fruit train.",
                )
            )
        return build_harvest_update(state, fruit_events=events, extra_diagnostics={"fruit_harvest_family": self.family})


__all__ = ["VanthoorBoxcarHarvestPolicy", "VanthoorHarvestConfig"]
