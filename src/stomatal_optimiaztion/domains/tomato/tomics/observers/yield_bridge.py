from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.contracts import (
    CANONICAL_2025_2C_FRUIT_DMC,
    DEFAULT_FRUIT_DRY_MATTER_CONTENT,
    DEPRECATED_PREVIOUS_DEFAULT_FRUIT_DMC,
    DMC_SENSITIVITY,
    HAF_2025_2C_LOADCELL_FLOOR_AREA_M2,
)


LEGACY_DEFAULT_DMC = CANONICAL_2025_2C_FRUIT_DMC

FRESH_YIELD_COLUMNS = (
    "loadcell_daily_yield_g",
    "loadcell_cumulative_yield_g",
    "individual_cumulative_yield_g",
    "final_fresh_yield_g",
)

CANONICAL_DMC_DRY_COLUMNS = (
    "final_dry_yield_g_est_5p6pct",
    "default_5p6pct",
    "dry_yield_5p6pct",
    "loadcell_daily_dry_yield_g_est_default_5p6pct",
    "loadcell_cumulative_dry_yield_g_est_default_5p6pct",
)

LEGACY_SENSITIVITY_DRY_COLUMNS = (
    "loadcell_daily_dry_yield_g_est_lower_5p2pct",
    "loadcell_cumulative_dry_yield_g_est_lower_5p2pct",
    "loadcell_daily_dry_yield_g_est_upper_6p0pct",
    "loadcell_cumulative_dry_yield_g_est_upper_6p0pct",
    "loadcell_daily_dry_yield_g_est_broad_low_4pct",
    "loadcell_cumulative_dry_yield_g_est_broad_low_4pct",
    "loadcell_daily_dry_yield_g_est_broad_high_8pct",
    "loadcell_cumulative_dry_yield_g_est_broad_high_8pct",
    "loadcell_daily_dry_yield_g_est_6p5pct",
    "loadcell_cumulative_dry_yield_g_est_6p5pct",
    "default_6p5pct",
    "dry_yield_6p5pct",
)


def fresh_g_to_dry_g(fresh_g: float, dmc: float = CANONICAL_2025_2C_FRUIT_DMC) -> float:
    return float(fresh_g) * float(dmc)


def dry_g_to_fresh_g(dry_g: float, dmc: float = CANONICAL_2025_2C_FRUIT_DMC) -> float:
    return float(dry_g) / float(dmc)


def fresh_loadcell_to_dry_floor_area(
    fresh_g_loadcell: float,
    dmc: float = CANONICAL_2025_2C_FRUIT_DMC,
    area: float = HAF_2025_2C_LOADCELL_FLOOR_AREA_M2,
) -> float:
    return fresh_g_to_dry_g(fresh_g_loadcell, dmc=dmc) / float(area)


