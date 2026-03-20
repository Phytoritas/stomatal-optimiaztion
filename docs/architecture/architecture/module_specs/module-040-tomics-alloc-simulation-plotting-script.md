# Module Spec 040: TOMATO tTHORP Simulation Plotting Script

## Purpose

Open the next bounded TOMATO `tTHORP` seam by porting the repo-level plotting script that renders simulation CSV outputs into a four-panel PNG summary.

## Source Inputs

- `TOMATO/tTHORP/scripts/plot_simulation_png.py`

## Target Outputs

- `scripts/plot_simulation_png.py`
- `tests/test_tomics_alloc_plot_simulation_png_script.py`

## Responsibilities

1. preserve CLI parsing for input path, output path, row stride, and DPI
2. preserve CSV subsampling and the four-panel simulation-summary plotting layout
3. keep matplotlib optional and fail with a clear error when the plotting dependency is unavailable

## Non-Goals

- migrate `TOMATO/tTHORP/scripts/plot_allocation_compare_png.py`
- introduce a shared plotting package or repo-wide visualization layer
- widen the migrated core package runtime dependency surface

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TOMATO/tTHORP/scripts/plot_allocation_compare_png.py`
