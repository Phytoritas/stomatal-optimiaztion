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
    TomatoModel,
    create_sample_input_csv,
    iter_forcing_csv,
    make_tomato_legacy_model,
)
from stomatal_optimiaztion.domains.tomato.tthorp.pipelines import (
    config_payload_for_exp_key,
    resolve_forcing_path,
    resolve_repo_root,
    run_tomato_legacy_pipeline,
    summarize_tomato_legacy_metrics,
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
    "TomatoModel",
    "create_sample_input_csv",
    "resolve_repo_root",
    "resolve_forcing_path",
    "config_payload_for_exp_key",
    "run_tomato_legacy_pipeline",
    "summarize_tomato_legacy_metrics",
]
