from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, Mapping):
        return {str(key): value for key, value in raw.items()}
    return {}


def _finite(raw: object, *, default: float) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(value):
        return float(default)
    return float(value)


def _text(raw: object, *, default: str) -> str:
    if raw is None:
        return str(default)
    if isinstance(raw, bool):
        return "on" if raw else "off"
    return str(raw).strip()


SUPPORTED_FRUIT_STRUCTURE_MODES = {
    "tomsim_truss_cohort",
    "tomgro_age_class",
    "vanthoor_fixed_boxcar",
}
SUPPORTED_FRUIT_PARTITION_MODES = {
    "legacy_sink_exact",
    "tomsim_relative_sink",
    "dekoning_potential_growth_competition",
}
SUPPORTED_VEGETATIVE_DEMAND_MODES = {
    "tomsim_constant_wholecrop",
    "dekoning_vegetative_unit",
    "tomgro_dynamic_age",
}
SUPPORTED_RESERVE_BUFFER_MODES = {
    "off",
    "tomsim_storage_pool",
    "vanthoor_carbohydrate_buffer",
}
SUPPORTED_FRUIT_FEEDBACK_MODES = {
    "off",
    "tomgro_abort_proxy",
    "dekoning_source_demand_abort_proxy",
}
SUPPORTED_SLA_MODES = {
    "derived_not_driver",
    "tomgro_independent_driver",
    "seasonal_empirical_proxy",
}
SUPPORTED_MAINTENANCE_MODES = {
    "fixed",
    "rgr_adjusted",
    "buffer_linked",
    "nsclimited_proxy",
}
SUPPORTED_CANOPY_GOVERNOR_MODES = {
    "off",
    "lai_band",
    "lai_band_plus_leaf_floor",
}
SUPPORTED_ROOT_REPRESENTATION_MODES = {
    "implicit_small_root",
    "stem_root_lumped_vanthoor",
    "bounded_explicit_root",
}
SUPPORTED_THORP_ROOT_CORRECTION_MODES = {
    "off",
    "bounded",
    "bounded_hysteretic",
}
SUPPORTED_TEMPORAL_COUPLING_MODES = {
    "daily_alloc",
    "hourly_source_daily_alloc",
    "buffered_daily",
}
SUPPORTED_ALLOCATION_SCHEMES = {"3pool", "4pool"}


@dataclass(frozen=True, slots=True)
class ResearchTraceRow:
    source_family: str
    source_file: str
    page_or_equation: str
    exact_reference: str
    original_symbols: str
    normalized_repo_symbols: str
    units: str
    validated_domain: str
    implementation_target: str
    status: str
    rationale: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


