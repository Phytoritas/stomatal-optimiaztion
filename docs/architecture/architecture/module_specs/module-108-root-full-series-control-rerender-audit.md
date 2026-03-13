# Module 108: Root Full-Series Control Rerender Audit

## Goal

Regenerate the live root-domain rerun comparison bundles from actual Python reruns over the full stored control horizon and record the resulting parity status for `THORP`, `GOSM`, and `TDGM`.

## Inputs

- module 107 rerun-only bundle contract
- root rerun parity renderers under:
  - `src/stomatal_optimiaztion/domains/thorp/examples/rerun_parity.py`
  - `src/stomatal_optimiaztion/domains/gosm/examples/rerun_parity.py`
  - `src/stomatal_optimiaztion/domains/tdgm/examples/rerun_parity.py`
- canonical legacy payloads:
  - `THORP_data_0.6RH.mat`
  - root `GOSM` control and sensitivity `.mat` files
  - `THORP_data_Control_Turgor.mat`

## Changed Artifacts

- `src/stomatal_optimiaztion/domains/thorp/hydraulics.py`
- `src/stomatal_optimiaztion/domains/tdgm/thorp_g/hydraulics.py`
- `README.md`
- `docs/architecture/Phytoritas.md`
- `docs/architecture/01_system_brief.md`
- `docs/architecture/gap_register.md`
- `docs/architecture/review/python-rerun-parity-audit-note.md`

## Decisions

1. Full-series rerendering is retained only for the canonical control cases of root `THORP` and root `TDGM`; root `GOSM` remains a response-domain rerun comparison because its legacy payloads are curve families rather than stored temporal traces.
2. The shared THORP/THORP-G root-uptake bottleneck is vectorized so the canonical full-series control rerenders complete in practical workstation time.
3. The rerun-only bundle contract remains:
   - `png`
   - `*_python.csv`
   - `*_legacy.csv`
   - `*_diff.csv`
4. A newly observed long-horizon root `TDGM` control drift is treated as an open bounded architecture gap rather than silently folded into the “closed parity” claim.

## Validation

1. `.\.venv\Scripts\python.exe -m pytest tests/test_thorp_rerun_parity.py tests/test_tdgm_thorp_g_rerun_parity.py tests/test_root_rerun_parity_figures.py -q`
2. `.\.venv\Scripts\python.exe scripts/render_root_rerun_parity_figures.py --output-dir out/rerun_parity --domains gosm`
3. `.\.venv\Scripts\python.exe scripts/render_root_rerun_parity_figures.py --output-dir out/rerun_parity --domains thorp`
4. `.\.venv\Scripts\python.exe scripts/render_root_rerun_parity_figures.py --output-dir out/rerun_parity --domains tdgm`
5. `.\.venv\Scripts\python.exe -m pytest`
6. `.\.venv\Scripts\ruff.exe check .`

## Exit Criteria

- `out/rerun_parity/` contains only live rerun comparison bundles
- root `THORP` full-series control rerun is regenerated from Python and compared directly against the legacy MATLAB payload
- root `GOSM` rerun bundles are regenerated under the rerun-only contract
- root `TDGM` full-series control rerun is regenerated from Python and its remaining drift is explicitly documented as an open gap
