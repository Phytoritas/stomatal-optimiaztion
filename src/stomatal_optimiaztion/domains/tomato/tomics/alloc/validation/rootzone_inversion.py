from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, load_config
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import resolve_repo_root
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.current_vs_promoted import (
    prepare_knu_bundle,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.runtime import (
    read_rootzone_table,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.irrigation_proxy import (
    infer_irrigation_proxy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.theta_proxy import (
    DEFAULT_SCENARIOS,
    apply_theta_substrate_proxy,
)
from stomatal_optimiaztion.domains.tomato.tomics.plotting import render_partition_compare_bundle


@dataclass(frozen=True, slots=True)
class RootzoneInversionResult:
    summary_df: pd.DataFrame
    band_df: pd.DataFrame
    scenario_frames: dict[str, pd.DataFrame]
    manifest: dict[str, Any]


def _oversaturation_days(frame: pd.DataFrame) -> int:
    work = frame.copy()
    work["date"] = pd.to_datetime(work["datetime"]).dt.normalize()
    flags = pd.to_numeric(work.get("rootzone_saturation"), errors="coerce").fillna(0.0) > 0.0
    return int(flags.groupby(work["date"]).any().sum())


def _stress_activation_days(frame: pd.DataFrame, *, threshold: float = 0.20) -> int:
    work = frame.copy()
    work["date"] = pd.to_datetime(work["datetime"]).dt.normalize()
    flags = pd.to_numeric(work.get("rootzone_multistress"), errors="coerce").fillna(0.0) >= threshold
    return int(flags.groupby(work["date"]).any().sum())


def _recharge_event_count(frame: pd.DataFrame) -> int:
    if "irrigation_proxy_flag" in frame.columns:
        raw_flags = frame["irrigation_proxy_flag"]
    elif "irrigation_recharge_flag" in frame.columns:
        raw_flags = frame["irrigation_recharge_flag"]
    else:
        raw_flags = pd.Series(0.0, index=frame.index)
    flags = pd.to_numeric(raw_flags, errors="coerce").fillna(0.0) > 0.0
    starts = flags & ~flags.shift(fill_value=False)
    return int(starts.sum())


def _measured_rootzone_frame(
    forcing_df: pd.DataFrame,
    measured_rootzone_df: pd.DataFrame,
    *,
    scenario_id: str,
    theta_min_hard: float,
    theta_max_hard: float,
    measured_theta_max_gap: str | pd.Timedelta = "1h",
) -> tuple[pd.DataFrame, dict[str, object]]:
    measured = measured_rootzone_df.copy()
    missing = [column for column in ("datetime", "theta_substrate") if column not in measured.columns]
    if missing:
        raise ValueError(f"Measured rootzone table is missing required columns: {missing}")
    measured["datetime"] = pd.to_datetime(measured["datetime"], errors="coerce")
    measured["theta_substrate"] = pd.to_numeric(measured["theta_substrate"], errors="coerce")
    measured = measured.dropna(subset=["datetime"])
    measured = (
        measured.groupby("datetime", as_index=False)
        .agg(
            theta_measured_raw=("theta_substrate", "mean"),
            measured_sensor_count=("theta_substrate", "count"),
        )
        .sort_values("datetime")
    )

    base = apply_theta_substrate_proxy(
        forcing_df,
        mode="flat_constant",
        scenario="moderate",
        theta_min_hard=theta_min_hard,
        theta_max_hard=theta_max_hard,
    )
    base = base.sort_values("datetime").reset_index(drop=True)
    aligned = pd.merge_asof(
        base,
        measured,
        on="datetime",
        direction="nearest",
        tolerance=pd.Timedelta(measured_theta_max_gap),
    )
    coverage_fraction = float(aligned["theta_measured_raw"].notna().mean()) if not aligned.empty else 0.0
    period_mean = pd.to_numeric(aligned["theta_measured_raw"], errors="coerce").mean()
    if pd.isna(period_mean):
        return base, {
            "used": False,
            "scenario_id": scenario_id,
            "coverage_fraction": coverage_fraction,
            "period_mean_theta_substrate": None,
            "fill_policy": "missing aligned values are filled with the aligned period mean",
            "clip_policy": "theta_substrate is clipped to theta_min_hard/theta_max_hard for model diagnostics",
            "max_alignment_gap": str(pd.Timedelta(measured_theta_max_gap)),
            "filled_row_count": int(len(aligned)),
            "clipped_row_count": 0,
            "skip_reason": "no_numeric_theta_after_alignment",
        }

    filled_raw = aligned["theta_measured_raw"].fillna(float(period_mean))
    clipped_theta = filled_raw.clip(lower=theta_min_hard, upper=theta_max_hard)
    scenario_cfg = DEFAULT_SCENARIOS["moderate"]
    saturation = ((clipped_theta - scenario_cfg.saturation_start) / max(theta_max_hard - scenario_cfg.saturation_start, 1e-6)).clip(
        lower=0.0,
        upper=1.0,
    )
    aligned["theta_proxy_mode"] = "measured_rootzone"
    aligned["theta_proxy_scenario"] = scenario_id
    aligned["theta_substrate"] = clipped_theta
    aligned["theta_measurement_source"] = aligned["theta_measured_raw"].notna().map(
        {True: "measured", False: "filled_with_period_mean"}
    )
    aligned["theta_measurement_was_clipped"] = clipped_theta.ne(filled_raw)
    aligned["theta_measurement_period_mean"] = float(period_mean)
    aligned["rootzone_saturation"] = saturation
    aligned["rootzone_multistress"] = (
        0.65 * aligned["rootzone_saturation"] + 0.35 * aligned["rootzone_temperature_stress"]
    ).clip(lower=0.0, upper=1.0)
    aligned["irrigation_recharge_flag"] = 0
    summary = {
        "used": True,
        "scenario_id": scenario_id,
        "coverage_fraction": coverage_fraction,
        "period_mean_theta_substrate": float(period_mean),
        "fill_policy": "missing aligned values are filled with the aligned period mean",
        "clip_policy": "theta_substrate is clipped to theta_min_hard/theta_max_hard for model diagnostics",
        "max_alignment_gap": str(pd.Timedelta(measured_theta_max_gap)),
        "filled_row_count": int(aligned["theta_measured_raw"].isna().sum()),
        "clipped_row_count": int(aligned["theta_measurement_was_clipped"].sum()),
    }
    return aligned, summary


def reconstruct_rootzone(
    forcing_df: pd.DataFrame,
    *,
    theta_proxy_mode: str = "bucket_irrigated",
    scenario_ids: tuple[str, ...] = ("dry", "moderate", "wet"),
    theta_min_hard: float = 0.40,
    theta_max_hard: float = 0.85,
    measured_rootzone_df: pd.DataFrame | None = None,
    measured_scenario_id: str = "measured",
    measured_theta_coverage_min: float = 0.50,
    measured_theta_max_gap: str | pd.Timedelta = "1h",
) -> RootzoneInversionResult:
    scenario_frames: dict[str, pd.DataFrame] = {}
    summary_rows: list[dict[str, object]] = []
    for scenario_id in scenario_ids:
        proxy = apply_theta_substrate_proxy(
            forcing_df,
            mode=theta_proxy_mode,
            scenario=scenario_id,
            theta_min_hard=theta_min_hard,
            theta_max_hard=theta_max_hard,
        )
        proxy = infer_irrigation_proxy(proxy)
        scenario_frames[scenario_id] = proxy

    measured_summary: dict[str, object] = {
        "used": False,
        "scenario_id": measured_scenario_id,
        "coverage_fraction": 0.0,
        "minimum_coverage_fraction": float(measured_theta_coverage_min),
    }
    if measured_rootzone_df is not None:
        measured_frame, measured_summary = _measured_rootzone_frame(
            forcing_df,
            measured_rootzone_df,
            scenario_id=measured_scenario_id,
            theta_min_hard=theta_min_hard,
            theta_max_hard=theta_max_hard,
            measured_theta_max_gap=measured_theta_max_gap,
        )
        measured_summary["minimum_coverage_fraction"] = float(measured_theta_coverage_min)
        if float(measured_summary["coverage_fraction"]) >= float(measured_theta_coverage_min):
            scenario_frames[measured_scenario_id] = measured_frame
        else:
            measured_summary["used"] = False
            measured_summary["skip_reason"] = "coverage_below_minimum"

    theta_stack = pd.DataFrame({"datetime": pd.to_datetime(next(iter(scenario_frames.values()))["datetime"])})
    for scenario_id, frame in scenario_frames.items():
        theta_stack[f"theta_{scenario_id}"] = pd.to_numeric(frame["theta_substrate"], errors="coerce")
    theta_stack["theta_low"] = theta_stack[[column for column in theta_stack.columns if column.startswith("theta_")]].min(axis=1)
    theta_stack["theta_high"] = theta_stack[[column for column in theta_stack.columns if column.startswith("theta_")]].max(axis=1)
    theta_stack["theta_mid"] = theta_stack.get("theta_moderate", theta_stack["theta_low"])
    theta_stack["proxy_uncertainty_width"] = theta_stack["theta_high"] - theta_stack["theta_low"]

    mean_uncertainty = float(pd.to_numeric(theta_stack["proxy_uncertainty_width"], errors="coerce").mean())
    for scenario_id, frame in scenario_frames.items():
        theta = pd.to_numeric(frame["theta_substrate"], errors="coerce")
        scenario_cfg = DEFAULT_SCENARIOS.get(scenario_id)
        mode_label = str(frame["theta_proxy_mode"].iloc[0]) if "theta_proxy_mode" in frame.columns else theta_proxy_mode
        summary_rows.append(
            {
                "theta_proxy_mode": mode_label,
                "theta_proxy_scenario": scenario_id,
                "theta_source": "proxy" if scenario_cfg is not None else "measured_rootzone",
                "mean_theta": float(theta.mean()),
                "theta_range": float(theta.max() - theta.min()),
                "recharge_event_count": _recharge_event_count(frame),
                "oversaturation_days": _oversaturation_days(frame),
                "proxy_uncertainty_width": mean_uncertainty,
                "rootzone_stress_activation_days": _stress_activation_days(frame),
                "scenario_center": scenario_cfg.center if scenario_cfg is not None else float(theta.mean()),
            }
        )

    manifest = {
        "theta_proxy_mode": theta_proxy_mode,
        "scenario_ids": list(scenario_ids),
        "hard_bounds": {
            "theta_min_hard": theta_min_hard,
            "theta_max_hard": theta_max_hard,
        },
        "assumptions": [
            "Greenhouse-soilless proxy bounds are conservative and explicit.",
            "Irrigation timing is inferred from daylight demand windows when measured irrigation is unavailable.",
            "Measured root-zone theta_substrate is added as a separate scenario when supplied with sufficient coverage.",
        ],
        "measured_rootzone": measured_summary,
    }
    return RootzoneInversionResult(
        summary_df=pd.DataFrame(summary_rows),
        band_df=theta_stack,
        scenario_frames=scenario_frames,
        manifest=manifest,
    )


def write_rootzone_manifest(*, output_root: Path, manifest: dict[str, Any]) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / "rootzone_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _resolve_config_path(raw: str | Path, *, repo_root: Path, config_path: Path) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    probes = [
        (config_path.parent / candidate).resolve(),
        (repo_root / candidate).resolve(),
    ]
    for probe in probes:
        if probe.exists():
            return probe
    return probes[0]


def run_knu_rootzone_reconstruction(*, config_path: str | Path) -> dict[str, object]:
    resolved_config_path = Path(config_path).resolve()
    config = load_config(resolved_config_path)
    repo_root = resolve_repo_root(config, config_path=resolved_config_path)
    prepared_bundle = prepare_knu_bundle(config, repo_root=repo_root, config_path=resolved_config_path)
    rootzone_cfg = _as_dict(config.get("rootzone_reconstruction"))
    output_root = ensure_dir(
        _resolve_config_path(
            rootzone_cfg.get("output_root", "out/tomics/validation/knu/fairness/rootzone-reconstruction"),
            repo_root=repo_root,
            config_path=resolved_config_path,
        )
    )
    result = reconstruct_rootzone(
        prepared_bundle.data.forcing_df,
        theta_proxy_mode=str(rootzone_cfg.get("theta_proxy_mode", "bucket_irrigated")),
        scenario_ids=tuple(str(value) for value in rootzone_cfg.get("scenario_ids", ["dry", "moderate", "wet"])),
        theta_min_hard=float(rootzone_cfg.get("theta_min_hard", 0.40)),
        theta_max_hard=float(rootzone_cfg.get("theta_max_hard", 0.85)),
        measured_rootzone_df=read_rootzone_table(prepared_bundle.data_contract.rootzone_path)
        if prepared_bundle.data_contract.rootzone_path is not None
        else None,
        measured_scenario_id=str(rootzone_cfg.get("measured_scenario_id", "measured")),
        measured_theta_coverage_min=float(rootzone_cfg.get("measured_theta_coverage_min", 0.50)),
        measured_theta_max_gap=str(rootzone_cfg.get("measured_theta_max_gap", "1h")),
    )
    result.summary_df.to_csv(output_root / "rootzone_summary.csv", index=False)
    result.band_df.to_csv(output_root / "theta_uncertainty_band.csv", index=False)
    manifest_path = write_rootzone_manifest(output_root=output_root, manifest=result.manifest)
    plot_spec = _resolve_config_path(
        _as_dict(config.get("plots")).get(
            "theta_proxy_diagnostics_spec",
            "configs/plotkit/tomics/knu_theta_proxy_diagnostics.yaml",
        ),
        repo_root=repo_root,
        config_path=resolved_config_path,
    )
    render_partition_compare_bundle(
        runs={
            scenario_id: frame[["datetime", "theta_substrate", "demand_index", "rootzone_multistress", "rootzone_saturation"]].copy()
            for scenario_id, frame in result.scenario_frames.items()
        },
        out_path=output_root / "theta_proxy_overlay.png",
        spec_path=plot_spec,
    )
    return {
        "output_root": str(output_root),
        "rootzone_summary_csv": str(output_root / "rootzone_summary.csv"),
        "theta_uncertainty_band_csv": str(output_root / "theta_uncertainty_band.csv"),
        "rootzone_manifest_json": str(manifest_path),
    }


__all__ = [
    "RootzoneInversionResult",
    "reconstruct_rootzone",
    "run_knu_rootzone_reconstruction",
    "write_rootzone_manifest",
]
