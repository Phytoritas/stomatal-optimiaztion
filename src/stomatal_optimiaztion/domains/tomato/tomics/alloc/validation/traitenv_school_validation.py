from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .knu_data import _first_sheet_rows_from_xlsx

SCHOOL_DATASET_ID = "school_trait_bundle__yield"
SCHOOL_YIELD_STANDARD_NAME = "total_yield_weight_g"
CANONICAL_DATE_COLUMN = "Date"
CANONICAL_MEASURED_COLUMN = "Measured_Cumulative_Total_Fruit_DW (g/m^2)"
CANONICAL_ESTIMATED_COLUMN = "Estimated_Cumulative_Total_Fruit_DW (g/m^2)"
CANONICAL_DAILY_INCREMENT_COLUMN = "Source_Daily_Fruit_DW (g/m^2)"
CANONICAL_REPORTING_BASIS = "floor_area_g_m2"
DEFAULT_DRY_MATTER_RATIO = 0.065
DEFAULT_PAR_UMOL_PER_W_M2 = 4.57
DEFAULT_DRY_MATTER_CITATIONS = (
    "Ref 4",
    "Ref 8",
    "Ref 3",
    "Ref 6",
    "Ref 7",
    "Ref 9",
)
_SOURCE_ORIGIN_MANIFEST_NAME = ".source_origin.json"
_RAW_COMMON_WORKBOOK_RELATIVE_PATH = Path("40_\uc791\uc5c5\u00b7\uc7ac\ubc30\uc815\ubcf4") / (
    "\ud1a0\ub9c8\ud1a0_\uc7ac\ubc30\uc815\ubcf4_\uacf5\ud1b5.xlsx"
)
_COMMON_WORKBOOK_SEASON_COLUMN = "\uc0dd\uc721\uc870\uc0ac \ud56d\ubaa9"
_COMMON_WORKBOOK_CULTIVAR_COLUMN = "\ud488\uc885"
_COMMON_WORKBOOK_TREATMENT_COLUMN = "\ucc98\ub9ac"
_COMMON_WORKBOOK_NOTE_COLUMN = "\ud30c\uc885, \ud050\ube0c \uac00\uc2dd, \uc815\uc2dd, \uccab\uc218\ud655"
_COMMON_WORKBOOK_CROP_START_COLUMN = "\uc791\uae30 \uc2dc\uc791"
_COMMON_WORKBOOK_CROP_END_COLUMN = "\uc791\uae30 \uc885\ub8cc"
_COMMON_WORKBOOK_AREA_COLUMN = "\uc7ac\ubc30\uba74\uc801(m2)"
_COMMON_WORKBOOK_PLANT_DENSITY_COLUMN = "\uc7ac\uc2dd\ubc00\ub3c4(plants/m2)"


@dataclass(frozen=True, slots=True)
class SchoolTraitenvSourcePaths:
    crop_metadata_path: Path
    environment_path: Path
    yield_comparison_daily_path: Path
    crop_common_workbook_path: Path | None = None
    raw_repo_root: Path | None = None
    raw_repo_resolution_mode: str = "unresolved"
    source_origin_manifest_path: Path | None = None


@dataclass(frozen=True, slots=True)
class SchoolTraitenvValidationBundle:
    season: str
    treatment: str
    traitenv_root: Path
    output_root: Path
    forcing_csv_path: Path
    yield_csv_path: Path
    overlay_yaml_path: Path
    overlay_json_path: Path
    manifest_path: Path
    generated_config_paths: dict[str, Path]
    validation_start: str
    validation_end: str
    crop_start: str
    crop_end: str
    area_m2: float
    plants_per_m2: float
    dry_matter_ratio: float
    approve_runnable_contract: bool
    dataset_overlay: dict[str, Any]


def _normalize_season_label(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if re.fullmatch(r"\d+\.0", text):
        return text.split(".", maxsplit=1)[0]
    return text


def _parse_date_like(value: object, *, label: str) -> pd.Timestamp:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.notna(numeric):
        numeric_value = float(numeric)
        if 20_000 <= numeric_value <= 60_000:
            return (pd.Timestamp("1899-12-30") + pd.to_timedelta(numeric_value, unit="D")).normalize()
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"Could not parse {label}: {value!r}")
    return pd.Timestamp(parsed).normalize()


def _parse_float_like(value: object, *, label: str) -> float:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        raise ValueError(f"Missing required numeric field {label}.")
    cleaned = re.sub(r"[^0-9.+-]", "", str(value))
    if cleaned in {"", ".", "-", "+"}:
        raise ValueError(f"Could not parse numeric field {label}: {value!r}")
    return float(cleaned)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return slug.strip("-") or "value"


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def _first_nonnull_value(frame: pd.DataFrame, columns: tuple[str, ...]) -> object:
    for column in columns:
        if column not in frame.columns:
            continue
        series = frame[column].dropna()
        if not series.empty:
            return series.iloc[0]
    return None


def _resolve_existing_column(frame: pd.DataFrame, candidates: tuple[str, ...], *, label: str) -> str:
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
    raise ValueError(f"Could not resolve {label} column from candidates: {candidates!r}")


