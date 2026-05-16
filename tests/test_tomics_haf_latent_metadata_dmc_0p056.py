import json
from pathlib import Path

import yaml

from tomics_haf_latent_fixtures import feature_frame, latent_config, observer_metadata

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.pipeline import (
    run_tomics_haf_latent_allocation,
)


def test_latent_metadata_carries_canonical_dmc_0p056(tmp_path: Path) -> None:
    feature_path = tmp_path / "feature.csv"
    metadata_path = tmp_path / "metadata.json"
    output_root = tmp_path / "latent_out"
    feature_frame().to_csv(feature_path, index=False)
    metadata = observer_metadata()
    metadata.update(
        {
            "harvest_yield_available": True,
            "fresh_yield_available": True,
            "fresh_yield_source": "legacy_v1_3_derived_output",
            "dry_yield_available": True,
            "dry_yield_source": "fresh_yield_times_canonical_DMC_0p056",
            "dry_yield_is_dmc_estimated": True,
            "direct_dry_yield_measured": False,
            "DMC_conversion_performed": True,
            "legacy_yield_bridge_used": True,
            "legacy_yield_bridge_provenance": "legacy_v1_3_derived_output",
        }
    )
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    config = latent_config(output_root)
    config["paths"]["repo_root"] = str(tmp_path)
    config["tomics_haf"]["observer_feature_frame"] = str(feature_path)
    config["tomics_haf"]["observer_metadata"] = str(metadata_path)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    result = run_tomics_haf_latent_allocation(config_path)
    latent_metadata = result["metadata"]

    assert latent_metadata["canonical_fruit_DMC_fraction"] == 0.056
    assert latent_metadata["fruit_DMC_fraction"] == 0.056
    assert latent_metadata["default_fruit_dry_matter_content"] == 0.056
    assert latent_metadata["DMC_fixed_for_2025_2C"] is True
    assert latent_metadata["DMC_sensitivity_enabled"] is False
    assert latent_metadata["DMC_sensitivity_values"] == []
    assert latent_metadata["deprecated_previous_default_fruit_DMC_fraction"] == 0.065
    assert latent_metadata["dry_yield_is_dmc_estimated"] is True
    assert latent_metadata["direct_dry_yield_measured"] is False
    assert latent_metadata["latent_allocation_directly_validated"] is False
    assert "configured_default_fruit_dry_matter_content" not in latent_metadata
