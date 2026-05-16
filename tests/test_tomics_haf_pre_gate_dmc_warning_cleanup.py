from pathlib import Path

import json

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_harvest_factorial import (
    run_tomics_haf_harvest_family_factorial,
)

from tests.tomics_haf_harvest_fixtures import (
    synthetic_haf_harvest_config,
    write_synthetic_haf_harvest_inputs,
)


def test_pre_gate_dmc_warning_cleanup_removes_top_level_legacy_alias(
    tmp_path: Path,
) -> None:
    paths = write_synthetic_haf_harvest_inputs(tmp_path)
    observer_metadata = json.loads(paths["observer_metadata"].read_text())
    observer_metadata["configured_default_fruit_dry_matter_content"] = 0.065
    paths["observer_metadata"].write_text(json.dumps(observer_metadata), encoding="utf-8")

    result = run_tomics_haf_harvest_family_factorial(
        synthetic_haf_harvest_config(paths),
        repo_root=tmp_path,
        config_path=tmp_path / "config.yaml",
    )

    cleaned = json.loads(paths["observer_metadata"].read_text())
    metadata = json.loads(Path(result["paths"]["metadata"]).read_text())
    audit = pd.read_csv(result["paths"]["stale_dmc_audit"])
    analysis_audit = pd.read_csv(result["paths"]["analysis_stale_dmc_audit"])

    assert "configured_default_fruit_dry_matter_content" not in cleaned
    assert metadata["canonical_fruit_DMC_fraction"] == 0.056
    assert metadata["fruit_DMC_fraction"] == 0.056
    assert metadata["default_fruit_dry_matter_content"] == 0.056
    assert audit["upstream_metadata_warning_count"].iloc[0] == 0
    assert analysis_audit["upstream_metadata_warning_count"].iloc[0] == 0


def test_pre_gate_dmc_warning_cleanup_handles_case_variants(tmp_path: Path) -> None:
    paths = write_synthetic_haf_harvest_inputs(tmp_path)
    observer_metadata = json.loads(paths["observer_metadata"].read_text())
    observer_metadata["Configured_Default_Fruit_Dry_Matter_Content"] = 0.065
    paths["observer_metadata"].write_text(json.dumps(observer_metadata), encoding="utf-8")

    run_tomics_haf_harvest_family_factorial(
        synthetic_haf_harvest_config(paths),
        repo_root=tmp_path,
        config_path=tmp_path / "config.yaml",
    )

    cleaned = json.loads(paths["observer_metadata"].read_text())
    assert "Configured_Default_Fruit_Dry_Matter_Content" not in cleaned
    assert (
        cleaned["legacy_metadata"]["deprecated_previous_default_fruit_DMC_fraction"]
        == 0.065
    )
