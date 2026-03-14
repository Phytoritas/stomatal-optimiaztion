# TDGM Root Sensitivity Zero-Point Diagnosis Note

## Purpose

Record the bounded diagnosis slice from module `111` / GitHub issue `#220` for the remaining post-day-`791.5` root `TDGM` control drift.

## Scope

- canonical control payload:
  - `TDGM/example/Supplementary Code __THORP_code_v1.4/Simulations_and_code_to_plot/THORP_data_Control_Turgor.mat`
- bounded Python rerun horizon:
  - `max_steps=3300`
  - stored horizon through day `819.5`
- current runtime seam under:
  - `src/stomatal_optimiaztion/domains/tdgm/thorp_g/hydraulics.py`

## Findings

1. The first reopened root `TDGM` mismatch still starts at stored index `113`, day `791.5`; the rerun remains exact through day `784.5`.
2. A bounded candidate that replaced the curve-building stem-state lookup `VC_sw(min(0, psi_l_i))` with `VC_sw(min(0, psi_s_i))` was rejected:
   - it introduced visible drift already by day `784.5`
   - it broke the fast THORP-G parity guard immediately
3. At day `791.5`, the stored `A_n`, `E`, and `psi_*` values are only slightly off, but the daily optimal allocation fractions are materially root-heavy:
   - `u_l_stor`: Python `0.1966` vs legacy `0.3378`
   - `u_r_H_stor`: Python `0.3803` vs legacy `0.3440`
   - `u_r_V_stor`: Python `0.4057` vs legacy `0.3044`
4. A scalar fit of the shared `lambda_wue * dE` product improves the day-`791.5` allocation mismatch only partially:
   - best global scale is about `0.54`
   - that improves `u_l_stor`, but still leaves sapwood too high and the root split off target
5. Holding the sapwood path unchanged while scaling only the root sensitivity derivatives gives a better fit than scaling every `dE` derivative together:
   - best root-only scale is about `0.52`
   - this exonerates `d_e_d_d` / sapwood sensitivity as the primary culprit
6. Allowing the root sensitivity branches to vary separately gives the tightest bounded fit near:
   - `d_e_d_c_r_h`: about `0.58` of the current Python amplitude
   - `d_e_d_c_r_v`: about `0.50` of the current Python amplitude
   This indicates the vertical-root sensitivity branch is more overestimated than the horizontal-root branch.
7. The next likely culprit is therefore the root-specific zero-point sensitivity branch inside `hydraulics.py`, not:
   - the mean-allocation filter
   - the exonerated root-uptake vectorization seam
   - the rejected stale stem-curve state candidate
   - the sapwood derivative path
8. The most likely next bounded source terms are:
   - `d_psi_rc0_d_c_r_h`
   - `d_psi_rc0_d_c_r_v`
   - `dk_canopy_max_d_c_r_h`
   - `dk_canopy_max_d_c_r_v`

## Validation Executed

- targeted parity guard after reverting the rejected stem-state candidate:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_tdgm_thorp_g_rerun_parity.py -q`
  - result: `11 passed`
- bounded allocation-fit audit at the reopened drift point:
  - rerun through `max_steps=3300`
  - compare day-`791.5` stored allocation fractions against the legacy MATLAB payload
  - scale experiments over:
    - shared `lambda_wue * dE` product
    - root-only sensitivity terms
    - separate horizontal vs vertical root sensitivity terms

## Result

- module `111` rejects the stale stem-curve state candidate as the next fix direction
- module `111` narrows the open `D-108` gap beyond the generic sensitivity path to the root-specific zero-point derivative branch
- module `111` identifies the vertical-root sensitivity branch as the more overestimated of the two root paths

## Next Action

1. start from `docs/architecture/architecture/module_specs/module-112-tdgm-root-sensitivity-zero-point-derivative-branch.md`
2. use `docs/architecture/executor/issue-222-bug-tdgm-root-sensitivity-zero-point-derivative-branch.md` as the GitHub execution packet
3. keep the next slice bounded to the zero-point root-sensitivity terms inside `src/stomatal_optimiaztion/domains/tdgm/thorp_g/hydraulics.py`
