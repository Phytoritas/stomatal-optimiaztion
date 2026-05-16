import json

import pytest

from scripts.run_tomics_haf_evidence_package import load_required_promotion_metadata
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_goal4a_evidence_package import (
    build_claim_boundary_freeze_rows,
    build_evidence_package_manifest,
    build_pr_stack_merge_readiness_rows,
    write_goal4a_evidence_package_outputs,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_promotion_gate import (
    run_haf_promotion_gate,
)
from tests.tomics_haf_gate_fixtures import write_haf_gate_fixture


def test_goal4a_evidence_package_manifest_records_required_categories(tmp_path):
    fixture = write_haf_gate_fixture(tmp_path)
    run_haf_promotion_gate(
        fixture["promotion_config"],
        repo_root=fixture["repo_root"],
        config_path=fixture["config_path"],
    )
    frame = build_evidence_package_manifest(
        repo_root=fixture["repo_root"],
        promotion_root=fixture["promotion_root"],
        harvest_root=fixture["harvest_root"],
        latent_root=fixture["repo_root"] / "out" / "tomics" / "validation" / "latent-allocation" / "haf_2025_2c",
        observer_root=fixture["repo_root"] / "out" / "tomics" / "analysis" / "haf_2025_2c",
        figures_root=fixture["repo_root"] / "out" / "tomics" / "figures" / "haf_2025_2c",
    )

    assert {
        "observer",
        "latent_allocation",
        "harvest_family",
        "promotion_cross_dataset",
        "figures",
    }.issubset(set(frame["stage"]))
    assert frame.loc[frame["path"].str.startswith("out/"), "committed_or_private"].eq("private_uncommitted").all()
    assert frame["safe_claim_supported"].astype(str).str.len().gt(0).all()
    assert frame["limitation"].astype(str).str.len().gt(0).all()
    assert "rendered_png_status" in set(frame["evidence_id"])


def test_goal4a_evidence_package_writer_emits_private_bundle(tmp_path):
    out_root = tmp_path / "out" / "tomics" / "validation" / "promotion-gate" / "haf_2025_2c"
    pr_readiness = build_pr_stack_merge_readiness_rows(
        [
            {
                "number": 309,
                "title": "observer",
                "state": "OPEN",
                "baseRefName": "main",
                "headRefName": "fix/308-diagnose-tomics-daily-harvest-increments",
                "headRefOid": "sha-309",
                "mergeStateStatus": "CLEAN",
                "isDraft": False,
                "body": "## Validation\npytest passed",
            },
            {
                "number": 311,
                "title": "latent",
                "state": "OPEN",
                "baseRefName": "fix/308-diagnose-tomics-daily-harvest-increments",
                "headRefName": "feat/tomics-haf-2025-2c-latent-allocation",
                "headRefOid": "sha-311",
                "mergeStateStatus": "CLEAN",
                "isDraft": False,
                "body": "## Validation\npytest passed",
            },
            {
                "number": 313,
                "title": "harvest",
                "state": "OPEN",
                "baseRefName": "feat/tomics-haf-2025-2c-latent-allocation",
                "headRefName": "feat/tomics-haf-2025-2c-harvest-family-eval",
                "headRefOid": "sha-313",
                "mergeStateStatus": "CLEAN",
                "isDraft": False,
                "body": "## Validation\npytest passed",
            },
            {
                "number": 315,
                "title": "promotion gate",
                "state": "OPEN",
                "baseRefName": "feat/tomics-haf-2025-2c-harvest-family-eval",
                "headRefName": "feat/tomics-haf-2025-2c-promotion-gate",
                "headRefOid": "sha-315",
                "mergeStateStatus": "CLEAN",
                "isDraft": False,
                "body": "Closes #314\n\n## Validation\npytest passed",
            },
        ]
    )
    evidence_manifest = build_evidence_package_manifest(
        repo_root=tmp_path,
        promotion_root=out_root,
        harvest_root=tmp_path / "out" / "tomics" / "validation" / "harvest-family" / "haf_2025_2c",
        latent_root=tmp_path / "out" / "tomics" / "validation" / "latent-allocation" / "haf_2025_2c",
        observer_root=tmp_path / "out" / "tomics" / "analysis" / "haf_2025_2c",
    )
    paths = write_goal4a_evidence_package_outputs(
        output_root=out_root,
        pr_readiness=pr_readiness,
        evidence_manifest=evidence_manifest,
        claim_boundary=build_claim_boundary_freeze_rows(
            promotion_gate_passed=False,
            cross_dataset_gate_passed=False,
            shipped_default_changed=False,
        ).head(1),
        decision_metadata={"promotion_remains_blocked": True},
    )

    assert (out_root / "evidence_package_manifest.csv").exists()
    assert (out_root / "evidence_package_manifest.json").exists()
    assert (out_root / "evidence_package_manifest.md").exists()
    assert "goal4a_decision_metadata_json" in paths


def test_goal4a_evidence_runner_requires_executed_promotion_metadata(tmp_path):
    promotion_root = tmp_path / "out" / "tomics" / "validation" / "promotion-gate" / "haf_2025_2c"
    with pytest.raises(FileNotFoundError):
        load_required_promotion_metadata(repo_root=tmp_path, promotion_root=promotion_root)

    metadata_path = promotion_root / "promotion_gate_metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps({"promotion_gate_run": "false", "cross_dataset_gate_run": "true"}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="promotion_gate_run=true"):
        load_required_promotion_metadata(repo_root=tmp_path, promotion_root=promotion_root)


def test_goal4a_evidence_runner_rejects_unfrozen_promotion_metadata(tmp_path):
    promotion_root = tmp_path / "out" / "tomics" / "validation" / "promotion-gate" / "haf_2025_2c"
    metadata_path = promotion_root / "promotion_gate_metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(
            {
                "promotion_gate_run": True,
                "cross_dataset_gate_run": True,
                "promotion_gate_passed": True,
                "cross_dataset_gate_passed": False,
                "promotion_gate_status": "blocked_cross_dataset_evidence_insufficient",
                "cross_dataset_gate_status": "blocked_insufficient_measured_datasets",
                "measured_dataset_count": 1,
                "required_measured_dataset_count": 2,
                "promoted_candidate_id": "candidate",
                "shipped_TOMICS_incumbent_changed": False,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="promotion_gate_passed=true"):
        load_required_promotion_metadata(repo_root=tmp_path, promotion_root=promotion_root)

    metadata_path.write_text(
        json.dumps(
            {
                "promotion_gate_run": True,
                "cross_dataset_gate_run": True,
                "promotion_gate_passed": False,
                "cross_dataset_gate_passed": False,
                "promotion_gate_status": "blocked_cross_dataset_evidence_insufficient",
                "cross_dataset_gate_status": "blocked_insufficient_measured_datasets",
                "measured_dataset_count": 1,
                "required_measured_dataset_count": 2,
                "promoted_candidate_id": None,
                "shipped_TOMICS_incumbent_changed": "true",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="shipped_TOMICS_incumbent_changed=false"):
        load_required_promotion_metadata(repo_root=tmp_path, promotion_root=promotion_root)

    metadata_path.write_text(
        json.dumps(
            {
                "promotion_gate_run": True,
                "cross_dataset_gate_run": True,
                "promotion_gate_passed": False,
                "cross_dataset_gate_passed": False,
                "promotion_gate_status": "passed",
                "cross_dataset_gate_status": "blocked_insufficient_measured_datasets",
                "measured_dataset_count": 1,
                "required_measured_dataset_count": 2,
                "promoted_candidate_id": None,
                "shipped_TOMICS_incumbent_changed": False,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="promotion_gate_status=blocked_cross_dataset_evidence_insufficient"):
        load_required_promotion_metadata(repo_root=tmp_path, promotion_root=promotion_root)

    metadata_path.write_text(
        json.dumps(
            {
                "promotion_gate_run": True,
                "cross_dataset_gate_run": True,
                "promotion_gate_passed": False,
                "cross_dataset_gate_passed": False,
                "promotion_gate_status": "blocked_cross_dataset_evidence_insufficient",
                "cross_dataset_gate_status": "blocked_insufficient_measured_datasets",
                "measured_dataset_count": 2,
                "required_measured_dataset_count": 2,
                "promoted_candidate_id": None,
                "shipped_TOMICS_incumbent_changed": False,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="measured_dataset_count"):
        load_required_promotion_metadata(repo_root=tmp_path, promotion_root=promotion_root)

    metadata_path.write_text(
        json.dumps(
            {
                "promotion_gate_run": True,
                "cross_dataset_gate_run": True,
                "promotion_gate_passed": False,
                "cross_dataset_gate_passed": False,
                "promotion_gate_status": "blocked_cross_dataset_evidence_insufficient",
                "cross_dataset_gate_status": "blocked_insufficient_measured_datasets",
                "required_measured_dataset_count": 2,
                "promoted_candidate_id": None,
                "shipped_TOMICS_incumbent_changed": False,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="requires measured_dataset_count"):
        load_required_promotion_metadata(repo_root=tmp_path, promotion_root=promotion_root)

    metadata_path.write_text(
        json.dumps(
            {
                "promotion_gate_run": True,
                "cross_dataset_gate_run": True,
                "promotion_gate_passed": False,
                "cross_dataset_gate_passed": False,
                "promotion_gate_status": "blocked_cross_dataset_evidence_insufficient",
                "cross_dataset_gate_status": "blocked_insufficient_measured_datasets",
                "measured_dataset_count": "not_numeric",
                "required_measured_dataset_count": 2,
                "promoted_candidate_id": None,
                "shipped_TOMICS_incumbent_changed": False,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="non-negative integer"):
        load_required_promotion_metadata(repo_root=tmp_path, promotion_root=promotion_root)

    metadata_path.write_text(
        json.dumps(
            {
                "promotion_gate_run": True,
                "cross_dataset_gate_run": True,
                "promotion_gate_passed": False,
                "cross_dataset_gate_passed": False,
                "promotion_gate_status": "blocked_cross_dataset_evidence_insufficient",
                "cross_dataset_gate_status": "blocked_insufficient_measured_datasets",
                "measured_dataset_count": "1.5",
                "required_measured_dataset_count": 2,
                "promoted_candidate_id": None,
                "shipped_TOMICS_incumbent_changed": False,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="non-negative integer"):
        load_required_promotion_metadata(repo_root=tmp_path, promotion_root=promotion_root)

    metadata_path.write_text(
        json.dumps(
            {
                "promotion_gate_run": True,
                "cross_dataset_gate_run": True,
                "promotion_gate_passed": False,
                "cross_dataset_gate_passed": False,
                "promotion_gate_status": "blocked_cross_dataset_evidence_insufficient",
                "cross_dataset_gate_status": "blocked_insufficient_measured_datasets",
                "measured_dataset_count": False,
                "required_measured_dataset_count": 2,
                "promoted_candidate_id": None,
                "shipped_TOMICS_incumbent_changed": False,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="non-negative integer"):
        load_required_promotion_metadata(repo_root=tmp_path, promotion_root=promotion_root)
