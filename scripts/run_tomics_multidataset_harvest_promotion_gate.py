from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, load_config, write_json
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import resolve_repo_root
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.cross_dataset_gate import (
    build_cross_dataset_guardrail_summary,
)


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _resolve_config_path(raw: str | Path, *, repo_root: Path, config_path: Path) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    config_probe = (config_path.parent / candidate).resolve()
    repo_probe = (repo_root / candidate).resolve()
    probes = [config_probe, repo_probe]
    for probe in probes:
        if probe.exists():
            return probe
    return repo_probe


def _resolve_artifact_path(raw: str | Path, *, repo_root: Path) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    return (repo_root / candidate).resolve()


def run_multidataset_harvest_promotion_gate(
    config: dict[str, Any],
    *,
    repo_root: Path,
    config_path: Path,
) -> dict[str, object]:
    validation_cfg = _as_dict(config.get("validation"))
    gate_cfg = _as_dict(validation_cfg.get("multidataset_promotion_gate"))
    output_root = ensure_dir(
        _resolve_artifact_path(
            gate_cfg.get("output_root", "out/tomics_multidataset_harvest_promotion_gate"),
            repo_root=repo_root,
        )
    )
    scorecard_root = _resolve_artifact_path(
        gate_cfg.get("scorecard_root", "out/tomics_multidataset_harvest_factorial"),
        repo_root=repo_root,
    )
    scorecard_df = pd.read_csv(scorecard_root / "cross_dataset_scorecard.csv")
    summary = build_cross_dataset_guardrail_summary(
        scorecard_df,
        native_state_coverage_min=float(gate_cfg.get("winner_native_state_coverage_min", 0.5)),
        shared_tdvs_proxy_fraction_max=float(gate_cfg.get("winner_shared_tdvs_proxy_fraction_max", 0.5)),
        cross_dataset_stability_score_min=float(gate_cfg.get("cross_dataset_stability_score_min", 0.5)),
        min_dataset_count=int(gate_cfg.get("min_dataset_count", 2)),
    )
    scorecard_df.to_csv(output_root / "cross_dataset_promotion_scorecard.csv", index=False)
    write_json(output_root / "cross_dataset_guardrails.json", summary)
    selected = summary.get("selected_candidate", {})
    decision_lines = [
        "# Cross-dataset Harvest Promotion Gate",
        "",
        f"Recommendation: `{summary['recommendation']}`",
        "",
    ]
    if selected:
        decision_lines.extend(
            [
                "Summary:",
                f"- selected family: {selected.get('fruit_harvest_family')} + {selected.get('leaf_harvest_family')} + {selected.get('fdmc_mode')}",
                f"- dataset count: {selected.get('dataset_count')}",
                f"- cross-dataset stability score: {float(selected.get('cross_dataset_stability_score', 0.0)):.2f}",
                f"- native-state coverage: {float(selected.get('winner_native_state_coverage', 0.0)):.2f}",
                f"- shared-TDVS proxy fraction: {float(selected.get('winner_shared_tdvs_proxy_fraction', 0.0)):.2f}",
                f"- proxy-heavy flag: {bool(selected.get('winner_proxy_heavy_flag', False))}",
                f"- single-dataset-only flag: {bool(selected.get('single_dataset_only_flag', False))}",
            ]
        )
    (output_root / "cross_dataset_promotion_decision.md").write_text(
        "\n".join(decision_lines) + "\n",
        encoding="utf-8",
    )
    return {"output_root": str(output_root), "selected_candidate": selected}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the TOMICS multi-dataset harvest promotion gate scaffold.")
    parser.add_argument("--config", required=True, help="Path to multi-dataset promotion-gate YAML config.")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    repo_root = resolve_repo_root(config, config_path=config_path)
    result = run_multidataset_harvest_promotion_gate(config, repo_root=repo_root, config_path=config_path)
    print(result["output_root"])


if __name__ == "__main__":
    main()
