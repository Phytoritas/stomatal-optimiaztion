from __future__ import annotations

import argparse
import json
from pathlib import Path

from stomatal_optimiaztion.domains.tomato.tomics.observers.pipeline import (
    run_tomics_haf_observer_pipeline,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the TOMICS-HAF 2025-2C observer pipeline.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/exp/tomics_haf_2025_2c_observer_pipeline.yaml"),
        help="Path to the observer pipeline config.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_tomics_haf_observer_pipeline(args.config)
    print(json.dumps(result["outputs"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

