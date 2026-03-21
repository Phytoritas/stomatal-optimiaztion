# TOMICS KNU Data Contract

## Purpose

Issue `#239` / module `118` adds a reproducible private-data contract so KNU fair-validation runs can find the raw files without committing them.

## Resolution order

The loader resolves KNU files from either:

1. repo-local paths such as `data/forcing/KNU_Tomato_Env.CSV` and `data/forcing/tomato_validation_data_yield_260321.xlsx`
2. a private root declared by `PHYTORITAS_PRIVATE_DATA_ROOT`
3. a contract template under `configs/data/knu_private_data_contract.template.yaml`

The raw files remain untracked and unmodified.

## Manifest contract

Every actual-data run writes:

- `out/tomics/validation/knu/longrun/data_contract_manifest.json`

This manifest records:

- source path used
- whether the source was `repo_local` or `private_root`
- reporting basis
- plants per square meter
- observation columns
- time coverage
- parser assumptions

## Sanitized fixture path

CI and local tests use sanitized fixtures under:

- `tests/fixtures/knu_sanitized/`

These files exercise the full loader and validation path without exposing the private KNU raw data.
