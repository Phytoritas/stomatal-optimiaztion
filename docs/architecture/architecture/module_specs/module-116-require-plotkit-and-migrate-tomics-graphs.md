# Module Spec 116: Require Plotkit And Migrate TOMICS Graphs

## Purpose

Standardize reusable repo-local graph rendering on a Plotkit-style spec-first bundle contract and migrate the live TOMICS graph scripts onto that path without changing tomato model semantics.

## Source Inputs

- `configs/plotkit/thorp/`
- `configs/plotkit/gosm/`
- `configs/plotkit/tdgm/`
- `src/stomatal_optimiaztion/shared_plotkit.py`
- live TOMICS graph scripts under `scripts/`

## Target Outputs

- `configs/plotkit/tomics/` specs
- TOMICS Plotkit renderer helpers under `src/stomatal_optimiaztion/domains/tomato/tomics/`
- updated graph scripts and tests
- bundle outputs with `png`, `pdf`, spec copy, resolved spec, tokens copy, metadata, and data CSV

## Responsibilities

1. keep existing TOMICS runner behavior stable apart from the rendering backend
2. make Plotkit spec-first rendering the repo-local default for reusable figures
3. preserve current output filenames while expanding them into reproducible bundles
4. avoid reintroducing tomato legacy import paths or naming churn

## Non-Goals

- changing tomato allocation semantics
- removing the root rerun parity figure surfaces
- introducing a destructive plotting refactor across unrelated code paths

## Validation

- targeted TOMICS plotting tests
- TOMICS compare/factorial/architecture runner tests
- current TOMICS compare/factorial runners
- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- if root rerun parity renderers need the same expanded bundle contract later, reuse the TOMICS Plotkit helper path rather than adding new ad-hoc figure code
