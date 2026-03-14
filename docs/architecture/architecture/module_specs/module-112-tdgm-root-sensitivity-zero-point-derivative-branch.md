# Module 112: TDGM Root Sensitivity Zero-Point Derivative Branch

## Goal

Reduce the remaining open `D-108` gap to the next bounded implementation slice by checking whether the post-day-`791.5` root `TDGM` drift is caused by the root-specific zero-point sensitivity derivatives inside `tdgm.thorp_g.hydraulics.stomata()`.

## Inputs

- module `111` diagnosis note:
  - `docs/architecture/review/tdgm-root-sensitivity-zero-point-diagnosis-note.md`
- open gap `D-108` in `docs/architecture/gap_register.md`
- current runtime seam under:
  - `src/stomatal_optimiaztion/domains/tdgm/thorp_g/hydraulics.py`
- current rerun evidence under:
  - `out/rerun_parity/tdgm/thorp_data_control_turgor/`

## Target Artifacts

- update `docs/architecture/review/python-rerun-parity-audit-note.md`
- update `docs/architecture/review/tdgm-root-sensitivity-zero-point-diagnosis-note.md`
- if the seam is fixed, extend the bounded TDGM rerun regression window beyond day `791.5`
- if the seam is only partially narrowed, open one more focused follow-up slice instead of a broad hydraulics rewrite

## Responsibilities

1. audit the root-specific zero-point derivative terms:
   - `d_psi_rc0_d_c_r_h`
   - `d_psi_rc0_d_c_r_v`
   - `dk_canopy_max_d_c_r_h`
   - `dk_canopy_max_d_c_r_v`
2. prove whether one bounded change in that branch moves or closes the first reopened day-`791.5` drift point
3. keep the slice scoped to root sensitivity amplitudes rather than reopening sapwood, mean-allocation, or the full TDGM runtime

## Non-Goals

- do not revisit the already-rejected stem-curve state candidate
- do not replace the MATLAB-consistent mean-allocation update with an exact filter
- do not reopen the exonerated root-uptake vectorization seam unless new evidence contradicts the earlier A/B check
- do not treat `d_e_d_d` / sapwood sensitivity as the primary target unless the root-specific branch is disproved

## Validation

1. `.\.venv\Scripts\python.exe -m pytest tests/test_tdgm_thorp_g_rerun_parity.py -q`
2. bounded rerun audit through at least `max_steps=3300`
3. `.\.venv\Scripts\python.exe -m pytest tests/test_tdgm_thorp_g_rerun_parity.py tests/test_root_rerun_parity_figures.py -q`
4. `.\.venv\Scripts\python.exe scripts\render_root_rerun_parity_figures.py --output-dir out/rerun_parity --domains tdgm`
5. `.\.venv\Scripts\python.exe -m pytest -q`
6. `.\.venv\Scripts\ruff.exe check .`

## Exit Criteria

- the first post-day-`791.5` drift point either moves later or is removed with one bounded root-sensitivity change, or
- the next remaining culprit is named explicitly inside the zero-point root-sensitivity branch with tighter evidence than module `111`
