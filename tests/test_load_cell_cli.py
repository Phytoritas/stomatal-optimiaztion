from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pytest

import stomatal_optimiaztion.domains.load_cell.cli as load_cell_cli
from stomatal_optimiaztion.domains import load_cell
from stomatal_optimiaztion.domains.load_cell import (
    PipelineConfig,
    build_parser,
    main as load_cell_main,
    run_pipeline,
)


def test_load_cell_import_surface_exposes_cli_helpers() -> None:
    assert load_cell.build_parser is build_parser
    assert load_cell.run_pipeline is run_pipeline
    assert load_cell.main is load_cell_main


def test_apply_overrides_maps_cli_arguments_to_config_fields() -> None:
    args = build_parser().parse_args(
        [
            "--input",
            "input.csv",
            "--output",
            "out.csv",
            "--smooth-method",
            "ma",
            "--smooth-window",
            "5",
            "--poly-order",
            "3",
            "--k-outlier",
            "2.5",
            "--max-spike-width",
            "4",
            "--derivative-method",
            "diff",
            "--no-auto-thresholds",
            "--irrigation-threshold",
            "0.4",
            "--drainage-threshold",
            "-0.3",
            "--min-event-duration",
            "6",
            "--merge-irrigation-gap",
            "7",
            "--min-pos-events",
            "8",
            "--min-neg-events",
            "9",
            "--k-tail",
            "4.5",
            "--min-factor",
            "3.5",
            "--include-interpolated-for-thresholds",
            "--use-hysteresis",
            "--hysteresis-ratio",
            "0.25",
            "--timestamp-column",
            "ts",
            "--weight-column",
            "w",
            "--no-transp-interp",
            "--no-balance-fix",
            "--balance-scale-min",
            "0.1",
            "--balance-scale-max",
            "2.2",
        ]
    )

    overrides = load_cell_cli._apply_overrides(args)

    assert overrides == {
        "input_path": Path("input.csv"),
        "output_path": Path("out.csv"),
        "smooth_method": "ma",
        "smooth_window_sec": 5,
        "poly_order": 3,
        "k_outlier": 2.5,
        "max_spike_width_sec": 4,
        "derivative_method": "diff",
        "use_auto_thresholds": False,
        "irrigation_step_threshold_kg": 0.4,
        "drainage_step_threshold_kg": -0.3,
        "min_event_duration_sec": 6,
        "merge_irrigation_gap_sec": 7,
        "min_pos_events": 8,
        "min_neg_events": 9,
        "k_tail": 4.5,
        "min_factor": 3.5,
        "exclude_interpolated_from_thresholds": False,
        "use_hysteresis_labels": True,
        "hysteresis_ratio": 0.25,
        "timestamp_column": "ts",
        "weight_column": "w",
        "interpolate_transpiration_during_events": False,
        "fix_water_balance": False,
        "water_balance_scale_min": 0.1,
        "water_balance_scale_max": 2.2,
    }


def test_run_pipeline_validates_input_and_output_paths(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="input_path"):
        run_pipeline(PipelineConfig())

    with pytest.raises(ValueError, match="output_path"):
        run_pipeline(
            PipelineConfig(input_path=tmp_path / "input.csv"),
            write_output=True,
        )


