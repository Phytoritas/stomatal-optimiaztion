from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import stomatal_optimiaztion.domains.load_cell.sweep as load_cell_sweep
from stomatal_optimiaztion.domains import load_cell
from stomatal_optimiaztion.domains.load_cell import PipelineConfig, run_sweep


def test_load_cell_import_surface_exposes_run_sweep() -> None:
    assert load_cell.run_sweep is run_sweep


def test_parse_value_and_grid_arg_cover_scalar_cases() -> None:
    assert load_cell_sweep._parse_value(" none ") is None
    assert load_cell_sweep._parse_value("TRUE") is True
    assert load_cell_sweep._parse_value("7") == 7
    assert load_cell_sweep._parse_value("3.5") == pytest.approx(3.5)
    assert load_cell_sweep._parse_value("07") == pytest.approx(7.0)
    assert load_cell_sweep._parse_value("text") == "text"

    assert load_cell_sweep._parse_grid_arg("smooth_window_sec=11,14,17") == (
        "smooth_window_sec",
        [11, 14, 17],
    )

    with pytest.raises(ValueError, match="Expected KEY"):
        load_cell_sweep._parse_grid_arg("bad-grid")

    with pytest.raises(ValueError, match="Empty key"):
        load_cell_sweep._parse_grid_arg(" =1,2")


def test_generate_configs_validates_unknown_fields() -> None:
    base_cfg = PipelineConfig()

    generated = load_cell_sweep._generate_configs(
        base_cfg,
        {"smooth_window_sec": [11, 14], "k_tail": [4.0]},
    )

    assert len(generated) == 2
    assert generated[0][0].smooth_window_sec == 11
    assert generated[1][0].smooth_window_sec == 14
    assert generated[0][1] == {"smooth_window_sec": 11, "k_tail": 4.0}

    with pytest.raises(KeyError, match="has no field"):
        load_cell_sweep._generate_configs(base_cfg, {"bad_field": [1]})