def _resolve_raw_repo_root_from_traitenv_root(root: Path) -> tuple[Path | None, Path | None, str]:
    if root.name == "traitenv" and root.parent.name == "outputs":
        candidate = root.parent.parent
        if (candidate / _RAW_COMMON_WORKBOOK_RELATIVE_PATH).exists():
            return candidate, None, "adjacent_outputs_layout"
    manifest_path = root / _SOURCE_ORIGIN_MANIFEST_NAME
    if manifest_path.exists():
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None, manifest_path, "source_origin_manifest_invalid"
        raw_repo_root = payload.get("source_raw_repo_root")
        if isinstance(raw_repo_root, str) and raw_repo_root:
            candidate = Path(raw_repo_root).expanduser().resolve()
            if (candidate / _RAW_COMMON_WORKBOOK_RELATIVE_PATH).exists():
                return candidate, manifest_path, "source_origin_manifest"
        return None, manifest_path, "source_origin_manifest_missing_workbook"
    return None, None, "unresolved"


def resolve_school_traitenv_source_paths(
    traitenv_root: str | Path,
    *,
    raw_repo_root: str | Path | None = None,
) -> SchoolTraitenvSourcePaths:
    root = Path(traitenv_root).expanduser().resolve()
    manifest_path = root / _SOURCE_ORIGIN_MANIFEST_NAME
    if raw_repo_root is not None:
        resolved_raw_root = Path(raw_repo_root).expanduser().resolve()
        raw_repo_resolution_mode = "explicit_arg"
    else:
        resolved_raw_root, inferred_manifest_path, raw_repo_resolution_mode = _resolve_raw_repo_root_from_traitenv_root(root)
        if inferred_manifest_path is not None:
            manifest_path = inferred_manifest_path
    crop_common_workbook_path = None
    if resolved_raw_root is not None:
        candidate = resolved_raw_root / _RAW_COMMON_WORKBOOK_RELATIVE_PATH
        if candidate.exists():
            crop_common_workbook_path = candidate
    paths = SchoolTraitenvSourcePaths(
        crop_metadata_path=(
            root
            / "partitioned_csv"
            / "integrated_observations"
            / "dataset_family=school_crop_info"
            / "observation_family=metadata"
            / "data.csv"
        ),
        environment_path=(
            root
            / "partitioned_csv"
            / "integrated_observations"
            / "dataset_family=school_greenhouse_environment"
            / "observation_family=environment"
            / "data.csv"
        ),
        yield_comparison_daily_path=(
            root
            / "partitioned_csv"
            / "comparison_daily"
            / "dataset_family=school_trait_bundle"
            / "observation_family=yield"
            / "data.csv"
        ),
        crop_common_workbook_path=crop_common_workbook_path,
        raw_repo_root=resolved_raw_root,
        raw_repo_resolution_mode=raw_repo_resolution_mode,
        source_origin_manifest_path=manifest_path if manifest_path.exists() else None,
    )
    required_paths = (
        paths.crop_metadata_path,
        paths.environment_path,
        paths.yield_comparison_daily_path,
    )
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"school traitenv private validation sources are missing: {missing}")
    return paths


def _rows_to_frame(rows: list[dict[int, Any]]) -> pd.DataFrame:
    if not rows:
        raise ValueError("Workbook is empty.")
    header_map = rows[0]
    if not header_map:
        raise ValueError("Workbook header row is empty.")
    max_idx = max(header_map)
    headers = [str(header_map.get(idx, "")).strip() for idx in range(max_idx + 1)]
    records: list[dict[str, Any]] = []
    for raw_row in rows[1:]:
        record: dict[str, Any] = {}
        for idx, value in raw_row.items():
            if idx > max_idx:
                continue
            header = headers[idx]
            if header:
                record[header] = value
        if any(value not in (None, "") for value in record.values()):
            records.append(record)
    return pd.DataFrame.from_records(records)


def _select_crop_context_from_processed_metadata(
    crop_df: pd.DataFrame,
    *,
    season: str,
    treatment: str,
) -> tuple[float, float, pd.Timestamp, pd.Timestamp, dict[str, Any]]:
    work = crop_df.copy()
    work["season_label_norm"] = work.get("season_label", pd.Series(dtype=object)).map(_normalize_season_label)
    season_rows = work.loc[work["season_label_norm"].eq(str(season))].copy()
    if season_rows.empty:
        raise ValueError(f"Could not resolve school crop metadata row for season={season!r}, treatment={treatment!r}.")

    context_rows = season_rows
    treatment_columns = [column for column in ("treatment", "treatment_plan") if column in work.columns]
    for column in treatment_columns:
        treatment_mask = season_rows[column].fillna("").astype(str).str.contains(treatment, case=False, na=False)
        if treatment_mask.any():
            context_rows = season_rows.loc[treatment_mask].copy()
            break

    area = _parse_float_like(
        _first_nonnull_value(season_rows, ("crop_area_m2", "area_m2")),
        label="school crop area",
    )
    plants_per_m2 = _parse_float_like(
        _first_nonnull_value(season_rows, ("plants_per_m2", "plant_density_plants_m2")),
        label="school plant density",
    )
    crop_start = _parse_date_like(_first_nonnull_value(season_rows, ("crop_start", "crop_start_date")), label="school crop start")
    crop_end = _parse_date_like(_first_nonnull_value(season_rows, ("crop_end", "crop_end_date")), label="school crop end")
    context = {
        "cultivar": str(_first_nonnull_value(context_rows, ("cultivar",)) or "unknown"),
        "treatment_label": str(_first_nonnull_value(context_rows, ("treatment_plan", "treatment")) or treatment),
        "season_notes": str(_first_nonnull_value(season_rows, ("season_notes",)) or ""),
        "metadata_source_kind": "processed_crop_metadata_csv",
    }
    return area, plants_per_m2, crop_start, crop_end, context


