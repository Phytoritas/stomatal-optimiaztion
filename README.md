# stomatal-optimiaztion

## Purpose
- Refactor the legacy `00. Stomatal Optimization` workspace into a scaffold-aligned Python repository.
- Keep architecture decisions, validation seams, and staged code migration explicit before broad implementation.

## Inputs
- Legacy source domains from `THORP`, `TOMATO`, and `load-cell-data`
- Canonical variable names in [`docs/variable_glossary.md`](docs/variable_glossary.md)
- Curated THORP `model_card` JSON assets for equation traceability

## Outputs
- Architecture artifacts under `docs/architecture/`
- Domain packages under `src/stomatal_optimiaztion/`
- Validation artifacts from `pytest` and `ruff`

## How to run
```bash
poetry install
poetry run pytest
poetry run ruff check .
```

## Current status
- Gates A through C are satisfied for the first bounded migration slice.
- THORP `model_card` and traceability helpers are migrated into the new package layout.
- THORP `radiation` runtime seam is migrated as slice 002.
- THORP `WeibullVC` runtime primitive is migrated as slice 003.
- THORP `SoilHydraulics` is migrated as slice 004.
- THORP `initial_soil_and_roots` is migrated as slice 005.
- THORP `richards_equation` is migrated as slice 006.
- THORP `soil_moisture` is migrated as slice 007.
- THORP `e_from_soil_to_root_collar` is migrated as slice 008.
- THORP `stomata` is migrated as slice 009.
- THORP `allocation_fractions` is migrated as slice 010.
- THORP `grow` is migrated as slice 011.
- THORP `biomass_fractions` is migrated as slice 012.
- THORP `huber_value` is migrated as slice 013.
- THORP `rooting_depth` is migrated as slice 014.
- THORP `soil_grid` helper is migrated as slice 015.
- THORP `default_params` is migrated as a bounded defaults bundle in slice 016.
- THORP `THORPParams` compatibility seam is migrated as slice 017.

## Next validation
- Migrate the next THORP seam, likely `load_forcing`, with behavior-preserving regression checks.
