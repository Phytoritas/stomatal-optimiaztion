from __future__ import annotations

import pandas as pd


def coerce_loadcell_id(frame: pd.DataFrame, *, column: str = "loadcell_id") -> pd.DataFrame:
    out = frame.copy()
    if column in out.columns:
        out[column] = pd.to_numeric(out[column], errors="coerce").astype("Int64")
    return out


def loadcell_treatment_lookup(frame: pd.DataFrame) -> pd.DataFrame:
    if not {"loadcell_id", "treatment"}.issubset(frame.columns):
        return pd.DataFrame(columns=["loadcell_id", "treatment"])
    return (
        coerce_loadcell_id(frame)[["loadcell_id", "treatment"]]
        .dropna()
        .drop_duplicates()
        .sort_values("loadcell_id")
        .reset_index(drop=True)
    )
