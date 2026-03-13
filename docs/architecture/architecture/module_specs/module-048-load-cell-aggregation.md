# Module Spec 048: load-cell-data Aggregation

## Purpose

Open the next bounded `load-cell-data` seam by porting the aggregation helpers that downsample per-second flux outputs and assemble daily summaries.

## Source Inputs

- `load-cell-data/loadcell_pipeline/aggregation.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/load_cell/aggregation.py`
- `src/stomatal_optimiaztion/domains/load_cell/__init__.py`
- `tests/test_load_cell_aggregation.py`

## Responsibilities

1. preserve coarse-timescale resampling of irrigation, drainage, and transpiration fluxes
2. preserve daily summary assembly, including event counts, label-derived durations, and metadata passthrough
3. keep the seam aggregation-bounded without widening into preprocessing, workflow, or CLI surfaces

## Non-Goals

- migrate `load-cell-data/loadcell_pipeline/thresholds.py`
- migrate `load-cell-data/loadcell_pipeline/preprocessing.py`
- widen into workflow or dashboard entrypoints

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `load-cell-data/loadcell_pipeline/thresholds.py`
