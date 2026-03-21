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

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation import (  # noqa: E402
    run_current_vs_promoted_factorial,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run current and promoted TOMICS allocation factorial studies on actual KNU greenhouse data."
    )
    parser.add_argument(
        "--config",
        default="configs/exp/tomics_current_vs_promoted_factorial_knu.yaml",
        help="Path to the KNU actual-data current-vs-promoted factorial config.",
    )
    parser.add_argument(
        "--mode",
        default="both",
        choices=["current", "promoted", "both"],
        help="Select whether to run the current study, promoted study, or both plus side-by-side comparison.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run_current_vs_promoted_factorial(config_path=args.config, mode=args.mode)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
