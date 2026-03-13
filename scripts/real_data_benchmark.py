#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stomatal_optimiaztion.domains.load_cell import (  # noqa: E402
    PipelineConfig,
    load_config,
    run_pipeline,
)

LOADCELL_MAP_RAW: dict[int, str] = {
    1: "M000.0 N",
    2: "M001.0 N",
    3: "M002.0 N",
    4: "M003.0 Kg",
    5: "M004.0 Kg",
    6: "M005.0 Kg",
}


def _safe_tail(df: pd.DataFrame, column: str) -> float:
    if column not in df.columns or df.empty:
        return 0.0
    return float(df[column].iloc[-1])


def _summarize_run(
    df: pd.DataFrame,
    events_df: pd.DataFrame,
    metadata: dict[str, Any],
    *,
    input_path: Path,
    weight_column: str,
    tag: str,
    loadcell: int,
    runtime_sec: float,
) -> dict[str, Any]:
    stats = metadata.get("stats", {})
    irrigation_threshold = float(metadata.get("irrigation_threshold", float("nan")))
    drainage_threshold = float(metadata.get("drainage_threshold", float("nan")))

    merged_events = metadata.get("events_merged", metadata.get("events", events_df))
    if merged_events is None:
        merged_events = events_df

    irrigation_events = (
        merged_events[merged_events["event_type"] == "irrigation"]
        if isinstance(merged_events, pd.DataFrame) and not merged_events.empty
        else pd.DataFrame()
    )
    drainage_events = (
        merged_events[merged_events["event_type"] == "drainage"]
        if isinstance(merged_events, pd.DataFrame) and not merged_events.empty
        else pd.DataFrame()
    )

    return {
        "tag": tag,
        "file": input_path.name,
        "path": str(input_path),
        "loadcell": int(loadcell),
        "weight_column": weight_column,
        "n_samples": int(len(df)),
        "start_time": df.index.min(),
        "end_time": df.index.max(),
        "irrigation_threshold": irrigation_threshold,
        "drainage_threshold": drainage_threshold,
        "irrigation_event_count": (
            int(len(irrigation_events)) if not irrigation_events.empty else 0
        ),
        "drainage_event_count": int(len(drainage_events)) if not drainage_events.empty else 0,
        "total_irrigation_kg": _safe_tail(df, "cum_irrigation_kg"),
        "total_drainage_kg": _safe_tail(df, "cum_drainage_kg"),
        "total_transpiration_kg": _safe_tail(df, "cum_transpiration_kg"),
        "final_balance_error_kg": float(stats.get("final_balance_error_kg", 0.0)),
        "mean_abs_balance_error_kg": (
            float(df["water_balance_error_kg"].abs().mean())
            if "water_balance_error_kg" in df.columns
            else 0.0
        ),
        "interpolated_frac": (
            float(df["is_interpolated"].mean()) if "is_interpolated" in df.columns else 0.0
        ),
        "outlier_frac": float(df["is_outlier"].mean()) if "is_outlier" in df.columns else 0.0,
        "transpiration_scale": (
            float(df["transpiration_scale"].iloc[-1]) if "transpiration_scale" in df.columns else 1.0
        ),
        "runtime_sec": float(runtime_sec),
    }


def _run_one_with_df(
    input_path: Path,
    base_cfg: PipelineConfig,
    *,
    weight_column: str,
    tag: str,
    loadcell: int,
    logger: logging.Logger,
) -> tuple[dict[str, Any], pd.DataFrame]:
    started = time.perf_counter()

    cfg = PipelineConfig(**asdict(base_cfg))
    cfg.input_path = Path(input_path)
    cfg.output_path = None
    cfg.timestamp_column = "timestamp"
    cfg.weight_column = weight_column

    df, events_df, metadata = run_pipeline(
        cfg,
        include_excel=False,
        write_output=False,
        logger=logger,
    )
    runtime_sec = time.perf_counter() - started

    row = _summarize_run(
        df,
        events_df,
        metadata,
        input_path=input_path,
        weight_column=weight_column,
        tag=tag,
        loadcell=loadcell,
        runtime_sec=runtime_sec,
    )
    return row, df


def _sum(df: pd.DataFrame, column: str) -> float:
    if column not in df.columns or df.empty:
        return 0.0
    return float(df[column].sum())


