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
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import resolve_repo_root  # noqa: E402
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.calibration import (  # noqa: E402
    load_candidate_specs,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.current_vs_promoted import (  # noqa: E402
    prepare_knu_bundle,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.state_reconstruction import (  # noqa: E402
    reconstruct_hidden_state,
)
from stomatal_optimiaztion.domains.tomato.tomics.plotting import render_partition_compare_bundle  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run KNU hidden-state reconstruction for fair TOMICS validation.")
    parser.add_argument(
        "--config",
        default="configs/exp/tomics_knu_state_reconstruction.yaml",
        help="Path to the KNU state-reconstruction config.",
    )
    return parser


def _resolve_config_path(raw: str | Path, *, repo_root: Path, config_path: Path) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    return (repo_root / candidate).resolve()


def main() -> int:
    args = _build_parser().parse_args()
    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    repo_root = resolve_repo_root(config, config_path=config_path)
    prepared_bundle = prepare_knu_bundle(config, repo_root=repo_root, config_path=config_path)
    specs, _, _ = load_candidate_specs(config=config, repo_root=repo_root, config_path=config_path)
    output_root = ensure_dir(
        _resolve_config_path(
            config.get("state_reconstruction", {}).get("output_root", "out/tomics_knu_state_reconstruction"),
            repo_root=repo_root,
            config_path=config_path,
        )
    )
    mode_values = tuple(config.get("state_reconstruction", {}).get("modes", ["minimal_scalar_init", "cohort_aware_init", "buffer_aware_init"]))
    summary_rows: list[dict[str, object]] = []
    initial_state_payload: dict[str, object] = {}
    runs: dict[str, pd.DataFrame] = {
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
        )
    }
    for candidate_label in ("shipped_tomics", "current_selected", "promoted_selected"):
        spec = specs[candidate_label]
        assert spec.candidate_row is not None
        assert spec.base_config_path is not None
        result = reconstruct_hidden_state(
            architecture_row=spec.candidate_row,
            base_config=load_config(spec.base_config_path),
            forcing_csv_path=prepared_bundle.scenarios["moderate"].forcing_csv_path,
            theta_center=float(prepared_bundle.scenarios["moderate"].summary.get("theta_mean", 0.65)),
            observed_df=prepared_bundle.observed_df,
            calibration_end=prepared_bundle.calibration_end,
            repo_root=repo_root,
            unit_label=prepared_bundle.data.observation_unit_label,
            modes=mode_values,
        )
        summary_rows.append(
            {
                "candidate_label": candidate_label,
                "architecture_id": result.architecture_id,
                "mode": result.mode,
                **result.metrics,
            }
        )
        initial_state_payload[candidate_label] = {
            "architecture_id": result.architecture_id,
            "mode": result.mode,
            "candidate_label": result.candidate_label,
            "initial_state_overrides": result.initial_state_overrides,
        }
        runs[candidate_label] = pd.DataFrame(
            {
                "datetime": pd.to_datetime(result.validation_df["date"]),
                "cumulative_total_fruit_floor_area": pd.to_numeric(
                    result.validation_df["model_cumulative_total_fruit_dry_weight_floor_area"],
                    errors="coerce",
                ),
                "offset_adjusted_cumulative_total_fruit_floor_area": pd.to_numeric(
                    result.validation_df["model_offset_adjusted"],
                    errors="coerce",
                ),
                "daily_increment_floor_area": pd.to_numeric(
                    result.validation_df["model_daily_increment_floor_area"],
                    errors="coerce",
                ),
            }
        )
    pd.DataFrame(summary_rows).to_csv(output_root / "reconstruction_summary.csv", index=False)
    (output_root / "reconstructed_initial_state.json").write_text(
        json.dumps(initial_state_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    spec_path = _resolve_config_path(
        config.get("state_reconstruction", {}).get("overlay_spec", "configs/plotkit/tomics/knu_cumulative_overlay.yaml"),
        repo_root=repo_root,
        config_path=config_path,
    )
    render_partition_compare_bundle(
        runs=runs,
        out_path=output_root / "reconstruction_overlay.png",
        spec_path=spec_path,
    )
    print(
        json.dumps(
            {
                "output_root": str(output_root),
                "modes": list(mode_values),
                "candidate_count": len(summary_rows),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
