# GOSM Sensitivity And Manuscript Parity Note

## Purpose

Record the bounded example-parity evidence packet that closes the remaining root `GOSM` sensitivity and manuscript plotting workflows.

## Legacy Reference

- MATLAB scripts:
  - `GOSM/example/PLOT_true_vs_imag_conductance_loss.m`
  - `GOSM/example/PLOT_sensitivity_analyses.m`
  - `GOSM/example/Inkscape_figure_plots.m`
- legacy sensitivity payloads:
  - `GOSM/example/Growth_Opt_Stomata__test_sensitivity__*.mat`
- legacy exports:
  - `GOSM/example/Figures/Compare_true_vs_imag_k_loss__ALL_results_from_steady-state_and_instantaneous.jpg`
  - `GOSM/example/Figures/Sensitivity_Analysis__ALL_results_from_steady-state_and_instantaneous.jpg`
  - `GOSM/example/Figures/Sensitivity_Analysis__SOME_results_from_steady-state_and_other_AOHs.jpg`

## Current Reproduction

- sensitivity loader and renderers:
  - `src/stomatal_optimiaztion/domains/gosm/examples/sensitivity_figures.py`
  - `scripts/render_gosm_sensitivity_figures.py`
- manuscript panel renderer:
  - `src/stomatal_optimiaztion/domains/gosm/examples/manuscript_panels.py`
  - `scripts/render_gosm_manuscript_panels.py`
- Plotkit-style specs:
  - `configs/plotkit/gosm/compare_true_vs_imag_figure.yaml`
  - `configs/plotkit/gosm/sensitivity_all_figure.yaml`
  - `configs/plotkit/gosm/sensitivity_some_figure.yaml`
  - `configs/plotkit/gosm/manuscript_panels.yaml`
- validation output bundle:
  - `out/gosm/parity_validation/sensitivity/compare_true_vs_imag/`
  - `out/gosm/parity_validation/sensitivity/sensitivity_all/`
  - `out/gosm/parity_validation/sensitivity/sensitivity_some/`
  - `out/gosm/parity_validation/manuscript/`

## Parity Results

- `compare_true_vs_imag`: legacy frame digest matched
  - expected: `2cd99cde31987687d5b1178e83d1a7554a825be1e416cd083dafd2cec4363195`
  - actual: `2cd99cde31987687d5b1178e83d1a7554a825be1e416cd083dafd2cec4363195`
- `sensitivity_all`: legacy frame digest matched
  - expected: `e935ff35b27a4bb28157e976dc6f4c2145a1195f71b8b0f10d6a779454f5075f`
  - actual: `e935ff35b27a4bb28157e976dc6f4c2145a1195f71b8b0f10d6a779454f5075f`
- `sensitivity_some`: legacy frame digest matched
  - expected: `4ea5026987d6fa5b0dc32857fdec057335a213481b277ba57ef6abe9fdf1c647`
  - actual: `4ea5026987d6fa5b0dc32857fdec057335a213481b277ba57ef6abe9fdf1c647`
- `manuscript_panels`: all nine panel digests matched the bounded kernel-derived reference set
  - `overall_passed: true`

## Interpretation

The remaining root `GOSM` example workflows are now parity-complete under the Plotkit-style reproduction rule. The rendered figures are not MATLAB-pixel-identical because publication tokens intentionally change typography and color treatment, but the numeric payloads, panel layout contracts, export bundles, and atomic manuscript-panel curves all match the bounded legacy references.
