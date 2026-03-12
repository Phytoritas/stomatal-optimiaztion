from __future__ import annotations

import argparse
from collections.abc import Sequence

from stomatal_optimiaztion.domains.thorp.matlab_io import save_mat
from stomatal_optimiaztion.domains.thorp.simulation import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the THORP Python port.")
    parser.add_argument("--max-steps", type=int, default=60, help="Max time steps (default: 60).")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run the full forcing horizon (can take a long time).",
    )
    parser.add_argument(
        "--save-mat",
        type=str,
        default=None,
        help="Optional output .mat path (e.g., THORP_data_0.6RH.mat).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    outputs = run(
        max_steps=None if args.full else args.max_steps,
        save_mat_path=args.save_mat,
        save_mat_callback=save_mat if args.save_mat is not None else None,
    )
    print(f"Stored {outputs.t_ts.size} points (last t={outputs.t_ts[-1]} s).")
    return 0
