from __future__ import annotations

import argparse
import json
from pathlib import Path

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import load_config
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import resolve_repo_root
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_cross_dataset_gate import (
    run_haf_cross_dataset_gate,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TOMICS-HAF 2025-2C cross-dataset gate.")
    parser.add_argument("--config", required=True, help="Path to HAF cross-dataset gate YAML config.")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    repo_root = resolve_repo_root(config, config_path=config_path)
    result = run_haf_cross_dataset_gate(config, repo_root=repo_root, config_path=config_path)
    print(json.dumps({key: value for key, value in result.items() if key != "metadata"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
