from __future__ import annotations

import argparse
import json
from pathlib import Path

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.pipeline import (
    run_tomics_haf_latent_allocation,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the TOMICS-HAF 2025-2C latent allocation inference.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/exp/tomics_haf_2025_2c_latent_allocation.yaml"),
        help="Path to the latent allocation config.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_tomics_haf_latent_allocation(args.config)
    print(json.dumps(result["outputs"], indent=2, ensure_ascii=False))
    metadata = result.get("metadata", {})
    if not bool(metadata.get("latent_allocation_ready", False)):
        return 1
    if not bool(metadata.get("latent_allocation_guardrails_passed", False)):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
