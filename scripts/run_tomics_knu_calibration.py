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

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import load_config  # noqa: E402
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import resolve_repo_root  # noqa: E402
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.calibration import (  # noqa: E402
    run_calibration_suite,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run KNU equal-budget TOMICS calibration and holdout evaluation.")
    parser.add_argument(
        "--config",
        default="configs/exp/tomics_knu_calibration.yaml",
        help="Path to the KNU calibration config.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    repo_root = resolve_repo_root(config, config_path=config_path)
    artifacts = run_calibration_suite(config, repo_root=repo_root, config_path=config_path)
    print(
        json.dumps(
            {
                "output_root": str(artifacts.output_root),
                "calibration_rows": int(artifacts.calibration_results_df.shape[0]),
                "holdout_rows": int(artifacts.holdout_results_df.shape[0]),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
