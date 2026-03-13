from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from stomatal_optimiaztion.domains.load_cell import PipelineConfig


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "real_data_benchmark.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location(
        "load_cell_real_data_benchmark_script",
        _script_path(),
    )
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_real_data_benchmark_requires_common_files(tmp_path: Path) -> None:
    module = _load_script_module()
    interpolated_dir = tmp_path / "interp"
    raw_dir = tmp_path / "raw"
    interpolated_dir.mkdir()
    raw_dir.mkdir()
    (interpolated_dir / "2025-01-01.csv").write_text("timestamp\n", encoding="utf-8")
    (raw_dir / "2025-01-02.csv").write_text("timestamp\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="No common CSV filenames"):
        module.run_real_data_benchmark(
            dir_interpolated=interpolated_dir,
            dir_raw=raw_dir,
            config_path=None,
            out_dir=tmp_path / "out",
            loadcells=[1],
        )


def test_real_data_benchmark_writes_summary_and_overlap_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_script_module()
    interpolated_dir = tmp_path / "interp"
    raw_dir = tmp_path / "raw"
    out_dir = tmp_path / "out"
    interpolated_dir.mkdir()
    raw_dir.mkdir()
    (interpolated_dir / "2025-01-01.csv").write_text("timestamp\n", encoding="utf-8")
    (raw_dir / "2025-01-01.csv").write_text("timestamp\n", encoding="utf-8")

    monkeypatch.setattr(module, "load_config", lambda path: PipelineConfig(smooth_window_sec=15))

    index = pd.date_range("2025-01-01 00:00:00", periods=3, freq="s", name="timestamp")
    events_df = pd.DataFrame(
        [
            {
                "event_id": 1,
                "event_type": "irrigation",
                "start_time": index[0],
                "end_time": index[0],
                "duration_sec": 1,
                "mass_change_kg": 0.2,
            }
        ]
    )

    def fake_run_pipeline(cfg, include_excel, write_output, logger):
        assert include_excel is False
        assert write_output is False
        if cfg.weight_column == "loadcell_1_kg":
            df = pd.DataFrame(
                {
                    "irrigation_kg_s": [0.2, 0.0, 0.0],
                    "drainage_kg_s": [0.0, 0.0, 0.1],
                    "transpiration_kg_s": [0.0, 0.1, 0.1],
                    "cum_irrigation_kg": [0.2, 0.2, 0.2],
                    "cum_drainage_kg": [0.0, 0.0, 0.1],
                    "cum_transpiration_kg": [0.0, 0.1, 0.2],
                    "water_balance_error_kg": [0.0, 0.01, 0.01],
                    "is_interpolated": [1.0, 1.0, 1.0],
                    "is_outlier": [0.0, 0.0, 0.0],
                    "transpiration_scale": [1.0, 1.0, 1.0],
                },
                index=index,
            )
        else:
            df = pd.DataFrame(
                {
                    "irrigation_kg_s": [0.1, 0.0, 0.0],
                    "drainage_kg_s": [0.0, 0.0, 0.05],
                    "transpiration_kg_s": [0.0, 0.05, 0.05],
                    "cum_irrigation_kg": [0.1, 0.1, 0.1],
                    "cum_drainage_kg": [0.0, 0.0, 0.05],
                    "cum_transpiration_kg": [0.0, 0.05, 0.1],
                    "water_balance_error_kg": [0.0, 0.02, 0.02],
                    "is_interpolated": [0.0, 0.0, 0.0],
                    "is_outlier": [0.0, 0.0, 0.0],
                    "transpiration_scale": [1.0, 1.0, 1.0],
                },
                index=index,
            )
        return (
            df,
            events_df.copy(),
            {
                "irrigation_threshold": 0.4,
                "drainage_threshold": -0.3,
                "events_merged": events_df.copy(),
                "stats": {"final_balance_error_kg": float(df["water_balance_error_kg"].iloc[-1])},
            },
        )

    monkeypatch.setattr(module, "run_pipeline", fake_run_pipeline)

    result = module.run_real_data_benchmark(
        dir_interpolated=interpolated_dir,
        dir_raw=raw_dir,
        config_path=tmp_path / "config.yaml",
        out_dir=out_dir,
        loadcells=[1],
    )

    summary_df = pd.read_csv(out_dir / "summary_runs.csv")
    comparison_df = pd.read_csv(out_dir / "comparison.csv")
    overlap_df = pd.read_csv(out_dir / "comparison_overlap.csv")
    captured = capsys.readouterr()

    assert result["row_count"] == 2
    assert result["failure_count"] == 0
    assert result["failures_path"] is None
    assert len(summary_df) == 2
    assert set(summary_df["tag"]) == {"interpolated", "raw"}
    assert comparison_df.loc[0, "diff_total_irrigation_kg"] == pytest.approx(0.1)
    assert comparison_df.loc[0, "diff_total_drainage_kg"] == pytest.approx(0.05)
    assert comparison_df.loc[0, "diff_total_transpiration_kg"] == pytest.approx(0.1)
    assert overlap_df.loc[0, "diff_irrigation_kg"] == pytest.approx(0.1)
    assert "No failures." in captured.out
    assert "Progress: 2/2 runs" in captured.out


def test_real_data_benchmark_writes_failures_csv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_script_module()
    interpolated_dir = tmp_path / "interp"
    raw_dir = tmp_path / "raw"
    out_dir = tmp_path / "out"
    interpolated_dir.mkdir()
    raw_dir.mkdir()
    (interpolated_dir / "2025-01-01.csv").write_text("timestamp\n", encoding="utf-8")
    (raw_dir / "2025-01-01.csv").write_text("timestamp\n", encoding="utf-8")

    monkeypatch.setattr(module, "load_config", lambda path: PipelineConfig())

    index = pd.date_range("2025-01-01 00:00:00", periods=2, freq="s", name="timestamp")

    def fake_run_pipeline(cfg, include_excel, write_output, logger):
        if cfg.weight_column == "M000.0 N":
            raise ValueError("raw failure")
        df = pd.DataFrame(
            {
                "cum_irrigation_kg": [0.1, 0.1],
                "cum_drainage_kg": [0.0, 0.0],
                "cum_transpiration_kg": [0.0, 0.05],
                "water_balance_error_kg": [0.0, 0.0],
            },
            index=index,
        )
        return df, pd.DataFrame(), {"stats": {"final_balance_error_kg": 0.0}}

    monkeypatch.setattr(module, "run_pipeline", fake_run_pipeline)

    result = module.run_real_data_benchmark(
        dir_interpolated=interpolated_dir,
        dir_raw=raw_dir,
        config_path=tmp_path / "config.yaml",
        out_dir=out_dir,
        loadcells=[1],
    )

    failures_df = pd.read_csv(out_dir / "failures.csv")
    assert result["failure_count"] == 1
    assert result["failures_path"] == out_dir / "failures.csv"
    assert failures_df.loc[0, "tag"] == "raw"
    assert "ValueError('raw failure')" in failures_df.loc[0, "error"]


def test_real_data_benchmark_main_dispatches_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_script_module()
    captures: dict[str, object] = {}

    def fake_run_real_data_benchmark(**kwargs):
        captures.update(kwargs)
        return {}

    monkeypatch.setattr(module, "run_real_data_benchmark", fake_run_real_data_benchmark)

    result = module.main(
        [
            "--interpolated-dir",
            "interp",
            "--raw-dir",
            "raw",
            "--config",
            "config.yaml",
            "--out-dir",
            "out",
            "--loadcells",
            "2",
            "4",
            "--log-level",
            "INFO",
        ]
    )

    assert result == 0
    assert captures == {
        "dir_interpolated": Path("interp"),
        "dir_raw": Path("raw"),
        "config_path": Path("config.yaml"),
        "out_dir": Path("out"),
        "loadcells": [2, 4],
        "log_level": "INFO",
    }
