from __future__ import annotations

import argparse
import json
from pathlib import Path

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import load_config
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import resolve_repo_root
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_harvest_factorial import (
    run_tomics_haf_harvest_family_factorial,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the TOMICS-HAF 2025-2C harvest-family factorial.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/exp/tomics_haf_2025_2c_harvest_family_factorial.yaml"),
        help="Path to the HAF harvest-family factorial config.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config_path = args.config.resolve()
    config = load_config(config_path)
    repo_root = resolve_repo_root(config, config_path=config_path)
    result = run_tomics_haf_harvest_family_factorial(
        config,
        repo_root=repo_root,
        config_path=config_path,
    )
    print(json.dumps(result["paths"], indent=2, ensure_ascii=False))
    metadata = result.get("metadata", {})
    if bool(metadata.get("promotion_gate_run", True)):
        return 1
    if bool(metadata.get("cross_dataset_gate_run", True)):
        return 1
    if bool(metadata.get("shipped_TOMICS_incumbent_changed", True)):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
