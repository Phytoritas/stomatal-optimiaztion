from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path

import pandas as pd
import pytest

import stomatal_optimiaztion.domains.tomato.tomics.alloc.models.tomato_legacy.run as legacy_run


def _write_forcing_csv(path: Path) -> None:
    pd.DataFrame(
        {
            "datetime": [
                "2026-01-01T00:00:00",
                "2026-01-01T01:00:00",
                "2026-01-01T02:00:00",
            ],
            "T_air_C": [21.0, 22.0, 23.0],
            "PAR_umol": [150.0, 250.0, 350.0],
            "CO2_ppm": [410.0, 420.0, 430.0],
            "RH_percent": [70.0, 65.0, 60.0],
            "wind_speed_ms": [0.8, 1.0, 1.2],
        }
    ).to_csv(path, index=False)


def test_parse_datetime_rejects_invalid_value() -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="Invalid datetime"):
        legacy_run._parse_datetime("2026/01/01 00:00:00")


def test_runner_main_writes_csv_and_prints_output_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    input_path = tmp_path / "forcing.csv"
    output_path = tmp_path / "out" / "results.csv"
    _write_forcing_csv(input_path)

    result = legacy_run.main(
        [
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--max-steps",
            "2",
            "--fixed-lai",
            "2.1",
        ]
    )

    assert result == 0
    assert output_path.exists()

    out = pd.read_csv(output_path)
    assert len(out) == 2
    assert out["LAI"].tolist() == pytest.approx([2.1, 2.1])
    assert "co2_flux_g_m2_s" in out.columns
    assert str(output_path.resolve()) in capsys.readouterr().out


def test_runner_module_execution_delegates_to_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_path = tmp_path / "forcing.csv"
    output_path = tmp_path / "module-out" / "results.csv"
    _write_forcing_csv(input_path)
    module_name = "stomatal_optimiaztion.domains.tomato.tomics.alloc.models.tomato_legacy.run"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run.py",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--max-steps",
            "1",
        ],
    )
    sys.modules.pop(module_name, None)

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module(module_name, run_name="__main__")

    assert exc_info.value.code == 0
    assert output_path.exists()
    out = pd.read_csv(output_path)
    assert len(out) == 1
