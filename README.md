# stomatal-optimiaztion

## Purpose
- Refactor the legacy `00. Stomatal Optimization` workspace into a scaffold-aligned Python repository.
- Keep architecture decisions, validation seams, and staged code migration explicit before broad implementation.

## Inputs
- Legacy source domains from `THORP`, `TOMATO`, and `load-cell-data`
- Canonical variable names in [`docs/variable_glossary.md`](docs/variable_glossary.md)
- Curated THORP `model_card` JSON assets for equation traceability
- Representative THORP forcing netCDF under `data/forcing/`

## Outputs
- Architecture artifacts under `docs/architecture/`
- Domain packages under `src/stomatal_optimiaztion/`
- Validation artifacts from `pytest` and `ruff`

## How to run
```bash
poetry install
poetry run python -m stomatal_optimiaztion.domains.thorp --max-steps 60
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
- THORP `load_forcing` seam is migrated as slice 018.
- THORP `SimulationOutputs` seam is migrated as slice 019.
- THORP `_Store` seam is migrated as slice 020.
- THORP `_initial_allometry` seam is migrated as slice 021.
- THORP `run` seam is migrated as slice 022.
- THORP `matlab_io` seam is migrated as slice 023.
- THORP CLI entrypoint seam is migrated as slice 024.
- TOMATO `tTHORP` contracts seam is migrated as slice 025.
- TOMATO `tTHORP` interface seam is migrated as slice 026.
- TOMATO `tTHORP` forcing CSV seam is migrated as slice 027.
- TOMATO `tTHORP` adapter seam is migrated as slice 028.
- TOMATO `tTHORP` `TomatoModel` surface seam is migrated as slice 029.
- TOMATO `tTHORP` runner seam is migrated as slice 030.
- TOMATO `tTHORP` partitioning core seam is migrated as slice 031.
- TOMATO `tTHORP` THORP-derived partition-policy seam is migrated as slice 032.
- TOMATO `tTHORP` package-level legacy pipeline seam is migrated as slice 033.
- TOMATO `tTHORP` shared IO seam is migrated as slice 034.
- TOMATO `tTHORP` shared scheduler seam is migrated as slice 035.
- TOMATO `tTHORP` dayrun pipeline seam is migrated as slice 036.
- TOMATO `tTHORP` repo-level pipeline script seam is migrated as slice 037.
- TOMATO `tTHORP` feature-builder script seam is migrated as slice 038.
- TOMATO `tTHORP` THORP reference adapter seam is migrated as slice 039.
- TOMATO `tTHORP` simulation plotting script seam is migrated as slice 040.
- TOMATO `tTHORP` allocation-comparison plotting script seam is migrated as slice 041.
- TOMATO `tGOSM` contracts seam is migrated as slice 042.
- TOMATO `tGOSM` interface seam is migrated as slice 043.
- TOMATO `tTDGM` contracts seam is migrated as slice 044.
- TOMATO `tTDGM` interface seam is migrated as slice 045.
- `load-cell-data` config seam is migrated as slice 046.
- `load-cell-data` IO seam is migrated as slice 047.
- `load-cell-data` aggregation seam is migrated as slice 048.
- `load-cell-data` threshold-detection seam is migrated as slice 049.
- `load-cell-data` preprocessing seam is migrated as slice 050.
- `load-cell-data` event-detection seam is migrated as slice 051.
- `load-cell-data` flux-decomposition seam is migrated as slice 052.
- `load-cell-data` pipeline CLI seam is migrated as slice 053.

## Next validation
- Audit the `load-cell-data` workflow seam at `loadcell_pipeline/workflow.py`.
