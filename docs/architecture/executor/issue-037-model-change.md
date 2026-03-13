## Why
- `slice 036` landed the TOMATO dayrun pipeline seam, so the next bounded orchestration surface is the repo-level script entrypoint at `scripts/run_pipeline.py`.
- The migrated repo still lacks the CLI-style wrapper that loads YAML configs, resolves default output directories, emits deterministic result artifacts, and prints a stable JSON summary for automation.

## Affected model
- `TOMATO tTHORP`
- `scripts/run_pipeline.py`
- related TOMATO CLI-style pipeline smoke tests

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for config-path execution, output-dir overrides, exp-key overrides, and printed JSON summaries

## Comparison target
- legacy `TOMATO/tTHORP/scripts/run_pipeline.py`
- current migrated TOMATO `core`, `tomato_legacy`, and `tomato_dayrun` seams