TRACEABILITY_ROWS: tuple[ResearchTraceRow, ...] = (
    ResearchTraceRow(
        source_family="Kuijpers",
        source_file="Kuijpers et al. - 2019 - Model selection with a common structure Tomato crop growth models.pdf",
        page_or_equation="p. 252, Eq. (3) and Eq. (5)",
        exact_reference="Common structure with xA assimilate buffer, xS biomass states, and p/gr/g/m/h blocks.",
        original_symbols="xA, xS, p, gr, g, m, h1, h2",
        normalized_repo_symbols="assimilate_buffer_g, biomass_leaf_g, biomass_stem_root_g, biomass_fruit_g, p, gr, g, m, h1, h2",
        units="model dependent; normalized in code to g CH2O or g DM per m2",
        validated_domain="Architectural synthesis across tomato crop models; not a direct cultivar calibration.",
        implementation_target="src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/common_structure.py",
        status="research-only",
        rationale="Scaffold for architecture study and diagnostics, not a shipped tomato allocation law by itself.",
    ),
    ResearchTraceRow(
        source_family="Heuvelink/TOMSIM",
        source_file="Heuvelink - 1996 - Tomato growth and yield quantitative analysis and synthesis.pdf",
        page_or_equation="Ch. 5.7, pp. 229-233",
        exact_reference="Relative sink-strength partitioning over one common assimilate pool.",
        original_symbols="S_i, sum(S_i)",
        normalized_repo_symbols="S_fr_g_d, S_veg_g_d, alloc_frac_fruit",
        units="g DM d^-1 and fraction",
        validated_domain="Greenhouse tomato crops used in the TOMSIM thesis comparisons.",
        implementation_target="src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/tomics_policy.py",
        status="shipped default",
        rationale="Current stable fruit anchoring remains the safe tomato-first baseline.",
    ),
    ResearchTraceRow(
        source_family="Heuvelink/TOMSIM",
        source_file="Heuvelink - 1996 - Tomato growth and yield quantitative analysis and synthesis.pdf",
        page_or_equation="Ch. 5.7 general discussion; thesis summary on TOMGRO storage weakness",
        exact_reference="Absence of an assimilate storage pool is a TOMGRO weakness; excess supply should not vanish.",
        original_symbols="storage pool / reserve pool conceptual statement",
        normalized_repo_symbols="reserve_pool_g_m2, reserve_fill_g_m2, reserve_draw_g_m2",
        units="g CH2O m^-2",
        validated_domain="Tomato greenhouse source-sink studies; exact storage dynamics not calibrated in current repo.",
        implementation_target="src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/reserve_buffer.py",
        status="research-only",
        rationale="Explicit reserve seam is screened as opt-in only.",
    ),
    ResearchTraceRow(
        source_family="Vanthoor",
        source_file="Vanthoor 2011 electronic appendix (Zotero item SIZ3ZU3W / attachment CKLNUS4Q; repo-local ...yiel 1.pdf resolves to appendix text)",
        page_or_equation="appendix p. 4 Eq. (2)",
        exact_reference="Cdot_Buf = MC_AirBuf - MC_BufFruit - MC_BufLeaf - MC_BufStem - MC_BufAir.",
        original_symbols="CBuf, MCAirBuf, MCBufFruit, MCBufLeaf, MCBufStem, MCBufAir",
        normalized_repo_symbols="buffer_pool_g_m2, buffer_fill_g_m2, buffer_draw_fruit_g_m2, buffer_draw_leaf_g_m2, buffer_draw_stem_g_m2, growth_respiration_buffer_g_m2",
        units="mg CH2O m^-2 s^-1 in source; normalized to g CH2O per step",
        validated_domain="Vanthoor greenhouse tomato model; appendix functions calibrated mainly around greenhouse canopy temperatures.",
        implementation_target="src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/reserve_buffer.py",
        status="research-only",
        rationale="Best exact greenhouse buffer equation in the local corpus, but too coupled for silent promotion to default.",
    ),
    ResearchTraceRow(
        source_family="TOMGRO",
        source_file="J. W. Jones et al. - 1991 - A DYNAMIC TOMATO GROWTH AND YIELD MODEL (TOMGRO).pdf",
        page_or_equation="pp. 665-666 Eq. (15), Eq. (19), Eq. (20)-(23)",
        exact_reference="DEMAND = Ldem + Sdem + Fdem; SUPPLY = E*(P-Mresp)*(1-Proot); actual growth scales by Rc when supply limited.",
        original_symbols="DEMAND, SUPPLY, Rc, gF(i), gL(i), gS(i)",
        normalized_repo_symbols="demand_g_d, supply_g_d, supply_demand_ratio, fruit_abort_fraction",
        units="g tissue m^-2 d^-1 or dimensionless",
        validated_domain="Original TOMGRO experiments; no dynamic carbon pool and empirical SLA driver.",
        implementation_target="src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/fruit_feedback.py",
        status="research-only",
        rationale="Used only as an opt-in fruit-feedback proxy under low supply-demand ratio.",
    ),
    ResearchTraceRow(
        source_family="De Koning",
        source_file="De Koning - 1994 - Development and dry matter distribution in glasshouse tomato  a quantitative approach.pdf",
        page_or_equation="pp. 9-10 and p. 193 Eq. 8.2.4",
        exact_reference="Dry matter partitioning is proportional to potential growth rates; long-term potential crop growth = sink formation rate * average potential sink weight.",
        original_symbols="potential growth rates, sink formation rate, average potential sink weight",
        normalized_repo_symbols="fruit_load_proxy, vegetative_vigor_proxy, fruit_abort_fraction",
        units="g d^-1, sinks d^-1",
        validated_domain="Glasshouse tomato crop-control framing; long-season greenhouse reasoning.",
        implementation_target="src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/fruit_feedback.py",
        status="research-only",
        rationale="Supports source-demand fruit-load proxy only in research mode.",
    ),
    ResearchTraceRow(
        source_family="Potkay/THORP",
        source_file="Potkay et al. - 2021 - Coupled whole-tree optimality and xylem hydraulics explain dynamic biomass partitioning.pdf",
        page_or_equation="Eq. 1(a)-(b)",
        exact_reference="Allocation proportional to marginal gain over marginal cost.",
        original_symbols="u_k, gain_k, cost_k",
        normalized_repo_symbols="root_fraction, thorp_root_blend, hysteretic_root_target",
        units="fraction and dimensionless gain-cost proxy",
        validated_domain="Whole-tree hydraulics; not validated as a greenhouse tomato master allocator.",
        implementation_target="src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/root_modes.py",
        status="research-only",
        rationale="Remains a bounded greenhouse root correction family only.",
    ),
)


