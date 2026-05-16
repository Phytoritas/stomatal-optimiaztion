# Rootzone RZI Reference Contract

Dataset2 contains LC4/LC5 drought-side moisture, EC, and tensiometer observations. It does not by itself provide a control reference for LC1-LC3.

Goal 3A.5 therefore uses Dataset1 LC1-LC6 moisture as the primary control/drought reference when available:

- `RZI_theta_paired = clip(1 - theta_lc4 / (theta_lc1 + eps), 0, 1)`
- `RZI_theta_group = clip(1 - theta_drought_group / (theta_control_group + eps), 0, 1)`
- `RZI_main` prefers paired LC4-vs-LC1, then group drought-vs-control, otherwise unavailable.

Dataset2 tensiometer values remain drought-group diagnostics. They are not extrapolated to all loadcells.
