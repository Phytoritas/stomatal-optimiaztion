# Architecture Closeout Note

## Status

- recursive architecture refactoring is closed through slices `101-108`
- the architecture artifact spine under `docs/architecture/` is present and internally consistent
- the repository is ready for the next bounded implementation slice, not for a blanket "all drift is solved" claim

## What Changed

- completed the rerun-parity architecture wave for root `THORP`, `GOSM`, and `TDGM`
- reduced live rerun artifacts to the canonical Plotkit-style `python/legacy/diff` bundle contract under `out/rerun_parity/`
- added `docs/architecture/review/appendix-equation-coverage-audit-note.md` to record paper-appendix coverage across `THORP`, `GOSM`, and `TDGM`
- slice `109` identified and fixed the first proven `TDGM` long-horizon control-drift seam in `tdgm.thorp_g.hydraulics.stomata()` and locked it with a bounded `max_steps=2050` regression
- the remaining `TDGM` long-horizon drift is now narrowed to a later post-day-`791.5` follow-up slice:
  - diagnosis note: `docs/architecture/review/tdgm-full-series-control-drift-diagnosis-note.md`
  - module `110` diagnosis note: `docs/architecture/review/tdgm-post-791d-stomata-sensitivity-diagnosis-note.md`
  - module `111` diagnosis note: `docs/architecture/review/tdgm-root-sensitivity-zero-point-diagnosis-note.md`
  - next module spec: `docs/architecture/architecture/module_specs/module-112-tdgm-root-sensitivity-zero-point-derivative-branch.md`
  - next executor packet: `docs/architecture/executor/issue-222-bug-tdgm-root-sensitivity-zero-point-derivative-branch.md`
  - GitHub tracking: issue `#222` should be the next `Ready` bounded bug slice

## Verification

- `.\.venv\Scripts\python.exe -m pytest -q`
  - last recorded result: `419 passed, 1 skipped`
- `.\.venv\Scripts\ruff.exe check .`
  - last recorded result: pass
- targeted appendix-coverage guard:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_gosm_steady_state_inversion.py tests/test_tdgm_coupling.py tests/test_thorp_equation_registry.py -q`
  - result: `9 passed`

## Open Gap

- `D-108`: root `TDGM` canonical full-series control rerun still reopens against the legacy MATLAB payload after day `791.5`; module `111` narrows the next likely culprit to the root-specific zero-point derivative branch inside the `THORP-G` sensitivity path
- this gap is not treated as a scaffold failure; it is a bounded numerical diagnosis slice queued for the next implementation wave

## Next Action

- start from module `112` / issue `#222`
- audit the root-specific zero-point derivative terms inside the `THORP-G` sensitivity path
- keep the next slice bounded to one fix or one tighter culprit
