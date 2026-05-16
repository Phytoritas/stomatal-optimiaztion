from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, write_json
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_gate_outputs import (
    bool_value,
    write_markdown_table,
)


READINESS_CATEGORIES = [
    "architecture_novelty",
    "actual_data_pipeline",
    "radiation_daynight_et",
    "event_bridged_water_flux",
    "rootzone_rzi",
    "apparent_conductance",
    "latent_allocation_inference",
    "harvest_family_factorial",
    "observation_operator_dmc_0p056",
    "budget_parity",
    "promotion_gate",
    "cross_dataset_gate",
    "plotkit_figures",
    "reproducibility_manifest",
    "paper_claim_safety",
]


def build_new_phytologist_readiness_matrix(
    *,
    promotion_metadata: Mapping[str, Any],
    cross_dataset_metadata: Mapping[str, Any],
    plotkit_manifest_exists: bool,
    rendered_plot_count: int,
    claim_register_exists: bool,
    reproducibility_manifest_exists: bool,
) -> pd.DataFrame:
    def row(
        category: str,
        status: str,
        evidence_path: str,
        limitation: str,
        paper_safe_claim: str,
    ) -> dict[str, object]:
        return {
            "category": category,
            "status": status,
            "evidence_path": evidence_path,
            "limitation": limitation,
            "paper_safe_claim": paper_safe_claim,
        }

    promotion_run = bool_value(promotion_metadata.get("promotion_gate_run"))
    promotion_passed = bool_value(promotion_metadata.get("promotion_gate_passed"))
    cross_run = bool_value(cross_dataset_metadata.get("cross_dataset_gate_run"))
    cross_passed = bool_value(cross_dataset_metadata.get("cross_dataset_gate_passed"))
    dmc_contract_pass = (
        promotion_metadata.get("canonical_fruit_DMC_fraction") == 0.056
        and bool_value(promotion_metadata.get("DMC_fixed_for_2025_2C"))
        and not bool_value(promotion_metadata.get("DMC_sensitivity_enabled"))
        and bool_value(promotion_metadata.get("dry_yield_is_dmc_estimated"))
        and not bool_value(promotion_metadata.get("direct_dry_yield_measured"))
    )
    radiation_contract_pass = (
        promotion_metadata.get("radiation_daynight_primary_source") == "dataset1"
        and promotion_metadata.get("radiation_column_used") == "env_inside_radiation_wm2"
        and not bool_value(promotion_metadata.get("fixed_clock_daynight_primary"))
    )
    latent_contract_pass = (
        not bool_value(promotion_metadata.get("latent_allocation_directly_validated"))
        and not bool_value(promotion_metadata.get("raw_THORP_allocator_used"))
        and bool_value(promotion_metadata.get("THORP_used_as_bounded_prior"), default=True)
    )
    fruit_diameter_contract_pass = (
        not bool_value(promotion_metadata.get("fruit_diameter_p_values_allowed"))
        and not bool_value(promotion_metadata.get("fruit_diameter_allocation_calibration_target"))
        and not bool_value(promotion_metadata.get("fruit_diameter_model_promotion_target"))
    )
    plotkit_status = "pass" if rendered_plot_count > 0 else ("partial" if plotkit_manifest_exists else "blocked")
    rows = [
        row(
            "architecture_novelty",
            "pass",
            "docs/architecture/tomics/harvest_family_architecture.md",
            "Bounded to 2025-2C architecture discrimination.",
            "Harvest-family evaluation separated allocator family, harvest family, and observation operator.",
        ),
        row(
            "actual_data_pipeline",
            "pass",
            "docs/architecture/tomics/tomics_haf_2025_2c_actual_data_pipeline.md",
            "Private raw data are not committed.",
            "We evaluated TOMICS-HAF on the 2025 second cropping cycle as a bounded architecture-discrimination test.",
        ),
        row(
            "radiation_daynight_et",
            "pass" if radiation_contract_pass else "blocked",
            "out/tomics/analysis/haf_2025_2c/2025_2c_tomics_haf_metadata.json",
            "Dataset1 radiation is the primary day/night source.",
            "Day/night phases were radiation-defined from Dataset1 env_inside_radiation_wm2.",
        ),
        row(
            "event_bridged_water_flux",
            "pass",
            "docs/architecture/tomics/tomics_haf_2025_2c_production_observer_export.md",
            "Water flux bridge is observer-derived.",
            "Event-bridged water flux supported observer construction.",
        ),
        row(
            "rootzone_rzi",
            "pass",
            "docs/architecture/tomics/tomics_haf_2025_2c_production_observer_export.md",
            "RZI is an observer feature, not direct root allocation measurement.",
            "Rootzone RZI supported observer-level stress diagnostics.",
        ),
        row(
            "apparent_conductance",
            "pass",
            "docs/architecture/tomics/tomics_haf_2025_2c_production_observer_export.md",
            "Apparent conductance is observer-level inference.",
            "Apparent conductance supported observer-level water-flux diagnostics.",
        ),
        row(
            "latent_allocation_inference",
            "pass" if latent_contract_pass else "blocked",
            "out/tomics/validation/latent-allocation/haf_2025_2c/latent_allocation_metadata.json",
            "Latent allocation is not direct allocation validation.",
            "Latent allocation was observer-supported inference, not direct allocation validation.",
        ),
        row(
            "harvest_family_factorial",
            "pass" if bool_value(promotion_metadata.get("harvest_family_factorial_run")) else "blocked",
            "out/tomics/validation/harvest-family/haf_2025_2c/harvest_family_rankings.csv",
            "Single 2025-2C dataset only.",
            "Harvest-family evaluation identified candidates for future testing.",
        ),
        row(
            "observation_operator_dmc_0p056",
            "pass" if dmc_contract_pass else "blocked",
            "out/tomics/validation/harvest-family/haf_2025_2c/observation_operator_dmc_0p056_audit.csv",
            "Dry yield is DMC-estimated, not direct dry mass.",
            "For 2025-2C, DMC was fixed at 0.056.",
        ),
        row(
            "budget_parity",
            "partial",
            "docs/architecture/tomics/harvest_budget_parity_2025_2c.md",
            "Knob-count and hidden-calibration-budget parity only; wall-clock parity was not evaluated.",
            "Budget parity was defined as knob-count and hidden-calibration-budget parity.",
        ),
        row(
            "promotion_gate",
            "pass" if promotion_passed else ("blocked" if promotion_run else "not_run"),
            "out/tomics/validation/promotion-gate/haf_2025_2c/promotion_gate_metadata.json",
            "Promotion remains blocked unless every hard gate passes.",
            "Promotion gate was executed; pass/fail is determined by the gate outputs.",
        ),
        row(
            "cross_dataset_gate",
            "pass" if cross_passed else ("blocked" if cross_run else "not_run"),
            "out/tomics/validation/multi-dataset/haf_2025_2c/cross_dataset_metadata.json",
            "At least two compatible measured datasets are required for promotion.",
            "Cross-dataset gate was executed as a safeguard.",
        ),
        row(
            "plotkit_figures",
            plotkit_status,
            "out/tomics/figures/haf_2025_2c/plotkit_render_manifest.csv",
            "Manifest-only evidence is partial until rendered PNGs exist.",
            "Plotkit figure specs were validated or explicitly manifested.",
        ),
        row(
            "reproducibility_manifest",
            "pass" if reproducibility_manifest_exists else "blocked",
            "out/tomics/validation/harvest-family/haf_2025_2c/harvest_family_reproducibility_manifest.json",
            "Private raw files are hashed or recorded without copying.",
            "A reproducibility manifest records config, input, and output provenance.",
        ),
        row(
            "paper_claim_safety",
            "pass" if claim_register_exists and fruit_diameter_contract_pass else "blocked",
            "out/tomics/validation/promotion-gate/haf_2025_2c/claim_register.csv",
            "Unsafe claims remain forbidden unless future evidence changes gate outputs.",
            "A claim register separates allowed, conditional, and forbidden claims.",
        ),
    ]
    return pd.DataFrame(rows)


