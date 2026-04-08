from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.metadata import (
    build_dataset_inventory_summary,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.registry import (
    DatasetRegistry,
)


KEY_COLUMNS = ["fruit_harvest_family", "leaf_harvest_family", "fdmc_mode"]
EMPTY_SCORECARD_COLUMNS = [
    *KEY_COLUMNS,
    "mean_score",
    "mean_rmse_cumulative_offset",
    "mean_rmse_daily_increment",
    "max_harvest_mass_balance_error",
    "max_canopy_collapse_days",
    "mean_native_family_state_fraction",
    "mean_proxy_family_state_fraction",
    "mean_shared_tdvs_proxy_fraction",
    "family_state_mode_distribution",
    "proxy_mode_used_distribution",
    "dataset_count",
    "dataset_ids",
    "dataset_win_count",
    "cross_dataset_stability_score",
]


def _aggregate_distribution_json(series: pd.Series) -> str:
    if series is None or series.empty:
        return json.dumps({}, sort_keys=True)
    aggregate: dict[str, float] = {}
    count = 0
    for raw in series.dropna():
        try:
            parsed = json.loads(str(raw))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(parsed, dict):
            continue
        count += 1
        for key, value in parsed.items():
            numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
            if pd.isna(numeric):
                continue
            aggregate[str(key)] = aggregate.get(str(key), 0.0) + float(numeric)
    if count <= 0:
        return json.dumps({}, sort_keys=True)
    return json.dumps({key: value / count for key, value in sorted(aggregate.items())}, sort_keys=True)


def load_dataset_factorial_outputs(
    *,
    dataset_id: str,
    factorial_root: str | Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    root = Path(factorial_root)
    ranking_path = root / "candidate_ranking.csv"
    selected_path = root / "selected_harvest_family.json"
    ranking_df = pd.read_csv(ranking_path)
    ranking_df["dataset_id"] = dataset_id
    selected_payload = json.loads(selected_path.read_text(encoding="utf-8"))
    selected_payload["dataset_id"] = dataset_id
    return ranking_df, selected_payload


def build_cross_dataset_scorecard(
    dataset_rankings: list[pd.DataFrame],
    dataset_selected_payloads: list[dict[str, Any]],
    *,
    registry: DatasetRegistry | None = None,
) -> pd.DataFrame:
    if not dataset_rankings:
        return pd.DataFrame(columns=EMPTY_SCORECARD_COLUMNS)
    combined = pd.concat(dataset_rankings, ignore_index=True)
    dataset_count = max(len({str(value) for value in combined["dataset_id"].dropna()}), 1)
    scorecard = (
        combined.groupby(KEY_COLUMNS, dropna=False, as_index=False)
        .agg(
            mean_score=("mean_score", "mean"),
            mean_rmse_cumulative_offset=("mean_rmse_cumulative_offset", "mean"),
            mean_rmse_daily_increment=("mean_rmse_daily_increment", "mean"),
            max_harvest_mass_balance_error=("max_harvest_mass_balance_error", "max"),
            max_canopy_collapse_days=("max_canopy_collapse_days", "max"),
            mean_native_family_state_fraction=("mean_native_family_state_fraction", "mean"),
            mean_proxy_family_state_fraction=("mean_proxy_family_state_fraction", "mean"),
            mean_shared_tdvs_proxy_fraction=("mean_shared_tdvs_proxy_fraction", "mean"),
            family_state_mode_distribution=("family_state_mode_distribution", _aggregate_distribution_json),
            proxy_mode_used_distribution=("proxy_mode_used_distribution", _aggregate_distribution_json),
            dataset_count=("dataset_id", "nunique"),
            dataset_ids=("dataset_id", lambda values: json.dumps(sorted({str(value) for value in values}), sort_keys=True)),
        )
        .sort_values(["mean_score", "mean_rmse_cumulative_offset"], ascending=[False, True])
        .reset_index(drop=True)
    )
    winner_counts: dict[tuple[str, str, str], int] = {}
    for payload in dataset_selected_payloads:
        key = (
            str(payload.get("selected_fruit_harvest_family", "")),
            str(payload.get("selected_leaf_harvest_family", "")),
            str(payload.get("selected_fdmc_mode", "")),
        )
        winner_counts[key] = winner_counts.get(key, 0) + 1
    scorecard["dataset_win_count"] = scorecard.apply(
        lambda row: winner_counts.get(
            (str(row["fruit_harvest_family"]), str(row["leaf_harvest_family"]), str(row["fdmc_mode"])),
            0,
        ),
        axis=1,
    )
    scorecard["cross_dataset_stability_score"] = scorecard["dataset_win_count"].astype(float) / float(dataset_count)
    if registry is not None:
        summary = build_dataset_inventory_summary(list(registry.datasets))
        scorecard["total_registry_datasets"] = int(summary["total_registry_datasets"])
        scorecard["runnable_measured_harvest_datasets"] = int(summary["runnable_measured_harvest_datasets"])
        scorecard["proxy_datasets"] = int(summary["proxy_datasets"])
        scorecard["context_only_datasets"] = int(summary["context_only_datasets"])
        scorecard["blocked_by_missing_raw_fixture"] = int(summary["blocked_by_missing_raw_fixture"])
        scorecard["blocked_by_missing_basis_or_density"] = int(summary["blocked_by_missing_basis_or_density"])
        scorecard["blocked_by_missing_cumulative_mapping"] = int(summary["blocked_by_missing_cumulative_mapping"])
    return scorecard


def build_cross_dataset_scorecard_report(
    scorecard_df: pd.DataFrame,
    *,
    registry: DatasetRegistry,
    skipped_datasets: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "dataset_inventory_summary": build_dataset_inventory_summary(list(registry.datasets)),
        "runnable_measured_dataset_ids": [dataset.dataset_id for dataset in registry.runnable_measured_harvest_datasets()],
        "draft_dataset_ids": [dataset.dataset_id for dataset in registry.draft_datasets()],
        "skipped_datasets": skipped_datasets or [],
        "scorecard_rows": scorecard_df.to_dict(orient="records"),
    }


def build_cross_dataset_inventory_scorecard(
    registry: DatasetRegistry,
    *,
    scorecard_df: pd.DataFrame | None = None,
    skipped_datasets: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return build_cross_dataset_scorecard_report(
        scorecard_df if scorecard_df is not None else pd.DataFrame(columns=EMPTY_SCORECARD_COLUMNS),
        registry=registry,
        skipped_datasets=skipped_datasets,
    )


__all__ = [
    "EMPTY_SCORECARD_COLUMNS",
    "KEY_COLUMNS",
    "build_cross_dataset_inventory_scorecard",
    "build_cross_dataset_scorecard",
    "build_cross_dataset_scorecard_report",
    "load_dataset_factorial_outputs",
]
