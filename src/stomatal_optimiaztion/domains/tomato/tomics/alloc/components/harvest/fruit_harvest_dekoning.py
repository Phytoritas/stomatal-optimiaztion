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
            return build_harvest_update(
                state,
                extra_diagnostics={
                    "fruit_harvest_family": self.family,
                    "delay_mode": "residence_clock",
                    "readiness_basis": "fds_plus_post_maturity_residence",
                },
            )
        frame["fds"] = pd.to_numeric(frame.get("fds"), errors="coerce").fillna(0.0)
        frame["days_since_maturity"] = pd.to_numeric(frame.get("days_since_maturity"), errors="coerce").fillna(0.0)
        frame["fruit_dm_g_m2"] = pd.to_numeric(frame.get("fruit_dm_g_m2"), errors="coerce").fillna(0.0)
        frame["fruit_count"] = pd.to_numeric(frame.get("fruit_count"), errors="coerce").fillna(0.0)
        events: list[FruitHarvestEvent] = []
        dayno = float(pd.Timestamp(state.datetime).dayofyear)
        tf = float(env.get("T_air_C", env.get("TF", 23.0)))
        proxy_mode_used = False
        for row in frame.itertuples(index=False):
            onplant_flag = getattr(row, "onplant_flag", True)
            harvested_flag = getattr(row, "harvested_flag", False)
            proxy_state_flag = getattr(row, "proxy_state_flag", False)
            if pd.isna(onplant_flag):
                onplant_flag = True
            if pd.isna(harvested_flag):
                harvested_flag = False
            if pd.isna(proxy_state_flag):
                proxy_state_flag = False
            if not bool(onplant_flag) or bool(harvested_flag):
                continue
            fds_value = float(getattr(row, "fds", 0.0))
            maturity_days = float(getattr(row, "days_since_maturity", 0.0))
            if not ready_dekoning_fds(
                fds_value,
                threshold=self.config.fds_harvest_threshold,
                days_since_maturity=maturity_days,
                harvest_delay_days=self.config.harvest_delay_days,
            ):
                continue
            dry_weight = max(float(getattr(row, "fruit_dm_g_m2", 0.0)), 0.0)
            if dry_weight <= 0.0:
                continue
            proxy_mode_used = proxy_mode_used or bool(proxy_state_flag)
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
                    removes_entity=True,
                    removal_fraction=1.0,
                    partial_outflow_flag=False,
                    notes="FDS-based research harvest with De Koning FDMC helpers and post-maturity residence-clock gating.",
                )
            )
        return build_harvest_update(
            state,
            fruit_events=events,
            extra_diagnostics={
                "fruit_harvest_family": self.family,
                "delay_mode": "residence_clock",
                "readiness_basis": "fds_plus_post_maturity_residence",
                "proxy_mode_used": proxy_mode_used,
                "fds_proxy_used": proxy_mode_used,
            },
        )


DeKoningFruitHarvestPolicy = DeKoningFdsHarvestPolicy


__all__ = [
    "DeKoningFdsHarvestPolicy",
    "DeKoningFruitHarvestPolicy",
    "DeKoningHarvestConfig",
]
