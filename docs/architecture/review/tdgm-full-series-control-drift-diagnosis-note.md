# TDGM Full-Series Control Drift Diagnosis Note

## Purpose

Record the bounded diagnosis slice from module `109` / GitHub issue `#209` for the canonical root `TDGM` control rerun against the legacy MATLAB payload.

## Scope

- canonical control payload:
  - `TDGM/example/Supplementary Code __THORP_code_v1.4/Simulations_and_code_to_plot/THORP_data_Control_Turgor.mat`
- current Python runtime:
  - `src/stomatal_optimiaztion/domains/tdgm/`
  - `src/stomatal_optimiaztion/domains/tdgm/thorp_g/`
- regenerated evidence bundle:
  - `out/rerun_parity/tdgm/thorp_data_control_turgor/`

## Findings

1. Before slice `109`, the regenerated canonical control rerun first diverged from the legacy MATLAB payload near day `497.5`.
2. The first proven seam was an off-by-one indexing mismatch in `tdgm.thorp_g.hydraulics.stomata()`.
3. MATLAB checks the first `diff(F)` entry together with the first `g_w_curve` / `psi_l_curve` point, but the Python implementation had started from the second pair.
4. Initializing the Python scan at `idx = -1` restores machine-precision agreement through the historical first-drift window.
5. A new bounded regression at `max_steps=2050` now locks the control case through that former day-`497.5` failure region without forcing the default suite to rerun the full multi-decade horizon.
6. The full-series gap is reduced but not closed. After rerendering the live control bundle, the residual drift reopens later, with the first visible mismatch near day `791.5`.
7. The remaining post-`791.5` gap is smaller than the pre-fix state but still material:
   - `assimilation` `max_abs_diff ~= 0.8675`
   - `transpiration` `max_abs_diff ~= 0.2879`
   - `height` `max_abs_diff ~= 0.03108`
   - `diameter` `max_abs_diff ~= 0.0004614`
8. An A/B check against the old loop-style root-uptake path reproduced the same post-`791.5` behavior, so slice `109` does not implicate the root-uptake vectorization seam as the next likely cause.

## Implemented Change

- `src/stomatal_optimiaztion/domains/tdgm/thorp_g/hydraulics.py`
  - fix the stomatal optimum scan start index in `stomata()` so the first derivative pair matches the legacy MATLAB control flow
- `tests/test_tdgm_thorp_g_rerun_parity.py`
  - add a bounded long-horizon control regression that extends beyond the former first drift point

## Validation Executed

- `.\.venv\Scripts\python.exe -m pytest tests/test_tdgm_thorp_g_rerun_parity.py tests/test_root_rerun_parity_figures.py -q`
  - result: `19 passed`
- `.\.venv\Scripts\python.exe scripts\render_root_rerun_parity_figures.py --output-dir out/rerun_parity --domains tdgm`
  - result: canonical root `TDGM` control bundle regenerated under `out/rerun_parity/`
- `.\.venv\Scripts\ruff.exe check .`
  - result: pass
- `.\.venv\Scripts\python.exe -m pytest -q`
  - result: `419 passed, 1 skipped`

## Result

- module `109` resolves the first proven long-horizon `TDGM` control-drift seam
- the canonical root `TDGM` control rerun is now exact through the former day-`497.5` failure window
- open gap `D-108` remains, but it is now narrowed to the later post-`791.5` horizon and handed off to module `110` / GitHub issue `#218`

## Next Action

1. start from the post-`791.5` bounded follow-up slice in `docs/architecture/architecture/module_specs/module-110-tdgm-post-791d-control-drift-investigation.md`
2. use `docs/architecture/executor/issue-218-bug-tdgm-post-791d-control-rerun-drift.md` as the GitHub execution packet
3. do not declare root `TDGM` full-series parity closed until the remaining post-`791.5` seam is either removed or explained
