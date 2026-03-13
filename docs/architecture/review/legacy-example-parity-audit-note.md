# Legacy Example Parity Audit Note

## Purpose

Open a new workflow-reproduction wave for the original MATLAB example and figure scripts after the root `THORP`, `GOSM`, and `TDGM` model-kernel parity audit closed.

## Scope

- original MATLAB example and figure assets under:
  - `THORP/example/THORP_code_forcing_outputs_plotting/`
  - `GOSM/example/`
  - `TDGM/example/Supplementary Code __ TDGM Offline Simulations/`
  - `TDGM/example/Supplementary Code __THORP_code_v1.4/`
- current migrated Python runtime surfaces under:
  - `src/stomatal_optimiaztion/domains/thorp/`
  - `src/stomatal_optimiaztion/domains/gosm/`
  - `src/stomatal_optimiaztion/domains/tdgm/`
  - repo-level plotting scripts under `scripts/`

Out of scope for this note:
- reopening closed model-kernel gaps already covered by slices `001-095`
- pixel-perfect reproduction of legacy fonts, colors, or MATLAB renderer defaults

## Parity Rule

The example wave now targets workflow parity, not MATLAB-style pixel parity.

Because the new figure layer will use Plotkit-style publication tokens, figure equivalence should be judged by:
- numeric series parity against legacy example data or recomputed legacy outputs
- panel count, panel order, axis-scale, and axis-limit parity
- series ordering, overlay semantics, and legend semantics
- reproducible output bundles containing data, spec, resolved spec, metadata, and exports

This means a Plotkit-styled figure can be parity-complete even when typography and line colors differ from the original MATLAB export.

## Inventory

### Root THORP example assets

Primary MATLAB entrypoints:
- `PLOT_data.m`
- `Simulations_and_additional_code_to_plot/PLOT_data_*.m`

Reference figure assets found in the legacy workspace:
- `Figures/Main Text Figs/FIGURE_1.png`
- `Figures/Main Text Figs/FIGURE_2_Control_(H_Z_LAI_etc).jpg`
- `Figures/Main Text Figs/FIGURE_3_Control_and_reduced_Precip_(MF).jpg`
- `Figures/Main Text Figs/FIGURE_4_Control_and_reduced_Precip_(allocation_fractions).jpg`
- `Figures/Main Text Figs/FIGURE_5_GW_(Z_RMF_fraction_E_from_below_2_m).jpg`
- `Figures/Main Text Figs/FIGURE_6_Control_and_eCO2_and_Light_limited_(MF).jpg`

Current repo status:
- the root `thorp` runtime is migrated
- the repo does not yet provide a root `THORP` example-data builder or Plotkit-style figure workflow

### Root GOSM example assets

Primary MATLAB entrypoints:
- `Growth_Opt_Stomata_plot_example.m`
- `PLOT_sensitivity_analyses.m`
- `PLOT_true_vs_imag_conductance_loss.m`
- `Inkscape_figure_plots.m`

Reference data and figure assets found in the legacy workspace:
- `Example_Growth_Opt__control.mat`
- `Growth_Opt_Stomata__test_sensitivity__*.mat`
- `Figures/Example_Growth_Opt__P_soil=0.jpeg`
- `Figures/Figure5.png`
- `Figures/Sensitivity_Analysis__ALL_results_from_steady-state_and_instantaneous.jpg`
- `Figures/Sensitivity_Analysis__SOME_results_from_steady-state_and_other_AOHs.jpg`
- `Figures/Compare_true_vs_imag_k_loss__ALL_results_from_steady-state_and_instantaneous.jpg`

Current repo status:
- the root `gosm` runtime is migrated
- the repo does not yet provide a root `GOSM` example-data builder, manuscript-figure builder, or Plotkit-style publication figure workflow

### Root TDGM example assets

Primary MATLAB entrypoints:
- `Supplementary Code __ TDGM Offline Simulations/ANALYSIS_*.m`
- `Supplementary Code __ TDGM Offline Simulations/PLOT_Poorter_SMF.m`
- `Supplementary Code __THORP_code_v1.4/PLOT_data.m`
- `Supplementary Code __THORP_code_v1.4/Simulations_and_code_to_plot/PLOT_*.m`

Current repo status:
- the root `tdgm` runtime and THORP-G helper wave are migrated
- the repo does not yet provide supplementary-analysis runners, reference-data adapters, or Plotkit-style TDGM/THORP-G figure workflows

## Findings

1. The earlier MATLAB source parity audit was correct for model kernels, but it explicitly left the example and manuscript figure workflows outside scope.
2. The user has now reopened the program with a broader workflow-reproduction goal, so the gap register must distinguish model parity from example parity.
3. `GOSM` is the best first bounded example slice because it has both a reusable control `.mat` artifact and a legacy figure export that can anchor numeric-series parity.

## Open Gaps

1. Root `GOSM` control example figure workflow: `Growth_Opt_Stomata_plot_example.m` plus `Example_Growth_Opt__control.mat`.
2. Root `GOSM` sensitivity and manuscript figure workflows: `PLOT_sensitivity_analyses.m`, `PLOT_true_vs_imag_conductance_loss.m`, and `Inkscape_figure_plots.m`.
3. Root `THORP` example figure workflows under `PLOT_data.m` and `PLOT_data_*.m`.
4. Root `TDGM` supplementary analysis and THORP-G figure workflows under both example directories.

## Next Actions

1. land a bounded root `GOSM` control-example slice first, using Plotkit-style tokens and spec-first exports
2. validate parity numerically against the legacy `.mat` payload rather than relying on pixel identity
3. keep `THORP` and `TDGM` example workflows blocked until the first GOSM publication-figure slice establishes the reusable pattern
