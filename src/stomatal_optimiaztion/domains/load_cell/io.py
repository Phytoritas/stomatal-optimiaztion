"""Input/output utilities for load-cell data ingestion."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from pandas.errors import ParserError


def read_load_cell_csv(
    path: Path,
    timestamp_column: str = "timestamp",
    weight_column: str = "weight_kg",
) -> pd.DataFrame:
    """Read raw load-cell CSV data and return a 1-second indexed DataFrame."""

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Input CSV not found: {path}")

    try:
        df = pd.read_csv(
            path,
            usecols=[timestamp_column, weight_column],
            low_memory=False,
        )
    except ParserError:
        df = pd.read_csv(
            path,
            usecols=[timestamp_column, weight_column],
            engine="python",
            on_bad_lines="skip",
        )

    if timestamp_column not in df.columns:
        raise KeyError(f"Missing timestamp column '{timestamp_column}' in CSV.")
    if weight_column not in df.columns:
        raise KeyError(f"Missing weight column '{weight_column}' in CSV.")

    df = df[[timestamp_column, weight_column]].copy()
    df[timestamp_column] = pd.to_datetime(
        df[timestamp_column], utc=False, errors="coerce"
    )
    df[weight_column] = pd.to_numeric(df[weight_column], errors="coerce")
    df = df.dropna(subset=[timestamp_column]).sort_values(timestamp_column)

    weight_series = df.groupby(timestamp_column, sort=True)[weight_column].first()
    df = weight_series.to_frame(name="weight_raw_kg")
    df.index = pd.DatetimeIndex(df.index, freq=None, name="timestamp")

    original_index = df.index.copy()
    full_index = pd.date_range(
        start=original_index.min(),
        end=original_index.max(),
        freq="1s",
        name="timestamp",
    )

    df = df.reindex(full_index)
    is_time_inserted = ~df.index.isin(original_index)
    is_value_missing = df["weight_raw_kg"].isna()
    df["is_interpolated"] = (is_time_inserted | is_value_missing).fillna(False)
    df["weight_kg"] = df["weight_raw_kg"].ffill().bfill()

    return df


def write_results(
    df: pd.DataFrame,
    output_path: Path,
    include_excel: bool = False,
) -> None:
    """Persist processed per-second fluxes to CSV and optional Excel."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index_label="timestamp")

    if include_excel:
        excel_path = output_path.with_suffix(".xlsx")
        try:
            df.to_excel(excel_path, index_label="timestamp")
        except ImportError as exc:  # pragma: no cover - depends on engines
            raise RuntimeError(
                "Writing Excel output requires 'openpyxl' or 'xlsxwriter'.",
            ) from exc


def write_multi_resolution_results(
    frames: dict[str, pd.DataFrame],
    output_path: Path,
    include_excel: bool = False,
) -> None:
    """Write multiple time resolutions to CSV and optional multi-sheet Excel."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if "1s" not in frames:
        raise KeyError("frames must contain the '1s' DataFrame.")

    df_1s = frames["1s"]
    df_1s.to_csv(output_path, index_label="timestamp")

    suffixes = {
        "10s": "_10s",
        "1min": "_1min",
        "1h": "_1h",
        "daily": "_daily",
    }
    for key, suffix in suffixes.items():
        df = frames.get(key)
        if df is None or df.empty:
            continue
        path_for_resolution = output_path.with_name(
            f"{output_path.stem}{suffix}{output_path.suffix}"
        )
        index_label = "day" if key == "daily" else "timestamp"
        df.to_csv(path_for_resolution, index_label=index_label)

    if include_excel:
        excel_path = output_path.with_suffix(".xlsx")
        try:
            with pd.ExcelWriter(excel_path) as writer:
                for key, sheet_name in [
                    ("1s", "1s"),
                    ("10s", "10s"),
                    ("1min", "1min"),
                    ("1h", "1h"),
                    ("daily", "daily"),
                ]:
                    df = frames.get(key)
                    if df is None or df.empty:
                        continue
                    index_label = "day" if key == "daily" else "timestamp"
                    df.to_excel(writer, sheet_name=sheet_name, index_label=index_label)
        except ImportError as exc:  # pragma: no cover - depends on engines
            raise RuntimeError(
                "Writing Excel output requires 'openpyxl' or 'xlsxwriter'.",
            ) from exc
