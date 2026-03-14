# Architecture Closeout Note

## Status

- recursive architecture refactoring is closed through slices `101-108`
- the architecture artifact spine under `docs/architecture/` is present and internally consistent
- the repository is ready for the next bounded implementation slice, not for a blanket "all drift is solved" claim

## What Changed

- completed the rerun-parity architecture wave for root `THORP`, `GOSM`, and `TDGM`
- reduced live rerun artifacts to the canonical Plotkit-style `python/legacy/diff` bundle contract under `out/rerun_parity/`
- added `docs/architecture/review/appendix-equation-coverage-audit-note.md` to record paper-appendix coverage across `THORP`, `GOSM`, and `TDGM`
- converted the remaining `TDGM` long-horizon drift into a bounded follow-up slice:
  - module spec: `docs/architecture/architecture/module_specs/module-109-tdgm-full-series-control-drift-investigation.md`
  - executor packet: `docs/architecture/executor/issue-209-bug-tdgm-full-series-control-rerun-drift.md`
  - GitHub tracking: issue `#209` set to `Ready`

## Verification

- `.\.venv\Scripts\python.exe -m pytest -q`
  - last recorded result: `418 passed, 1 skipped`
- `.\.venv\Scripts\ruff.exe check .`
  - last recorded result: pass
- targeted appendix-coverage guard:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_gosm_steady_state_inversion.py tests/test_tdgm_coupling.py tests/test_thorp_equation_registry.py -q`
  - result: `9 passed`

## Open Gap

- `D-108`: root `TDGM` canonical full-series control rerun still drifts from the legacy MATLAB payload over the full stored horizon even though the fast bounded parity tests pass
- this gap is not treated as a scaffold failure; it is a bounded numerical diagnosis slice queued for the next implementation wave

## Next Action

- start from module `109` / issue `#209`
- identify the first divergence point in the full-series root `TDGM` control rerun
- narrow the cause to one runtime seam before changing numerical kernels broadly
