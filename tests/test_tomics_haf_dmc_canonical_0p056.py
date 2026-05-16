from stomatal_optimiaztion.domains.tomato.tomics.observers.contracts import (
    CANONICAL_2025_2C_FRUIT_DMC,
    DEFAULT_FRUIT_DRY_MATTER_CONTENT,
    DEPRECATED_PREVIOUS_DEFAULT_FRUIT_DMC,
    DMC_SENSITIVITY,
    base_metadata,
)


def test_haf_2025_2c_dmc_metadata_uses_fixed_0p056_contract() -> None:
    metadata = base_metadata()

    assert CANONICAL_2025_2C_FRUIT_DMC == 0.056
    assert DEFAULT_FRUIT_DRY_MATTER_CONTENT == 0.056
    assert DMC_SENSITIVITY == ()
    assert metadata["canonical_fruit_DMC_fraction"] == 0.056
    assert metadata["fruit_DMC_fraction"] == 0.056
    assert metadata["default_fruit_dry_matter_content"] == 0.056
    assert metadata["DMC_fixed_for_2025_2C"] is True
    assert metadata["DMC_sensitivity_enabled"] is False
    assert metadata["DMC_sensitivity_values"] == []
    assert metadata["deprecated_previous_default_fruit_DMC_fraction"] == DEPRECATED_PREVIOUS_DEFAULT_FRUIT_DMC
    assert metadata["deprecated_previous_default_fruit_DMC_fraction"] == 0.065
