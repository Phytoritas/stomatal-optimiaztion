## Background
- `slice 036` landed the TOMATO dayrun pipeline seam, but the migrated repo still lacked the repo-level runner script that shells and automation can call directly.
- This PR lands `slice 037` by migrating `scripts/run_pipeline.py`, and moves the next TOMATO architectural uncertainty to the feature-builder script seam at `scripts/make_features.py`.

## Changes
- add the migrated repo-local `scripts/run_pipeline.py` runner over the already ported TOMATO package seams
- preserve CLI arguments for config path, output-dir override, and explicit experiment-key override
- add subprocess-based tests for printed JSON summaries and deterministic artifact outputs
- update architecture artifacts and README so `slice 037` is recorded and `scripts/make_features.py` becomes the next blocked seam

## Validation
- `poetry run pytest`
- `poetry run ruff check .`

## Impact
- the migrated workspace now has a repo-level pipeline runner script over the TOMATO package seams
- feature-building and remaining repo-level entrypoints stay explicitly blocked and documented for the next slice

## Linked issue
Closes #69
