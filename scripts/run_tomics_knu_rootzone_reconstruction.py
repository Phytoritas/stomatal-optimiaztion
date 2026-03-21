#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, load_config  # noqa: E402
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import resolve_repo_root  # noqa: E402
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.current_vs_promoted import (  # noqa: E402
    prepare_knu_bundle,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.rootzone_inversion import (  # noqa: E402
    reconstruct_rootzone,
    write_rootzone_manifest,
)
from stomatal_optimiaztion.domains.tomato.tomics.plotting import render_partition_compare_bundle  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run KNU greenhouse root-zone reconstruction for fair TOMICS validation.")
    parser.add_argument(
        "--config",
        default="configs/exp/tomics_knu_rootzone_reconstruction.yaml",
        help="Path to the KNU root-zone reconstruction config.",
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
    rootzone_cfg = config.get("rootzone_reconstruction", {})
    output_root = ensure_dir(
        _resolve_config_path(
            rootzone_cfg.get("output_root", "out/tomics_knu_rootzone_reconstruction"),
            repo_root=repo_root,
            config_path=config_path,
        )
    )
    result = reconstruct_rootzone(
        prepared_bundle.data.forcing_df,
        theta_proxy_mode=str(rootzone_cfg.get("theta_proxy_mode", "bucket_irrigated")),
        scenario_ids=tuple(rootzone_cfg.get("scenario_ids", ["dry", "moderate", "wet"])),
        theta_min_hard=float(rootzone_cfg.get("theta_min_hard", 0.40)),
        theta_max_hard=float(rootzone_cfg.get("theta_max_hard", 0.85)),
    )
    result.summary_df.to_csv(output_root / "rootzone_summary.csv", index=False)
    result.band_df.to_csv(output_root / "theta_uncertainty_band.csv", index=False)
    write_rootzone_manifest(output_root=output_root, manifest=result.manifest)
    runs = {}
    for scenario_id, frame in result.scenario_frames.items():
        runs[scenario_id] = frame.rename(
            columns={
                "theta_substrate": "theta_substrate",
                "rootzone_multistress": "rootzone_multistress",
                "rootzone_saturation": "rootzone_saturation",
                "demand_index": "demand_index",
            }
        )
    spec_path = _resolve_config_path(
        rootzone_cfg.get("overlay_spec", "configs/plotkit/tomics/knu_theta_proxy_diagnostics.yaml"),
        repo_root=repo_root,
        config_path=config_path,
    )
    render_partition_compare_bundle(
        runs=runs,
        out_path=output_root / "theta_proxy_overlay.png",
        spec_path=spec_path,
    )
    print(json.dumps({"output_root": str(output_root), "scenario_count": len(result.scenario_frames)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
