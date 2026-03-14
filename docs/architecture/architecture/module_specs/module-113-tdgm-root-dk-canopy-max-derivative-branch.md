# Module 113: TDGM Root dk_canopy_max Derivative Branch

## Goal

Reduce the remaining open `D-108` gap to the next bounded implementation slice by checking whether the post-day-`791.5` root `TDGM` drift is caused specifically by `dk_canopy_max_d_c_r_h` and `dk_canopy_max_d_c_r_v` inside `tdgm.thorp_g.hydraulics.stomata()`.

## Inputs

- module `112` diagnosis note:
  - `docs/architecture/review/tdgm-root-dk-canopy-max-derivative-diagnosis-note.md`
- open gap `D-108` in `docs/architecture/gap_register.md`
- current runtime seam under:
  - `src/stomatal_optimiaztion/domains/tdgm/thorp_g/hydraulics.py`
- current rerun evidence under:
  - `out/rerun_parity/tdgm/thorp_data_control_turgor/`

## Target Artifacts

- update `docs/architecture/review/python-rerun-parity-audit-note.md`
- add or update a focused diagnosis note for the `dk_canopy_max` branch
- if the seam is fixed, extend the bounded TDGM rerun regression window beyond day `791.5`
- if the seam is only partially narrowed, open one more focused follow-up slice instead of reopening the full THORP-G sensitivity path

## Responsibilities

1. audit the root-specific `dk_canopy_max` derivative terms:
   - `dk_canopy_max_d_c_r_h`
   - `dk_canopy_max_d_c_r_v`
2. compare their upstream state terms against the legacy MATLAB path:
   - `c0_var`
   - `f_r0`
   - `df_r0_d_psi_rc0`
   - `d2f_r0_d_psi_rc0`
   - `r_r_h0`
   - `r_r_v0`
   - `r_r0`
3. prove whether one bounded change in that branch moves or closes the first reopened day-`791.5` drift point
4. keep the slice scoped to the `dk_canopy_max` root branch rather than reopening mean allocation, sapwood sensitivity, or the direct `d_psi_rc0_d_c_r_*` path

## Non-Goals

- do not revisit the already-exonerated zero-flux `f_ri` branch in `e_from_soil_to_root_collar()`
- do not reopen the rejected stale stem-curve candidate
- do not replace the MATLAB-consistent mean-allocation update with an exact filter
- do not treat the direct `d_psi_rc0_d_c_r_*` terms as the primary target unless new evidence contradicts module `112`

## Validation

1. `.\.venv\Scripts\python.exe -m pytest tests/test_tdgm_thorp_g_rerun_parity.py -q`
2. bounded rerun audit through at least `max_steps=3300`
3. `.\.venv\Scripts\python.exe -m pytest tests/test_tdgm_thorp_g_rerun_parity.py tests/test_root_rerun_parity_figures.py -q`
4. `.\.venv\Scripts\python.exe scripts\render_root_rerun_parity_figures.py --output-dir out/rerun_parity --domains tdgm`
5. `.\.venv\Scripts\python.exe -m pytest -q`
6. `.\.venv\Scripts\ruff.exe check .`

## Exit Criteria

- the first post-day-`791.5` drift point either moves later or is removed with one bounded `dk_canopy_max` root-sensitivity change, or
- the next remaining culprit is named explicitly inside the root-specific `dk_canopy_max` derivative branch with tighter evidence than module `112`
