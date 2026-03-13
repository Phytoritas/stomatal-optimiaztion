"""Parameter sweep helpers for load-cell workflow comparison."""

from __future__ import annotations

import argparse
import itertools
import json
import logging
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from . import config
from . import workflow


def _parse_value(raw: str) -> Any:
    text = raw.strip()
    if text == "":
        return text

    lowered = text.lower()
    if lowered in {"none", "null"}:
        return None
    if lowered in {"true", "false"}:
        return lowered == "true"

    try:
        if lowered.startswith("0") and len(lowered) > 1 and lowered[1].isdigit():
            raise ValueError
        return int(text)
    except ValueError:
        pass

    try:
        return float(text)
    except ValueError:
        return text


def _parse_grid_arg(arg: str) -> tuple[str, list[Any]]:
    if "=" not in arg:
        raise ValueError(f"Invalid --grid '{arg}'. Expected KEY=V1,V2,...")

    key, values_str = arg.split("=", 1)
    key = key.strip()
    if not key:
        raise ValueError(f"Invalid --grid '{arg}'. Empty key.")

    values = [_parse_value(value) for value in values_str.split(",")]
    values = [value for value in values if not (isinstance(value, str) and value == "")]
    if not values:
        raise ValueError(f"Invalid --grid '{arg}'. No values.")
    return key, values


def _generate_configs(
    base_cfg: config.PipelineConfig,
    grid: dict[str, list[Any]],
) -> list[tuple[config.PipelineConfig, dict[str, Any]]]:
    keys = list(grid.keys())
    values = [grid[key] for key in keys]

    base_dict = asdict(base_cfg)
    out: list[tuple[config.PipelineConfig, dict[str, Any]]] = []
    for combo in itertools.product(*values):
        overrides = dict(zip(keys, combo))
        cfg = config.PipelineConfig(**base_dict)
        for key, value in overrides.items():
            if not hasattr(cfg, key):
                raise KeyError(f"PipelineConfig has no field '{key}' (from --grid).")
            setattr(cfg, key, value)
        out.append((cfg, overrides))
    return out


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    try:
        import yaml  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "PyYAML is required for sweep config generation. Install 'pyyaml'."
        ) from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=True)


