# stomatal-optimiaztion

## Purpose
- Refactor the legacy `00. Stomatal Optimization` workspace into a scaffold-aligned Python repository.
- Keep architecture decisions, validation seams, and staged code migration explicit before broad implementation.

## Inputs
- Legacy source domains from `THORP`, `GOSM`, `TDGM`, `TOMATO`, and `load-cell-data`
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
poetry run python scripts/render_thorp_example_figures.py --legacy-example-dir "../00. Stomatal Optimization/THORP/example/THORP_code_forcing_outputs_plotting"
poetry run python scripts/render_gosm_control_example.py --output-dir out/gosm/control_example
poetry run python scripts/render_gosm_sensitivity_figures.py --legacy-example-dir "../00. Stomatal Optimization/GOSM/example"
poetry run python scripts/render_gosm_manuscript_panels.py --output-dir out/gosm/manuscript_panels
poetry run python scripts/render_tdgm_example_figures.py --output-dir out/tdgm/example_figures
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
- `load-cell-data` workflow seam is migrated as slice 054.
- `load-cell-data` sweep seam is migrated as slice 055.
- `load-cell-data` end-to-end runner seam is migrated as slice 056.
- `load-cell-data` raw ALMEMO preprocessing seam is migrated as slice 057.
- `load-cell-data` synthetic validation harness seam is migrated as slice 058.
- `load-cell-data` real-data benchmark harness seam is migrated as slice 059.
- `load-cell-data` incremental preprocess harness seam is migrated as slice 060.
- `load-cell-data` preprocess-compare local server seam is migrated as slice 061.
- `load-cell-data` static preprocess-compare viewer seam is migrated as slice 062.
- THORP stable `sim` runner seam is migrated as slice 063.
- THORP equation-registry seam is migrated as slice 064.
- THORP utilities namespace seam is migrated as slice 065.
- THORP IO namespace seam is migrated as slice 066.
- THORP model namespace seam is migrated as slice 067.
- THORP params compatibility seam is migrated as slice 068.
- THORP package-level smoke validation note is recorded as slice 069.
- Second-domain utility comparison note is recorded as slice 070.
- Root GOSM model-card and traceability foundation is migrated as slice 071.
- Root TDGM model-card and traceability foundation is migrated as slice 072.
- Root GOSM parameter-defaults seam is migrated as slice 073.
- Root GOSM radiation kernel seam is migrated as slice 074.
- Root GOSM allometry helper seam is migrated as slice 075.
- Root GOSM NPP/GPP helper seam is migrated as slice 076.
- Root GOSM optimal-control helper seam is migrated as slice 077.
- Root GOSM carbon-dynamics helper seam is migrated as slice 078.
- Root GOSM conductance-temperature kernel is migrated as slice 079.
- Root GOSM carbon-assimilation kernel is migrated as slice 080.
- Root GOSM math helper seam is migrated as slice 081.
- Root GOSM hydraulics kernel is migrated as slice 082.
- Root GOSM runtime pipeline seam is migrated as slice 083.
- Root GOSM future-work helper seam is migrated as slice 084.
- Root GOSM stomatal-model comparison seam is migrated as slice 085.
- Root GOSM instantaneous optimum seam is migrated as slice 086.
- Root GOSM steady-state helper seam is migrated as slice 087.
- Root TDGM turgor-driven growth seam is migrated as slice 088.
- Root TDGM phloem-transport seam is migrated as slice 089.
- Root TDGM coupling seam is migrated as slice 090.
- Root TDGM equation-registry seam is migrated as slice 091.
- Root TDGM THORP-G postprocess seam is migrated as slice 092.
- MATLAB source parity audit is recorded as slice 093 and reopens only the bounded gaps that remain against the original THORP, GOSM, and TDGM `.m` source.
- Root GOSM steady-state inversion helper is migrated as slice 094.
- Root TDGM initial mean-allocation helper is migrated as slice 095.
- Legacy example and figure parity audit is recorded as slice 096 and reopens bounded workflow-reproduction gaps for root `GOSM`, `THORP`, and `TDGM`.
- Root GOSM control example figure workflow is migrated as slice 097.
- Root GOSM sensitivity and manuscript figure workflows are migrated as slice 098.
- Root THORP main-text example figure workflows are migrated as slice 099.
- Root TDGM supplementary offline and THORP-G example figure workflows are migrated as slice 100.
- Root THORP fast Python rerun parity is locked against `THORP_data_0.6RH.mat` in slice 101.
- Root GOSM legacy rerun helpers and fast MATLAB-output parity tests are restored in slice 102.
- Root TDGM `thorp_g` runtime surface and fast MATLAB-output parity tests are restored in slice 103.
- Root Python rerun parity audit is recorded in slice 104.

## Next validation
- Keep `pytest`, `ruff`, the fast root rerun parity tests, and the Plotkit example renderers green while the architecture remains in monitor mode.
- Run the opt-in slow `GOSM` `imag` conductance-loss parity branch when root `gosm` hydraulics or stomatal logic changes.
