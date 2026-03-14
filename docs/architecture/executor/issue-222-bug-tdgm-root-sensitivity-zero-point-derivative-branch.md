## repro
- rerun the canonical root `TDGM` control case against `THORP_data_Control_Turgor.mat`
- confirm that the first remaining mismatch still reopens at day `791.5`
- inspect the root-specific zero-point sensitivity terms inside `src/stomatal_optimiaztion/domains/tdgm/thorp_g/hydraulics.py`

## expected / actual
- expected: the post-day-`791.5` control drift should be reducible by one bounded root-sensitivity change or be narrowed to one explicit zero-point derivative culprit
- actual: module `111` shows that root sensitivities are overestimated relative to legacy at day `791.5`, with the vertical-root branch more inflated than the horizontal-root branch, while sapwood is not the primary culprit

## scope
- `src/stomatal_optimiaztion/domains/tdgm/thorp_g/hydraulics.py`
- the root-specific zero-point sensitivity terms that feed `allocation_fractions()`
- bounded rerun evidence around day `791.5`

## fix idea
- audit `d_psi_rc0_d_c_r_h`, `d_psi_rc0_d_c_r_v`, `dk_canopy_max_d_c_r_h`, and `dk_canopy_max_d_c_r_v`
- test one bounded change at a time inside that branch
- keep the fast parity tests and the bounded long-horizon diagnostics green while pushing the first mismatch later than day `791.5`

## test
- `.\.venv\Scripts\python.exe -m pytest tests/test_tdgm_thorp_g_rerun_parity.py -q`
- bounded rerun audit through `max_steps=3300`
- `.\.venv\Scripts\python.exe -m pytest tests/test_tdgm_thorp_g_rerun_parity.py tests/test_root_rerun_parity_figures.py -q`
- `.\.venv\Scripts\python.exe -m pytest -q`
- `.\.venv\Scripts\ruff.exe check .`
