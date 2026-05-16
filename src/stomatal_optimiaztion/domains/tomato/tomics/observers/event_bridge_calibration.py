from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EVENT_TOTAL_COL = "event_bridged_loss_g_per_day"
CALIBRATION_TOTAL_COL = "existing_daily_event_bridged_loss_g_per_day"


def _normalize_keys(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    if "loadcell_id" in out.columns:
        out["loadcell_id"] = pd.to_numeric(out["loadcell_id"], errors="coerce").astype("Int64").astype(str)
    if "treatment" in out.columns:
        out["treatment"] = out["treatment"].astype(str)
    return out


def load_legacy_event_bridge_daily_totals(
    config: Mapping[str, Any],
    *,
    min_valid_coverage_fraction: float = 0.0,
    allow_qc_false: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    min_valid_coverage_fraction = float(
        config.get("event_bridge_min_valid_coverage_fraction", min_valid_coverage_fraction)
    )
    allow_qc_false = bool(config.get("allow_legacy_event_bridge_qc_false", allow_qc_false))
    if not bool(config.get("enabled")) or not bool(config.get("allow_legacy_event_bridge_calibration")):
        empty_audit = pd.DataFrame(
            [
                {
                    "source_path": "",
                    "status": "disabled",
                    "rows_total": 0,
                    "rows_usable": 0,
                    "notes": "Legacy event bridge calibration is disabled.",
                }
            ]
        )
        return pd.DataFrame(), empty_audit, {
            "existing_daily_event_bridged_total_available": False,
            "event_bridged_ET_calibration_status": "uncalibrated_no_daily_total",
            "event_bridged_ET_calibration_source": "",
            "event_bridged_ET_calibration_provenance": config.get("provenance_label", "legacy_v1_3_derived_output"),
            "event_bridged_ET_calibration_direct_raw_recomputed": False,
            "event_bridged_ET_calibration_rows_matched": 0,
            "event_bridged_ET_calibration_rows_unmatched": 0,
        }

    archive_root = Path(config["archive_root_path"])
    candidates = [archive_root / str(path) for path in config.get("event_bridge_daily_candidates", [])]
    audit_rows: list[dict[str, Any]] = []
    for path in candidates:
        row = {"source_path": str(path), "status": "missing_file", "rows_total": 0, "rows_usable": 0, "notes": ""}
        if not path.exists():
            audit_rows.append(row)
            continue
        frame = pd.read_csv(path)
        row["rows_total"] = int(frame.shape[0])
        required = {"date", "loadcell_id", "treatment", EVENT_TOTAL_COL}
        missing = sorted(required.difference(frame.columns))
        if missing:
            row["status"] = "missing_required_columns"
            row["notes"] = ";".join(missing)
            audit_rows.append(row)
            continue
        work = _normalize_keys(frame)
        work[EVENT_TOTAL_COL] = pd.to_numeric(work[EVENT_TOTAL_COL], errors="coerce")
        work = work[np.isfinite(work[EVENT_TOTAL_COL])]
        if "valid_coverage_fraction" in work.columns:
            work["valid_coverage_fraction"] = pd.to_numeric(work["valid_coverage_fraction"], errors="coerce")
            work = work[work["valid_coverage_fraction"].fillna(-np.inf).ge(min_valid_coverage_fraction)]
        if "primary_event_bridge_qc" in work.columns and not allow_qc_false:
            work = work[work["primary_event_bridge_qc"].astype(str).str.lower().eq("true")]
        work = work[work[EVENT_TOTAL_COL].notna()]
        work = work.rename(columns={EVENT_TOTAL_COL: CALIBRATION_TOTAL_COL})
        keep = [
            column
            for column in (
                "date",
                "loadcell_id",
                "treatment",
                CALIBRATION_TOTAL_COL,
                "primary_event_bridge_qc",
                "valid_coverage_fraction",
                "event_bridge_rate_source",
                "bridge_to_quiet_scaled_ratio",
            )
            if column in work.columns
        ]
        usable = work[keep].drop_duplicates(["date", "loadcell_id", "treatment"])
        row["rows_usable"] = int(usable.shape[0])
        row["status"] = "ok" if not usable.empty else "no_usable_rows"
        audit_rows.append(row)
        if not usable.empty:
            metadata = {
                "existing_daily_event_bridged_total_available": True,
                "event_bridged_ET_calibration_status": "legacy_daily_totals_available",
                "event_bridged_ET_calibration_source": str(path),
                "event_bridged_ET_calibration_provenance": config.get("provenance_label", "legacy_v1_3_derived_output"),
                "event_bridged_ET_calibration_direct_raw_recomputed": False,
                "event_bridged_ET_calibration_rows_matched": 0,
                "event_bridged_ET_calibration_rows_unmatched": 0,
            }
            return usable, pd.DataFrame(audit_rows), metadata

    return pd.DataFrame(), pd.DataFrame(audit_rows), {
        "existing_daily_event_bridged_total_available": False,
        "event_bridged_ET_calibration_status": "uncalibrated_no_daily_total",
        "event_bridged_ET_calibration_source": "",
        "event_bridged_ET_calibration_provenance": config.get("provenance_label", "legacy_v1_3_derived_output"),
        "event_bridged_ET_calibration_direct_raw_recomputed": False,
        "event_bridged_ET_calibration_rows_matched": 0,
        "event_bridged_ET_calibration_rows_unmatched": 0,
    }


def calibration_match_metadata(intervals: pd.DataFrame, daily_totals: pd.DataFrame, metadata: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(metadata)
    if daily_totals.empty or intervals.empty:
        return out
    interval_keys = _normalize_keys(intervals)[["date", "loadcell_id", "treatment"]].drop_duplicates()
    total_keys = _normalize_keys(daily_totals)[["date", "loadcell_id", "treatment"]].drop_duplicates()
    matched = interval_keys.merge(total_keys, on=["date", "loadcell_id", "treatment"], how="inner")
    out["event_bridged_ET_calibration_rows_matched"] = int(matched.shape[0])
    out["event_bridged_ET_calibration_rows_unmatched"] = int(interval_keys.shape[0] - matched.shape[0])
    out["event_bridged_ET_calibration_status"] = (
        "calibrated_to_legacy_daily_event_total" if out["event_bridged_ET_calibration_rows_matched"] else "uncalibrated_no_matching_daily_total"
    )
    return out
