from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.contracts import (
    DEFAULT_FRUIT_DRY_MATTER_CONTENT,
    DMC_SENSITIVITY,
)


LEGACY_DEFAULT_DMC = 0.056

FRESH_YIELD_COLUMNS = (
    "loadcell_daily_yield_g",
    "loadcell_cumulative_yield_g",
    "individual_cumulative_yield_g",
    "final_fresh_yield_g",
)


def _normalize_keys(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    if "loadcell_id" in out.columns:
        out["loadcell_id"] = pd.to_numeric(out["loadcell_id"], errors="coerce").astype("Int64").astype(str)
    if "treatment" in out.columns:
        out["treatment"] = out["treatment"].astype(str)
    return out


def load_legacy_yield_bridge(config: Mapping[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    provenance = str(config.get("provenance_label", "legacy_v1_3_derived_output"))
    if not bool(config.get("enabled")) or not bool(config.get("allow_legacy_yield_bridge")):
        audit = pd.DataFrame([{"source_role": "legacy_yield_bridge", "status": "disabled", "rows_total": 0, "rows_usable": 0}])
        return pd.DataFrame(), audit, _metadata(
            False,
            False,
            "",
            provenance,
            direct_dry=bool(config.get("direct_dry_yield_measured", False)),
        )

    archive_root = Path(config["archive_root_path"])
    sources = [
        ("integrated_daily_master", archive_root / str(config.get("integrated_daily_master"))),
        ("fresh_dry_loadcell_summary", archive_root / str(config.get("fresh_dry_loadcell_summary"))),
    ]
    audit_rows: list[dict[str, Any]] = []
    for role, path in sources:
        row = {"source_role": role, "path": str(path), "status": "missing_file", "rows_total": 0, "rows_usable": 0}
        if not path.exists():
            audit_rows.append(row)
            continue
        frame = pd.read_csv(path)
        row["rows_total"] = int(frame.shape[0])
        work = _normalize_keys(frame)
        keep = [
            column
            for column in work.columns
            if column in {"date", "loadcell_id", "treatment"}
            or column in {
                "loadcell_daily_yield_g",
                "loadcell_cumulative_yield_g",
                "individual_cumulative_yield_g",
                "final_fresh_yield_g",
                "final_dry_yield_g_est_5p6pct",
                "loadcell_daily_dry_yield_g_est_default_5p6pct",
                "loadcell_cumulative_dry_yield_g_est_default_5p6pct",
                "loadcell_daily_dry_yield_g_est_lower_5p2pct",
                "loadcell_cumulative_dry_yield_g_est_lower_5p2pct",
                "loadcell_daily_dry_yield_g_est_upper_6p0pct",
                "loadcell_cumulative_dry_yield_g_est_upper_6p0pct",
                "loadcell_daily_dry_yield_g_est_broad_low_4pct",
                "loadcell_cumulative_dry_yield_g_est_broad_low_4pct",
                "loadcell_daily_dry_yield_g_est_broad_high_8pct",
                "loadcell_cumulative_dry_yield_g_est_broad_high_8pct",
            }
        ]
        usable = work[keep].copy()
        for fresh_column in FRESH_YIELD_COLUMNS:
            if fresh_column in usable.columns:
                usable["measured_or_legacy_fresh_yield_g"] = usable[fresh_column]
                break
        dry_cols = [column for column in usable.columns if "_dry_yield_g_est_" in column or column.endswith("_dry_yield_g_est_5p6pct")]
        fresh_available = bool(
            any(
                column in usable.columns and usable[column].notna().any()
                for column in ("measured_or_legacy_fresh_yield_g", *FRESH_YIELD_COLUMNS)
            )
        )
        dry_available = bool(dry_cols and usable[dry_cols].notna().any().any())
        usable["dry_yield_is_dmc_estimated"] = bool(dry_cols)
        usable["direct_dry_yield_measured"] = bool(config.get("direct_dry_yield_measured", False))
        usable["legacy_yield_bridge_provenance"] = provenance
        row["rows_usable"] = int(usable.shape[0])
        row["status"] = "ok" if not usable.empty else "no_usable_rows"
        audit_rows.append(row)
        if not usable.empty:
            return usable, pd.DataFrame(audit_rows), _metadata(
                fresh_available,
                dry_available,
                str(path),
                provenance,
                direct_dry=bool(config.get("direct_dry_yield_measured", False)),
            )
    return pd.DataFrame(), pd.DataFrame(audit_rows), _metadata(False, False, "", provenance, direct_dry=False)


def _metadata(fresh_available: bool, dry_available: bool, source: str, provenance: str, *, direct_dry: bool) -> dict[str, Any]:
    any_available = fresh_available or dry_available
    return {
        "harvest_yield_available": any_available,
        "fresh_yield_available": fresh_available,
        "fresh_yield_source": source if fresh_available else "",
        "dry_yield_available": dry_available,
        "dry_yield_source": source if dry_available else "",
        "dry_yield_is_dmc_estimated": dry_available and not direct_dry,
        "direct_dry_yield_measured": direct_dry if dry_available else False,
        "legacy_yield_bridge_used": any_available,
        "legacy_yield_bridge_provenance": provenance if any_available else "",
        "DMC_conversion_performed": dry_available,
        "default_fruit_dry_matter_content_from_legacy": LEGACY_DEFAULT_DMC,
        "configured_default_fruit_dry_matter_content": DEFAULT_FRUIT_DRY_MATTER_CONTENT,
        "dmc_sensitivity": list(DMC_SENSITIVITY),
    }
