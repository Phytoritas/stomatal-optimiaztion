## repro
- rerun the canonical root `TDGM` control case against `THORP_data_Control_Turgor.mat`
- confirm that the first remaining mismatch still reopens at day `791.5`
- inspect the root-specific `dk_canopy_max` derivative terms inside `src/stomatal_optimiaztion/domains/tdgm/thorp_g/hydraulics.py`

## expected / actual
- expected: the post-day-`791.5` control drift should be reducible by one bounded `dk_canopy_max` change or be narrowed to one explicit derivative culprit inside that branch
- actual: module `112` shows that scaling the direct `d_psi_rc0_d_c_r_*` terms does almost nothing, while scaling only `dk_canopy_max_d_c_r_h` and `dk_canopy_max_d_c_r_v` sharply improves the day-`791.5` legacy allocation fit

## scope
- `src/stomatal_optimiaztion/domains/tdgm/thorp_g/hydraulics.py`
- specifically `dk_canopy_max_d_c_r_h` and `dk_canopy_max_d_c_r_v`
- bounded rerun evidence around day `791.5`

## fix idea
- audit the `dk_canopy_max` derivative formulas and their upstream state terms against the legacy MATLAB path
- test one bounded change at a time inside that branch
- keep the fast parity tests and the bounded long-horizon diagnostics green while pushing the first mismatch later than day `791.5`

## test
- `.\.venv\Scripts\python.exe -m pytest tests/test_tdgm_thorp_g_rerun_parity.py -q`
- bounded rerun audit through `max_steps=3300`
- `.\.venv\Scripts\python.exe -m pytest tests/test_tdgm_thorp_g_rerun_parity.py tests/test_root_rerun_parity_figures.py -q`
- `.\.venv\Scripts\python.exe -m pytest -q`
- `.\.venv\Scripts\ruff.exe check .`
