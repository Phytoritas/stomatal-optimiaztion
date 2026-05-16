from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping, Sequence

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, write_json
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_gate_outputs import (
    bool_value,
    write_markdown_table,
)


GOAL4A_PIPELINE_VERSION = "haf_goal4a_merge_readiness_v1"
GOAL4A_OUTPUT_ROOT = "out/tomics/validation/promotion-gate/haf_2025_2c"
MERGE_ORDER = [309, 311, 313, 315]
EXPECTED_BASES = {
    309: "main",
    311: "fix/308-diagnose-tomics-daily-harvest-increments",
    313: "feat/tomics-haf-2025-2c-latent-allocation",
    315: "feat/tomics-haf-2025-2c-harvest-family-eval",
}
EXPECTED_DEPENDS_ON = {309: "", 311: "#309", 313: "#311", 315: "#313"}

ALLOWED_PRIMARY_CLAIMS = [
    "TOMICS-HAF was evaluated on the 2025 second cropping cycle as a bounded architecture-discrimination test.",
    "Day/night phases were radiation-defined from Dataset1 env_inside_radiation_wm2.",
    "For 2025-2C, DMC was fixed at 0.056.",
    "Dry yield derived from fresh yield using DMC 0.056 was an estimated dry-yield basis, not direct destructive dry-mass measurement.",
    "Latent allocation was observer-supported inference, not direct allocation validation.",
    "THORP was used only as a bounded mechanistic prior/correction, not as a raw tomato allocator.",
    "Harvest-family evaluation separated allocator family, harvest family, and observation operator.",
    "Promotion and cross-dataset gates were executed as safeguards.",
    "The gate selected candidates for future cross-dataset testing but did not promote a new shipped TOMICS default.",
]

FORBIDDEN_CLAIMS = [
    "Promotion gate passed.",
    "Cross-dataset validation passed.",
    "Allocation was directly validated.",
    "Dry yield was directly measured.",
    "DMC sensitivity was evaluated.",
    "Raw THORP allocator was promoted.",
    "Drought significantly reduced fruit expansion.",
    "TOMICS-HAF is universally superior across seasons.",
    "This proves universal multi-season generalization.",
    "A shipped TOMICS default was changed.",
]

SAFE_FORBIDDEN_REWRITES = {
    "Promotion gate passed.": (
        "Promotion gate was executed and blocked promotion because compatible cross-dataset evidence is insufficient."
    ),
    "Cross-dataset validation passed.": (
        "Cross-dataset gate was executed and blocked because compatible measured datasets are insufficient."
    ),
    "Allocation was directly validated.": (
        "Latent allocation remains observer-supported inference, not direct allocation validation."
    ),
    "Dry yield was directly measured.": (
        "Dry yield derived from fresh yield using DMC 0.056 is an estimated dry-yield basis."
    ),
    "DMC sensitivity was evaluated.": "For 2025-2C, DMC is fixed at 0.056.",
    "Raw THORP allocator was promoted.": (
        "THORP was used only as a bounded mechanistic prior/correction, not as a raw tomato allocator."
    ),
    "Drought significantly reduced fruit expansion.": (
        "Fruit diameter remains sensor-level apparent expansion diagnostics."
    ),
    "TOMICS-HAF is universally superior across seasons.": (
        "TOMICS-HAF 2025-2C is a bounded architecture-discrimination test."
    ),
    "This proves universal multi-season generalization.": (
        "TOMICS-HAF 2025-2C is not universal multi-season generalization."
    ),
    "A shipped TOMICS default was changed.": "No shipped TOMICS default change is recommended at this stage.",
}


