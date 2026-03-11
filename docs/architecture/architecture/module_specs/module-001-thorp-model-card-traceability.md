# Module Spec 001: THORP Model-Card Traceability

## Purpose

Migrate the lowest-risk THORP seam first by bringing equation metadata and traceability helpers into the new package layout.

## Source Inputs

- `THORP/model_card/*.json`
- `THORP/src/thorp/implements.py`
- traceability patterns from `THORP/src/thorp/equation_registry.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/model_card.py`
- `src/stomatal_optimiaztion/domains/thorp/implements.py`
- `src/stomatal_optimiaztion/domains/thorp/traceability.py`
- `tests/test_thorp_model_card.py`
- `tests/test_thorp_traceability.py`

## Responsibilities

1. expose THORP equation metadata from in-package JSON assets
2. preserve decorator-based equation tagging for future migrated callables
3. provide a generic mapping helper that later runtime modules can reuse
4. keep the seam stdlib-only so validation stays lightweight

## Non-Goals

- copy the THORP source PDF into this repo
- migrate runtime simulation modules or numerical kernels
- introduce cross-domain shared abstractions

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Artifact Policy

- keep only the curated JSON model-card assets in Git
- exclude MATLAB outputs, generated plots, caches, and binary reference files
