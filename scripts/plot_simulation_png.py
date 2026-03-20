#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot tomato simulation CSV outputs to a PNG summary.")
    parser.add_argument(
        "--input",
        default="out/tomics_partition_compare/example/tomics/df.csv",
        help="Input CSV path (model outputs).",
    )
    parser.add_argument(
        "--output",
        default="out/tomics_partition_compare/example/tomics/simulation_summary.png",
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
    return parser


def _maybe_get(df: pd.DataFrame, column: str) -> pd.Series | None:
    if column not in df.columns:
        return None
    return pd.to_numeric(df[column], errors="coerce")


def _plot(df: pd.DataFrame, *, out_path: Path, dpi: int) -> None:
    try:
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ModuleNotFoundError(
            "Plotting requires matplotlib. Install with: python -m pip install matplotlib"
        ) from exc

    x = df["datetime"]

    fig, axes = plt.subplots(nrows=4, ncols=1, sharex=True, figsize=(14, 10), constrained_layout=True)

    ax = axes[0]
    lai = _maybe_get(df, "LAI")
    t_canopy = _maybe_get(df, "T_canopy_C")
    if lai is not None:
        ax.plot(x, lai, label="LAI", color="tab:green", linewidth=1.0)
        ax.set_ylabel("LAI")
    if t_canopy is not None:
        ax2 = ax.twinx()
        ax2.plot(x, t_canopy, label="T_canopy_C", color="tab:red", linewidth=1.0, alpha=0.8)
        ax2.set_ylabel("T_canopy (C)")
    ax.grid(True, alpha=0.25)
    ax.set_title("TOMICS-Alloc Tomato Legacy Simulation Summary")

    ax = axes[1]
    total_dw = _maybe_get(df, "total_dry_weight_g_m2")
    leaf_dw = _maybe_get(df, "leaf_dry_weight_g_m2")
    stem_dw = _maybe_get(df, "stem_dry_weight_g_m2")
    root_dw = _maybe_get(df, "root_dry_weight_g_m2")
    fruit_dw = _maybe_get(df, "fruit_dry_weight_g_m2")
    if total_dw is not None:
        ax.plot(x, total_dw, label="total", color="black", linewidth=1.0)
    if leaf_dw is not None:
        ax.plot(x, leaf_dw, label="leaf", linewidth=0.9)
    if stem_dw is not None:
        ax.plot(x, stem_dw, label="stem", linewidth=0.9)
    if root_dw is not None:
        ax.plot(x, root_dw, label="root", linewidth=0.9)
    if fruit_dw is not None:
        ax.plot(x, fruit_dw, label="fruit", linewidth=0.9)
    ax.set_ylabel("Dry weight (g/m2)")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper left", ncols=5, fontsize=9)

    ax = axes[2]
    co2_flux = _maybe_get(df, "co2_flux_g_m2_s")
    transp_rate = _maybe_get(df, "transpiration_rate_g_s_m2")
    if co2_flux is not None:
        ax.plot(x, co2_flux, label="co2_flux_g_m2_s", color="tab:blue", linewidth=0.9)
        ax.set_ylabel("CO2 flux (g/m2/s)")
    if transp_rate is not None:
        ax2 = ax.twinx()
        ax2.plot(x, transp_rate, label="transpiration_rate_g_s_m2", color="tab:purple", linewidth=0.9, alpha=0.8)
        ax2.set_ylabel("Transp. rate (g/m2/s)")
    ax.grid(True, alpha=0.25)

    ax = axes[3]
    for col, label, color in (
        ("alloc_frac_fruit", "fruit", "tab:orange"),
        ("alloc_frac_leaf", "leaf", "tab:green"),
        ("alloc_frac_stem", "stem", "tab:brown"),
        ("alloc_frac_root", "root", "tab:gray"),
        ("alloc_frac_shoot", "shoot", "tab:cyan"),
    ):
        series = _maybe_get(df, col)
        if series is None:
            continue
        ax.plot(x, series, label=label, linewidth=0.9, alpha=0.9, color=color)
    ax.set_ylabel("Allocation fraction (-)")
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper left", ncols=5, fontsize=9)

    locator = mdates.AutoDateLocator(minticks=4, maxticks=10)
    axes[-1].xaxis.set_major_locator(locator)
    axes[-1].xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    axes[-1].set_xlabel("datetime")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=int(dpi), bbox_inches="tight")
    plt.close(fig)


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
    _plot(df_plot, out_path=out_path, dpi=int(args.dpi))
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
