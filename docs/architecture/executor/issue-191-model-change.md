## Why
- `G-097` is still open: the repo cannot yet reproduce the remaining root `GOSM` sensitivity and manuscript figure workflows from the legacy MATLAB example directory.
- The next example slice should synchronize the legacy sensitivity/manuscript figures with Plotkit-style publication bundles while preserving numeric-series parity.
- Parity should be judged by numeric series, panel order, axis semantics, and reproducible bundle outputs rather than MATLAB pixel identity.

## Scope
- migrate the root `GOSM` sensitivity figure workflows built from `PLOT_true_vs_imag_conductance_loss.m`, `PLOT_sensitivity_analyses.m`, and the paired atomic manuscript panels from `Inkscape_figure_plots.m`
- add Plotkit-style YAML specs and publication tokens for the resulting figure bundles
- add repo-level rendering scripts that export PNG, PDF, CSV, spec, resolved spec, tokens, and metadata
- add regression tests for legacy `.mat` parity, figure bundle exports, and CLI entrypoints

## Validation
- compare grouped numeric payloads against the legacy `Growth_Opt_Stomata__test_sensitivity__*.mat` payloads
- render full bundles to disk and verify the export set plus metadata parity status
- keep `pytest` and `ruff` green

## Comparison target
- `C:\\Users\\yhmoo\\OneDrive\\Phytoritas\\00. Stomatal Optimization\\GOSM\\example\\PLOT_true_vs_imag_conductance_loss.m`
- `C:\\Users\\yhmoo\\OneDrive\\Phytoritas\\00. Stomatal Optimization\\GOSM\\example\\PLOT_sensitivity_analyses.m`
- `C:\\Users\\yhmoo\\OneDrive\\Phytoritas\\00. Stomatal Optimization\\GOSM\\example\\Inkscape_figure_plots.m`
- `C:\\Users\\yhmoo\\OneDrive\\Phytoritas\\00. Stomatal Optimization\\GOSM\\example\\Figures\\Compare_true_vs_imag_k_loss__ALL_results_from_steady-state_and_instantaneous.jpg`
- `C:\\Users\\yhmoo\\OneDrive\\Phytoritas\\00. Stomatal Optimization\\GOSM\\example\\Figures\\Sensitivity_Analysis__ALL_results_from_steady-state_and_instantaneous.jpg`
- `C:\\Users\\yhmoo\\OneDrive\\Phytoritas\\00. Stomatal Optimization\\GOSM\\example\\Figures\\Sensitivity_Analysis__SOME_results_from_steady-state_and_other_AOHs.jpg`
