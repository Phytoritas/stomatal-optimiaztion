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
- the repo now provides a root `THORP` example-data adapter plus Plotkit-style figure workflows for the five main-text figures

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
- the repo now provides root `GOSM` control, sensitivity, and manuscript Plotkit-style figure workflows with digest-locked metadata

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
2. The user reopened the program with a broader workflow-reproduction goal, so the gap register had to distinguish model parity from example parity.
3. The root `GOSM` wave provided the first reusable Plotkit-style figure-bundle contract, and root `THORP` confirmed that the contract is now cross-domain rather than GOSM-local.
4. Root `THORP` example parity is now closed against the real legacy `.mat` payloads plus the empirical tables embedded in the original MATLAB scripts.

## Open Gaps

1. Root `TDGM` supplementary analysis and THORP-G figure workflows under both example directories.

## Next Actions

1. `slice 097` closed the root `GOSM` control-example figure workflow with Plotkit-style, spec-first exports
2. `slice 098` closed the remaining root `GOSM` sensitivity and manuscript figure workflows
3. `slice 099` closed the root `THORP` main-text example figure workflows with real legacy-data digest locking and visual spot checks
4. move next to root `TDGM`
