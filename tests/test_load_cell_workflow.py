from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import stomatal_optimiaztion.domains.load_cell.workflow as load_cell_workflow
from stomatal_optimiaztion.domains import load_cell
from stomatal_optimiaztion.domains.load_cell import (
    PipelineConfig,
    config_signature,
    run_workflow,
)


def test_load_cell_import_surface_exposes_workflow_helpers() -> None:
    assert load_cell.config_signature is config_signature
    assert load_cell.run_workflow is run_workflow


def test_config_signature_is_stable_across_io_fields_only() -> None:
    base = PipelineConfig(
        input_path=Path("input-a.csv"),
        output_path=Path("out-a.csv"),
        timestamp_column="timestamp",
        weight_column="weight_kg",
        smooth_window_sec=31,
    )
    same_model = PipelineConfig(
        input_path=Path("input-b.csv"),
        output_path=Path("out-b.csv"),
        timestamp_column="ts",
        weight_column="mass",
        smooth_window_sec=31,
    )
    changed_model = PipelineConfig(smooth_window_sec=41)

    base_slug, base_hash = config_signature(base)
    same_slug, same_hash = config_signature(same_model)
    changed_slug, changed_hash = config_signature(changed_model)

    assert base_slug == same_slug
    assert base_hash == same_hash
    assert changed_slug != base_slug
    assert changed_hash != base_hash


def test_infer_weight_column_supports_canonical_and_legacy_headers(
    tmp_path: Path,
) -> None:
    canonical = tmp_path / "canonical.csv"
    canonical.write_text(
        "timestamp,loadcell_1_kg,M000.0 N\n2025-01-01 00:00:00,1.0,2.0\n",
        encoding="utf-8",
    )
    legacy = tmp_path / "legacy.csv"
    legacy.write_text(
        "timestamp,M000.0 N\n2025-01-01 00:00:00,2.0\n",
        encoding="utf-8",
    )

    assert load_cell_workflow._infer_weight_column(canonical, 1) == "loadcell_1_kg"
    assert load_cell_workflow._infer_weight_column(legacy, 1) == "M000.0 N"

    missing = tmp_path / "missing.csv"
    missing.write_text("timestamp,other\n2025-01-01 00:00:00,3.0\n", encoding="utf-8")

    with pytest.raises(KeyError, match="Could not find weight column"):
        load_cell_workflow._infer_weight_column(missing, 1)


def test_common_filenames_filters_by_variant(tmp_path: Path) -> None:
    interpolated_dir = tmp_path / "interpolated"
    raw_dir = tmp_path / "raw"
    interpolated_dir.mkdir()
    raw_dir.mkdir()
    for path in [
        interpolated_dir / "2025-01-01.csv",
        interpolated_dir / "2025-01-02.csv",
        raw_dir / "2025-01-02.csv",
        raw_dir / "2025-01-03.csv",
    ]:
        path.write_text("timestamp,weight\n", encoding="utf-8")

    assert load_cell_workflow._common_filenames(interpolated_dir, raw_dir, "interpolated") == [
        "2025-01-01.csv",
        "2025-01-02.csv",
    ]
    assert load_cell_workflow._common_filenames(interpolated_dir, raw_dir, "raw") == [
        "2025-01-02.csv",
        "2025-01-03.csv",
    ]
    assert load_cell_workflow._common_filenames(interpolated_dir, raw_dir, "both") == [
        "2025-01-02.csv"
    ]


