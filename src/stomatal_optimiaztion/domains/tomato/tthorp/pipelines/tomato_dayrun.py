from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from stomatal_optimiaztion.domains.tomato.tthorp.core import (
    build_exp_key,
    ensure_dir,
    load_config,
    schedule_from_config,
    write_json,
)
from stomatal_optimiaztion.domains.tomato.tthorp.pipelines.tomato_legacy import (
    config_payload_for_exp_key,
    resolve_repo_root,
    run_tomato_legacy_pipeline,
    summarize_tomato_legacy_metrics,
)


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, Mapping):
        return {str(key): value for key, value in raw.items()}
    return {}


def _resolve_output_dir(repo_root: Path, output_dir: str | Path) -> Path:
    out_dir = Path(output_dir)
    if out_dir.is_absolute():
        return out_dir
    return (repo_root / out_dir).resolve()


@dataclass(frozen=True, slots=True)
class TomatoDayrunArtifacts:
    output_dir: Path
    df_csv: Path
    meta_json: Path


def run_tomato_dayrun(
    config: Mapping[str, Any],
    *,
    output_dir: str | Path,
    repo_root: Path | None = None,
    config_path: Path | None = None,
) -> TomatoDayrunArtifacts:
    """Run the migrated tomato dayrun and write deterministic artifacts."""

    root = repo_root or resolve_repo_root(config, config_path=config_path)
    out_dir = ensure_dir(_resolve_output_dir(root, output_dir))

    df = run_tomato_legacy_pipeline(config, repo_root=root, config_path=config_path)
    df_path = out_dir / "df.csv"
    meta_path = out_dir / "meta.json"
    df.to_csv(df_path, index=False)

    metrics = summarize_tomato_legacy_metrics(df)
    schedule = schedule_from_config(config)
    exp_cfg = _as_dict(config.get("exp"))
    exp_name = str(exp_cfg.get("name", "tomato_dayrun"))
    exp_key = build_exp_key(config_payload_for_exp_key(config), prefix=exp_name)

    meta: dict[str, Any] = {
        "exp_key": exp_key,
        "exp_name": exp_name,
        "model": "tomato_legacy",
        "rows": int(df.shape[0]),
        "columns": [str(column) for column in df.columns],
        "schedule": {
            "max_steps": schedule.max_steps,
            "default_dt_s": schedule.default_dt_s,
        },
        "metrics": dict(metrics),
    }
    write_json(meta_path, meta)
    return TomatoDayrunArtifacts(output_dir=out_dir, df_csv=df_path, meta_json=meta_path)


def run_tomato_dayrun_from_config(
    config_path: str | Path,
    *,
    output_dir: str | Path,
    repo_root: Path | None = None,
) -> TomatoDayrunArtifacts:
    resolved_config_path = Path(config_path).resolve()
    config = load_config(resolved_config_path)
    root = repo_root or resolve_repo_root(config, config_path=resolved_config_path)
    return run_tomato_dayrun(
        config,
        output_dir=output_dir,
        repo_root=root,
        config_path=resolved_config_path,
    )


__all__ = [
    "TomatoDayrunArtifacts",
    "run_tomato_dayrun",
    "run_tomato_dayrun_from_config",
]