def test_run_pipeline_orchestrates_auto_threshold_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    index = pd.date_range("2025-01-01 00:00:00", periods=3, freq="s", name="timestamp")
    raw_df = pd.DataFrame(
        {
            "weight_raw_kg": [10.0, 10.2, 10.0],
            "is_interpolated": [False, True, False],
            "weight_kg": [10.0, 10.2, 10.0],
        },
        index=index,
    )
    smoothed_df = raw_df.copy()
    smoothed_df["dW_smooth_kg_s"] = [0.0, 0.5, -0.2]
    labeled_df = smoothed_df.copy()
    labeled_df["label"] = ["baseline", "irrigation", "drainage"]
    grouped_df = labeled_df.copy()
    grouped_df["event_id"] = pd.Series([pd.NA, 1, 2], index=index, dtype="Int64")
    events_df = pd.DataFrame(
        [
            {
                "event_id": 1,
                "event_type": "irrigation",
                "start_time": index[1],
                "end_time": index[1],
                "duration_sec": 1,
                "mass_change_kg": 0.2,
            },
            {
                "event_id": 2,
                "event_type": "drainage",
                "start_time": index[2],
                "end_time": index[2],
                "duration_sec": 1,
                "mass_change_kg": -0.2,
            },
        ]
    )
    merged_events_df = events_df.copy()
    flux_df = grouped_df.copy()
    flux_df["event_id_merged"] = pd.Series([pd.NA, 1, 2], index=index, dtype="Int64")
    flux_df["irrigation_kg_s"] = [0.0, 0.2, 0.0]
    flux_df["drainage_kg_s"] = [0.0, 0.0, 0.2]
    flux_df["transpiration_kg_s"] = [0.0, 0.0, 0.1]
    flux_df["cum_irrigation_kg"] = [0.0, 0.2, 0.2]
    flux_df["cum_drainage_kg"] = [0.0, 0.0, 0.2]
    flux_df["cum_transpiration_kg"] = [0.0, 0.0, 0.1]
    flux_df["water_balance_error_kg"] = [0.0, 0.0, 0.0]

    captures: dict[str, object] = {}

    monkeypatch.setattr(load_cell_cli.io, "read_load_cell_csv", lambda *args, **kwargs: raw_df.copy())
    monkeypatch.setattr(
        load_cell_cli.preprocessing,
        "detect_and_correct_outliers",
        lambda df, **kwargs: df.copy(),
    )
    monkeypatch.setattr(
        load_cell_cli.preprocessing,
        "smooth_weight",
        lambda df, **kwargs: smoothed_df.copy(),
    )

    def fake_thresholds(series: pd.Series, **kwargs: object) -> tuple[float, float]:
        captures["valid_mask"] = kwargs["valid_mask"]
        captures["threshold_logger"] = kwargs["logger"]
        assert series.equals(smoothed_df["dW_smooth_kg_s"])
        return 0.4, -0.3

    monkeypatch.setattr(
        load_cell_cli.thresholds,
        "auto_detect_step_thresholds",
        fake_thresholds,
    )
    monkeypatch.setattr(
        load_cell_cli.events,
        "label_points_by_derivative",
        lambda df, irrigation_threshold, drainage_threshold: labeled_df.copy(),
    )
    monkeypatch.setattr(
        load_cell_cli.events,
        "group_events",
        lambda df, min_event_duration_sec: (grouped_df.copy(), events_df.copy()),
    )
    monkeypatch.setattr(
        load_cell_cli.events,
        "merge_close_events_with_df",
        lambda df, events_df, gap_threshold_sec, event_type: (
            merged_events_df.copy(),
            {1: 1, 2: 2},
        ),
    )
    monkeypatch.setattr(
        load_cell_cli.fluxes,
        "compute_fluxes_per_second",
        lambda df, **kwargs: flux_df.copy(),
    )
    monkeypatch.setattr(
        load_cell_cli.aggregation,
        "resample_flux_timeseries",
        lambda df, rule: pd.DataFrame({"rule": [rule]}),
    )
    monkeypatch.setattr(
        load_cell_cli.aggregation,
        "daily_summary",
        lambda df, events_df, metadata: pd.DataFrame({"day": [1]}),
    )

    def fake_write(
        frames: dict[str, pd.DataFrame],
        output_path: Path,
        include_excel: bool,
    ) -> None:
        captures["frames"] = frames
        captures["output_path"] = output_path
        captures["include_excel"] = include_excel

    monkeypatch.setattr(
        load_cell_cli.io,
        "write_multi_resolution_results",
        fake_write,
    )

    cfg = PipelineConfig(
        input_path=Path("input.csv"),
        output_path=Path("artifacts/out.csv"),
        merge_irrigation_gap_sec=3,
    )
    logger = logging.getLogger("load-cell-cli-test")

    out_df, out_events, metadata = run_pipeline(
        cfg,
        include_excel=True,
        logger=logger,
    )

    assert captures["valid_mask"].tolist() == [True, False, True]
    assert captures["threshold_logger"] is logger
    assert out_df.equals(flux_df)
    assert out_events.equals(events_df)
    assert metadata["irrigation_threshold"] == pytest.approx(0.4)
    assert metadata["drainage_threshold"] == pytest.approx(-0.3)
    assert metadata["events"].equals(merged_events_df)
    assert metadata["events_merged"].equals(merged_events_df)
    assert metadata["events_raw"].equals(events_df)
    assert metadata["event_id_map"] == {1: 1, 2: 2}
    assert metadata["stats"] == {
        "irrigation_event_count": 1,
        "drainage_event_count": 1,
        "total_irrigation_kg": 0.2,
        "total_drainage_kg": 0.2,
        "total_transpiration_kg": 0.1,
        "final_balance_error_kg": 0.0,
    }
    assert list(captures["frames"].keys()) == ["1s", "10s", "1min", "1h", "daily"]
    assert captures["output_path"] == Path("artifacts/out.csv")
    assert captures["include_excel"] is True