def write_new_phytologist_readiness_matrix(
    *,
    output_root: Path,
    promotion_metadata: Mapping[str, Any],
    cross_dataset_metadata: Mapping[str, Any],
    plotkit_manifest_exists: bool,
    rendered_plot_count: int,
    claim_register_exists: bool,
    reproducibility_manifest_exists: bool,
) -> dict[str, str]:
    output_root = ensure_dir(output_root)
    frame = build_new_phytologist_readiness_matrix(
        promotion_metadata=promotion_metadata,
        cross_dataset_metadata=cross_dataset_metadata,
        plotkit_manifest_exists=plotkit_manifest_exists,
        rendered_plot_count=rendered_plot_count,
        claim_register_exists=claim_register_exists,
        reproducibility_manifest_exists=reproducibility_manifest_exists,
    )
    csv_path = output_root / "new_phytologist_readiness_matrix.csv"
    md_path = output_root / "new_phytologist_readiness_matrix.md"
    json_path = output_root / "new_phytologist_readiness_metadata.json"
    frame.to_csv(csv_path, index=False)
    write_markdown_table(
        md_path,
        frame,
        title="HAF 2025-2C New Phytologist Readiness Matrix",
        intro_lines=[
            "This matrix is paper-readiness evidence, not a promotion claim.",
            "Blocked promotion or cross-dataset categories prevent a final readiness claim.",
        ],
    )
    status_counts = frame["status"].value_counts().to_dict()
    ready_for_new_phytologist_claim = not frame["status"].isin(["blocked", "not_run", "partial"]).any()
    write_json(
        json_path,
        {
            "ready_for_new_phytologist_claim": bool(ready_for_new_phytologist_claim),
            "status_counts": {str(key): int(value) for key, value in status_counts.items()},
            "universal_generalization_claim_allowed": False,
            "promotion_gate_status": promotion_metadata.get("promotion_gate_status"),
            "cross_dataset_gate_status": cross_dataset_metadata.get("cross_dataset_gate_status"),
        },
    )
    return {
        "new_phytologist_readiness_matrix_csv": str(csv_path),
        "new_phytologist_readiness_matrix_md": str(md_path),
        "new_phytologist_readiness_metadata_json": str(json_path),
    }


__all__ = [
    "READINESS_CATEGORIES",
    "build_new_phytologist_readiness_matrix",
    "write_new_phytologist_readiness_matrix",
]
