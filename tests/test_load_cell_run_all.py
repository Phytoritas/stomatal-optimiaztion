from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from stomatal_optimiaztion.domains import load_cell
from stomatal_optimiaztion.domains.load_cell import run_all

load_cell_run_all = importlib.import_module("stomatal_optimiaztion.domains.load_cell.run_all")


def test_load_cell_import_surface_exposes_run_all_helper() -> None:
    assert load_cell.run_all is run_all


def test_run_all_raises_when_preprocess_is_required_but_missing() -> None:
    with pytest.raises(RuntimeError, match="skip_preprocess=True|inject preprocess_raw_folder"):
        run_all(raw_input_dir=Path("raw"))


def test_run_all_preprocesses_then_dispatches_workflow() -> None:
    preprocess_calls: list[dict[str, object]] = []
    captures: dict[str, object] = {}

    def fake_preprocess(
        input_dir: Path,
        output_dir: Path,
        *,
        pattern: str,
        max_files: int | None,
        overwrite: bool,
        encoding: str,
        interpolate_1s: bool,
    ) -> None:
        preprocess_calls.append(
            {
                "input_dir": input_dir,
                "output_dir": output_dir,
                "pattern": pattern,
                "max_files": max_files,
                "overwrite": overwrite,
                "encoding": encoding,
                "interpolate_1s": interpolate_1s,
            }
        )

    def fake_run_workflow(**kwargs: object) -> None:
        captures.update(kwargs)

    original_run_workflow = load_cell_run_all.workflow.run_workflow
    load_cell_run_all.workflow.run_workflow = fake_run_workflow
    try:
        run_all(
            raw_input_dir=Path("raw-data"),
            pattern="demo*.csv",
            encoding="cp949",
            max_files=3,
            overwrite_preprocess=True,
            daily_raw_dir=Path("daily-raw"),
            daily_interpolated_dir=Path("daily-interp"),
            out_root=Path("runs"),
            variants="both",
            loadcells=[1, 4],
            dates=["2025-01-01.csv"],
            config_paths=[Path("cfg-a.yaml"), Path("cfg-b.yaml")],
            include_excel=True,
            log_level="INFO",
            base_config=Path("base.yaml"),
            preprocess_raw_folder=fake_preprocess,
        )
    finally:
        load_cell_run_all.workflow.run_workflow = original_run_workflow

    assert preprocess_calls == [
        {
            "input_dir": Path("raw-data"),
            "output_dir": Path("daily-raw"),
            "pattern": "demo*.csv",
            "max_files": 3,
            "overwrite": True,
            "encoding": "cp949",
            "interpolate_1s": False,
        },
        {
            "input_dir": Path("raw-data"),
            "output_dir": Path("daily-interp"),
            "pattern": "demo*.csv",
            "max_files": 3,
            "overwrite": True,
            "encoding": "cp949",
            "interpolate_1s": True,
        },
    ]
    assert captures == {
        "interpolated_dir": Path("daily-interp"),
        "raw_dir": Path("daily-raw"),
        "out_root": Path("runs"),
        "config_paths": [Path("cfg-a.yaml"), Path("cfg-b.yaml")],
        "variants": "both",
        "loadcells": [1, 4],
        "dates": ["2025-01-01.csv"],
        "include_excel": True,
        "log_level": "INFO",
    }


def test_run_all_skips_preprocess_and_dispatches_sweep() -> None:
    captures: dict[str, object] = {}

    def fake_run_sweep(**kwargs: object) -> None:
        captures.update(kwargs)

    original_run_sweep = load_cell_run_all.sweep.run_sweep
    load_cell_run_all.sweep.run_sweep = fake_run_sweep
    try:
        run_all(
            raw_input_dir=Path("raw-data"),
            skip_preprocess=True,
            daily_raw_dir=Path("daily-raw"),
            daily_interpolated_dir=Path("daily-interp"),
            out_root=Path("runs-sweep"),
            variants="raw",
            loadcells=[2],
            dates=["2025-01-02.csv"],
            include_excel=False,
            log_level="DEBUG",
            base_config=Path("base.yaml"),
            grid_args=["smooth_window_sec=11,14"],
        )
    finally:
        load_cell_run_all.sweep.run_sweep = original_run_sweep

    assert captures == {
        "out_root": Path("runs-sweep"),
        "interpolated_dir": Path("daily-interp"),
        "raw_dir": Path("daily-raw"),
        "base_config_path": Path("base.yaml"),
        "grid_args": ["smooth_window_sec=11,14"],
        "variants": "raw",
        "loadcells": [2],
        "dates": ["2025-01-02.csv"],
        "include_excel": False,
        "log_level": "DEBUG",
    }


def test_main_parses_cli_and_delegates_to_run_all() -> None:
    captures: dict[str, object] = {}

    def fake_run_all(**kwargs: object) -> None:
        captures.update(kwargs)

    original_run_all = load_cell_run_all.run_all
    load_cell_run_all.run_all = fake_run_all
    try:
        result = load_cell_run_all.main(
            [
                "--raw-input-dir",
                "raw",
                "--pattern",
                "ALM*.csv",
                "--encoding",
                "utf-8",
                "--max-files",
                "2",
                "--overwrite-preprocess",
                "--daily-raw-dir",
                "daily-raw",
                "--daily-interpolated-dir",
                "daily-interp",
                "--out-root",
                "runs",
                "--variants",
                "interpolated",
                "--loadcells",
                "1",
                "5",
                "--dates",
                "2025-01-03.csv",
                "--config",
                "cfg.yaml",
                "--excel",
                "--log-level",
                "INFO",
                "--base-config",
                "base.yaml",
                "--grid",
                "k_tail=4.0,4.5",
            ]
        )
    finally:
        load_cell_run_all.run_all = original_run_all

    assert result == 0
    assert captures == {
        "raw_input_dir": Path("raw"),
        "pattern": "ALM*.csv",
        "encoding": "utf-8",
        "max_files": 2,
        "skip_preprocess": False,
        "overwrite_preprocess": True,
        "daily_raw_dir": Path("daily-raw"),
        "daily_interpolated_dir": Path("daily-interp"),
        "out_root": Path("runs"),
        "variants": "interpolated",
        "loadcells": [1, 5],
        "dates": ["2025-01-03.csv"],
        "config_paths": [Path("cfg.yaml")],
        "include_excel": True,
        "log_level": "INFO",
        "base_config": Path("base.yaml"),
        "grid_args": ["k_tail=4.0,4.5"],
        "preprocess_raw_folder": None,
    }
