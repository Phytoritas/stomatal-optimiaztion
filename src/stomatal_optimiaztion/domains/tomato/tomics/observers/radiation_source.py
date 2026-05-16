from __future__ import annotations

from collections.abc import Mapping
import json
import math

import pandas as pd

RADIATION_THRESHOLDS_TO_TEST = [0, 1, 5, 10]

RADIATION_CANDIDATE_SPECS: tuple[dict[str, object], ...] = (
    {
        "candidate_rank": 1,
        "source_file_role": "dataset1",
        "candidate_column": "env_inside_radiation_wm2",
        "preference_group": "dataset1",
    },
    {
        "candidate_rank": 2,
        "source_file_role": "dataset1",
        "candidate_column": "env_radiation_wm2",
        "preference_group": "dataset1",
    },
    {
        "candidate_rank": 3,
        "source_file_role": "dataset1",
        "candidate_column": "env_radiation_wm2_mean",
        "preference_group": "dataset1",
    },
    {
        "candidate_rank": 3,
        "source_file_role": "dataset1",
        "candidate_column": "env_radiation_wm2_max",
        "preference_group": "dataset1",
    },
    {
        "candidate_rank": 4,
        "source_file_role": "fruit_leaf_temperature_solar_raw_dat",
        "candidate_column": "SolarRad_Avg",
        "preference_group": "raw_dat",
    },
    {
        "candidate_rank": 5,
        "source_file_role": "dataset1",
        "candidate_column": "env_outside_radiation_wm2",
        "preference_group": "dataset1_outside_fallback",
    },
)


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out):
        return None
    return out


def _bool(value: object) -> bool:
    return bool(value) if value is not None else False


def _column_stats(audit_row: Mapping[str, object] | None, column: str) -> Mapping[str, object]:
    raw = (audit_row or {}).get("column_stats_json")
    if not raw:
        return {}
    try:
        parsed = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    stats = parsed.get(column)
    return stats if isinstance(stats, Mapping) else {}


