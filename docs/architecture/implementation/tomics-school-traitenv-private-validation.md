# TOMICS school traitenv private validation path

## Why this exists

The committed public traitenv snapshot remains intentionally conservative.

- `configs/data/tomics_multidataset_candidates/traitenv_candidate_registry.json` keeps `school_trait_bundle__yield` review-only.
- the literature dry-matter seam stays visible on review and diagnostic surfaces.
- public promotion logic must not silently turn the school dataset runnable.

This implementation adds a separate **private reviewed derivative path** for the cloned traitenv bundle under `out/private-data/traitenv`.

## Official workflow status

For issue `#265`, the repository treats this path as **manual-reviewed derivative workflow by default**.

- the repo-local helper is kept as a bounded preparation utility
- it is not the source of truth for public promotion eligibility
- it does not mutate the committed public registry snapshot
- it does not replace the incumbent TOMICS gate policy

This is intentionally more conservative than a full source-sync automation policy.

## What the private helper does

`scripts/prepare_traitenv_school_validation.py` reads three school-specific partition tables from the cloned bundle:

- `school_crop_info__metadata`
- `school_greenhouse_environment__environment`
- `school_trait_bundle__yield` from `comparison_daily`

It then derives:

1. a KNU-compatible forcing CSV
2. a KNU-compatible cumulative harvested DW CSV
3. a dataset overlay payload for `validation.datasets.items`
4. generated configs for:
   - current-vs-promoted factorial
   - harvest-family factorial
   - multidataset harvest factorial
   - multidataset promotion gate

When the cloned `school_crop_info__metadata` surface only contains notes or mixed review rows, the helper falls back to the raw tomato common workbook:

- `40_작업·재배정보/토마토_재배정보_공통.xlsx`

That fallback supplies:

- crop start / end
- floor-area basis metadata
- plant density

## Contract semantics

The helper does **not** edit the committed public registry snapshot.

- without `--approve-runnable-contract`, the generated overlay still carries `dry_matter_conversion.review_only = true`
- with `--approve-runnable-contract`, the overlay clears only that blocker because the helper also supplies the missing runtime contract fields:
  - `forcing_path`
  - `observed_harvest_path`
  - `date_column`
  - `measured_cumulative_column`
  - `reporting_basis`
  - `validation_start` / `validation_end`
  - sanitized fixture pair

This keeps the original rule intact: review-only FWDW conversion never becomes runnable by accident.

Even with `--approve-runnable-contract`, the effect remains scoped to the generated **private overlay and generated private configs** under the chosen output root.

- the committed public candidate snapshot remains review-only
- public `promotion_surface.csv` semantics remain unchanged
- this helper run must not be cited as a public promotion-clear signal by itself

## Source mapping

- basis metadata comes from `school_crop_info__metadata` when it already carries the runtime fields
- otherwise basis metadata falls back to `40_작업·재배정보/토마토_재배정보_공통.xlsx`
- greenhouse forcing comes from `school_greenhouse_environment__environment`
- harvested fresh-weight signal comes from `school_trait_bundle__yield` in `comparison_daily`
- cumulative harvested DW is derived with the explicit literature ratio configured in the helper

For repeated local worktree runs, the cloned bundle can carry a local origin manifest:

- `out/private-data/traitenv/.source_origin.json`

This manifest records:

- `source_traitenv_root`
- `source_raw_repo_root`

If present, the helper can run from the default cloned path and still recover the raw workbook fallback automatically.

The helper currently also supports an adjacent `outputs/traitenv` layout inference. That legacy convenience is one reason the repo does **not** yet promote this path to a stricter source-sync automation policy.

## Expected workflow

```powershell
poetry run python scripts/prepare_traitenv_school_validation.py --approve-runnable-contract
poetry run python scripts/run_tomics_current_vs_promoted_factorial.py --config <generated current config> --mode both
poetry run python scripts/run_tomics_knu_harvest_family_factorial.py --config <generated harvest config>
poetry run python scripts/run_tomics_multidataset_harvest_factorial.py --config <generated multidataset config>
poetry run python scripts/run_tomics_multidataset_harvest_promotion_gate.py --config <generated gate config>
```

All generated artifacts stay under the private output root and do not mutate the public review snapshot.

## Reviewed derivative contract

Inputs:

- cloned `traitenv` root, either passed explicitly with `--traitenv-root` or available at `out/private-data/traitenv`
- optional explicit `--raw-repo-root`
- if no explicit raw root is passed, `.source_origin.json` may recover `source_raw_repo_root`
- season and treatment selectors
- explicit `--approve-runnable-contract` only when the operator intends to clear the review-only blocker in the generated private overlay

Required metadata:

- greenhouse environment rows for the selected season
- school yield comparison rows for the selected season/treatment
- crop start/end, area, and plant density from processed metadata or the raw common workbook fallback

Outputs:

- private forcing CSV
- private cumulative harvested DW CSV
- private overlay YAML/JSON
- private manifest JSON
- generated configs rooted under the same private output root

Blockers that remain in force:

- without explicit approval, `review_only_dry_matter_conversion` stays active
- the committed public registry remains review-only regardless of local helper output
- no helper run widens public promotion eligibility or replaces the incumbent TOMICS gate

Runnable means only this:

- the generated **private** overlay carries the missing runtime contract fields and clears the review-only blocker because the operator explicitly approved that private derivative contract

Runnable does **not** mean:

- the public registry became promotable
- the repository default changed from manual-reviewed to automated source-sync
- issue `#265` is complete without a separate branch/PR hygiene pass
