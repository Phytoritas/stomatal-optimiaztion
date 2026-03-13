"""ALMEMO 500 raw CSV preprocessing."""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path

import numpy as np
import pandas as pd

CANONICAL_COLUMNS: list[str] = [
    "loadcell_1_kg",
    "loadcell_2_kg",
    "loadcell_3_kg",
    "loadcell_4_kg",
    "loadcell_5_kg",
    "loadcell_6_kg",
    "air_temp_c",
    "air_rh_percent",
    "dewpoint_c",
    "air_pressure_mb",
    "ec_1_ds",
    "moisture_1_percent",
    "ec_2_ds",
    "moisture_2_percent",
    "ec_3_ds",
    "moisture_3_percent",
    "ec_4_ds",
    "moisture_4_percent",
    "ec_5_ds",
    "moisture_5_percent",
    "ec_6_ds",
    "moisture_6_percent",
    "weather_temp_c",
    "wind_speed_m_s",
    "weather_pressure_mb",
    "tensiometer_4_hp",
    "tensiometer_5_hp",
]

RAW_PREFIX_BY_CANONICAL: dict[str, str] = {
    "loadcell_1_kg": "M000.0",
    "loadcell_2_kg": "M001.0",
    "loadcell_3_kg": "M002.0",
    "loadcell_4_kg": "M003.0",
    "loadcell_5_kg": "M004.0",
    "loadcell_6_kg": "M005.0",
    "air_temp_c": "M006.0",
    "air_rh_percent": "M006.1",
    "dewpoint_c": "M006.2",
    "air_pressure_mb": "M006.3",
    "ec_1_ds": "M010.0",
    "moisture_1_percent": "M010.1",
    "ec_2_ds": "M011.0",
    "moisture_2_percent": "M011.1",
    "ec_3_ds": "M012.0",
    "moisture_3_percent": "M012.1",
    "ec_4_ds": "M013.0",
    "moisture_4_percent": "M013.1",
    "ec_5_ds": "M014.0",
    "moisture_5_percent": "M014.1",
    "ec_6_ds": "M015.0",
    "moisture_6_percent": "M015.1",
    "weather_temp_c": "M016.0",
    "wind_speed_m_s": "M016.1",
    "weather_pressure_mb": "M016.2",
    "tensiometer_4_hp": "M017.0",
    "tensiometer_5_hp": "M018.0",
}


def _infer_max_decimals_from_raw_strings(series: pd.Series) -> int:
    """Infer the maximum number of decimal places used in raw string values."""

    if series.empty:
        return 0

    max_decimals = 0
    for value in series.astype(str):
        text = value.strip()
        if not text or text.lower() == "nan" or "." not in text:
            continue
        decimal_part = text.split(".", 1)[1]
        match = re.match(r"(\d+)", decimal_part)
        if not match:
            continue
        max_decimals = max(max_decimals, len(match.group(1)))
    return int(max_decimals)


def _update_precision_map_from_raw(
    df_raw: pd.DataFrame,
    precision_map: dict[str, int],
) -> None:
    """Update per-column decimal precision from a raw ALMEMO frame."""

    columns = [str(column) for column in df_raw.columns]
    for canonical, prefix in RAW_PREFIX_BY_CANONICAL.items():
        raw_col = _match_col(columns, prefix)
        if raw_col is None or raw_col not in df_raw.columns:
            continue
        precision_map[canonical] = max(
            int(precision_map.get(canonical, 0)),
            _infer_max_decimals_from_raw_strings(df_raw[raw_col]),
        )


def _format_float_value(value: float, decimals: int) -> str:
    if pd.isna(value):
        return ""
    number = float(value)
    if decimals <= 0:
        text = f"{number:.0f}"
    else:
        text = f"{number:.{decimals}f}".rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


def format_df_with_precision(df: pd.DataFrame, precision_map: dict[str, int]) -> pd.DataFrame:
    """Format numeric columns as strings using raw-data precision."""

    if df.empty:
        return df

    formatted = df.copy()
    for column in formatted.columns:
        if column not in precision_map:
            continue
        decimals = int(precision_map.get(column, 0))
        formatted[column] = formatted[column].map(
            lambda value, dec=decimals: _format_float_value(value, dec)
        )
    return formatted


def _sort_key_almemo_file(path: Path) -> tuple[int, str]:
    """Sort ALMEMO files numerically by the ``~N`` suffix."""

    stem = path.stem
    number = -1
    if "~" in stem:
        tail = stem.split("~", 1)[1]
        try:
            number = int(tail)
        except ValueError:
            number = -1
    return (number, path.name)


