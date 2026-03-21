from __future__ import annotations

import json
from collections.abc import Mapping

import pandas as pd

from .contracts import FRUIT_ENTITY_COLUMNS, LEAF_ENTITY_COLUMNS, HarvestState, ensure_entity_frame


def _as_series(row: pd.Series | Mapping[str, object] | None) -> pd.Series | None:
    if row is None:
        return None
    if isinstance(row, pd.Series):
        return row
    return pd.Series(dict(row))


def _float_from(series: pd.Series, key: str, default: float = 0.0) -> float:
    value = series.get(key, default)
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(default if pd.isna(numeric) else numeric)


def _bool_series(frame: pd.DataFrame, column: str, default: bool) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([default] * len(frame), index=frame.index, dtype=bool)
    normalized = frame[column]
    if normalized.dtype == bool:
        return normalized.fillna(default)
    text = normalized.astype("string").str.strip().str.lower()
    mapped = text.map({"true": True, "false": False, "1": True, "0": False})
    return mapped.fillna(default).astype(bool)


def _default_maturity_basis(frame: pd.DataFrame) -> pd.Series:
    if "maturity_basis" in frame.columns:
        return frame["maturity_basis"].fillna("tdvs").astype("string")
    if "fds" in frame.columns and pd.to_numeric(frame["fds"], errors="coerce").notna().any():
        return pd.Series(["fds"] * len(frame), index=frame.index, dtype="string")
    if "age_class" in frame.columns and pd.to_numeric(frame["age_class"], errors="coerce").notna().any():
        return pd.Series(["age_class"] * len(frame), index=frame.index, dtype="string")
    if "stage_index" in frame.columns and pd.to_numeric(frame["stage_index"], errors="coerce").notna().any():
        return pd.Series(["stage_index"] * len(frame), index=frame.index, dtype="string")
    return pd.Series(["tdvs"] * len(frame), index=frame.index, dtype="string")


