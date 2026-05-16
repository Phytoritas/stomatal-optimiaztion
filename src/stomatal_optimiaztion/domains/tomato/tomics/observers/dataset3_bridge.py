from __future__ import annotations

from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.input_schema_audit import match_semantic_roles


def audit_dataset3_schema(frame: pd.DataFrame) -> dict[str, Any]:
    roles = match_semantic_roles(frame.columns)
    return {
        "columns": list(map(str, frame.columns)),
        "matched_roles": roles,
        "datetime_or_date_available": "datetime" in roles or "date" in roles,
        "truss_position_available": "truss_position" in roles,
        "loadcell_available": "loadcell" in roles,
        "treatment_available": "treatment" in roles,
    }


def build_dataset3_growth_phenology_bridge(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    schema = audit_dataset3_schema(frame)
    data = frame.copy()
    has_date = bool(schema["datetime_or_date_available"])
    has_loadcell = "loadcell_id" in data.columns or "loadcell" in data.columns
    has_treatment = "treatment" in data.columns
    if "date" in data.columns:
        data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.strftime("%Y-%m-%d")

    if has_loadcell and has_date:
        confidence = "direct_loadcell"
        group_cols = [column for column in ("date", "loadcell_id", "treatment") if column in data.columns]
    elif has_loadcell:
        confidence = "direct_loadcell_no_date"
        group_cols = [column for column in ("loadcell_id", "treatment") if column in data.columns]
    elif has_treatment and has_date:
        confidence = "treatment_level_only"
        group_cols = [column for column in ("date", "treatment") if column in data.columns]
    else:
        confidence = "unlinked"
        group_cols = [column for column in ("season",) if column in data.columns]

    if not group_cols:
        data["_standalone_dataset3"] = "all"
        group_cols = ["_standalone_dataset3"]

    aggregations: dict[str, tuple[str, str]] = {"dataset3_row_count": (group_cols[0], "size")}
    if "stem_diameter" in data.columns:
        aggregations["stem_diameter_mean"] = ("stem_diameter", "mean")
    if "flower_cluster_height" in data.columns:
        aggregations["flower_cluster_height_mean"] = ("flower_cluster_height", "mean")
    if "flowering_date" in data.columns:
        data["flowering_date"] = pd.to_datetime(data["flowering_date"], errors="coerce")
        aggregations["flowering_date_min"] = ("flowering_date", "min")
        aggregations["flowering_date_max"] = ("flowering_date", "max")
    if "flower_cluster_no" in data.columns:
        aggregations["flower_cluster_no_mean"] = ("flower_cluster_no", "mean")

    summary = data.groupby(group_cols, dropna=False).agg(**aggregations).reset_index()
    summary["Dataset3_mapping_confidence"] = confidence
    summary["Dataset3_datetime_or_date_available"] = has_date
    summary["Dataset3_truss_position_available"] = bool(schema["truss_position_available"])
    summary["causal_allocation_fitting_run"] = False
    summary["allocation_use"] = "growth_phenology_observer_only"
    counts = summary["Dataset3_mapping_confidence"].value_counts().to_dict()
    metadata = {
        **schema,
        "Dataset3_mapping_confidence": confidence,
        "Dataset3_mapping_confidence_counts": {str(key): int(value) for key, value in counts.items()},
    }
    return summary, metadata