def dry_floor_area_to_fresh_loadcell(
    dry_g_m2: float,
    dmc: float = CANONICAL_2025_2C_FRUIT_DMC,
    area: float = HAF_2025_2C_LOADCELL_FLOOR_AREA_M2,
) -> float:
    return dry_g_to_fresh_g(float(dry_g_m2) * float(area), dmc=dmc)


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
            legacy_sensitivity_columns_present=(),
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
        yield_columns = set(FRESH_YIELD_COLUMNS) | set(CANONICAL_DMC_DRY_COLUMNS) | set(LEGACY_SENSITIVITY_DRY_COLUMNS)
        keep = [
            column
            for column in work.columns
            if column in {"date", "loadcell_id", "treatment"} or column in yield_columns
        ]
        usable = work[keep].copy()
        for fresh_column in FRESH_YIELD_COLUMNS:
            if fresh_column in usable.columns:
                usable["measured_or_legacy_fresh_yield_g"] = usable[fresh_column]
                break
        canonical_dry_cols = [column for column in CANONICAL_DMC_DRY_COLUMNS if column in usable.columns]
        legacy_sensitivity_cols = [column for column in LEGACY_SENSITIVITY_DRY_COLUMNS if column in usable.columns]
        canonical_dry = (
            pd.to_numeric(usable[canonical_dry_cols[0]], errors="coerce")
            if canonical_dry_cols
            else pd.Series(pd.NA, index=usable.index)
        )
        fresh_available = bool(
            any(
                column in usable.columns and usable[column].notna().any()
                for column in ("measured_or_legacy_fresh_yield_g", *FRESH_YIELD_COLUMNS)
            )
        )
        fresh_fw = (
            pd.to_numeric(usable["measured_or_legacy_fresh_yield_g"], errors="coerce")
            if "measured_or_legacy_fresh_yield_g" in usable.columns
            else pd.Series(pd.NA, index=usable.index)
        )
        fresh_has_value = fresh_fw.notna()
        canonical_dry_has_value = canonical_dry.notna()
        usable["observed_fruit_FW_g_loadcell"] = fresh_fw.fillna(canonical_dry / CANONICAL_2025_2C_FRUIT_DMC)

        usable["observed_fruit_DW_g_loadcell_dmc_0p056"] = (
            fresh_fw * CANONICAL_2025_2C_FRUIT_DMC
        ).fillna(canonical_dry)
        usable["observed_fruit_DW_g_m2_floor_dmc_0p056"] = pd.to_numeric(
            usable["observed_fruit_DW_g_loadcell_dmc_0p056"],
            errors="coerce",
        ) / HAF_2025_2C_LOADCELL_FLOOR_AREA_M2
        dry_available = bool(usable["observed_fruit_DW_g_loadcell_dmc_0p056"].notna().any())
        usable["fresh_yield_source"] = ""
        usable.loc[fresh_has_value, "fresh_yield_source"] = str(path)
        usable["canonical_fruit_DMC_fraction"] = CANONICAL_2025_2C_FRUIT_DMC
        usable["fruit_DMC_fraction"] = CANONICAL_2025_2C_FRUIT_DMC
        usable["default_fruit_dry_matter_content"] = DEFAULT_FRUIT_DRY_MATTER_CONTENT
        usable["DMC_fixed_for_2025_2C"] = True
        usable["DMC_sensitivity_enabled"] = False
        usable["dry_yield_source"] = ""
        usable.loc[
            usable["observed_fruit_DW_g_loadcell_dmc_0p056"].notna() & fresh_has_value,
            "dry_yield_source",
        ] = "fresh_yield_times_canonical_DMC_0p056"
        usable.loc[
            usable["observed_fruit_DW_g_loadcell_dmc_0p056"].notna()
            & ~fresh_has_value
            & canonical_dry_has_value,
            "dry_yield_source",
        ] = "legacy_canonical_DMC_0p056_column"
        usable["dry_yield_is_dmc_estimated"] = dry_available
        usable["direct_dry_yield_measured"] = bool(config.get("direct_dry_yield_measured", False))
        usable["legacy_yield_bridge_provenance"] = provenance
        usable["legacy_sensitivity_columns_present"] = ",".join(legacy_sensitivity_cols)
        row["rows_usable"] = int(usable.shape[0])
        row["status"] = "ok" if not usable.empty else "no_usable_rows"
        row["legacy_sensitivity_columns_present"] = ",".join(legacy_sensitivity_cols)
        audit_rows.append(row)
        if not usable.empty:
            return usable, pd.DataFrame(audit_rows), _metadata(
                fresh_available,
                dry_available,
                str(path),
                provenance,
                direct_dry=bool(config.get("direct_dry_yield_measured", False)),
                legacy_sensitivity_columns_present=legacy_sensitivity_cols,
            )
    return pd.DataFrame(), pd.DataFrame(audit_rows), _metadata(
        False,
        False,
        "",
        provenance,
        direct_dry=False,
        legacy_sensitivity_columns_present=(),
    )


def _metadata(
    fresh_available: bool,
    dry_available: bool,
    source: str,
    provenance: str,
    *,
    direct_dry: bool,
    legacy_sensitivity_columns_present: tuple[str, ...] | list[str],
) -> dict[str, Any]:
    any_available = fresh_available or dry_available
    return {
        "harvest_yield_available": any_available,
        "fresh_yield_available": fresh_available,
        "fresh_yield_source": source if fresh_available else "",
        "dry_yield_available": dry_available,
        "dry_yield_source": (
            "fresh_yield_times_canonical_DMC_0p056"
            if dry_available and fresh_available
            else "legacy_canonical_DMC_0p056_column"
            if dry_available
            else ""
        ),
        "dry_yield_is_dmc_estimated": dry_available and not direct_dry,
        "direct_dry_yield_measured": direct_dry if dry_available else False,
        "legacy_yield_bridge_used": any_available,
        "legacy_yield_bridge_provenance": provenance if any_available else "",
        "DMC_conversion_performed": dry_available,
        "canonical_fruit_DMC_fraction": CANONICAL_2025_2C_FRUIT_DMC,
        "fruit_DMC_fraction": CANONICAL_2025_2C_FRUIT_DMC,
        "default_fruit_dry_matter_content": DEFAULT_FRUIT_DRY_MATTER_CONTENT,
        "DMC_fixed_for_2025_2C": True,
        "DMC_sensitivity_enabled": False,
        "DMC_sensitivity_values": list(DMC_SENSITIVITY),
        "deprecated_previous_default_fruit_DMC_fraction": DEPRECATED_PREVIOUS_DEFAULT_FRUIT_DMC,
        "legacy_sensitivity_columns_present": list(legacy_sensitivity_columns_present),
        "default_fruit_dry_matter_content_from_legacy": LEGACY_DEFAULT_DMC,
    }
