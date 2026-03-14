# Architecture Closeout Note

## Status

- recursive architecture refactoring is closed through slices `101-113`
- the architecture artifact spine under `docs/architecture/` is present and internally consistent
- the repository is in monitor mode, not in "open parity gap" mode

## What Changed

- completed the rerun-parity architecture wave for root `THORP`, `GOSM`, and `TDGM`
- reduced live rerun artifacts to the canonical Plotkit-style `python/legacy/diff` bundle contract under `out/rerun_parity/`
- added `docs/architecture/review/appendix-equation-coverage-audit-note.md` to record paper-appendix coverage across `THORP`, `GOSM`, and `TDGM`
- slice `109` identified and fixed the first proven `TDGM` long-horizon control-drift seam in `tdgm.thorp_g.hydraulics.stomata()` and locked it with a bounded `max_steps=2050` regression
- the former post-day-`791.5` `TDGM` reopening is now closed as reference-payload provenance:
  - closeout note: `docs/architecture/review/tdgm-reference-payload-resume-provenance-note.md`
  - continuous Python rerun remains exact through day `784.5`
  - the shipped later-horizon payload is explained by a one-off MATLAB resume from the last weekly checkpoint after the day-`787` file save

## Verification

- `.\.venv\Scripts\python.exe -m pytest -q`
  - last recorded result: `420 passed, 1 skipped`
- `.\.venv\Scripts\ruff.exe check .`
  - last recorded result: pass
- targeted appendix-coverage guard:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_gosm_steady_state_inversion.py tests/test_tdgm_coupling.py tests/test_thorp_equation_registry.py -q`
  - result: `9 passed`

## Open Gap

- none

## Next Action

- keep the rerun parity and provenance guards green when `tdgm.thorp_g` kernels change
- open a new bounded issue only if a future change breaks either the continuous exact window through day `784.5` or the shipped-payload provenance replay