def test_run_pipeline_supports_manual_thresholds_and_hysteresis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    index = pd.date_range("2025-01-01 00:00:00", periods=2, freq="s", name="timestamp")
    raw_df = pd.DataFrame(
        {
            "weight_raw_kg": [10.0, 10.1],
            "is_interpolated": [False, False],
            "weight_kg": [10.0, 10.1],
        },
        index=index,
    )
    smoothed_df = raw_df.copy()
    smoothed_df["dW_smooth_kg_s"] = [0.0, 0.1]
    labeled_df = smoothed_df.copy()
    labeled_df["label"] = ["baseline", "irrigation"]
    grouped_df = labeled_df.copy()
    grouped_df["event_id"] = pd.Series([pd.NA, 1], index=index, dtype="Int64")
    flux_df = grouped_df.copy()
    flux_df["irrigation_kg_s"] = [0.0, 0.1]
    flux_df["drainage_kg_s"] = [0.0, 0.0]
    flux_df["transpiration_kg_s"] = [0.0, 0.0]
    flux_df["cum_irrigation_kg"] = [0.0, 0.1]
    flux_df["cum_drainage_kg"] = [0.0, 0.0]
    flux_df["cum_transpiration_kg"] = [0.0, 0.0]
    flux_df["water_balance_error_kg"] = [0.0, 0.0]

    monkeypatch.setattr(load_cell_cli.io, "read_load_cell_csv", lambda *args, **kwargs: raw_df.copy())
    monkeypatch.setattr(
        load_cell_cli.preprocessing,
        "detect_and_correct_outliers",
        lambda df, **kwargs: df.copy(),
    )
    monkeypatch.setattr(
        load_cell_cli.preprocessing,
        "smooth_weight",
        lambda df, **kwargs: smoothed_df.copy(),
    )
    monkeypatch.setattr(
        load_cell_cli.thresholds,
        "auto_detect_step_thresholds",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not auto-detect")),
    )

    captures: dict[str, object] = {}

    def fake_hysteresis(
        df: pd.DataFrame,
        irrigation_threshold: float,
        drainage_threshold: float,
        hysteresis_ratio: float,
    ) -> pd.DataFrame:
        captures["thresholds"] = (irrigation_threshold, drainage_threshold)
        captures["hysteresis_ratio"] = hysteresis_ratio
        return labeled_df.copy()

    monkeypatch.setattr(
        load_cell_cli.events,
        "label_points_by_derivative_hysteresis",
        fake_hysteresis,
    )
    monkeypatch.setattr(
        load_cell_cli.events,
        "group_events",
        lambda df, min_event_duration_sec: (grouped_df.copy(), pd.DataFrame()),
    )
    monkeypatch.setattr(
        load_cell_cli.fluxes,
        "compute_fluxes_per_second",
        lambda df, **kwargs: flux_df.copy(),
    )

    cfg = PipelineConfig(
        input_path=Path("input.csv"),
        output_path=None,
        use_auto_thresholds=False,
        irrigation_step_threshold_kg=0.4,
        drainage_step_threshold_kg=-0.2,
        use_hysteresis_labels=True,
        hysteresis_ratio=0.3,
    )

    out_df, out_events, metadata = run_pipeline(
        cfg,
        write_output=False,
    )

    assert captures["thresholds"] == (0.4, -0.2)
    assert captures["hysteresis_ratio"] == pytest.approx(0.3)
    assert out_df.equals(flux_df)
    assert out_events.empty
    assert metadata["irrigation_threshold"] == pytest.approx(0.4)
    assert metadata["drainage_threshold"] == pytest.approx(-0.2)
    assert metadata["event_id_map"] == {}


def test_summarize_stats_uses_event_counts_and_cumulative_tails() -> None:
    df = pd.DataFrame(
        {
            "cum_irrigation_kg": [0.0, 0.3],
            "cum_drainage_kg": [0.0, 0.1],
            "cum_transpiration_kg": [0.0, 0.2],
            "water_balance_error_kg": [0.0, -0.05],
        }
    )
    events_df = pd.DataFrame(
        [
            {"event_type": "irrigation"},
            {"event_type": "drainage"},
            {"event_type": "irrigation"},
        ]
    )

    stats = load_cell_cli._summarize_stats(df, events_df)

    assert stats == {
        "irrigation_event_count": 2,
        "drainage_event_count": 1,
        "total_irrigation_kg": 0.3,
        "total_drainage_kg": 0.1,
        "total_transpiration_kg": 0.2,
        "final_balance_error_kg": -0.05,
    }


def test_main_loads_config_and_dispatches_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    captures: dict[str, object] = {}
    cfg = PipelineConfig(input_path=Path("input.csv"), output_path=Path("out.csv"))

    def fake_load_config(
        path: Path | None,
        overrides: dict[str, object] | None = None,
    ) -> PipelineConfig:
        captures["config_path"] = path
        captures["overrides"] = overrides
        return cfg

    def fake_run_pipeline(
        run_cfg: PipelineConfig,
        include_excel: bool,
        write_output: bool,
        logger: logging.Logger,
    ) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
        captures["run_cfg"] = run_cfg
        captures["include_excel"] = include_excel
        captures["write_output"] = write_output
        captures["logger_name"] = logger.name
        return pd.DataFrame(), pd.DataFrame(), {}

    monkeypatch.setattr(load_cell_cli.load_cell_config, "load_config", fake_load_config)
    monkeypatch.setattr(load_cell_cli, "run_pipeline", fake_run_pipeline)

    result = load_cell_main(
        [
            "--config",
            "cfg.yaml",
            "--output",
            "out.csv",
            "--excel",
            "--no-balance-fix",
        ]
    )

    assert result == 0
    assert captures["config_path"] == Path("cfg.yaml")
    assert captures["overrides"]["output_path"] == Path("out.csv")
    assert captures["overrides"]["fix_water_balance"] is False
    assert captures["run_cfg"] is cfg
    assert captures["include_excel"] is True
    assert captures["write_output"] is True
    assert captures["logger_name"] == "loadcell_pipeline"
