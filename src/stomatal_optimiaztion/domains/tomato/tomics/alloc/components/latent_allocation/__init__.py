"""TOMICS-HAF latent allocation inference artifacts."""

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.constraints import (
    apply_lai_protection,
    apply_root_stress_gate,
    apply_tomato_constraints,
    apply_wet_root_cap,
    normalize_allocation_fractions,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.diagnostics import (
    compute_allocation_identifiability,
    compute_observer_support_scores,
    compute_prior_family_diagnostics,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.guardrails import (
    evaluate_latent_allocation_guardrails,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.inference import (
    infer_latent_allocation,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.input_state import (
    LatentAllocationInputState,
    build_latent_allocation_input_state,
    check_production_preconditions,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.pipeline import (
    run_tomics_haf_latent_allocation,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.priors import (
    build_latent_allocation_priors,
    legacy_tomato_prior,
    thorp_bounded_prior,
    tomato_constrained_thorp_prior,
    validate_prior_families,
)

__all__ = [
    "apply_lai_protection",
    "apply_root_stress_gate",
    "apply_tomato_constraints",
    "apply_wet_root_cap",
    "LatentAllocationInputState",
    "build_latent_allocation_input_state",
    "build_latent_allocation_priors",
    "check_production_preconditions",
    "compute_allocation_identifiability",
    "compute_observer_support_scores",
    "compute_prior_family_diagnostics",
    "evaluate_latent_allocation_guardrails",
    "infer_latent_allocation",
    "legacy_tomato_prior",
    "normalize_allocation_fractions",
    "run_tomics_haf_latent_allocation",
    "thorp_bounded_prior",
    "tomato_constrained_thorp_prior",
    "validate_prior_families",
]
