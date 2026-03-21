from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
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
    return str(raw).strip()


SUPPORTED_OPTIMIZER_MODES = {
    "bounded_static_current",
    "prior_weighted_softmax",
    "prior_weighted_softmax_plus_lowpass",
}
SUPPORTED_VEGETATIVE_PRIOR_MODES = {
    "current_tomics_prior",
    "legacy_empirical_prior",
    "fit_from_warmup_prior",
}
SUPPORTED_LEAF_MARGINAL_MODES = {
    "canopy_only",
    "canopy_plus_weak_sink_penalty",
    "canopy_plus_turnover",
}
SUPPORTED_STEM_MARGINAL_MODES = {
    "support_only",
    "support_plus_transport",
    "support_transport_positioning",
}
SUPPORTED_ROOT_MARGINAL_MODES = {
    "water_only_gate",
    "greenhouse_multistress_gate",
    "greenhouse_multistress_gate_plus_saturation",
}
SUPPORTED_FRUIT_FEEDBACK_MODES = {
    "off",
    "tomgro_abort_proxy",
    "dekoning_source_demand_proxy",
}
SUPPORTED_RESERVE_BUFFER_MODES = {
    "off",
    "tomsim_storage_pool",
    "vanthoor_carbohydrate_buffer",
}
SUPPORTED_CANOPY_GOVERNOR_MODES = {
    "lai_band",
    "lai_band_plus_leaf_floor",
}
SUPPORTED_TEMPORAL_MODES = {
    "daily_marginal_daily_alloc",
    "subdaily_signal_daily_integral_alloc",
    "subdaily_signal_daily_integral_alloc_lowpass",
}
SUPPORTED_THORP_ROOT_CORRECTION_MODES = {
    "off",
    "bounded",
    "bounded_hysteretic",
}
SUPPORTED_ALLOCATION_SCHEMES = {"3pool", "4pool"}


@dataclass(frozen=True, slots=True)
class PromotedTraceRow:
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


PROMOTED_TRACE_ROWS: tuple[PromotedTraceRow, ...] = (
    PromotedTraceRow(
        source_family="Heuvelink/TOMSIM",
        source_file="Heuvelink - 1996 - Tomato growth and yield quantitative analysis and synthesis.pdf",
        page_or_equation="Ch. 5.7, sink-strength discussion",
        exact_reference="Fruit-vs-vegetative allocation remains one common assimilate pool with fruit anchored to relative sink strength.",
        original_symbols="S_i, common assimilate pool",
        normalized_repo_symbols="u_fruit, legacy_fruit_gate, p0_veg",
        units="fraction",
        validated_domain="Greenhouse tomato source-sink modelling.",
        implementation_target="src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/promoted_policy.py",
        status="research-only",
        rationale="Promoted allocator preserves legacy fruit anchoring and only perturbs vegetative split.",
    ),
    PromotedTraceRow(
        source_family="De Koning",
        source_file="De Koning - 1994 - Development and dry matter distribution in glasshouse tomato  a quantitative approach.pdf",
        page_or_equation="fruit load / crop-control discussion, LAI optimum reasoning",
        exact_reference="Vegetative control must preserve canopy function under high fruit load, with LAI targets in greenhouse crop control.",
        original_symbols="vegetative units, LAI optimum",
        normalized_repo_symbols="lai_target_center, leaf_marginal_mode, canopy_governor_mode",
        units="dimensionless proxy",
        validated_domain="Glasshouse tomato crop control.",
        implementation_target="src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/marginal_terms.py",
        status="research-only",
        rationale="Leaf marginal stays canopy-first and stem marginal reflects support under fruit load.",
    ),
    PromotedTraceRow(
        source_family="Kuijpers",
        source_file="Kuijpers et al. - 2019 - Model selection with a common structure Tomato crop growth models.pdf",
        page_or_equation="common-structure synthesis and identifiability discussion",
        exact_reference="Architecture mixing requires explicit interfaces and disciplined component boundaries.",
        original_symbols="p, gr, m, xA, g, xS, h1, h2",
        normalized_repo_symbols="optimizer_mode, reserve_buffer_mode, temporal_mode",
        units="architecture scaffold",
        validated_domain="Model-selection synthesis across tomato crop models.",
        implementation_target="src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/promoted_modes.py",
        status="research-only",
        rationale="Promoted allocator is opt-in and remains separated from shipped default semantics.",
    ),
    PromotedTraceRow(
        source_family="Potkay/THORP",
        source_file="Potkay et al. - 2021 - Coupled whole-tree optimality and xylem hydraulics explain dynamic biomass partitioning.pdf",
        page_or_equation="Eq. 1(a)-(b)",
        exact_reference="Marginal gain-over-cost framing is used only as a bounded root correction cue, not as whole-plant tomato allocation.",
        original_symbols="u_k, gain_k, cost_k",
        normalized_repo_symbols="root_marginal_mode, thorp_root_correction_mode, thorp_root_blend",
        units="dimensionless proxy",
        validated_domain="Whole-tree hydraulics, not greenhouse tomato default.",
        implementation_target="src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/marginal_terms.py",
        status="research-only",
        rationale="THORP remains subordinate and stress-gated.",
    ),
    PromotedTraceRow(
        source_family="Research design synthesis",
        source_file="docs/architecture/review/tomics-promoted-allocator-design.md",
        page_or_equation="promoted constrained-marginal allocator concept",
        exact_reference="Prior-weighted vegetative softmax with low-pass memory and bounded greenhouse stress gates.",
        original_symbols="p0_veg, ΔM_i, beta, tau_alloc",
        normalized_repo_symbols="vegetative_prior_mode, leaf_marginal_mode, stem_marginal_mode, root_marginal_mode, beta, tau_alloc_days",
        units="fraction and dimensionless marginal proxies",
        validated_domain="Research-only allocator family; not yet validated for default promotion.",
        implementation_target="src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/prior_optimizer.py",
        status="research-only",
        rationale="This is the explicit promoted-family algorithm under test in issue #236.",
    ),
)


