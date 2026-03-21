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


def reconstruct_rootzone(
    forcing_df: pd.DataFrame,
    *,
    theta_proxy_mode: str = "bucket_irrigated",
    scenario_ids: tuple[str, ...] = ("dry", "moderate", "wet"),
    theta_min_hard: float = 0.40,
    theta_max_hard: float = 0.85,
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

    theta_stack = pd.DataFrame({"datetime": pd.to_datetime(next(iter(scenario_frames.values()))["datetime"])})
    for scenario_id, frame in scenario_frames.items():
        theta_stack[f"theta_{scenario_id}"] = pd.to_numeric(frame["theta_substrate"], errors="coerce")
    theta_stack["theta_low"] = theta_stack[[column for column in theta_stack.columns if column.startswith("theta_")]].min(axis=1)
    theta_stack["theta_high"] = theta_stack[[column for column in theta_stack.columns if column.startswith("theta_")]].max(axis=1)
    theta_stack["theta_mid"] = theta_stack.get("theta_moderate", theta_stack["theta_low"])
    theta_stack["proxy_uncertainty_width"] = theta_stack["theta_high"] - theta_stack["theta_low"]

    mean_uncertainty = float(pd.to_numeric(theta_stack["proxy_uncertainty_width"], errors="coerce").mean())
    for scenario_id, frame in scenario_frames.items():
        scenario_cfg = DEFAULT_SCENARIOS[scenario_id]
        theta = pd.to_numeric(frame["theta_substrate"], errors="coerce")
        summary_rows.append(
            {
                "theta_proxy_mode": theta_proxy_mode,
                "theta_proxy_scenario": scenario_id,
                "mean_theta": float(theta.mean()),
                "theta_range": float(theta.max() - theta.min()),
                "recharge_event_count": int(pd.to_numeric(frame.get("irrigation_proxy_flag"), errors="coerce").fillna(0.0).sum()),
                "oversaturation_days": _oversaturation_days(frame),
                "proxy_uncertainty_width": mean_uncertainty,
                "rootzone_stress_activation_days": _stress_activation_days(frame),
                "scenario_center": scenario_cfg.center,
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
            "Measured root-zone variables may override the proxy in future runs if supplied.",
        ],
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
            rootzone_cfg.get("output_root", "out/tomics_knu_rootzone_reconstruction"),
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