def traceability_rows() -> list[dict[str, str]]:
    return [row.to_dict() for row in TRACEABILITY_ROWS]


def equation_traceability_rows() -> list[dict[str, str]]:
    return traceability_rows()


@dataclass(frozen=True, slots=True)
class ResearchArchitectureConfig:
    architecture_id: str = "research_default"
    fruit_structure_mode: str = "tomsim_truss_cohort"
    fruit_partition_mode: str = "legacy_sink_exact"
    vegetative_demand_mode: str = "tomsim_constant_wholecrop"
    reserve_buffer_mode: str = "off"
    fruit_feedback_mode: str = "off"
    sla_mode: str = "derived_not_driver"
    maintenance_mode: str = "rgr_adjusted"
    canopy_governor_mode: str = "lai_band"
    root_representation_mode: str = "bounded_explicit_root"
    thorp_root_correction_mode: str = "bounded"
    temporal_coupling_mode: str = "daily_alloc"
    allocation_scheme: str = "4pool"
    wet_root_cap: float = 0.10
    dry_root_cap: float = 0.18
    lai_target_center: float = 2.75
    lai_target_half_band: float = 0.5
    leaf_fraction_of_shoot_base: float = 0.70
    stem_fraction_of_shoot_base: float = 0.30
    min_leaf_fraction_of_shoot: float = 0.58
    max_leaf_fraction_of_shoot: float = 0.85
    leaf_fraction_floor: float = 0.20
    canopy_lai_floor: float = 2.00
    thorp_root_blend: float = 1.0
    hysteresis_gain: float = 0.35
    smoothing_tau_days: float = 1.0
    fruit_abort_threshold: float = 0.82
    fruit_abort_slope: float = 2.5
    reserve_capacity_g_m2: float = 20.0
    reserve_carryover_fraction: float = 1.0
    reserve_min_fraction: float = 0.05
    buffer_capacity_g_m2: float = 20.0
    buffer_min_fraction: float = 0.05
    buffer_release_rate_g_m2_d: float = 10.0
    fruit_load_multiplier: float = 1.0
    boxcar_stage_count: int = 5
    notes: str = ""

    @classmethod
    def from_params(
        cls,
        params: Mapping[str, object] | None,
        *,
        scheme: str | None = None,
    ) -> "ResearchArchitectureConfig":
        flat = _flatten_research_params(params)
        allocation_scheme = _text(flat.get("allocation_scheme", scheme), default=scheme or "4pool")
        leaf_fraction_of_shoot_base = _finite(flat.get("leaf_fraction_of_shoot_base"), default=0.70)
        if "stem_fraction_of_shoot_base" in flat:
            stem_fraction_of_shoot_base = _finite(flat.get("stem_fraction_of_shoot_base"), default=0.30)
        else:
            stem_fraction_of_shoot_base = max(1.0 - leaf_fraction_of_shoot_base, 0.0)
        config = cls(
            architecture_id=_text(flat.get("architecture_id"), default="research_default"),
            fruit_structure_mode=_text(flat.get("fruit_structure_mode"), default="tomsim_truss_cohort"),
            fruit_partition_mode=_text(flat.get("fruit_partition_mode"), default="legacy_sink_exact"),
            vegetative_demand_mode=_text(flat.get("vegetative_demand_mode"), default="tomsim_constant_wholecrop"),
            reserve_buffer_mode=_text(flat.get("reserve_buffer_mode"), default="off"),
            fruit_feedback_mode=_text(flat.get("fruit_feedback_mode"), default="off"),
            sla_mode=_text(flat.get("sla_mode"), default="derived_not_driver"),
            maintenance_mode=_text(flat.get("maintenance_mode"), default="rgr_adjusted"),
            canopy_governor_mode=_text(flat.get("canopy_governor_mode"), default="lai_band"),
            root_representation_mode=_text(flat.get("root_representation_mode"), default="bounded_explicit_root"),
            thorp_root_correction_mode=_text(flat.get("thorp_root_correction_mode"), default="bounded"),
            temporal_coupling_mode=_text(flat.get("temporal_coupling_mode"), default="daily_alloc"),
            allocation_scheme=allocation_scheme,
            wet_root_cap=_finite(flat.get("wet_root_cap"), default=0.10),
            dry_root_cap=_finite(flat.get("dry_root_cap"), default=0.18),
            lai_target_center=_finite(flat.get("lai_target_center"), default=2.75),
            lai_target_half_band=_finite(flat.get("lai_target_half_band"), default=0.5),
            leaf_fraction_of_shoot_base=leaf_fraction_of_shoot_base,
            stem_fraction_of_shoot_base=stem_fraction_of_shoot_base,
            min_leaf_fraction_of_shoot=_finite(flat.get("min_leaf_fraction_of_shoot"), default=0.58),
            max_leaf_fraction_of_shoot=_finite(flat.get("max_leaf_fraction_of_shoot"), default=0.85),
            leaf_fraction_floor=_finite(flat.get("leaf_fraction_floor"), default=0.20),
            canopy_lai_floor=_finite(flat.get("canopy_lai_floor"), default=2.00),
            thorp_root_blend=_finite(flat.get("thorp_root_blend"), default=1.0),
            hysteresis_gain=_finite(flat.get("hysteresis_gain"), default=0.35),
            smoothing_tau_days=max(_finite(flat.get("smoothing_tau_days"), default=1.0), 1e-6),
            fruit_abort_threshold=_finite(flat.get("fruit_abort_threshold"), default=0.82),
            fruit_abort_slope=_finite(flat.get("fruit_abort_slope"), default=2.5),
            reserve_capacity_g_m2=max(_finite(flat.get("reserve_capacity_g_m2"), default=20.0), 0.0),
            reserve_carryover_fraction=_finite(flat.get("reserve_carryover_fraction"), default=1.0),
            reserve_min_fraction=_finite(flat.get("reserve_min_fraction"), default=0.05),
            buffer_capacity_g_m2=max(_finite(flat.get("buffer_capacity_g_m2"), default=20.0), 0.0),
            buffer_min_fraction=_finite(flat.get("buffer_min_fraction"), default=0.05),
            buffer_release_rate_g_m2_d=max(_finite(flat.get("buffer_release_rate_g_m2_d"), default=10.0), 0.0),
            fruit_load_multiplier=max(_finite(flat.get("fruit_load_multiplier"), default=1.0), 0.0),
            boxcar_stage_count=max(int(round(_finite(flat.get("boxcar_stage_count"), default=5))), 1),
            notes=_text(flat.get("notes"), default=""),
        )
        config.validate()
        return config

    def validate(self) -> None:
        _validate_choice("fruit_structure_mode", self.fruit_structure_mode, SUPPORTED_FRUIT_STRUCTURE_MODES)
        _validate_choice("fruit_partition_mode", self.fruit_partition_mode, SUPPORTED_FRUIT_PARTITION_MODES)
        _validate_choice("vegetative_demand_mode", self.vegetative_demand_mode, SUPPORTED_VEGETATIVE_DEMAND_MODES)
        _validate_choice("reserve_buffer_mode", self.reserve_buffer_mode, SUPPORTED_RESERVE_BUFFER_MODES)
        _validate_choice("fruit_feedback_mode", self.fruit_feedback_mode, SUPPORTED_FRUIT_FEEDBACK_MODES)
        _validate_choice("sla_mode", self.sla_mode, SUPPORTED_SLA_MODES)
        _validate_choice("maintenance_mode", self.maintenance_mode, SUPPORTED_MAINTENANCE_MODES)
        _validate_choice("canopy_governor_mode", self.canopy_governor_mode, SUPPORTED_CANOPY_GOVERNOR_MODES)
        _validate_choice("root_representation_mode", self.root_representation_mode, SUPPORTED_ROOT_REPRESENTATION_MODES)
        _validate_choice("thorp_root_correction_mode", self.thorp_root_correction_mode, SUPPORTED_THORP_ROOT_CORRECTION_MODES)
        _validate_choice("temporal_coupling_mode", self.temporal_coupling_mode, SUPPORTED_TEMPORAL_COUPLING_MODES)
        _validate_choice("allocation_scheme", self.allocation_scheme, SUPPORTED_ALLOCATION_SCHEMES)
        if self.reserve_buffer_mode == "vanthoor_carbohydrate_buffer" and self.temporal_coupling_mode != "buffered_daily":
            raise ValueError(
                "reserve_buffer_mode='vanthoor_carbohydrate_buffer' requires temporal_coupling_mode='buffered_daily'."
            )
        if self.thorp_root_correction_mode == "bounded_hysteretic" and self.root_representation_mode != "bounded_explicit_root":
            raise ValueError(
                "thorp_root_correction_mode='bounded_hysteretic' requires root_representation_mode='bounded_explicit_root'."
            )
        if self.buffer_min_fraction < 0.0 or self.buffer_min_fraction >= 1.0:
            raise ValueError("buffer_min_fraction must be in [0, 1).")
        if self.reserve_min_fraction < 0.0 or self.reserve_min_fraction >= 1.0:
            raise ValueError("reserve_min_fraction must be in [0, 1).")

    def to_public_dict(self) -> dict[str, object]:
        return asdict(self)

    @property
    def storage_capacity_g_ch2o_m2(self) -> float:
        return float(self.reserve_capacity_g_m2)

    @property
    def buffer_capacity_g_ch2o_m2(self) -> float:
        return float(self.buffer_capacity_g_m2)

    @property
    def storage_carryover_fraction(self) -> float:
        return float(self.reserve_carryover_fraction)

    @property
    def fruit_feedback_threshold(self) -> float:
        return float(self.fruit_abort_threshold)

    @property
    def fruit_feedback_slope(self) -> float:
        return float(self.fruit_abort_slope)


