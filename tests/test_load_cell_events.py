from __future__ import annotations

import pandas as pd
import pytest

from stomatal_optimiaztion.domains import load_cell
from stomatal_optimiaztion.domains.load_cell import (
    group_events,
    label_points_by_derivative,
    label_points_by_derivative_hysteresis,
    merge_close_events,
    merge_close_events_with_df,
)


def test_load_cell_import_surface_exposes_event_helpers() -> None:
    assert load_cell.label_points_by_derivative is label_points_by_derivative
    assert (
        load_cell.label_points_by_derivative_hysteresis
        is label_points_by_derivative_hysteresis
    )
    assert load_cell.group_events is group_events
    assert load_cell.merge_close_events is merge_close_events
    assert load_cell.merge_close_events_with_df is merge_close_events_with_df


def test_label_points_by_derivative_requires_derivative_column() -> None:
    with pytest.raises(KeyError, match="dW_smooth_kg_s"):
        label_points_by_derivative(pd.DataFrame({"x": [1.0, 2.0]}), 0.1, -0.1)


def test_label_points_by_derivative_assigns_expected_labels() -> None:
    df = pd.DataFrame({"dW_smooth_kg_s": [None, 0.5, -0.6, 0.1]})

    out = label_points_by_derivative(df, irrigation_threshold=0.4, drainage_threshold=-0.4)

    assert out["label"].tolist() == ["baseline", "irrigation", "drainage", "baseline"]


def test_label_points_by_derivative_hysteresis_validates_ratio() -> None:
    df = pd.DataFrame({"dW_smooth_kg_s": [0.0, 1.0]})

    with pytest.raises(ValueError, match="must be in"):
        label_points_by_derivative_hysteresis(
            df,
            irrigation_threshold=0.4,
            drainage_threshold=-0.4,
            hysteresis_ratio=0.0,
        )


def test_label_points_by_derivative_hysteresis_supports_direct_state_transition() -> None:
    df = pd.DataFrame({"dW_smooth_kg_s": [0.8, -0.8, 0.0]})

    out = label_points_by_derivative_hysteresis(
        df,
        irrigation_threshold=0.6,
        drainage_threshold=-0.6,
        hysteresis_ratio=0.5,
        baseline_center=0.0,
    )

    assert out["label"].tolist() == ["irrigation", "drainage", "baseline"]


def test_group_events_requires_label_and_weight_columns() -> None:
    with pytest.raises(KeyError, match="label"):
        group_events(pd.DataFrame({"weight_kg": [1.0, 2.0]}))

    with pytest.raises(KeyError, match="weight_smooth_kg|weight_kg"):
        group_events(pd.DataFrame({"label": ["baseline", "irrigation"]}))


def test_group_events_builds_event_ids_and_summary_rows() -> None:
    index = pd.date_range("2025-01-01 00:00:00", periods=8, freq="s")
    df = pd.DataFrame(
        {
            "label": [
                "baseline",
                "irrigation",
                "irrigation",
                "baseline",
                "drainage",
                "drainage",
                "drainage",
                "baseline",
            ],
            "weight_smooth_kg": [10.0, 10.2, 10.5, 10.5, 10.4, 10.2, 10.1, 10.1],
        },
        index=index,
    )

    out, events_df = group_events(df, min_event_duration_sec=2)

    assert pd.isna(out.iloc[0]["event_id"])
    assert out.iloc[1]["event_id"] == 1
    assert out.iloc[2]["event_id"] == 1
    assert pd.isna(out.iloc[3]["event_id"])
    assert out.iloc[4]["event_id"] == 2
    assert out.iloc[6]["event_id"] == 2
    assert events_df.to_dict("records") == [
        {
            "event_id": 1,
            "event_type": "irrigation",
            "start_time": index[1],
            "end_time": index[2],
            "duration_sec": 2,
            "mass_change_kg": pytest.approx(0.5),
        },
        {
            "event_id": 2,
            "event_type": "drainage",
            "start_time": index[4],
            "end_time": index[6],
            "duration_sec": 3,
            "mass_change_kg": pytest.approx(-0.4),
        },
    ]


def test_group_events_drops_short_events() -> None:
    index = pd.date_range("2025-01-01 00:00:00", periods=3, freq="s")
    df = pd.DataFrame(
        {
            "label": ["baseline", "irrigation", "baseline"],
            "weight_kg": [1.0, 1.2, 1.2],
        },
        index=index,
    )

    out, events_df = group_events(df, min_event_duration_sec=2)

    assert out["event_id"].isna().all()
    assert events_df.empty


