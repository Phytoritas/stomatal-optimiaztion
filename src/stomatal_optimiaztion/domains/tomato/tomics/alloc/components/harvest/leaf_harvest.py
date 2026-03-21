from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .adapters import build_harvest_update
from .contracts import HarvestState, LeafHarvestEvent


def _linked_stage_map(state: HarvestState, stage_column: str = "tdvs") -> dict[float, float]:
    frame = state.fruit_entities.copy()
    if frame.empty:
        return {}
    frame["truss_id"] = pd.to_numeric(frame.get("truss_id"), errors="coerce")
    frame[stage_column] = pd.to_numeric(frame.get(stage_column), errors="coerce")
    grouped = frame.dropna(subset=["truss_id"]).groupby("truss_id")[stage_column].max()
    return {float(key): float(value) for key, value in grouped.items()}


@dataclass(slots=True)
class LinkedTrussStageLeafHarvestConfig:
    linked_leaf_stage: float = 0.9


class LinkedTrussStageLeafHarvestPolicy:
    family = "linked_truss_stage"

    def __init__(self, config: LinkedTrussStageLeafHarvestConfig | None = None, **params: object) -> None:
        self.config = config or LinkedTrussStageLeafHarvestConfig(**params)

    def step(self, state: HarvestState, env: dict[str, float], dt_days: float):
        linked_stage = _linked_stage_map(state, "tdvs")
        frame = state.leaf_entities.copy()
        frame["leaf_dm_g_m2"] = pd.to_numeric(frame.get("leaf_dm_g_m2"), errors="coerce").fillna(0.0)
        events: list[LeafHarvestEvent] = []
        for row in frame.itertuples(index=False):
            truss_id = float(getattr(row, "linked_truss_id", 0.0) or 0.0)
            if linked_stage.get(truss_id, float(getattr(row, "vds", 0.0))) < self.config.linked_leaf_stage:
                continue
            dry_weight = max(float(getattr(row, "leaf_dm_g_m2", 0.0)), 0.0)
            if dry_weight <= 0.0:
                continue
            events.append(
                LeafHarvestEvent(
                    date=state.datetime,
                    entity_id=str(row.entity_id),
                    family=self.family,
                    leaf_harvest_flux_g_m2=dry_weight,
                    reason="linked_truss_stage",
                    linked_truss_id=truss_id,
                    notes="Whole linked vegetative unit leaf removal.",
                )
            )
        return build_harvest_update(state, leaf_events=events, extra_diagnostics={"leaf_harvest_family": self.family})


@dataclass(slots=True)
class VegetativeUnitLeafHarvestConfig:
    colour_threshold: float = 0.9
    pruning_lag_days: float = 0.0


class VegetativeUnitLeafHarvestPolicy:
    family = "vegetative_unit_pruning"

    def __init__(self, config: VegetativeUnitLeafHarvestConfig | None = None, **params: object) -> None:
        self.config = config or VegetativeUnitLeafHarvestConfig(**params)

    def step(self, state: HarvestState, env: dict[str, float], dt_days: float):
        linked_stage = _linked_stage_map(state, "fds")
        frame = state.leaf_entities.copy()
        frame["leaf_dm_g_m2"] = pd.to_numeric(frame.get("leaf_dm_g_m2"), errors="coerce").fillna(0.0)
        threshold = self.config.colour_threshold + 0.03 * self.config.pruning_lag_days
        events: list[LeafHarvestEvent] = []
        for row in frame.itertuples(index=False):
            truss_id = float(getattr(row, "linked_truss_id", 0.0) or 0.0)
            if linked_stage.get(truss_id, 0.0) < threshold:
                continue
            dry_weight = max(float(getattr(row, "leaf_dm_g_m2", 0.0)), 0.0)
            if dry_weight <= 0.0:
                continue
            events.append(
                LeafHarvestEvent(
                    date=state.datetime,
                    entity_id=str(row.entity_id),
                    family=self.family,
                    leaf_harvest_flux_g_m2=dry_weight,
                    reason="first_fruit_colouring",
                    linked_truss_id=truss_id,
                    notes="Vegetative unit pruning linked to corresponding truss colouring proxy.",
                )
            )
        return build_harvest_update(state, leaf_events=events, extra_diagnostics={"leaf_harvest_family": self.family})


@dataclass(slots=True)
class MaxLaiPruningConfig:
    max_lai: float = 3.0


class MaxLaiPruningFlowPolicy:
    family = "max_lai_pruning_flow"

    def __init__(self, config: MaxLaiPruningConfig | None = None, **params: object) -> None:
        self.config = config or MaxLaiPruningConfig(**params)

    def step(self, state: HarvestState, env: dict[str, float], dt_days: float):
        current_lai = float(state.lai or 0.0)
        if current_lai <= self.config.max_lai or state.leaf_entities.empty:
            return build_harvest_update(state, extra_diagnostics={"leaf_harvest_family": self.family})
        frame = state.leaf_entities.copy()
        frame["leaf_dm_g_m2"] = pd.to_numeric(frame.get("leaf_dm_g_m2"), errors="coerce").fillna(0.0)
        frame["leaf_area_m2_m2"] = pd.to_numeric(frame.get("leaf_area_m2_m2"), errors="coerce").fillna(0.0)
        frame = frame.sort_values(["linked_truss_id", "vpos"], ascending=False, na_position="last")
        excess_lai = current_lai - self.config.max_lai
        events: list[LeafHarvestEvent] = []
        for row in frame.itertuples(index=False):
            if excess_lai <= 1e-9:
                break
            leaf_area = max(float(getattr(row, "leaf_area_m2_m2", 0.0)), 0.0)
            leaf_dm = max(float(getattr(row, "leaf_dm_g_m2", 0.0)), 0.0)
            if leaf_area <= 0.0 or leaf_dm <= 0.0:
                continue
            removal_fraction = min(excess_lai / leaf_area, 1.0)
            removal_dm = leaf_dm * removal_fraction
            events.append(
                LeafHarvestEvent(
                    date=state.datetime,
                    entity_id=str(row.entity_id),
                    family=self.family,
                    leaf_harvest_flux_g_m2=removal_dm,
                    reason="max_lai_pruning",
                    linked_truss_id=float(getattr(row, "linked_truss_id", 0.0) or 0.0),
                    notes="Pruning flow to enforce LAI ceiling.",
                )
            )
            excess_lai = max(excess_lai - leaf_area * removal_fraction, 0.0)
        return build_harvest_update(state, leaf_events=events, extra_diagnostics={"leaf_harvest_family": self.family})


VegetativeUnitPruningPolicy = VegetativeUnitLeafHarvestPolicy


__all__ = [
    "LinkedTrussStageLeafHarvestConfig",
    "LinkedTrussStageLeafHarvestPolicy",
    "MaxLaiPruningConfig",
    "MaxLaiPruningFlowPolicy",
    "VegetativeUnitLeafHarvestConfig",
    "VegetativeUnitLeafHarvestPolicy",
    "VegetativeUnitPruningPolicy",
]
