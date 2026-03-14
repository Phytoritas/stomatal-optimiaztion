# TDGM Root dk_canopy_max Derivative Diagnosis Note

## Purpose

Record the bounded diagnosis slice from module `112` / GitHub issue `#222` for the remaining post-day-`791.5` root `TDGM` control drift.

## Scope

- canonical control payload:
  - `TDGM/example/Supplementary Code __THORP_code_v1.4/Simulations_and_code_to_plot/THORP_data_Control_Turgor.mat`
- bounded Python rerun horizon:
  - `max_steps=3300`
  - stored horizon through day `819.5`
- current runtime seam under:
  - `src/stomatal_optimiaztion/domains/tdgm/thorp_g/hydraulics.py`

## Findings

1. The MATLAB `FUNCTION_E_from_Soil_to_Root_Collar.m` zero-flux branch where `E_i = 0` leaves `f_ri` implicit, but that legacy quirk is not the reopened culprit in the bounded rerun:
   - a wrapper audit recorded `0` hits for that branch through `max_steps=3300`
   - the active equality branch fired `3300` times instead
   - carrying the previous `f_ri` value through the zero-flux branch changed nothing at day `784.5` or day `791.5`
2. At the reopened day `791.5` drift point, the root-sensitivity decomposition inside `stomata()` is dominated by the `dk_canopy_max` branch rather than the direct zero-point derivative branch:
   - horizontal root sum:
     - direct `k_canopy_max * d_psi_rc0_d_c_r_h`: `2.76e-06`
     - `i_var * dk_canopy_max_d_c_r_h`: `5.18e-04`
     - local additive term: `-1.43e-04`
   - vertical root sum:
     - direct `k_canopy_max * d_psi_rc0_d_c_r_v`: `6.57e-06`
     - `i_var * dk_canopy_max_d_c_r_v`: `5.69e-04`
     - local additive term: `-1.12e-04`
3. Scaling only the shared `dk_canopy_max` contribution sharply improves the day-`791.5` legacy allocation fit:
   - baseline allocation-fit error: `0.03152`
   - best shared `dk` scale: about `0.60`
   - improved allocation-fit error: `0.00151`
4. Scaling only the direct `d_psi_rc0_d_c_r_*` contribution does not materially improve the fit:
   - best shared direct scale: `0.00`
   - allocation-fit error remains `0.03046`
   - the direct branch is therefore too small to explain the reopened drift on its own
5. Allowing the `dk_canopy_max` terms to vary separately gives the tightest bounded fit near:
   - `dk_canopy_max_d_c_r_h`: about `0.64` of the current Python amplitude
   - `dk_canopy_max_d_c_r_v`: about `0.58` of the current Python amplitude
   - resulting allocation-fit error: `0.000339`
   This keeps the vertical-root path as the more inflated of the two `dk` branches.
6. Allowing the direct `d_psi_rc0_d_c_r_*` terms to vary separately still does not move the fit in a meaningful way:
   - best separate direct scales: `0.00 / 0.00`
   - allocation-fit error remains `0.03046`
7. The source-parity read-through did not reveal an obvious text-level transcription mismatch between the current Python `dk_canopy_max` formulas and the shipped MATLAB `FUNCTION_Stomata.m` expressions. The next bounded culprit is therefore narrower than "root zero-point derivatives" but not yet a proven one-line formula typo.

## Validation Executed

- targeted parity guard:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_tdgm_thorp_g_rerun_parity.py -q`
  - result: `11 passed`
- bounded decomposition and allocation-fit audit:
  - rerun through `max_steps=3300`
  - capture the day-`791.5` `stomata()` state
  - decompose `d_e_d_c_r_h` and `d_e_d_c_r_v` into:
    - direct `k_canopy_max * d_psi_rc0_d_c_r_*`
    - `i_var * dk_canopy_max_d_c_r_*`
    - local additive root term
  - compare legacy allocation fit under:
    - shared `dk` scaling
    - shared direct scaling
    - separate horizontal / vertical `dk` scaling
    - separate horizontal / vertical direct scaling

## Result

- module `112` rules out the direct `d_psi_rc0_d_c_r_*` branch as the next meaningful fix target
- module `112` narrows the open `D-108` gap further to the root-specific `dk_canopy_max` derivative branch inside `tdgm.thorp_g.hydraulics.stomata()`
- the remaining likely culprits are now:
  - `dk_canopy_max_d_c_r_h`
  - `dk_canopy_max_d_c_r_v`
  - especially the vertical-root `dk_canopy_max_d_c_r_v` path

## Next Action

1. start from `docs/architecture/architecture/module_specs/module-113-tdgm-root-dk-canopy-max-derivative-branch.md`
2. use `docs/architecture/executor/issue-224-bug-tdgm-root-dk-canopy-max-derivative-branch.md` as the GitHub execution packet
3. keep the next slice bounded to the `dk_canopy_max_d_c_r_*` formulas and their upstream state terms inside `src/stomatal_optimiaztion/domains/tdgm/thorp_g/hydraulics.py`
