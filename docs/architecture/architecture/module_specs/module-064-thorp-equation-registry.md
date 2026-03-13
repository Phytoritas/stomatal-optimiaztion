# Module Spec 064: THORP Equation Registry

## Purpose

Open the next bounded THORP compatibility seam by restoring the explicit `equation_registry` module path over the already migrated traceability helpers and annotated runtime modules.

## Source Inputs

- `THORP/src/thorp/equation_registry.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/equation_registry.py`
- `tests/test_thorp_equation_registry.py`

## Responsibilities

1. preserve module-bound annotated-callable discovery across migrated THORP runtime modules
2. preserve one-call mapping construction without caller-provided namespaces
3. keep the seam compatibility-bounded instead of redesigning the traceability helper layer

## Non-Goals

- redesign `traceability.py` or `implements.py`
- widen the THORP root package exports in the same slice
- migrate the `THORP/src/thorp/utils/__init__.py` namespace wrapper in the same slice

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `THORP/src/thorp/utils/__init__.py`
