# Module Spec 065: THORP Utilities Namespace

## Purpose

Open the next bounded THORP namespace-wrapper seam by restoring the legacy `thorp.utils` convenience import surface over the already migrated traceability and model-card helpers.

## Source Inputs

- `THORP/src/thorp/utils/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/utils/__init__.py`
- `tests/test_thorp_utils_namespace.py`

## Responsibilities

1. preserve the `thorp.utils` grouped import surface for equation-registry, implements, and model-card helpers
2. preserve symbol identity instead of wrapping or redefining existing helpers
3. keep the seam namespace-wrapper-bounded instead of widening into new shared utility abstractions

## Non-Goals

- redesign `equation_registry.py`, `implements.py`, or `model_card.py`
- widen the THORP root package exports in the same slice
- migrate the `THORP/src/thorp/io/__init__.py` namespace wrapper in the same slice

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `THORP/src/thorp/io/__init__.py`