def _infer_fruit_lifecycle_flags(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    normalized = frame.copy()
    normalized["tdvs"] = pd.to_numeric(normalized.get("tdvs"), errors="coerce").fillna(0.0)
    normalized["fds"] = pd.to_numeric(normalized.get("fds"), errors="coerce").fillna(normalized["tdvs"])
    normalized["age_class"] = pd.to_numeric(normalized.get("age_class"), errors="coerce").fillna(0.0)
    normalized["stage_index"] = pd.to_numeric(normalized.get("stage_index"), errors="coerce").fillna(0.0)
    if "sink_active_flag" not in normalized.columns:
        normalized["sink_active_flag"] = _bool_series(normalized, "active", True)
    else:
        normalized["sink_active_flag"] = _bool_series(normalized, "sink_active_flag", True)
    mature_default = (
        (normalized["tdvs"] >= 1.0)
        | (normalized["fds"] >= 1.0)
        | (normalized["age_class"] >= 20.0)
        | (normalized["stage_index"] >= 5.0)
        | (~normalized["sink_active_flag"])
    )
    if "mature_flag" not in normalized.columns:
        normalized["mature_flag"] = mature_default.astype(bool)
    else:
        normalized["mature_flag"] = _bool_series(normalized, "mature_flag", False) | mature_default
    if "harvest_ready_flag" not in normalized.columns:
        normalized["harvest_ready_flag"] = normalized["mature_flag"].astype(bool)
    else:
        normalized["harvest_ready_flag"] = _bool_series(normalized, "harvest_ready_flag", False) | normalized[
            "mature_flag"
        ].astype(bool)
    normalized["onplant_flag"] = _bool_series(normalized, "onplant_flag", True)
    normalized["harvested_flag"] = _bool_series(normalized, "harvested_flag", False)
    if "removal_reason" not in normalized.columns:
        normalized["removal_reason"] = ""
    else:
        normalized["removal_reason"] = normalized["removal_reason"].fillna("").astype("string")
    normalized["maturity_basis"] = _default_maturity_basis(normalized)
    return normalized


def _parse_truss_payload(series: pd.Series) -> pd.DataFrame:
    payload = series.get("truss_cohorts_json", "")
    records: list[dict[str, object]] = []
    if isinstance(payload, str) and payload.strip():
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            parsed = []
        if isinstance(parsed, list):
            records = [record for record in parsed if isinstance(record, dict)]
    if not records:
        fruit_dm = _float_from(series, "fruit_dry_weight_g_m2", 0.0)
        if fruit_dm <= 0.0:
            return pd.DataFrame(columns=FRUIT_ENTITY_COLUMNS)
        records = [
            {
                "entity_id": "fruit_bulk_001",
                "family_semantics": str(series.get("harvest_family_semantics", "bulk_fruit")),
                "truss_id": 1.0,
                "fruit_position": 1.0,
                "age_class": _float_from(series, "age_class", 1.0),
                "stage_index": _float_from(series, "stage_index", 1.0),
                "tdvs": _float_from(series, "mean_truss_tdvs", 0.0),
                "fds": _float_from(series, "mean_truss_tdvs", 0.0),
                "fruit_dm_g_m2": fruit_dm,
                "fruit_count": max(_float_from(series, "n_fruits_per_truss", 1.0), 1.0),
                "sink_active_flag": True,
                "mature_flag": False,
                "harvest_ready_flag": False,
                "onplant_flag": True,
                "harvested_flag": False,
                "removal_reason": "",
                "maturity_basis": "tdvs",
                "potential_weight_proxy_g_m2": fruit_dm,
            }
        ]
    frame = pd.DataFrame(records)
    if "family_semantics" not in frame.columns:
        frame["family_semantics"] = str(series.get("harvest_family_semantics", "unknown"))
    frame = _infer_fruit_lifecycle_flags(frame)
    return ensure_entity_frame(frame, FRUIT_ENTITY_COLUMNS)


def _synthesize_leaf_entities(series: pd.Series, fruit_entities: pd.DataFrame) -> pd.DataFrame:
    leaf_dm = _float_from(series, "leaf_dry_weight_g_m2", 0.0)
    lai = _float_from(series, "LAI", 0.0)
    if leaf_dm <= 0.0 and lai <= 0.0:
        return pd.DataFrame(columns=LEAF_ENTITY_COLUMNS)
    truss_ids = sorted(
        {
            int(float(value))
            for value in pd.to_numeric(fruit_entities.get("truss_id"), errors="coerce").dropna().tolist()
            if float(value) >= 1.0
        }
    )
    if not truss_ids:
        fallback = max(int(round(_float_from(series, "truss_count", 1.0))), 1)
        truss_ids = list(range(1, fallback + 1))
    per_leaf_dm = leaf_dm / len(truss_ids) if truss_ids else 0.0
    per_leaf_area = lai / len(truss_ids) if truss_ids else 0.0
    tdvs_by_truss = {}
    if not fruit_entities.empty:
        grouped = fruit_entities.groupby("truss_id")["tdvs"].max()
        tdvs_by_truss = {int(float(key)): float(value) for key, value in grouped.items()}
    records = [
        {
            "entity_id": f"leaf_unit_{truss_id:03d}",
            "linked_truss_id": float(truss_id),
            "vpos": float(truss_id),
            "vds": tdvs_by_truss.get(truss_id, _float_from(series, "mean_truss_tdvs", 0.0)),
            "leaf_dm_g_m2": per_leaf_dm,
            "leaf_area_m2_m2": per_leaf_area,
            "onplant_flag": True,
            "harvested_flag": False,
        }
        for truss_id in truss_ids
    ]
    return ensure_entity_frame(pd.DataFrame(records), LEAF_ENTITY_COLUMNS)


def normalize_harvest_state(
    current_row: pd.Series | Mapping[str, object],
    prior_row: pd.Series | Mapping[str, object] | None = None,
    *,
    plants_per_m2: float = 1.836091,
    floor_area_basis: bool = True,
) -> HarvestState:
    current = _as_series(current_row)
    prior = _as_series(prior_row)
    current_time = pd.Timestamp(current.get("datetime"))
    if prior is not None and pd.notna(prior.get("datetime")):
        dt_days = max((current_time - pd.Timestamp(prior.get("datetime"))).total_seconds() / 86400.0, 0.0)
    else:
        dt_days = max(_float_from(current, "dt_days", 1.0), 1e-9)
    fruit_entities = _parse_truss_payload(current)
    leaf_entities = _synthesize_leaf_entities(current, fruit_entities)
    stem_root_state = {
        "stem_dry_weight_g_m2": _float_from(current, "stem_dry_weight_g_m2", 0.0),
        "root_dry_weight_g_m2": _float_from(current, "root_dry_weight_g_m2", 0.0),
        "reserve_pool_g_m2": _float_from(current, "reserve_pool_g_m2", 0.0),
        "buffer_pool_g_m2": _float_from(current, "buffer_pool_g_m2", 0.0),
    }
    diagnostics = {
        "truss_count": _float_from(current, "truss_count", float(len(fruit_entities))),
        "active_trusses": _float_from(current, "active_trusses", float(len(fruit_entities))),
        "fruit_harvest_g_m2_step": _float_from(current, "fruit_harvest_g_m2_step", 0.0),
        "leaf_harvest_g_m2_step": _float_from(current, "leaf_harvest_g_m2_step", 0.0),
    }
    return HarvestState(
        datetime=current_time,
        dt_days=dt_days,
        floor_area_basis=bool(floor_area_basis),
        plants_per_m2=float(plants_per_m2),
        lai=_float_from(current, "LAI", 0.0),
        cbuf_g_m2=_float_from(current, "buffer_pool_g_m2", 0.0),
        fruit_entities=fruit_entities,
        leaf_entities=leaf_entities,
        stem_root_state=stem_root_state,
        harvested_fruit_cumulative_g_m2=_float_from(current, "harvested_fruit_g_m2", 0.0),
        harvested_leaf_cumulative_g_m2=_float_from(current, "harvested_leaf_g_m2", 0.0),
        diagnostics=diagnostics,
    )


def snapshot_to_harvest_state(
    current_row: pd.Series | Mapping[str, object],
    prior_row: pd.Series | Mapping[str, object] | None = None,
    *,
    plants_per_m2: float = 1.836091,
    floor_area_basis: bool = True,
) -> HarvestState:
    return normalize_harvest_state(
        current_row,
        prior_row=prior_row,
        plants_per_m2=plants_per_m2,
        floor_area_basis=floor_area_basis,
    )


__all__ = ["normalize_harvest_state", "snapshot_to_harvest_state"]
