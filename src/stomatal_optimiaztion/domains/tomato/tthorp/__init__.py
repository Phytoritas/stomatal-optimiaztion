"""tTHORP package."""

from stomatal_optimiaztion.domains.tomato.tthorp.contracts import Context, EnvStep, Module
from stomatal_optimiaztion.domains.tomato.tthorp.interface import (
    PipelineModel,
    StepModel,
    run_flux_step,
    simulate,
)
from stomatal_optimiaztion.domains.tomato.tthorp.models.tomato_legacy import (
    TomatoLegacyAdapter,
    TomatoLegacyModule,
    iter_forcing_csv,
    make_tomato_legacy_model,
)

MODEL_NAME = "tTHORP"

__all__ = [
    "MODEL_NAME",
    "Context",
    "EnvStep",
    "Module",
    "StepModel",
    "PipelineModel",
    "run_flux_step",
    "simulate",
    "iter_forcing_csv",
    "TomatoLegacyAdapter",
    "TomatoLegacyModule",
    "make_tomato_legacy_model",
]
