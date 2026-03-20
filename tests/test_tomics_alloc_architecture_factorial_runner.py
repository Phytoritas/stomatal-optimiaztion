from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pandas as pd


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "run_tomics_allocation_factorial.py"


def test_architecture_factorial_runner_writes_required_bundle(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config_path = tmp_path / "tomics_allocation_factorial.yaml"
    output_root = tmp_path / "factorial-output"
    forcing_path = repo_root / "data" / "forcing" / "tomics_tomato_example.csv"

    config_path.write_text(
        "\n".join(
            [
                "exp:",
                "  name: architecture_factorial_test",
                "pipeline:",
                "  model: tomato_legacy",
                "  partition_policy: tomics",
                "  allocation_scheme: 4pool",
                "  theta_substrate: 0.33",
                "  fixed_lai: 2.4",
                "forcing:",
                f"  csv_path: {forcing_path.as_posix()}",
                "  default_dt_s: 21600",
                "  default_co2_ppm: 420",
                "  max_steps: 24",
                "  repeat_cycles: 4",
                "study:",
                "  shortlist_count: 1",
                "  wet_theta_threshold: 0.40",
                "  canopy_lai_floor: 2.0",
                "  leaf_fraction_floor: 0.18",
                "stage1:",
                "  theta_substrate: [0.20, 0.33]",
                "  candidates:",
                "    - architecture_id: shipped_default_tomics",
                "      partition_policy: tomics",
                "      fruit_structure_mode: tomsim_truss_cohort",
                "      fruit_partition_mode: legacy_sink_exact",
                "      vegetative_demand_mode: tomsim_constant_wholecrop",
                "      reserve_buffer_mode: 'off'",
                "      fruit_feedback_mode: 'off'",
                "      sla_mode: derived_not_driver",
                "      maintenance_mode: rgr_adjusted",
                "      canopy_governor_mode: lai_band",
                "      root_representation_mode: bounded_explicit_root",
                "      thorp_root_correction_mode: bounded",
                "      temporal_coupling_mode: daily_alloc",
                "      allocation_scheme: 4pool",
                "    - architecture_id: research_candidate",
                "      partition_policy: tomics_alloc_research",
                "      fruit_structure_mode: tomsim_truss_cohort",
                "      fruit_partition_mode: legacy_sink_exact",
                "      vegetative_demand_mode: dekoning_vegetative_unit",
                "      reserve_buffer_mode: tomsim_storage_pool",
                "      fruit_feedback_mode: 'off'",
                "      sla_mode: derived_not_driver",
                "      maintenance_mode: rgr_adjusted",
                "      canopy_governor_mode: lai_band_plus_leaf_floor",
                "      root_representation_mode: bounded_explicit_root",
                "      thorp_root_correction_mode: bounded_hysteretic",
                "      temporal_coupling_mode: buffered_daily",
                "      allocation_scheme: 4pool",
                "stage2:",
                "  theta_substrate: 0.33",
                "  parameter_axes:",
                "    wet_root_cap: [0.08, 0.10]",
                "    dry_root_cap: [0.15]",
                "stage3:",
                "  theta_substrate:",
                "    wet: 0.50",
                "    dry: 0.20",
                "  fruit_load_regimes:",
                "    baseline: 1.0",
                "paths:",
                f"  repo_root: {repo_root.as_posix()}",
                "  output_root: out/tomics_allocation_factorial",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(_script_path()),
            "--config",
            str(config_path),
            "--output-root",
            str(output_root),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout.strip().splitlines()[-1])

    required = {
        "design_table_csv",
        "run_metrics_csv",
        "interaction_summary_csv",
        "candidate_ranking_csv",
        "selected_architecture_json",
        "decision_bundle_md",
        "equation_traceability_csv",
        "summary_plot",
        "summary_plot_metadata",
        "main_effects_plot",
        "main_effects_plot_metadata",
    }
    assert required.issubset(summary)

    for key in required:
        assert Path(summary[key]).exists(), key
    assert not Path(summary["summary_plot"]).with_suffix(".pdf").exists()
    assert not Path(summary["main_effects_plot"]).with_suffix(".pdf").exists()

    metrics_df = pd.read_csv(summary["run_metrics_csv"])
    assert {
        "architecture_id",
        "fruit_structure_mode",
        "reserve_buffer_mode",
        "fruit_feedback_mode",
        "final_fruit_dry_weight",
        "fruit_anchor_error_vs_legacy",
        "canopy_collapse_days",
    }.issubset(metrics_df.columns)


def test_gap_analysis_artifacts_contain_research_only_recommendation() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    gap_doc = (repo_root / "docs" / "architecture" / "review" / "tomics-allocation-gap-analysis.md").read_text(
        encoding="utf-8"
    )
    pipeline_doc = (repo_root / "docs" / "architecture" / "tomics-allocation-architecture-pipeline.md").read_text(
        encoding="utf-8"
    )

    assert "Current shipped TOMICS default" in gap_doc
    assert "Kuijpers hybrid candidate" in gap_doc
    assert "research-only" in gap_doc
    assert "canopy_collapse_days" in pipeline_doc
    assert "partition_policy: tomics_alloc_research" in pipeline_doc
