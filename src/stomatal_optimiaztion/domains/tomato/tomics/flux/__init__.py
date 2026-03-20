"""Canonical TOMICS-Flux package."""

from stomatal_optimiaztion.domains.tomato.tomics.flux.contracts import (
    OptimizationRequest,
    OptimizationResult,
    clamp_nonnegative,
)
from stomatal_optimiaztion.domains.tomato.tomics.flux.interface import (
    run_stomatal_optimization,
)

MODEL_NAME = "TOMICS-Flux"

__all__ = [
    "MODEL_NAME",
    "OptimizationRequest",
    "OptimizationResult",
    "clamp_nonnegative",
    "run_stomatal_optimization",
]
