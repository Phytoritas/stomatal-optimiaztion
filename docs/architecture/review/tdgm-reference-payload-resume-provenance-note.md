# TDGM Reference Payload Resume Provenance Note

## Purpose

Record the closing slice for open gap `D-108` by proving that the remaining post-day-`791.5` control drift belongs to the shipped legacy MATLAB payload provenance, not to a remaining live `tdgm.thorp_g` kernel mismatch.

## Scope

- canonical control payload:
  - `TDGM/example/Supplementary Code __THORP_code_v1.4/Simulations_and_code_to_plot/THORP_data_Control_Turgor.mat`
- continuous Python rerun:
  - `src/stomatal_optimiaztion/domains/tdgm/thorp_g/`
- bounded provenance window:
  - exact continuous parity through day `784.5`
  - shipped-payload explanation through stored days `791.5` to `819.5`

## Findings

1. The continuous Python rerun is exact against the shipped control payload through the last pre-artifact weekly checkpoint at day `784.5`.
   - bounded guard: `max_steps=3150`
   - all stored scalar and layerwise keys stay within machine precision
2. The first reopened shipped-payload mismatch appears at day `791.5`, exactly `4.5` days after the MATLAB file-save boundary at day `787`.
3. The MATLAB restart surface explains that timing:
   - `STORE_data.m` initializes `t_sav_file = dt_sav_data`, so the first file save is at day `7` and later saves advance by `dt_sav_file`
   - `LOAD_data.m` resumes from `t = t_stor(end)` and `P_soil = P_soil_stor(:, end)`, which means a rerun after day `787` would restart from the last weekly checkpoint at day `784.5`, not from the true midnight file-save state
   - `THORP.m` computes `FUNCTION_Initial_Mean_Allocation_Fractions(...)` before `LOAD_data`, so a resumed run also carries fresh-run mean-allocation history instead of restoring the current one
4. A bounded Python replay that starts from the shipped day-`784.5` stored checkpoint and applies exactly that one-off resume behavior reproduces the later shipped payload very closely through day `819.5`.
   - `A_n_stor` max abs diff: `1.73e-11`
   - `E_stor` max abs diff: `8.01e-09`
   - daily allocation fractions max abs diff: `1.22e-05`
   - `P_x_l_stor` max abs diff: `1.58e-06`
   - `P_soil_stor` max abs diff: `2.59e-06`
5. The earlier diagnosis slices were therefore tracing a reference-payload artifact, not a remaining scientific-runtime formula bug.
   - the `dk_canopy_max` sensitivity branch was a symptom of the resumed checkpoint state, not the root cause of the shipped-payload reopening

## Validation Executed

- `.\.venv\Scripts\python.exe -m pytest tests/test_tdgm_thorp_g_rerun_parity.py -q`
  - result: `12 passed`
- bounded replay audit:
  - exact continuous rerun through `max_steps=3150`
  - single resumed replay from the shipped day-`784.5` checkpoint through day `819.5`
  - compare stored `A_n`, `E`, `u_*`, `c_*`, `P_x_*`, and `P_soil` against the shipped payload
- `.\.venv\Scripts\python.exe -m pytest -q`
  - result: `420 passed, 1 skipped`
- `.\.venv\Scripts\ruff.exe check .`
  - result: pass

## Result

- `D-108` is closed
- root `TDGM` continuous source parity remains exact through the last pre-artifact checkpoint at day `784.5`
- the shipped control payload after day `791.5` is now explained by one external MATLAB resume from the last weekly checkpoint after the day-`787` file save

## Next Action

1. keep the continuous exact rerun guard through day `784.5` green whenever `tdgm.thorp_g` runtime kernels change
2. keep the shipped-payload provenance replay guard green so the reference explanation does not need to be rediscovered
3. treat any new later-horizon `TDGM` drift as a new issue only if it breaks either of those two guards
