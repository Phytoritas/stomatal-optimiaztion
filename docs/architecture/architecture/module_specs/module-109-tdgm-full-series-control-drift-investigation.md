# Module 109: TDGM Full-Series Control Drift Investigation

## Goal

Turn the open `D-108` gap into a bounded diagnosis slice by identifying where the canonical root `TDGM` full-series control rerun first diverges from the legacy MATLAB payload and which runtime seam most likely introduces that drift.

## Inputs

- module 108 full-series rerender audit
- open gap `D-108` in `docs/architecture/gap_register.md`
- current rerun evidence under:
  - `out/rerun_parity/tdgm/thorp_data_control_turgor/`
- current root `TDGM` runtime seams under:
  - `src/stomatal_optimiaztion/domains/tdgm/`
  - `src/stomatal_optimiaztion/domains/tdgm/thorp_g/`

## Target Artifacts

- `docs/architecture/review/python-rerun-parity-audit-note.md`
- `docs/architecture/review/appendix-equation-coverage-audit-note.md` only if appendix interpretation changes
- one new bounded drift-diagnosis note under `docs/architecture/review/`
- if needed, one follow-up module spec for the first proven kernel mismatch

## Responsibilities

1. identify the first stored timestep or horizon segment where the canonical root `TDGM` control rerun begins to drift from the legacy MATLAB payload
2. classify the likely source of the drift into one of:
   - growth-state carryover
   - mean allocation updates
   - THORP-G coupling state
   - another bounded long-horizon kernel mismatch
3. keep the slice diagnosis-bounded rather than opening a broad numerical refactor before the first failing seam is explicit

## Non-Goals

- do not declare the root `TDGM` parity wave closed without new full-series evidence
- do not broaden the slice into unrelated `THORP` or `GOSM` runtime changes
- do not rewrite the rerun bundle contract under `out/rerun_parity/`

## Validation

1. `.\.venv\Scripts\python.exe -m pytest tests/test_tdgm_thorp_g_rerun_parity.py tests/test_root_rerun_parity_figures.py -q`
2. `.\.venv\Scripts\python.exe scripts\render_root_rerun_parity_figures.py --output-dir out/rerun_parity --domains tdgm`
3. compare:
   - `*_python.csv`
   - `*_legacy.csv`
   - `*_diff.csv`
4. `.\.venv\Scripts\python.exe -m pytest`
5. `.\.venv\Scripts\ruff.exe check .`

## Exit Criteria

- the first clear divergence point in the full-series root `TDGM` control rerun is documented
- the most likely bounded source seam is named explicitly
- the next architecture step is one focused implementation slice, not a broad exploratory rewrite
