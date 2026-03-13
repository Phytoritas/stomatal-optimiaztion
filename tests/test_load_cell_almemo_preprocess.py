from __future__ import annotations

import importlib
from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains import load_cell
from stomatal_optimiaztion.domains.load_cell import CANONICAL_COLUMNS
from stomatal_optimiaztion.domains.load_cell import preprocess_raw_folder

load_cell_almemo_preprocess = importlib.import_module(
    "stomatal_optimiaztion.domains.load_cell.almemo_preprocess"
)


def _write_raw_file(path: Path, rows: list[str]) -> None:
    path.write_text("\n".join(rows) + "\n", encoding="latin1")


def test_load_cell_import_surface_exposes_almemo_helpers() -> None:
    assert load_cell.preprocess_raw_folder is preprocess_raw_folder
    assert load_cell.build_almemo_preprocess_parser is load_cell_almemo_preprocess.build_parser


def test_read_almemo_raw_csv_parses_semicolon_export(tmp_path: Path) -> None:
    raw_path = tmp_path / "ALMEMO500~19.csv"
    _write_raw_file(
        raw_path,
        [
            "metadata;;;;;;;;",
            "DATE:;TIME:;M000.0 N;M006.0 C;M006.1 %",
            "01.01.25;12:00:00.000;10.0;;",
            ";12:00:00.000;;20.5;60.0",
            "01.01.25;12:00:02.000;12.5;21.0;61.0",
        ],
    )

    df_raw = load_cell_almemo_preprocess.read_almemo_raw_csv(raw_path)

    assert list(df_raw.index.astype(str)) == [
        "2025-01-01 12:00:00",
        "2025-01-01 12:00:00",
        "2025-01-01 12:00:02",
    ]
    assert float(df_raw.iloc[0]["M000.0 N"]) == 10.0
    assert float(df_raw.iloc[1]["M006.0 C"]) == 20.5
    assert float(df_raw.iloc[1]["M006.1 %"]) == 60.0


def test_standardize_almemo_columns_maps_known_channels() -> None:
    index = pd.DatetimeIndex(["2025-01-01 12:00:00"], name="timestamp")
    raw = pd.DataFrame(
        {
            "M000.0 N": ["10.0"],
            "M006.0 C": ["22.5"],
            "M006.1 %": ["70.0"],
            "M017.0 hP": ["-12.0"],
        },
        index=index,
    )

    standardized = load_cell_almemo_preprocess.standardize_almemo_columns(raw)

    assert list(standardized.columns) == CANONICAL_COLUMNS
    assert standardized.loc[index[0], "loadcell_1_kg"] == 10.0
    assert standardized.loc[index[0], "air_temp_c"] == 22.5
    assert standardized.loc[index[0], "air_rh_percent"] == 70.0
    assert standardized.loc[index[0], "tensiometer_4_hp"] == -12.0
    assert pd.isna(standardized.loc[index[0], "loadcell_2_kg"])


def test_merge_duplicate_timestamps_uses_first_non_null_values() -> None:
    index = pd.DatetimeIndex(
        ["2025-01-01 12:00:00", "2025-01-01 12:00:00"],
        name="timestamp",
    )
    df = pd.DataFrame(
        {
            "loadcell_1_kg": [10.0, None],
            "air_temp_c": [None, 23.0],
        },
        index=index,
    )

    merged = load_cell_almemo_preprocess.merge_duplicate_timestamps(df)

    assert merged.shape == (1, 2)
    assert merged.iloc[0]["loadcell_1_kg"] == 10.0
    assert merged.iloc[0]["air_temp_c"] == 23.0


def test_resample_and_interpolate_1s_fills_missing_seconds() -> None:
    index = pd.DatetimeIndex(
        ["2025-01-01 12:00:00", "2025-01-01 12:00:02"],
        name="timestamp",
    )
    df = pd.DataFrame({"loadcell_1_kg": [10.0, 12.0]}, index=index)

    interpolated = load_cell_almemo_preprocess.resample_and_interpolate_1s(df)

    assert list(interpolated.index.astype(str)) == [
        "2025-01-01 12:00:00",
        "2025-01-01 12:00:01",
        "2025-01-01 12:00:02",
    ]
    assert interpolated.iloc[1]["loadcell_1_kg"] == 11.0


def test_preprocess_raw_folder_writes_interpolated_daily_csv(tmp_path: Path) -> None:
    input_dir = tmp_path / "raw"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    _write_raw_file(
        input_dir / "ALMEMO500~2.csv",
        [
            "metadata;;;;;;;;",
            "DATE:;TIME:;M000.0 N;M006.0 C;M006.1 %",
            "01.01.25;12:00:00.000;10.0;;",
            ";12:00:00.000;;20.0;60.0",
            "01.01.25;12:00:02.000;12.0;22.0;64.0",
        ],
    )

    written = load_cell_almemo_preprocess.preprocess_raw_folder(
        input_dir,
        output_dir,
        interpolate_1s=True,
    )

    assert written == [output_dir / "2025-01-01.csv"]
    out_df = pd.read_csv(written[0])
    assert list(out_df["timestamp"]) == [
        "2025-01-01 12:00:00",
        "2025-01-01 12:00:01",
        "2025-01-01 12:00:02",
    ]
    assert list(out_df["loadcell_1_kg"]) == [10.0, 11.0, 12.0]
    assert list(out_df["air_temp_c"]) == [20.0, 21.0, 22.0]
    assert list(out_df["air_rh_percent"]) == [60.0, 62.0, 64.0]


def test_main_parses_cli_and_prints_summary(tmp_path: Path, capsys) -> None:
    input_dir = tmp_path / "raw"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    _write_raw_file(
        input_dir / "ALMEMO500~1.csv",
        [
            "metadata;;;;;;;;",
            "DATE:;TIME:;M000.0 N",
            "01.01.25;12:00:00.000;10.0",
        ],
    )

    result = load_cell_almemo_preprocess.main(
        [
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            "--no-interpolate",
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "Wrote 1 file(s) to:" in captured.out
    assert (output_dir / "2025-01-01.csv").exists()
