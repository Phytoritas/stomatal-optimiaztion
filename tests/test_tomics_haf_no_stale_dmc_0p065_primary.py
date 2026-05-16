from pathlib import Path


HAF_PRIMARY_PATHS = [
    Path("configs/exp/tomics_haf_2025_2c_observer_pipeline.yaml"),
    Path("configs/exp/tomics_haf_2025_2c_observer_pipeline_production.yaml"),
    Path("configs/exp/tomics_haf_2025_2c_latent_allocation.yaml"),
    Path("src/stomatal_optimiaztion/domains/tomato/tomics/observers/contracts.py"),
    Path("src/stomatal_optimiaztion/domains/tomato/tomics/observers/feature_frame.py"),
    Path("src/stomatal_optimiaztion/domains/tomato/tomics/observers/metadata_contract.py"),
    Path("src/stomatal_optimiaztion/domains/tomato/tomics/observers/pipeline.py"),
    Path("src/stomatal_optimiaztion/domains/tomato/tomics/observers/yield_bridge.py"),
    Path("docs/architecture/tomics/fresh_dry_yield_bridge_contract.md"),
    Path("docs/architecture/tomics/harvest_aware_promotion_gate.md"),
    Path("docs/architecture/tomics/harvest_family_architecture.md"),
    Path("docs/architecture/tomics/harvest_family_factorial_design_2025_2c.md"),
    Path("docs/architecture/tomics/legacy_v1_3_bridge_contract.md"),
    Path("docs/architecture/tomics/latent_allocation_inference_with_thorp_prior.md"),
    Path("docs/architecture/tomics/new_phytologist_readiness_checklist.md"),
    Path("docs/architecture/tomics/pr_309_goal2_5_summary.md"),
    Path("docs/architecture/tomics/tomics_haf_2025_2c_actual_data_pipeline.md"),
]


def test_haf_2025_2c_primary_files_do_not_use_0p065_as_current_default() -> None:
    forbidden_tokens = (
        "configured_default_fruit_dry_matter_content",
        "constant_0p065",
        "dmc_0p065",
        "fruit_DMC_fraction = 0.065",
        "default_fruit_dry_matter_content = 0.065",
        "default DMC = 0.065",
    )
    for path in HAF_PRIMARY_PATHS:
        text = path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            assert token not in text
        for line in text.splitlines():
            if "0.065" in line:
                lowered = line.lower()
                assert "deprecated" in lowered or "previous" in lowered or "historical" in lowered
