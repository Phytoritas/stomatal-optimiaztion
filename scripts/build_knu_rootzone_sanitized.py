#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = PROJECT_ROOT / "data" / "fixtures" / "knu_rootzone_sanitized"
DEFAULT_MANIFEST_PATH = FIXTURE_ROOT / "knu_rootzone_fixture_manifest.json"
DEFAULT_ROOTZONE_PATH = FIXTURE_ROOT / "KNU_Tomato_Rootzone_fixture.csv"
DEFAULT_EC_PATH = FIXTURE_ROOT / "KNU_Tomato_Rootzone_EC_fixture.csv"


@dataclass(frozen=True, slots=True)
class SeasonWindow:
    season_id: str
    start: pd.Timestamp
    end: pd.Timestamp


SEASON_WINDOWS: tuple[SeasonWindow, ...] = (
    SeasonWindow("2024", pd.Timestamp("2024-06-13 00:00:00"), pd.Timestamp("2024-12-18 23:59:59")),
    SeasonWindow("2025_1", pd.Timestamp("2025-06-04 00:00:00"), pd.Timestamp("2025-09-03 23:59:59")),
    SeasonWindow("2025_2", pd.Timestamp("2025-10-22 00:00:00"), pd.Timestamp("2026-02-21 23:59:59")),
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build sanitized KNU rootzone and EC fixtures.")
    parser.add_argument(
        "--raw-root",
        required=True,
        help="Path to the raw tomato workspace that contains outputs/loadcell and 2024 CR1000X sources.",
    )
    parser.add_argument(
        "--output-root",
        default=str(FIXTURE_ROOT),
        help="Output directory for sanitized fixtures.",
    )
    return parser.parse_args()


def _format_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")


def _sensor_id(index: int) -> str:
    return f"RZ{index:02d}"


def _zone_id(index: int) -> str:
    return f"BED{index:02d}"


def _combine_excel_datetime(date_series: pd.Series, time_series: pd.Series) -> pd.Series:
    date_text = pd.to_datetime(date_series, errors="coerce").dt.strftime("%Y-%m-%d")
    time_text = (
        time_series.astype(str)
        .str.extract(r"(\d{2}:\d{2}:\d{2})", expand=False)
        .where(lambda value: value.str.fullmatch(r"\d{2}:\d{2}:\d{2}"), None)
    )
    return pd.to_datetime(date_text + " " + time_text, errors="coerce")


def _iter_2024_cr1000x_files(raw_root: Path) -> list[Path]:
    env_root = next(
        (path for path in raw_root.iterdir() if path.is_dir() and path.name.startswith("30_")),
        None,
    )
    if env_root is None:
        raise FileNotFoundError(f"Could not locate 30_* environment root under {raw_root}")
    files = [path for path in env_root.rglob("*.xlsx") if "CR1000X" in path.as_posix()]
    if not files:
        raise FileNotFoundError(f"Could not locate 2024 CR1000X workbook bundle under {env_root}")
    return sorted(files)


def _parse_2024_frames(raw_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    rootzone_frames: list[pd.DataFrame] = []
    ec_frames: list[pd.DataFrame] = []
    window = next(season for season in SEASON_WINDOWS if season.season_id == "2024")
    for workbook in _iter_2024_cr1000x_files(raw_root):
        raw_df = pd.read_excel(workbook, sheet_name="hourly", header=None, skiprows=4, usecols=[0, 1, 4, 5])
        raw_df.columns = ["date", "time", "theta_substrate", "rootzone_ec_dS_m"]
        raw_df["datetime"] = _combine_excel_datetime(raw_df["date"], raw_df["time"])
        raw_df = raw_df.dropna(subset=["datetime"]).copy()
        raw_df = raw_df[(raw_df["datetime"] >= window.start) & (raw_df["datetime"] <= window.end)].copy()
        if raw_df.empty:
            continue

        base = pd.DataFrame(
            {
                "datetime": raw_df["datetime"],
                "sensor_id": "RZ00",
                "zone_id": "BED00",
                "depth_cm": pd.NA,
            }
        )

        theta_frame = base.copy()
        theta_values = pd.to_numeric(raw_df["theta_substrate"], errors="coerce")
        theta_frame["theta_substrate"] = theta_values.where((theta_values >= 0.0) & (theta_values <= 2.0))
        theta_frame["slab_weight_kg"] = pd.NA
        theta_frame = theta_frame.loc[
            theta_frame["theta_substrate"].notna() | theta_frame["slab_weight_kg"].notna()
        ].copy()
        if not theta_frame.empty:
            rootzone_frames.append(theta_frame)

        ec_frame = base.copy()
        ec_frame["rootzone_ec_dS_m"] = pd.to_numeric(raw_df["rootzone_ec_dS_m"], errors="coerce")
        ec_frame = ec_frame.loc[ec_frame["rootzone_ec_dS_m"].notna()].copy()
        if not ec_frame.empty:
            ec_frames.append(ec_frame)

    if not rootzone_frames:
        raise ValueError("No 2024 rootzone records were parsed from CR1000X hourly sheets.")
    return pd.concat(rootzone_frames, ignore_index=True), pd.concat(ec_frames, ignore_index=True)


def _select_2025_parquet_files(raw_root: Path, season: SeasonWindow) -> list[Path]:
    loadcell_root = raw_root / "outputs" / "loadcell"
    if not loadcell_root.exists():
        raise FileNotFoundError(f"Could not locate loadcell outputs at {loadcell_root}")

    selected: list[Path] = []
    for directory in sorted(path for path in loadcell_root.iterdir() if path.is_dir()):
        for parquet_path in sorted(directory.glob("*.parquet")):
            try:
                file_day = pd.Timestamp(parquet_path.stem)
            except ValueError:
                continue
            if season.start.normalize() <= file_day.normalize() <= season.end.normalize():
                selected.append(parquet_path)
    return selected


def _hourly_mean_frame(path: Path, *, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    if not isinstance(frame.index, pd.DatetimeIndex):
        frame.index = pd.to_datetime(frame.index, errors="coerce")
    frame = frame.loc[frame.index.notna()].sort_index()
    frame = frame[(frame.index >= start) & (frame.index <= end)]
    if frame.empty:
        return frame
    return frame.resample("1h").mean(numeric_only=True)


def _parse_2025_frames(raw_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    rootzone_frames: list[pd.DataFrame] = []
    ec_frames: list[pd.DataFrame] = []
    for season in SEASON_WINDOWS:
        if not season.season_id.startswith("2025"):
            continue
        parquet_files = _select_2025_parquet_files(raw_root, season)
        for parquet_path in parquet_files:
            hourly = _hourly_mean_frame(parquet_path, start=season.start, end=season.end)
            if hourly.empty:
                continue
            hourly = hourly.reset_index(names="datetime")
            for sensor_index in range(1, 7):
                theta_col = f"moisture_{sensor_index}_percent"
                weight_col = f"loadcell_{sensor_index}_kg"
                ec_col = f"ec_{sensor_index}_ds"
                meta = {
                    "sensor_id": _sensor_id(sensor_index),
                    "zone_id": _zone_id(sensor_index),
                    "depth_cm": pd.NA,
                }
                theta_frame = pd.DataFrame(
                    {
                        "datetime": hourly["datetime"],
                        "theta_substrate": pd.to_numeric(hourly.get(theta_col), errors="coerce") / 100.0,
                        "slab_weight_kg": pd.to_numeric(hourly.get(weight_col), errors="coerce"),
                        **meta,
                    }
                )
                theta_frame = theta_frame.loc[
                    theta_frame["theta_substrate"].notna() | theta_frame["slab_weight_kg"].notna()
                ].copy()
                if not theta_frame.empty:
                    rootzone_frames.append(theta_frame)

                ec_frame = pd.DataFrame(
                    {
                        "datetime": hourly["datetime"],
                        "rootzone_ec_dS_m": pd.to_numeric(hourly.get(ec_col), errors="coerce"),
                        **meta,
                    }
                )
                ec_frame = ec_frame.loc[ec_frame["rootzone_ec_dS_m"].notna()].copy()
                if not ec_frame.empty:
                    ec_frames.append(ec_frame)

    if not rootzone_frames:
        raise ValueError("No 2025 rootzone records were parsed from loadcell parquet outputs.")
    return pd.concat(rootzone_frames, ignore_index=True), pd.concat(ec_frames, ignore_index=True)


def _finalize_rootzone_frame(frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    frame = pd.concat(list(frames), ignore_index=True)
    frame = frame.sort_values(["datetime", "sensor_id"]).reset_index(drop=True)
    frame["datetime"] = _format_datetime(frame["datetime"])
    ordered = ["datetime", "theta_substrate", "slab_weight_kg", "sensor_id", "zone_id", "depth_cm"]
    return frame[ordered]


def _finalize_ec_frame(frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    frame = pd.concat(list(frames), ignore_index=True)
    frame = frame.sort_values(["datetime", "sensor_id"]).reset_index(drop=True)
    frame["datetime"] = _format_datetime(frame["datetime"])
    ordered = ["datetime", "rootzone_ec_dS_m", "sensor_id", "zone_id", "depth_cm"]
    return frame[ordered]


def _frame_coverage(frame: pd.DataFrame) -> dict[str, object]:
    if frame.empty:
        return {"row_count": 0, "start": None, "end": None, "sensor_count": 0}
    dt = pd.to_datetime(frame["datetime"], errors="coerce")
    return {
        "row_count": int(len(frame)),
        "start": dt.min().strftime("%Y-%m-%d %H:%M:%S"),
        "end": dt.max().strftime("%Y-%m-%d %H:%M:%S"),
        "sensor_count": int(frame["sensor_id"].nunique()),
    }


def _season_windows_payload() -> dict[str, dict[str, str]]:
    return {
        season.season_id: {
            "start": season.start.strftime("%Y-%m-%d %H:%M:%S"),
            "end": season.end.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for season in SEASON_WINDOWS
    }


def _theta_range(frame: pd.DataFrame) -> dict[str, float | None]:
    series = pd.to_numeric(frame["theta_substrate"], errors="coerce").dropna()
    if series.empty:
        return {"min": None, "max": None}
    return {"min": float(series.min()), "max": float(series.max())}


def _write_manifest(
    *,
    output_root: Path,
    rootzone_frame: pd.DataFrame,
    ec_frame: pd.DataFrame,
    raw_root: Path,
) -> Path:
    payload = {
        "dataset_id": "knu_actual",
        "fixture_kind": "knu_rootzone_sanitized",
        "timezone": "Asia/Seoul",
        "rootzone_path": "data/fixtures/knu_rootzone_sanitized/KNU_Tomato_Rootzone_fixture.csv",
        "ec_path": "data/fixtures/knu_rootzone_sanitized/KNU_Tomato_Rootzone_EC_fixture.csv",
        "irrigation_path": None,
        "units": {
            "theta_substrate": "fraction",
            "slab_weight_kg": "kg",
            "rootzone_ec_dS_m": "dS/m",
            "depth_cm": "cm",
        },
        "sensor_layout": "representative probe layout for KNU tomato greenhouse",
        "aggregation_rule": "one row per timestamp per sensor",
        "missing_policy": "keep missing as blank; do not forward-fill in raw sanitized fixture",
        "source_refs": [
            "2024 CR1000X hourly substrate workbook bundle under the raw tomato workspace 30_* environment tree",
            "outputs/loadcell/*/*.parquet within 2025 season windows",
        ],
        "notes": {
            "contains_irrigation_events": False,
            "includes_only_measured_values": True,
            "derived_rootzone_stress_metrics_are_excluded": True,
            "season_windows": _season_windows_payload(),
            "rootzone_coverage": _frame_coverage(rootzone_frame),
            "ec_coverage": _frame_coverage(ec_frame),
            "theta_range": _theta_range(rootzone_frame),
            "theta_substrate_semantics": (
                "2024 values come from CR1000X VWC_Avg. 2025 values come from moisture_i_percent / 100 without clipping."
            ),
            "theta_cleanup_note": "2024 CR1000X VWC_Avg values outside 0-2 were treated as logger sentinel missing values and left blank.",
            "slab_weight_note": "2024 CR1000X source has no slab_weight_kg field; rows remain blank for that column.",
            "depth_note": "depth_cm metadata is unavailable in the current raw source and is preserved as blank.",
        },
    }
    manifest_path = output_root / DEFAULT_MANIFEST_PATH.name
    manifest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return manifest_path


def _ensure_output_root(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, encoding="utf-8", na_rep="")


def main() -> int:
    args = _parse_args()
    raw_root = Path(args.raw_root).expanduser().resolve()
    output_root = _ensure_output_root(Path(args.output_root).expanduser().resolve())
    if not raw_root.exists():
        raise FileNotFoundError(f"Raw root does not exist: {raw_root}")

    rootzone_2024, ec_2024 = _parse_2024_frames(raw_root)
    rootzone_2025, ec_2025 = _parse_2025_frames(raw_root)
    rootzone_frame = _finalize_rootzone_frame([rootzone_2024, rootzone_2025])
    ec_frame = _finalize_ec_frame([ec_2024, ec_2025])

    rootzone_path = output_root / DEFAULT_ROOTZONE_PATH.name
    ec_path = output_root / DEFAULT_EC_PATH.name
    _write_csv(rootzone_frame, rootzone_path)
    _write_csv(ec_frame, ec_path)
    manifest_path = _write_manifest(
        output_root=output_root,
        rootzone_frame=rootzone_frame,
        ec_frame=ec_frame,
        raw_root=raw_root,
    )

    summary = {
        "rootzone_path": str(rootzone_path),
        "ec_path": str(ec_path),
        "manifest_path": str(manifest_path),
        "rootzone_row_count": int(len(rootzone_frame)),
        "ec_row_count": int(len(ec_frame)),
        "theta_min": _theta_range(rootzone_frame)["min"],
        "theta_max": _theta_range(rootzone_frame)["max"],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
