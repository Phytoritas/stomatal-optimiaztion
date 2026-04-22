from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, write_json
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.contracts import (
    DatasetMetadataContract,
    is_measured_harvest_runnable,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.knu_data import (
    _first_sheet_rows_from_xlsx,
    read_knu_forcing_csv,
    resample_forcing,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.metrics import (
    to_floor_area_value,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.theta_proxy import (
    DEFAULT_SCENARIOS,
    apply_theta_substrate_proxy,
    theta_proxy_summary,
)


CANONICAL_REPORTING_BASIS = "floor_area_g_m2"
ROOTZONE_REQUIRED_COLUMNS = (
    "datetime",
    "theta_substrate",
    "slab_weight_kg",
    "sensor_id",
    "zone_id",
    "depth_cm",
)
ROOTZONE_EC_REQUIRED_COLUMNS = (
    "datetime",
    "rootzone_ec_dS_m",
    "sensor_id",
    "zone_id",
    "depth_cm",
)


@dataclass(frozen=True, slots=True)
class PreparedDatasetThetaScenario:
    scenario_id: str
    minute_df: pd.DataFrame
    hourly_df: pd.DataFrame
    forcing_csv_path: Path
    summary: dict[str, object]


@dataclass(frozen=True, slots=True)
class PreparedMeasuredHarvestBundle:
    dataset_id: str
    observed_df: pd.DataFrame
    validation_start: pd.Timestamp
    validation_end: pd.Timestamp
    calibration_end: pd.Timestamp
    holdout_start: pd.Timestamp
    prepared_root: Path
    scenarios: dict[str, PreparedDatasetThetaScenario]
    source_unit_label: str
    reporting_basis_in: str
    reporting_basis_canonical: str
    basis_normalization_resolved: bool
    normalization_factor_to_floor_area: float
    manifest_summary: dict[str, object]
    rootzone_df: pd.DataFrame | None = None
    rootzone_ec_df: pd.DataFrame | None = None
    rootzone_path: Path | None = None
    rootzone_ec_path: Path | None = None
    rootzone_summary: dict[str, object] = field(default_factory=dict)


def _as_list(raw: object) -> list[Any]:
    if isinstance(raw, list):
        return list(raw)
    return []


def _read_first_sheet_frame(path: Path) -> pd.DataFrame:
    rows = _first_sheet_rows_from_xlsx(path)
    if not rows:
        raise ValueError(f"Observation workbook {path} is empty.")
    header_map = rows[0]
    max_idx = max(header_map) if header_map else -1
    headers = [
        str(header_map.get(idx)).strip() if header_map.get(idx) is not None else ""
        for idx in range(max_idx + 1)
    ]
    records: list[dict[str, Any]] = []
    for raw_row in rows[1:]:
        record: dict[str, Any] = {}
        for idx, header in enumerate(headers):
            if not header:
                continue
            record[header] = raw_row.get(idx)
        if record:
            records.append(record)
    return pd.DataFrame.from_records(records)


def read_dataset_observation_table(path: str | Path) -> pd.DataFrame:
    resolved_path = Path(path)
    suffix = resolved_path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(resolved_path)
    if suffix in {".xlsx", ".xlsm"}:
        return _read_first_sheet_frame(resolved_path)
    raise ValueError(f"Unsupported observation table format {resolved_path.suffix!r}.")


def _read_csv_with_required_columns(
    path: str | Path,
    *,
    required_columns: tuple[str, ...],
    numeric_columns: tuple[str, ...],
    table_label: str,
) -> pd.DataFrame:
    resolved_path = Path(path)
    frame = pd.read_csv(resolved_path)
    missing = [column for column in required_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{table_label} {resolved_path} is missing required columns: {missing}")

    frame = frame.copy()
    frame["datetime"] = pd.to_datetime(frame["datetime"], errors="coerce")
    if frame["datetime"].isna().any():
        raise ValueError(f"{table_label} {resolved_path} contains blank or invalid datetime values.")
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    sort_columns = ["datetime", *[column for column in ("sensor_id", "zone_id", "depth_cm") if column in frame.columns]]
    return frame.sort_values(sort_columns).reset_index(drop=True)


def read_rootzone_table(path: str | Path) -> pd.DataFrame:
    """Read measured KNU substrate water content and slab weight without imputing blanks."""

    return _read_csv_with_required_columns(
        path,
        required_columns=ROOTZONE_REQUIRED_COLUMNS,
        numeric_columns=("theta_substrate", "slab_weight_kg", "depth_cm"),
        table_label="Rootzone table",
    )


def read_rootzone_ec_table(path: str | Path) -> pd.DataFrame:
    """Read measured KNU substrate EC without deriving rootzone stress metrics."""

    return _read_csv_with_required_columns(
        path,
        required_columns=ROOTZONE_EC_REQUIRED_COLUMNS,
        numeric_columns=("rootzone_ec_dS_m", "depth_cm"),
        table_label="Rootzone EC table",
    )


def _filter_by_validation_window(
    frame: pd.DataFrame,
    *,
    validation_start: pd.Timestamp,
    validation_end: pd.Timestamp,
) -> pd.DataFrame:
    end_exclusive = validation_end.normalize() + pd.Timedelta(days=1)
    return frame.loc[
        frame["datetime"].ge(validation_start.normalize()) & frame["datetime"].lt(end_exclusive)
    ].reset_index(drop=True)


def _time_series_summary(frame: pd.DataFrame | None, *, value_columns: tuple[str, ...]) -> dict[str, object]:
    if frame is None:
        return {"rows": 0, "start": None, "end": None, "sensor_count": 0, "non_null_counts": {}}
    if frame.empty:
        return {"rows": 0, "start": None, "end": None, "sensor_count": 0, "non_null_counts": {}}
    return {
        "rows": int(len(frame)),
        "start": str(frame["datetime"].min()),
        "end": str(frame["datetime"].max()),
        "sensor_count": int(frame["sensor_id"].nunique(dropna=True)) if "sensor_id" in frame.columns else 0,
        "non_null_counts": {
            column: int(frame[column].notna().sum()) for column in value_columns if column in frame.columns
        },
    }


def _normalization_factor(dataset: DatasetMetadataContract) -> float:
    if dataset.basis.reporting_basis == CANONICAL_REPORTING_BASIS:
        return 1.0
    if dataset.basis.reporting_basis == "g_per_plant":
        if dataset.basis.plants_per_m2 is None:
            raise ValueError(
                f"Dataset {dataset.dataset_id!r} declares g_per_plant basis without plants_per_m2."
            )
        return float(to_floor_area_value(1.0, basis="g/plant", plants_per_m2=dataset.basis.plants_per_m2))
    raise ValueError(f"Unsupported reporting basis {dataset.basis.reporting_basis!r}.")


def _canonical_observed_frame(dataset: DatasetMetadataContract) -> tuple[pd.DataFrame, float]:
    if dataset.observed_harvest_path is None:
        raise ValueError(f"Dataset {dataset.dataset_id!r} does not define an observed_harvest_path.")
    observed_table = read_dataset_observation_table(dataset.observed_harvest_path)
    observation = dataset.observation
    required_columns = {
        observation.date_column,
        observation.measured_cumulative_column,
    }
    missing = [column for column in required_columns if column not in observed_table.columns]
    if missing:
        raise ValueError(
            f"Dataset {dataset.dataset_id!r} is missing observation columns required by its contract: {missing}"
        )
    if observation.estimated_cumulative_column and observation.estimated_cumulative_column not in observed_table.columns:
        raise ValueError(
            f"Dataset {dataset.dataset_id!r} is missing estimated column {observation.estimated_cumulative_column!r}."
        )

    factor = _normalization_factor(dataset)
    measured_series = pd.to_numeric(observed_table[observation.measured_cumulative_column], errors="coerce") * factor
    if observation.estimated_cumulative_column is None:
        estimated_series = measured_series.copy()
    else:
        estimated_series = pd.to_numeric(observed_table[observation.estimated_cumulative_column], errors="coerce") * factor

    observed_df = pd.DataFrame(
        {
            "date": pd.to_datetime(observed_table[observation.date_column], errors="coerce").dt.normalize(),
            "measured_cumulative_harvested_fruit_dry_weight_floor_area": measured_series,
            "estimated_cumulative_harvested_fruit_dry_weight_floor_area": estimated_series,
        }
    )
    observed_df = observed_df.dropna(subset=["date"]).sort_values("date").drop_duplicates(
        subset=["date"],
        keep="last",
    )
    validation_start = pd.Timestamp(dataset.validation_start).normalize()
    validation_end = pd.Timestamp(dataset.validation_end).normalize()
    observed_df = observed_df.loc[
        observed_df["date"].ge(validation_start) & observed_df["date"].le(validation_end)
    ].reset_index(drop=True)
    if observed_df.empty:
        raise ValueError(
            f"Dataset {dataset.dataset_id!r} did not retain any observations inside "
            f"{dataset.validation_start}..{dataset.validation_end}."
        )
    observed_df["measured_cumulative_total_fruit_dry_weight_floor_area"] = observed_df[
        "measured_cumulative_harvested_fruit_dry_weight_floor_area"
    ]
    observed_df["estimated_cumulative_total_fruit_dry_weight_floor_area"] = observed_df[
        "estimated_cumulative_harvested_fruit_dry_weight_floor_area"
    ]
    observed_df["measured_daily_increment_floor_area"] = pd.to_numeric(
        observed_df["measured_cumulative_harvested_fruit_dry_weight_floor_area"],
        errors="coerce",
    ).diff()
    observed_df["estimated_daily_increment_floor_area"] = pd.to_numeric(
        observed_df["estimated_cumulative_harvested_fruit_dry_weight_floor_area"],
        errors="coerce",
    ).diff()
    return observed_df, factor


def prepare_measured_harvest_bundle(
    dataset: DatasetMetadataContract,
    *,
    validation_cfg: dict[str, Any],
    prepared_root: Path,
) -> PreparedMeasuredHarvestBundle:
    if not is_measured_harvest_runnable(dataset):
        raise ValueError(
            f"Dataset {dataset.dataset_id!r} is not a runnable measured-harvest dataset."
        )
    prepared_root = ensure_dir(prepared_root)
    resample_rule = str(validation_cfg.get("resample_rule", "1h"))
    theta_mode = str(validation_cfg.get("theta_proxy_mode", "bucket_irrigated"))
    scenario_ids = [str(value) for value in _as_list(validation_cfg.get("theta_proxy_scenarios"))] or list(DEFAULT_SCENARIOS)

    if dataset.forcing_path is None:
        raise ValueError(f"Dataset {dataset.dataset_id!r} does not define a forcing_path.")
    forcing_df = read_knu_forcing_csv(dataset.forcing_path)
    observed_df, normalization_factor = _canonical_observed_frame(dataset)
    validation_start = pd.Timestamp(dataset.validation_start).normalize()
    validation_end = pd.Timestamp(dataset.validation_end).normalize()
    rootzone_path = dataset.management.rootzone_path
    rootzone_ec_path = dataset.management.ec_path
    rootzone_df = (
        _filter_by_validation_window(
            read_rootzone_table(rootzone_path),
            validation_start=validation_start,
            validation_end=validation_end,
        )
        if rootzone_path is not None
        else None
    )
    rootzone_ec_df = (
        _filter_by_validation_window(
            read_rootzone_ec_table(rootzone_ec_path),
            validation_start=validation_start,
            validation_end=validation_end,
        )
        if rootzone_ec_path is not None
        else None
    )
    rootzone_summary = {
        "rootzone_path": str(rootzone_path) if rootzone_path is not None else None,
        "rootzone_ec_path": str(rootzone_ec_path) if rootzone_ec_path is not None else None,
        "rootzone": _time_series_summary(
            rootzone_df,
            value_columns=("theta_substrate", "slab_weight_kg"),
        ),
        "rootzone_ec": _time_series_summary(
            rootzone_ec_df,
            value_columns=("rootzone_ec_dS_m",),
        ),
        "missing_policy": "preserve_missing_no_forward_fill",
        "derived_rootzone_stress_metrics_included": False,
    }
    if validation_cfg.get("calibration_end"):
        calibration_end = pd.Timestamp(validation_cfg["calibration_end"]).normalize()
    else:
        midpoint = len(observed_df) // 2
        calibration_end = pd.Timestamp(observed_df["date"].iloc[max(midpoint - 1, 0)]).normalize()
    holdout_start = calibration_end + pd.Timedelta(days=1)

    prepared_dir = ensure_dir(prepared_root / "prepared_forcing")
    scenarios: dict[str, PreparedDatasetThetaScenario] = {}
    for scenario_id in scenario_ids:
        minute_df = apply_theta_substrate_proxy(forcing_df, mode=theta_mode, scenario=scenario_id)
        hourly_df = resample_forcing(minute_df, freq=resample_rule)
        hourly_path = prepared_dir / f"{dataset.dataset_id}_{theta_mode}_{scenario_id}_{resample_rule.replace('/', '_')}.csv"
        hourly_df.to_csv(hourly_path, index=False)
        scenarios[scenario_id] = PreparedDatasetThetaScenario(
            scenario_id=scenario_id,
            minute_df=minute_df,
            hourly_df=hourly_df,
            forcing_csv_path=hourly_path,
            summary=theta_proxy_summary(minute_df),
        )

    observed_canonical_path = prepared_root / "observed_harvest_canonical.csv"
    observed_df.to_csv(observed_canonical_path, index=False)
    observation_contract_manifest_path = prepared_root / "observation_contract_manifest.json"
    write_json(
        observation_contract_manifest_path,
        {
            "dataset_id": dataset.dataset_id,
            "observation_path": str(dataset.observed_harvest_path),
            "forcing_path": str(dataset.forcing_path),
            "validation_start": dataset.validation_start,
            "validation_end": dataset.validation_end,
            "reporting_basis_in": dataset.basis.reporting_basis,
            "reporting_basis_canonical": CANONICAL_REPORTING_BASIS,
            "basis_normalization_resolved": True,
            "normalization_factor_to_floor_area": normalization_factor,
            "plants_per_m2": float(dataset.basis.plants_per_m2) if dataset.basis.plants_per_m2 is not None else None,
            "date_column": dataset.observation.date_column,
            "measured_cumulative_column": dataset.observation.measured_cumulative_column,
            "estimated_cumulative_column": dataset.observation.estimated_cumulative_column,
            "measured_semantics": dataset.observation.measured_semantics,
            "management": dataset.management.to_payload(),
            "rootzone_measurements": rootzone_summary,
            "sanitized_fixture": dataset.sanitized_fixture.to_payload(),
        },
    )
    return PreparedMeasuredHarvestBundle(
        dataset_id=dataset.dataset_id,
        observed_df=observed_df,
        validation_start=validation_start,
        validation_end=validation_end,
        calibration_end=calibration_end,
        holdout_start=holdout_start,
        prepared_root=prepared_root,
        scenarios=scenarios,
        source_unit_label=dataset.basis.basis_unit_label,
        reporting_basis_in=dataset.basis.reporting_basis,
        reporting_basis_canonical=CANONICAL_REPORTING_BASIS,
        basis_normalization_resolved=True,
        normalization_factor_to_floor_area=normalization_factor,
        manifest_summary={
            "observed_harvest_canonical_csv": str(observed_canonical_path),
            "observation_contract_manifest_json": str(observation_contract_manifest_path),
            "rootzone_measurements": rootzone_summary,
        },
        rootzone_df=rootzone_df,
        rootzone_ec_df=rootzone_ec_df,
        rootzone_path=rootzone_path,
        rootzone_ec_path=rootzone_ec_path,
        rootzone_summary=rootzone_summary,
    )


__all__ = [
    "CANONICAL_REPORTING_BASIS",
    "PreparedDatasetThetaScenario",
    "PreparedMeasuredHarvestBundle",
    "prepare_measured_harvest_bundle",
    "read_dataset_observation_table",
    "read_rootzone_ec_table",
    "read_rootzone_table",
]
