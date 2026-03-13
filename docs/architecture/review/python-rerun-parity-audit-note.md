# Python Rerun Parity Audit Note

## Purpose

Verify that the migrated root `THORP`, `GOSM`, and `TDGM` packages can be rerun today in Python and compared directly against legacy MATLAB output payloads, rather than only against figure digests or adapter-derived summaries.

## Scope

- current Python reruns from:
  - `src/stomatal_optimiaztion/domains/thorp/`
  - `src/stomatal_optimiaztion/domains/gosm/`
  - `src/stomatal_optimiaztion/domains/tdgm/`
- legacy MATLAB output payloads from:
  - `THORP/example/THORP_code_forcing_outputs_plotting/Simulations_and_additional_code_to_plot/`
  - `GOSM/example/`
  - `TDGM/example/Supplementary Code __THORP_code_v1.4/Simulations_and_code_to_plot/`

Out of scope for this note:
- pixel-level figure comparison
- full-horizon reruns for every scenario
- re-running MATLAB itself

## Findings

1. Root `THORP` rerun parity is now closed for the fast control regression. The current Python runtime reproduces `THORP_data_0.6RH.mat` for the time axis and the first three stored points after `max_steps=60`.
2. Root `GOSM` rerun parity is now closed for:
   - `Example_Growth_Opt__control.mat`
   - `Growth_Opt_Stomata__test_sensitivity__RH.mat`
   - `Growth_Opt_Stomata__test_sensitivity__c_a.mat`
   - `Growth_Opt_Stomata__test_sensitivity__P_soil.mat`
   - `Growth_Opt_Stomata__test_sensitivity__P_soil_min__true_k_loss.mat`
3. Root `GOSM` also exposes the legacy `imag` conductance-loss rerun path. That branch remains opt-in behind `GOSM_RUN_SLOW=1` to keep the default validation loop bounded, and it was executed once during this audit to confirm that the slower path still reproduces the legacy MATLAB payload.
4. Root `TDGM` rerun parity required restoring the legacy `tdgm.thorp_g` runtime surface. With that seam restored, the current Python runtime matches ten representative THORP-G MATLAB scenarios for the time axis and the first three stored points after `max_steps=60`.
5. Within the documented fast-rerun scope, no open root architecture gap remains.

## Validation Executed

- `.\.venv\Scripts\python.exe -m pytest tests/test_thorp_rerun_parity.py tests/test_gosm_rerun_control.py tests/test_gosm_rerun_sensitivity_environmental_conditions.py tests/test_gosm_rerun_sensitivity_p_soil_min.py tests/test_tdgm_thorp_g_rerun_parity.py`
- result: `16 passed, 1 skipped`
- the skipped test is the opt-in slow `GOSM` `imag` conductance-loss rerun branch
- `powershell -Command "$env:GOSM_RUN_SLOW='1'; .\.venv\Scripts\python.exe -m pytest tests/test_gosm_rerun_sensitivity_p_soil_min.py -k imag"`
- result: `1 passed, 1 deselected`
- `.\.venv\Scripts\python.exe -m pytest`
- result: `428 passed, 1 skipped`
- `.\.venv\Scripts\ruff.exe check .`
- result: `passed`

## Result

- root `THORP`: direct Python rerun vs legacy MATLAB output comparison available and passing
- root `GOSM`: direct Python rerun vs legacy MATLAB output comparison available and passing for the default fast control and sensitivity set, with the slower `imag` conductance-loss branch manually verified as well
- root `TDGM`: direct Python rerun vs legacy MATLAB output comparison available and passing for the fast THORP-G regression set

## Next Actions

1. keep the rerun parity tests green whenever root hydraulic or growth kernels change
2. rerun the opt-in slow `GOSM` `imag` conductance-loss branch when touching root `gosm` hydraulics or stomatal-model logic
3. leave the architecture in monitor mode until a new bounded rerun or workflow gap appears
