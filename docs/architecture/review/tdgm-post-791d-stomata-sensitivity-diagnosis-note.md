# TDGM Post-791d Stomata Sensitivity Diagnosis Note

## Purpose

Record the bounded diagnosis slice from module `110` / GitHub issue `#218` for the remaining post-day-`791.5` root `TDGM` control drift.

## Scope

- canonical control payload:
  - `TDGM/example/Supplementary Code __THORP_code_v1.4/Simulations_and_code_to_plot/THORP_data_Control_Turgor.mat`
- bounded Python rerun horizon:
  - `max_steps=3300`
  - stored horizon through day `819.5`
- current runtime seams under:
  - `src/stomatal_optimiaztion/domains/tdgm/thorp_g/`

## Findings

1. The remaining root `TDGM` control drift reopens for the first time at stored index `113`, day `791.5`.
2. The first reopened mismatch is simultaneous across the stored control outputs, not isolated to a single plotted panel:
   - `A_n_stor`
   - `E_stor`
   - `P_x_l_stor`, `P_x_s_stor`, `P_x_r_stor`, `P_soil_stor`
   - `u_l_stor`, `u_sw_stor`, `u_r_H_stor`, `u_r_V_stor`
   - `c_NSC_stor`, `c_l_stor`, `c_sw_stor`, `c_hw_stor`
   - `D_stor`, `D_hw_stor`, `H_stor`, `W_stor`
3. At the first reopened point, the largest qualitative jump is in the daily optimal allocation fractions rather than in the slower structural state variables:
   - `u_l_stor`: Python `0.1966` vs legacy `0.3378`
   - `u_r_H_stor`: Python `0.3803` vs legacy `0.3440`
   - `u_r_V_stor`: Python `0.4057` vs legacy `0.3044`
4. Because `u_*_stor` are the daily optimal allocations emitted before growth uses the smoothed means, the first visible post-day-`791.5` seam is upstream of the mean-allocation history state itself.
5. A bounded A/B experiment replacing the runtime mean-allocation update with an exact exponential filter made the first mismatch much worse, moving the first drift forward to day `56.5`. That rules out the current `update_mean_allocation_fractions()` realization as the next fix direction.
6. The earlier standalone A/B check against the old loop-style root-uptake implementation did not change the post-day-`791.5` reopening point, so the remaining drift is not attributed to the root-uptake vectorization seam.
7. The pre-refactor TDGM reference port already treated long-horizon THORP-G parity as tolerance-based rather than exact, especially for:
   - allocation fractions (`atol=0.4`)
   - root and soil hydraulic keys (`P_soil_stor` absolute tolerance path)
   This indicates the post-day-`791.5` drift predates the current repository refactor.
8. The most likely next bounded source seam is the `THORP-G` stomata/hydraulic sensitivity branch that feeds the daily optimal allocation fractions, especially:
   - `d_e_d_c_r_h`
   - `d_e_d_c_r_v`
   - `lambda_wue` / `dA_n_dE`
   - `k_canopy_max` and `psi_rc0` sensitivity terms inside `hydraulics.py`

## Validation Executed

- bounded first-drift audit:
  - `max_steps=3300` rerun vs legacy `THORP_data_Control_Turgor.mat`
  - result: first reopened mismatch at stored index `113`, day `791.5`
- mean-allocation A/B experiment:
  - one-off exact exponential replacement for `update_mean_allocation_fractions()`
  - result: first mismatch moved earlier to day `56.5`
- reference-port audit:
  - `C:\Users\yhmoo\OneDrive\Phytoritas\00. Stomatal Optimization\TDGM\tests\test_thorp_g_v14_slow_regression_long_cases_full.py`
  - result: the older TDGM Python port already carried relaxed long-horizon tolerances for allocation and soil/hydraulic keys

## Result

- module `110` identifies the first remaining post-day-`791.5` divergence point explicitly
- module `110` rules out the mean-allocation filter realization as the next likely fix
- module `110` narrows the open `D-108` gap to the `THORP-G stomata/hydraulics sensitivity -> daily optimal allocation` seam

## Next Action

1. start from `docs/architecture/architecture/module_specs/module-111-tdgm-stomata-sensitivity-allocation-seam.md`
2. use `docs/architecture/executor/issue-220-bug-tdgm-stomata-sensitivity-allocation-seam.md` as the GitHub execution packet
3. keep the slice bounded to the sensitivity path inside `src/stomatal_optimiaztion/domains/tdgm/thorp_g/hydraulics.py`
