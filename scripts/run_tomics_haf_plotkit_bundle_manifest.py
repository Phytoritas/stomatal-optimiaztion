from __future__ import annotations

import argparse
import json
from pathlib import Path

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_plotkit_manifest import (
    write_haf_plotkit_render_manifest,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write the TOMICS-HAF 2025-2C Plotkit render manifest.",
    )
    parser.add_argument(
        "--spec-dir",
        type=Path,
        default=Path("configs/plotkit/tomics/haf_2025_2c"),
        help="Directory containing HAF 2025-2C Plotkit specs.",
    )
    parser.add_argument(
        "--input-root",
        type=Path,
        default=Path("out/tomics/validation/harvest-family/haf_2025_2c"),
        help="Directory containing harvest-family CSV outputs.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("out/tomics/figures/haf_2025_2c"),
        help="Directory for manifest-only Plotkit figure bundle status.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = write_haf_plotkit_render_manifest(
        spec_dir=args.spec_dir.resolve(),
        input_root=args.input_root.resolve(),
        output_root=args.output_root.resolve(),
    )
    print(json.dumps(paths, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
