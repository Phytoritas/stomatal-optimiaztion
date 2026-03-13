## Why
- `slice 040` landed the TOMATO simulation plotting script, so the next bounded TOMATO `tTHORP` seam is the allocation-comparison plotting script at `scripts/plot_allocation_compare_png.py`.
- The migrated repo still lacks the CLI utility that compares baseline and candidate simulation CSV outputs, aligns them on `datetime`, and renders the legacy four-panel allocation-fraction comparison PNG.
- This seam should remain repo-level tooling with an optional `matplotlib` dependency instead of widening the package runtime surface.

## Affected model
- `TOMATO tTHORP`
- `scripts/plot_allocation_compare_png.py`
- related TOMATO plotting tests and architecture docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for CLI parsing, allocation-column ingestion, overlap filtering, subsampling, and optional plotting dependency behavior

## Comparison target
- legacy `TOMATO/tTHORP/scripts/plot_allocation_compare_png.py`
- current migrated TOMATO repo-level plotting utilities and architecture slice records
