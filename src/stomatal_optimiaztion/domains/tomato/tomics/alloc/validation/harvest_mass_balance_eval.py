from __future__ import annotations

import math

import pandas as pd


def summarize_harvest_mass_balance(frame: pd.DataFrame) -> dict[str, float | bool]:
    if frame.empty:
        return {
            "harvest_mass_balance_error": 0.0,
            "latent_fruit_residual_end": 0.0,
            "leaf_harvest_mass_balance_error": 0.0,
            "duplicate_harvest_flag": False,
            "negative_mass_flag": False,
        }
    return {
        "harvest_mass_balance_error": float(pd.to_numeric(frame["harvest_mass_balance_error"], errors="coerce").fillna(0.0).max()),
        "latent_fruit_residual_end": float(pd.to_numeric(frame["latent_fruit_residual_end"], errors="coerce").fillna(0.0).iloc[-1]),
        "leaf_harvest_mass_balance_error": float(
            pd.to_numeric(frame["leaf_harvest_mass_balance_error"], errors="coerce").fillna(0.0).max()
        ),
        "duplicate_harvest_flag": bool(
            pd.to_numeric(frame.get("duplicate_harvest_flag", pd.Series(dtype=float)), errors="coerce").fillna(0.0).max() > 0.0
        )
        if "duplicate_harvest_flag" in frame.columns
        else False,
        "negative_mass_flag": bool(
            pd.to_numeric(frame.get("negative_mass_flag", pd.Series(dtype=float)), errors="coerce").fillna(0.0).max() > 0.0
        )
        if "negative_mass_flag" in frame.columns
        else False,
    }


def winner_stability_score(frame: pd.DataFrame, *, candidate_column: str = "candidate_key") -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=[candidate_column, "winner_stability_score", "win_count"])
    grouped = (
        frame.groupby(["split_label", candidate_column], as_index=False)["score"].mean().sort_values(["split_label", "score"], ascending=[True, False])
    )
    winners = grouped.groupby("split_label", as_index=False).first()
    counts = winners.groupby(candidate_column, as_index=False).agg(win_count=("split_label", "count"))
    counts["winner_stability_score"] = counts["win_count"] / max(frame["split_label"].nunique(), 1)
    return counts


def safe_max(frame: pd.DataFrame, column: str, *, default: float = math.nan) -> float:
    if column not in frame.columns or frame.empty:
        return float(default)
    series = pd.to_numeric(frame[column], errors="coerce").dropna()
    if series.empty:
        return float(default)
    return float(series.max())


__all__ = ["safe_max", "summarize_harvest_mass_balance", "winner_stability_score"]
