## repro
- regenerate the canonical root `TDGM` rerun bundle from the current Python runtime against the legacy MATLAB control payload:
  - `.\.venv\Scripts\python.exe scripts\render_root_rerun_parity_figures.py --output-dir out/rerun_parity --domains tdgm`
- inspect:
  - `out/rerun_parity/tdgm/thorp_data_control_turgor/tdgm_thorp_g_rerun_parity_case_thorp_data_control_turgor_diff.csv`
- compare the full stored horizon, not only the fast bounded regression window

## expected / actual
- expected: the canonical root `TDGM` control rerun should remain numerically tight against `THORP_data_Control_Turgor.mat` over the full stored series, the same way root `THORP` now does
- actual: the fast bounded parity tests pass, but the full-series diff file still shows long-horizon drift in assimilation, transpiration, height, and diameter

## scope
- root `TDGM` rerun runtime under `src/stomatal_optimiaztion/domains/tdgm/`
- shared THORP-G rerun dependencies used by the canonical control case
- live rerun inspection artifacts under `out/rerun_parity/tdgm/`

## fix idea
- isolate the first timestep or horizon segment where the Python and legacy control traces begin to diverge
- test whether the drift is introduced by growth-state carryover, mean allocation updates, THORP-G coupling state, or another long-horizon kernel mismatch
- keep the investigation bounded to diagnosis and evidence capture before changing any numerical kernel broadly

## test
- rerun the bounded fast parity tests first so the short-horizon contract stays protected
- regenerate the full root `TDGM` control rerun bundle and compare `*_python.csv`, `*_legacy.csv`, and `*_diff.csv`
- keep `pytest` and `ruff` green while narrowing the first divergence point
