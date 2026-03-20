"""Canonical TOMICS-Alloc package."""

from stomatal_optimiaztion.domains.tomato.tomics.alloc.contracts import (
    Context,
    EnvStep,
    Module,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.interface import (
    PipelineModel,
    StepModel,
    run_flux_step,
    simulate,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.models.thorp_ref import (
    THORPReferenceAdapter,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.models.tomato_legacy import (
    TomatoLegacyAdapter,
    TomatoLegacyModule,
    TomatoModel,
    create_sample_input_csv,
    iter_forcing_csv,
    make_tomato_legacy_model,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import (
    TomatoDayrunArtifacts,
    config_payload_for_exp_key,
    resolve_forcing_path,
    resolve_repo_root,
    run_tomato_dayrun,
    run_tomato_dayrun_from_config,
    run_tomato_legacy_pipeline,
    summarize_tomato_legacy_metrics,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning import (
    TomicsPolicy,
    build_partition_policy,
    coerce_partition_policy,
)

MODEL_NAME = "TOMICS-Alloc"
PARTITION_POLICY_ALIASES = ("tomics", "tomics_alloc", "tomics_hybrid", "tomics-alloc")

__all__ = [
    "MODEL_NAME",
    "PARTITION_POLICY_ALIASES",
    "Context",
    "EnvStep",
    "Module",
    "StepModel",
    "PipelineModel",
    "run_flux_step",
    "simulate",
    "TomicsPolicy",
    "build_partition_policy",
    "coerce_partition_policy",
    "iter_forcing_csv",
    "TomatoLegacyAdapter",
    "TomatoLegacyModule",
    "make_tomato_legacy_model",
    "TomatoModel",
    "THORPReferenceAdapter",
    "create_sample_input_csv",
    "TomatoDayrunArtifacts",
    "resolve_repo_root",
    "resolve_forcing_path",
    "config_payload_for_exp_key",
    "run_tomato_dayrun",
    "run_tomato_dayrun_from_config",
    "run_tomato_legacy_pipeline",
    "summarize_tomato_legacy_metrics",
]
