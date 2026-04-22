#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = PROJECT_ROOT / "data" / "fixtures" / "knu_rootzone_sanitized"
RAW_ROOTZONE_NAME = "KNU_Tomato_Rootzone_fixture.csv"
RAW_EC_NAME = "KNU_Tomato_Rootzone_EC_fixture.csv"
ALIGNED_ROOTZONE_NAME = "KNU_Tomato_Rootzone_aligned_fixture.csv"
ALIGNED_EC_NAME = "KNU_Tomato_Rootzone_EC_aligned_fixture.csv"
ALIGNED_MANIFEST_NAME = "knu_rootzone_aligned_fixture_manifest.json"
ALIGNED_PROVENANCE_NAME = "knu_rootzone_aligned_provenance.md"

COL_SEASON_LABEL = "\uc0dd\uc721\uc870\uc0ac \ud56d\ubaa9"
COL_SEASON_START = "\uc791\uae30 \uc2dc\uc791"
COL_SEASON_END = "\uc791\uae30 \uc885\ub8cc"
COL_CONTROL = "Control"
COL_DROUGHT = "Drought"
COMMON_METADATA_TOKEN = "\uacf5\ud1b5"


@dataclass(frozen=True, slots=True)
class SeasonWindow:
    season_id: str
    label: str
    start: pd.Timestamp
    end: pd.Timestamp
    treatment_map: dict[str, str]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build metadata-window-aligned KNU rootzone fixtures with mean-imputed gaps."
    )
    parser.add_argument(
        "--raw-root",
        required=True,
        help="Raw tomato workspace containing 40_* metadata and configs/loadcell_seasons.json.",
    )
    parser.add_argument(
        "--fixture-root",
        default=str(FIXTURE_ROOT),
        help="Directory containing raw sanitized rootzone/EC fixtures and receiving aligned outputs.",
    )
    return parser.parse_args()


def _find_common_metadata(raw_root: Path) -> Path:
    candidates = [
        path
        for path in raw_root.glob("40_*/*.xlsx")
        if COMMON_METADATA_TOKEN in path.name and not path.name.startswith("~$")
    ]
    if len(candidates) != 1:
        raise FileNotFoundError(
            f"Expected exactly one common metadata workbook under {raw_root}, found {len(candidates)}"
        )
    return candidates[0]


def _end_of_day(value: Any) -> pd.Timestamp:
    return pd.Timestamp(value).normalize() + pd.Timedelta(hours=23)


