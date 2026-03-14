# Module 110: TDGM Post-791d Control Drift Investigation

## Goal

Reduce the remaining open `D-108` gap to the next bounded diagnosis slice by identifying which runtime seam causes the canonical root `TDGM` control rerun to reopen against the legacy MATLAB payload after day `791.5`, after slice `109` already fixed the first proven seam near day `497.5`.

## Inputs

- module `109` drift diagnosis note:
  - `docs/architecture/review/tdgm-full-series-control-drift-diagnosis-note.md`
- open gap `D-108` in `docs/architecture/gap_register.md`
- current rerun evidence under:
  - `out/rerun_parity/tdgm/thorp_data_control_turgor/`
- current root `TDGM` runtime seams under:
  - `src/stomatal_optimiaztion/domains/tdgm/`
  - `src/stomatal_optimiaztion/domains/tdgm/thorp_g/`

## Target Artifacts

- update `docs/architecture/review/python-rerun-parity-audit-note.md`
- update `docs/architecture/review/tdgm-full-series-control-drift-diagnosis-note.md`
- if the next culprit is proven, add one more bounded follow-up review note or module spec rather than opening a broad numerical rewrite

## Responsibilities

1. identify the first stored timestep or horizon segment where the remaining root `TDGM` control rerun drift reopens after day `791.5`
2. classify the most likely source seam into one of:
   - growth-state carryover
   - mean allocation updates
   - TDGM coupling state
   - another bounded long-horizon kernel mismatch
3. keep the slice bounded to one next proven seam rather than diffusing into a broad long-horizon cleanup wave

## Non-Goals

- do not reopen the already-fixed pre-day-`497.5` stomatal-index seam
- do not broaden the slice into unrelated `THORP` or `GOSM` runtime work
- do not declare the root `TDGM` parity wave closed without new full-series evidence

## Validation

1. `.\.venv\Scripts\python.exe -m pytest tests/test_tdgm_thorp_g_rerun_parity.py tests/test_root_rerun_parity_figures.py -q`
2. `.\.venv\Scripts\python.exe scripts\render_root_rerun_parity_figures.py --output-dir out/rerun_parity --domains tdgm`
3. compare:
   - `*_python.csv`
   - `*_legacy.csv`
   - `*_diff.csv`
4. `.\.venv\Scripts\python.exe -m pytest -q`
5. `.\.venv\Scripts\ruff.exe check .`

## Exit Criteria

- the first post-day-`791.5` divergence point in the full-series root `TDGM` control rerun is documented
- the most likely next bounded source seam is named explicitly
- the next architecture step remains one focused implementation slice, not a broad exploratory rewrite
