from stomatal_optimiaztion.domains.tomato.ttdgm.contracts import (
    GrowthDrivers,
    GrowthStepOutput,
    OrganAllocationFractions,
    OrganCarbonPools,
    validate_allocations,
)

MODEL_NAME = "tTDGM"

__all__ = [
    "MODEL_NAME",
    "GrowthDrivers",
    "GrowthStepOutput",
    "OrganAllocationFractions",
    "OrganCarbonPools",
    "validate_allocations",
]
