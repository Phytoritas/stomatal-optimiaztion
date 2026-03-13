## Why
- `slice 055` opened the bounded `load-cell-data` sweep seam, so the next staged helper surface is the end-to-end runner at `loadcell_pipeline/run_all.py`.
- The migrated repo now has workflow and sweep orchestration, but it still lacks the top-level entrypoint that decides whether to preprocess raw ALMEMO files, run workflow, or run sweep from one command.
- This slice should stay runner-bounded: parser construction, preprocess dispatch, workflow-or-sweep branching, and lazy missing-preprocessor error handling only.

## Affected model
- `load-cell-data`
- `src/stomatal_optimiaztion/domains/load_cell/`
- related load-cell run-all tests and package exports

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for preprocess dispatch, skip-preprocess mode, workflow vs sweep branching, parser wiring, and missing-preprocessor failure path

## Comparison target
- legacy `load-cell-data/loadcell_pipeline/run_all.py`
- current migrated `src/stomatal_optimiaztion/domains/load_cell/{workflow.py,sweep.py}`