def _select_crop_context_from_common_workbook(
    crop_common_workbook_path: Path,
    *,
    season: str,
    treatment: str,
) -> tuple[float, float, pd.Timestamp, pd.Timestamp, dict[str, Any]]:
    workbook_df = _rows_to_frame(_first_sheet_rows_from_xlsx(crop_common_workbook_path))
    if _COMMON_WORKBOOK_SEASON_COLUMN not in workbook_df.columns:
        raise ValueError(
            f"Common crop workbook is missing required season column {_COMMON_WORKBOOK_SEASON_COLUMN!r}: {crop_common_workbook_path}"
        )
    season_mask = workbook_df[_COMMON_WORKBOOK_SEASON_COLUMN].fillna("").astype(str).str.contains(str(season), na=False)
    season_rows = workbook_df.loc[season_mask].copy()
    if season_rows.empty:
        raise ValueError(
            f"Could not resolve school crop workbook row for season={season!r}, treatment={treatment!r}: {crop_common_workbook_path}"
        )

    context_rows = season_rows
    if _COMMON_WORKBOOK_TREATMENT_COLUMN in season_rows.columns:
        treatment_mask = (
            season_rows[_COMMON_WORKBOOK_TREATMENT_COLUMN].fillna("").astype(str).str.contains(treatment, case=False, na=False)
        )
        if treatment_mask.any():
            context_rows = season_rows.loc[treatment_mask].copy()

    area = _parse_float_like(_first_nonnull_value(season_rows, (_COMMON_WORKBOOK_AREA_COLUMN,)), label="school crop area")
    plants_per_m2 = _parse_float_like(
        _first_nonnull_value(season_rows, (_COMMON_WORKBOOK_PLANT_DENSITY_COLUMN,)),
        label="school plant density",
    )
    crop_start = _parse_date_like(
        _first_nonnull_value(season_rows, (_COMMON_WORKBOOK_CROP_START_COLUMN,)),
        label="school crop start",
    )
    crop_end = _parse_date_like(
        _first_nonnull_value(season_rows, (_COMMON_WORKBOOK_CROP_END_COLUMN,)),
        label="school crop end",
    )
    context = {
        "cultivar": str(_first_nonnull_value(context_rows, (_COMMON_WORKBOOK_CULTIVAR_COLUMN,)) or "unknown"),
        "treatment_label": str(_first_nonnull_value(context_rows, (_COMMON_WORKBOOK_TREATMENT_COLUMN,)) or treatment),
        "season_notes": str(_first_nonnull_value(season_rows, (_COMMON_WORKBOOK_NOTE_COLUMN,)) or ""),
        "metadata_source_kind": "raw_common_workbook",
        "metadata_source_path": str(crop_common_workbook_path),
    }
    return area, plants_per_m2, crop_start, crop_end, context


def _select_crop_context(
    crop_df: pd.DataFrame,
    *,
    season: str,
    treatment: str,
    crop_common_workbook_path: Path | None = None,
) -> tuple[float, float, pd.Timestamp, pd.Timestamp, dict[str, Any]]:
    try:
        return _select_crop_context_from_processed_metadata(crop_df, season=season, treatment=treatment)
    except ValueError:
        if crop_common_workbook_path is None:
            raise
        return _select_crop_context_from_common_workbook(
            crop_common_workbook_path,
            season=season,
            treatment=treatment,
        )


def _resolved_yield_value(series: pd.DataFrame) -> pd.Series:
    for column in ("value_sum", "value_mean", "value"):
        if column in series.columns:
            return pd.to_numeric(series[column], errors="coerce")
    raise ValueError("school traitenv comparison_daily file is missing value_sum/value_mean/value columns.")


