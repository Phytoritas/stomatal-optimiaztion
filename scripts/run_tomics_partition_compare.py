#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
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
    summarize_tomato_legacy_metrics,
)
from stomatal_optimiaztion.domains.tomato.tomics.plotting import (  # noqa: E402
    render_partition_compare_bundle,
)


POLICY_ORDER: tuple[str, ...] = ("legacy", "thorp_fruit_veg", "tomics")
POLICY_LABELS = {
    "legacy": "Legacy sink-based",
    "thorp_fruit_veg": "Raw THORP",
    "tomics": "TOMICS hybrid",
}
DEFAULT_COMPARE_SPEC_PATH = PROJECT_ROOT / "configs" / "plotkit" / "tomics" / "partition_compare.yaml"


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _resolve_output_root(config: dict[str, Any], repo_root: Path, override: str | None) -> Path:
    if override:
        raw = Path(override)
    else:
        raw = Path(str(_as_dict(config.get("paths")).get("output_root", "out/tomics_partition_compare")))
    if raw.is_absolute():
        return raw
    return (repo_root / raw).resolve()


def _resolve_plot_spec_path(config: dict[str, Any], repo_root: Path) -> Path:
    plots_cfg = _as_dict(config.get("plots"))
    raw = Path(str(plots_cfg.get("comparison_plot_spec", DEFAULT_COMPARE_SPEC_PATH)))
    if raw.is_absolute():
        return raw
    return (repo_root / raw).resolve()


def _override_base_config(config: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    updated = copy.deepcopy(config)
    pipeline_cfg = updated.setdefault("pipeline", {})
    forcing_cfg = updated.setdefault("forcing", {})

    if not isinstance(pipeline_cfg, dict) or not isinstance(forcing_cfg, dict):
        raise TypeError("Config sections 'pipeline' and 'forcing' must be mappings.")

    if args.forcing_csv:
        forcing_cfg["csv_path"] = args.forcing_csv
    if args.theta_substrate is not None:
        pipeline_cfg["theta_substrate"] = float(args.theta_substrate)
    if args.fixed_lai is not None:
        pipeline_cfg["fixed_lai"] = float(args.fixed_lai)
    if args.allocation_scheme is not None:
        pipeline_cfg["allocation_scheme"] = str(args.allocation_scheme)

    return updated


def _policy_config(base_config: dict[str, Any], policy_name: str) -> dict[str, Any]:
    config = copy.deepcopy(base_config)
    pipeline_cfg = config.setdefault("pipeline", {})
    if not isinstance(pipeline_cfg, dict):
        raise TypeError("pipeline config must be a mapping.")
    pipeline_cfg["partition_policy"] = policy_name
    return config


def _mean_series(df: pd.DataFrame, column: str) -> float | None:
    if column not in df.columns:
        return None
    return float(pd.to_numeric(df[column], errors="coerce").mean())


def _final_series(df: pd.DataFrame, column: str) -> float | None:
    if column not in df.columns or df.empty:
        return None
    return float(pd.to_numeric(df[column], errors="coerce").iloc[-1])


def _summary_row(policy_name: str, df: pd.DataFrame) -> dict[str, object]:
    leaf = _mean_series(df, "alloc_frac_leaf")
    stem = _mean_series(df, "alloc_frac_stem")
    root = _mean_series(df, "alloc_frac_root")
    row: dict[str, object] = {
        "policy": policy_name,
        "policy_label": POLICY_LABELS.get(policy_name, policy_name),
        "rows": int(df.shape[0]),
        "mean_alloc_frac_fruit": _mean_series(df, "alloc_frac_fruit"),
        "mean_alloc_frac_leaf": leaf,
        "mean_alloc_frac_stem": stem,
        "mean_alloc_frac_root": root,
        "mean_alloc_frac_shoot": _mean_series(df, "alloc_frac_shoot"),
        "final_lai": _final_series(df, "LAI"),
        "final_total_dry_weight_g_m2": _final_series(df, "total_dry_weight_g_m2"),
        "mean_theta_substrate": _mean_series(df, "theta_substrate"),
        "mean_water_supply_stress": _mean_series(df, "water_supply_stress"),
    }
    if leaf is not None and stem is not None and root is not None:
        row["mean_canopy_minus_root_frac"] = (leaf + stem) - root
    return row


def _plot_compare(
    runs: dict[str, pd.DataFrame],
    *,
    out_path: Path,
    spec_path: Path,
) -> dict[str, str]:
    artifacts = render_partition_compare_bundle(
        runs=runs,
        out_path=out_path,
        spec_path=spec_path,
    )
    return artifacts.to_summary()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run legacy, raw THORP, and TOMICS tomato partition policies on one config."
    )
    parser.add_argument(
        "--config",
        default="configs/exp/tomics_partition_compare.yaml",
        help="Path to comparison YAML config.",
    )
    parser.add_argument(
        "--output-root",
        default=None,
        help="Override output root (default from config or out/tomics_partition_compare).",
    )
    parser.add_argument(
        "--exp-key",
        default=None,
        help="Optional explicit experiment key.",
    )
    parser.add_argument(
        "--forcing-csv",
        default=None,
        help="Optional forcing CSV override.",
    )
    parser.add_argument(
        "--theta-substrate",
        type=float,
        default=None,
        help="Optional theta_substrate override.",
    )
    parser.add_argument(
        "--allocation-scheme",
        default=None,
        help="Optional allocation scheme override.",
    )
    parser.add_argument(
        "--fixed-lai",
        type=float,
        default=None,
        help="Optional fixed LAI override.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    config_path = Path(args.config).resolve()
    config = _override_base_config(load_config(config_path), args)
    repo_root = resolve_repo_root(config, config_path=config_path)

    exp_cfg = _as_dict(config.get("exp"))
    exp_name = str(exp_cfg.get("name", "tomato_partition_compare"))
    exp_key = args.exp_key or build_exp_key(
        config_payload_for_exp_key(config),
        prefix=exp_name,
    )

    output_root = ensure_dir(_resolve_output_root(config, repo_root, args.output_root) / exp_key)
    plot_spec_path = _resolve_plot_spec_path(config, repo_root)

    runs: dict[str, pd.DataFrame] = {}
    summary_rows: list[dict[str, object]] = []
    for policy_name in POLICY_ORDER:
        policy_dir = ensure_dir(output_root / policy_name)
        policy_config = _policy_config(config, policy_name)
        df = run_tomato_legacy_pipeline(policy_config, repo_root=repo_root, config_path=config_path)
        df.to_csv(policy_dir / "df.csv", index=False)
        metrics = summarize_tomato_legacy_metrics(df)
        write_json(
            policy_dir / "meta.json",
            {
                "exp_key": exp_key,
                "policy": policy_name,
                "policy_label": POLICY_LABELS.get(policy_name, policy_name),
                "rows": int(df.shape[0]),
                "metrics": metrics,
                "config": policy_config,
            },
        )
        runs[policy_name] = df
        summary_rows.append(_summary_row(policy_name, df))

    summary_df = pd.DataFrame(summary_rows)
    summary_path = output_root / "summary.csv"
    summary_df.to_csv(summary_path, index=False)
    plot_path = output_root / "comparison_plot.png"
    plot_summary = _plot_compare(runs, out_path=plot_path, spec_path=plot_spec_path)

    print(
        json.dumps(
            {
                "comparison_plot": str(plot_path),
                "comparison_plot_metadata": plot_summary.get("metadata"),
                "exp_key": exp_key,
                "output_root": str(output_root),
                "summary_csv": str(summary_path),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
