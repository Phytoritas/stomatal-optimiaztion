# Gap Register

| ID | Gap | Impact | Required Artifact |
| --- | --- | --- | --- |
| GAP-002 | `load-cell-data` migration depth is still shallow beyond the completed aggregation seam | threshold detection, preprocessing, workflow, and CLI surfaces remain unmigrated, so the third domain boundary is only partially explicit in the staged repo | next load-cell module spec |
| GAP-008 | THORP migrated seams are still validated primarily by unit and seam-level tests | Package-level execution regressions may still hide outside the current harness | package-level smoke validation note |
| GAP-007 | Shared utilities layer is not justified yet | Premature abstraction could create churn | second-domain comparison note |
