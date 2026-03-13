# Module Spec 062: load-cell-data Static Preprocess-Compare Viewer

## Purpose

Close the last bounded `load-cell-data/src` seam by porting the static preprocess-compare viewer builder that materializes viewer assets and per-day JSON payloads.

## Source Inputs

- `load-cell-data/src/build_preprocess_compare_viewer.py`

## Target Outputs

- `scripts/build_preprocess_compare_viewer.py`
- `tests/test_load_cell_build_preprocess_compare_viewer_script.py`

## Responsibilities

1. preserve canonical day discovery, explicit/ranged date selection, and latest-N day limiting
2. preserve transpiration parquet lookup plus canonical-derived 1-minute fallback and integer-packed JSON payloads
3. preserve repo-level static asset writing and `dates.json` refresh behavior without widening into a new frontend stack

## Non-Goals

- redesign the viewer HTML, CSS, or JS bundle
- widen the compare tooling into a package-level web application
- choose and migrate the next non-`load-cell-data` seam in the same slice

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- post-`load-cell-data` workspace re-audit for the next bounded seam selection
