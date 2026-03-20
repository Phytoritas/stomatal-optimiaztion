#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import itertools
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import (  # noqa: E402
    build_exp_key,
    ensure_dir,
    load_config,
    write_json,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import (  # noqa: E402
    config_payload_for_exp_key,
    resolve_repo_root,
    run_tomato_legacy_pipeline,
)
from stomatal_optimiaztion.domains.tomato.tomics.plotting import (  # noqa: E402
    render_factorial_summary_bundle,
)


DEFAULT_POLICY_ORDER: tuple[str, ...] = ("legacy", "thorp_fruit_veg", "tomics")
DEFAULT_FACTORIAL_SUMMARY_SPEC_PATH = PROJECT_ROOT / "configs" / "plotkit" / "tomics" / "factorial_summary.yaml"


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _as_float_list(raw: object, *, default: tuple[float, ...]) -> list[float]:
    if isinstance(raw, (list, tuple)):
        return [float(value) for value in raw]
    return [float(value) for value in default]


def _as_str_list(raw: object, *, default: tuple[str, ...]) -> list[str]:
    if isinstance(raw, (list, tuple)):
        return [str(value) for value in raw]
    return [str(value) for value in default]


def _resolve_output_root(config: dict[str, Any], repo_root: Path, override: str | None) -> Path:
    if override:
        raw = Path(override)
    else:
        raw = Path(str(_as_dict(config.get("paths")).get("output_root", "out/tomics_factorial")))
    if raw.is_absolute():
        return raw
    return (repo_root / raw).resolve()


def _resolve_plot_spec_path(config: dict[str, Any], repo_root: Path) -> Path:
    plots_cfg = _as_dict(config.get("plots"))
    raw = Path(str(plots_cfg.get("summary_plot_spec", DEFAULT_FACTORIAL_SUMMARY_SPEC_PATH)))
    if raw.is_absolute():
        return raw
    return (repo_root / raw).resolve()


def _base_tomics_params(config: dict[str, Any]) -> dict[str, object]:
    pipeline_cfg = _as_dict(config.get("pipeline"))
    params = _as_dict(pipeline_cfg.get("partition_policy_params"))
    tomics = _as_dict(pipeline_cfg.get("tomics"))
    if tomics:
        params = {**params, **tomics}
    return params


def _design_rows(config: dict[str, Any]) -> list[dict[str, object]]:
    pipeline_cfg = _as_dict(config.get("pipeline"))
    screen_cfg = _as_dict(config.get("screen"))
    default_tomics = _base_tomics_params(config)

    policies = _as_str_list(
        screen_cfg.get("partition_policies"),
        default=DEFAULT_POLICY_ORDER,
    )
    theta_levels = _as_float_list(
        screen_cfg.get("theta_substrate"),
        default=(0.20, 0.33, 0.50),
    )
    wet_caps = _as_float_list(screen_cfg.get("wet_root_cap"), default=(0.08, 0.10))
    dry_caps = _as_float_list(screen_cfg.get("dry_root_cap"), default=(0.15, 0.18))
    lai_targets = _as_float_list(screen_cfg.get("lai_target_center"), default=(2.5, 3.0))
    collapse_non_tomics = bool(screen_cfg.get("collapse_non_tomics_tomics_factors", True))

    default_wet = float(default_tomics.get("wet_root_cap", 0.10))
    default_dry = float(default_tomics.get("dry_root_cap", 0.18))
    default_lai = float(default_tomics.get("lai_target_center", 2.75))

    design_rows: list[dict[str, object]] = []
    for policy_name in policies:
        if collapse_non_tomics and policy_name != "tomics":
            combos = ((theta, default_wet, default_dry, default_lai) for theta in theta_levels)
        else:
            combos = itertools.product(theta_levels, wet_caps, dry_caps, lai_targets)

        for theta_substrate, wet_root_cap, dry_root_cap, lai_target_center in combos:
            row = {
                "partition_policy": str(policy_name),
                "theta_substrate": float(theta_substrate),
                "wet_root_cap": float(wet_root_cap),
                "dry_root_cap": float(dry_root_cap),
                "lai_target_center": float(lai_target_center),
                "allocation_scheme": str(pipeline_cfg.get("allocation_scheme", "4pool")),
                "collapse_non_tomics_tomics_factors": collapse_non_tomics,
            }
            design_rows.append(row)

    return design_rows


def _config_for_row(base_config: dict[str, Any], row: dict[str, object]) -> dict[str, Any]:
    config = copy.deepcopy(base_config)
    pipeline_cfg = config.setdefault("pipeline", {})
    if not isinstance(pipeline_cfg, dict):
        raise TypeError("pipeline config must be a mapping.")

    pipeline_cfg["partition_policy"] = row["partition_policy"]
    pipeline_cfg["theta_substrate"] = row["theta_substrate"]
    pipeline_cfg["tomics"] = {
        "wet_root_cap": row["wet_root_cap"],
        "dry_root_cap": row["dry_root_cap"],
        "lai_target_center": row["lai_target_center"],
    }
    return config


def _mean_series(df: pd.DataFrame, column: str) -> float | None:
    if column not in df.columns:
        return None
    return float(pd.to_numeric(df[column], errors="coerce").mean())


def _final_series(df: pd.DataFrame, column: str) -> float | None:
    if column not in df.columns or df.empty:
        return None
    return float(pd.to_numeric(df[column], errors="coerce").iloc[-1])


def _metrics_row(
    *,
    run_key: str,
    design_row: dict[str, object],
    df: pd.DataFrame,
) -> dict[str, object]:
    leaf = _mean_series(df, "alloc_frac_leaf")
    stem = _mean_series(df, "alloc_frac_stem")
    root = _mean_series(df, "alloc_frac_root")
    metrics: dict[str, object] = {
        "run_key": run_key,
        **design_row,
        "rows": int(df.shape[0]),
        "mean_alloc_frac_fruit": _mean_series(df, "alloc_frac_fruit"),
        "mean_alloc_frac_leaf": leaf,
        "mean_alloc_frac_stem": stem,
        "mean_alloc_frac_root": root,
        "mean_theta_substrate": _mean_series(df, "theta_substrate"),
        "mean_water_supply_stress": _mean_series(df, "water_supply_stress"),
        "final_lai": _final_series(df, "LAI"),
        "final_total_dry_weight_g_m2": _final_series(df, "total_dry_weight_g_m2"),
    }
    if leaf is not None and stem is not None and root is not None:
        metrics["mean_canopy_minus_root_frac"] = (leaf + stem) - root
    return metrics


def _plot_summary(metrics_df: pd.DataFrame, *, out_path: Path, spec_path: Path) -> dict[str, str]:
    artifacts = render_factorial_summary_bundle(
        metrics_df=metrics_df,
        out_path=out_path,
        spec_path=spec_path,
    )
    return artifacts.to_summary()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a small TOMICS tomato factorial screen.")
    parser.add_argument(
        "--config",
        default="configs/exp/tomics_factorial.yaml",
        help="Path to factorial YAML config.",
    )
    parser.add_argument(
        "--output-root",
        default=None,
        help="Override output root (default from config or out/tomics_factorial).",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    repo_root = resolve_repo_root(config, config_path=config_path)
    output_root = ensure_dir(_resolve_output_root(config, repo_root, args.output_root))
    plot_spec_path = _resolve_plot_spec_path(config, repo_root)

    design_rows = _design_rows(config)
    design_df = pd.DataFrame(design_rows)
    design_df.index = range(1, len(design_df) + 1)
    design_df.index.name = "design_id"
    design_path = output_root / "design_table.csv"
    design_df.to_csv(design_path)

    metrics_rows: list[dict[str, object]] = []
    for design_id, row in design_df.reset_index().iterrows():
        design_row = {
            "partition_policy": str(row["partition_policy"]),
            "theta_substrate": float(row["theta_substrate"]),
            "wet_root_cap": float(row["wet_root_cap"]),
            "dry_root_cap": float(row["dry_root_cap"]),
            "lai_target_center": float(row["lai_target_center"]),
            "allocation_scheme": str(row["allocation_scheme"]),
            "collapse_non_tomics_tomics_factors": bool(row["collapse_non_tomics_tomics_factors"]),
        }
        run_config = _config_for_row(config, design_row)
        run_key = build_exp_key(
            config_payload_for_exp_key(run_config),
            prefix=f"run_{int(row['design_id']):03d}",
        )
        df = run_tomato_legacy_pipeline(run_config, repo_root=repo_root, config_path=config_path)
        metrics_rows.append(_metrics_row(run_key=run_key, design_row=design_row, df=df))

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_path = output_root / "run_metrics.csv"
    metrics_df.to_csv(metrics_path, index=False)
    plot_path = output_root / "summary_plot.png"
    plot_summary = _plot_summary(metrics_df, out_path=plot_path, spec_path=plot_spec_path)

    write_json(
        output_root / "meta.json",
        {
            "config": config,
            "design_rows": int(design_df.shape[0]),
            "collapse_non_tomics_tomics_factors": bool(
                _as_dict(config.get("screen")).get("collapse_non_tomics_tomics_factors", True)
            ),
            "note": (
                "Non-TOMICS policies keep one default TOMICS parameter set per theta_substrate "
                "when collapse_non_tomics_tomics_factors=true because TOMICS-only factors do not "
                "change legacy or raw THORP policy outputs."
            ),
        },
    )

    print(
        json.dumps(
            {
                "design_table_csv": str(design_path),
                "output_root": str(output_root),
                "run_metrics_csv": str(metrics_path),
                "summary_plot": str(plot_path),
                "summary_plot_metadata": plot_summary.get("metadata"),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
