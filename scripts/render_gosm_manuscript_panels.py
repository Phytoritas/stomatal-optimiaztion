from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stomatal_optimiaztion.domains.gosm.examples import (  # noqa: E402
    DEFAULT_MANUSCRIPT_PANEL_OUTPUT_DIR,
    DEFAULT_MANUSCRIPT_PANEL_SPEC_PATH,
    render_manuscript_panel_bundle,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render the root GOSM manuscript atomic panel bundle.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_MANUSCRIPT_PANEL_OUTPUT_DIR,
        help="Directory where the rendered manuscript panel bundle will be written.",
    )
    parser.add_argument(
        "--spec",
        type=Path,
        default=DEFAULT_MANUSCRIPT_PANEL_SPEC_PATH,
        help="Plotkit-style YAML spec path for the manuscript panels.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    artifacts = render_manuscript_panel_bundle(
        output_dir=args.output_dir,
        spec_path=args.spec,
    )
    print(json.dumps(artifacts.to_summary(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