def promoted_traceability_rows() -> list[dict[str, str]]:
    return [row.to_dict() for row in PROMOTED_TRACE_ROWS]


@dataclass(frozen=True, slots=True)
class PromotedAllocatorConfig:
    architecture_id: str = "promoted_default"
    optimizer_mode: str = "prior_weighted_softmax"
    vegetative_prior_mode: str = "current_tomics_prior"
    leaf_marginal_mode: str = "canopy_only"
    stem_marginal_mode: str = "support_only"
    root_marginal_mode: str = "water_only_gate"
    fruit_feedback_mode: str = "off"
    reserve_buffer_mode: str = "off"
    canopy_governor_mode: str = "lai_band"
    temporal_mode: str = "daily_marginal_daily_alloc"
    thorp_root_correction_mode: str = "bounded"
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
    beta: float = 3.0
    tau_alloc_days: float = 3.0
    thorp_root_blend: float = 0.5
    low_sink_threshold: float = 0.70
    low_sink_slope: float = 0.18
    rootzone_multistress_weight: float = 0.30
    rootzone_saturation_weight: float = 0.25
    rootzone_temperature_weight: float = 0.15
    reserve_capacity_g_m2: float = 15.0
    reserve_carryover_fraction: float = 0.80
    reserve_min_fraction: float = 0.05
    buffer_capacity_g_m2: float = 18.0
    buffer_min_fraction: float = 0.10
    buffer_release_rate_g_m2_d: float = 10.0
    fruit_abort_threshold: float = 0.82
    fruit_abort_slope: float = 2.5
    fruit_load_multiplier: float = 1.0
    boxcar_stage_count: int = 5
    notes: str = ""

    @classmethod
    def from_params(
        cls,
        params: Mapping[str, object] | None,
        *,
        scheme: str | None = None,
    ) -> "PromotedAllocatorConfig":
        flat = _as_dict(params)
        for nested_key in ("promoted_allocator", "tomics_promoted", "research", "architecture"):
            nested = _as_dict(flat.get(nested_key))
            if nested:
                flat = {**flat, **nested}
        if "smoothing_tau_days" in flat and "tau_alloc_days" not in flat:
            flat["tau_alloc_days"] = flat["smoothing_tau_days"]
        config = cls(
            architecture_id=_text(flat.get("architecture_id"), default="promoted_default"),
            optimizer_mode=_text(flat.get("optimizer_mode"), default="prior_weighted_softmax"),
            vegetative_prior_mode=_text(flat.get("vegetative_prior_mode"), default="current_tomics_prior"),
            leaf_marginal_mode=_text(flat.get("leaf_marginal_mode"), default="canopy_only"),
            stem_marginal_mode=_text(flat.get("stem_marginal_mode"), default="support_only"),
            root_marginal_mode=_text(flat.get("root_marginal_mode"), default="water_only_gate"),
            fruit_feedback_mode=_text(flat.get("fruit_feedback_mode"), default="off"),
            reserve_buffer_mode=_text(flat.get("reserve_buffer_mode"), default="off"),
            canopy_governor_mode=_text(flat.get("canopy_governor_mode"), default="lai_band"),
            temporal_mode=_text(flat.get("temporal_mode"), default="daily_marginal_daily_alloc"),
            thorp_root_correction_mode=_text(flat.get("thorp_root_correction_mode"), default="bounded"),
            allocation_scheme=_text(flat.get("allocation_scheme", scheme), default=scheme or "4pool"),
            wet_root_cap=_finite(flat.get("wet_root_cap"), default=0.10),
            dry_root_cap=_finite(flat.get("dry_root_cap"), default=0.18),
            lai_target_center=_finite(flat.get("lai_target_center"), default=2.75),
            lai_target_half_band=_finite(flat.get("lai_target_half_band"), default=0.5),
            leaf_fraction_of_shoot_base=_finite(flat.get("leaf_fraction_of_shoot_base"), default=0.70),
            stem_fraction_of_shoot_base=_finite(flat.get("stem_fraction_of_shoot_base"), default=0.30),
            min_leaf_fraction_of_shoot=_finite(flat.get("min_leaf_fraction_of_shoot"), default=0.58),
            max_leaf_fraction_of_shoot=_finite(flat.get("max_leaf_fraction_of_shoot"), default=0.85),
            leaf_fraction_floor=_finite(flat.get("leaf_fraction_floor"), default=0.20),
            canopy_lai_floor=_finite(flat.get("canopy_lai_floor"), default=2.0),
            beta=max(_finite(flat.get("beta"), default=3.0), 0.0),
            tau_alloc_days=max(_finite(flat.get("tau_alloc_days"), default=3.0), 1e-6),
            thorp_root_blend=_finite(flat.get("thorp_root_blend"), default=0.5),
            low_sink_threshold=_finite(flat.get("low_sink_threshold"), default=0.70),
            low_sink_slope=_finite(flat.get("low_sink_slope"), default=0.18),
            rootzone_multistress_weight=max(_finite(flat.get("rootzone_multistress_weight"), default=0.30), 0.0),
            rootzone_saturation_weight=max(_finite(flat.get("rootzone_saturation_weight"), default=0.25), 0.0),
            rootzone_temperature_weight=max(_finite(flat.get("rootzone_temperature_weight"), default=0.15), 0.0),
            reserve_capacity_g_m2=max(_finite(flat.get("reserve_capacity_g_m2"), default=15.0), 0.0),
            reserve_carryover_fraction=_finite(flat.get("reserve_carryover_fraction"), default=0.80),
            reserve_min_fraction=_finite(flat.get("reserve_min_fraction"), default=0.05),
            buffer_capacity_g_m2=max(_finite(flat.get("buffer_capacity_g_m2"), default=18.0), 0.0),
            buffer_min_fraction=_finite(flat.get("buffer_min_fraction"), default=0.10),
            buffer_release_rate_g_m2_d=max(_finite(flat.get("buffer_release_rate_g_m2_d"), default=10.0), 0.0),
            fruit_abort_threshold=_finite(flat.get("fruit_abort_threshold"), default=0.82),
            fruit_abort_slope=_finite(flat.get("fruit_abort_slope"), default=2.5),
            fruit_load_multiplier=max(_finite(flat.get("fruit_load_multiplier"), default=1.0), 0.0),
            boxcar_stage_count=max(int(round(_finite(flat.get("boxcar_stage_count"), default=5.0))), 1),
            notes=_text(flat.get("notes"), default=""),
        )
        config.validate()
        return config

    def validate(self) -> None:
        _validate_choice("optimizer_mode", self.optimizer_mode, SUPPORTED_OPTIMIZER_MODES)
        _validate_choice("vegetative_prior_mode", self.vegetative_prior_mode, SUPPORTED_VEGETATIVE_PRIOR_MODES)
        _validate_choice("leaf_marginal_mode", self.leaf_marginal_mode, SUPPORTED_LEAF_MARGINAL_MODES)
        _validate_choice("stem_marginal_mode", self.stem_marginal_mode, SUPPORTED_STEM_MARGINAL_MODES)
        _validate_choice("root_marginal_mode", self.root_marginal_mode, SUPPORTED_ROOT_MARGINAL_MODES)
        _validate_choice("fruit_feedback_mode", self.fruit_feedback_mode, SUPPORTED_FRUIT_FEEDBACK_MODES)
        _validate_choice("reserve_buffer_mode", self.reserve_buffer_mode, SUPPORTED_RESERVE_BUFFER_MODES)
        _validate_choice("canopy_governor_mode", self.canopy_governor_mode, SUPPORTED_CANOPY_GOVERNOR_MODES)
        _validate_choice("temporal_mode", self.temporal_mode, SUPPORTED_TEMPORAL_MODES)
        _validate_choice("thorp_root_correction_mode", self.thorp_root_correction_mode, SUPPORTED_THORP_ROOT_CORRECTION_MODES)
        _validate_choice("allocation_scheme", self.allocation_scheme, SUPPORTED_ALLOCATION_SCHEMES)
        if self.buffer_min_fraction < 0.0 or self.buffer_min_fraction >= 1.0:
            raise ValueError("buffer_min_fraction must be in [0, 1).")
        if self.reserve_min_fraction < 0.0 or self.reserve_min_fraction >= 1.0:
            raise ValueError("reserve_min_fraction must be in [0, 1).")

    def to_public_dict(self) -> dict[str, object]:
        return asdict(self)

    @property
    def fruit_structure_mode(self) -> str:
        if self.reserve_buffer_mode == "vanthoor_carbohydrate_buffer":
            return "vanthoor_fixed_boxcar"
        return "tomsim_truss_cohort"

    @property
    def fruit_partition_mode(self) -> str:
        return "legacy_sink_exact"

    @property
    def vegetative_demand_mode(self) -> str:
        return "dekoning_vegetative_unit"

    @property
    def sla_mode(self) -> str:
        return "derived_not_driver"

    @property
    def maintenance_mode(self) -> str:
        if self.reserve_buffer_mode == "vanthoor_carbohydrate_buffer":
            return "buffer_linked"
        return "rgr_adjusted"

    @property
    def temporal_coupling_mode(self) -> str:
        mapping = {
            "daily_marginal_daily_alloc": "daily_alloc",
            "subdaily_signal_daily_integral_alloc": "hourly_source_daily_alloc",
            "subdaily_signal_daily_integral_alloc_lowpass": "buffered_daily",
        }
        return mapping[self.temporal_mode]

    @property
    def storage_capacity_g_ch2o_m2(self) -> float:
        return float(self.reserve_capacity_g_m2)

    @property
    def storage_carryover_fraction(self) -> float:
        return float(self.reserve_carryover_fraction)

    @property
    def buffer_capacity_g_ch2o_m2(self) -> float:
        return float(self.buffer_capacity_g_m2)

    @property
    def fruit_feedback_threshold(self) -> float:
        return float(self.fruit_abort_threshold)

    @property
    def fruit_feedback_slope(self) -> float:
        return float(self.fruit_abort_slope)

    @property
    def smoothing_tau_days(self) -> float:
        return float(self.tau_alloc_days)


def _validate_choice(name: str, value: str, allowed: set[str]) -> None:
    if value not in allowed:
        ordered = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported {name}={value!r}; expected one of: {ordered}.")


__all__ = [
    "PROMOTED_TRACE_ROWS",
    "PromotedAllocatorConfig",
    "SUPPORTED_ALLOCATION_SCHEMES",
    "SUPPORTED_CANOPY_GOVERNOR_MODES",
    "SUPPORTED_FRUIT_FEEDBACK_MODES",
    "SUPPORTED_LEAF_MARGINAL_MODES",
    "SUPPORTED_OPTIMIZER_MODES",
    "SUPPORTED_RESERVE_BUFFER_MODES",
    "SUPPORTED_ROOT_MARGINAL_MODES",
    "SUPPORTED_STEM_MARGINAL_MODES",
    "SUPPORTED_TEMPORAL_MODES",
    "SUPPORTED_THORP_ROOT_CORRECTION_MODES",
    "SUPPORTED_VEGETATIVE_PRIOR_MODES",
    "promoted_traceability_rows",
]
