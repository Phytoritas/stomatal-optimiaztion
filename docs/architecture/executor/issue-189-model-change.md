## Why
- The example parity audit reopened `G-096`: the repo still cannot reproduce the root GOSM control example figure workflow.
- The first example slice should prove that migrated `gosm` kernels can regenerate the legacy control payload and export a publication-style figure bundle.
- Figure validation should target numeric series parity and reproducible outputs, not MATLAB pixel identity.

## Scope
- add a root `GOSM` control-example payload builder on top of migrated `gosm.model` kernels
- add a Plotkit-style YAML spec and publication tokens
- add a repo-level script that exports PNG, PDF, CSV, spec, resolved spec, tokens, and metadata
- add regression tests for legacy digest parity and CLI rendering

## Validation
- compare regenerated control-example series against the legacy `Example_Growth_Opt__control.mat` payload
- render a full bundle to disk and verify the export set
- keep `pytest` and `ruff` green

## Comparison target
- `C:\\Users\\yhmoo\\OneDrive\\Phytoritas\\00. Stomatal Optimization\\GOSM\\example\\Growth_Opt_Stomata_plot_example.m`
- `C:\\Users\\yhmoo\\OneDrive\\Phytoritas\\00. Stomatal Optimization\\GOSM\\example\\Example_Growth_Opt__control.mat`
- `C:\\Users\\yhmoo\\OneDrive\\Phytoritas\\00. Stomatal Optimization\\GOSM\\example\\Figures\\Example_Growth_Opt__P_soil=0.jpeg`
