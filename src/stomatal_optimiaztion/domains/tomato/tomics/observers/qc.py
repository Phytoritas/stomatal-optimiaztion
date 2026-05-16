from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

DEFAULT_FRUIT_COLUMNS = ("Fruit1Diameter_Avg", "Fruit2Diameter_Avg")
DEFAULT_LEAF_COLUMNS = ("LeafTemp1_Avg", "LeafTemp2_Avg")


def _numeric_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce")


def apply_fruit_leaf_qc(
    frame: pd.DataFrame,
    *,
    timestamp_col: str = "TIMESTAMP",
    fruit_columns: Iterable[str] = DEFAULT_FRUIT_COLUMNS,
    leaf_columns: Iterable[str] = DEFAULT_LEAF_COLUMNS,
    min_fruit_mm: float = 20.0,
    max_fruit_mm: float = 120.0,
    max_10min_jump_mm: float = 1.0,
    min_valid_points: int = 3,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    qc = frame.copy()
    if timestamp_col in qc.columns:
        qc[timestamp_col] = pd.to_datetime(qc[timestamp_col], errors="coerce")
        qc = qc.sort_values(timestamp_col).reset_index(drop=True)

    report_rows: list[dict[str, object]] = []
    for column in fruit_columns:
        values = _numeric_series(qc, column)
        step = values.diff().abs()
        in_range = values.between(min_fruit_mm, max_fruit_mm)
        jump_ok = step.le(max_10min_jump_mm) | step.isna()
        valid = values.notna() & in_range & jump_ok
        valid_col = f"{column}_valid"
        reason_col = f"{column}_qc_reason"
        qc[column] = values
        qc[valid_col] = valid
        qc[reason_col] = np.select(
            [values.isna(), ~in_range, ~jump_ok],
            ["missing", "outside_20_120_mm", "jump_gt_1_mm"],
            default="valid",
        )
        report_rows.append(
            {
                "sensor_column": column,
                "sensor_type": "fruit_diameter",
                "valid_count": int(valid.sum()),
                "invalid_count": int((~valid).sum()),
                "max_10min_step_mm": float(step.max(skipna=True)) if step.notna().any() else np.nan,
                "stable_flag": bool(valid.sum() >= min_valid_points and (step.dropna() <= max_10min_jump_mm).all()),
                "insufficient_valid_points": bool(valid.sum() < min_valid_points),
            }
        )

    for column in leaf_columns:
        values = _numeric_series(qc, column)
        valid = values.notna()
        qc[column] = values
        qc[f"{column}_valid"] = valid
        report_rows.append(
            {
                "sensor_column": column,
                "sensor_type": "leaf_temperature",
                "valid_count": int(valid.sum()),
                "invalid_count": int((~valid).sum()),
                "max_10min_step_mm": np.nan,
                "stable_flag": bool(valid.any()),
                "insufficient_valid_points": bool(valid.sum() < min_valid_points),
            }
        )

    return qc, pd.DataFrame(report_rows)