def _match_col(columns: Iterable[str], prefix: str) -> str | None:
    """Return the first column name whose string value starts with ``prefix``."""

    for column in columns:
        column_text = str(column)
        if column_text.startswith(prefix):
            return column_text
    return None


def _find_col_like(columns: Iterable[str], startswith: str) -> str | None:
    for column in columns:
        column_text = str(column)
        if column_text.startswith(startswith):
            return column_text
    return None


def _find_date_time_columns(columns: Iterable[str]) -> tuple[str, str]:
    columns_list = [str(column) for column in columns]
    date_col = "DATE:" if "DATE:" in columns_list else _find_col_like(columns_list, "DATE")
    time_col = "TIME:" if "TIME:" in columns_list else _find_col_like(columns_list, "TIME")
    if not date_col or not time_col:
        raise KeyError(
            "Could not find DATE/TIME columns. Available columns: "
            + ", ".join(columns_list[:20]),
        )
    return date_col, time_col


def read_almemo_raw_csv(path: Path, encoding: str = "latin1") -> pd.DataFrame:
    """Read a raw ALMEMO CSV export into a DataFrame indexed by timestamp."""

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Input CSV not found: {path}")

    header: list[str] | None = None
    rows: list[list[str]] = []

    with path.open("r", encoding=encoding, errors="replace", newline="") as handle:
        reader = csv.reader(handle, delimiter=";", quotechar='"')
        for row in reader:
            if not row:
                continue
            row = [cell.strip() for cell in row]

            if header is None:
                if len(row) >= 2 and row[0].startswith("DATE") and row[1].startswith("TIME"):
                    header = row
                continue

            if all(cell == "" for cell in row):
                continue

            if len(row) < len(header):
                row = row + [""] * (len(header) - len(row))
            elif len(row) > len(header):
                row = row[: len(header)]

            rows.append(row)

    if header is None:
        raise ValueError(f"No ALMEMO header row (DATE/TIME) found in file: {path.name}")

    if not rows:
        return pd.DataFrame(index=pd.DatetimeIndex([], name="timestamp"))

    df = pd.DataFrame(rows, columns=header)
    date_col, time_col = _find_date_time_columns(df.columns)
    df[date_col] = df[date_col].replace("", pd.NA).ffill()
    df[time_col] = df[time_col].replace("", pd.NA)

    dt_text = df[date_col].astype(str).str.strip() + " " + df[time_col].astype(str).str.strip()
    timestamp = pd.to_datetime(
        dt_text,
        format="%d.%m.%y %H:%M:%S.%f",
        errors="coerce",
    )

    df.insert(0, "timestamp", timestamp)
    df = df.dropna(subset=["timestamp"]).set_index("timestamp").sort_index()
    df.index = pd.DatetimeIndex(df.index, freq=None, name="timestamp")
    return df


