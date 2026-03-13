# Module Spec: Slice 098 GOSM Sensitivity And Manuscript Figure Workflows

## Goal

Reproduce the remaining root `GOSM` example plotting workflows from the original MATLAB example directory with Plotkit-style, spec-first figure bundles.

## Source

- `GOSM/example/PLOT_true_vs_imag_conductance_loss.m`
- `GOSM/example/PLOT_sensitivity_analyses.m`
- `GOSM/example/Inkscape_figure_plots.m`
- `GOSM/example/Growth_Opt_Stomata__test_sensitivity__*.mat`
- `GOSM/example/Figures/Compare_true_vs_imag_k_loss__ALL_results_from_steady-state_and_instantaneous.jpg`
- `GOSM/example/Figures/Sensitivity_Analysis__ALL_results_from_steady-state_and_instantaneous.jpg`
- `GOSM/example/Figures/Sensitivity_Analysis__SOME_results_from_steady-state_and_other_AOHs.jpg`

## Target

- `src/stomatal_optimiaztion/domains/gosm/examples/sensitivity_figures.py`
- `src/stomatal_optimiaztion/domains/gosm/examples/manuscript_panels.py`
- `scripts/render_gosm_sensitivity_figures.py`
- `scripts/render_gosm_manuscript_panels.py`
- `configs/plotkit/gosm/compare_true_vs_imag_figure.yaml`
- `configs/plotkit/gosm/sensitivity_all_figure.yaml`
- `configs/plotkit/gosm/sensitivity_some_figure.yaml`
- `configs/plotkit/gosm/manuscript_panels.yaml`
- `tests/test_gosm_sensitivity_figures.py`
- `tests/test_gosm_manuscript_panels.py`

## Requirements

1. read the legacy `.mat` sensitivity payloads and re-render the three root `GOSM` sensitivity figures with Plotkit-style specs and tokens
2. export each figure bundle as PNG, PDF, CSV, spec copy, resolved spec, tokens copy, and metadata
3. regenerate the atomic manuscript panels from migrated `gosm` kernels and export both overview plus per-panel outputs
4. lock numeric parity with digest summaries so legacy-folder validation can report `passed=true`

## Non-Goals

- pixel-perfect reproduction of MATLAB typography or colors
- rebuilding the upstream sensitivity `.mat` payloads from scratch
- moving into root `THORP` or `TDGM` example workflows

## Validation

1. compare long-form sensitivity frames against fixed legacy digests from the real legacy `.mat` payloads
2. compare manuscript panel curves against fixed digests from the migrated kernel outputs
3. render real bundles to disk and verify metadata parity flags
4. keep `pytest` and `ruff` green