def _validate_choice(name: str, value: str, allowed: set[str]) -> None:
    if value not in allowed:
        ordered = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported {name}={value!r}; expected one of: {ordered}.")


def _flatten_research_params(params: Mapping[str, object] | None) -> dict[str, object]:
    flat = _as_dict(params)
    for nested_key in ("tomics_research", "architecture", "research"):
        nested = _as_dict(flat.get(nested_key))
        if nested:
            flat = {**flat, **nested}
    aliases = {
        "storage_capacity_g_ch2o_m2": "reserve_capacity_g_m2",
        "storage_carryover_fraction": "reserve_carryover_fraction",
        "fruit_feedback_threshold": "fruit_abort_threshold",
        "fruit_feedback_slope": "fruit_abort_slope",
        "buffer_capacity_g_ch2o_m2": "buffer_capacity_g_m2",
    }
    for alias, canonical in aliases.items():
        if canonical not in flat and alias in flat:
            flat[canonical] = flat[alias]
    return flat


def has_research_modes(params: Mapping[str, object] | None) -> bool:
    flat = _flatten_research_params(params)
    return bool(flat)


TomicsResearchArchitecture = ResearchArchitectureConfig


def coerce_tomics_research_architecture(
    params: Mapping[str, object] | None,
) -> TomicsResearchArchitecture:
    return ResearchArchitectureConfig.from_params(params)


def traceability_missing_paths(root: Path) -> list[str]:
    missing: list[str] = []
    for row in TRACEABILITY_ROWS:
        path = (root / row.implementation_target).resolve()
        if not path.exists():
            missing.append(row.implementation_target)
    return missing
