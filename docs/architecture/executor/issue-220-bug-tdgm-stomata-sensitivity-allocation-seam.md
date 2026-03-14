## repro
- rerun the canonical root `TDGM` control case against `THORP_data_Control_Turgor.mat`
- confirm that the first remaining mismatch still reopens at day `791.5`
- inspect the `THORP-G` sensitivity path inside `src/stomatal_optimiaztion/domains/tdgm/thorp_g/hydraulics.py`

## expected / actual
- expected: the post-day-`791.5` control drift should be explainable by one bounded sensitivity-path seam or be reduced by one bounded fix
- actual: module `110` shows that the first reopened mismatch appears simultaneously in hydraulics, daily optimal allocation fractions, and downstream growth states, with the sharpest visible jump in `u_*_stor`

## scope
- `src/stomatal_optimiaztion/domains/tdgm/thorp_g/hydraulics.py`
- the daily optimal allocation inputs derived from the selected stomatal optimum
- bounded rerun evidence around day `791.5`

## fix idea
- audit the derivative and sensitivity terms that feed `allocation_fractions()`
- test one bounded change at a time inside the sensitivity path
- keep the fast parity tests and the bounded long-horizon diagnostics green while pushing the first mismatch later than day `791.5`

## test
- `.\.venv\Scripts\python.exe -m pytest tests/test_tdgm_thorp_g_rerun_parity.py tests/test_root_rerun_parity_figures.py -q`
- bounded rerun audit through `max_steps=3300`
- `.\.venv\Scripts\python.exe -m pytest -q`
- `.\.venv\Scripts\ruff.exe check .`
