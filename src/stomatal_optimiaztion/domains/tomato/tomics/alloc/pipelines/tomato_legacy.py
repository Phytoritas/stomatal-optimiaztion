from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.interface import simulate
from stomatal_optimiaztion.domains.tomato.tomics.alloc.models.tomato_legacy import (
    iter_forcing_csv,
    make_tomato_legacy_model,
)


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, Mapping):
        return {str(key): value for key, value in raw.items()}
    return {}


def _policy_params_from_pipeline(pipeline_cfg: Mapping[str, object]) -> dict[str, object]:
    params = _as_dict(pipeline_cfg.get("partition_policy_params"))
    tomics = _as_dict(pipeline_cfg.get("tomics"))
    if tomics:
        params = {**params, **tomics}
    return params


def _resolve_existing_path(
    path: str | Path,
    *,
    config_path: Path | None = None,
    repo_root: Path | None = None,
) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate

    probes: list[Path] = []
    if config_path is not None:
        probes.append((config_path.parent / candidate).resolve())
    if repo_root is not None:
        probes.append((repo_root / candidate).resolve())
    probes.append((Path.cwd() / candidate).resolve())

    for probe in probes:
        if probe.exists():
            return probe
    return probes[0]


def _looks_like_repo_root(path: Path) -> bool:
    staged_root = (path / "src" / "stomatal_optimiaztion").exists() and (
        (path / "pyproject.toml").exists() or (path / ".git").exists()
    )
    legacy_root = (path / "THORP").exists() and (path / "TOMATO").exists()
    return staged_root or legacy_root


def _default_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if _looks_like_repo_root(parent):
            return parent
    parents = Path(__file__).resolve().parents
    return parents[min(6, len(parents) - 1)]


def _infer_repo_root(config_path: Path | None) -> Path | None:
    if config_path is None:
        return None
    for parent in config_path.resolve().parents:
        if _looks_like_repo_root(parent):
            return parent
    return None


def resolve_repo_root(config: Mapping[str, object], *, config_path: Path | None = None) -> Path:
    paths_cfg = _as_dict(config.get("paths"))
    repo_root_raw = paths_cfg.get("repo_root")
    if repo_root_raw is not None:
        configured = _resolve_existing_path(str(repo_root_raw), config_path=config_path)
        if configured.exists():
            return configured
        raise FileNotFoundError(f"Configured repo_root does not exist: {configured}")

    inferred = _infer_repo_root(config_path)
    if inferred is not None:
        return inferred
    return _default_repo_root()


def resolve_forcing_path(
    config: Mapping[str, object],
    *,
    repo_root: Path,
    config_path: Path | None = None,
) -> Path:
    forcing_cfg = _as_dict(config.get("forcing"))
    forcing_raw = forcing_cfg.get("csv_path")
    if forcing_raw is None:
        raise KeyError("forcing.csv_path is required for tomato_legacy pipeline.")
    return _resolve_existing_path(str(forcing_raw), config_path=config_path, repo_root=repo_root)


def config_payload_for_exp_key(config: Mapping[str, object]) -> dict[str, object]:
    return {
        "exp": _as_dict(config.get("exp")),
        "pipeline": _as_dict(config.get("pipeline")),
        "forcing": _as_dict(config.get("forcing")),
    }


def run_tomato_legacy_pipeline(
    config: Mapping[str, object],
    *,
    repo_root: Path | None = None,
    config_path: Path | None = None,
) -> pd.DataFrame:
    pipeline_cfg = _as_dict(config.get("pipeline"))
    forcing_cfg = _as_dict(config.get("forcing"))

    model_name = str(pipeline_cfg.get("model", "tomato_legacy"))
    if model_name != "tomato_legacy":
        raise ValueError(
            f"Unsupported pipeline.model {model_name!r}; only 'tomato_legacy' is supported."
        )

    root = repo_root or resolve_repo_root(config, config_path=config_path)
    forcing_path = resolve_forcing_path(config, repo_root=root, config_path=config_path)

    max_steps_raw = forcing_cfg.get("max_steps")
    max_steps = None if max_steps_raw is None else max(0, int(max_steps_raw))

    fixed_lai_raw = pipeline_cfg.get("fixed_lai")
    fixed_lai = None if fixed_lai_raw is None else float(fixed_lai_raw)
    partition_policy_raw = pipeline_cfg.get("partition_policy")
    partition_policy = None if partition_policy_raw is None else str(partition_policy_raw)
    allocation_scheme = str(pipeline_cfg.get("allocation_scheme", "4pool"))
    partition_policy_params = _policy_params_from_pipeline(pipeline_cfg)
    initial_state_overrides = _as_dict(pipeline_cfg.get("initial_state_overrides"))

    forcing = iter_forcing_csv(
        forcing_path,
        max_steps=max_steps,
        default_dt_s=float(forcing_cfg.get("default_dt_s", 6.0 * 3600.0)),
        default_co2_ppm=float(forcing_cfg.get("default_co2_ppm", 420.0)),
        default_n_fruits_per_truss=int(forcing_cfg.get("default_n_fruits_per_truss", 4)),
    )
    model = make_tomato_legacy_model(
        theta_substrate=float(pipeline_cfg.get("theta_substrate", 0.33)),
        fixed_lai=fixed_lai,
        partition_policy=partition_policy,
        allocation_scheme=allocation_scheme,
        partition_policy_params=partition_policy_params,
        initial_state_overrides=initial_state_overrides,
        internal_harvest_enabled=bool(pipeline_cfg.get("internal_harvest_enabled", True)),
    )
    return simulate(model=model, forcing=forcing, max_steps=max_steps)


def summarize_tomato_legacy_metrics(df: pd.DataFrame) -> dict[str, float | int]:
    metrics: dict[str, float | int] = {"rows": int(df.shape[0])}
    if df.empty:
        return metrics

    for column in (
        "theta_substrate",
        "water_supply_stress",
        "e",
        "g_w",
        "a_n",
        "r_d",
        "alloc_frac_fruit",
        "alloc_frac_leaf",
        "alloc_frac_stem",
        "alloc_frac_root",
        "alloc_frac_shoot",
    ):
        if column in df.columns:
            metrics[f"mean_{column}"] = float(df[column].astype(float).mean())

    if "a_n" in df.columns:
        metrics["sum_a_n"] = float(df["a_n"].astype(float).sum())
    if "LAI" in df.columns:
        metrics["final_lai"] = float(df["LAI"].astype(float).iloc[-1])
    if "total_dry_weight_g_m2" in df.columns:
        metrics["final_total_dry_weight_g_m2"] = float(
            df["total_dry_weight_g_m2"].astype(float).iloc[-1]
        )
    return metrics


__all__ = [
    "config_payload_for_exp_key",
    "resolve_forcing_path",
    "resolve_repo_root",
    "run_tomato_legacy_pipeline",
    "summarize_tomato_legacy_metrics",
]