def _load_metadata_windows(raw_root: Path) -> tuple[list[SeasonWindow], dict[str, Any]]:
    metadata_path = _find_common_metadata(raw_root)
    metadata = pd.read_excel(metadata_path).dropna(axis=0, how="all")
    labels = metadata[COL_SEASON_LABEL].astype(str).str.strip()

    def row_for(label: str) -> pd.Series:
        matches = metadata.loc[labels == label]
        if matches.empty:
            raise KeyError(f"Missing metadata row: {label}")
        return matches.iloc[0]

    row_2024 = row_for("2024\ub144 \uc791\uae30")
    row_2025_1 = row_for("2025\ub144 1\uc791\uae30")
    row_2025_2 = row_for("2025\ub144 2\uc791\uae30")

    windows = [
        SeasonWindow(
            season_id="2024",
            label=str(row_2024[COL_SEASON_LABEL]),
            start=pd.Timestamp(row_2024[COL_SEASON_START]).normalize(),
            end=_end_of_day(row_2024[COL_SEASON_END]),
            treatment_map={"RZ00": "Control"},
        ),
        SeasonWindow(
            season_id="2025_1",
            label=str(row_2025_1[COL_SEASON_LABEL]),
            start=pd.Timestamp(row_2025_1[COL_SEASON_START]).normalize(),
            end=_end_of_day(row_2025_1[COL_SEASON_END]),
            treatment_map={
                "RZ01": "Control",
                "RZ02": "Control",
                "RZ03": "Control",
                "RZ04": "Drought",
                "RZ05": "Drought",
                "RZ06": "Drought",
            },
        ),
        SeasonWindow(
            season_id="2025_2",
            label=str(row_2025_2[COL_SEASON_LABEL]),
            start=pd.Timestamp(row_2025_2[COL_SEASON_START]).normalize(),
            end=_end_of_day(row_2025_2[COL_SEASON_END]),
            treatment_map={
                "RZ01": "Control",
                "RZ02": "Control",
                "RZ03": "Control",
                "RZ04": "Drought",
                "RZ05": "Drought",
                "RZ06": "Drought",
            },
        ),
    ]

    metadata_payload = {
        "metadata_path": str(metadata_path),
        "season_workbook_rows": {
            "2024": {
                "label": str(row_2024[COL_SEASON_LABEL]),
                "start": pd.Timestamp(row_2024[COL_SEASON_START]).strftime("%Y-%m-%d"),
                "end": pd.Timestamp(row_2024[COL_SEASON_END]).strftime("%Y-%m-%d"),
                "control": str(row_2024.get(COL_CONTROL, "")),
                "drought": str(row_2024.get(COL_DROUGHT, "")),
            },
            "2025_1": {
                "label": str(row_2025_1[COL_SEASON_LABEL]),
                "start": pd.Timestamp(row_2025_1[COL_SEASON_START]).strftime("%Y-%m-%d"),
                "end": pd.Timestamp(row_2025_1[COL_SEASON_END]).strftime("%Y-%m-%d"),
                "control": str(row_2025_1.get(COL_CONTROL, "")),
                "drought": str(row_2025_1.get(COL_DROUGHT, "")),
            },
            "2025_2": {
                "label": str(row_2025_2[COL_SEASON_LABEL]),
                "start": pd.Timestamp(row_2025_2[COL_SEASON_START]).strftime("%Y-%m-%d"),
                "end": pd.Timestamp(row_2025_2[COL_SEASON_END]).strftime("%Y-%m-%d"),
                "control": str(row_2025_2.get(COL_CONTROL, "")),
                "drought": str(row_2025_2.get(COL_DROUGHT, "")),
            },
        },
    }
    return windows, metadata_payload


