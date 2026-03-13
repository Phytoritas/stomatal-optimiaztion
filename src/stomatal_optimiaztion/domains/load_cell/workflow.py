"""Batch workflow runner for daily load-cell datasets."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from collections.abc import Iterable, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from . import aggregation
from . import cli
from . import config
from . import io

LOADCELL_MAP_RAW: dict[int, str] = {
    1: "M000.0 N",
    2: "M001.0 N",
    3: "M002.0 N",
    4: "M003.0 Kg",
    5: "M004.0 Kg",
    6: "M005.0 Kg",
}

ENV_COLUMNS_CANDIDATES = [
    "air_temp_c",
    "air_rh_percent",
    "dewpoint_c",
    "air_pressure_mb",
    "weather_temp_c",
    "wind_speed_m_s",
    "weather_pressure_mb",
    "tensiometer_4_hp",
    "tensiometer_5_hp",
]


def _safe_slug(text: str) -> str:
    sanitized = text.strip().replace(" ", "")
    sanitized = sanitized.replace(":", "_").replace("/", "_").replace("\\", "_")
    sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "_", sanitized)
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized or "run"


def _format_number(value: Any) -> str:
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.6g}".replace(".", "p")
    return _safe_slug(str(value))


def config_signature(cfg: config.PipelineConfig) -> tuple[str, str]:
    """Build a human-readable slug and stable short hash for a config."""

    data = cfg.to_dict()
    for io_key in ["input_path", "output_path", "timestamp_column", "weight_column"]:
        data.pop(io_key, None)

    blob = json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    digest = hashlib.sha1(blob).hexdigest()[:8]

    parts = [
        f"sm{_safe_slug(str(cfg.smooth_method))}",
        f"w{_format_number(cfg.smooth_window_sec)}",
        f"po{_format_number(cfg.poly_order)}",
        f"kout{_format_number(cfg.k_outlier)}",
        f"sp{_format_number(cfg.max_spike_width_sec)}",
        f"deriv{_safe_slug(str(cfg.derivative_method))}",
        f"kt{_format_number(cfg.k_tail)}",
        f"mf{_format_number(cfg.min_factor)}",
        f"dur{_format_number(cfg.min_event_duration_sec)}",
        f"merge{_format_number(cfg.merge_irrigation_gap_sec)}",
        f"bfix{_format_number(cfg.fix_water_balance)}",
        f"bmin{_format_number(cfg.water_balance_scale_min)}",
        f"bmax{_format_number(cfg.water_balance_scale_max)}",
    ]
    return "_".join(parts), digest


def _read_interpolated_full(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "timestamp" not in df.columns:
        raise KeyError(f"Missing 'timestamp' column in {path}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df.dropna(subset=["timestamp"]).set_index("timestamp").sort_index()


def _read_csv_header(path: Path) -> list[str]:
    path = Path(path)
    with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
        header = handle.readline().strip()
    return [column.strip() for column in header.split(",")] if header else []


def _infer_weight_column(
    path: Path,
    loadcell: int,
    *,
    prefer_canonical: bool = True,
) -> str:
    """Infer the weight column name for a given daily CSV and loadcell id."""

    columns = set(_read_csv_header(path))
    canonical = f"loadcell_{int(loadcell)}_kg"
    legacy = LOADCELL_MAP_RAW[int(loadcell)]

    if prefer_canonical and canonical in columns:
        return canonical
    if legacy in columns:
        return legacy
    if canonical in columns:
        return canonical
    raise KeyError(
        f"Could not find weight column for loadcell {loadcell} in {path.name}. "
        f"Tried: '{canonical}', '{legacy}'."
    )


def _resample_numeric_mean(df_1s: pd.DataFrame, rule: str) -> pd.DataFrame:
    if df_1s.empty:
        return pd.DataFrame()
    grouped = df_1s.resample(rule)
    out = grouped.mean(numeric_only=True)
    out.index.name = "timestamp"
    out["n_samples"] = grouped.size().astype("int64")
    return out


def _write_environment_once(
    date_dir: Path,
    df_interpolated_1s: pd.DataFrame,
    include_excel: bool = False,
) -> None:
    env_cols = [
        column for column in ENV_COLUMNS_CANDIDATES if column in df_interpolated_1s.columns
    ]
    if not env_cols:
        return

    env_1s = df_interpolated_1s[env_cols].copy()
    env_dir = date_dir / "env"
    env_dir.mkdir(parents=True, exist_ok=True)

    frames: dict[str, pd.DataFrame] = {"1s": env_1s}
    frames["10s"] = _resample_numeric_mean(env_1s, "10s")
    frames["1min"] = _resample_numeric_mean(env_1s, "1min")
    frames["1h"] = _resample_numeric_mean(env_1s, "1h")
    frames["daily"] = _resample_numeric_mean(env_1s, "1D")
    if "daily" in frames and not frames["daily"].empty:
        frames["daily"].index.name = "day"

    io.write_multi_resolution_results(
        frames,
        env_dir / "environment.csv",
        include_excel=include_excel,
    )


def _join_substrate_sensors(
    df_result_1s: pd.DataFrame,
    df_interpolated_1s: pd.DataFrame,
    loadcell: int,
) -> pd.DataFrame:
    df_out = df_result_1s.copy()
    ec_col = f"ec_{loadcell}_ds"
    moist_col = f"moisture_{loadcell}_percent"

    if ec_col in df_interpolated_1s.columns:
        df_out["substrate_ec_ds"] = df_interpolated_1s[ec_col].reindex(df_out.index)
    if moist_col in df_interpolated_1s.columns:
        df_out["substrate_moisture_percent"] = df_interpolated_1s[moist_col].reindex(
            df_out.index
        )
    return df_out


def _common_filenames(
    interpolated_dir: Path,
    raw_dir: Path,
    variants: str,
) -> list[str]:
    files_interpolated = {path.name for path in interpolated_dir.glob("*.csv")}
    files_raw = {path.name for path in raw_dir.glob("*.csv")}

    if variants == "interpolated":
        return sorted(files_interpolated)
    if variants == "raw":
        return sorted(files_raw)
    return sorted(files_interpolated & files_raw)


def run_workflow(
    interpolated_dir: Path,
    raw_dir: Path,
    out_root: Path,
    config_paths: list[Path],
    variants: str = "both",
    loadcells: Iterable[int] = (1, 2, 3, 4, 5, 6),
    dates: list[str] | None = None,
    include_excel: bool = False,
    log_level: str = "WARNING",
) -> None:
    """Run the batch workflow across matched daily files and configs."""

    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.WARNING),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger("loadcell_workflow")

    configs: list[tuple[Path, config.PipelineConfig, str]] = []
    for path in config_paths:
        cfg = config.load_config(path)
        slug, digest = config_signature(cfg)
        configs.append((path, cfg, f"{slug}__{digest}"))

    all_files = _common_filenames(interpolated_dir, raw_dir, variants)
    if dates:
        wanted = set(dates)
        all_files = [filename for filename in all_files if filename in wanted]

    if not all_files:
        raise SystemExit("No input files matched (check directories / --dates).")

    variant_order = ["interpolated", "raw"] if variants == "both" else [variants]
    for filename in all_files:
        date_key = Path(filename).stem
        date_dir = out_root / date_key
        date_dir.mkdir(parents=True, exist_ok=True)

        interpolated_path = interpolated_dir / filename
        df_interpolated = (
            _read_interpolated_full(interpolated_path)
            if interpolated_path.exists()
            else pd.DataFrame()
        )
        if not df_interpolated.empty:
            _write_environment_once(
                date_dir,
                df_interpolated,
                include_excel=include_excel,
            )

        for variant in variant_order:
            for cfg_path, base_cfg, cfg_id in configs:
                run_dir = date_dir / "results" / variant / cfg_id
                run_dir.mkdir(parents=True, exist_ok=True)
                (run_dir / "config_used.yaml").write_text(
                    Path(cfg_path).read_text(encoding="utf-8"),
                    encoding="utf-8",
                )

                for loadcell in loadcells:
                    if variant == "interpolated":
                        input_path = interpolated_dir / filename
                        weight_column = _infer_weight_column(
                            input_path,
                            int(loadcell),
                            prefer_canonical=True,
                        )
                    else:
                        input_path = raw_dir / filename
                        weight_column = _infer_weight_column(
                            input_path,
                            int(loadcell),
                            prefer_canonical=True,
                        )

                    cfg_run = config.PipelineConfig(**asdict(base_cfg))
                    cfg_run.input_path = input_path
                    cfg_run.output_path = None
                    cfg_run.timestamp_column = "timestamp"
                    cfg_run.weight_column = weight_column

                    df_1s, events_df, metadata = cli.run_pipeline(
                        cfg_run,
                        include_excel=False,
                        write_output=False,
                        logger=logger,
                    )

                    if not df_interpolated.empty:
                        df_1s = _join_substrate_sensors(
                            df_1s,
                            df_interpolated,
                            int(loadcell),
                        )

                    merged_events_df = metadata.get("events_merged", metadata.get("events", events_df))
                    frames: dict[str, pd.DataFrame] = {"1s": df_1s}
                    frames["10s"] = aggregation.resample_flux_timeseries(df_1s, "10s")
                    frames["1min"] = aggregation.resample_flux_timeseries(df_1s, "1min")
                    frames["1h"] = aggregation.resample_flux_timeseries(df_1s, "1h")
                    frames["daily"] = aggregation.daily_summary(
                        df_1s,
                        events_df=merged_events_df,
                        metadata={
                            "irrigation_threshold": metadata.get("irrigation_threshold"),
                            "drainage_threshold": metadata.get("drainage_threshold"),
                        },
                    )

                    io.write_multi_resolution_results(
                        frames,
                        run_dir / f"loadcell_{int(loadcell)}.csv",
                        include_excel=include_excel,
                    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Batch workflow: per-day env once + per-config results for loadcells.",
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
        help="Directory containing raw (non-interpolated) daily CSVs.",
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=Path("runs"),
        help="Root output directory.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        action="append",
        default=[],
        help="Config YAML (repeatable). Default: ./config.yaml",
    )
    parser.add_argument(
        "--variants",
        choices=["interpolated", "raw", "both"],
        default="both",
        help="Which datasets to process.",
    )
    parser.add_argument(
        "--loadcells",
        type=int,
        nargs="+",
        default=[1, 2, 3, 4, 5, 6],
        help="Loadcell ids to process.",
    )
    parser.add_argument(
        "--dates",
        nargs="*",
        help="Optional list of filenames (e.g., 2025-06-17.csv). If omitted, process all matched files.",
    )
    parser.add_argument("--excel", action="store_true", help="Also write Excel outputs.")
    parser.add_argument(
        "--log-level",
        type=str,
        default="WARNING",
        help="Logging level (DEBUG, INFO, WARNING, ...).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for batch workflow execution."""

    args = build_parser().parse_args(list(argv) if argv is not None else None)
    config_paths = args.config if args.config else [Path("config.yaml")]
    run_workflow(
        interpolated_dir=args.interpolated_dir,
        raw_dir=args.raw_dir,
        out_root=args.out_root,
        config_paths=config_paths,
        variants=args.variants,
        loadcells=args.loadcells,
        dates=args.dates,
        include_excel=args.excel,
        log_level=args.log_level,
    )
    return 0
