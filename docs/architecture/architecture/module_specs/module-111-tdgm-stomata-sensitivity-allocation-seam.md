# Module 111: TDGM Stomata Sensitivity Allocation Seam

## Goal

Reduce the remaining open `D-108` gap to the next bounded implementation slice by checking whether the post-day-`791.5` root `TDGM` drift comes from the `THORP-G` stomata/hydraulic sensitivity terms that drive the daily optimal allocation fractions.

## Inputs

- module `110` diagnosis note:
  - `docs/architecture/review/tdgm-post-791d-stomata-sensitivity-diagnosis-note.md`
- open gap `D-108` in `docs/architecture/gap_register.md`
- current runtime seam under:
  - `src/stomatal_optimiaztion/domains/tdgm/thorp_g/hydraulics.py`
- current rerun evidence under:
  - `out/rerun_parity/tdgm/thorp_data_control_turgor/`

## Target Artifacts

- update `docs/architecture/review/python-rerun-parity-audit-note.md`
- update `docs/architecture/review/tdgm-post-791d-stomata-sensitivity-diagnosis-note.md`
- if the seam is fixed, extend the bounded TDGM rerun regression window beyond day `791.5`
- if the seam is only partially narrowed, open one more focused follow-up slice instead of a broad hydraulic rewrite

## Responsibilities

1. audit the `THORP-G` sensitivity terms that feed `allocation_fractions()`:
   - `d_e_d_c_r_h`
   - `d_e_d_c_r_v`
   - `lambda_wue` / `dA_n_dE`
   - `k_canopy_max`, `psi_rc0`, and related derivative terms
2. prove whether one bounded change in `hydraulics.py` moves or closes the first reopened day-`791.5` drift point
3. keep the slice scoped to the allocation-driving sensitivity path rather than reopening the full TDGM runtime

## Non-Goals

- do not revisit the already-fixed pre-day-`497.5` stomatal optimum index seam
- do not replace the MATLAB-consistent mean-allocation update with an exact filter
- do not reopen the exonerated root-uptake vectorization seam unless new evidence contradicts the earlier A/B check

## Validation

1. `.\.venv\Scripts\python.exe -m pytest tests/test_tdgm_thorp_g_rerun_parity.py tests/test_root_rerun_parity_figures.py -q`
2. bounded rerun audit through at least `max_steps=3300`
3. `.\.venv\Scripts\python.exe scripts\render_root_rerun_parity_figures.py --output-dir out/rerun_parity --domains tdgm`
4. `.\.venv\Scripts\python.exe -m pytest -q`
5. `.\.venv\Scripts\ruff.exe check .`

## Exit Criteria

- the first post-day-`791.5` drift point either moves later or is removed with one bounded sensitivity-path change, or
- the next remaining culprit is named explicitly with tighter evidence than module `110`
