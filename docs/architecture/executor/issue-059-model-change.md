## Why
- `slice 058` migrated the synthetic validation harness seam, so the next remaining bounded `load-cell-data` surface is the repo-level real-data benchmark harness at `real_data_benchmark.py`.
- The migrated repo now has package-level pipeline coverage, but it still lacks the legacy batch comparison script that benchmarks interpolated versus raw daily CSV outputs across dates and loadcells.
- This slice should stay benchmark-harness-bounded: batch run orchestration, summary/comparison CSV emission, overlap-window diffs, failure capture, and repo-level CLI wiring only.

## Affected model
- `load-cell-data`
- `scripts/`
- related load-cell real-data benchmark tests and architecture docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for no-common-file failure, batch summary output, overlap comparison output, failure capture, and CLI argument dispatch

## Comparison target
- legacy `load-cell-data/real_data_benchmark.py`
- current migrated `src/stomatal_optimiaztion/domains/load_cell/{cli.py,config.py,workflow.py}`