def test_merge_close_events_merges_nearby_irrigation_events() -> None:
    events_df = pd.DataFrame(
        [
            {
                "event_id": 10,
                "event_type": "irrigation",
                "start_time": pd.Timestamp("2025-01-01 00:00:00"),
                "end_time": pd.Timestamp("2025-01-01 00:00:02"),
                "duration_sec": 3,
                "mass_change_kg": 0.3,
            },
            {
                "event_id": 11,
                "event_type": "irrigation",
                "start_time": pd.Timestamp("2025-01-01 00:00:05"),
                "end_time": pd.Timestamp("2025-01-01 00:00:06"),
                "duration_sec": 2,
                "mass_change_kg": 0.2,
            },
            {
                "event_id": 12,
                "event_type": "drainage",
                "start_time": pd.Timestamp("2025-01-01 00:00:08"),
                "end_time": pd.Timestamp("2025-01-01 00:00:09"),
                "duration_sec": 2,
                "mass_change_kg": -0.1,
            },
        ]
    )

    merged = merge_close_events(events_df, gap_threshold_sec=3)

    assert merged["event_id"].tolist() == [1, 2]
    assert merged["event_type"].tolist() == ["irrigation", "drainage"]
    assert merged.loc[0, "start_time"] == pd.Timestamp("2025-01-01 00:00:00")
    assert merged.loc[0, "end_time"] == pd.Timestamp("2025-01-01 00:00:06")
    assert merged.loc[0, "duration_sec"] == 7
    assert merged.loc[0, "mass_change_kg"] == pytest.approx(0.5)


def test_merge_close_events_with_df_validates_inputs() -> None:
    index = pd.date_range("2025-01-01 00:00:00", periods=3, freq="s")
    df = pd.DataFrame({"weight_kg": [1.0, 1.1, 1.2]}, index=index)
    events_df = pd.DataFrame(
        [
            {
                "event_id": 1,
                "event_type": "irrigation",
                "start_time": index[1],
                "end_time": index[2],
            }
        ]
    )

    with pytest.raises(ValueError, match=">= 0"):
        merge_close_events_with_df(df, events_df, gap_threshold_sec=-1)

    with pytest.raises(KeyError, match="required columns"):
        merge_close_events_with_df(
            df,
            pd.DataFrame([{"event_id": 1, "event_type": "irrigation"}]),
        )


def test_merge_close_events_with_df_recomputes_mass_change_and_id_map() -> None:
    index = pd.date_range("2025-01-01 00:00:00", periods=8, freq="s")
    df = pd.DataFrame(
        {
            "weight_smooth_kg": [10.0, 10.0, 10.2, 10.3, 10.3, 10.5, 10.6, 10.4],
        },
        index=index,
    )
    events_df = pd.DataFrame(
        [
            {
                "event_id": 1,
                "event_type": "irrigation",
                "start_time": index[1],
                "end_time": index[2],
                "duration_sec": 2,
                "mass_change_kg": 0.2,
            },
            {
                "event_id": 2,
                "event_type": "irrigation",
                "start_time": index[4],
                "end_time": index[5],
                "duration_sec": 2,
                "mass_change_kg": 0.2,
            },
            {
                "event_id": 3,
                "event_type": "drainage",
                "start_time": index[7],
                "end_time": index[7],
                "duration_sec": 1,
                "mass_change_kg": -0.2,
            },
        ]
    )

    merged_df, id_map = merge_close_events_with_df(
        df,
        events_df,
        gap_threshold_sec=2,
    )

    assert merged_df["event_id"].tolist() == [1, 2]
    assert merged_df.loc[0, "event_type"] == "irrigation"
    assert merged_df.loc[0, "start_time"] == index[1]
    assert merged_df.loc[0, "end_time"] == index[5]
    assert merged_df.loc[0, "duration_sec"] == 5
    assert merged_df.loc[0, "mass_change_kg"] == pytest.approx(0.5)
    assert merged_df.loc[0, "source_event_ids"] == [1, 2]
    assert merged_df.loc[1, "event_type"] == "drainage"
    assert merged_df.loc[1, "mass_change_kg"] == pytest.approx(-0.2)
    assert id_map == {1: 1, 2: 1, 3: 2}
