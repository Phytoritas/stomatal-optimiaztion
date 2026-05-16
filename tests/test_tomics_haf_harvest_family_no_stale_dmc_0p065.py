from pathlib import Path

import json

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_harvest_factorial import (
    build_haf_harvest_factorial_design,
    run_tomics_haf_harvest_family_factorial,
)

from tests.tomics_haf_harvest_fixtures import (
    synthetic_haf_harvest_config,
    write_synthetic_haf_harvest_inputs,
)


def test_haf_harvest_no_stale_primary_0p065(tmp_path: Path) -> None:
    paths = write_synthetic_haf_harvest_inputs(tmp_path)
    config = synthetic_haf_harvest_config(paths)
    design = build_haf_harvest_factorial_design(config)

    assert set(design["fdmc_mode"]) == {"constant_0p056"}

    result = run_tomics_haf_harvest_family_factorial(
        config,
        repo_root=tmp_path,
        config_path=tmp_path / "config.yaml",
    )
    metadata = json.loads(Path(result["paths"]["metadata"]).read_text())
    audit = pd.read_csv(result["paths"]["stale_dmc_audit"])

    assert metadata["default_fruit_dry_matter_content"] == 0.056
    assert metadata["fruit_DMC_fraction"] == 0.056
    assert metadata["deprecated_previous_default_fruit_DMC_fraction"] == 0.065
    assert metadata["DMC_sensitivity_enabled"] is False
    assert "configured_default_fruit_dry_matter_content" not in metadata
    assert audit["status"].iloc[0] == "pass"


def test_haf_harvest_stale_audit_cleans_upstream_metadata_warning(tmp_path: Path) -> None:
    paths = write_synthetic_haf_harvest_inputs(tmp_path)
    observer_metadata = json.loads(paths["observer_metadata"].read_text())
    observer_metadata["configured_default_fruit_dry_matter_content"] = 0.065
    paths["observer_metadata"].write_text(json.dumps(observer_metadata), encoding="utf-8")

    result = run_tomics_haf_harvest_family_factorial(
        synthetic_haf_harvest_config(paths),
        repo_root=tmp_path,
        config_path=tmp_path / "config.yaml",
    )

    audit = pd.read_csv(result["paths"]["stale_dmc_audit"])
    cleaned_metadata = json.loads(paths["observer_metadata"].read_text())
    warning_hits = json.loads(audit["upstream_metadata_warning_hits_json"].iloc[0])
    assert audit["status"].iloc[0] == "pass"
    assert warning_hits == []
    assert "configured_default_fruit_dry_matter_content" not in cleaned_metadata
    assert (
        cleaned_metadata["legacy_metadata"]["deprecated_previous_default_fruit_DMC_fraction"]
        == 0.065
    )
