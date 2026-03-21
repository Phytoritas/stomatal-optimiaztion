#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, load_config  # noqa: E402
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import (  # noqa: E402
    resolve_repo_root,
    run_tomato_legacy_pipeline,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.calibration import (  # noqa: E402
    load_candidate_specs,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.current_vs_promoted import (  # noqa: E402
    configure_candidate_run,
    prepare_knu_bundle,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_operator import (  # noqa: E402
    model_floor_area_cumulative_total_fruit,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.metrics import (  # noqa: E402
    compute_validation_bundle,
)
from stomatal_optimiaztion.domains.tomato.tomics.plotting import (  # noqa: E402
    render_partition_compare_bundle,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run fair KNU harvest observation evaluation for TOMICS candidates.")
    parser.add_argument(
        "--config",
        default="configs/exp/tomics_knu_observation_eval.yaml",
        help="Path to the KNU observation-evaluation config.",
    )
    return parser


def _resolve_config_path(raw: str | Path, *, repo_root: Path, config_path: Path) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    return (repo_root / candidate).resolve()


def _candidate_runs(config: dict, *, repo_root: Path, config_path: Path) -> dict[str, pd.DataFrame]:
    prepared_bundle = prepare_knu_bundle(config, repo_root=repo_root, config_path=config_path)
    specs, _, _ = load_candidate_specs(config=config, repo_root=repo_root, config_path=config_path)
    moderate = prepared_bundle.scenarios["moderate"]
    runs = {
        "measured": pd.DataFrame(
            {
                "datetime": pd.to_datetime(prepared_bundle.observed_df["date"]),
                "cumulative_total_fruit_floor_area": pd.to_numeric(
                    prepared_bundle.observed_df["measured_cumulative_total_fruit_dry_weight_floor_area"],
                    errors="coerce",
                ),
                "offset_adjusted_cumulative_total_fruit_floor_area": pd.to_numeric(
                    prepared_bundle.observed_df["measured_offset_adjusted"],
                    errors="coerce",
                ),
                "daily_increment_floor_area": pd.to_numeric(
                    prepared_bundle.observed_df["measured_daily_increment_floor_area"],
                    errors="coerce",
                ),
            }
        ),
        "workbook_estimated": pd.DataFrame(
            {
                "datetime": pd.to_datetime(prepared_bundle.workbook_validation_df["date"]),
                "cumulative_total_fruit_floor_area": pd.to_numeric(
                    prepared_bundle.workbook_validation_df["estimated_cumulative_total_fruit_dry_weight_floor_area"],
                    errors="coerce",
                ),
                "offset_adjusted_cumulative_total_fruit_floor_area": pd.to_numeric(
                    prepared_bundle.workbook_validation_df["estimated_offset_adjusted"],
                    errors="coerce",
                ),
                "daily_increment_floor_area": pd.to_numeric(
                    prepared_bundle.workbook_validation_df["estimated_daily_increment_floor_area"],
                    errors="coerce",
                ),
            }
        ),
    }
    summary_rows: list[dict[str, object]] = []
    for label in ("shipped_tomics", "current_selected", "promoted_selected"):
        spec = specs[label]
        assert spec.candidate_row is not None
        assert spec.base_config_path is not None
        run_cfg = configure_candidate_run(
            load_config(spec.base_config_path),
            forcing_csv_path=moderate.forcing_csv_path,
            theta_center=float(moderate.summary.get("theta_mean", 0.65)),
            row=spec.candidate_row,
        )
        run_df = run_tomato_legacy_pipeline(run_cfg, repo_root=repo_root)
        model_daily_df = model_floor_area_cumulative_total_fruit(run_df)
        candidate_series = prepared_bundle.observed_df["date"].map(
            model_daily_df.set_index("date")["model_cumulative_total_fruit_dry_weight_floor_area"]
        )
        bundle = compute_validation_bundle(
            prepared_bundle.observed_df.copy(),
            candidate_series=candidate_series,
            candidate_label="model",
            unit_declared_in_observation_file=prepared_bundle.data.observation_unit_label,
        )
        summary_rows.append(
            {
                "candidate_label": label,
                "architecture_id": str(spec.architecture_id),
                "rmse_cumulative_raw": bundle.metrics["rmse_cumulative_raw"],
                "rmse_cumulative_offset": bundle.metrics["rmse_cumulative_offset"],
                "mae_cumulative_offset": bundle.metrics["mae_cumulative_offset"],
                "r2_cumulative_offset": bundle.metrics["r2_cumulative_offset"],
                "rmse_daily_increment": bundle.metrics["rmse_daily_increment"],
                "mae_daily_increment": bundle.metrics["mae_daily_increment"],
                "harvest_timing_mae_days": bundle.metrics["harvest_timing_mae_days"],
                "final_cumulative_bias": bundle.metrics["final_cumulative_bias"],
                "final_cumulative_bias_pct": bundle.metrics["final_cumulative_bias_pct"],
            }
        )
        runs[label] = pd.DataFrame(
            {
                "datetime": pd.to_datetime(bundle.merged_df["date"]),
                "cumulative_total_fruit_floor_area": pd.to_numeric(
                    bundle.merged_df["model_cumulative_total_fruit_dry_weight_floor_area"],
                    errors="coerce",
                ),
                "offset_adjusted_cumulative_total_fruit_floor_area": pd.to_numeric(
                    bundle.merged_df["model_offset_adjusted"],
                    errors="coerce",
                ),
                "daily_increment_floor_area": pd.to_numeric(
                    bundle.merged_df["model_daily_increment_floor_area"],
                    errors="coerce",
                ),
            }
        )
    workbook_row = {
        "candidate_label": "workbook_estimated",
        "architecture_id": "workbook_estimated_baseline",
        "rmse_cumulative_raw": prepared_bundle.workbook_metrics["rmse_cumulative_raw"],
        "rmse_cumulative_offset": prepared_bundle.workbook_metrics["rmse_cumulative_offset"],
        "mae_cumulative_offset": prepared_bundle.workbook_metrics["mae_cumulative_offset"],
        "r2_cumulative_offset": prepared_bundle.workbook_metrics["r2_cumulative_offset"],
        "rmse_daily_increment": prepared_bundle.workbook_metrics["rmse_daily_increment"],
        "mae_daily_increment": prepared_bundle.workbook_metrics["mae_daily_increment"],
        "harvest_timing_mae_days": prepared_bundle.workbook_metrics["harvest_timing_mae_days"],
        "final_cumulative_bias": prepared_bundle.workbook_metrics["final_cumulative_bias"],
        "final_cumulative_bias_pct": prepared_bundle.workbook_metrics["final_cumulative_bias_pct"],
    }
    summary_rows.insert(0, workbook_row)
    output_root = ensure_dir(
        _resolve_config_path(
            load_config(config_path).get("observation_eval", {}).get("output_root", "out/tomics/validation/knu/fairness/observation-eval"),
            repo_root=repo_root,
            config_path=config_path,
        )
    )
    pd.DataFrame(summary_rows).to_csv(output_root / "observation_fit_summary.csv", index=False)
    cumulative_spec = _resolve_config_path(
        load_config(config_path).get("observation_eval", {}).get("cumulative_overlay_spec", "configs/plotkit/tomics/knu_cumulative_overlay.yaml"),
        repo_root=repo_root,
        config_path=config_path,
    )
    daily_spec = _resolve_config_path(
        load_config(config_path).get("observation_eval", {}).get("daily_overlay_spec", "configs/plotkit/tomics/knu_daily_increment_overlay.yaml"),
        repo_root=repo_root,
        config_path=config_path,
    )
    render_partition_compare_bundle(runs=runs, out_path=output_root / "cumulative_overlay.png", spec_path=cumulative_spec)
    render_partition_compare_bundle(runs=runs, out_path=output_root / "daily_increment_overlay.png", spec_path=daily_spec)
    manifest = {
        "observation_semantics": "cumulative_harvested_fruit_dry_weight_floor_area",
        "reporting_basis": "floor_area_g_m2",
        "candidate_labels": ["workbook_estimated", "shipped_tomics", "current_selected", "promoted_selected"],
        "prepared_bundle_root": str(prepared_bundle.prepared_root),
    }
    (output_root / "observation_operator_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return {"output_root": str(output_root), "prepared_bundle_root": str(prepared_bundle.prepared_root)}


def main() -> int:
    args = _build_parser().parse_args()
    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    repo_root = resolve_repo_root(config, config_path=config_path)
    result = _candidate_runs(config, repo_root=repo_root, config_path=config_path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
