## Why
- `G-098` is still open: the repo cannot yet reproduce the root `THORP` example figure workflows from the migrated runtime surfaces and legacy `.mat` outputs.
- The next bounded slice should synchronize the legacy main-text `THORP` example figures with Plotkit-style publication bundles while preserving numeric-series parity.
- Figure equivalence should be judged by numeric series, panel order, axis semantics, and reproducible bundle outputs rather than MATLAB pixel identity.

## Scope
- migrate the root `THORP` example-data adapter needed to reproduce the main-text figure workflows under `THORP/example/THORP_code_forcing_outputs_plotting/`
- add Plotkit-style YAML specs and publication tokens for the resulting figure bundles
- add repo-level rendering scripts that export PNG, PDF, CSV, spec, resolved spec, tokens, and metadata
- add regression tests for legacy `.mat` parity, figure bundle exports, and CLI entrypoints

## Validation
- compare grouped numeric payloads against the legacy `THORP_data_*.mat` payloads used by the MATLAB example scripts
- render full bundles to disk and verify the export set plus metadata parity status
- keep `pytest` and `ruff` green

## Comparison target
- `C:\\Users\\yhmoo\\OneDrive\\Phytoritas\\00. Stomatal Optimization\\THORP\\example\\THORP_code_forcing_outputs_plotting\\Simulations_and_additional_code_to_plot\\PLOT_data_2_Mass_Fractions.m`
- `C:\\Users\\yhmoo\\OneDrive\\Phytoritas\\00. Stomatal Optimization\\THORP\\example\\THORP_code_forcing_outputs_plotting\\Simulations_and_additional_code_to_plot\\PLOT_data_3_Allocation_Fractions.m`
- `C:\\Users\\yhmoo\\OneDrive\\Phytoritas\\00. Stomatal Optimization\\THORP\\example\\THORP_code_forcing_outputs_plotting\\Simulations_and_additional_code_to_plot\\PLOT_data_5_H_Z_LAI_Hv.m`
- `C:\\Users\\yhmoo\\OneDrive\\Phytoritas\\00. Stomatal Optimization\\THORP\\example\\THORP_code_forcing_outputs_plotting\\Simulations_and_additional_code_to_plot\\PLOT_data_6_Z_Ppd_WUE.m`
- `C:\\Users\\yhmoo\\OneDrive\\Phytoritas\\00. Stomatal Optimization\\THORP\\example\\THORP_code_forcing_outputs_plotting\\Simulations_and_additional_code_to_plot\\PLOT_data_8_eCO2_and_light.m`
- `C:\\Users\\yhmoo\\OneDrive\\Phytoritas\\00. Stomatal Optimization\\THORP\\example\\THORP_code_forcing_outputs_plotting\\Figures\\Main Text Figs\\FIGURE_2_Control_(H_Z_LAI_etc).jpg`
- `C:\\Users\\yhmoo\\OneDrive\\Phytoritas\\00. Stomatal Optimization\\THORP\\example\\THORP_code_forcing_outputs_plotting\\Figures\\Main Text Figs\\FIGURE_3_Control_and_reduced_Precip_(MF).jpg`
- `C:\\Users\\yhmoo\\OneDrive\\Phytoritas\\00. Stomatal Optimization\\THORP\\example\\THORP_code_forcing_outputs_plotting\\Figures\\Main Text Figs\\FIGURE_4_Control_and_reduced_Precip_(allocation_fractions).jpg`
- `C:\\Users\\yhmoo\\OneDrive\\Phytoritas\\00. Stomatal Optimization\\THORP\\example\\THORP_code_forcing_outputs_plotting\\Figures\\Main Text Figs\\FIGURE_5_GW_(Z_RMF_fraction_E_from_below_2_m).jpg`
- `C:\\Users\\yhmoo\\OneDrive\\Phytoritas\\00. Stomatal Optimization\\THORP\\example\\THORP_code_forcing_outputs_plotting\\Figures\\Main Text Figs\\FIGURE_6_Control_and_eCO2_and_Light_limited_(MF).jpg`
