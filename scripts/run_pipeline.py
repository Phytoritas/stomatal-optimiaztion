#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stomatal_optimiaztion.domains.tomato.tthorp.core import (  # noqa: E402
    build_exp_key,
    ensure_dir,
    load_config,
    write_json,
)
from stomatal_optimiaztion.domains.tomato.tthorp.pipelines import (  # noqa: E402
    config_payload_for_exp_key,
    resolve_repo_root,
    run_tomato_legacy_pipeline,
    summarize_tomato_legacy_metrics,
)


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    return {}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run YAML-configured tTHORP pipeline.")
    parser.add_argument(
        "--config",
        default="configs/exp/tomato_dayrun.yaml",
        help="Path to experiment YAML config.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override output directory (default from config).",
    )
    parser.add_argument(
        "--exp-key",
        default=None,
        help="Optional explicit experiment key; otherwise deterministic hash from config payload.",
    )
    return parser.parse_args()


def _resolve_output_dir(config: dict[str, Any], repo_root: Path, override: str | None) -> Path:
    if override:
        raw = Path(override)
    else:
        raw = Path(str(_as_dict(config.get("paths")).get("output_dir", "TOMATO/tTHORP/artifacts/runs")))

    if raw.is_absolute():
        return raw
    return (repo_root / raw).resolve()


def main() -> int:
    args = _parse_args()

    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    repo_root = resolve_repo_root(config, config_path=config_path)

    exp_name = str(_as_dict(config.get("exp")).get("name", "exp"))
    exp_key = args.exp_key or build_exp_key(config_payload_for_exp_key(config), prefix=exp_name)

    output_dir = ensure_dir(_resolve_output_dir(config, repo_root, args.output_dir))
    results = run_tomato_legacy_pipeline(config, repo_root=repo_root, config_path=config_path)
    metrics = summarize_tomato_legacy_metrics(results)

    csv_path = output_dir / f"{exp_key}.csv"
    metrics_path = output_dir / f"{exp_key}.metrics.json"
    results.to_csv(csv_path, index=False)
    write_json(metrics_path, metrics)

    summary = {
        "exp_key": exp_key,
        "rows": int(metrics.get("rows", 0)),
        "output_csv": str(csv_path),
        "metrics_json": str(metrics_path),
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