def build_school_traitenv_yield_frame(
    *,
    yield_daily_path: Path,
    season: str,
    treatment: str,
    area_m2: float,
    dry_matter_ratio: float,
) -> tuple[pd.DataFrame, str, str]:
    yield_daily_df = _read_csv(yield_daily_path)
    work = yield_daily_df.copy()
    work["season_label_norm"] = work.get("season_label", pd.Series(dtype=object)).map(_normalize_season_label)
    work["parsed_date"] = pd.to_datetime(work.get("comparison_date"), errors="coerce").dt.normalize()
    work["resolved_value"] = _resolved_yield_value(work)
    mask = (
        work["season_label_norm"].eq(str(season))
        & work.get("standard_name", pd.Series(dtype=object)).fillna("").astype(str).eq(SCHOOL_YIELD_STANDARD_NAME)
        & work["parsed_date"].notna()
    )
    if "treatment" in work.columns:
        mask &= work["treatment"].fillna("").astype(str).str.contains(treatment, case=False, na=False)
    filtered = work.loc[mask].copy()
    if filtered.empty:
        raise ValueError(
            f"Could not find school traitenv yield comparison rows for season={season!r}, treatment={treatment!r}."
        )
    filtered["resolved_value"] = pd.to_numeric(filtered["resolved_value"], errors="coerce").fillna(0.0)
    grouped = filtered.groupby("parsed_date", as_index=False).agg(
        Source_Daily_Fresh_Weight_Total_g=("resolved_value", "sum"),
        Source_Comparison_Entities=("comparison_entity", "nunique"),
    )
    grouped["Source_Daily_Fresh_Weight_g_m2"] = grouped["Source_Daily_Fresh_Weight_Total_g"] / float(area_m2)
    grouped[CANONICAL_DAILY_INCREMENT_COLUMN] = grouped["Source_Daily_Fresh_Weight_g_m2"] * float(dry_matter_ratio)
    grouped[CANONICAL_MEASURED_COLUMN] = grouped[CANONICAL_DAILY_INCREMENT_COLUMN].cumsum()
    grouped[CANONICAL_ESTIMATED_COLUMN] = grouped[CANONICAL_MEASURED_COLUMN]
    grouped["Source_Dry_Matter_Ratio"] = float(dry_matter_ratio)
    grouped[CANONICAL_DATE_COLUMN] = grouped["parsed_date"].dt.strftime("%Y-%m-%d")
    ordered = grouped[
        [
            CANONICAL_DATE_COLUMN,
            "Source_Daily_Fresh_Weight_Total_g",
            "Source_Daily_Fresh_Weight_g_m2",
            CANONICAL_DAILY_INCREMENT_COLUMN,
            CANONICAL_MEASURED_COLUMN,
            CANONICAL_ESTIMATED_COLUMN,
            "Source_Dry_Matter_Ratio",
            "Source_Comparison_Entities",
        ]
    ].copy()
    validation_start = str(ordered[CANONICAL_DATE_COLUMN].iloc[0])
    validation_end = str(ordered[CANONICAL_DATE_COLUMN].iloc[-1])
    return ordered, validation_start, validation_end


def build_school_traitenv_forcing_frame(
    *,
    environment_path: Path,
    season: str,
    crop_start: pd.Timestamp,
    crop_end: pd.Timestamp,
    par_umol_per_w_m2: float,
) -> pd.DataFrame:
    env_df = _read_csv(environment_path)
    work = env_df.copy()
    work["season_label_norm"] = work.get("season_label", pd.Series(dtype=object)).map(_normalize_season_label)
    work["parsed_timestamp"] = pd.to_datetime(work.get("Timestamp"), errors="coerce")
    work["parsed_date"] = work["parsed_timestamp"].dt.normalize()
    mask = (
        work["season_label_norm"].eq(str(season))
        & work["parsed_timestamp"].notna()
        & work["parsed_date"].between(crop_start, crop_end, inclusive="both")
    )
    filtered = work.loc[mask].copy()
    if filtered.empty:
        raise ValueError(f"Could not find school greenhouse environment rows for season={season!r}.")
    temp_column = _resolve_existing_column(
        filtered,
        ("Air temperature (°C)_mean", "Air temperature (째C)_mean", "온도_내부_mean", "Air temperature_mean"),
        label="school air temperature",
    )
    radiation_column = _resolve_existing_column(
        filtered,
        (
            "Inside radiation intensity (W/m2)_mean",
            "내부-내부일사량_mean",
            "Radiation intensity in_mean",
        ),
        label="school radiation",
    )
    co2_column = _resolve_existing_column(
        filtered,
        ("CO2 (ppm)_mean", "내부-내부CO2_mean", "CO2_mean"),
        label="school CO2",
    )
    rh_column = _resolve_existing_column(
        filtered,
        ("RH (%)_mean", "RH_mean", "상대습도_내부_mean", "내부-내부습도_mean"),
        label="school RH",
    )
    wind_column = _resolve_existing_column(
        filtered,
        ("Wind speed (m/s)_mean", "외부-외부풍속_mean", "풍속_외부_mean"),
        label="school wind speed",
    )
    forcing = pd.DataFrame(
        {
            "datetime": filtered["parsed_timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S"),
            "T_air_C": pd.to_numeric(filtered[temp_column], errors="coerce"),
            "PAR_umol": pd.to_numeric(filtered[radiation_column], errors="coerce") * float(par_umol_per_w_m2),
            "CO2_ppm": pd.to_numeric(filtered[co2_column], errors="coerce"),
            "RH_percent": pd.to_numeric(filtered[rh_column], errors="coerce"),
            "wind_speed_ms": pd.to_numeric(filtered[wind_column], errors="coerce"),
        }
    )
    forcing = forcing.dropna(subset=["T_air_C", "PAR_umol", "CO2_ppm", "RH_percent", "wind_speed_ms"]).copy()
    forcing = forcing.sort_values("datetime").reset_index(drop=True)
    if forcing.empty:
        raise ValueError("Derived school traitenv forcing frame is empty after numeric filtering.")
    return forcing