def _collect_runs(out_root: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    cfg_cache: dict[str, dict[str, Any]] = {}

    for date_dir in sorted(path for path in out_root.iterdir() if path.is_dir()):
        results_dir = date_dir / "results"
        if not results_dir.exists():
            continue
        date_key = date_dir.name

        for variant_dir in sorted(path for path in results_dir.iterdir() if path.is_dir()):
            variant = variant_dir.name
            for cfg_dir in sorted(path for path in variant_dir.iterdir() if path.is_dir()):
                cfg_id = cfg_dir.name

                if cfg_id not in cfg_cache:
                    cfg_used = cfg_dir / "config_used.yaml"
                    if cfg_used.exists():
                        try:
                            loaded_cfg = config.load_config(cfg_used)
                            cfg_cache[cfg_id] = loaded_cfg.to_dict()
                        except Exception:  # noqa: BLE001
                            cfg_cache[cfg_id] = {}
                    else:
                        cfg_cache[cfg_id] = {}

                for daily_path in sorted(cfg_dir.glob("loadcell_*_daily.csv")):
                    df = pd.read_csv(daily_path)
                    loadcell = int(daily_path.stem.split("_")[1])
                    for _, row in df.iterrows():
                        out_row = {
                            "date": date_key,
                            "variant": variant,
                            "config_id": cfg_id,
                            "loadcell": loadcell,
                        }
                        out_row.update(row.to_dict())

                        cfg_dict = cfg_cache.get(cfg_id, {})
                        for cfg_key in [
                            "smooth_method",
                            "smooth_window_sec",
                            "poly_order",
                            "k_outlier",
                            "max_spike_width_sec",
                            "derivative_method",
                            "use_auto_thresholds",
                            "k_tail",
                            "min_factor",
                            "min_event_duration_sec",
                            "merge_irrigation_gap_sec",
                            "exclude_interpolated_from_thresholds",
                            "use_hysteresis_labels",
                            "hysteresis_ratio",
                            "fix_water_balance",
                            "water_balance_scale_min",
                            "water_balance_scale_max",
                        ]:
                            if cfg_key in cfg_dict:
                                out_row[f"cfg_{cfg_key}"] = cfg_dict[cfg_key]

                        rows.append(out_row)

    return pd.DataFrame(rows)


def _rank_configs(df_runs: pd.DataFrame) -> pd.DataFrame:
    if df_runs.empty:
        return pd.DataFrame()

    df = df_runs.copy()
    for column in [
        "mean_abs_balance_error_kg",
        "final_balance_error_kg",
        "transpiration_scale",
        "irrigation_event_count",
        "drainage_event_count",
    ]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    df["abs_final_balance_error_kg"] = df.get("final_balance_error_kg", 0.0).abs()
    df["abs_transpiration_scale_minus1"] = (
        df.get("transpiration_scale", 1.0) - 1.0
    ).abs()
    df["event_count"] = df.get("irrigation_event_count", 0.0).fillna(0.0) + df.get(
        "drainage_event_count", 0.0
    ).fillna(0.0)

    grouped = df.groupby(["variant", "config_id"], dropna=False)
    aggregated = grouped.agg(
        n_rows=("date", "count"),
        n_days=("date", "nunique"),
        n_loadcells=("loadcell", "nunique"),
        mean_abs_balance_error_kg_mean=("mean_abs_balance_error_kg", "mean"),
        abs_final_balance_error_kg_mean=("abs_final_balance_error_kg", "mean"),
        abs_transpiration_scale_minus1_mean=("abs_transpiration_scale_minus1", "mean"),
        event_count_mean=("event_count", "mean"),
        total_irrigation_kg_mean=("total_irrigation_kg", "mean"),
        total_drainage_kg_mean=("total_drainage_kg", "mean"),
        total_transpiration_kg_mean=("total_transpiration_kg", "mean"),
    ).reset_index()

    aggregated["score"] = (
        aggregated["mean_abs_balance_error_kg_mean"].fillna(0.0)
        + 0.1 * aggregated["abs_final_balance_error_kg_mean"].fillna(0.0)
        + 0.02 * aggregated["abs_transpiration_scale_minus1_mean"].fillna(0.0)
        + 0.00001 * aggregated["event_count_mean"].fillna(0.0)
    )
    aggregated = aggregated.sort_values(
        [
            "variant",
            "score",
            "mean_abs_balance_error_kg_mean",
            "abs_final_balance_error_kg_mean",
            "abs_transpiration_scale_minus1_mean",
            "event_count_mean",
        ],
        ascending=[True, True, True, True, True, True],
    )
    aggregated["rank"] = aggregated.groupby("variant").cumcount() + 1
    return aggregated


def run_sweep(
    out_root: Path,
    interpolated_dir: Path,
    raw_dir: Path,
    base_config_path: Path,
    grid_args: list[str],
    variants: str,
    loadcells: list[int],
    dates: list[str] | None,
    include_excel: bool,
    log_level: str,
) -> None:
    """Generate config variants, run the workflow, and rank results."""

    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.WARNING),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    base_cfg = config.load_config(base_config_path)

    grid: dict[str, list[Any]] = {}
    for grid_arg in grid_args:
        key, values = _parse_grid_arg(grid_arg)
        grid[key] = values

    if not grid:
        grid = {
            "smooth_window_sec": [11, 14, 17],
            "k_tail": [4.0, 4.5, 5.0],
        }

    generated = _generate_configs(base_cfg, grid)

    cfg_dir = out_root / "_sweep" / "configs"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_paths: list[Path] = []
    cfg_rows: list[dict[str, Any]] = []

    for cfg, overrides in generated:
        slug, digest = workflow.config_signature(cfg)
        cfg_id = f"{slug}__{digest}"
        cfg_path = cfg_dir / f"{cfg_id}.yaml"
        _write_yaml(cfg_path, cfg.to_dict())
        cfg_paths.append(cfg_path)
        cfg_rows.append({"config_id": cfg_id, "path": str(cfg_path), **overrides})

    sweep_dir = out_root / "_sweep"
    sweep_dir.mkdir(parents=True, exist_ok=True)
    (sweep_dir / "grid.json").write_text(
        json.dumps(
            {"base_config": str(base_config_path), "grid": grid},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    pd.DataFrame(cfg_rows).to_csv(sweep_dir / "configs.csv", index=False)

    workflow.run_workflow(
        interpolated_dir=interpolated_dir,
        raw_dir=raw_dir,
        out_root=out_root,
        config_paths=cfg_paths,
        variants=variants,
        loadcells=loadcells,
        dates=dates,
        include_excel=include_excel,
        log_level=log_level,
    )

    runs = _collect_runs(out_root)
    runs.to_csv(out_root / "summary_runs.csv", index=False)

    ranking = _rank_configs(runs)
    ranking.to_csv(out_root / "ranking.csv", index=False)

    if not ranking.empty:
        top = ranking.sort_values(["variant", "rank"]).groupby("variant").head(20)
        top.to_csv(out_root / "ranking_top20.csv", index=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Grid sweep runner + ranking.")
    parser.add_argument("--out-root", type=Path, default=Path("runs_sweep"))
    parser.add_argument(
        "--interpolated-dir",
        type=Path,
        default=Path("data/preprocessed_csv_interpolated"),
    )
    parser.add_argument("--raw-dir", type=Path, default=Path("data/preprocessed_csv"))
    parser.add_argument("--base-config", type=Path, default=Path("config.yaml"))
    parser.add_argument(
        "--grid",
        action="append",
        default=[],
        help="Grid spec KEY=V1,V2,... (repeatable). Example: --grid smooth_window_sec=11,14,17",
    )
    parser.add_argument(
        "--variants",
        choices=["interpolated", "raw", "both"],
        default="both",
    )
    parser.add_argument("--loadcells", type=int, nargs="+", default=[1, 2, 3, 4, 5, 6])
    parser.add_argument(
        "--dates", nargs="*", help="Optional list of filenames (YYYY-MM-DD.csv)"
    )
    parser.add_argument("--excel", action="store_true")
    parser.add_argument("--log-level", type=str, default="WARNING")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for sweep execution."""

    args = build_parser().parse_args(list(argv) if argv is not None else None)
    run_sweep(
        out_root=args.out_root,
        interpolated_dir=args.interpolated_dir,
        raw_dir=args.raw_dir,
        base_config_path=args.base_config,
        grid_args=args.grid,
        variants=args.variants,
        loadcells=args.loadcells,
        dates=args.dates,
        include_excel=args.excel,
        log_level=args.log_level,
    )
    return 0
