from tomics_haf_latent_fixtures import feature_frame, latent_config, observer_metadata

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.contracts import (
    DIRECT_VALIDATION_STATEMENT,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.diagnostics import (
    compute_allocation_identifiability,
    compute_observer_support_scores,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.input_state import (
    build_latent_allocation_input_state,
)


def test_direct_partition_absence_is_not_direct_validation() -> None:
    state, _ = build_latent_allocation_input_state(feature_frame(), observer_metadata(), latent_config())
    identifiability = compute_allocation_identifiability(state, observer_metadata())
    row = identifiability.iloc[0]

    assert bool(row["direct_partition_observation_available"]) is False
    assert bool(row["latent_allocation_directly_validated"]) is False
    assert row["identifiability_interpretation"] == "not_direct_validation"
    assert row["diagnostic_statement"] == DIRECT_VALIDATION_STATEMENT


def test_observer_group_counts_are_reported() -> None:
    state, _ = build_latent_allocation_input_state(feature_frame(), observer_metadata(), latent_config())
    support = compute_observer_support_scores(state, observer_metadata())

    assert bool(support["radiation_daynight_et_available"]) is True
    assert bool(support["rootzone_rzi_available"]) is True
    assert bool(support["apparent_conductance_available"]) is True
    assert support["observer_group_count"] >= 3
    assert support["allocation_identifiability_score"] == "medium"