def _relative(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _path_from_root(repo_root: Path, raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else repo_root / path


def _sha256_status(path: Path, *, max_bytes: int = 25_000_000) -> str:
    if not path.exists():
        return "missing"
    if path.is_dir():
        return "directory_no_hash"
    if path.stat().st_size > max_bytes:
        return "exists_unhashed_large_file"
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _evidence_item(
    *,
    repo_root: Path,
    evidence_id: str,
    stage: str,
    path: str,
    required_for_claim: str,
    safe_claim_supported: str,
    limitation: str,
    committed_or_private: str | None = None,
) -> dict[str, object]:
    resolved = _path_from_root(repo_root, path)
    if committed_or_private is None:
        committed_or_private = "committed" if path.startswith(("docs/", "configs/")) else "private_uncommitted"
    return {
        "evidence_id": evidence_id,
        "stage": stage,
        "path": path,
        "committed_or_private": committed_or_private,
        "required_for_claim": required_for_claim,
        "exists": resolved.exists(),
        "hash_status": _sha256_status(resolved),
        "safe_claim_supported": safe_claim_supported,
        "limitation": limitation,
    }


def build_evidence_package_manifest(
    *,
    repo_root: Path,
    promotion_root: Path | str,
    harvest_root: Path | str,
    latent_root: Path | str,
    observer_root: Path | str,
    figures_root: Path | str | None = None,
) -> pd.DataFrame:
    repo_root = repo_root.resolve()
    promotion_root = Path(promotion_root)
    harvest_root = Path(harvest_root)
    latent_root = Path(latent_root)
    observer_root = Path(observer_root)
    figures_root = Path(figures_root or "out/tomics/figures/haf_2025_2c")

    rows = [
        _evidence_item(
            repo_root=repo_root,
            evidence_id="observer_metadata",
            stage="observer",
            path=_relative(_path_from_root(repo_root, observer_root / "2025_2c_tomics_haf_metadata.json"), repo_root),
            required_for_claim="actual_data_pipeline",
            safe_claim_supported="Production observer metadata exists for bounded 2025-2C evaluation.",
            limitation="Private generated output; not committed.",
        ),
        _evidence_item(
            repo_root=repo_root,
            evidence_id="radiation_daynight_summaries",
            stage="observer",
            path=_relative(
                _path_from_root(repo_root, observer_root / "radiation_daynight_event_bridged_daily_main_0W.csv"),
                repo_root,
            ),
            required_for_claim="radiation_daynight_et",
            safe_claim_supported="Day/night phases were radiation-defined from Dataset1 env_inside_radiation_wm2.",
            limitation="Dataset-specific observer evidence only.",
        ),
        _evidence_item(
            repo_root=repo_root,
            evidence_id="event_bridged_et_outputs",
            stage="observer",
            path=_relative(
                _path_from_root(repo_root, observer_root / "radiation_daynight_event_bridged_daily_all_thresholds.csv"),
                repo_root,
            ),
            required_for_claim="event_bridged_water_flux",
            safe_claim_supported="Event-bridged ET outputs support observer water-flux summaries.",
            limitation="Observer-derived flux, not an allocation validation.",
        ),
        _evidence_item(
            repo_root=repo_root,
            evidence_id="rootzone_rzi_outputs",
            stage="observer",
            path=_relative(_path_from_root(repo_root, observer_root / "2025_2c_rootzone_indices.csv"), repo_root),
            required_for_claim="rootzone_rzi",
            safe_claim_supported="Root-zone stress index outputs exist for 2025-2C.",
            limitation="RZI is an observer feature, not a promoted allocator.",
        ),
        _evidence_item(
            repo_root=repo_root,
            evidence_id="fruit_leaf_observer_outputs",
            stage="observer",
            path=_relative(_path_from_root(repo_root, observer_root / "2025_2c_fruit_leaf_radiation_windows.csv"), repo_root),
            required_for_claim="fruit_leaf_observer",
            safe_claim_supported="Fruit and leaf observer windows exist.",
            limitation="Fruit diameter remains sensor-level diagnostics only.",
        ),
        _evidence_item(
            repo_root=repo_root,
            evidence_id="dataset3_bridge_outputs",
            stage="observer",
            path=_relative(_path_from_root(repo_root, observer_root / "2025_2c_dataset3_growth_phenology_bridge.csv"), repo_root),
            required_for_claim="dataset3_bridge",
            safe_claim_supported="Dataset3 bridge outputs are indexed as observer bridge evidence.",
            limitation="Bridge evidence is not cross-dataset promotion evidence.",
        ),
        _evidence_item(
            repo_root=repo_root,
            evidence_id="observer_feature_frame",
            stage="observer",
            path=_relative(_path_from_root(repo_root, observer_root / "2025_2c_tomics_haf_observer_feature_frame.csv"), repo_root),
            required_for_claim="actual_data_pipeline",
            safe_claim_supported="Observer feature frame exists for downstream latent allocation and harvest-family runs.",
            limitation="Private generated output; not committed.",
        ),
    ]
    for evidence_id, filename, claim, limitation in [
        ("latent_input_state", "latent_allocation_inference_inputs.csv", "latent_allocation_inference", "Input state is observer-derived."),
        ("latent_priors", "latent_allocation_priors.csv", "latent_allocation_inference", "Priors are bounded inference inputs."),
        ("latent_posteriors", "latent_allocation_posteriors.csv", "latent_allocation_inference", "Posteriors are inferred, not direct organ allocation measurements."),
        ("latent_diagnostics", "latent_allocation_diagnostics.csv", "latent_allocation_inference", "Diagnostics do not authorize promotion."),
        ("latent_identifiability", "latent_allocation_identifiability.csv", "latent_allocation_inference", "Identifiability is bounded to 2025-2C observer features."),
        ("latent_guardrails", "latent_allocation_guardrails.csv", "paper_claim_safety", "Guardrails support claim boundaries only."),
        ("latent_metadata", "latent_allocation_metadata.json", "latent_allocation_inference", "Metadata must retain direct-validation false."),
    ]:
        rows.append(
            _evidence_item(
                repo_root=repo_root,
                evidence_id=evidence_id,
                stage="latent_allocation",
                path=_relative(_path_from_root(repo_root, latent_root / filename), repo_root),
                required_for_claim=claim,
                safe_claim_supported="Latent allocation was observer-supported inference, not direct allocation validation.",
                limitation=limitation,
            )
        )
    for evidence_id, filename, claim, safe_claim, limitation in [
        ("harvest_design_doc", "docs/architecture/tomics/harvest_family_factorial_design_2025_2c.md", "harvest_family_factorial", "Harvest-family design is documented.", "Committed architecture document."),
        ("harvest_run_manifest", harvest_root / "harvest_family_run_manifest.csv", "harvest_family_factorial", "Harvest-family run manifest exists.", "Private generated output; not committed."),
        ("harvest_metrics_pooled", harvest_root / "harvest_family_metrics_pooled.csv", "harvest_family_factorial", "Pooled harvest-family metrics exist.", "Single compatible measured dataset only."),
        ("harvest_metrics_by_loadcell", harvest_root / "harvest_family_metrics_by_loadcell.csv", "harvest_family_factorial", "By-loadcell metrics exist.", "Does not establish multi-season generalization."),
        ("harvest_metrics_mean_sd", harvest_root / "harvest_family_metrics_mean_sd.csv", "harvest_family_factorial", "Mean/SD metrics exist.", "DMC-estimated dry yield basis."),
        ("harvest_mass_balance", harvest_root / "harvest_family_mass_balance.csv", "budget_parity", "Mass-balance evidence exists for candidate screening.", "Screening evidence only."),
        ("harvest_budget_parity", harvest_root / "harvest_family_budget_parity.csv", "budget_parity", "Budget parity evidence exists.", "Knob-count and hidden-calibration parity, not wall-clock compute parity."),
        ("harvest_rankings", harvest_root / "harvest_family_rankings.csv", "harvest_family_factorial", "Research candidate rankings exist.", "Candidate selection is for future testing only."),
        ("harvest_selected_research_candidate", harvest_root / "harvest_family_selected_research_candidate.json", "harvest_family_factorial", "Selected research candidate is recorded.", "Selected is not promoted."),
        ("harvest_reproducibility_manifest", harvest_root / "harvest_family_reproducibility_manifest.json", "reproducibility_manifest", "Reproducibility manifest exists.", "Private generated output; not committed."),
    ]:
        path = filename if isinstance(filename, str) else _relative(_path_from_root(repo_root, filename), repo_root)
        rows.append(
            _evidence_item(
                repo_root=repo_root,
                evidence_id=evidence_id,
                stage="harvest_family",
                path=str(path),
                required_for_claim=claim,
                safe_claim_supported=safe_claim,
                limitation=limitation,
            )
        )
    for evidence_id, filename, claim, safe_claim, limitation in [
        ("promotion_scorecard", promotion_root / "promotion_gate_scorecard.csv", "promotion_gate", "Promotion gate was executed.", "Gate execution blocked promotion."),
        ("promotion_metadata", promotion_root / "promotion_gate_metadata.json", "promotion_gate", "Promotion metadata records blocked status and no promoted candidate.", "Private generated output; not committed."),
        ("promotion_blockers", promotion_root / "promotion_gate_blockers.csv", "promotion_gate", "Blocker list records cross-dataset evidence insufficiency.", "Blocked promotion is the safeguard result."),
        ("promotion_future_candidate", promotion_root / "promotion_candidate_for_future_gate.json", "promotion_gate", "Future candidate record exists.", "Future candidate is not a shipped default."),
        ("cross_dataset_scorecard", "out/tomics/validation/multi-dataset/haf_2025_2c/cross_dataset_scorecard.csv", "cross_dataset_gate", "Cross-dataset gate was executed.", "Measured dataset count remains insufficient."),
        ("cross_dataset_metadata", "out/tomics/validation/multi-dataset/haf_2025_2c/cross_dataset_metadata.json", "cross_dataset_gate", "Cross-dataset metadata records insufficient measured datasets.", "Does not pass cross-dataset validation."),
        ("claim_register", promotion_root / "claim_register.md", "paper_claim_safety", "Paper-safe claim register exists.", "Unsafe claims remain blocked."),
        ("new_phytologist_readiness_matrix", promotion_root / "new_phytologist_readiness_matrix.md", "new_phytologist_readiness", "Readiness matrix exists.", "Readiness is not final-pass while gates are blocked and figures are manifest-only."),
    ]:
        path = filename if isinstance(filename, str) else _relative(_path_from_root(repo_root, filename), repo_root)
        rows.append(
            _evidence_item(
                repo_root=repo_root,
                evidence_id=evidence_id,
                stage="promotion_cross_dataset",
                path=str(path),
                required_for_claim=claim,
                safe_claim_supported=safe_claim,
                limitation=limitation,
            )
        )
    rows.extend(
        [
            _evidence_item(
                repo_root=repo_root,
                evidence_id="plotkit_manifest_csv",
                stage="figures",
                path=_relative(_path_from_root(repo_root, figures_root / "plotkit_render_manifest.csv"), repo_root),
                required_for_claim="plotkit_figures",
                safe_claim_supported="Plotkit figure bundle is manifest-backed.",
                limitation="Rendered PNG evidence is pending; no fake PNGs.",
            ),
            _evidence_item(
                repo_root=repo_root,
                evidence_id="plotkit_manifest_md",
                stage="figures",
                path=_relative(_path_from_root(repo_root, figures_root / "plotkit_render_manifest.md"), repo_root),
                required_for_claim="plotkit_figures",
                safe_claim_supported="Plotkit render status is documented.",
                limitation="Manifest-only evidence is partial, not final rendered figure evidence.",
            ),
        ]
    )
    png_count = len(list(_path_from_root(repo_root, figures_root).glob("*.png")))
    rows.append(
        {
            "evidence_id": "rendered_png_status",
            "stage": "figures",
            "path": _relative(_path_from_root(repo_root, figures_root), repo_root) + "/*.png",
            "committed_or_private": "private_uncommitted",
            "required_for_claim": "plotkit_figures",
            "exists": png_count > 0,
            "hash_status": f"rendered_png_count:{png_count}" if png_count else "manifest_only_no_png_hash",
            "safe_claim_supported": "Rendered PNG status is explicitly recorded.",
            "limitation": "Do not claim completed rendered figure bundle when count is zero.",
        }
    )
    return pd.DataFrame(rows)


def build_claim_boundary_freeze_rows(
    *,
    promotion_gate_passed: bool,
    cross_dataset_gate_passed: bool,
    shipped_default_changed: bool,
    evidence_path: str = "out/tomics/validation/promotion-gate/haf_2025_2c/promotion_gate_metadata.json",
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for claim in ALLOWED_PRIMARY_CLAIMS:
        rows.append(
            {
                "claim_text": claim,
                "status": "allowed",
                "condition": "Allowed only with stated 2025-2C limitations and Goal 4A frozen decision.",
                "evidence_path": evidence_path,
                "safe_rewrite": claim,
            }
        )
    for claim in FORBIDDEN_CLAIMS:
        status = "forbidden"
        condition = "Forbidden under Goal 4A frozen decision."
        if claim == "Promotion gate passed." and promotion_gate_passed:
            status = "conditional"
            condition = "Allowed only if promotion_gate_passed is true and promoted_candidate_id is non-null."
        if claim == "Cross-dataset validation passed." and cross_dataset_gate_passed:
            status = "conditional"
            condition = "Allowed only if cross_dataset_gate_passed is true."
        if claim == "A shipped TOMICS default was changed." and shipped_default_changed:
            status = "conditional"
            condition = "Allowed only in a separate approved shipped default change PR."
        rows.append(
            {
                "claim_text": claim,
                "status": status,
                "condition": condition,
                "evidence_path": evidence_path,
                "safe_rewrite": SAFE_FORBIDDEN_REWRITES[claim],
            }
        )
    return pd.DataFrame(rows)


def build_goal4a_decision_metadata(
    *,
    promotion_gate_executed: bool = True,
    promotion_gate_passed: bool = False,
    cross_dataset_gate_executed: bool = True,
    cross_dataset_gate_passed: bool = False,
    measured_dataset_count: int = 1,
    required_measured_dataset_count: int = 2,
    shipped_tomics_incumbent_changed: bool = False,
) -> dict[str, object]:
    return {
        "goal": "4A",
        "pipeline_version": GOAL4A_PIPELINE_VERSION,
        "shipped_default_change_recommended": False,
        "shipped_default_change_blocked_reason": "cross_dataset_evidence_insufficient",
        "promotion_gate_executed": bool(promotion_gate_executed),
        "promotion_gate_passed": bool(promotion_gate_passed),
        "cross_dataset_gate_executed": bool(cross_dataset_gate_executed),
        "cross_dataset_gate_passed": bool(cross_dataset_gate_passed),
        "measured_dataset_count": int(measured_dataset_count),
        "required_measured_dataset_count": int(required_measured_dataset_count),
        "promotion_remains_blocked": not bool(promotion_gate_passed),
        "shipped_TOMICS_incumbent_changed": bool(shipped_tomics_incumbent_changed),
        "shipped_default_change_blocked": True,
    }


def build_pr_stack_merge_readiness_rows(
    prs: Sequence[Mapping[str, Any]],
    *,
    tracked_out_paths: Sequence[str] | None = None,
    raw_data_committed: bool = False,
) -> pd.DataFrame:
    by_number = {int(pr.get("number")): pr for pr in prs if pr.get("number") is not None}
    tracked_out_paths = list(tracked_out_paths or [])
    rows: list[dict[str, object]] = []
    for index, number in enumerate(MERGE_ORDER, start=1):
        pr = by_number.get(number, {})
        body = str(pr.get("body", ""))
        closing_refs = pr.get("closingIssuesReferences") or []
        closes_issue = _closes_issue_value(body=body, closing_refs=closing_refs)
        base = str(pr.get("baseRefName", ""))
        state = str(pr.get("state", "UNKNOWN"))
        draft = bool_value(pr.get("isDraft"))
        merge_state = str(pr.get("mergeStateStatus", "UNKNOWN"))
        blockers: list[str] = []
        warnings: list[str] = []
        if not pr:
            blockers.append("pr_metadata_missing")
        if state != "OPEN":
            blockers.append("pr_not_open")
        if draft:
            blockers.append("pr_is_draft")
        if EXPECTED_BASES[number] and base != EXPECTED_BASES[number]:
            blockers.append("unexpected_base_branch")
        if number == 315 and not closing_refs and "Closes #314" in body:
            warnings.append("stacked_pr_closing_issue_reference_may_resolve_after_stack_lands")
        if not closes_issue and number == 315:
            warnings.append("closing_issue_reference_missing")
        if merge_state == "UNKNOWN":
            warnings.append("merge_state_unknown")
        elif merge_state not in {"CLEAN", "HAS_HOOKS"}:
            blockers.append(f"merge_state_{merge_state.casefold() or 'missing'}")
        if not _validation_summary_present(body):
            warnings.append("validation_summary_not_visible_in_pr_body")
        unsafe_claims_absent = _unsafe_claims_absent(body)
        if not unsafe_claims_absent:
            blockers.append("unsafe_claims_present")
        if tracked_out_paths:
            blockers.append("out_artifacts_committed")
        if raw_data_committed:
            blockers.append("raw_data_committed")
        rows.append(
            {
                "pr_number": number,
                "title": str(pr.get("title", "")),
                "head_branch": str(pr.get("headRefName", "")),
                "base_branch": base,
                "head_sha": str(pr.get("headRefOid", "")),
                "state": state,
                "merge_state": merge_state,
                "draft": draft,
                "closes_issue": closes_issue,
                "depends_on": EXPECTED_DEPENDS_ON[number],
                "validation_summary_present": _validation_summary_present(body),
                "unsafe_claims_absent": unsafe_claims_absent,
                "out_artifacts_committed": bool(tracked_out_paths),
                "raw_data_committed": bool(raw_data_committed),
                "shipped_TOMICS_incumbent_changed": False,
                "allowed_to_merge_order_index": index,
                "merge_blockers": ";".join(blockers) if blockers else "",
                "process_warnings": ";".join(warnings) if warnings else "",
            }
        )
    return pd.DataFrame(rows)


def _validation_summary_present(body: str) -> bool:
    lowered = body.casefold()
    return "validation" in lowered or "tests" in lowered or "pytest" in lowered


def _closes_issue_value(*, body: str, closing_refs: Sequence[Any]) -> str:
    if closing_refs:
        numbers = []
        for ref in closing_refs:
            if isinstance(ref, Mapping) and ref.get("number") is not None:
                numbers.append(f"#{ref['number']}")
        if numbers:
            return ",".join(numbers)
    match = re.search(r"\bCloses\s+#(\d+)\b", body, flags=re.IGNORECASE)
    return f"#{match.group(1)}" if match else ""


def _unsafe_claims_absent(body: str) -> bool:
    lowered = body.casefold()
    unsafe_needles = set()
    for claim in FORBIDDEN_CLAIMS:
        normalized = claim.casefold()
        unsafe_needles.add(normalized)
        unsafe_needles.add(normalized.rstrip("."))
    return not any(needle in lowered for needle in unsafe_needles)


def gh_pr_payloads(pr_numbers: Sequence[int], *, repo_root: Path | None = None) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    fields = "number,title,state,baseRefName,headRefName,headRefOid,mergeStateStatus,isDraft,url,body,closingIssuesReferences"
    for number in pr_numbers:
        try:
            result = subprocess.run(
                ["gh", "pr", "view", str(number), "--json", fields],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(repo_root) if repo_root is not None else None,
            )
        except (OSError, subprocess.SubprocessError):
            payloads.append({"number": number})
            continue
        payloads.append(json.loads(result.stdout))
    return payloads


def tracked_forbidden_artifacts(repo_root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "out", "artifacts", "results", "runs", ".venv"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def _write_frame_bundle(*, output_root: Path, stem: str, frame: pd.DataFrame, title: str, intro_lines: list[str]) -> dict[str, str]:
    output_root = ensure_dir(output_root)
    csv_path = output_root / f"{stem}.csv"
    json_path = output_root / f"{stem}.json"
    md_path = output_root / f"{stem}.md"
    frame.to_csv(csv_path, index=False)
    write_json(json_path, {"rows": frame.to_dict(orient="records")})
    write_markdown_table(md_path, frame, title=title, intro_lines=intro_lines)
    return {f"{stem}_csv": str(csv_path), f"{stem}_json": str(json_path), f"{stem}_md": str(md_path)}


def write_goal4a_evidence_package_outputs(
    *,
    output_root: Path,
    pr_readiness: pd.DataFrame,
    evidence_manifest: pd.DataFrame,
    claim_boundary: pd.DataFrame,
    decision_metadata: Mapping[str, Any],
) -> dict[str, str]:
    paths: dict[str, str] = {}
    paths.update(
        _write_frame_bundle(
            output_root=output_root,
            stem="pr_stack_merge_readiness",
            frame=pr_readiness,
            title="TOMICS-HAF 2025-2C PR Stack Merge Readiness",
            intro_lines=[
                "Merge order is PR #309 -> PR #311 -> PR #313 -> PR #315.",
                "No shipped TOMICS default change is recommended at this stage.",
            ],
        )
    )
    paths.update(
        _write_frame_bundle(
            output_root=output_root,
            stem="evidence_package_manifest",
            frame=evidence_manifest,
            title="TOMICS-HAF 2025-2C Evidence Package Manifest",
            intro_lines=[
                "Private paths under out/ are manifest evidence and are not committed.",
                "Manifest-only Plotkit evidence is partial until rendered PNGs exist.",
            ],
        )
    )
    paths.update(
        _write_frame_bundle(
            output_root=output_root,
            stem="claim_boundary_freeze",
            frame=claim_boundary,
            title="TOMICS-HAF 2025-2C Claim Boundary Freeze",
            intro_lines=[
                "Forbidden claims require the safe rewrite before manuscript or thesis use.",
                "Promotion and shipped default changes remain blocked by cross-dataset evidence insufficiency.",
            ],
        )
    )
    decision_path = output_root / "goal4a_decision_metadata.json"
    write_json(decision_path, decision_metadata)
    paths["goal4a_decision_metadata_json"] = str(decision_path)
    return paths


__all__ = [
    "ALLOWED_PRIMARY_CLAIMS",
    "FORBIDDEN_CLAIMS",
    "GOAL4A_PIPELINE_VERSION",
    "MERGE_ORDER",
    "build_claim_boundary_freeze_rows",
    "build_evidence_package_manifest",
    "build_goal4a_decision_metadata",
    "build_pr_stack_merge_readiness_rows",
    "gh_pr_payloads",
    "tracked_forbidden_artifacts",
    "write_goal4a_evidence_package_outputs",
]