def build_school_traitenv_dataset_overlay(
    *,
    traitenv_root: Path,
    source_paths: SchoolTraitenvSourcePaths,
    forcing_csv_path: Path,
    yield_csv_path: Path,
    season: str,
    treatment: str,
    validation_start: str,
    validation_end: str,
    crop_start: str,
    crop_end: str,
    area_m2: float,
    plants_per_m2: float,
    dry_matter_ratio: float,
    approve_runnable_contract: bool,
    crop_context: dict[str, Any],
) -> dict[str, Any]:
    source_path_payload = {
        "crop_metadata_path": str(source_paths.crop_metadata_path),
        "environment_path": str(source_paths.environment_path),
        "yield_comparison_daily_path": str(source_paths.yield_comparison_daily_path),
        "crop_common_workbook_path": (
            str(source_paths.crop_common_workbook_path) if source_paths.crop_common_workbook_path is not None else None
        ),
        "raw_repo_root": str(source_paths.raw_repo_root) if source_paths.raw_repo_root is not None else None,
        "raw_repo_resolution_mode": source_paths.raw_repo_resolution_mode,
        "source_origin_manifest_path": (
            str(source_paths.source_origin_manifest_path) if source_paths.source_origin_manifest_path is not None else None
        ),
    }
    return {
        "dataset_id": SCHOOL_DATASET_ID,
        "dataset_kind": "traitenv_private_reviewed_candidate",
        "display_name": "School measured harvest derived from traitenv private bundle",
        "ingestion_status": None,
        "blocker_codes": [],
        "forcing_path": str(forcing_csv_path),
        "observed_harvest_path": str(yield_csv_path),
        "validation_start": validation_start,
        "validation_end": validation_end,
        "cultivar": str(crop_context.get("cultivar", "unknown")),
        "greenhouse": "school_greenhouse",
        "season": str(season),
        "basis": {
            "reporting_basis": CANONICAL_REPORTING_BASIS,
            "plants_per_m2": float(plants_per_m2),
        },
        "observation": {
            "date_column": CANONICAL_DATE_COLUMN,
            "measured_cumulative_column": CANONICAL_MEASURED_COLUMN,
            "estimated_cumulative_column": CANONICAL_ESTIMATED_COLUMN,
            "measured_semantics": "cumulative_harvested_fruit_dry_weight_floor_area",
            "daily_increment_column": CANONICAL_DAILY_INCREMENT_COLUMN,
        },
        "dry_matter_conversion": {
            "mode": "literature_fixed_ratio",
            "fresh_weight_column": "Source_Daily_Fresh_Weight_Total_g",
            "dry_matter_ratio": float(dry_matter_ratio),
            "dry_matter_ratio_low": 0.05,
            "dry_matter_ratio_high": 0.10,
            "citations": list(DEFAULT_DRY_MATTER_CITATIONS),
            "review_only": not approve_runnable_contract,
        },
        "sanitized_fixture": {
            "fixture_kind": "private_traitenv_reviewed_derivative",
            "forcing_fixture_path": str(forcing_csv_path),
            "observed_harvest_fixture_path": str(yield_csv_path),
        },
        "notes": {
            "dataset_family": "school_trait_bundle",
            "observation_family": "yield",
            "dataset_role_hint": (
                "measured_harvest_runnable" if approve_runnable_contract else "measured_harvest_review_only"
            ),
            "observed_harvest_derivation": "derived_dw_from_measured_fresh_school_harvest",
            "is_direct_dry_weight": False,
            "uses_literature_dry_matter_fraction": True,
            "dry_weight_derivation_review_grade": (
                "manual_reviewed_private" if approve_runnable_contract else "review_only"
            ),
            "private_derivation_official_mode": "manual_reviewed_derivative",
            "private_derivation_helper_role": "local_preparation_utility",
            "private_derivation_public_promotion_default": "unchanged",
            "private_derivation_kind": "traitenv_school_private_reviewed_bundle",
            "private_derivation_approved_runnable_contract": bool(approve_runnable_contract),
            "private_derivation_validation_season": str(season),
            "private_derivation_treatment": str(treatment),
            "private_derivation_crop_start": crop_start,
            "private_derivation_crop_end": crop_end,
            "private_derivation_validation_start": validation_start,
            "private_derivation_validation_end": validation_end,
            "private_derivation_area_m2": float(area_m2),
            "private_derivation_plants_per_m2": float(plants_per_m2),
            "private_derivation_dry_matter_ratio": float(dry_matter_ratio),
            "private_derivation_traitenv_root": str(traitenv_root),
            "private_derivation_source_paths": source_path_payload,
            "private_derivation_crop_context": crop_context,
        },
    }


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _calibration_end_from_validation_start(validation_start: str) -> str:
    return str((pd.Timestamp(validation_start) + pd.Timedelta(days=11)).date())


def _school_config_slug(season: str, treatment: str) -> str:
    return f"school-traitenv-{season}-{_slugify(treatment)}"


