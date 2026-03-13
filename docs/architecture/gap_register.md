# Gap Register

| ID | Gap | Impact | Required Artifact |
| --- | --- | --- | --- |
| GAP-002 | The next bounded seam after the completed `load-cell-data` source wave is not yet selected | Recursive slice flow can stall now that the remaining `load-cell-data/src` viewer builder is migrated but the next cross-domain target is still unset | workspace-audit delta plus next module spec |
| GAP-008 | THORP migrated seams are still validated primarily by unit and seam-level tests | Package-level execution regressions may still hide outside the current harness | package-level smoke validation note |
| GAP-007 | Shared utilities layer is not justified yet | Premature abstraction could create churn | second-domain comparison note |
