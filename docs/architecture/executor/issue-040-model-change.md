## Why
- `slice 039` landed the TOMATO THORP reference adapter, so the next bounded TOMATO `tTHORP` seam is the repo-level simulation plotting script at `scripts/plot_simulation_png.py`.
- The migrated repo still lacks the CLI wrapper that reads simulation CSV outputs, subsamples rows, and renders the legacy four-panel PNG summary for canopy, biomass, flux, and allocation diagnostics.
- This plotting seam should remain a repo-level utility with an optional `matplotlib` dependency instead of widening the package runtime surface.

## Affected model
- `TOMATO tTHORP`
- `scripts/plot_simulation_png.py`
- related TOMATO plotting tests and architecture docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for CLI argument parsing, CSV subsampling, optional plotting dependency behavior, and deterministic output-path printing

## Comparison target
- legacy `TOMATO/tTHORP/scripts/plot_simulation_png.py`
- current migrated TOMATO repo-level scripts and architecture slice records
