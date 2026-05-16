from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, write_json
from stomatal_optimiaztion.domains.tomato.tomics.observers.metadata_contract import (
    normalize_metadata,
    write_stage_metadata_snapshot,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.radiation_source import (
    build_radiation_source_verification,
)

SEASON_ID = "2025_2C"
RAW_FILENAME_NOTE = (
    "some raw filenames contain 2026_2; evaluation season is user-defined as "
    "2025 second cropping cycle."
)

SENSOR_MAPPING_METADATA = {
    "leaf_temperature_mapping": [
        {"column": "LeafTemp1_Avg", "loadcell_id": 4, "treatment": "Drought"},
        {"column": "LeafTemp2_Avg", "loadcell_id": 1, "treatment": "Control"},
    ],
    "fruit_diameter_mapping": [
        {"column": "Fruit1Diameter_Avg", "loadcell_id": 4, "treatment": "Drought"},
        {"column": "Fruit2Diameter_Avg", "loadcell_id": 1, "treatment": "Control"},
    ],
    "fruit_diameter_rules": {
        "sensor_level_only": True,
        "fruit_diameter_treatment_endpoint": False,
        "fruit_diameter_p_values_allowed": False,
        "fruit_diameter_allocation_calibration_target": False,
        "fruit_diameter_model_promotion_target": False,
    },
}

DEFAULT_INPUT_FILE_SPECS: tuple[dict[str, str], ...] = (
    {
        "file_role": "fruit_leaf_temperature_solar_raw_dat",
        "expected_filename": "2026_2작기_토마토_엽온_과실직경.dat",
    },
    {
        "file_role": "dataset1",
        "expected_filename": "dataset1_loadcell_1_6_daily_ec_moisture_yield_env.parquet",
    },
    {
        "file_role": "dataset2",
        "expected_filename": "dataset2_loadcell_4_5_daily_ec_moisture_tensiometer.parquet",
    },
    {
        "file_role": "dataset3",
        "expected_filename": "dataset3_individual_stem_diameter_flower_height_flowering_date.parquet",
    },
)

DEFAULT_ROLE_ALIASES: dict[str, tuple[str, ...]] = {
    "datetime": ("timestamp", "TIMESTAMP", "datetime", "date_time", "DateTime", "time"),
    "date": ("date", "Date", "window_date", "day"),
    "loadcell": ("loadcell_id", "loadcell", "lc", "Loadcell", "load_cell_id"),
    "treatment": ("treatment", "Treatment", "water_treatment", "irrigation_treatment"),
    "radiation": (
        "env_inside_radiation_wm2",
        "env_radiation_wm2",
        "env_radiation_wm2_mean",
        "env_radiation_wm2_max",
        "env_outside_radiation_wm2",
        "SolarRad_Avg",
        "solar_w_m2",
        "radiation_wm2",
    ),
    "vpd": ("env_vpd_kpa", "vpd_kpa", "VPD", "VPD_kPa"),
    "temperature": ("env_air_temperature_c", "air_temperature_c", "T_air_C", "temperature_c"),
    "co2": ("env_co2_ppm", "CO2_ppm", "co2_ppm"),
    "rh": ("env_rh_pct", "RH_percent", "rh_pct"),
    "moisture": ("moisture_percent_mean", "moisture_percent", "substrate_moisture", "theta", "vwc", "water_content"),
    "ec": ("ec_ds_mean", "ec_ds", "substrate_ec", "EC", "ec"),
    "tensiometer": ("tensiometer_hp_mean", "tensiometer_hp", "tensiometer", "matric_potential", "substrate_tension"),
    "yield_fresh": (
        "yield_fresh_g",
        "fresh_yield_g",
        "individual_fresh_yield_g",
        "harvest_fresh_weight_g",
        "loadcell_daily_yield_g",
        "loadcell_cumulative_yield_g",
        "individual_cumulative_yield_g",
        "final_fresh_yield_g",
    ),
    "yield_dry": ("yield_dry_g", "dry_yield_g", "fruit_dry_weight_g", "harvest_dry_weight_g"),
    "estimated_dry_yield_from_dmc": (
        "final_dry_yield_g_est_5p6pct",
        "loadcell_daily_dry_yield_g_est_default_5p6pct",
        "loadcell_cumulative_dry_yield_g_est_default_5p6pct",
        "individual_cumulative_dry_yield_g_est_5p6pct",
    ),
    "direct_dry_yield_measured": ("yield_dry_g", "dry_yield_g", "fruit_dry_weight_g", "harvest_dry_weight_g"),
    "lai": ("LAI", "lai", "leaf_area_index"),
    "fruit_count": ("fruit_count", "n_fruits", "fruits_per_truss", "n_fruits_per_truss"),
    "stem_diameter": ("stem_diameter", "stem diameter", "stem_diameter_mm"),
    "flower_height": ("flower_height", "flower height", "flower_cluster_height"),
    "flowering_date": ("flowering_date", "flowering date"),
    "truss_position": ("truss_position", "flower_cluster_no", "truss", "cluster"),
    "plant_id": ("plant_id", "sample_id", "individual_id"),
    "leaf_temperature": ("LeafTemp1_Avg", "LeafTemp2_Avg"),
    "fruit_diameter": ("Fruit1Diameter_Avg", "Fruit2Diameter_Avg"),
}

IMPORTANT_ROLES_BY_FILE_ROLE: dict[str, tuple[str, ...]] = {
    "fruit_leaf_temperature_solar_raw_dat": (
        "datetime",
        "radiation",
        "leaf_temperature",
        "fruit_diameter",
    ),
    "dataset1": (
        "datetime_or_date",
        "loadcell",
        "treatment",
        "radiation",
        "vpd",
        "temperature",
        "co2",
        "rh",
        "moisture",
        "ec",
        "yield_fresh",
        "yield_dry",
        "lai",
    ),
    "dataset2": ("datetime_or_date", "loadcell", "treatment", "moisture", "ec", "tensiometer"),
    "dataset3": (
        "datetime_or_date",
        "loadcell",
        "treatment",
        "stem_diameter",
        "flower_height",
        "flowering_date",
        "truss_position",
        "plant_id",
    ),
}


@dataclass(frozen=True)
class LoadedTable:
    frame: pd.DataFrame | None
    parser_used: str
    error: str | None = None
    row_count: int | None = None
    column_names: tuple[str, ...] | None = None
    dtype_map: Mapping[str, str] | None = None
    column_stats: Mapping[str, Mapping[str, object]] | None = None


def normalize_column_name(value: object) -> str:
    text = str(value).strip().lower()
    for token in (" ", "-", ".", "/", "\\"):
        text = text.replace(token, "_")
    while "__" in text:
        text = text.replace("__", "_")
    return text


def match_semantic_roles(
    columns: Sequence[object],
    aliases: Mapping[str, Sequence[str]] = DEFAULT_ROLE_ALIASES,
) -> dict[str, list[str]]:
    normalized_columns = {normalize_column_name(column): str(column) for column in columns}
    matched: dict[str, list[str]] = {}
    for role, role_aliases in aliases.items():
        role_matches: list[str] = []
        for alias in role_aliases:
            candidate = normalized_columns.get(normalize_column_name(alias))
            if candidate is not None and candidate not in role_matches:
                role_matches.append(candidate)
        if role_matches:
            matched[role] = role_matches
    return matched


def _json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _jsonable_scalar(value: object) -> object:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    return value


def _sorted_unique_json_values(series: pd.Series, *, limit: int = 100) -> list[object]:
    values = [_jsonable_scalar(value) for value in series.dropna().unique().tolist()]
    values = sorted(values, key=lambda item: str(item))
    return values[:limit]


def _iso_timestamp(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).isoformat()


def _jsonable_stat_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except (TypeError, ValueError):
            pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    return value


def _stat_less(left: object, right: object) -> bool:
    try:
        return left < right  # type: ignore[operator]
    except TypeError:
        return str(left) < str(right)


def _stat_greater(left: object, right: object) -> bool:
    try:
        return left > right  # type: ignore[operator]
    except TypeError:
        return str(left) > str(right)


def _infer_resolution_seconds(values: pd.Series) -> float | None:
    parsed = pd.to_datetime(values, errors="coerce").dropna().sort_values().drop_duplicates()
    if parsed.shape[0] < 2:
        return None
    diffs = parsed.diff().dropna().dt.total_seconds()
    if diffs.empty:
        return None
    return float(diffs.median())


def _read_toa5_dat(path: Path) -> LoadedTable | None:
    errors: list[str] = []
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                first_line = handle.readline()
        except UnicodeDecodeError as exc:
            errors.append(f"{encoding}: {type(exc).__name__}: {exc}")
            continue
        if "TOA5" not in first_line[:32]:
            return None
        try:
            frame = pd.read_csv(path, encoding=encoding, skiprows=[0, 2, 3])
        except Exception as exc:  # pragma: no cover - surfaced in parse_failed notes
            errors.append(f"{encoding}:toa5: {type(exc).__name__}: {exc}")
            continue
        if frame.shape[1] > 1:
            return LoadedTable(frame=frame, parser_used=f"pandas.read_csv({encoding}:toa5)")
        errors.append(f"{encoding}:toa5: parsed one column")
    return LoadedTable(frame=None, parser_used="pandas.read_csv(toa5)", error="; ".join(errors))


def _read_dat_or_csv(path: Path) -> LoadedTable:
    toa5 = _read_toa5_dat(path)
    if toa5 is not None:
        return toa5

    attempts: tuple[tuple[str, dict[str, object]], ...] = (
        ("utf-8-sig:sniff", {"encoding": "utf-8-sig", "sep": None, "engine": "python"}),
        ("utf-8:sniff", {"encoding": "utf-8", "sep": None, "engine": "python"}),
        ("cp949:sniff", {"encoding": "cp949", "sep": None, "engine": "python"}),
        ("utf-8-sig:tab", {"encoding": "utf-8-sig", "sep": "\t"}),
        ("utf-8-sig:whitespace", {"encoding": "utf-8-sig", "sep": r"\s+", "engine": "python"}),
    )
    errors: list[str] = []
    for label, kwargs in attempts:
        try:
            frame = pd.read_csv(path, **kwargs)
        except Exception as exc:  # pragma: no cover - surfaced in parse_failed notes
            errors.append(f"{label}: {type(exc).__name__}: {exc}")
            continue
        if frame.shape[1] > 1:
            return LoadedTable(frame=frame, parser_used=f"pandas.read_csv({label})")
        errors.append(f"{label}: parsed one column")
    return LoadedTable(frame=None, parser_used="pandas.read_csv", error="; ".join(errors))


def _parquet_column_stats(path: Path) -> dict[str, dict[str, object]]:
    import pyarrow.parquet as pq

    parquet_file = pq.ParquetFile(path)
    names = list(parquet_file.schema_arrow.names)
    out: dict[str, dict[str, object]] = {
        name: {"null_count": 0, "num_values": 0, "min": None, "max": None} for name in names
    }
    for row_group_idx in range(parquet_file.metadata.num_row_groups):
        row_group = parquet_file.metadata.row_group(row_group_idx)
        for column_idx, name in enumerate(names):
            stats = row_group.column(column_idx).statistics
            if stats is None:
                continue
            target = out[name]
            target["null_count"] = int(target["null_count"] or 0) + int(stats.null_count or 0)
            target["num_values"] = int(target["num_values"] or 0) + int(stats.num_values or 0)
            if not stats.has_min_max:
                continue
            min_value = _jsonable_stat_value(stats.min)
            max_value = _jsonable_stat_value(stats.max)
            if target["min"] is None or _stat_less(min_value, target["min"]):
                target["min"] = min_value
            if target["max"] is None or _stat_greater(max_value, target["max"]):
                target["max"] = max_value
    return out


def _sample_columns_for_audit(columns: Sequence[str]) -> list[str]:
    matched = match_semantic_roles(columns)
    selected: list[str] = []
    for role_matches in matched.values():
        selected.extend(role_matches)
    for required in ("env_radiation_wm2_mean", "env_radiation_wm2_max"):
        if required in columns:
            selected.append(required)
    deduped = list(dict.fromkeys(selected))
    return deduped or list(columns[: min(len(columns), 20)])


def _read_large_parquet_metadata_sample(path: Path) -> LoadedTable:
    import pyarrow.parquet as pq

    parquet_file = pq.ParquetFile(path)
    column_names = tuple(str(name) for name in parquet_file.schema_arrow.names)
    sample_columns = _sample_columns_for_audit(column_names)
    try:
        first_batch = next(parquet_file.iter_batches(batch_size=10_000, columns=sample_columns), None)
    except StopIteration:
        first_batch = None
    sample = first_batch.to_pandas() if first_batch is not None else pd.DataFrame(columns=sample_columns)
    return LoadedTable(
        frame=sample,
        parser_used="pyarrow.parquet.metadata_sample",
        row_count=int(parquet_file.metadata.num_rows),
        column_names=column_names,
        dtype_map={str(field.name): str(field.type) for field in parquet_file.schema_arrow},
        column_stats=_parquet_column_stats(path),
    )


def load_input_table(path: Path) -> LoadedTable:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        if path.stat().st_size > 64 * 1024 * 1024:
            try:
                return _read_large_parquet_metadata_sample(path)
            except Exception as exc:  # pragma: no cover - surfaced in parse_failed notes
                return LoadedTable(
                    frame=None,
                    parser_used="pyarrow.parquet.metadata_sample",
                    error=f"{type(exc).__name__}: {exc}",
                )
        try:
            frame = pd.read_parquet(path)
            return LoadedTable(
                frame=frame,
                parser_used="pandas.read_parquet",
                row_count=int(frame.shape[0]),
                column_names=tuple(str(column) for column in frame.columns),
                dtype_map={str(column): str(dtype) for column, dtype in frame.dtypes.items()},
            )
        except Exception as exc:  # pragma: no cover - surfaced in parse_failed notes
            return LoadedTable(frame=None, parser_used="pandas.read_parquet", error=f"{type(exc).__name__}: {exc}")
    if suffix in {".csv", ".dat", ".txt"}:
        return _read_dat_or_csv(path)
    return LoadedTable(frame=None, parser_used="unsupported", error=f"Unsupported extension: {suffix}")


def _missing_important_roles(file_role: str, matched_roles: Mapping[str, list[str]]) -> list[str]:
    missing: list[str] = []
    for role in IMPORTANT_ROLES_BY_FILE_ROLE.get(file_role, ()):
        if role == "datetime_or_date":
            if "datetime" not in matched_roles and "date" not in matched_roles:
                missing.append(role)
        elif role not in matched_roles:
            missing.append(role)
    return missing


def _status_for(file_role: str, missing_roles: Sequence[str], parse_error: str | None) -> str:
    if parse_error:
        return "parse_failed"
    if "datetime_or_date" in missing_roles or "datetime" in missing_roles:
        return "missing_required_column"
    if file_role == "dataset1" and "radiation" in missing_roles:
        return "unsafe_for_primary_use"
    if missing_roles:
        return "ok_with_warnings"
    return "ok"


def audit_input_file(
    *,
    file_role: str,
    expected_filename: str,
    resolved_path: Path,
) -> tuple[dict[str, object], pd.DataFrame | None]:
    base_row: dict[str, object] = {
        "file_role": file_role,
        "expected_filename": expected_filename,
        "resolved_path": str(resolved_path),
        "exists": resolved_path.exists(),
        "file_size_bytes": resolved_path.stat().st_size if resolved_path.exists() else None,
        "extension": resolved_path.suffix.lower(),
        "parser_used": "",
        "row_count": None,
        "column_count": None,
        "columns_json": "[]",
        "dtype_json": "{}",
        "datetime_column": None,
        "date_column": None,
        "date_min": None,
        "date_max": None,
        "inferred_time_resolution_seconds": None,
        "loadcell_column": None,
        "loadcell_ids_json": "[]",
        "treatment_column": None,
        "treatment_values_json": "[]",
        "matched_semantic_roles_json": "{}",
        "missing_important_roles_json": "[]",
        "notes": "",
        "status": "missing_file",
    }
    if not resolved_path.exists():
        base_row["notes"] = "Required raw input file is missing."
        return base_row, None

    loaded = load_input_table(resolved_path)
    base_row["parser_used"] = loaded.parser_used
    if loaded.frame is None:
        base_row["notes"] = loaded.error or "Parse failed."
        base_row["status"] = "parse_failed"
        return base_row, None

    frame = loaded.frame
    column_names = list(loaded.column_names or tuple(str(column) for column in frame.columns))
    matched_roles = match_semantic_roles(column_names)
    datetime_column = matched_roles.get("datetime", [None])[0]
    date_column = matched_roles.get("date", [None])[0]
    date_source_column = datetime_column or date_column
    if date_source_column is not None:
        stats = (loaded.column_stats or {}).get(date_source_column, {})
        if stats.get("min") is not None:
            base_row["date_min"] = _iso_timestamp(stats.get("min"))
        if stats.get("max") is not None:
            base_row["date_max"] = _iso_timestamp(stats.get("max"))
        parsed_dates = pd.to_datetime(frame[date_source_column], errors="coerce").dropna()
        if not parsed_dates.empty:
            base_row["date_min"] = base_row["date_min"] or _iso_timestamp(parsed_dates.min())
            base_row["date_max"] = base_row["date_max"] or _iso_timestamp(parsed_dates.max())
            base_row["inferred_time_resolution_seconds"] = _infer_resolution_seconds(frame[date_source_column])

    loadcell_column = matched_roles.get("loadcell", [None])[0]
    treatment_column = matched_roles.get("treatment", [None])[0]
    missing_roles = _missing_important_roles(file_role, matched_roles)

    base_row.update(
        {
            "row_count": loaded.row_count if loaded.row_count is not None else int(frame.shape[0]),
            "column_count": len(column_names),
            "columns_json": _json_dumps(column_names),
            "dtype_json": _json_dumps(
                dict(loaded.dtype_map or {str(column): str(dtype) for column, dtype in frame.dtypes.items()})
            ),
            "datetime_column": datetime_column,
            "date_column": date_column,
            "loadcell_column": loadcell_column,
            "loadcell_ids_json": _json_dumps(
                _sorted_unique_json_values(frame[loadcell_column]) if loadcell_column else []
            ),
            "treatment_column": treatment_column,
            "treatment_values_json": _json_dumps(
                _sorted_unique_json_values(frame[treatment_column]) if treatment_column else []
            ),
            "matched_semantic_roles_json": _json_dumps(matched_roles),
            "missing_important_roles_json": _json_dumps(missing_roles),
            "column_stats_json": _json_dumps(dict(loaded.column_stats or {})),
            "status": _status_for(file_role, missing_roles, None),
        }
    )
    if missing_roles:
        base_row["notes"] = f"Missing or ambiguous roles: {', '.join(missing_roles)}"
    return base_row, frame


def _as_mapping(raw: object) -> dict[str, Any]:
    if isinstance(raw, Mapping):
        return {str(key): value for key, value in raw.items()}
    return {}


def _resolve_path(raw: str | Path, *, repo_root: Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def _input_specs_from_config(config: Mapping[str, object]) -> list[dict[str, str]]:
    raw_specs = _as_mapping(_as_mapping(config.get("tomics_haf")).get("input_files"))
    specs: list[dict[str, str]] = []
    for default_spec in DEFAULT_INPUT_FILE_SPECS:
        role = default_spec["file_role"]
        specs.append(
            {
                "file_role": role,
                "expected_filename": str(raw_specs.get(role, default_spec["expected_filename"])),
            }
        )
    return specs


def _dataset3_mapping(audit_rows_by_role: Mapping[str, Mapping[str, object]]) -> str:
    dataset3 = audit_rows_by_role.get("dataset3", {})
    if dataset3.get("loadcell_column"):
        return "direct_loadcell"
    if dataset3.get("treatment_column"):
        return "treatment_level_only"
    return "unlinked"


def _role_available(audit_rows: Sequence[Mapping[str, object]], role: str) -> bool:
    for row in audit_rows:
        try:
            matched = json.loads(str(row.get("matched_semantic_roles_json") or "{}"))
        except json.JSONDecodeError:
            continue
        if matched.get(role):
            return True
    return False


def _build_metadata(
    *,
    audit_rows: Sequence[Mapping[str, object]],
    audit_rows_by_role: Mapping[str, Mapping[str, object]],
    radiation_metadata: Mapping[str, object],
) -> dict[str, object]:
    return {
        "season_id": SEASON_ID,
        "raw_filename_note": RAW_FILENAME_NOTE,
        **SENSOR_MAPPING_METADATA,
        **dict(radiation_metadata),
        "VPD_available": _role_available(audit_rows, "vpd"),
        "LAI_available": _role_available(audit_rows, "lai"),
        "fresh_yield_available": _role_available(audit_rows, "yield_fresh"),
        "dry_yield_available": _role_available(audit_rows, "yield_dry")
        or _role_available(audit_rows, "estimated_dry_yield_from_dmc"),
        "dry_yield_is_dmc_estimated": _role_available(audit_rows, "estimated_dry_yield_from_dmc"),
        "direct_dry_yield_measured": _role_available(audit_rows, "direct_dry_yield_measured"),
        "Dataset3_mapping_confidence": _dataset3_mapping(audit_rows_by_role),
        "fruit_diameter_p_values_allowed": False,
        "fruit_diameter_allocation_calibration_target": False,
        "fruit_diameter_model_promotion_target": False,
        "shipped_TOMICS_incumbent_changed": False,
        "raw_thorp_promoted": False,
    }


def _markdown_report(
    *,
    audit_rows: Sequence[Mapping[str, object]],
    radiation_rows: Sequence[Mapping[str, object]],
    metadata: Mapping[str, object],
) -> str:
    found = [row for row in audit_rows if row.get("exists")]
    missing = [row for row in audit_rows if not row.get("exists")]
    primary = next((row for row in radiation_rows if row.get("chosen_primary")), None)
    lines = [
        "# TOMICS-HAF 2025-2C radiation source verification",
        "",
        "Day/night phases will be radiation-defined from Dataset1 when Dataset1 radiation is usable.",
        "Fixed 06:00-18:00 windows remain compatibility-only.",
        "Fruit diameter observer remains sensor-level apparent expansion diagnostics.",
        "Shipped TOMICS incumbent remains unchanged.",
        "",
        "## Files found",
    ]
    for row in found:
        lines.append(f"- `{row['file_role']}`: `{row['expected_filename']}` via `{row['parser_used']}`")
    if missing:
        lines.append("")
        lines.append("## Files missing")
        for row in missing:
            lines.append(f"- `{row['file_role']}`: `{row['expected_filename']}`")
    lines.extend(["", "## Semantic roles"])
    for row in audit_rows:
        lines.append(f"- `{row['file_role']}` status `{row['status']}`")
        lines.append(f"  - matched: `{row['matched_semantic_roles_json']}`")
        lines.append(f"  - missing/ambiguous: `{row['missing_important_roles_json']}`")
    lines.extend(["", "## Radiation decision"])
    if primary is None:
        lines.append("- No primary radiation column was selected.")
    else:
        lines.append(
            f"- Selected `{primary['candidate_column']}` from `{primary['source_file_role']}` "
            f"(rank {primary['candidate_rank']})."
        )
    lines.append(f"- Dataset1 radiation grain: `{metadata['dataset1_radiation_grain']}`")
    lines.append(f"- Dataset1 directly usable for Goal 2: `{metadata['dataset1_radiation_directly_usable']}`")
    lines.append(f"- Fallback required: `{metadata['fallback_required']}`")
    lines.append(f"- Fallback source if required: `{metadata['fallback_source_if_required']}`")
    lines.append("- Thresholds to test later: `[0, 1, 5, 10]`")
    lines.extend(["", "## Role availability"])
    lines.append(f"- VPD available: `{metadata['VPD_available']}`")
    lines.append(f"- LAI available: `{metadata['LAI_available']}`")
    lines.append(f"- Fresh yield available: `{metadata['fresh_yield_available']}`")
    lines.append(f"- Dry yield available: `{metadata['dry_yield_available']}`")
    lines.append(f"- Dataset3 mapping: `{metadata['Dataset3_mapping_confidence']}`")
    lines.extend(["", "## Unresolved assumptions"])
    notes = metadata.get("radiation_source_decision_notes") or []
    if notes:
        for note in notes:
            lines.append(f"- {note}")
    else:
        lines.append("- None beyond the recorded schema and radiation grain checks.")
    return "\n".join(lines) + "\n"


def run_tomics_haf_input_schema_audit(
    config: Mapping[str, object],
    *,
    repo_root: Path,
    config_path: Path | None = None,
) -> dict[str, object]:
    del config_path
    haf_cfg = _as_mapping(config.get("tomics_haf"))
    raw_data_root = _resolve_path(
        str(haf_cfg.get("raw_data_root", "artifacts/tomato_integrated_radiation_architecture_v1_3/input_raw")),
        repo_root=repo_root,
    )
    output_root = ensure_dir(
        _resolve_path(str(haf_cfg.get("output_root", "out/tomics/analysis/haf_2025_2c")), repo_root=repo_root)
    )

    audit_rows: list[dict[str, object]] = []
    tables_by_role: dict[str, pd.DataFrame | None] = {}
    for spec in _input_specs_from_config(config):
        path = raw_data_root / spec["expected_filename"]
        row, frame = audit_input_file(
            file_role=spec["file_role"],
            expected_filename=spec["expected_filename"],
            resolved_path=path,
        )
        audit_rows.append(row)
        tables_by_role[spec["file_role"]] = frame

    audit_rows_by_role = {str(row["file_role"]): row for row in audit_rows}
    radiation_rows, radiation_metadata = build_radiation_source_verification(
        tables_by_role,
        audit_rows_by_role,
    )
    metadata = normalize_metadata(
        _build_metadata(
        audit_rows=audit_rows,
        audit_rows_by_role=audit_rows_by_role,
        radiation_metadata=radiation_metadata,
        )
    )

    input_csv = output_root / "input_schema_audit.csv"
    input_json = output_root / "input_schema_audit.json"
    radiation_csv = output_root / "radiation_source_verification.csv"
    radiation_json = output_root / "radiation_source_verification.json"
    radiation_md = output_root / "radiation_source_verification.md"
    metadata_json = output_root / "2025_2c_tomics_haf_metadata.json"
    metadata_snapshot = output_root / "metadata_goal1_schema_radiation.json"

    pd.DataFrame.from_records(audit_rows).to_csv(input_csv, index=False)
    write_json(input_json, {"files": audit_rows})
    pd.DataFrame.from_records(radiation_rows).to_csv(radiation_csv, index=False)
    write_json(radiation_json, {"candidates": radiation_rows, "metadata": metadata})
    write_json(metadata_json, metadata)
    write_stage_metadata_snapshot(metadata_snapshot, metadata)
    radiation_md.write_text(
        _markdown_report(audit_rows=audit_rows, radiation_rows=radiation_rows, metadata=metadata),
        encoding="utf-8",
    )

    return {
        "output_root": str(output_root),
        "input_schema_audit_csv": str(input_csv),
        "input_schema_audit_json": str(input_json),
        "radiation_source_verification_csv": str(radiation_csv),
        "radiation_source_verification_json": str(radiation_json),
        "radiation_source_verification_md": str(radiation_md),
        "metadata_json": str(metadata_json),
        "metadata": metadata,
    }


__all__ = [
    "DEFAULT_INPUT_FILE_SPECS",
    "DEFAULT_ROLE_ALIASES",
    "RAW_FILENAME_NOTE",
    "SEASON_ID",
    "SENSOR_MAPPING_METADATA",
    "audit_input_file",
    "load_input_table",
    "match_semantic_roles",
    "normalize_column_name",
    "run_tomics_haf_input_schema_audit",
]
