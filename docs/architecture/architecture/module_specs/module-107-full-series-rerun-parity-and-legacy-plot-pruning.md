# Module 107: Full-Series Rerun Parity And Legacy Plot Pruning

## Goal

Keep only live `Python rerun vs MATLAB reference` comparison artifacts in the repository and upgrade the dynamic root-domain graph exports to compare the full legacy stored series for the canonical control cases.

## Inputs

- root rerun parity slices `101-106`
- legacy MATLAB payloads under:
  - `THORP/example/THORP_code_forcing_outputs_plotting/Simulations_and_additional_code_to_plot/`
  - `GOSM/example/`
  - `TDGM/example/Supplementary Code __THORP_code_v1.4/Simulations_and_code_to_plot/`

## Changed Artifacts

- `src/stomatal_optimiaztion/shared_plotkit.py`
- `src/stomatal_optimiaztion/domains/thorp/examples/rerun_parity.py`
- `src/stomatal_optimiaztion/domains/gosm/examples/rerun_parity.py`
- `src/stomatal_optimiaztion/domains/tdgm/examples/rerun_parity.py`
- `src/stomatal_optimiaztion/domains/thorp/examples/__init__.py`
- `src/stomatal_optimiaztion/domains/gosm/examples/__init__.py`
- `src/stomatal_optimiaztion/domains/tdgm/examples/__init__.py`
- `scripts/render_root_rerun_parity_figures.py`
- `tests/test_root_rerun_parity_figures.py`
- `README.md`
- `docs/architecture/Phytoritas.md`
- `docs/architecture/01_system_brief.md`
- `docs/architecture/review/python-rerun-parity-audit-note.md`

Removed from the live repository surface:
- legacy-only example plotting scripts
- their tests
- their dedicated Plotkit specs
- obsolete review notes tied only to those plotting workflows

## Decisions

1. `out/rerun_parity/` is now the only supported root-domain graph inspection surface.
2. Bundle exports are reduced to:
   - `png`
   - `*_python.csv`
   - `*_legacy.csv`
   - `*_diff.csv`
3. Root `THORP` and root `TDGM` default graph exports target the full legacy stored series for the canonical control case.
4. Root `GOSM` remains a full response-domain comparison rather than a time-series comparison because the legacy MATLAB references are control/sensitivity surfaces.
5. Fast bounded rendering remains available behind `scripts/render_root_rerun_parity_figures.py --fast-smoke`.

## Validation

1. `.\.venv\Scripts\python.exe -m pytest tests/test_root_rerun_parity_figures.py`
2. `.\.venv\Scripts\ruff.exe check .`
3. `.\.venv\Scripts\python.exe scripts/render_root_rerun_parity_figures.py --output-dir out/rerun_parity --fast-smoke`
4. default full rerender for canonical control cases under `out/rerun_parity/`

## Exit Criteria

- no legacy-only example plotting entrypoint remains in the live repository surface
- root rerun bundles write only rerun comparison outputs
- canonical control comparisons for dynamic root domains are exported over the full stored series
