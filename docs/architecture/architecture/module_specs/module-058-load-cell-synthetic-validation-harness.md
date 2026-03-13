# Module Spec 058: load-cell-data Synthetic Validation Harness

## Purpose

Open the next bounded `load-cell-data` seam by porting the synthetic dataset generator and end-to-end validation harness that exercises the migrated pipeline without external greenhouse files.

## Source Inputs

- `load-cell-data/loadcell_pipeline/synthetic_test.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/load_cell/synthetic_test.py`
- `src/stomatal_optimiaztion/domains/load_cell/__init__.py`
- `tests/test_load_cell_synthetic_test.py`

## Responsibilities

1. preserve deterministic synthetic dataset generation and ground-truth irrigation, drainage, and transpiration totals
2. preserve full-pipeline execution via `run_pipeline()` plus tolerance-based validation of estimates and water-balance bias
3. keep the seam validation-harness-bounded without widening into repo-level real-data benchmarks or dashboard surfaces

## Non-Goals

- migrate `load-cell-data/real_data_benchmark.py`
- widen into dashboard or viewer artifacts
- introduce new physics or pipeline behavior beyond the legacy synthetic harness

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `load-cell-data/real_data_benchmark.py`
