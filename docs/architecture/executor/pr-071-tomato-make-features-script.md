## Background
- `slice 037` landed the TOMATO repo-level pipeline runner, but the migrated repo still lacked the deterministic feature-builder script used to prepare forcing CSVs for downstream runs.
- This PR lands `slice 038` by migrating `scripts/make_features.py` plus the direct `core.util_units` dependency, and moves the next TOMATO architectural uncertainty to the THORP reference adapter seam at `models/thorp_ref/adapter.py`.

## Changes
- add the migrated repo-local `scripts/make_features.py` feature-builder over the already ported TOMATO package seams
- add the shared `core.util_units` PAR conversion helper and expose it through the `core` surface
- add subprocess-based script tests and direct unit-conversion tests
- update architecture artifacts and README so `slice 038` is recorded and `models/thorp_ref/adapter.py` becomes the next blocked seam

## Validation
- `poetry run pytest`
- `poetry run ruff check .`

## Impact
- the migrated workspace now has a repo-level feature-builder script and shared PAR conversion helpers for TOMATO forcing preparation
- THORP reference bridging and remaining plotting scripts stay explicitly blocked and documented for the next slice

## Linked issue
Closes #71
