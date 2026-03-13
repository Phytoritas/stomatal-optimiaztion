# Module Spec 061: load-cell-data Preprocess-Compare Local Server

## Purpose

Open the next bounded `load-cell-data` seam by porting the repo-level preprocess-compare local server that serves static viewer assets and exposes export plus preprocess APIs.

## Source Inputs

- `load-cell-data/src/preprocess_compare_server.py`

## Target Outputs

- `scripts/preprocess_compare_server.py`
- `tests/test_load_cell_preprocess_compare_server_script.py`

## Responsibilities

1. preserve local health, export, preprocess, and cancel API behavior
2. preserve transpiration export computation across `diff_1s`, `ma_diff_1s`, `reg_1s`, and `diff60_1m`
3. keep the seam repo-level and server-bounded without widening into static viewer generation

## Non-Goals

- migrate `load-cell-data/src/build_preprocess_compare_viewer.py`
- redesign the viewer HTML, CSS, or JS bundle
- widen the server into a package-level web framework

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `load-cell-data/src/build_preprocess_compare_viewer.py`