def standardize_almemo_columns(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Map raw ALMEMO channel columns into the standardized 27-column schema."""

    if df_raw.empty:
        return pd.DataFrame(index=df_raw.index, columns=CANONICAL_COLUMNS, dtype=float)

    columns = [str(column) for column in df_raw.columns]

    def numeric_series(prefix: str) -> pd.Series | None:
        raw_col = _match_col(columns, prefix)
        if raw_col is None or raw_col not in df_raw.columns:
            return None
        return pd.to_numeric(df_raw[raw_col], errors="coerce")

    standardized = pd.DataFrame(index=df_raw.index)

    mapping_groups = {
        "loadcell_1_kg": numeric_series("M000.0"),
        "loadcell_2_kg": numeric_series("M001.0"),
        "loadcell_3_kg": numeric_series("M002.0"),
        "loadcell_4_kg": numeric_series("M003.0"),
        "loadcell_5_kg": numeric_series("M004.0"),
        "loadcell_6_kg": numeric_series("M005.0"),
        "air_temp_c": numeric_series("M006.0"),
        "air_rh_percent": numeric_series("M006.1"),
        "dewpoint_c": numeric_series("M006.2"),
        "air_pressure_mb": numeric_series("M006.3"),
        "ec_1_ds": numeric_series("M010.0"),
        "moisture_1_percent": numeric_series("M010.1"),
        "ec_2_ds": numeric_series("M011.0"),
        "moisture_2_percent": numeric_series("M011.1"),
        "ec_3_ds": numeric_series("M012.0"),
        "moisture_3_percent": numeric_series("M012.1"),
        "ec_4_ds": numeric_series("M013.0"),
        "moisture_4_percent": numeric_series("M013.1"),
        "ec_5_ds": numeric_series("M014.0"),
        "moisture_5_percent": numeric_series("M014.1"),
        "ec_6_ds": numeric_series("M015.0"),
        "moisture_6_percent": numeric_series("M015.1"),
        "weather_temp_c": numeric_series("M016.0"),
        "wind_speed_m_s": numeric_series("M016.1"),
        "weather_pressure_mb": numeric_series("M016.2"),
        "tensiometer_4_hp": numeric_series("M017.0"),
        "tensiometer_5_hp": numeric_series("M018.0"),
    }

    for canonical, series in mapping_groups.items():
        if series is not None:
            standardized[canonical] = series

    for canonical in CANONICAL_COLUMNS:
        if canonical not in standardized.columns:
            standardized[canonical] = np.nan

    return standardized[CANONICAL_COLUMNS].astype(float)


def merge_duplicate_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """Merge duplicate timestamps by taking the first non-null value per column."""

    if df.empty:
        return df
    return df.groupby(df.index).first().sort_index()


def resample_and_interpolate_1s(df: pd.DataFrame) -> pd.DataFrame:
    """Reindex to 1-second frequency and fill gaps using linear interpolation."""

    if df.empty:
        return df

    start = df.index.min()
    end = df.index.max()
    if pd.isna(start) or pd.isna(end):
        return df

    full_index = pd.date_range(start=start, end=end, freq="1s", name="timestamp")
    interpolated = df.reindex(full_index)
    return interpolated.interpolate(method="time", limit_direction="both")


def preprocess_raw_folder(
    input_dir: Path,
    output_dir: Path,
    *,
    pattern: str = "ALMEMO500~*.csv",
    max_files: int | None = None,
    overwrite: bool = False,
    encoding: str = "latin1",
    interpolate_1s: bool = True,
) -> list[Path]:
    """Preprocess all raw ALMEMO files under ``input_dir`` and write per-day CSVs."""

    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(input_dir.glob(pattern), key=_sort_key_almemo_file)
    if max_files is not None:
        files = files[: int(max_files)]

    per_day_parts: dict[pd.Timestamp, list[pd.DataFrame]] = defaultdict(list)
    precision_map: dict[str, int] = {column: 0 for column in CANONICAL_COLUMNS}

    for path in files:
        df_raw = read_almemo_raw_csv(path, encoding=encoding)
        if df_raw.empty:
            continue

        _update_precision_map_from_raw(df_raw, precision_map)
        df_standardized = standardize_almemo_columns(df_raw)
        df_standardized = merge_duplicate_timestamps(df_standardized)
        if df_standardized.empty:
            continue

        for day, group in df_standardized.groupby(df_standardized.index.normalize()):
            per_day_parts[day].append(group)

    written: list[Path] = []

    for day in sorted(per_day_parts.keys()):
        out_path = output_dir / f"{day.date().isoformat()}.csv"
        if out_path.exists() and not overwrite:
            continue

        day_df = pd.concat(per_day_parts[day], axis=0).sort_index()
        day_df = merge_duplicate_timestamps(day_df)
        if interpolate_1s:
            day_df = resample_and_interpolate_1s(day_df)

        formatted = format_df_with_precision(day_df, precision_map)
        formatted.to_csv(out_path, index_label="timestamp")
        written.append(out_path)

    return written


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for ALMEMO preprocessing."""

    parser = argparse.ArgumentParser(
        description="Preprocess ALMEMO500 raw CSVs (merge split rows; optional 1s interpolation).",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/raw"),
        help="Directory containing raw ALMEMO500~*.csv files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/preprocessed_csv_interpolated"),
        help="Directory to write per-day preprocessed CSVs.",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="ALMEMO500~*.csv",
        help="Glob pattern for input files.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Optional cap on number of files to process (for testing).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output CSVs.",
    )
    parser.add_argument(
        "--encoding",
        type=str,
        default="latin1",
        help="Text encoding for raw files (latin1 is safest for ALMEMO exports).",
    )
    parser.add_argument(
        "--no-interpolate",
        dest="interpolate_1s",
        action="store_false",
        help="Do NOT resample/interpolate to 1-second grid (keep original timestamps).",
    )
    parser.set_defaults(interpolate_1s=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for command-line execution."""

    args = build_parser().parse_args(list(argv) if argv is not None else None)
    written = preprocess_raw_folder(
        args.input_dir,
        args.output_dir,
        pattern=args.pattern,
        max_files=args.max_files,
        overwrite=args.overwrite,
        encoding=args.encoding,
        interpolate_1s=args.interpolate_1s,
    )

    if not written:
        print("No output files were written.")
        return 0

    print(f"Wrote {len(written)} file(s) to: {Path(args.output_dir).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
