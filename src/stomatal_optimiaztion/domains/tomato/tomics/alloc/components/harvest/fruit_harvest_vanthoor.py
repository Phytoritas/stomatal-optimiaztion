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
    harvest_delay_days: float = 0.0
    residence_outflow_days: float | None = None
    harvest_outflow_mode: str = "explicit_last_stage_outflow"


class VanthoorBoxcarHarvestPolicy:
    family = "vanthoor_boxcar"

    def __init__(self, config: VanthoorHarvestConfig | None = None, **params: object) -> None:
        self.config = config or VanthoorHarvestConfig(**params)

    def step(self, state: HarvestState, env: dict[str, float], dt_days: float):
        frame = state.fruit_entities.copy()
        if frame.empty:
            return build_harvest_update(
                state,
                extra_diagnostics={
                    "fruit_harvest_family": self.family,
                    "proxy_mode_used": False,
                    "explicit_outflow_used": False,
                    "residence_outflow_used": False,
                },
            )
        frame["stage_index"] = pd.to_numeric(frame.get("stage_index"), errors="coerce").fillna(0.0)
        frame["fruit_dm_g_m2"] = pd.to_numeric(frame.get("fruit_dm_g_m2"), errors="coerce").fillna(0.0)
        frame["final_stage_residence_days"] = pd.to_numeric(
            frame.get("final_stage_residence_days"),
            errors="coerce",
        ).fillna(0.0)
        frame["explicit_outflow_capacity_g_m2_d"] = pd.to_numeric(
            frame.get("explicit_outflow_capacity_g_m2_d"),
            errors="coerce",
        ).fillna(0.0)
        frame["onplant_flag"] = frame.get("onplant_flag", True).fillna(True).astype(bool)
        frame["harvested_flag"] = frame.get("harvested_flag", False).fillna(False).astype(bool)
        explicit_outflow = max(float(env.get("MCFruitHar_g_m2_d", env.get("DMHar_g_m2_d", 0.0))), 0.0)
        if explicit_outflow <= 0.0:
            explicit_outflow = max(float((frame["explicit_outflow_capacity_g_m2_d"] * max(float(dt_days), 0.0)).sum()), 0.0)
        final_stage = frame.loc[
            frame.apply(
                lambda row: bool(row["onplant_flag"])
                and (not bool(row["harvested_flag"]))
                and ready_vanthoor_stage(
                    row["stage_index"],
                    self.config.n_dev,
                    explicit_outflow=row["explicit_outflow_capacity_g_m2_d"] if explicit_outflow <= 0.0 else explicit_outflow,
                    final_stage_residence_days=row["final_stage_residence_days"],
                    harvest_delay_days=self.config.harvest_delay_days,
                ),
                axis=1,
            )
        ].copy()
        total_final_mass = float(final_stage["fruit_dm_g_m2"].sum())
        residence_outflow_days = self.config.residence_outflow_days
        if residence_outflow_days is None:
            fraction = max(float(self.config.outflow_fraction_per_day), 1e-9)
            residence_outflow_days = 1.0 / fraction
        residence_days = max(float(residence_outflow_days), 1e-9)
        explicit_outflow_used = explicit_outflow > 0.0 and total_final_mass > 0.0
        residence_outflow_used = (not explicit_outflow_used) and total_final_mass > 0.0
        proxy_mode_used = bool(frame.get("proxy_state_flag", pd.Series(dtype=bool)).fillna(False).astype(bool).any())
        events: list[FruitHarvestEvent] = []
        for row in final_stage.itertuples(index=False):
            available = max(float(getattr(row, "fruit_dm_g_m2", 0.0)), 0.0)
            if available <= 0.0:
                continue
            if explicit_outflow_used:
                dry_weight = explicit_outflow * (available / total_final_mass) * max(float(dt_days), 0.0)
            else:
                dry_weight = available * max(min(max(float(dt_days), 0.0) / residence_days, 1.0), 0.0)
            dry_weight = min(dry_weight, available)
            if dry_weight <= 0.0:
                continue
            removal_fraction = 0.0 if available <= 1e-12 else min(max(dry_weight / available, 0.0), 1.0)
            partial_outflow = removal_fraction < 0.999999
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
                    removes_entity=not partial_outflow,
                    removal_fraction=removal_fraction,
                    partial_outflow_flag=partial_outflow,
                    notes="Explicit last-stage harvest outflow proxy for Vanthoor boxcar fruit train.",
                )
            )
        return build_harvest_update(
            state,
            fruit_events=events,
            extra_diagnostics={
                "fruit_harvest_family": self.family,
                "final_stage_mass_g_m2": total_final_mass,
                "explicit_outflow_used": explicit_outflow_used,
                "residence_outflow_used": residence_outflow_used,
                "proxy_mode_used": proxy_mode_used,
            },
        )


__all__ = ["VanthoorBoxcarHarvestPolicy", "VanthoorHarvestConfig"]
