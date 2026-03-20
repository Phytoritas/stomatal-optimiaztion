"""Canonical TOMICS tomato-facing namespace."""

from stomatal_optimiaztion.domains.tomato.tomics import alloc, flux, grow

MODEL_NAME = "TOMICS"
ALLOC_NAME = "TOMICS-Alloc"
FLUX_NAME = "TOMICS-Flux"
GROW_NAME = "TOMICS-Grow"

__all__ = [
    "MODEL_NAME",
    "ALLOC_NAME",
    "FLUX_NAME",
    "GROW_NAME",
    "alloc",
    "flux",
    "grow",
]
