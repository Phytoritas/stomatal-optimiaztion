from __future__ import annotations

from stomatal_optimiaztion.domains.tomato.tomics.flux.contracts import (
    OptimizationRequest,
    OptimizationResult,
    clamp_nonnegative,
)


def run_stomatal_optimization(request: OptimizationRequest) -> OptimizationResult:
    """TOMICS-Flux step contract.

    Placeholder optimizer that returns a nonnegative conductance target and
    keeps explicit WUE multiplier output for downstream coupling.
    """

    stress_gain = max(0.0, min(1.0, request.water_supply_stress))
    g_w_opt = clamp_nonnegative(request.current_g_w * stress_gain)
    return OptimizationResult(
        g_w_opt=g_w_opt,
        lambda_wue=1.0,
        objective_value=0.0,
    )
