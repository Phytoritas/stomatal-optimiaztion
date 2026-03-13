"""Command-line interface for the load-cell processing pipeline."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from . import aggregation
from . import config as load_cell_config
from . import events
from . import fluxes
from . import io
from . import preprocessing
from . import thresholds


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Process greenhouse load-cell data to estimate fluxes.",
    )
    parser.add_argument("--config", type=Path, help="Path to YAML configuration file.")
    parser.add_argument(
        "--input", type=Path, help="Input CSV file with load-cell data."
    )
    parser.add_argument(
        "--output", type=Path, help="Output CSV path for per-second fluxes."
    )
    parser.add_argument(
        "--excel", action="store_true", help="Also write an Excel workbook."
    )
    parser.add_argument(
        "--smooth-method",
        choices=["ma", "savgol"],
        help="Smoothing method for weight signal.",
    )
    parser.add_argument(
        "--smooth-window", type=int, help="Smoothing window length in seconds."
    )
    parser.add_argument(
        "--poly-order", type=int, help="Savitzky-Golay polynomial order."
    )
    parser.add_argument("--k-outlier", type=float, help="Outlier MAD multiplier.")
    parser.add_argument(
        "--max-spike-width",
        type=int,
        help="Max spike width (s) to correct as outliers (guards real events).",
    )
    parser.add_argument(
        "--derivative-method",
        choices=["diff", "central", "savgol"],
        help="Derivative method for dW (diff|central|savgol).",
    )
    parser.add_argument(
        "--use-auto-thresholds", dest="use_auto_thresholds", action="store_true"
    )
    parser.add_argument(
        "--no-auto-thresholds", dest="use_auto_thresholds", action="store_false"
    )
    parser.set_defaults(use_auto_thresholds=None)
    parser.add_argument(
        "--irrigation-threshold", type=float, help="Manual irrigation step threshold."
    )
    parser.add_argument(
        "--drainage-threshold", type=float, help="Manual drainage step threshold."
    )
    parser.add_argument(
        "--min-event-duration", type=int, help="Minimum event duration in seconds."
    )
    parser.add_argument(
        "--merge-irrigation-gap",
        type=int,
        help="Gap (s) to merge irrigation events; omit to disable.",
    )
    parser.add_argument(
        "--min-pos-events", type=int, help="Minimum positive tail points."
    )
    parser.add_argument(
        "--min-neg-events", type=int, help="Minimum negative tail points."
    )
    parser.add_argument("--k-tail", type=float, help="Tail sigma multiplier.")
    parser.add_argument(
        "--min-factor", type=float, help="Minimum sigma distance from baseline."
    )
    parser.add_argument(
        "--exclude-interpolated-for-thresholds",
        dest="exclude_interpolated_from_thresholds",
        action="store_true",
        help="Exclude interpolated (forward-filled) samples when auto-detecting thresholds.",
    )
    parser.add_argument(
        "--include-interpolated-for-thresholds",
        dest="exclude_interpolated_from_thresholds",
        action="store_false",
        help="Include interpolated samples when auto-detecting thresholds.",
    )
    parser.set_defaults(exclude_interpolated_from_thresholds=None)
    parser.add_argument(
        "--use-hysteresis",
        dest="use_hysteresis_labels",
        action="store_true",
        help="Enable hysteresis labeling (reduces label flicker).",
    )
    parser.add_argument(
        "--no-hysteresis",
        dest="use_hysteresis_labels",
        action="store_false",
        help="Disable hysteresis labeling.",
    )
    parser.set_defaults(use_hysteresis_labels=None)
    parser.add_argument(
        "--hysteresis-ratio", type=float, help="Hysteresis ratio in (0, 1]."
    )
    parser.add_argument("--timestamp-column", type=str, help="Timestamp column name.")
    parser.add_argument("--weight-column", type=str, help="Weight column name.")
    parser.add_argument(
        "--no-transp-interp",
        dest="interpolate_transpiration_during_events",
        action="store_false",
        help="Disable transpiration interpolation during events.",
    )
    parser.add_argument(
        "--no-balance-fix",
        dest="fix_water_balance",
        action="store_false",
        help="Disable water balance bias correction.",
    )
    parser.add_argument(
        "--balance-scale-min",
        type=float,
        help="Minimum transpiration scale applied by water-balance fix.",
    )
    parser.add_argument(
        "--balance-scale-max",
        type=float,
        help="Maximum transpiration scale applied by water-balance fix (omit to disable).",
    )
    parser.set_defaults(
        interpolate_transpiration_during_events=None,
        fix_water_balance=None,
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ...).",
    )
    return parser


def _apply_overrides(args: argparse.Namespace) -> dict[str, Any]:
    """Convert CLI arguments into config overrides."""

    overrides: dict[str, Any] = {}
    if args.input:
        overrides["input_path"] = args.input
    if args.output:
        overrides["output_path"] = args.output
    if args.smooth_method:
        overrides["smooth_method"] = args.smooth_method
    if args.smooth_window:
        overrides["smooth_window_sec"] = args.smooth_window
    if args.poly_order is not None:
        overrides["poly_order"] = args.poly_order
    if args.k_outlier is not None:
        overrides["k_outlier"] = args.k_outlier
    if args.max_spike_width is not None:
        overrides["max_spike_width_sec"] = args.max_spike_width
    if args.derivative_method:
        overrides["derivative_method"] = args.derivative_method
    if args.use_auto_thresholds is not None:
        overrides["use_auto_thresholds"] = args.use_auto_thresholds
    if args.irrigation_threshold is not None:
        overrides["irrigation_step_threshold_kg"] = args.irrigation_threshold
    if args.drainage_threshold is not None:
        overrides["drainage_step_threshold_kg"] = args.drainage_threshold
    if args.min_event_duration is not None:
        overrides["min_event_duration_sec"] = args.min_event_duration
    if args.merge_irrigation_gap is not None:
        overrides["merge_irrigation_gap_sec"] = args.merge_irrigation_gap
    if args.min_pos_events is not None:
        overrides["min_pos_events"] = args.min_pos_events
    if args.min_neg_events is not None:
        overrides["min_neg_events"] = args.min_neg_events
    if args.k_tail is not None:
        overrides["k_tail"] = args.k_tail
    if args.min_factor is not None:
        overrides["min_factor"] = args.min_factor
    if args.exclude_interpolated_from_thresholds is not None:
        overrides["exclude_interpolated_from_thresholds"] = (
            args.exclude_interpolated_from_thresholds
        )
    if args.use_hysteresis_labels is not None:
        overrides["use_hysteresis_labels"] = args.use_hysteresis_labels
    if args.hysteresis_ratio is not None:
        overrides["hysteresis_ratio"] = args.hysteresis_ratio
    if args.timestamp_column:
        overrides["timestamp_column"] = args.timestamp_column
    if args.weight_column:
        overrides["weight_column"] = args.weight_column
    if args.interpolate_transpiration_during_events is not None:
        overrides["interpolate_transpiration_during_events"] = (
            args.interpolate_transpiration_during_events
        )
    if args.fix_water_balance is not None:
        overrides["fix_water_balance"] = args.fix_water_balance
    if args.balance_scale_min is not None:
        overrides["water_balance_scale_min"] = args.balance_scale_min
    if args.balance_scale_max is not None:
        overrides["water_balance_scale_max"] = args.balance_scale_max
    return overrides


def run_pipeline(
    cfg: load_cell_config.PipelineConfig,
    include_excel: bool = False,
    write_output: bool = True,
    logger: logging.Logger | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Execute the load-cell pipeline and optionally persist outputs."""

    log = logger or logging.getLogger(__name__)
    if cfg.input_path is None:
        raise ValueError("input_path must be specified.")
    if write_output and cfg.output_path is None:
        raise ValueError("output_path must be specified to write results.")

    df = io.read_load_cell_csv(
        cfg.input_path,
        timestamp_column=cfg.timestamp_column,
        weight_column=cfg.weight_column,
    )

    df = preprocessing.detect_and_correct_outliers(
        df,
        k_outlier=cfg.k_outlier,
        max_spike_width_sec=cfg.max_spike_width_sec,
    )
    df = preprocessing.smooth_weight(
        df,
        method=cfg.smooth_method,
        window_sec=cfg.smooth_window_sec,
        poly_order=cfg.poly_order,
        derivative_method=cfg.derivative_method,
    )

    use_auto = (
        cfg.use_auto_thresholds
        or cfg.irrigation_step_threshold_kg is None
        or cfg.drainage_step_threshold_kg is None
    )
    if use_auto:
        valid_mask = None
        if cfg.exclude_interpolated_from_thresholds and "is_interpolated" in df.columns:
            valid_mask = ~df["is_interpolated"].fillna(False)
        irrigation_threshold, drainage_threshold = thresholds.auto_detect_step_thresholds(
            df["dW_smooth_kg_s"],
            min_pos_events=cfg.min_pos_events,
            min_neg_events=cfg.min_neg_events,
            k_tail=cfg.k_tail,
            min_factor=cfg.min_factor,
            valid_mask=valid_mask,
            logger=log,
        )
    else:
        irrigation_threshold = float(cfg.irrigation_step_threshold_kg)
        drainage_threshold = float(cfg.drainage_step_threshold_kg)

    if cfg.use_hysteresis_labels:
        df = events.label_points_by_derivative_hysteresis(
            df,
            irrigation_threshold,
            drainage_threshold,
            hysteresis_ratio=cfg.hysteresis_ratio,
        )
    else:
        df = events.label_points_by_derivative(
            df,
            irrigation_threshold,
            drainage_threshold,
        )
    df, events_df = events.group_events(
        df,
        min_event_duration_sec=cfg.min_event_duration_sec,
    )

    if "label" in df.columns:
        labels = df["label"].fillna("baseline").astype(str)
        df["irrigation_time_sec_raw"] = (labels == "irrigation").astype("int64")
        df["drainage_time_sec_raw"] = (labels == "drainage").astype("int64")
        if "event_id" in df.columns:
            is_event = df["event_id"].notna()
            df["irrigation_time_sec"] = ((labels == "irrigation") & is_event).astype(
                "int64"
            )
            df["drainage_time_sec"] = ((labels == "drainage") & is_event).astype(
                "int64"
            )

    merged_events_df = events_df
    event_id_map: dict[int, int] = {}
    if cfg.merge_irrigation_gap_sec is not None:
        merged_events_df, event_id_map = events.merge_close_events_with_df(
            df,
            events_df,
            gap_threshold_sec=cfg.merge_irrigation_gap_sec,
            event_type="irrigation",
        )
        if "event_id" in df.columns:
            df["event_id_merged"] = df["event_id"].map(event_id_map).astype("Int64")

    df = fluxes.compute_fluxes_per_second(
        df,
        interpolate_transpiration_during_events=(
            cfg.interpolate_transpiration_during_events
        ),
        fix_water_balance=cfg.fix_water_balance,
        min_transpiration_scale=cfg.water_balance_scale_min,
        max_transpiration_scale=cfg.water_balance_scale_max,
    )

    if write_output and cfg.output_path:
        frames: dict[str, pd.DataFrame] = {"1s": df}
        frames["10s"] = aggregation.resample_flux_timeseries(df, "10s")
        frames["1min"] = aggregation.resample_flux_timeseries(df, "1min")
        frames["1h"] = aggregation.resample_flux_timeseries(df, "1h")
        frames["daily"] = aggregation.daily_summary(
            df,
            events_df=merged_events_df,
            metadata={
                "irrigation_threshold": irrigation_threshold,
                "drainage_threshold": drainage_threshold,
            },
        )
        io.write_multi_resolution_results(
            frames,
            cfg.output_path,
            include_excel=include_excel,
        )

    stats = _summarize_stats(df, merged_events_df)
    log.info("Processed %d samples (%s to %s)", len(df), df.index.min(), df.index.max())
    log.info(
        "Irrigation events: %d (%.3f kg total)",
        stats["irrigation_event_count"],
        stats["total_irrigation_kg"],
    )
    log.info(
        "Drainage events: %d (%.3f kg total)",
        stats["drainage_event_count"],
        stats["total_drainage_kg"],
    )
    log.info("Total transpiration: %.3f kg", stats["total_transpiration_kg"])
    log.info("Final water balance error: %.4f kg", stats["final_balance_error_kg"])

    metadata = {
        "irrigation_threshold": irrigation_threshold,
        "drainage_threshold": drainage_threshold,
        "stats": stats,
        "events": merged_events_df,
        "events_merged": merged_events_df,
        "events_raw": events_df,
        "event_id_map": event_id_map,
    }
    return df, events_df, metadata


