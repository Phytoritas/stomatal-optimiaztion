# Gap Register

| ID | Gap | Impact | Required Artifact |
| --- | --- | --- | --- |
| GAP-002 | THORP namespace wrappers are still incomplete after the restored equation-registry path | Compatibility callers may still miss legacy `utils`, `io`, `model`, or `params` package-level import surfaces | next THORP namespace-wrapper module spec |
| GAP-008 | THORP migrated seams are still validated primarily by unit and seam-level tests | Package-level execution regressions may still hide outside the current harness | package-level smoke validation note |
| GAP-007 | Shared utilities layer is not justified yet | Premature abstraction could create churn | second-domain comparison note |
