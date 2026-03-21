from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import pandas as pd


HARVEST_FRUIT_COLUMNS = [
    "entity_id",
    "family_semantics",
    "truss_id",
    "fruit_position",
    "age_class",
    "stage_index",
    "tdvs",
    "fds",
    "fruit_dm_g_m2",
    "fruit_count",
    "onplant_flag",
    "harvested_flag",
    "potential_weight_proxy_g_m2",
]

HARVEST_LEAF_COLUMNS = [
    "entity_id",
    "linked_truss_id",
    "vpos",
    "vds",
    "leaf_dm_g_m2",
    "leaf_area_m2_m2",
    "onplant_flag",
    "harvested_flag",
]


def _ensure_frame(frame: pd.DataFrame | None, columns: list[str]) -> pd.DataFrame:
    if frame is None:
        return pd.DataFrame(columns=columns)
    out = frame.copy()
    for column in columns:
        if column not in out.columns:
            out[column] = pd.NA
    return out[columns + [column for column in out.columns if column not in columns]]


FRUIT_ENTITY_COLUMNS = HARVEST_FRUIT_COLUMNS
LEAF_ENTITY_COLUMNS = HARVEST_LEAF_COLUMNS


def ensure_entity_frame(frame: pd.DataFrame | None, columns: list[str]) -> pd.DataFrame:
    return _ensure_frame(frame, columns)


@dataclass(frozen=True, slots=True)
class HarvestState:
    datetime: pd.Timestamp
    dt_days: float
    floor_area_basis: bool
    plants_per_m2: float
    lai: float | None
    cbuf_g_m2: float | None
    fruit_entities: pd.DataFrame
    leaf_entities: pd.DataFrame
    stem_root_state: dict[str, float] | None
    harvested_fruit_cumulative_g_m2: float
    harvested_leaf_cumulative_g_m2: float
    diagnostics: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "fruit_entities", _ensure_frame(self.fruit_entities, HARVEST_FRUIT_COLUMNS))
        object.__setattr__(self, "leaf_entities", _ensure_frame(self.leaf_entities, HARVEST_LEAF_COLUMNS))

    def with_updates(
        self,
        *,
        fruit_entities: pd.DataFrame | None = None,
        leaf_entities: pd.DataFrame | None = None,
        harvested_fruit_cumulative_g_m2: float | None = None,
        harvested_leaf_cumulative_g_m2: float | None = None,
        diagnostics: dict[str, float] | None = None,
        lai: float | None = None,
    ) -> "HarvestState":
        return HarvestState(
            datetime=self.datetime,
            dt_days=self.dt_days,
            floor_area_basis=self.floor_area_basis,
            plants_per_m2=self.plants_per_m2,
            lai=self.lai if lai is None else lai,
            cbuf_g_m2=self.cbuf_g_m2,
            fruit_entities=self.fruit_entities if fruit_entities is None else fruit_entities,
            leaf_entities=self.leaf_entities if leaf_entities is None else leaf_entities,
            stem_root_state=self.stem_root_state,
            harvested_fruit_cumulative_g_m2=(
                self.harvested_fruit_cumulative_g_m2
                if harvested_fruit_cumulative_g_m2 is None
                else float(harvested_fruit_cumulative_g_m2)
            ),
            harvested_leaf_cumulative_g_m2=(
                self.harvested_leaf_cumulative_g_m2
                if harvested_leaf_cumulative_g_m2 is None
                else float(harvested_leaf_cumulative_g_m2)
            ),
            diagnostics={**self.diagnostics, **(diagnostics or {})},
        )


@dataclass(frozen=True, slots=True)
class FruitHarvestEvent:
    date: pd.Timestamp
    entity_id: str
    family: str
    harvest_flux_g_m2: float
    harvest_count: float
    harvest_ready_score: float
    fdmc_used: float | None
    fresh_weight_equivalent_g_m2: float | None
    dry_weight_g_m2: float
    notes: str = ""


@dataclass(frozen=True, slots=True)
class LeafHarvestEvent:
    date: pd.Timestamp
    entity_id: str
    family: str
    leaf_harvest_flux_g_m2: float
    reason: str
    linked_truss_id: str | None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class HarvestUpdate:
    updated_state: HarvestState
    fruit_harvest_flux_g_m2_d: float
    leaf_harvest_flux_g_m2_d: float
    fruit_harvest_event_count: int
    leaf_harvest_event_count: int
    mass_balance_error: float
    diagnostics: dict[str, float] = field(default_factory=dict)


class HarvestPolicy(Protocol):
    def step(self, state: HarvestState, env: dict[str, float], dt_days: float) -> HarvestUpdate: ...


class LeafHarvestPolicy(Protocol):
    def step(self, state: HarvestState, env: dict[str, float], dt_days: float) -> HarvestUpdate: ...


__all__ = [
    "ensure_entity_frame",
    "FRUIT_ENTITY_COLUMNS",
    "HARVEST_FRUIT_COLUMNS",
    "HARVEST_LEAF_COLUMNS",
    "LEAF_ENTITY_COLUMNS",
    "FruitHarvestEvent",
    "HarvestPolicy",
    "HarvestState",
    "HarvestUpdate",
    "LeafHarvestEvent",
    "LeafHarvestPolicy",
]
