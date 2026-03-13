from __future__ import annotations

import argparse
import json
from pathlib import Path

from stomatal_optimiaztion.domains.tdgm.examples import render_tdgm_example_figure_suite


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render root TDGM supplementary example figures.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional output directory for the TDGM example figure suite.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    artifacts = render_tdgm_example_figure_suite(output_dir=args.output_dir)
    print(json.dumps(artifacts.to_summary(), indent=2))


if __name__ == "__main__":
    main()
