#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stomatal_optimiaztion.domains.tomato.tomics.plotting import (  # noqa: E402
    render_simulation_summary_bundle,
)

DEFAULT_SIMULATION_SPEC_PATH = PROJECT_ROOT / "configs" / "plotkit" / "tomics" / "simulation_summary.yaml"

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot tomato simulation CSV outputs to a PNG summary.")
    parser.add_argument(
        "--input",
        default="out/tomics/analysis/partition-compare/example/tomics/df.csv",
        help="Input CSV path (model outputs).",
    )
    parser.add_argument(
        "--output",
        default="out/tomics/analysis/partition-compare/example/tomics/simulation_summary.png",
        help="Output PNG path.",
    )
    parser.add_argument(
        "--every",
        type=int,
        default=10,
        help="Row stride for plotting (e.g., 10 plots every 10th row).",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=160,
        help="PNG DPI.",
    )
    parser.add_argument(
        "--spec",
        default=str(DEFAULT_SIMULATION_SPEC_PATH),
        help="Plotkit spec path for the simulation summary figure.",
    )
    return parser


def _maybe_get(df: pd.DataFrame, column: str) -> pd.Series | None:
    if column not in df.columns:
        return None
    return pd.to_numeric(df[column], errors="coerce")


def _plot(df: pd.DataFrame, *, out_path: Path, dpi: int, spec_path: Path) -> None:
    render_simulation_summary_bundle(df=df, out_path=out_path, spec_path=spec_path)


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    every = max(int(args.every), 1)
    df = pd.read_csv(input_path, parse_dates=["datetime"])
    if df.empty:
        raise ValueError(f"Input CSV is empty: {input_path}")

    df_plot = df.iloc[::every].copy()
    out_path = Path(args.output).resolve()
    _plot(df_plot, out_path=out_path, dpi=int(args.dpi), spec_path=Path(args.spec).resolve())
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
