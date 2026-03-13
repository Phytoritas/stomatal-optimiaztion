# Gap Register

| ID | Gap | Impact | Required Artifact |
| --- | --- | --- | --- |
| GAP-002 | THORP compatibility imports still miss the legacy equation-registry module surface | Traceability helpers exist, but callers that expect the explicit `equation_registry` module path still have no migrated seam | next THORP module spec |
| GAP-008 | THORP migrated seams are still validated primarily by unit and seam-level tests | Package-level execution regressions may still hide outside the current harness | package-level smoke validation note |
| GAP-007 | Shared utilities layer is not justified yet | Premature abstraction could create churn | second-domain comparison note |
