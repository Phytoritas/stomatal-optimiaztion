# Module Spec 025: TOMATO tTHORP Contracts

## Purpose

Start the TOMATO migration with the smallest explicit `tTHORP` seam: the step contracts and coercion helpers that define forcing rows, context mutation, and bounded output validation.

## Source Inputs

- `TOMATO/tTHORP/src/tthorp/contracts.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/contracts.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/__init__.py`
- `tests/test_tomics_alloc_contracts.py`

## Responsibilities

1. preserve the legacy `EnvStep.from_row` parsing and timestep clipping behavior
2. preserve the `Context` and `Module` step-contract surface for later pipeline slices
3. keep the first TOMATO slice stdlib-only so the nested workspace boundary is explicit before adding pandas-backed interfaces

## Non-Goals

- port `interface.py`
- port tomato adapters, pipelines, or CLI entrypoints
- introduce shared abstractions between THORP and TOMATO

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TOMATO/tTHORP/src/tthorp/interface.py`
