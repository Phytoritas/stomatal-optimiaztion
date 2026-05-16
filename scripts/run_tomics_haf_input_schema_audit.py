from __future__ import annotations

import argparse
from pathlib import Path

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import load_config
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import resolve_repo_root
from stomatal_optimiaztion.domains.tomato.tomics.observers import run_tomics_haf_input_schema_audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TOMICS-HAF 2025-2C input schema audit.")
    parser.add_argument("--config", required=True, help="Path to input schema audit YAML config.")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    repo_root = resolve_repo_root(config, config_path=config_path)
    result = run_tomics_haf_input_schema_audit(config, repo_root=repo_root, config_path=config_path)
    print(result["output_root"])


if __name__ == "__main__":
    main()
