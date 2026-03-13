# Module Spec 066: THORP IO Namespace

## Purpose

Restore the legacy `thorp.io` convenience import surface over the already migrated forcing and MATLAB compatibility helpers.

## Source Inputs

- `THORP/src/thorp/io/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/io/__init__.py`
- `tests/test_thorp_io_namespace.py`

## Responsibilities

1. preserve the `thorp.io` grouped import surface for forcing and MATLAB I/O helpers
2. preserve symbol identity instead of wrapping or redefining existing helpers
3. keep the seam namespace-wrapper-bounded instead of widening into new file-format or forcing abstractions

## Non-Goals

- redesign `forcing.py` or `matlab_io.py`
- widen the THORP root package exports in the same slice
- migrate the `THORP/src/thorp/model/__init__.py` namespace wrapper in the same slice

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `THORP/src/thorp/model/__init__.py`
