# Module Spec 067: THORP Model Namespace

## Purpose

Restore the legacy `thorp.model` convenience import surface over the already migrated allocation, growth, hydraulics, radiation, and soil helpers.

## Source Inputs

- `THORP/src/thorp/model/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/model/__init__.py`
- `tests/test_thorp_model_namespace.py`

## Responsibilities

1. preserve the `thorp.model` grouped import surface for model-core helpers
2. preserve symbol identity instead of wrapping or redefining existing helpers
3. keep the seam namespace-wrapper-bounded instead of widening into new runtime abstractions

## Non-Goals

- redesign allocation, growth, hydraulics, radiation, or soil runtime modules
- widen the THORP root package exports in the same slice
- migrate the broadened `thorp.params` compatibility surface in the same slice

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `THORP/src/thorp/params/__init__.py`
