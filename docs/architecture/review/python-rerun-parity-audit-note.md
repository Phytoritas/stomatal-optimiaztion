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
- full-horizon reruns for every historical scenario variant
- re-running MATLAB itself

## Findings

1. Root `THORP` rerun parity is now closed for:
   - fast regression coverage at `max_steps=60`
   - regenerated full stored-series graph/data export for the canonical control case `THORP_data_0.6RH.mat`
   - full-series control `max_abs_diff` within machine precision (`<= 4.99e-13` across the live `*_diff.csv`)
2. Root `GOSM` rerun parity is now closed for:
   - `Example_Growth_Opt__control.mat`
   - `Growth_Opt_Stomata__test_sensitivity__RH.mat`
   - `Growth_Opt_Stomata__test_sensitivity__c_a.mat`
   - `Growth_Opt_Stomata__test_sensitivity__P_soil.mat`
   - `Growth_Opt_Stomata__test_sensitivity__P_soil_min__true_k_loss.mat`
   These are full response-domain comparisons rather than time-series reruns, because the legacy `GOSM` reference payloads are control/sensitivity curves rather than stored temporal traces.
3. Root `GOSM` reruns are now warning-free for the fast control and sensitivity paths. The rerun regressions promote `RuntimeWarning` to test failures, so the current `hydraulics`, `conductance_temperature`, stomata-model, and example helper branches no longer emit transient NumPy warnings during parity checks.
4. Root `GOSM` also exposes the legacy `imag` conductance-loss rerun path. That branch remains opt-in behind `GOSM_RUN_SLOW=1` to keep the default validation loop bounded, and it was executed under `warnings-as-errors` to confirm that the slower path still reproduces the legacy MATLAB payload without emitting `RuntimeWarning`.
5. Root `TDGM` rerun parity required restoring the legacy `tdgm.thorp_g` runtime surface. With that seam restored, the current Python runtime matches ten representative THORP-G MATLAB scenarios for the time axis and the first three stored points after `max_steps=60`.
6. Slice `109` fixed the first proven long-horizon `TDGM` control-drift seam in `tdgm.thorp_g.hydraulics.stomata()`. The canonical control rerun now matches the legacy MATLAB payload through the historical first-drift window near day `497.5`, and that bounded window is locked by a `max_steps=2050` regression.
7. The canonical root `TDGM` control case still has a regenerated full stored-series graph/data export path, and that full-horizon comparison exposes a later reopening if compared naively against the shipped control payload:
   - first reopened divergence near day `791.5`
   - `assimilation` `max_abs_diff ~= 0.8675`
   - `transpiration` `max_abs_diff ~= 0.2879`
   - `height` `max_abs_diff ~= 0.03108`
   - `diameter` `max_abs_diff ~= 0.0004614`
   The later slices below explain that reopening as payload provenance rather than a remaining live-kernel mismatch.
8. Module `110` narrows that remaining post-day-`791.5` gap further:
   - the first reopened mismatch is simultaneous across hydraulics, daily optimal allocation fractions, and downstream growth states at stored index `113`
   - a bounded A/B experiment shows that replacing the runtime mean-allocation filter with an exact exponential update makes the drift much worse, so the mean-allocation realization is not the next fix direction
   - the most likely next seam is the `THORP-G` stomata/hydraulic sensitivity path that feeds `allocation_fractions()`
9. Module `111` narrows that remaining gap again:
   - a bounded stem-curve candidate that swapped `VC_sw(min(0, psi_l_i))` for `VC_sw(min(0, psi_s_i))` is rejected because it breaks the fast THORP-G parity guard immediately
   - day-`791.5` allocation-fit experiments show that scaling only the root sensitivity derivatives improves the legacy match more than scaling all `dE` derivatives together
   - the vertical-root sensitivity branch is more overestimated than the horizontal-root branch, so the next likely culprit is the root-specific zero-point derivative branch rather than sapwood or the shared mean-allocation logic
10. Module `112` narrows the same gap one step further:
   - the zero-flux `f_ri` legacy quirk in `e_from_soil_to_root_collar()` never triggers in the bounded rerun and is therefore exonerated as the reopened culprit
   - at day `791.5`, the direct `k_canopy_max * d_psi_rc0_d_c_r_*` contribution is tiny, while the `i_var * dk_canopy_max_d_c_r_*` contribution dominates both root sensitivity branches
   - scaling only the `dk_canopy_max` contribution improves the day-`791.5` legacy allocation fit by about twenty-fold, while scaling only the direct `d_psi_rc0` contribution does almost nothing
   - the next likely culprit is therefore the root-specific `dk_canopy_max_d_c_r_*` branch, especially the vertical-root path
