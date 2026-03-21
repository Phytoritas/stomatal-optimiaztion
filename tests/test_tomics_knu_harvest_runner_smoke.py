from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import load_config
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.current_vs_promoted import (
    run_current_vs_promoted_factorial,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_family_eval import (
    HarvestFamilyRunResult,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_promotion_gate import (
    run_harvest_promotion_gate,
)

from .tomics_knu_test_helpers import (
    write_minimal_knu_config,
    write_minimal_knu_harvest_factorial_config,
    write_minimal_knu_harvest_promotion_gate_config,
    write_sampled_knu_forcing,
    write_sampled_knu_yield_fixture,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script_path(name: str) -> Path:
    return _repo_root() / "scripts" / name


def _run_script(script_name: str, config_path: Path) -> tuple[subprocess.CompletedProcess[str], Path]:
    result = subprocess.run(
        [
            sys.executable,
            str(_script_path(script_name)),
            "--config",
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=_repo_root(),
    )
    output_root = Path(result.stdout.strip().splitlines()[-1]).resolve() if result.stdout.strip() else Path()
    return result, output_root


def _bootstrap_current_vs_promoted_outputs(tmp_path: Path) -> Path:
    repo_root = _repo_root()
    config_path = write_minimal_knu_config(tmp_path, repo_root=repo_root, mode="both")
    run_current_vs_promoted_factorial(config_path=config_path, mode="both")
    return config_path


def assert_harvest_family_factorial_runner_writes_required_outputs_from_sanitized_fixture(
    tmp_path: Path,
) -> None:
    repo_root = _repo_root()
    bootstrap_config = _bootstrap_current_vs_promoted_outputs(tmp_path)
    config_path = write_minimal_knu_harvest_factorial_config(
        tmp_path,
        repo_root=repo_root,
        current_vs_promoted_config=bootstrap_config,
    )

    result, output_root = _run_script("run_tomics_knu_harvest_family_factorial.py", config_path)

    assert result.returncode == 0, result.stderr
    required = {
        "design_table.csv",
        "run_metrics.csv",
        "candidate_ranking.csv",
        "selected_harvest_family.json",
        "canonical_harvest_winners.json",
        "cumulative_harvest_overlay.png",
        "daily_increment_overlay.png",
        "harvest_mass_balance_overlay.png",
        "harvest_family_manifest.json",
        "equation_traceability.csv",
    }
    assert all((output_root / name).exists() for name in required)

    selected = json.loads((output_root / "selected_harvest_family.json").read_text(encoding="utf-8"))
    metrics_df = pd.read_csv(output_root / "run_metrics.csv")
    ranking_df = pd.read_csv(output_root / "candidate_ranking.csv")

    assert {
        "selected_fruit_harvest_family",
        "selected_leaf_harvest_family",
        "selected_fdmc_mode",
        "selected_metric_row",
    }.issubset(selected)
    assert {
        "fruit_harvest_family",
        "leaf_harvest_family",
        "rmse_cumulative_offset",
        "rmse_daily_increment",
        "harvest_mass_balance_error",
    }.issubset(metrics_df.columns)
    assert not ranking_df.empty


def assert_harvest_promotion_gate_runner_writes_scorecard_outputs_from_sanitized_fixture(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = _repo_root()
    bootstrap_config = _bootstrap_current_vs_promoted_outputs(tmp_path)
    extended_forcing_path = write_sampled_knu_forcing(tmp_path, sample_every_rows=360, min_days=14)
    extended_yield_path = write_sampled_knu_yield_fixture(tmp_path, min_days=14)
    factorial_config = write_minimal_knu_harvest_factorial_config(
        tmp_path,
        repo_root=repo_root,
        current_vs_promoted_config=bootstrap_config,
        forcing_path=extended_forcing_path,
        yield_path=extended_yield_path,
    )
    factorial_result, factorial_root = _run_script("run_tomics_knu_harvest_family_factorial.py", factorial_config)
    assert factorial_result.returncode == 0, factorial_result.stderr

    gate_config = write_minimal_knu_harvest_promotion_gate_config(
        tmp_path,
        repo_root=repo_root,
        current_vs_promoted_config=bootstrap_config,
        harvest_factorial_root=factorial_root,
        forcing_path=extended_forcing_path,
        yield_path=extended_yield_path,
    )
    config = load_config(gate_config)

    from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation import harvest_promotion_gate as gate_module

    original_run_harvest_family_simulation = gate_module.run_harvest_family_simulation

    def _with_theta_substrate(*args, **kwargs) -> HarvestFamilyRunResult:
        result = original_run_harvest_family_simulation(*args, **kwargs)
        if "theta_substrate" in result.run_df.columns:
            return result
        run_df = result.run_df.copy()
        run_df["theta_substrate"] = 0.65
        return HarvestFamilyRunResult(
            run_df=run_df,
            model_daily_df=result.model_daily_df,
            validation_df=result.validation_df,
            fruit_events_df=result.fruit_events_df,
            leaf_events_df=result.leaf_events_df,
            harvest_mass_balance_df=result.harvest_mass_balance_df,
            metrics=result.metrics,
        )

    monkeypatch.setattr(gate_module, "run_harvest_family_simulation", _with_theta_substrate)
    output = run_harvest_promotion_gate(config, repo_root=repo_root, config_path=gate_config)
    output_root = Path(output["output_root"])

    required = {
        "harvest_promotion_scorecard.csv",
        "harvest_promotion_decision.md",
        "promotion_guardrails.json",
        "promotion_holdout_overlay.png",
        "winner_stability.csv",
        "harvest_calibration_budget_manifest.json",
    }
    assert all((output_root / name).exists() for name in required)

    scorecard_df = pd.read_csv(output_root / "harvest_promotion_scorecard.csv")
    decision = (output_root / "harvest_promotion_decision.md").read_text(encoding="utf-8")
    guardrails = json.loads((output_root / "promotion_guardrails.json").read_text(encoding="utf-8"))

    assert {"shipped_tomics", "current_selected", "promoted_selected"}.issubset(set(scorecard_df["candidate_label"]))
    assert "Recommendation:" in decision
    assert set(guardrails).issuperset({"guardrails", "current_selected", "promoted_selected", "recommendation"})
