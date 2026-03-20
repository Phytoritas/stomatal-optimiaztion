# Module Spec 038: TOMATO tTHORP Feature-Builder Script

## Purpose

Open the next bounded TOMATO `tTHORP` seam by porting the repo-level feature-builder script that converts forcing CSV inputs into deterministic feature CSV outputs for downstream runs.

## Source Inputs

- `TOMATO/tTHORP/scripts/make_features.py`
- `TOMATO/tTHORP/src/tthorp/core/util_units.py`

## Target Outputs

- `scripts/make_features.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/core/util_units.py`
- `tests/test_tomics_alloc_make_features_script.py`
- `tests/test_tomics_alloc_util_units.py`

## Responsibilities

1. preserve CLI argument parsing for config path and output-path override
2. preserve deterministic feature CSV output naming, SW-to-PAR conversion, and forcing default injection
3. expose shared PAR conversion helpers through the migrated `core` surface

## Non-Goals

- migrate `TOMATO/tTHORP/src/tthorp/models/thorp_ref/adapter.py`
- migrate plotting scripts under `TOMATO/tTHORP/scripts/`
- broaden into non-TOMATO repo-level automation entrypoints

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TOMATO/tTHORP/src/tthorp/models/thorp_ref/adapter.py`
