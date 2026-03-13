# Module Spec 059: load-cell-data Real-Data Benchmark Harness

## Purpose

Open the next bounded `load-cell-data` seam by porting the repo-level real-data benchmark harness that compares interpolated and raw daily CSV runs across dates and loadcells.

## Source Inputs

- `load-cell-data/real_data_benchmark.py`

## Target Outputs

- `scripts/real_data_benchmark.py`
- `tests/test_load_cell_real_data_benchmark_script.py`

## Responsibilities

1. preserve batch orchestration across matched interpolated and raw daily CSV files
2. preserve summary, comparison, overlap-window comparison, and failure CSV outputs
3. keep the seam repo-level and benchmark-bounded without widening into preprocess-compare viewer tooling

## Non-Goals

- migrate `load-cell-data/src/preprocess_incremental.py`
- migrate `load-cell-data/src/preprocess_compare_server.py`
- migrate `load-cell-data/src/build_preprocess_compare_viewer.py`

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `load-cell-data/src/preprocess_incremental.py`