def write_school_traitenv_generated_configs(
    *,
    repo_root: Path,
    output_root: Path,
    overlay_item: dict[str, Any],
    forcing_csv_path: Path,
    yield_csv_path: Path,
    season: str,
    treatment: str,
    validation_start: str,
    current_vs_promoted_base_config: Path,
    harvest_factorial_base_config: Path,
    multidataset_base_config: Path,
    promotion_gate_base_config: Path,
) -> dict[str, Path]:
    config_slug = _school_config_slug(season, treatment)
    config_root = output_root / "configs"
    current_cfg_path = config_root / f"tomics_current_vs_promoted_factorial_{config_slug}.yaml"
    harvest_cfg_path = config_root / f"tomics_harvest_family_factorial_{config_slug}.yaml"
    multidataset_cfg_path = config_root / f"tomics_multidataset_harvest_factorial_{config_slug}.yaml"
    gate_cfg_path = config_root / f"tomics_multidataset_harvest_promotion_gate_{config_slug}.yaml"

    current_output_root = output_root / "architecture" / "current-factorial"
    promoted_output_root = output_root / "architecture" / "promoted-factorial"
    comparison_output_root = output_root / "architecture" / "comparison"
    prepared_output_root = output_root / "prepared"
    harvest_output_root = output_root / "harvest-family"
    multidataset_output_root = output_root / "multidataset"

    current_cfg = copy.deepcopy(_load_yaml(current_vs_promoted_base_config))
    current_cfg["exp"]["name"] = f"tomics_current_vs_promoted_factorial_{config_slug}"
    current_cfg["paths"] = {"repo_root": str(repo_root)}
    current_cfg["validation"].update(
        {
            "forcing_csv_path": str(forcing_csv_path),
            "yield_xlsx_path": str(yield_csv_path),
            "prepared_output_root": str(prepared_output_root),
            "resample_rule": "1D",
            "calibration_end": _calibration_end_from_validation_start(validation_start),
        }
    )
    current_cfg["current"]["base_config"] = str((repo_root / "configs" / "exp" / "tomics_allocation_factorial.yaml").resolve())
    current_cfg["promoted"]["base_config"] = str(
        (repo_root / "configs" / "exp" / "tomics_allocation_factorial.yaml").resolve()
    )
    current_cfg["paths"].update(
        {
            "current_output_root": str(current_output_root),
            "promoted_output_root": str(promoted_output_root),
            "comparison_output_root": str(comparison_output_root),
        }
    )
    for section in ("plots",):
        current_cfg[section] = {
            key: str((repo_root / Path(value)).resolve()) if isinstance(value, str) and not Path(value).is_absolute() else value
            for key, value in current_cfg.get(section, {}).items()
        }
    if "prior_selected_architecture_json" in current_cfg.get("current", {}):
        prior_path = Path(str(current_cfg["current"]["prior_selected_architecture_json"]))
        if not prior_path.is_absolute():
            current_cfg["current"]["prior_selected_architecture_json"] = str((repo_root / prior_path).resolve())
    _write_yaml(current_cfg_path, current_cfg)

    harvest_cfg = copy.deepcopy(_load_yaml(harvest_factorial_base_config))
    harvest_cfg["exp"]["name"] = f"tomics_harvest_family_factorial_{config_slug}"
    harvest_cfg["paths"] = {"repo_root": str(repo_root)}
    harvest_cfg["validation"].update(
        {
            "forcing_csv_path": str(forcing_csv_path),
            "yield_xlsx_path": str(yield_csv_path),
            "prepared_output_root": str(prepared_output_root),
            "resample_rule": "1D",
            "calibration_end": _calibration_end_from_validation_start(validation_start),
        }
    )
    harvest_cfg["reference"] = {
        "current_vs_promoted_config": str(current_cfg_path),
        "current_output_root": str(current_output_root),
        "promoted_output_root": str(promoted_output_root),
    }
    harvest_cfg["harvest_factorial"]["output_root"] = str(harvest_output_root)
    for key, value in harvest_cfg["harvest_factorial"].items():
        if key.endswith("_spec") and isinstance(value, str) and not Path(value).is_absolute():
            harvest_cfg["harvest_factorial"][key] = str((repo_root / value).resolve())
    _write_yaml(harvest_cfg_path, harvest_cfg)

    multidataset_cfg = copy.deepcopy(_load_yaml(multidataset_base_config))
    multidataset_cfg["exp"]["name"] = f"tomics_multidataset_harvest_factorial_{config_slug}"
    datasets_cfg = multidataset_cfg.setdefault("validation", {}).setdefault("datasets", {})
    existing_items = list(datasets_cfg.get("items", []))
    merged_items = [item for item in existing_items if str(item.get("dataset_id", "")) != SCHOOL_DATASET_ID]
    merged_items.append(overlay_item)
    datasets_cfg["items"] = merged_items
    default_dataset_ids = [str(value) for value in datasets_cfg.get("default_dataset_ids", [])]
    if SCHOOL_DATASET_ID not in default_dataset_ids:
        default_dataset_ids.append(SCHOOL_DATASET_ID)
    datasets_cfg["default_dataset_ids"] = default_dataset_ids
    multidataset_cfg["validation"]["multidataset_factorial"]["output_root"] = str(multidataset_output_root)
    multidataset_cfg["validation"]["multidataset_factorial"].setdefault("dataset_factorial_roots", {})
    multidataset_cfg["validation"]["multidataset_factorial"]["dataset_factorial_roots"][SCHOOL_DATASET_ID] = str(
        harvest_output_root
    )
    _write_yaml(multidataset_cfg_path, multidataset_cfg)

    gate_cfg = copy.deepcopy(_load_yaml(promotion_gate_base_config))
    gate_cfg["exp"]["name"] = f"tomics_multidataset_harvest_promotion_gate_{config_slug}"
    gate_cfg.setdefault("validation", {}).setdefault("multidataset_promotion_gate", {})
    gate_cfg["validation"]["multidataset_promotion_gate"]["scorecard_root"] = str(multidataset_output_root)
    gate_cfg["validation"]["multidataset_promotion_gate"]["output_root"] = str(multidataset_output_root)
    _write_yaml(gate_cfg_path, gate_cfg)

    return {
        "current_vs_promoted_config": current_cfg_path,
        "harvest_factorial_config": harvest_cfg_path,
        "multidataset_factorial_config": multidataset_cfg_path,
        "multidataset_promotion_gate_config": gate_cfg_path,
    }


