from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.contracts import resolve_repo_path


DEFAULT_LEGACY_V1_3_CONFIG = {
    "enabled": False,
    "archive_root": "artifacts/tomato_integrated_radiation_architecture_v1_3",
    "event_bridge_daily_candidates": [
        "previous_outputs/event_bridge_outputs/daily_event_bridged_transpiration.csv",
        "outputs/derived/legacy_daily_event_bridged_transpiration.csv",
    ],
    "integrated_daily_master": "outputs/derived/integrated_daily_master_radiation_daynight_fresh_dry.csv",
    "fresh_dry_loadcell_summary": "outputs/tables/fresh_dry_weight_loadcell_final_summary.csv",
    "fresh_dry_treatment_summary": "outputs/tables/fresh_dry_weight_treatment_summary.csv",
    "dataset3_traits_plus_yield": "outputs/derived/dataset3_traits_plus_fresh_dry_yield.csv",
    "provenance_label": "legacy_v1_3_derived_output",
    "allow_legacy_event_bridge_calibration": False,
    "allow_legacy_event_bridge_qc_false": True,
    "event_bridge_min_valid_coverage_fraction": 0.0,
    "allow_legacy_yield_bridge": False,
    "direct_dry_yield_measured": False,
}


def legacy_v1_3_config(config: Mapping[str, Any], *, repo_root: Path) -> dict[str, Any]:
    raw = dict(DEFAULT_LEGACY_V1_3_CONFIG)
    override = config.get("legacy_v1_3")
    if isinstance(override, Mapping):
        raw.update({str(key): value for key, value in override.items()})
    raw["archive_root_path"] = resolve_repo_path(repo_root, str(raw["archive_root"]))
    return raw


def _candidate_paths(archive_root: Path, values: Sequence[object] | object) -> list[Path]:
    if isinstance(values, (str, Path)):
        raw_values = [values]
    elif isinstance(values, Sequence):
        raw_values = list(values)
    else:
        raw_values = []
    return [(archive_root / str(value)).resolve() for value in raw_values]


def audit_legacy_v1_3_bridge(config: Mapping[str, Any]) -> pd.DataFrame:
    archive_root = Path(config["archive_root_path"])
    rows: list[dict[str, Any]] = []
    source_specs = {
        "event_bridge_daily_candidate": config.get("event_bridge_daily_candidates", []),
        "integrated_daily_master": config.get("integrated_daily_master"),
        "fresh_dry_loadcell_summary": config.get("fresh_dry_loadcell_summary"),
        "fresh_dry_treatment_summary": config.get("fresh_dry_treatment_summary"),
        "dataset3_traits_plus_yield": config.get("dataset3_traits_plus_yield"),
    }
    for role, values in source_specs.items():
        for path in _candidate_paths(archive_root, values):
            row: dict[str, Any] = {
                "source_role": role,
                "path": str(path),
                "exists": path.exists(),
                "provenance": config.get("provenance_label", "legacy_v1_3_derived_output"),
                "row_count": None,
                "column_count": None,
                "columns_json": "[]",
                "date_min": None,
                "date_max": None,
                "loadcell_ids_json": "[]",
                "treatment_values_json": "[]",
                "status": "missing_file",
                "notes": "",
            }
            if path.exists():
                try:
                    frame = pd.read_csv(path)
                except Exception as exc:  # pragma: no cover - defensive audit note
                    row["status"] = "parse_failed"
                    row["notes"] = f"{type(exc).__name__}: {exc}"
                else:
                    row["row_count"] = int(frame.shape[0])
                    row["column_count"] = int(frame.shape[1])
                    row["columns_json"] = pd.Series([list(frame.columns)]).to_json(orient="values", force_ascii=False)
                    if "date" in frame.columns:
                        dates = pd.to_datetime(frame["date"], errors="coerce").dropna()
                        if not dates.empty:
                            row["date_min"] = dates.min().strftime("%Y-%m-%d")
                            row["date_max"] = dates.max().strftime("%Y-%m-%d")
                    if "loadcell_id" in frame.columns:
                        row["loadcell_ids_json"] = (
                            pd.Series(sorted(pd.to_numeric(frame["loadcell_id"], errors="coerce").dropna().astype(int).unique()))
                            .to_json(orient="values")
                        )
                    if "treatment" in frame.columns:
                        row["treatment_values_json"] = (
                            pd.Series(sorted(frame["treatment"].dropna().astype(str).unique())).to_json(orient="values")
                        )
                    row["status"] = "ok"
            rows.append(row)
    return pd.DataFrame(rows)
