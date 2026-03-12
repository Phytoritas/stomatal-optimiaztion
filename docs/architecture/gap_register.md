# Gap Register

| ID | Gap | Impact | Required Artifact |
| --- | --- | --- | --- |
| GAP-002 | TOMATO migration depth is still shallow beyond the partitioning package, package-local runner, and bounded `TomatoModel` surface | package-level pipeline coupling and shared core helpers can still hide legacy assumptions | next TOMATO module spec |
| GAP-008 | THORP migrated seams are still validated primarily by unit and seam-level tests | Package-level execution regressions may still hide outside the current harness | package-level smoke validation note |
| GAP-007 | Shared utilities layer is not justified yet | Premature abstraction could create churn | second-domain comparison note |