def test_run_workflow_requires_matching_files(tmp_path: Path) -> None:
    interpolated_dir = tmp_path / "interpolated"
    raw_dir = tmp_path / "raw"
    out_root = tmp_path / "runs"
    interpolated_dir.mkdir()
    raw_dir.mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text("smooth_window_sec: 31\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="No input files matched"):
        run_workflow(
            interpolated_dir=interpolated_dir,
            raw_dir=raw_dir,
            out_root=out_root,
            config_paths=[config_path],
            variants="both",
        )


def test_run_workflow_writes_environment_and_variant_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    interpolated_dir = tmp_path / "interpolated"
    raw_dir = tmp_path / "raw"
    out_root = tmp_path / "runs"
    interpolated_dir.mkdir()
    raw_dir.mkdir()
    filename = "2025-01-02.csv"
    (interpolated_dir / filename).write_text(
        "timestamp,loadcell_1_kg,ec_1_ds,moisture_1_percent\n"
        "2025-01-02 00:00:00,10.0,1.2,55.0\n",
        encoding="utf-8",
    )
    (raw_dir / filename).write_text(
        "timestamp,M000.0 N\n2025-01-02 00:00:00,10.0\n",
        encoding="utf-8",
    )

    config_path = tmp_path / "config.yaml"
    config_text = "smooth_window_sec: 15\nmerge_irrigation_gap_sec: 5\n"
    config_path.write_text(config_text, encoding="utf-8")
    base_cfg = PipelineConfig(smooth_window_sec=15, merge_irrigation_gap_sec=5)
    slug, digest = config_signature(base_cfg)
    cfg_id = f"{slug}__{digest}"

    index = pd.date_range("2025-01-02 00:00:00", periods=2, freq="s", name="timestamp")
    df_interpolated = pd.DataFrame(
        {
            "loadcell_1_kg": [10.0, 10.1],
            "ec_1_ds": [1.2, 1.3],
            "moisture_1_percent": [55.0, 56.0],
            "air_temp_c": [22.0, 22.1],
        },
        index=index,
    )
    events_df = pd.DataFrame(
        [
            {
                "event_id": 1,
                "event_type": "irrigation",
                "start_time": index[0],
                "end_time": index[0],
                "duration_sec": 1,
                "mass_change_kg": 0.1,
            }
        ]
    )
    merged_events_df = events_df.copy()
    df_result = pd.DataFrame(
        {
            "irrigation_kg_s": [0.1, 0.0],
            "drainage_kg_s": [0.0, 0.0],
            "transpiration_kg_s": [0.0, 0.1],
            "cum_irrigation_kg": [0.1, 0.1],
            "cum_drainage_kg": [0.0, 0.0],
            "cum_transpiration_kg": [0.0, 0.1],
            "water_balance_error_kg": [0.0, 0.0],
        },
        index=index,
    )

    calls: list[dict[str, object]] = []
    writes: list[dict[str, object]] = []

    monkeypatch.setattr(
        load_cell_workflow,
        "_read_interpolated_full",
        lambda path: df_interpolated.copy(),
    )

    def fake_run_pipeline(
        cfg: PipelineConfig,
        include_excel: bool,
        write_output: bool,
        logger,
    ) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
        calls.append(
            {
                "input_path": cfg.input_path,
                "output_path": cfg.output_path,
                "timestamp_column": cfg.timestamp_column,
                "weight_column": cfg.weight_column,
                "include_excel": include_excel,
                "write_output": write_output,
                "logger_name": logger.name,
            }
        )
        return (
            df_result.copy(),
            events_df.copy(),
            {
                "irrigation_threshold": 0.4,
                "drainage_threshold": -0.3,
                "events_merged": merged_events_df.copy(),
            },
        )

    monkeypatch.setattr(load_cell_workflow.cli, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(
        load_cell_workflow.aggregation,
        "resample_flux_timeseries",
        lambda df, rule: pd.DataFrame({"rule": [rule]}),
    )
    monkeypatch.setattr(
        load_cell_workflow.aggregation,
        "daily_summary",
        lambda df, events_df, metadata: pd.DataFrame({"day": [1]}),
    )

    def fake_write_multi_resolution_results(
        frames: dict[str, pd.DataFrame],
        output_path: Path,
        include_excel: bool = False,
    ) -> None:
        writes.append(
            {
                "frames": frames,
                "output_path": output_path,
                "include_excel": include_excel,
            }
        )

    monkeypatch.setattr(
        load_cell_workflow.io,
        "write_multi_resolution_results",
        fake_write_multi_resolution_results,
    )

    run_workflow(
        interpolated_dir=interpolated_dir,
        raw_dir=raw_dir,
        out_root=out_root,
        config_paths=[config_path],
        variants="both",
        loadcells=[1],
        include_excel=True,
    )

    assert len(writes) == 3
    assert writes[0]["output_path"] == out_root / "2025-01-02" / "env" / "environment.csv"
    assert writes[1]["output_path"] == (
        out_root / "2025-01-02" / "results" / "interpolated" / cfg_id / "loadcell_1.csv"
    )
    assert writes[2]["output_path"] == (
        out_root / "2025-01-02" / "results" / "raw" / cfg_id / "loadcell_1.csv"
    )
    assert writes[0]["include_excel"] is True
    assert writes[1]["include_excel"] is True
    assert writes[2]["include_excel"] is True
    assert "air_temp_c" in writes[0]["frames"]["1s"].columns
    assert "substrate_ec_ds" in writes[1]["frames"]["1s"].columns
    assert "substrate_moisture_percent" in writes[2]["frames"]["1s"].columns

    assert calls == [
        {
            "input_path": interpolated_dir / filename,
            "output_path": None,
            "timestamp_column": "timestamp",
            "weight_column": "loadcell_1_kg",
            "include_excel": False,
            "write_output": False,
            "logger_name": "loadcell_workflow",
        },
        {
            "input_path": raw_dir / filename,
            "output_path": None,
            "timestamp_column": "timestamp",
            "weight_column": "M000.0 N",
            "include_excel": False,
            "write_output": False,
            "logger_name": "loadcell_workflow",
        },
    ]
    assert (
        out_root / "2025-01-02" / "results" / "interpolated" / cfg_id / "config_used.yaml"
    ).read_text(encoding="utf-8") == config_text
    assert (
        out_root / "2025-01-02" / "results" / "raw" / cfg_id / "config_used.yaml"
    ).read_text(encoding="utf-8") == config_text


def test_workflow_main_dispatches_with_default_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captures: dict[str, object] = {}

    def fake_run_workflow(**kwargs: object) -> None:
        captures.update(kwargs)

    monkeypatch.setattr(load_cell_workflow, "run_workflow", fake_run_workflow)

    result = load_cell_workflow.main(
        [
            "--interpolated-dir",
            "interp",
            "--raw-dir",
            "raw",
            "--out-root",
            "runs-out",
            "--variants",
            "raw",
            "--loadcells",
            "2",
            "4",
            "--dates",
            "2025-01-01.csv",
            "--excel",
            "--log-level",
            "INFO",
        ]
    )

    assert result == 0
    assert captures == {
        "interpolated_dir": Path("interp"),
        "raw_dir": Path("raw"),
        "out_root": Path("runs-out"),
        "config_paths": [Path("config.yaml")],
        "variants": "raw",
        "loadcells": [2, 4],
        "dates": ["2025-01-01.csv"],
        "include_excel": True,
        "log_level": "INFO",
    }
