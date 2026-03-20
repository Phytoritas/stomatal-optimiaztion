# Module Spec 026: TOMATO tTHORP Interface

## Purpose

Open the next bounded TOMATO `tTHORP` seam by porting the pipeline-facing interface that binds migrated step contracts into a runnable `PipelineModel`, tabular simulation loop, and placeholder flux-step helper.

## Source Inputs

- `TOMATO/tTHORP/src/tthorp/interface.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/interface.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/__init__.py`
- `tests/test_tomics_alloc_interface.py`

## Responsibilities

1. preserve `PipelineModel.step` state mutation and finite-output coercion over migrated `Context` and `Module`
2. preserve `simulate()` column-stability checks and datetime handling while isolating the `pandas` dependency to this seam
3. preserve the lightweight `run_flux_step()` placeholder contract without pulling in tomato adapters or legacy model packages

## Non-Goals

- port `models/tomato_legacy/*`
- port TOMATO pipeline entrypoints or CLI wrappers
- introduce shared abstractions between THORP and TOMATO

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TOMATO/tTHORP/src/tthorp/models/tomato_legacy/forcing_csv.py`
