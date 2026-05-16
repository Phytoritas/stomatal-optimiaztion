from __future__ import annotations

from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.input_schema_audit import load_input_table


def read_toa5_dat(path: str | Path, *, timestamp_col: str = "TIMESTAMP") -> pd.DataFrame:
    loaded = load_input_table(Path(path))
    if loaded.frame is None:
        raise ValueError(f"Could not parse TOA5/dat file {path}: {loaded.error}")
    frame = loaded.frame.copy()
    if timestamp_col in frame.columns:
        frame[timestamp_col] = pd.to_datetime(frame[timestamp_col], errors="coerce")
    return frame