def run_real_data_benchmark(
    *,
    dir_interpolated: Path = Path("data/preprocessed_csv_interpolated"),
    dir_raw: Path = Path("data/preprocessed_csv"),
    config_path: Path | None = Path("config.yaml"),
    out_dir: Path = Path("real_data_test"),
    loadcells: list[int] | tuple[int, ...] = (1, 2, 3, 4, 5, 6),
    log_level: str = "WARNING",
) -> dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.WARNING),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger("real_data_benchmark")
    logger.setLevel(getattr(logging, log_level.upper(), logging.WARNING))

    base_cfg = load_config(config_path) if config_path else PipelineConfig()
    files_interpolated = {path.name: path for path in Path(dir_interpolated).glob("*.csv")}
    files_raw = {path.name: path for path in Path(dir_raw).glob("*.csv")}
    common = sorted(set(files_interpolated) & set(files_raw))
    if not common:
        raise SystemExit("No common CSV filenames between the two directories.")

    rows: list[dict[str, Any]] = []
    overlap_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    total_runs = len(common) * len(loadcells) * 2
    done = 0

    for name in common:
        interpolated_path = files_interpolated[name]
        raw_path = files_raw[name]
        for loadcell in loadcells:
            df_interpolated: pd.DataFrame | None = None
            df_raw: pd.DataFrame | None = None

            try:
                row_interpolated, df_interpolated = _run_one_with_df(
                    interpolated_path,
                    base_cfg,
                    weight_column=f"loadcell_{loadcell}_kg",
                    tag="interpolated",
                    loadcell=loadcell,
                    logger=logger,
                )
                rows.append(row_interpolated)
            except Exception as exc:  # noqa: BLE001
                failures.append(
                    {
                        "tag": "interpolated",
                        "file": name,
                        "loadcell": int(loadcell),
                        "error": repr(exc),
                    }
                )
            done += 1

            try:
                row_raw, df_raw = _run_one_with_df(
                    raw_path,
                    base_cfg,
                    weight_column=LOADCELL_MAP_RAW[int(loadcell)],
                    tag="raw",
                    loadcell=loadcell,
                    logger=logger,
                )
                rows.append(row_raw)
            except Exception as exc:  # noqa: BLE001
                failures.append(
                    {
                        "tag": "raw",
                        "file": name,
                        "loadcell": int(loadcell),
                        "error": repr(exc),
                    }
                )
            done += 1

            if isinstance(df_interpolated, pd.DataFrame) and isinstance(df_raw, pd.DataFrame):
                overlap_start = max(df_interpolated.index.min(), df_raw.index.min())
                overlap_end = min(df_interpolated.index.max(), df_raw.index.max())
                if (
                    pd.notna(overlap_start)
                    and pd.notna(overlap_end)
                    and overlap_start <= overlap_end
                ):
                    di = df_interpolated.loc[overlap_start:overlap_end]
                    dr = df_raw.loc[overlap_start:overlap_end]
                    overlap_rows.append(
                        {
                            "file": name,
                            "loadcell": int(loadcell),
                            "overlap_start": overlap_start,
                            "overlap_end": overlap_end,
                            "overlap_n_samples": int(min(len(di), len(dr))),
                            "irrigation_kg_interp": _sum(di, "irrigation_kg_s"),
                            "drainage_kg_interp": _sum(di, "drainage_kg_s"),
                            "transpiration_kg_interp": _sum(di, "transpiration_kg_s"),
                            "irrigation_kg_raw": _sum(dr, "irrigation_kg_s"),
                            "drainage_kg_raw": _sum(dr, "drainage_kg_s"),
                            "transpiration_kg_raw": _sum(dr, "transpiration_kg_s"),
                            "diff_irrigation_kg": _sum(di, "irrigation_kg_s")
                            - _sum(dr, "irrigation_kg_s"),
                            "diff_drainage_kg": _sum(di, "drainage_kg_s")
                            - _sum(dr, "drainage_kg_s"),
                            "diff_transpiration_kg": _sum(di, "transpiration_kg_s")
                            - _sum(dr, "transpiration_kg_s"),
                            "mean_abs_balance_error_kg_interp": (
                                float(di["water_balance_error_kg"].abs().mean())
                                if "water_balance_error_kg" in di.columns and not di.empty
                                else 0.0
                            ),
                            "mean_abs_balance_error_kg_raw": (
                                float(dr["water_balance_error_kg"].abs().mean())
                                if "water_balance_error_kg" in dr.columns and not dr.empty
                                else 0.0
                            ),
                        }
                    )

        if done % max(2 * len(loadcells), 1) == 0:
            print(f"Progress: {done}/{total_runs} runs")

    summary_path = out_dir / "summary_runs.csv"
    summary = pd.DataFrame(rows)
    summary.to_csv(summary_path, index=False)

    comparison_path: Path | None = None
    if not summary.empty:
        interpolated_df = summary[summary["tag"] == "interpolated"].copy()
        raw_df = summary[summary["tag"] == "raw"].copy()
        merged = interpolated_df.merge(raw_df, on=["file", "loadcell"], suffixes=("_interp", "_raw"), how="inner")
        for column in [
            "total_irrigation_kg",
            "total_drainage_kg",
            "total_transpiration_kg",
            "final_balance_error_kg",
            "irrigation_event_count",
            "drainage_event_count",
            "runtime_sec",
            "interpolated_frac",
        ]:
            merged[f"diff_{column}"] = merged[f"{column}_interp"] - merged[f"{column}_raw"]
        comparison_path = out_dir / "comparison.csv"
        merged.to_csv(comparison_path, index=False)

        abs_drain = merged["diff_total_drainage_kg"].abs()
        abs_irrig = merged["diff_total_irrigation_kg"].abs()
        abs_trans = merged["diff_total_transpiration_kg"].abs()
        print("\n=== Summary (abs diff) ===")
        print("files:", len(common), "loadcells:", len(loadcells))
        print(
            "Irrigation kg | median:",
            float(abs_irrig.median()),
            "p90:",
            float(abs_irrig.quantile(0.9)),
        )
        print(
            "Drainage   kg | median:",
            float(abs_drain.median()),
            "p90:",
            float(abs_drain.quantile(0.9)),
        )
        print(
            "Transp.    kg | median:",
            float(abs_trans.median()),
            "p90:",
            float(abs_trans.quantile(0.9)),
        )

    overlap_path: Path | None = None
    overlap_df = pd.DataFrame(overlap_rows)
    if not overlap_df.empty:
        overlap_path = out_dir / "comparison_overlap.csv"
        overlap_df.to_csv(overlap_path, index=False)

        abs_irrig = overlap_df["diff_irrigation_kg"].abs()
        abs_drain = overlap_df["diff_drainage_kg"].abs()
        abs_trans = overlap_df["diff_transpiration_kg"].abs()
        print("\n=== Summary (abs diff, overlap window only) ===")
        print("rows:", int(len(overlap_df)))
        print(
            "Irrigation kg | median:",
            float(abs_irrig.median()),
            "p90:",
            float(abs_irrig.quantile(0.9)),
        )
        print(
            "Drainage   kg | median:",
            float(abs_drain.median()),
            "p90:",
            float(abs_drain.quantile(0.9)),
        )
        print(
            "Transp.    kg | median:",
            float(abs_trans.median()),
            "p90:",
            float(abs_trans.quantile(0.9)),
        )

    failures_path: Path | None = None
    if failures:
        failures_path = out_dir / "failures.csv"
        pd.DataFrame(failures).to_csv(failures_path, index=False)
        print(f"\nFailures: {len(failures)} (see {failures_path})")
    else:
        print("\nNo failures.")

    return {
        "common_files": common,
        "summary_path": summary_path,
        "comparison_path": comparison_path,
        "overlap_path": overlap_path,
        "failures_path": failures_path,
        "row_count": int(len(rows)),
        "failure_count": int(len(failures)),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Batch benchmark for real greenhouse data (interpolated vs raw)."
    )
    parser.add_argument(
        "--interpolated-dir",
        type=Path,
        default=Path("data/preprocessed_csv_interpolated"),
        help="Directory containing interpolated daily CSVs.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/preprocessed_csv"),
        help="Directory containing raw daily CSVs.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Pipeline config YAML path.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("real_data_test"),
        help="Output directory for benchmark CSVs.",
    )
    parser.add_argument(
        "--loadcells",
        type=int,
        nargs="+",
        default=[1, 2, 3, 4, 5, 6],
        help="Loadcell ids to benchmark.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="WARNING",
        help="Logging level (DEBUG, INFO, WARNING, ...).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_real_data_benchmark(
        dir_interpolated=args.interpolated_dir,
        dir_raw=args.raw_dir,
        config_path=args.config,
        out_dir=args.out_dir,
        loadcells=args.loadcells,
        log_level=args.log_level,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
