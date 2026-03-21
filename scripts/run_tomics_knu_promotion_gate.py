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
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.promotion_gate import (  # noqa: E402
    run_promotion_gate,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the final KNU fair-validation promotion gate for TOMICS.")
    parser.add_argument(
        "--config",
        default="configs/exp/tomics_knu_promotion_gate.yaml",
        help="Path to the KNU promotion-gate config.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    repo_root = resolve_repo_root(config, config_path=config_path)
    result = run_promotion_gate(config, repo_root=repo_root, config_path=config_path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
