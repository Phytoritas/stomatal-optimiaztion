## repro
- regenerate the canonical root `TDGM` rerun bundle from the current Python runtime against the legacy MATLAB control payload after slice `109`:
  - `.\.venv\Scripts\python.exe scripts\render_root_rerun_parity_figures.py --output-dir out/rerun_parity --domains tdgm`
- inspect:
  - `out/rerun_parity/tdgm/thorp_data_control_turgor/tdgm_thorp_g_rerun_parity_case_thorp_data_control_turgor_diff.csv`
- confirm that the pre-day-`497.5` window now matches and that the remaining drift reopens later, near day `791.5`

## expected / actual
- expected: after slice `109`, the canonical root `TDGM` control rerun should either stay tight against `THORP_data_Control_Turgor.mat` over the rest of the stored series or expose one next bounded seam with explicit evidence
- actual: slice `109` fixed the first proven seam near day `497.5`, but the regenerated full-series diff file still reopens later in assimilation, transpiration, height, and diameter near day `791.5`

## scope
- root `TDGM` rerun runtime under `src/stomatal_optimiaztion/domains/tdgm/`
- shared `tdgm.thorp_g` rerun dependencies used by the canonical control case
- live rerun inspection artifacts under `out/rerun_parity/tdgm/`

## fix idea
- isolate the first timestep or horizon segment where the remaining Python and legacy control traces begin to diverge after day `791.5`
- test whether the later drift is introduced by growth-state carryover, mean allocation updates, TDGM coupling state, or another long-horizon kernel mismatch
- keep the investigation bounded to one next proven seam before changing numerical kernels broadly

## test
- keep the bounded fast parity tests and the new `max_steps=2050` regression green
- regenerate the full root `TDGM` control rerun bundle and compare `*_python.csv`, `*_legacy.csv`, and `*_diff.csv`
- keep `pytest` and `ruff` green while narrowing the post-day-`791.5` divergence point
