from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any, Mapping

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, write_json
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_claim_register import write_claim_register
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_cross_dataset_gate import (
    CROSS_DATASET_BLOCKER,
    build_haf_cross_dataset_gate_payload,
    write_haf_cross_dataset_gate_outputs,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_gate_outputs import (
    as_dict,
    bool_value,
    check_row,
    float_value,
    int_value,
    read_json,
    read_required_csv,
    resolve_artifact_path,
    write_key_value_csv,
    write_markdown_table,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_new_phytologist_readiness import (
    write_new_phytologist_readiness_matrix,
)


GATE_PIPELINE_VERSION = "haf_promotion_gate_v1"
BASE_PRS = [309, 311, 313]
REQUIRED_LATENT_GUARDRAILS = {
    "no_leaf_collapse",
    "no_wet_root_excess",
    "stress_gated_root_increase",
    "sum_to_one",
    "no_raw_THORP",
    "no_fruit_diameter_calibration",
    "no_direct_validation_claim",
}


def _git_value(repo_root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    return result.stdout.strip() or "unavailable"


def _candidate_row(frame: pd.DataFrame, candidate_id: str) -> pd.Series | None:
    if frame.empty or "candidate_id" not in frame.columns:
        return None
    matches = frame.loc[frame["candidate_id"].astype(str).eq(candidate_id)]
    if matches.empty:
        return None
    return matches.iloc[0]


def _best_research_candidate(rankings: pd.DataFrame) -> pd.Series:
    research = rankings.loc[~rankings["allocator_family"].astype(str).eq("shipped_tomics")].copy()
    if research.empty:
        return rankings.iloc[0]
    return research.iloc[0]


def _all_latent_guardrails_pass(frame: pd.DataFrame) -> bool:
    if frame.empty or "pass_fail" not in frame.columns or "guardrail_name" not in frame.columns:
        return False
    observed = set(frame["guardrail_name"].dropna().astype(str))
    if not REQUIRED_LATENT_GUARDRAILS.issubset(observed):
        return False
    required = frame.loc[frame["guardrail_name"].astype(str).isin(REQUIRED_LATENT_GUARDRAILS)]
    return required["pass_fail"].apply(lambda value: bool_value(value)).all()


def _selected_candidate_id(haf_root: Path, rankings: pd.DataFrame) -> str:
    selected_path = haf_root / "harvest_family_selected_research_candidate.json"
    if selected_path.exists():
        selected = read_json(selected_path, artifact_label="harvest_family_selected_research_candidate")
        raw = selected.get("selected_candidate_id")
        if raw:
            return str(raw)
    return str(_best_research_candidate(rankings)["candidate_id"])


def _candidate_max_bool(frame: pd.DataFrame, candidate_id: str, column: str) -> bool:
    if frame.empty or column not in frame.columns or "candidate_id" not in frame.columns:
        return True
    selected = frame.loc[frame["candidate_id"].astype(str).eq(candidate_id)]
    if selected.empty:
        return True
    return selected[column].apply(lambda value: bool_value(value)).any()


def _candidate_max_abs(frame: pd.DataFrame, candidate_id: str, column: str) -> float:
    if frame.empty or column not in frame.columns or "candidate_id" not in frame.columns:
        return float("inf")
    selected = frame.loc[frame["candidate_id"].astype(str).eq(candidate_id)]
    if selected.empty:
        return float("inf")
    values = pd.to_numeric(selected[column], errors="coerce").abs()
    if values.dropna().empty:
        return float("inf")
    return float(values.max())


def _candidate_max(frame: pd.DataFrame, candidate_id: str, column: str) -> float:
    if frame.empty or column not in frame.columns or "candidate_id" not in frame.columns:
        return float("inf")
    selected = frame.loc[frame["candidate_id"].astype(str).eq(candidate_id)]
    if selected.empty:
        return float("inf")
    values = pd.to_numeric(selected[column], errors="coerce")
    if values.dropna().empty:
        return float("inf")
    return float(values.max())


def _plotkit_render_count(repo_root: Path) -> int:
    manifest = repo_root / "out" / "tomics" / "figures" / "haf_2025_2c" / "plotkit_render_manifest.csv"
    if not manifest.exists():
        return 0
    frame = pd.read_csv(manifest)
    if frame.empty or "render_status" not in frame.columns:
        return 0
    return int(frame["render_status"].astype(str).eq("rendered").sum())


def _relative(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)


def build_haf_promotion_gate_payload(
    *,
    config: Mapping[str, Any],
    repo_root: Path,
    config_path: Path,
) -> dict[str, Any]:
    haf_cfg = as_dict(config.get("tomics_haf"))
    gate_cfg = as_dict(config.get("gate"))
    output_root = resolve_artifact_path(
        str(haf_cfg.get("output_root", "out/tomics/validation/promotion-gate/haf_2025_2c")),
        repo_root=repo_root,
        config_path=config_path,
        prefer_repo_root=True,
    )
    harvest_root = resolve_artifact_path(
        str(haf_cfg.get("harvest_family_output_root", "out/tomics/validation/harvest-family/haf_2025_2c")),
        repo_root=repo_root,
        config_path=config_path,
    )
    observer_metadata = read_json(
        resolve_artifact_path(str(haf_cfg["observer_metadata"]), repo_root=repo_root, config_path=config_path),
        artifact_label="observer_metadata",
    )
    latent_metadata = read_json(
        resolve_artifact_path(
            str(haf_cfg["latent_allocation_metadata"]),
            repo_root=repo_root,
            config_path=config_path,
        ),
        artifact_label="latent_allocation_metadata",
    )
    harvest_metadata = read_json(
        resolve_artifact_path(str(haf_cfg["harvest_family_metadata"]), repo_root=repo_root, config_path=config_path),
        artifact_label="harvest_family_metadata",
    )
    readiness = read_json(
        resolve_artifact_path(str(haf_cfg["goal3c_readiness_audit"]), repo_root=repo_root, config_path=config_path),
        artifact_label="goal3c_readiness_audit",
    )
    rankings = read_required_csv(
        resolve_artifact_path(str(haf_cfg["harvest_family_rankings"]), repo_root=repo_root, config_path=config_path),
        artifact_label="harvest_family_rankings",
    )
    by_loadcell = read_required_csv(
        resolve_artifact_path(
            str(haf_cfg["harvest_family_metrics_by_loadcell"]),
            repo_root=repo_root,
            config_path=config_path,
        ),
        artifact_label="harvest_family_metrics_by_loadcell",
    )
    mean_sd = read_required_csv(
        resolve_artifact_path(
            str(haf_cfg["harvest_family_metrics_mean_sd"]),
            repo_root=repo_root,
            config_path=config_path,
        ),
        artifact_label="harvest_family_metrics_mean_sd",
    )
    budget = read_required_csv(
        resolve_artifact_path(str(haf_cfg["harvest_family_budget_parity"]), repo_root=repo_root, config_path=config_path),
        artifact_label="harvest_family_budget_parity",
    )
    mass_balance = read_required_csv(
        resolve_artifact_path(str(haf_cfg["harvest_family_mass_balance"]), repo_root=repo_root, config_path=config_path),
        artifact_label="harvest_family_mass_balance",
    )
    latent_guardrails = read_required_csv(
        resolve_artifact_path(
            str(haf_cfg["latent_allocation_guardrails"]),
            repo_root=repo_root,
            config_path=config_path,
        ),
        artifact_label="latent_allocation_guardrails",
    )
    dmc_sensitivity_enabled = any(
        bool_value(source.get("DMC_sensitivity_enabled"))
        for source in [observer_metadata, latent_metadata, harvest_metadata]
    )
    canonical_fruit_dmc = harvest_metadata.get(
        "canonical_fruit_DMC_fraction",
        observer_metadata.get("canonical_fruit_DMC_fraction", latent_metadata.get("canonical_fruit_DMC_fraction")),
    )
    dmc_fixed_for_2025_2c = all(
        bool_value(source.get("DMC_fixed_for_2025_2C"))
        for source in [observer_metadata, latent_metadata, harvest_metadata]
    )
    dry_yield_is_dmc_estimated = all(
        bool_value(source.get("dry_yield_is_dmc_estimated"))
        for source in [observer_metadata, latent_metadata, harvest_metadata]
    )
    direct_dry_yield_measured = any(
        bool_value(source.get("direct_dry_yield_measured"))
        for source in [observer_metadata, latent_metadata, harvest_metadata]
    )
    latent_allocation_directly_validated = bool_value(
        latent_metadata.get("latent_allocation_directly_validated")
    ) or bool_value(harvest_metadata.get("latent_allocation_directly_validated"))
    raw_thorp_allocator_used = bool_value(latent_metadata.get("raw_THORP_allocator_used")) or bool_value(
        harvest_metadata.get("raw_THORP_allocator_used")
    )
    fruit_diameter_p_values_allowed = bool_value(observer_metadata.get("fruit_diameter_p_values_allowed"))
    fruit_diameter_allocation_calibration_target = bool_value(
        observer_metadata.get("fruit_diameter_allocation_calibration_target")
    )
    fruit_diameter_model_promotion_target = bool_value(
        observer_metadata.get("fruit_diameter_model_promotion_target")
    )
    shipped_tomics_incumbent_changed = bool_value(
        harvest_metadata.get("shipped_TOMICS_incumbent_changed")
    )
    radiation_daynight_primary_source = str(
        harvest_metadata.get(
            "radiation_daynight_primary_source",
            observer_metadata.get("radiation_daynight_primary_source", ""),
        )
    )
    radiation_column_used = str(
        harvest_metadata.get("radiation_column_used", observer_metadata.get("radiation_column_used", ""))
    )
    fixed_clock_daynight_primary = bool_value(
        harvest_metadata.get(
            "fixed_clock_daynight_primary",
            observer_metadata.get("fixed_clock_daynight_primary"),
        )
    )
    thorp_used_as_bounded_prior = any(
        bool_value(source.get("THORP_used_as_bounded_prior"))
        for source in [observer_metadata, latent_metadata, harvest_metadata]
    )
    harvest_family_factorial_run = bool_value(harvest_metadata.get("harvest_family_factorial_run"))
    selected_id = _selected_candidate_id(harvest_root, rankings)
    selected_row = _candidate_row(rankings, selected_id)
    best_research = _best_research_candidate(rankings)
    incumbent_rows = rankings.loc[
        rankings["allocator_family"].astype(str).eq("shipped_tomics")
        & rankings["stage"].astype(str).eq("HF0")
    ]
    if incumbent_rows.empty:
        incumbent_rows = rankings.loc[rankings["allocator_family"].astype(str).eq("shipped_tomics")]
    incumbent = incumbent_rows.iloc[0] if not incumbent_rows.empty else rankings.iloc[0]
    selected_exists = selected_row is not None
    selected_row = selected_row if selected_row is not None else best_research
    selected_rmse = float_value(selected_row.get("rmse_cumulative_DW_g_m2_floor"), default=float("inf"))
    incumbent_rmse = float_value(incumbent.get("rmse_cumulative_DW_g_m2_floor"), default=float("inf"))
    relative_improvement = (incumbent_rmse - selected_rmse) / incumbent_rmse if incumbent_rmse > 0 else 0.0
    max_final_bias_abs = max(
        abs(float_value(selected_row.get("final_cumulative_bias_pct"), default=float("inf"))),
        _candidate_max_abs(by_loadcell, selected_id, "final_cumulative_bias_pct"),
        _candidate_max_abs(mean_sd, selected_id, "mean_final_cumulative_bias_pct"),
    )
    cross_payload = build_haf_cross_dataset_gate_payload(
        config={
            "cross_dataset_gate": {
                "current_dataset_id": haf_cfg.get("current_dataset_id", "haf_2025_2c"),
                "require_measured_dataset_count_min": gate_cfg.get("require_measured_dataset_count_min", 2),
                "available_dataset_outputs": [
                    {
                        "dataset_id": gate_cfg.get("current_dataset_id", "haf_2025_2c"),
                        "dataset_type": "haf_measured_actual",
                        "measured_or_proxy": "measured",
                        "harvest_family_metadata": haf_cfg.get("harvest_family_metadata"),
                        "harvest_family_rankings": haf_cfg.get("harvest_family_rankings"),
                        "contributes_to_promotion_gate": True,
                    }
                ],
                "single_dataset_promotion_allowed": gate_cfg.get("allow_single_dataset_promotion", False),
                "allow_legacy_or_public_proxy_for_promotion": False,
                "proxy_dataset_use": "diagnostic_only",
            }
        },
        repo_root=repo_root,
        config_path=config_path,
    )
    cross_metadata = as_dict(cross_payload["metadata"])
    selected_budget = _candidate_row(budget, selected_id)
    budget_pass = selected_budget is not None and not bool_value(selected_budget.get("budget_parity_violation"))
    selected_mass_balance_invalid = _candidate_max_bool(mass_balance, selected_id, "invalid_run_flag")
    mass_balance_pass = (
        not selected_mass_balance_invalid
        and _candidate_max(mass_balance, selected_id, "mass_balance_error") <= 1e-9
        and _candidate_max(mass_balance, selected_id, "leaf_harvest_mass_balance_error") <= 1e-9
    )
    effect_cfg = as_dict(gate_cfg.get("promotion_effect_size_requirements"))
    min_relative_improvement = float_value(effect_cfg.get("min_relative_improvement_vs_incumbent"), default=0.05)
    max_bias_abs_allowed = float_value(effect_cfg.get("max_final_bias_pct_abs"), default=20.0)
    checks = [
        check_row("goal3c_ready", bool_value(readiness.get("goal3c_ready")), evidence_value=readiness.get("blockers", [])),
        check_row(
            "dmc_0p056_contract",
            dmc_fixed_for_2025_2c
            and harvest_metadata.get("canonical_fruit_DMC_fraction") == 0.056
            and observer_metadata.get("canonical_fruit_DMC_fraction") == 0.056
            and latent_metadata.get("canonical_fruit_DMC_fraction") == 0.056,
            evidence_value={
                "observer": observer_metadata.get("canonical_fruit_DMC_fraction"),
                "latent": latent_metadata.get("canonical_fruit_DMC_fraction"),
                "harvest": harvest_metadata.get("canonical_fruit_DMC_fraction"),
                "DMC_fixed_for_2025_2C": dmc_fixed_for_2025_2c,
            },
        ),
        check_row(
            "dmc_sensitivity_disabled",
            not dmc_sensitivity_enabled,
            evidence_value=dmc_sensitivity_enabled,
        ),
        check_row(
            "dry_yield_estimated_not_direct",
            dry_yield_is_dmc_estimated and not direct_dry_yield_measured,
            evidence_value={
                "dry_yield_is_dmc_estimated": dry_yield_is_dmc_estimated,
                "direct_dry_yield_measured": direct_dry_yield_measured,
            },
        ),
        check_row(
            "radiation_daynight_contract",
            radiation_daynight_primary_source == "dataset1"
            and radiation_column_used == "env_inside_radiation_wm2"
            and not fixed_clock_daynight_primary,
            evidence_value={
                "radiation_daynight_primary_source": radiation_daynight_primary_source,
                "radiation_column_used": radiation_column_used,
                "fixed_clock_daynight_primary": fixed_clock_daynight_primary,
            },
        ),
        check_row(
            "latent_allocation_not_direct_validation",
            not latent_allocation_directly_validated,
            evidence_value=latent_allocation_directly_validated,
        ),
        check_row(
            "raw_thorp_absent",
            not raw_thorp_allocator_used,
            blocker_code="raw_THORP_allocator_used",
            evidence_value=raw_thorp_allocator_used,
        ),
        check_row(
            "latent_guardrails_pass",
            _all_latent_guardrails_pass(latent_guardrails),
            evidence_value=latent_guardrails.to_dict(orient="records"),
        ),
        check_row(
            "fruit_diameter_diagnostic_only",
            not fruit_diameter_p_values_allowed
            and not fruit_diameter_allocation_calibration_target
            and not fruit_diameter_model_promotion_target,
            blocker_code="fruit_diameter_model_promotion_target",
            evidence_value={
                "fruit_diameter_p_values_allowed": fruit_diameter_p_values_allowed,
                "fruit_diameter_allocation_calibration_target": fruit_diameter_allocation_calibration_target,
                "fruit_diameter_model_promotion_target": fruit_diameter_model_promotion_target,
            },
        ),
        check_row(
            "harvest_family_factorial_run",
            harvest_family_factorial_run and int_value(harvest_metadata.get("candidate_count")) > 0,
            evidence_value=harvest_metadata.get("candidate_count"),
        ),
        check_row("selected_candidate_exists", selected_exists, evidence_value=selected_id),
        check_row("budget_parity_pass", budget_pass, evidence_value=selected_budget.to_dict() if selected_budget is not None else {}),
        check_row("mass_balance_pass", mass_balance_pass, evidence_value={"candidate_id": selected_id}),
        check_row(
            "invalid_run_flag_zero_for_selected",
            int_value(selected_row.get("invalid_run_flag")) == 0 and not _candidate_max_bool(by_loadcell, selected_id, "invalid_run_flag"),
            evidence_value=selected_row.get("invalid_run_flag"),
        ),
        check_row(
            "nonfinite_flag_zero_for_selected",
            int_value(selected_row.get("nonfinite_flag")) == 0 and not _candidate_max_bool(by_loadcell, selected_id, "nonfinite_flag"),
            evidence_value=selected_row.get("nonfinite_flag"),
        ),
        check_row(
            "candidate_effect_size_thresholds",
            relative_improvement >= min_relative_improvement and max_final_bias_abs <= max_bias_abs_allowed,
            evidence_value={
                "relative_improvement_vs_incumbent": relative_improvement,
                "max_final_bias_pct_abs": max_final_bias_abs,
            },
        ),
        check_row(
            "no_treatment_group_failure",
            not mean_sd.loc[mean_sd["candidate_id"].astype(str).eq(selected_id)].empty
            and _candidate_max_abs(mean_sd, selected_id, "mean_final_cumulative_bias_pct") <= max_bias_abs_allowed,
            evidence_value={"candidate_id": selected_id},
        ),
        check_row(
            "cross_dataset_evidence_sufficient",
            bool_value(cross_metadata.get("cross_dataset_gate_passed")),
            blocker_code=CROSS_DATASET_BLOCKER,
            evidence_value={
                "measured_dataset_count": cross_metadata.get("measured_dataset_count"),
                "required_measured_dataset_count": cross_metadata.get("required_measured_dataset_count"),
            },
        ),
        check_row(
            "single_dataset_promotion_blocked",
            not bool_value(gate_cfg.get("allow_single_dataset_promotion")),
            evidence_value=gate_cfg.get("allow_single_dataset_promotion"),
        ),
        check_row(
            "shipped_tomics_incumbent_unchanged",
            not shipped_tomics_incumbent_changed,
            blocker_code="shipped_TOMICS_incumbent_changed",
            evidence_value=shipped_tomics_incumbent_changed,
        ),
    ]
    blockers = [
        str(row["blocker_code"])
        for row in checks
        if bool_value(row["hard_blocker"]) and row["status"] != "pass" and str(row["blocker_code"])
    ]
    blockers = sorted(set(blockers), key=blockers.index)
    promotion_passed = not blockers
    non_cross_blockers = [blocker for blocker in blockers if blocker != CROSS_DATASET_BLOCKER]
    selected_for_future_gate = bool(blockers == [CROSS_DATASET_BLOCKER])
    if promotion_passed:
        status = "passed"
    elif not non_cross_blockers and CROSS_DATASET_BLOCKER in blockers:
        status = "blocked_cross_dataset_evidence_insufficient"
    else:
        status = "blocked_guardrail_failure"
    promoted_candidate_id = selected_id if promotion_passed else None
    future_candidate_id = selected_id if selected_for_future_gate else None
    metadata = {
        "season_id": "2025_2C",
        "gate_pipeline_version": GATE_PIPELINE_VERSION,
        "current_branch": _git_value(repo_root, "branch", "--show-current"),
        "current_head_sha": _git_value(repo_root, "rev-parse", "HEAD"),
        "base_prs": BASE_PRS,
        "canonical_fruit_DMC_fraction": canonical_fruit_dmc,
        "DMC_fixed_for_2025_2C": dmc_fixed_for_2025_2c,
        "DMC_sensitivity_enabled": dmc_sensitivity_enabled,
        "dry_yield_is_dmc_estimated": dry_yield_is_dmc_estimated,
        "direct_dry_yield_measured": direct_dry_yield_measured,
        "radiation_daynight_primary_source": radiation_daynight_primary_source,
        "radiation_column_used": radiation_column_used,
        "fixed_clock_daynight_primary": fixed_clock_daynight_primary,
        "latent_allocation_directly_validated": latent_allocation_directly_validated,
        "raw_THORP_allocator_used": raw_thorp_allocator_used,
        "THORP_used_as_bounded_prior": thorp_used_as_bounded_prior,
        "fruit_diameter_p_values_allowed": fruit_diameter_p_values_allowed,
        "fruit_diameter_allocation_calibration_target": fruit_diameter_allocation_calibration_target,
        "fruit_diameter_model_promotion_target": fruit_diameter_model_promotion_target,
        "harvest_family_factorial_run": harvest_family_factorial_run,
        "promotion_gate_run": True,
        "cross_dataset_gate_run": True,
        "promotion_gate_passed": promotion_passed,
        "promotion_gate_status": status,
        "promotion_block_reasons": blockers,
        "measured_dataset_count": cross_metadata.get("measured_dataset_count"),
        "required_measured_dataset_count": cross_metadata.get("required_measured_dataset_count"),
        "single_dataset_promotion_allowed": False,
        "cross_dataset_gate_required": True,
        "cross_dataset_gate_passed": cross_metadata.get("cross_dataset_gate_passed"),
        "cross_dataset_gate_status": cross_metadata.get("cross_dataset_gate_status"),
        "best_research_candidate_id": str(best_research["candidate_id"]),
        "selected_candidate_for_future_cross_dataset_gate": future_candidate_id,
        "promoted_candidate_id": promoted_candidate_id,
        "shipped_TOMICS_incumbent_changed": shipped_tomics_incumbent_changed,
        "shipped_TOMICS_change_proposed": False,
        "relative_improvement_vs_incumbent": relative_improvement,
        "max_final_bias_pct_abs": max_final_bias_abs,
        "config_path": _relative(config_path, repo_root),
        "output_root": _relative(output_root, repo_root),
    }
    summary = {
        "promotion_gate_run": True,
        "promotion_gate_passed": promotion_passed,
        "promotion_gate_status": status,
        "promotion_block_reasons": blockers,
        "best_research_candidate_id": str(best_research["candidate_id"]),
        "selected_candidate_for_future_cross_dataset_gate": future_candidate_id,
        "promoted_candidate_id": promoted_candidate_id,
        "shipped_TOMICS_incumbent_changed": shipped_tomics_incumbent_changed,
    }
    candidate_for_future_gate = {
        "candidate_id": future_candidate_id,
        "selection_status": "selected_for_future_cross_dataset_gate"
        if selected_for_future_gate
        else "blocked_by_guardrails",
        "promoted_candidate_id": promoted_candidate_id,
        "promotion_gate_passed": promotion_passed,
        "promotion_block_reasons": blockers,
        "candidate_metrics": selected_row.to_dict(),
    }
    cross_output_root = resolve_artifact_path(
        str(gate_cfg.get("cross_dataset_output_root", "out/tomics/validation/multi-dataset/haf_2025_2c")),
        repo_root=repo_root,
        config_path=config_path,
        prefer_repo_root=True,
    )
    return {
        "output_root": output_root,
        "cross_dataset_output_root": cross_output_root,
        "scorecard": pd.DataFrame(checks),
        "metadata": metadata,
        "summary": summary,
        "blockers": pd.DataFrame([{"blocker_code": blocker, "blocking": True} for blocker in blockers]),
        "candidate_for_future_gate": candidate_for_future_gate,
        "cross_dataset_scorecard": cross_payload["scorecard"],
        "cross_dataset_metadata": cross_metadata,
    }


def write_haf_promotion_gate_outputs(
    *,
    payload: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, str]:
    output_root = ensure_dir(Path(payload["output_root"]))
    scorecard = payload["scorecard"]
    if not isinstance(scorecard, pd.DataFrame):
        scorecard = pd.DataFrame(scorecard)
    blockers = payload["blockers"]
    if not isinstance(blockers, pd.DataFrame):
        blockers = pd.DataFrame(blockers)
    metadata = as_dict(payload["metadata"])
    summary = as_dict(payload["summary"])
    scorecard_path = output_root / "promotion_gate_scorecard.csv"
    summary_csv_path = output_root / "promotion_gate_summary.csv"
    summary_md_path = output_root / "promotion_gate_summary.md"
    metadata_path = output_root / "promotion_gate_metadata.json"
    blockers_path = output_root / "promotion_gate_blockers.csv"
    future_candidate_path = output_root / "promotion_candidate_for_future_gate.json"
    scorecard.to_csv(scorecard_path, index=False)
    write_key_value_csv(summary_csv_path, summary)
    write_json(metadata_path, metadata)
    blockers.to_csv(blockers_path, index=False)
    write_json(future_candidate_path, as_dict(payload["candidate_for_future_gate"]))
    write_markdown_table(
        summary_md_path,
        pd.DataFrame([summary]),
        title="HAF 2025-2C Promotion Gate",
        intro_lines=[
            "Promotion gate was executed; pass/fail is determined by the gate outputs.",
            "If measured dataset count remains one, promotion is blocked by cross-dataset evidence insufficiency.",
            "Shipped TOMICS incumbent remains unchanged.",
        ],
    )
    claim_paths = write_claim_register(output_root=output_root, promotion_metadata=metadata)
    plotkit_manifest = repo_root / "out" / "tomics" / "figures" / "haf_2025_2c" / "plotkit_render_manifest.csv"
    repro_manifest = (
        repo_root
        / "out"
        / "tomics"
        / "validation"
        / "harvest-family"
        / "haf_2025_2c"
        / "harvest_family_reproducibility_manifest.json"
    )
    readiness_paths = write_new_phytologist_readiness_matrix(
        output_root=output_root,
        promotion_metadata=metadata,
        cross_dataset_metadata=as_dict(payload.get("cross_dataset_metadata")),
        plotkit_manifest_exists=plotkit_manifest.exists(),
        rendered_plot_count=_plotkit_render_count(repo_root),
        claim_register_exists=Path(claim_paths["claim_register_csv"]).exists(),
        reproducibility_manifest_exists=repro_manifest.exists(),
    )
    cross_paths = write_haf_cross_dataset_gate_outputs(
        output_root=Path(payload["cross_dataset_output_root"]),
        payload={
            "scorecard": payload.get("cross_dataset_scorecard", pd.DataFrame()),
            "metadata": as_dict(payload.get("cross_dataset_metadata")),
        },
    )
    return {
        "promotion_gate_scorecard": str(scorecard_path),
        "promotion_gate_summary_csv": str(summary_csv_path),
        "promotion_gate_summary_md": str(summary_md_path),
        "promotion_gate_metadata": str(metadata_path),
        "promotion_gate_blockers": str(blockers_path),
        "promotion_candidate_for_future_gate": str(future_candidate_path),
        **claim_paths,
        **readiness_paths,
        **cross_paths,
    }


def run_haf_promotion_gate(
    config: Mapping[str, Any],
    *,
    repo_root: Path,
    config_path: Path,
) -> dict[str, Any]:
    payload = build_haf_promotion_gate_payload(config=config, repo_root=repo_root, config_path=config_path)
    paths = write_haf_promotion_gate_outputs(payload=payload, repo_root=repo_root)
    return {
        **paths,
        "output_root": str(payload["output_root"]),
        "metadata": payload["metadata"],
    }


__all__ = [
    "GATE_PIPELINE_VERSION",
    "build_haf_promotion_gate_payload",
    "run_haf_promotion_gate",
    "write_haf_promotion_gate_outputs",
]
