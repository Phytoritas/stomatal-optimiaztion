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
        frame = state.fruit_entities.copy()
        if frame.empty:
            return build_harvest_update(
                state,
                extra_diagnostics={
                    "fruit_harvest_family": self.family,
                    "delay_mode": "residence_clock",
                    "readiness_basis": "tdvs_plus_post_maturity_residence",
                },
            )
        frame["tdvs"] = pd.to_numeric(frame.get("tdvs"), errors="coerce").fillna(0.0)
        frame["days_since_maturity"] = pd.to_numeric(frame.get("days_since_maturity"), errors="coerce").fillna(0.0)
        frame["fruit_dm_g_m2"] = pd.to_numeric(frame.get("fruit_dm_g_m2"), errors="coerce").fillna(0.0)
        frame["fruit_count"] = pd.to_numeric(frame.get("fruit_count"), errors="coerce").fillna(0.0)
        events: list[FruitHarvestEvent] = []
        for row in frame.itertuples(index=False):
            onplant_flag = getattr(row, "onplant_flag", True)
            harvested_flag = getattr(row, "harvested_flag", False)
            if pd.isna(onplant_flag):
                onplant_flag = True
            if pd.isna(harvested_flag):
                harvested_flag = False
            if not bool(onplant_flag) or bool(harvested_flag):
                continue
            tdvs_value = float(getattr(row, "tdvs", 0.0))
            maturity_days = float(getattr(row, "days_since_maturity", 0.0))
            if not ready_tomsim_truss(
                tdvs_value,
                threshold=self.config.tdvs_harvest_threshold,
                days_since_maturity=maturity_days,
                harvest_delay_days=self.config.harvest_delay_days,
            ):
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
                    harvest_ready_score=tdvs_value,
                    fdmc_used=None,
                    fresh_weight_equivalent_g_m2=None,
                    dry_weight_g_m2=dry_weight,
                    removes_entity=True,
                    removal_fraction=1.0,
                    partial_outflow_flag=False,
                    notes="Whole ready truss harvest with post-maturity residence-clock gating.",
                )
            )
        return build_harvest_update(
            state,
            fruit_events=events,
            extra_diagnostics={
                "fruit_harvest_family": self.family,
                "delay_mode": "residence_clock",
                "readiness_basis": "tdvs_plus_post_maturity_residence",
            },
        )


__all__ = ["TomsimHarvestConfig", "TomsimTrussHarvestPolicy"]
