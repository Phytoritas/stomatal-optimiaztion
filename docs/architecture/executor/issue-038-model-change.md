## Why
- `slice 037` landed the TOMATO repo-level pipeline runner, so the next bounded repo-level seam is the deterministic forcing feature builder at `scripts/make_features.py`.
- The migrated repo still lacks the CLI-style wrapper that loads YAML configs, resolves forcing CSV paths, injects derived `PAR_umol` and default forcing columns, and writes a deterministic feature CSV for downstream runs.
- This seam depends on the shared PAR conversion helper from `core.util_units`, so that helper should land as a direct supporting dependency instead of duplicating conversion logic again.

## Affected model
- `TOMATO tTHORP`
- `scripts/make_features.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/core/`
- related TOMATO feature-building tests

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for deterministic feature output paths, SW-to-PAR derivation, forcing defaults, and direct unit-conversion helper behavior

## Comparison target
- legacy `TOMATO/tTHORP/scripts/make_features.py`
- legacy `TOMATO/tTHORP/src/tthorp/core/util_units.py`
- current migrated TOMATO `core`, `forcing_csv`, and repo-level pipeline runner seams
