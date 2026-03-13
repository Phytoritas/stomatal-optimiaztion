from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from pandas.errors import ParserError

from stomatal_optimiaztion.domains import load_cell
from stomatal_optimiaztion.domains.load_cell import (
    read_load_cell_csv,
    write_multi_resolution_results,
    write_results,
)


def test_load_cell_import_surface_exposes_io_helpers() -> None:
    assert load_cell.read_load_cell_csv is read_load_cell_csv
    assert load_cell.write_results is write_results
    assert load_cell.write_multi_resolution_results is write_multi_resolution_results


def test_read_load_cell_csv_reindexes_and_marks_interpolation(tmp_path: Path) -> None:
    csv_path = tmp_path / "input.csv"
    csv_path.write_text(
        "\n".join(
            [
                "timestamp,weight_kg",
                "2025-06-01 00:00:00,1.0",
                "2025-06-01 00:00:00,",
                "bad-row,5.0",
                "2025-06-01 00:00:02,",
                "2025-06-01 00:00:03,1.3",
            ]
        ),
        encoding="utf-8",
    )

    df = read_load_cell_csv(csv_path)

    assert list(df.columns) == ["weight_raw_kg", "is_interpolated", "weight_kg"]
    assert list(df.index.astype(str)) == [
        "2025-06-01 00:00:00",
        "2025-06-01 00:00:01",
        "2025-06-01 00:00:02",
        "2025-06-01 00:00:03",
    ]
    assert df.loc["2025-06-01 00:00:00", "weight_raw_kg"] == 1.0
    assert pd.isna(df.loc["2025-06-01 00:00:01", "weight_raw_kg"])
    assert pd.isna(df.loc["2025-06-01 00:00:02", "weight_raw_kg"])
    assert df.loc["2025-06-01 00:00:03", "weight_raw_kg"] == 1.3
    assert bool(df.loc["2025-06-01 00:00:01", "is_interpolated"])
    assert bool(df.loc["2025-06-01 00:00:02", "is_interpolated"])
    assert df.loc["2025-06-01 00:00:02", "weight_kg"] == 1.0


def test_read_load_cell_csv_falls_back_after_parser_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_path = tmp_path / "input.csv"
    csv_path.write_text("timestamp,weight_kg\n2025-06-01 00:00:00,1.0\n", encoding="utf-8")

    calls: list[dict[str, object]] = []

    def fake_read_csv(*args: object, **kwargs: object) -> pd.DataFrame:
        calls.append(dict(kwargs))
        if len(calls) == 1:
            raise ParserError("broken csv")
        return pd.DataFrame(
            {
                "timestamp": ["2025-06-01 00:00:00"],
                "weight_kg": [1.0],
            }
        )

    monkeypatch.setattr(
        "stomatal_optimiaztion.domains.load_cell.io.pd.read_csv",
        fake_read_csv,
    )

    df = read_load_cell_csv(csv_path)

    assert len(calls) == 2
    assert calls[1]["engine"] == "python"
    assert calls[1]["on_bad_lines"] == "skip"
    assert df.loc["2025-06-01 00:00:00", "weight_kg"] == 1.0


def test_read_load_cell_csv_raises_for_missing_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError):
        read_load_cell_csv(missing_path)


def test_write_results_writes_csv(tmp_path: Path) -> None:
    output_path = tmp_path / "out" / "results.csv"
    frame = pd.DataFrame({"weight_kg": [1.0, 1.2]})
    frame.index = pd.date_range("2025-06-01", periods=2, freq="1s", name="timestamp")

    write_results(frame, output_path)

    written = pd.read_csv(output_path)
    assert list(written.columns) == ["timestamp", "weight_kg"]
    assert len(written) == 2


def test_write_results_wraps_excel_import_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "out" / "results.csv"
    frame = pd.DataFrame({"weight_kg": [1.0]})
    frame.index = pd.date_range("2025-06-01", periods=1, freq="1s", name="timestamp")

    def fake_to_excel(*args: object, **kwargs: object) -> None:
        raise ImportError("missing engine")

    monkeypatch.setattr(pd.DataFrame, "to_excel", fake_to_excel)

    with pytest.raises(RuntimeError, match="openpyxl|xlsxwriter"):
        write_results(frame, output_path, include_excel=True)


def test_write_multi_resolution_results_writes_expected_csvs(tmp_path: Path) -> None:
    output_path = tmp_path / "out" / "results.csv"
    frames = {
        "1s": pd.DataFrame({"weight_kg": [1.0]}),
        "10s": pd.DataFrame({"weight_kg": [1.1]}),
        "daily": pd.DataFrame({"weight_kg": [1.2]}),
    }
    frames["1s"].index = pd.date_range("2025-06-01", periods=1, freq="1s", name="timestamp")
    frames["10s"].index = pd.date_range("2025-06-01", periods=1, freq="10s", name="timestamp")
    frames["daily"].index = pd.Index(["2025-06-01"], name="day")

    write_multi_resolution_results(frames, output_path)

    assert output_path.exists()
    assert output_path.with_name("results_10s.csv").exists()
    assert output_path.with_name("results_daily.csv").exists()
    assert not output_path.with_name("results_1h.csv").exists()


def test_write_multi_resolution_results_requires_1s_frame(tmp_path: Path) -> None:
    output_path = tmp_path / "out" / "results.csv"

    with pytest.raises(KeyError, match="1s"):
        write_multi_resolution_results({}, output_path)