def _read_fixture(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["datetime"] = pd.to_datetime(frame["datetime"], errors="coerce")
    frame = frame.loc[frame["datetime"].notna()].copy()
    return frame


def _format_datetime(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["datetime"] = pd.to_datetime(frame["datetime"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    return frame


def _aggregate_sensor_rows(frame: pd.DataFrame, value_columns: list[str]) -> pd.DataFrame:
    aggregations = {column: "mean" for column in value_columns}
    aggregations.update({"zone_id": "last", "depth_cm": "last"})
    return (
        frame.groupby(["datetime", "sensor_id"], as_index=False)
        .agg(aggregations)
        .sort_values(["datetime", "sensor_id"])
    )


def _align_sensor_values(
    source: pd.DataFrame,
    *,
    season: SeasonWindow,
    sensor_id: str,
    value_columns: list[str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    hourly_index = pd.date_range(season.start, season.end, freq="1h", name="datetime")
    sensor_source = source.loc[
        (source["sensor_id"] == sensor_id)
        & (source["datetime"] >= season.start)
        & (source["datetime"] <= season.end)
    ].copy()
    sensor_source = _aggregate_sensor_rows(sensor_source, value_columns)
    indexed = sensor_source.set_index("datetime").reindex(hourly_index)

    zone_id = sensor_source["zone_id"].dropna().iloc[0] if sensor_source["zone_id"].notna().any() else sensor_id
    depth_cm = sensor_source["depth_cm"].dropna().iloc[0] if sensor_source["depth_cm"].notna().any() else pd.NA

    aligned = pd.DataFrame(
        {
            "datetime": hourly_index,
            "season_id": season.season_id,
            "season_label": season.label,
            "treatment": season.treatment_map[sensor_id],
            "sensor_id": sensor_id,
            "zone_id": zone_id,
            "depth_cm": depth_cm,
            "metadata_window_start": season.start.strftime("%Y-%m-%d %H:%M:%S"),
            "metadata_window_end": season.end.strftime("%Y-%m-%d %H:%M:%S"),
        }
    )

    stats: dict[str, Any] = {
        "season_id": season.season_id,
        "sensor_id": sensor_id,
        "treatment": season.treatment_map[sensor_id],
        "row_count": int(len(aligned)),
        "source_start": None,
        "source_end": None,
        "columns": {},
    }
    if not sensor_source.empty:
        stats["source_start"] = sensor_source["datetime"].min().strftime("%Y-%m-%d %H:%M:%S")
        stats["source_end"] = sensor_source["datetime"].max().strftime("%Y-%m-%d %H:%M:%S")

    for column in value_columns:
        values = pd.to_numeric(indexed[column], errors="coerce")
        observed_mask = values.notna()
        mean_value = values.mean()
        filled_values = values.copy()
        fillable_mask = values.isna() & pd.notna(mean_value)
        filled_values.loc[fillable_mask] = mean_value

        aligned[column] = filled_values.to_numpy()
        aligned[f"{column}_source"] = "measured"
        aligned.loc[fillable_mask.to_numpy(), f"{column}_source"] = "imputed_period_mean"
        aligned.loc[
            (values.isna() & pd.isna(mean_value)).to_numpy(),
            f"{column}_source",
        ] = "missing_no_period_mean"
        aligned[f"{column}_is_imputed"] = fillable_mask.to_numpy()

        stats["columns"][column] = {
            "observed_count": int(observed_mask.sum()),
            "imputed_count": int(fillable_mask.sum()),
            "missing_after_count": int(aligned[column].isna().sum()),
            "period_mean": None if pd.isna(mean_value) else float(mean_value),
        }

    return aligned, stats


def _align_fixture(
    source: pd.DataFrame,
    *,
    windows: list[SeasonWindow],
    value_columns: list[str],
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    frames: list[pd.DataFrame] = []
    stats: list[dict[str, Any]] = []
    for season in windows:
        for sensor_id in season.treatment_map:
            aligned, sensor_stats = _align_sensor_values(
                source,
                season=season,
                sensor_id=sensor_id,
                value_columns=value_columns,
            )
            frames.append(aligned)
            stats.append(sensor_stats)
    return pd.concat(frames, ignore_index=True), stats


def _reorder_rootzone(frame: pd.DataFrame) -> pd.DataFrame:
    ordered = [
        "datetime",
        "season_id",
        "season_label",
        "treatment",
        "theta_substrate",
        "theta_substrate_source",
        "theta_substrate_is_imputed",
        "slab_weight_kg",
        "slab_weight_kg_source",
        "slab_weight_kg_is_imputed",
        "sensor_id",
        "zone_id",
        "depth_cm",
        "metadata_window_start",
        "metadata_window_end",
    ]
    return _format_datetime(frame[ordered])


def _reorder_ec(frame: pd.DataFrame) -> pd.DataFrame:
    ordered = [
        "datetime",
        "season_id",
        "season_label",
        "treatment",
        "rootzone_ec_dS_m",
        "rootzone_ec_dS_m_source",
        "rootzone_ec_dS_m_is_imputed",
        "sensor_id",
        "zone_id",
        "depth_cm",
        "metadata_window_start",
        "metadata_window_end",
    ]
    return _format_datetime(frame[ordered])


def _summarize_frame(frame: pd.DataFrame, value_columns: list[str]) -> dict[str, Any]:
    dt = pd.to_datetime(frame["datetime"], errors="coerce")
    summary: dict[str, Any] = {
        "row_count": int(len(frame)),
        "start": dt.min().strftime("%Y-%m-%d %H:%M:%S"),
        "end": dt.max().strftime("%Y-%m-%d %H:%M:%S"),
        "season_count": int(frame["season_id"].nunique()),
        "sensor_count": int(frame["sensor_id"].nunique()),
        "by_season": {},
        "columns": {},
    }
    for season_id, season_frame in frame.groupby("season_id"):
        summary["by_season"][season_id] = {
            "row_count": int(len(season_frame)),
            "sensor_count": int(season_frame["sensor_id"].nunique()),
            "start": pd.to_datetime(season_frame["datetime"]).min().strftime("%Y-%m-%d %H:%M:%S"),
            "end": pd.to_datetime(season_frame["datetime"]).max().strftime("%Y-%m-%d %H:%M:%S"),
        }
    for column in value_columns:
        source_col = f"{column}_source"
        summary["columns"][column] = {
            "missing_after_count": int(frame[column].isna().sum()),
            "source_counts": {
                str(key): int(value)
                for key, value in frame[source_col].value_counts(dropna=False).sort_index().items()
            },
        }
    return summary


def _write_manifest(
    *,
    fixture_root: Path,
    metadata_payload: dict[str, Any],
    rootzone_frame: pd.DataFrame,
    ec_frame: pd.DataFrame,
    rootzone_stats: list[dict[str, Any]],
    ec_stats: list[dict[str, Any]],
) -> None:
    payload = {
        "dataset_id": "knu_actual",
        "fixture_kind": "knu_rootzone_aligned_mean_imputed",
        "timezone": "Asia/Seoul",
        "rootzone_path": f"data/fixtures/knu_rootzone_sanitized/{ALIGNED_ROOTZONE_NAME}",
        "ec_path": f"data/fixtures/knu_rootzone_sanitized/{ALIGNED_EC_NAME}",
        "raw_sanitized_rootzone_path": f"data/fixtures/knu_rootzone_sanitized/{RAW_ROOTZONE_NAME}",
        "raw_sanitized_ec_path": f"data/fixtures/knu_rootzone_sanitized/{RAW_EC_NAME}",
        "provenance_path": f"data/fixtures/knu_rootzone_sanitized/{ALIGNED_PROVENANCE_NAME}",
        "units": {
            "theta_substrate": "fraction",
            "slab_weight_kg": "kg",
            "rootzone_ec_dS_m": "dS/m",
            "depth_cm": "cm",
        },
        "metadata_source": metadata_payload,
        "alignment_rule": "hourly grid from metadata transplant/season start through metadata season end",
        "missing_policy": (
            "for each season_id and sensor_id, fill missing measured value with the whole-period "
            "mean of available values for the same column; preserve per-value source and is_imputed labels"
        ),
        "treatment_mapping": {
            "2024": {"RZ00": "Control"},
            "2025_1": {
                "RZ01": "Control",
                "RZ02": "Control",
                "RZ03": "Control",
                "RZ04": "Drought",
                "RZ05": "Drought",
                "RZ06": "Drought",
            },
            "2025_2": {
                "RZ01": "Control",
                "RZ02": "Control",
                "RZ03": "Control",
                "RZ04": "Drought",
                "RZ05": "Drought",
                "RZ06": "Drought",
            },
            "harvest_individual_mapping_note": "2025 harvest sheets use 1-9 Control and 10-18 Drought; rootzone loadcell channels available in the current fixture are 1-6.",
        },
        "harvest_availability_note": {
            "2025_1": "summer season harvest workbook is not present yet; rootzone fixture is prepared for later harvest intake",
            "2025_2": "winter harvest workbook exists and was handled in school_knu__yield fixtures",
        },
        "rootzone_summary": _summarize_frame(rootzone_frame, ["theta_substrate", "slab_weight_kg"]),
        "ec_summary": _summarize_frame(ec_frame, ["rootzone_ec_dS_m"]),
        "rootzone_sensor_stats": rootzone_stats,
        "ec_sensor_stats": ec_stats,
        "notes": {
            "raw_fixture_policy": "raw sanitized fixtures are kept unchanged; aligned fixtures are the completed mean-imputed analysis inputs",
            "not_included": [
                "irrigation_event_flag",
                "rootzone_multistress",
                "rootzone_saturation",
                "derived stress scores",
            ],
        },
    }
    (fixture_root / ALIGNED_MANIFEST_NAME).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_provenance(fixture_root: Path, metadata_payload: dict[str, Any]) -> None:
    rows = metadata_payload["season_workbook_rows"]
    text = "\n".join(
        [
            "# KNU rootzone aligned fixture provenance",
            "",
            "- dataset_id: knu_actual",
            "- fixture_kind: knu_rootzone_aligned_mean_imputed",
            f"- source_metadata: {metadata_payload['metadata_path']}",
            f"- raw_rootzone_fixture: data/fixtures/knu_rootzone_sanitized/{RAW_ROOTZONE_NAME}",
            f"- raw_ec_fixture: data/fixtures/knu_rootzone_sanitized/{RAW_EC_NAME}",
            f"- aligned_rootzone_fixture: data/fixtures/knu_rootzone_sanitized/{ALIGNED_ROOTZONE_NAME}",
            f"- aligned_ec_fixture: data/fixtures/knu_rootzone_sanitized/{ALIGNED_EC_NAME}",
            "- alignment_rule: use metadata season start/end columns; expand each season/sensor to hourly timestamps.",
            "- missing_policy: fill missing loadcell/rootzone values with the season+sensor whole-period mean and label the filled cells.",
            "- 2024_window: "
            + f"{rows['2024']['start']} -> {rows['2024']['end']} ({rows['2024']['label']})",
            "- 2025_1_window: "
            + f"{rows['2025_1']['start']} -> {rows['2025_1']['end']} ({rows['2025_1']['label']})",
            "- 2025_2_window: "
            + f"{rows['2025_2']['start']} -> {rows['2025_2']['end']} ({rows['2025_2']['label']})",
            "- 2025_rootzone_treatment_map: Control=RZ01,RZ02,RZ03; Drought=RZ04,RZ05,RZ06.",
            "- 2025_harvest_individual_map: Control=individual sheets 1-9; Drought=individual sheets 10-18.",
            "- 2025_1_harvest_status: pending; summer harvest raw workbook is not in the current raw workspace yet.",
            "- 2025_2_harvest_status: available; handled by school_knu__yield fixture generation.",
            "",
        ]
    )
    (fixture_root / ALIGNED_PROVENANCE_NAME).write_text(text, encoding="utf-8")


def main() -> int:
    args = _parse_args()
    raw_root = Path(args.raw_root).expanduser().resolve()
    fixture_root = Path(args.fixture_root).expanduser().resolve()
    fixture_root.mkdir(parents=True, exist_ok=True)

    windows, metadata_payload = _load_metadata_windows(raw_root)
    rootzone_source = _read_fixture(fixture_root / RAW_ROOTZONE_NAME)
    ec_source = _read_fixture(fixture_root / RAW_EC_NAME)

    rootzone_aligned, rootzone_stats = _align_fixture(
        rootzone_source,
        windows=windows,
        value_columns=["theta_substrate", "slab_weight_kg"],
    )
    ec_aligned, ec_stats = _align_fixture(
        ec_source,
        windows=windows,
        value_columns=["rootzone_ec_dS_m"],
    )

    rootzone_aligned = _reorder_rootzone(rootzone_aligned)
    ec_aligned = _reorder_ec(ec_aligned)

    rootzone_aligned.to_csv(fixture_root / ALIGNED_ROOTZONE_NAME, index=False, encoding="utf-8", na_rep="")
    ec_aligned.to_csv(fixture_root / ALIGNED_EC_NAME, index=False, encoding="utf-8", na_rep="")
    _write_manifest(
        fixture_root=fixture_root,
        metadata_payload=metadata_payload,
        rootzone_frame=rootzone_aligned,
        ec_frame=ec_aligned,
        rootzone_stats=rootzone_stats,
        ec_stats=ec_stats,
    )
    _write_provenance(fixture_root, metadata_payload)

    print(
        json.dumps(
            {
                "rootzone_path": str(fixture_root / ALIGNED_ROOTZONE_NAME),
                "ec_path": str(fixture_root / ALIGNED_EC_NAME),
                "manifest_path": str(fixture_root / ALIGNED_MANIFEST_NAME),
                "provenance_path": str(fixture_root / ALIGNED_PROVENANCE_NAME),
                "rootzone_summary": _summarize_frame(
                    rootzone_aligned, ["theta_substrate", "slab_weight_kg"]
                ),
                "ec_summary": _summarize_frame(ec_aligned, ["rootzone_ec_dS_m"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