def _grain_from_resolution(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    if seconds <= 600:
        return "high_frequency_10min_or_finer"
    if seconds < 86_400:
        return "subdaily_not_10min"
    if seconds == 86_400:
        return "daily_only"
    return "coarser_than_daily"


def _infer_resolution_from_frame(frame: pd.DataFrame | None) -> float | None:
    if frame is None or frame.empty:
        return None
    timestamp_col = next(
        (column for column in ("timestamp", "TIMESTAMP", "datetime", "date_time", "DateTime", "time") if column in frame.columns),
        None,
    )
    if timestamp_col is None:
        return None
    values = pd.to_datetime(frame[timestamp_col], errors="coerce").dropna().sort_values()
    if values.shape[0] < 2:
        return None
    deltas = values.diff().dt.total_seconds().dropna()
    if deltas.empty:
        return None
    positive = deltas[deltas.gt(0)]
    if positive.empty:
        return None
    return float(positive.median())


def _radiation_metrics(
    frame: pd.DataFrame | None,
    *,
    column: str,
    audit_row: Mapping[str, object] | None,
) -> dict[str, object]:
    exists = frame is not None and column in frame.columns
    resolution = _to_float((audit_row or {}).get("inferred_time_resolution_seconds"))
    if resolution is None:
        resolution = _infer_resolution_from_frame(frame)
    stats = _column_stats(audit_row, column)
    if not exists or frame is None:
        stats_num_values = int(stats.get("num_values") or 0)
        if stats:
            row_count = int((audit_row or {}).get("row_count") or stats_num_values)
            null_count = int(stats.get("null_count") or 0)
            min_value = _to_float(stats.get("min"))
            max_value = _to_float(stats.get("max"))
            return {
                "exists": True,
                "non_null_count": stats_num_values,
                "missing_fraction": float(null_count / row_count) if row_count else None,
                "min_value": min_value,
                "max_value": max_value,
                "mean_value": None,
                "has_positive_values": bool(max_value is not None and max_value > 0.0),
                "has_zero_values": bool(
                    min_value is not None and max_value is not None and min_value <= 0.0 <= max_value
                ),
                "date_min": (audit_row or {}).get("date_min"),
                "date_max": (audit_row or {}).get("date_max"),
                "inferred_time_resolution_seconds": resolution,
                "usable_for_10min_daynight": bool(
                    stats_num_values and max_value is not None and max_value > 0.0 and resolution is not None and resolution <= 600
                ),
                "usable_for_daily_summary_only": bool(stats_num_values and resolution is not None and resolution >= 86_400),
            }
        return {
            "exists": False,
            "non_null_count": 0,
            "missing_fraction": None,
            "min_value": None,
            "max_value": None,
            "mean_value": None,
            "has_positive_values": False,
            "has_zero_values": False,
            "date_min": (audit_row or {}).get("date_min"),
            "date_max": (audit_row or {}).get("date_max"),
            "inferred_time_resolution_seconds": resolution,
            "usable_for_10min_daynight": False,
            "usable_for_daily_summary_only": False,
        }

    values = pd.to_numeric(frame[column], errors="coerce")
    sample_non_null_count = int(values.notna().sum())
    sample_row_count = int(values.shape[0])
    row_count = int((audit_row or {}).get("row_count") or sample_row_count)
    non_null_count = int(stats.get("num_values") or sample_non_null_count)
    null_count = int(stats.get("null_count") or max(sample_row_count - sample_non_null_count, 0))
    missing_fraction = float(null_count / row_count) if row_count else None
    min_value = _to_float(stats.get("min")) if stats else None
    max_value = _to_float(stats.get("max")) if stats else None
    if min_value is None and sample_non_null_count:
        min_value = float(values.min())
    if max_value is None and sample_non_null_count:
        max_value = float(values.max())
    has_positive = bool(max_value is not None and max_value > 0.0)
    has_zero = bool(min_value is not None and max_value is not None and min_value <= 0.0 <= max_value)
    usable_10min = bool(non_null_count and has_positive and has_zero and resolution is not None and resolution <= 600)
    usable_daily = bool(non_null_count and resolution is not None and resolution >= 86_400)
    return {
        "exists": True,
        "non_null_count": non_null_count,
        "missing_fraction": missing_fraction,
        "min_value": min_value,
        "max_value": max_value,
        "mean_value": float(values.mean()) if sample_non_null_count else None,
        "has_positive_values": has_positive,
        "has_zero_values": has_zero,
        "date_min": (audit_row or {}).get("date_min"),
        "date_max": (audit_row or {}).get("date_max"),
        "inferred_time_resolution_seconds": resolution,
        "usable_for_10min_daynight": usable_10min,
        "usable_for_daily_summary_only": usable_daily,
    }


def _candidate_is_selectable(row: Mapping[str, object]) -> bool:
    return _bool(row.get("exists")) and int(row.get("non_null_count") or 0) > 0 and _bool(
        row.get("has_positive_values")
    )


def _candidate_rejection_reason(row: Mapping[str, object]) -> str:
    if not _bool(row.get("exists")):
        return "column_missing"
    if int(row.get("non_null_count") or 0) <= 0:
        return "no_non_null_values"
    if not _bool(row.get("has_positive_values")):
        return "no_positive_radiation_values"
    if not _bool(row.get("usable_for_10min_daynight")) and _bool(row.get("usable_for_daily_summary_only")):
        return "daily_only_not_valid_for_10min_daynight"
    if not _bool(row.get("has_zero_values")):
        return "no_zero_radiation_values_for_night"
    if not _bool(row.get("usable_for_10min_daynight")):
        return "grain_not_valid_for_10min_daynight"
    return ""


def build_radiation_source_verification(
    tables_by_role: Mapping[str, pd.DataFrame | None],
    audit_rows_by_role: Mapping[str, Mapping[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Build candidate radiation-source rows and decision metadata."""

    rows: list[dict[str, object]] = []
    for spec in RADIATION_CANDIDATE_SPECS:
        role = str(spec["source_file_role"])
        candidate_column = str(spec["candidate_column"])
        audit_row = audit_rows_by_role.get(role, {})
        metrics = _radiation_metrics(
            tables_by_role.get(role),
            column=candidate_column,
            audit_row=audit_row,
        )
        rows.append(
            {
                "candidate_rank": int(spec["candidate_rank"]),
                "source_file_role": role,
                "source_filename": audit_row.get("expected_filename"),
                "candidate_column": candidate_column,
                **metrics,
                "chosen_primary": False,
                "selected_for_daynight_10min": False,
                "selected_for_daily_summary_only": False,
                "candidate_rejection_reason": "",
                "fallback_reason": "",
                "notes": "",
            }
        )

    chosen_index: int | None = None
    for idx, row in enumerate(rows):
        if row["source_file_role"] == "dataset1" and _candidate_is_selectable(row):
            chosen_index = idx
            break
    for row in rows:
        row["candidate_rejection_reason"] = _candidate_rejection_reason(row)

    fallback_required = True
    fallback_source = ""
    decision_notes: list[str] = []
    dataset1_direct = False
    dataset1_grain = "unknown"
    primary_source = ""
    primary_column = ""

    if chosen_index is not None:
        chosen = rows[chosen_index]
        fallback_required = not _bool(chosen.get("usable_for_10min_daynight"))
        if _bool(chosen.get("usable_for_10min_daynight")):
            chosen["selected_for_daynight_10min"] = True
            chosen["chosen_primary"] = True
            primary_source = str(chosen["source_file_role"])
            primary_column = str(chosen["candidate_column"])
        elif _bool(chosen.get("usable_for_daily_summary_only")):
            chosen["selected_for_daily_summary_only"] = True
        if primary_source == "dataset1":
            dataset1_direct = _bool(chosen.get("usable_for_10min_daynight"))
            dataset1_grain = _grain_from_resolution(_to_float(chosen.get("inferred_time_resolution_seconds")))
        chosen["notes"] = (
            "Highest-ranked available Dataset1 radiation candidate. "
            "It is selected for 10-minute day/night only when grain and zero/positive values support that use."
        )
    else:
        decision_notes.append("No selectable Dataset1 radiation candidate with positive numeric values was found.")

    dataset1_candidates = [row for row in rows if row["source_file_role"] == "dataset1" and _candidate_is_selectable(row)]
    if dataset1_candidates and dataset1_grain == "unknown":
        dataset1_grain = _grain_from_resolution(
            _to_float(dataset1_candidates[0].get("inferred_time_resolution_seconds"))
        )
        dataset1_direct = _bool(dataset1_candidates[0].get("usable_for_10min_daynight"))

    if fallback_required:
        for row in rows:
            if row.get("selected_for_daynight_10min"):
                continue
            if _bool(row.get("usable_for_10min_daynight")):
                fallback_source = f"{row['source_file_role']}:{row['candidate_column']}"
                row["fallback_reason"] = "10min_daynight_candidate_if_primary_is_daily_or_unusable"
                break
        if not fallback_source:
            raw_candidate = next(
                (
                    row
                    for row in rows
                    if row["source_file_role"] == "fruit_leaf_temperature_solar_raw_dat"
                    and row["candidate_column"] == "SolarRad_Avg"
                    and _candidate_is_selectable(row)
                ),
                None,
            )
            if raw_candidate is not None:
                fallback_source = "fruit_leaf_temperature_solar_raw_dat:SolarRad_Avg"
                raw_candidate["fallback_reason"] = "candidate_high_frequency_fallback_for_goal2_review"

    if fallback_required and not fallback_source:
        decision_notes.append("No high-frequency fallback has been verified yet.")
    if dataset1_grain == "daily_only":
        decision_notes.append("Dataset1 radiation is daily-only; do not force 10-minute day/night from daily means.")
    if dataset1_grain == "subdaily_not_10min":
        decision_notes.append("Dataset1 radiation is subdaily but coarser than 10 minutes.")
    if not dataset1_direct:
        decision_notes.append("No Dataset1 radiation candidate was verified as a 10-minute day/night primary.")

    metadata = {
        "radiation_daynight_primary_source": primary_source,
        "radiation_column_used": primary_column,
        "selected_for_daynight_10min": bool(primary_source and primary_column),
        "selected_for_daily_summary_only": bool(
            chosen_index is not None and rows[chosen_index].get("selected_for_daily_summary_only")
        ),
        "radiation_thresholds_to_test": RADIATION_THRESHOLDS_TO_TEST,
        "fixed_clock_daynight_primary": False,
        "clock_06_18_used_only_for_compatibility": True,
        "dataset1_radiation_directly_usable": dataset1_direct,
        "dataset1_radiation_grain": dataset1_grain,
        "fallback_required": fallback_required,
        "fallback_source_if_required": fallback_source,
        "radiation_source_decision_notes": decision_notes,
    }
    return rows, metadata


__all__ = [
    "RADIATION_CANDIDATE_SPECS",
    "RADIATION_THRESHOLDS_TO_TEST",
    "build_radiation_source_verification",
]