def _summarize_stats(df: pd.DataFrame, events_df: pd.DataFrame) -> dict[str, Any]:
    """Compute aggregate statistics for reporting."""

    irrigation_events = (
        events_df[events_df["event_type"] == "irrigation"]
        if not events_df.empty
        else events_df
    )
    drainage_events = (
        events_df[events_df["event_type"] == "drainage"]
        if not events_df.empty
        else events_df
    )

    def safe_tail(series: pd.Series) -> float:
        return float(series.iloc[-1]) if not series.empty else 0.0

    return {
        "irrigation_event_count": int(len(irrigation_events)) if not events_df.empty else 0,
        "drainage_event_count": int(len(drainage_events)) if not events_df.empty else 0,
        "total_irrigation_kg": safe_tail(df.get("cum_irrigation_kg", pd.Series(dtype=float))),
        "total_drainage_kg": safe_tail(df.get("cum_drainage_kg", pd.Series(dtype=float))),
        "total_transpiration_kg": safe_tail(
            df.get("cum_transpiration_kg", pd.Series(dtype=float))
        ),
        "final_balance_error_kg": float(
            df["water_balance_error_kg"].iloc[-1]
            if "water_balance_error_kg" in df.columns
            else 0.0
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for command-line execution."""

    args = build_parser().parse_args(list(argv) if argv is not None else None)
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    overrides = _apply_overrides(args)
    cfg = load_cell_config.load_config(args.config, overrides=overrides)
    run_pipeline(
        cfg,
        include_excel=args.excel,
        write_output=True,
        logger=logging.getLogger("loadcell_pipeline"),
    )
    return 0