def build_school_traitenv_validation_bundle(
    *,
    traitenv_root: str | Path,
    output_root: str | Path,
    repo_root: str | Path,
    raw_repo_root: str | Path | None = None,
    season: str = "2024",
    treatment: str = "Control",
    dry_matter_ratio: float = DEFAULT_DRY_MATTER_RATIO,
    par_umol_per_w_m2: float = DEFAULT_PAR_UMOL_PER_W_M2,
    approve_runnable_contract: bool = False,
    current_vs_promoted_base_config: str | Path = "configs/exp/tomics_current_vs_promoted_factorial_knu.yaml",
    harvest_factorial_base_config: str | Path = "configs/exp/tomics_knu_harvest_family_factorial.yaml",
    multidataset_base_config: str | Path = "configs/exp/tomics_multidataset_harvest_factorial.yaml",
    promotion_gate_base_config: str | Path = "configs/exp/tomics_multidataset_harvest_promotion_gate.yaml",
) -> SchoolTraitenvValidationBundle:
    traitenv_root_path = Path(traitenv_root).expanduser().resolve()
    repo_root_path = Path(repo_root).expanduser().resolve()
    output_root_path = Path(output_root).expanduser().resolve()
    output_root_path.mkdir(parents=True, exist_ok=True)
    source_paths = resolve_school_traitenv_source_paths(traitenv_root_path, raw_repo_root=raw_repo_root)

    area_m2, plants_per_m2, crop_start, crop_end, crop_context = _select_crop_context(
        _read_csv(source_paths.crop_metadata_path),
        season=str(season),
        treatment=treatment,
        crop_common_workbook_path=source_paths.crop_common_workbook_path,
    )
    yield_frame, validation_start, validation_end = build_school_traitenv_yield_frame(
        yield_daily_path=source_paths.yield_comparison_daily_path,
        season=str(season),
        treatment=treatment,
        area_m2=area_m2,
        dry_matter_ratio=float(dry_matter_ratio),
    )
    forcing_frame = build_school_traitenv_forcing_frame(
        environment_path=source_paths.environment_path,
        season=str(season),
        crop_start=crop_start,
        crop_end=crop_end,
        par_umol_per_w_m2=float(par_umol_per_w_m2),
    )

    season_slug = _slugify(str(season))
    treatment_slug = _slugify(treatment)
    forcing_csv_path = output_root_path / f"school_traitenv_forcing_{season_slug}_{treatment_slug}.csv"
    yield_csv_path = output_root_path / f"school_traitenv_yield_{season_slug}_{treatment_slug}.csv"
    overlay_yaml_path = output_root_path / f"school_traitenv_dataset_overlay_{season_slug}_{treatment_slug}.yaml"
    overlay_json_path = output_root_path / f"school_traitenv_dataset_overlay_{season_slug}_{treatment_slug}.json"
    manifest_path = output_root_path / f"school_traitenv_bundle_manifest_{season_slug}_{treatment_slug}.json"
    forcing_frame.to_csv(forcing_csv_path, index=False)
    yield_frame.to_csv(yield_csv_path, index=False)

    dataset_overlay = build_school_traitenv_dataset_overlay(
        traitenv_root=traitenv_root_path,
        source_paths=source_paths,
        forcing_csv_path=forcing_csv_path,
        yield_csv_path=yield_csv_path,
        season=str(season),
        treatment=treatment,
        validation_start=validation_start,
        validation_end=validation_end,
        crop_start=str(crop_start.date()),
        crop_end=str(crop_end.date()),
        area_m2=area_m2,
        plants_per_m2=plants_per_m2,
        dry_matter_ratio=float(dry_matter_ratio),
        approve_runnable_contract=approve_runnable_contract,
        crop_context=crop_context,
    )
    overlay_json_path.write_text(json.dumps(dataset_overlay, indent=2, sort_keys=True), encoding="utf-8")
    _write_yaml(overlay_yaml_path, {"validation": {"datasets": {"items": [dataset_overlay]}}})

    generated_config_paths = write_school_traitenv_generated_configs(
        repo_root=repo_root_path,
        output_root=output_root_path,
        overlay_item=dataset_overlay,
        forcing_csv_path=forcing_csv_path,
        yield_csv_path=yield_csv_path,
        season=str(season),
        treatment=treatment,
        validation_start=validation_start,
        current_vs_promoted_base_config=(repo_root_path / current_vs_promoted_base_config).resolve(),
        harvest_factorial_base_config=(repo_root_path / harvest_factorial_base_config).resolve(),
        multidataset_base_config=(repo_root_path / multidataset_base_config).resolve(),
        promotion_gate_base_config=(repo_root_path / promotion_gate_base_config).resolve(),
    )

    manifest = {
        "dataset_id": SCHOOL_DATASET_ID,
        "season": str(season),
        "treatment": treatment,
        "traitenv_root": str(traitenv_root_path),
        "source_paths": {
            "crop_metadata_path": str(source_paths.crop_metadata_path),
            "environment_path": str(source_paths.environment_path),
            "yield_comparison_daily_path": str(source_paths.yield_comparison_daily_path),
            "crop_common_workbook_path": (
                str(source_paths.crop_common_workbook_path) if source_paths.crop_common_workbook_path is not None else None
            ),
            "raw_repo_root": str(source_paths.raw_repo_root) if source_paths.raw_repo_root is not None else None,
            "raw_repo_resolution_mode": source_paths.raw_repo_resolution_mode,
            "source_origin_manifest_path": (
                str(source_paths.source_origin_manifest_path) if source_paths.source_origin_manifest_path is not None else None
            ),
        },
        "output_root": str(output_root_path),
        "forcing_csv_path": str(forcing_csv_path),
        "yield_csv_path": str(yield_csv_path),
        "overlay_yaml_path": str(overlay_yaml_path),
        "overlay_json_path": str(overlay_json_path),
        "validation_start": validation_start,
        "validation_end": validation_end,
        "crop_start": str(crop_start.date()),
        "crop_end": str(crop_end.date()),
        "area_m2": float(area_m2),
        "plants_per_m2": float(plants_per_m2),
        "dry_matter_ratio": float(dry_matter_ratio),
        "approve_runnable_contract": bool(approve_runnable_contract),
        "workflow_contract": {
            "official_mode": "manual_reviewed_derivative",
            "helper_role": "local_preparation_utility",
            "runnable_approval_required": True,
            "generated_private_overlay_is_locally_runnable": bool(approve_runnable_contract),
            "public_registry_mutated": False,
            "public_promotion_semantics_unchanged": True,
            "raw_repo_resolution_mode": source_paths.raw_repo_resolution_mode,
            "source_origin_manifest_path": (
                str(source_paths.source_origin_manifest_path) if source_paths.source_origin_manifest_path is not None else None
            ),
        },
        "generated_configs": {key: str(value) for key, value in generated_config_paths.items()},
        "source_coverage": {
            "forcing_rows": int(len(forcing_frame)),
            "yield_rows": int(len(yield_frame)),
            "yield_final_cumulative_g_m2": float(yield_frame[CANONICAL_MEASURED_COLUMN].iloc[-1]),
        },
        "dataset_overlay": dataset_overlay,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return SchoolTraitenvValidationBundle(
        season=str(season),
        treatment=treatment,
        traitenv_root=traitenv_root_path,
        output_root=output_root_path,
        forcing_csv_path=forcing_csv_path,
        yield_csv_path=yield_csv_path,
        overlay_yaml_path=overlay_yaml_path,
        overlay_json_path=overlay_json_path,
        manifest_path=manifest_path,
        generated_config_paths=generated_config_paths,
        validation_start=validation_start,
        validation_end=validation_end,
        crop_start=str(crop_start.date()),
        crop_end=str(crop_end.date()),
        area_m2=float(area_m2),
        plants_per_m2=float(plants_per_m2),
        dry_matter_ratio=float(dry_matter_ratio),
        approve_runnable_contract=bool(approve_runnable_contract),
        dataset_overlay=dataset_overlay,
    )


__all__ = [
    "CANONICAL_DAILY_INCREMENT_COLUMN",
    "CANONICAL_DATE_COLUMN",
    "CANONICAL_ESTIMATED_COLUMN",
    "CANONICAL_MEASURED_COLUMN",
    "CANONICAL_REPORTING_BASIS",
    "DEFAULT_DRY_MATTER_CITATIONS",
    "DEFAULT_DRY_MATTER_RATIO",
    "DEFAULT_PAR_UMOL_PER_W_M2",
    "SCHOOL_DATASET_ID",
    "SchoolTraitenvSourcePaths",
    "SchoolTraitenvValidationBundle",
    "build_school_traitenv_dataset_overlay",
    "build_school_traitenv_forcing_frame",
    "build_school_traitenv_validation_bundle",
    "build_school_traitenv_yield_frame",
    "resolve_school_traitenv_source_paths",
    "write_school_traitenv_generated_configs",
]
