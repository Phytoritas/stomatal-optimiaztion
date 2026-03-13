# Module Spec 041: TOMATO tTHORP Allocation-Comparison Plotting Script

## Purpose

Open the next bounded TOMATO `tTHORP` seam by porting the repo-level plotting script that compares allocation-fraction time series between baseline and candidate simulation CSV outputs.

## Source Inputs

- `TOMATO/tTHORP/scripts/plot_allocation_compare_png.py`

## Target Outputs

- `scripts/plot_allocation_compare_png.py`
- `tests/test_tomato_tthorp_plot_allocation_compare_png_script.py`

## Responsibilities

1. preserve CLI parsing for baseline/candidate paths, legend labels, output path, row stride, and DPI
2. preserve allocation-column ingestion, datetime alignment, overlap filtering, subsampling, and four-panel comparison plotting behavior
3. keep matplotlib optional and fail with a clear error when the plotting dependency is unavailable

## Non-Goals

- migrate `TOMATO/tGOSM/src/tgosm/contracts.py`
- introduce a shared plotting package or repo-wide visualization layer
- widen the migrated core package runtime dependency surface

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TOMATO/tGOSM/src/tgosm/contracts.py`