11. Module `113` closes `D-108` by resolving the shipped payload provenance:
   - the continuous Python rerun is exact through day `784.5`
   - the MATLAB restart surface (`STORE_data.m` + `LOAD_data.m`) can resume from the last weekly checkpoint at day `784.5` after the day-`787` file save, while leaving the mean-allocation history at its fresh-run initialization
   - replaying that one-off resume reproduces the shipped day-`791.5` to `819.5` payload within tight tolerances, so the later reopening is not treated as a remaining live `tdgm.thorp_g` kernel bug
12. Root rerun parity is now directly inspectable without reading pytest internals. `scripts/render_root_rerun_parity_figures.py` renders Plotkit-style bundles under `out/rerun_parity/` with:
   - `THORP` control `png + python/legacy/diff csv`
   - `GOSM` control plus fast sensitivity `png + python/legacy/diff csv`
   - `TDGM` canonical control `png + python/legacy/diff csv` by default
13. The old legacy-only example plotting scripts/specs/tests have been pruned from the live repository surface so that `out/rerun_parity/` is the only supported graph inspection entrypoint for root rerun comparison.
14. Within the documented rerun-comparison scope, root `THORP`, root `GOSM`, and root `TDGM` are currently closed. The former post-day-`791.5` `TDGM` reopening is now explained by shipped-payload resume provenance.

## Validation Executed

- `.\.venv\Scripts\python.exe -m pytest tests/test_thorp_rerun_parity.py tests/test_gosm_rerun_control.py tests/test_gosm_rerun_sensitivity_environmental_conditions.py tests/test_gosm_rerun_sensitivity_p_soil_min.py tests/test_tdgm_thorp_g_rerun_parity.py`
- result: `16 passed, 1 skipped`
- the skipped test is the opt-in slow `GOSM` `imag` conductance-loss rerun branch
- `.\.venv\Scripts\python.exe -m pytest tests/test_root_rerun_parity_figures.py`
- result: root rerun graph/data bundle contract passes under fast smoke mode
- `.\.venv\Scripts\python.exe -m pytest tests/test_gosm_rerun_control.py tests/test_gosm_rerun_sensitivity_environmental_conditions.py tests/test_gosm_rerun_sensitivity_p_soil_min.py -W error::RuntimeWarning`
- result: `5 passed, 1 skipped`
- `powershell -Command "$env:GOSM_RUN_SLOW='1'; .\.venv\Scripts\python.exe -m pytest tests/test_gosm_rerun_sensitivity_p_soil_min.py -k imag"`
- result: `1 passed, 1 deselected`
- `powershell -Command "$env:GOSM_RUN_SLOW='1'; .\.venv\Scripts\python.exe -m pytest tests/test_gosm_rerun_sensitivity_p_soil_min.py -k imag -W error::RuntimeWarning"`
- result: `1 passed, 1 deselected`
- `.\.venv\Scripts\python.exe scripts\render_root_rerun_parity_figures.py --output-dir out/rerun_parity --domains gosm`
- result: full root `GOSM` rerun bundles regenerated under `out/rerun_parity/`
- `.\.venv\Scripts\python.exe scripts\render_root_rerun_parity_figures.py --output-dir out/rerun_parity --domains thorp`
- result: canonical root `THORP` full-series control rerun bundle regenerated under `out/rerun_parity/`
- `.\.venv\Scripts\python.exe scripts\render_root_rerun_parity_figures.py --output-dir out/rerun_parity --domains tdgm`
- result: canonical root `TDGM` full-series control rerun bundle regenerated under `out/rerun_parity/`
- `.\.venv\Scripts\python.exe -m pytest tests/test_tdgm_thorp_g_rerun_parity.py tests/test_root_rerun_parity_figures.py -q`
  - result: `19 passed`
- `.\.venv\Scripts\python.exe -m pytest`
- result: `419 passed, 1 skipped`
- `.\.venv\Scripts\ruff.exe check .`
- result: `passed`

## Result

- root `THORP`: direct Python rerun vs legacy MATLAB output comparison available and passing, with regenerated full stored-series control exports matching the legacy payload to machine precision
- root `GOSM`: direct Python rerun vs legacy MATLAB output comparison available and passing for the default fast control and sensitivity set, warning-free under `warnings-as-errors`, with the slower `imag` conductance-loss branch manually verified the same way
- root `TDGM`: direct Python rerun vs legacy MATLAB output comparison available and passing for the fast THORP-G regression set, with exact continuous parity through day `784.5` and a closed explanation for the shipped post-day-`791.5` payload reopening
- root rerun parity graph bundles: reproducible Plotkit-style rerun-only overlays available under `out/rerun_parity/`

## Next Actions

1. keep the rerun parity tests green whenever root hydraulic or growth kernels change
2. rerun the opt-in slow `GOSM` `imag` conductance-loss branch when touching root `gosm` hydraulics or stomatal-model logic
3. rerender `scripts/render_root_rerun_parity_figures.py` whenever root rerun kernels change
4. use `docs/architecture/review/tdgm-reference-payload-resume-provenance-note.md` if later-horizon root `TDGM` payload diffs need to be interpreted again
