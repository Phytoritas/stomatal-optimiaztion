## Why
- `slice 052` opened the bounded `load-cell-data` flux-decomposition seam, so the next staged helper surface is the package-level pipeline CLI at `loadcell_pipeline/cli.py`.
- The migrated repo now has config, IO, aggregation, thresholds, preprocessing, events, and flux helpers, but it still lacks the canonical parser, override mapping, and pipeline orchestration surface that ties those seams together.
- This slice should stay CLI-bounded: parser construction, CLI override mapping, pipeline execution, summary stats, and entrypoint behavior only.

## Affected model
- `load-cell-data`
- `src/stomatal_optimiaztion/domains/load_cell/`
- related load-cell CLI tests and package exports

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for parser overrides, input/output validation, pipeline orchestration, summary stats, and CLI entrypoint wiring

## Comparison target
- legacy `load-cell-data/loadcell_pipeline/cli.py`
- current migrated `src/stomatal_optimiaztion/domains/load_cell/fluxes.py`
