from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_promotion_gate import (
    run_haf_promotion_gate,
)
from tests.tomics_haf_gate_fixtures import write_haf_gate_fixture


def test_haf_promotion_gate_preserves_dmc_0p056_contract(tmp_path):
    fixture = write_haf_gate_fixture(tmp_path)

    metadata = run_haf_promotion_gate(
        fixture["promotion_config"],
        repo_root=fixture["repo_root"],
        config_path=fixture["config_path"],
    )["metadata"]

    assert metadata["canonical_fruit_DMC_fraction"] == 0.056
    assert metadata["DMC_sensitivity_enabled"] is False
    assert metadata["dry_yield_is_dmc_estimated"] is True
    assert metadata["direct_dry_yield_measured"] is False