def test_collect_runs_reads_daily_outputs_and_attaches_config_fields(
    tmp_path: Path,
) -> None:
    out_root = tmp_path / "runs"
    cfg_dir = out_root / "2025-01-01" / "results" / "raw" / "cfg-a"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "config_used.yaml").write_text(
        "\n".join(
            [
                "smooth_method: savgol",
                "smooth_window_sec: 31",
                "k_tail: 4.5",
                "min_factor: 3.0",
            ]
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        [
            {
                "day": "2025-01-01",
                "mean_abs_balance_error_kg": 0.02,
                "final_balance_error_kg": -0.01,
                "transpiration_scale": 1.1,
                "irrigation_event_count": 2,
                "drainage_event_count": 1,
                "total_irrigation_kg": 1.2,
                "total_drainage_kg": 0.6,
                "total_transpiration_kg": 0.5,
            }
        ]
    ).to_csv(cfg_dir / "loadcell_1_daily.csv", index=False)

    collected = load_cell_sweep._collect_runs(out_root)

    assert collected.shape[0] == 1
    row = collected.iloc[0]
    assert row["date"] == "2025-01-01"
    assert row["variant"] == "raw"
    assert row["config_id"] == "cfg-a"
    assert row["loadcell"] == 1
    assert row["cfg_smooth_method"] == "savgol"
    assert row["cfg_smooth_window_sec"] == 31
    assert row["cfg_k_tail"] == pytest.approx(4.5)


def test_rank_configs_scores_and_orders_by_variant() -> None:
    df_runs = pd.DataFrame(
        [
            {
                "date": "2025-01-01",
                "variant": "raw",
                "config_id": "cfg-good",
                "loadcell": 1,
                "mean_abs_balance_error_kg": 0.01,
                "final_balance_error_kg": 0.0,
                "transpiration_scale": 1.0,
                "irrigation_event_count": 1,
                "drainage_event_count": 1,
                "total_irrigation_kg": 1.0,
                "total_drainage_kg": 0.5,
                "total_transpiration_kg": 0.4,
            },
            {
                "date": "2025-01-02",
                "variant": "raw",
                "config_id": "cfg-bad",
                "loadcell": 1,
                "mean_abs_balance_error_kg": 0.2,
                "final_balance_error_kg": 0.1,
                "transpiration_scale": 1.5,
                "irrigation_event_count": 4,
                "drainage_event_count": 3,
                "total_irrigation_kg": 1.2,
                "total_drainage_kg": 0.7,
                "total_transpiration_kg": 0.5,
            },
        ]
    )

    ranking = load_cell_sweep._rank_configs(df_runs)

    assert ranking["config_id"].tolist() == ["cfg-good", "cfg-bad"]
    assert ranking["rank"].tolist() == [1, 2]
    assert ranking.iloc[0]["score"] < ranking.iloc[1]["score"]


def test_run_sweep_writes_generated_configs_and_rankings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out_root = tmp_path / "runs_sweep"
    base_config_path = tmp_path / "base.yaml"
    base_config_path.write_text("smooth_window_sec: 31\nk_tail: 4.0\n", encoding="utf-8")

    workflow_calls: dict[str, object] = {}

    def fake_run_workflow(**kwargs: object) -> None:
        workflow_calls.update(kwargs)
        for cfg_path in kwargs["config_paths"]:
            cfg_file = Path(cfg_path)
            cfg_id = cfg_file.stem
            result_dir = out_root / "2025-01-01" / "results" / "raw" / cfg_id
            result_dir.mkdir(parents=True, exist_ok=True)
            (result_dir / "config_used.yaml").write_text(
                cfg_file.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            pd.DataFrame(
                [
                    {
                        "day": "2025-01-01",
                        "mean_abs_balance_error_kg": 0.05 if "w11" in cfg_id else 0.02,
                        "final_balance_error_kg": 0.01 if "w11" in cfg_id else 0.0,
                        "transpiration_scale": 1.2 if "w11" in cfg_id else 1.0,
                        "irrigation_event_count": 2,
                        "drainage_event_count": 1,
                        "total_irrigation_kg": 1.0,
                        "total_drainage_kg": 0.4,
                        "total_transpiration_kg": 0.5,
                    }
                ]
            ).to_csv(result_dir / "loadcell_1_daily.csv", index=False)

    monkeypatch.setattr(load_cell_sweep.workflow, "run_workflow", fake_run_workflow)

    run_sweep(
        out_root=out_root,
        interpolated_dir=Path("interp"),
        raw_dir=Path("raw"),
        base_config_path=base_config_path,
        grid_args=["smooth_window_sec=11,14"],
        variants="raw",
        loadcells=[1],
        dates=["2025-01-01.csv"],
        include_excel=False,
        log_level="INFO",
    )

    sweep_dir = out_root / "_sweep"
    assert (sweep_dir / "grid.json").exists()
    assert json.loads((sweep_dir / "grid.json").read_text(encoding="utf-8")) == {
        "base_config": str(base_config_path),
        "grid": {"smooth_window_sec": [11, 14]},
    }
    configs_csv = pd.read_csv(sweep_dir / "configs.csv")
    assert len(configs_csv) == 2
    assert set(configs_csv["smooth_window_sec"].tolist()) == {11, 14}
    generated_config_paths = workflow_calls["config_paths"]
    assert len(generated_config_paths) == 2
    assert workflow_calls["variants"] == "raw"
    assert workflow_calls["loadcells"] == [1]
    assert workflow_calls["dates"] == ["2025-01-01.csv"]
    summary = pd.read_csv(out_root / "summary_runs.csv")
    ranking = pd.read_csv(out_root / "ranking.csv")
    top20 = pd.read_csv(out_root / "ranking_top20.csv")
    assert summary.shape[0] == 2
    assert ranking.shape[0] == 2
    assert top20.shape[0] == 2
    assert ranking.iloc[0]["rank"] == 1
    assert ranking.iloc[0]["score"] <= ranking.iloc[1]["score"]


def test_sweep_main_dispatches_expected_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captures: dict[str, object] = {}

    def fake_run_sweep(**kwargs: object) -> None:
        captures.update(kwargs)

    monkeypatch.setattr(load_cell_sweep, "run_sweep", fake_run_sweep)

    result = load_cell_sweep.main(
        [
            "--out-root",
            "runs",
            "--interpolated-dir",
            "interp",
            "--raw-dir",
            "raw",
            "--base-config",
            "base.yaml",
            "--grid",
            "smooth_window_sec=11,14",
            "--variants",
            "interpolated",
            "--loadcells",
            "1",
            "3",
            "--dates",
            "2025-01-01.csv",
            "--excel",
            "--log-level",
            "DEBUG",
        ]
    )

    assert result == 0
    assert captures == {
        "out_root": Path("runs"),
        "interpolated_dir": Path("interp"),
        "raw_dir": Path("raw"),
        "base_config_path": Path("base.yaml"),
        "grid_args": ["smooth_window_sec=11,14"],
        "variants": "interpolated",
        "loadcells": [1, 3],
        "dates": ["2025-01-01.csv"],
        "include_excel": True,
        "log_level": "DEBUG",
    }
