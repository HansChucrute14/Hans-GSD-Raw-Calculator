#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gsd.types -- Centralized type definitions for the GSD package.

Literal types for string constants used across the codebase.
TypedDict structures for JSON data contracts.
Type aliases for complex nested structures.
Type guard helper functions.

Note: Runtime dataclasses (AnimalInput, DerEnvelope, SolverRequest,
CrossRefIndex) live in core.py to avoid circular imports.

All types compatible with Python 3.10+.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Set, Tuple, TypedDict, Union


# -- Nutrient Status Literals (3-state contract per DB) ------------------------

NutrientStatus = Literal["measured", "missing", "not_applicable", "data_incomplete"]
"""3-state nutrient entry status. Every nutrient in DB is one of these."""


# -- Constraint / Cascade Literals ---------------------------------------------

ConstraintTier = Literal["adequacy_soft", "safety_hard", "envelope_soft"]
"""LP constraint tier classification per sat_dados_schema:4.2."""

ClinicalCriticality = Literal["critical", "high", "moderate", "low"]
"""Clinical priority for nutrient deficiencies per sat_dados_schema:4.2."""

CascadeLevel = Literal[1, 2, 3]
"""Lexicographic cascade level identifier."""

ObjectiveStageKind = Literal[
    "goal_deviation",
    "weighted_normalized_deviation",
    "adequacy_slack",
    "weighted_normalized_slack",
    "sul_violation",
    "minimize_normalized_sul_violation",
    "der_deviation",
    "minimize_absolute_der_deviation",
    "minimize_weighted_normalized_adequacy_slack",
]
"""Objective stage kind identifiers from solve_cascade[]."""


# -- Solver Output Literals ----------------------------------------------------

SolverOutputStatus = Literal[
    "optimal",
    "suboptimal",
    "unsafe_diagnostic",
    "structurally_infeasible",
    "data_incomplete",
]
"""Canonical solver output status. These are the 5 values in the output contract."""

SolverRawStatus = Literal["feasible", "infeasible"]
"""Internal raw LP solver status (not exposed in output contract)."""

FeedingRecommendation = Literal["SAFE_TO_FEED", "FEED_WITH_CAUTION", "DO_NOT_FEED"]
"""Solver output feeding recommendation per sat_solver_contrato:7."""

NutrientAdequacyStatus = Literal["adequate", "deficient", "excess", "unknown"]
"""Nutrient result adequacy status in output contract."""


# -- Ingredient Category Literal -----------------------------------------------

IngredientCategory = Literal[
    "muscle_meat",
    "muscle_organ",
    "organ_secreting",
    "organ_non_secreting",
    "connective_tissue",
    "blood_source",
    "fish",
    "bone",
    "cartilage",
    "fat_source",
    "supplement",
    "grain",
    "vegetable",
    "fruit",
    "dairy",
    "egg",
]
"""Ingredient category enum from db_ingredientes.schema.json (16 categories)."""


# -- TypedDict: Nutrient Entry (3-state contract) -----------------------------


class NutrientEntry(TypedDict, total=False):
    """3-state nutrient entry from DB_ingredientes.json.

    Attributes:
        status: One of "measured", "missing", "not_applicable", "data_incomplete"
        value: Numeric value (present only when status="measured")
    """
    status: NutrientStatus
    value: Optional[float]


class NutrientEntryMeasured(TypedDict):
    """Refinement: measured nutrient (has value)."""
    status: Literal["measured"]
    value: float


class NutrientEntryMissing(TypedDict):
    """Refinement: missing/not_applicable/data_incomplete (no value)."""
    status: Literal["missing", "not_applicable", "data_incomplete"]


# -- TypedDict: Ingredient Structure -------------------------------------------


class BromatologicalProfile(TypedDict, total=False):
    """Ingredient bromatological profile structure."""
    nutrients: Dict[str, NutrientEntry]
    moisture_pct: Optional[float]
    ash_pct: Optional[float]
    fiber_g: Optional[float]


class Ingredient(TypedDict, total=False):
    """DB ingredient structure from DB_ingredientes.json."""
    ingredient_id: str
    display_name: str
    category: IngredientCategory
    requires_cooking: bool
    bromatological_profile: BromatologicalProfile
    bioavailability_factors: Optional[List[Dict[str, Any]]]
    lp_constraints: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
    safety_alerts: Optional[List[Dict[str, Any]]]


# -- TypedDict: Constraint Structures -----------------------------------------


class NutrientBound(TypedDict, total=False):
    """Nutrient bound constraint from constraints.json."""
    constraint_id: str
    nutrient_id: str
    tier: ConstraintTier
    target: Optional[Dict[str, Any]]
    bounds: Optional[List[Dict[str, Any]]]


class ToxicologicalLimitEntry(TypedDict, total=False):
    """Single entry from toxicological_limits.json (list at top level)."""
    nutrient_id: str
    sul: Dict[str, Any]
    constraint_tier: ConstraintTier


# -- TypedDict: Scenario Structures -------------------------------------------


class TargetValue(TypedDict):
    """Target value for a nutrient in scenarios.json."""
    nutrient_id: str
    value: float
    unit: str


class Scenario(TypedDict, total=False):
    """Scenario definition from scenarios.json."""
    scenario_id: str
    display_name: str
    targets: List[TargetValue]
    k_multiplier_ref: Optional[str]


# -- TypedDict: LP Parameters --------------------------------------------------


class CategoryGoal(TypedDict):
    """Category goal for cascade level."""
    target_pct: float
    tolerance: Optional[float]


class CascadeLevelConfig(TypedDict, total=False):
    """Solve cascade level configuration from lp_parameters_schema.json."""
    level: int
    relax_tiers: List[str]
    category_goals: Optional[Dict[str, CategoryGoal]]
    clinical_floor: Optional[Dict[str, Any]]
    objective_stages: List[Dict[str, Any]]


class SolverParams(TypedDict, total=False):
    """Solver parameters from lp_parameters_schema.json."""
    tie_break_weight: float
    tie_break_objective: str
    fix_optimum_tolerance_abs: float
    fix_optimum_tolerance_rel: float
    cbc_time_limit_seconds: int
    cbc_mip_gap: float
    big_m_strategy: str


class NUTRIENT_REGISTRY_Entry(TypedDict, total=False):
    """NUTRIENT_REGISTRY entry from lp_parameters_schema.json."""
    nutrient_id: str
    display_name: str
    unit: str
    basis: str
    constraint_tier: ConstraintTier
    clinical_criticality: ClinicalCriticality
    has_sul: bool
    sul_value: Optional[float]


# -- TypedDict: Audit Provenance ----------------------------------------------


class ReferenceEntry(TypedDict, total=False):
    """Reference entry from audit_provenance.json."""
    ref_id: str
    title: str
    authors: Optional[List[str]]
    year: Optional[int]
    quality_flag: str
    url: Optional[str]


# -- TypedDict: Solver Output Contract ----------------------------------------


class AllocationEntry(TypedDict):
    """Single allocation in solver output (Level 1/2)."""
    ingredient_id: str
    display_name: str
    category: str
    grams_per_day: float
    pct_of_total: float
    kcal_per_day: float
    cost_per_day: Optional[float]


class NutrientResult(TypedDict, total=False):
    """Nutrient result in solver output."""
    nutrient_id: str
    display_name: str
    value: Optional[float]
    unit: str
    basis: str
    target_min: Optional[float]
    target_max: Optional[float]
    sul: Optional[float]
    pct_of_min: Optional[float]
    pct_of_sul: Optional[float]
    status: NutrientAdequacyStatus
    constraint_tier: ConstraintTier
    clinical_criticality: ClinicalCriticality


class Gap(TypedDict):
    """Gap entry in solver output."""
    nutrient_id: str
    pct_of_min: float
    category_missing: str
    top_ingredients_in_category: List[Dict[str, Any]]


class Alert(TypedDict, total=False):
    """Alert entry in solver output."""
    type: str
    severity: str
    nutrient_id: str
    message: str
    action: str


class WhatWouldHappen(TypedDict, total=False):
    """Counterfactual scenario in Level 3 diagnostic_analysis."""
    description: str
    grams_needed_for_der: Optional[float]
    nutrient_at_risk: Optional[str]
    value_at_that_amount: Optional[float]
    sul_value: Optional[float]
    clinical_significance: str
    clinical_floor_applied: bool
    clinical_floor_relaxed: bool
    ingredients_below_floor: List[Dict[str, Any]]
    x_min_i_effective: Dict[str, float]
    clinical_floor_relaxation_note: Optional[str]


class DiagnosticAnalysis(TypedDict, total=False):
    """Diagnostic analysis for Level 3 (unsafe_diagnostic)."""
    reason: str
    sul_violations_inevitable: List[Dict[str, Any]]
    what_would_happen: WhatWouldHappen
    recommended_alternative_actions: List[str]


class LexicographicStagesUsed(TypedDict, total=False):
    """Lexicographic solve stages metadata in solver_metadata."""
    stages: List[str]
    order_verified: bool
    note: str


class SolverMetadata(TypedDict, total=False):
    """Solver metadata in output contract."""
    solver_engine: str
    solve_time_ms: float
    cascade_attempts: List[int]
    final_level: int
    objective_value: Optional[float]
    slack_variables_used: Optional[List[str]]
    total_slack_weighted: Optional[float]
    sul_violations: Optional[List[Dict[str, Any]]]
    lexicographic_stages_used: Optional[LexicographicStagesUsed]
    clinical_floor_applied: Optional[bool]
    clinical_floor_bounds: Optional[Dict[str, float]]


class RecommendedAddition(TypedDict):
    """Recommended addition entry in solver output."""
    category: str
    rationale: str
    top_3_ingredients: List[str]


class AnimalContext(TypedDict, total=False):
    """Animal context in solver output."""
    sex: str
    weight_kg: float
    age_months: int
    gonadal_status: str
    der_kcal: float
    ter_kcal: float
    k_multiplier: float
    bw_source: str


class EnvelopeOutput(TypedDict, total=False):
    """Envelope in solver output."""
    min_total_g: float
    max_total_g: float
    actual_total_g: Optional[float]
    strategy: str


class SolverOutput(TypedDict, total=False):
    """Complete solver output contract per sat_solver_contrato:7."""
    solver_output_schema: str
    solver_status: SolverOutputStatus
    feeding_recommendation: FeedingRecommendation
    cascade_level_used: int
    animal_context: AnimalContext
    envelope: EnvelopeOutput
    allocations: Optional[List[AllocationEntry]]
    nutrient_results: List[NutrientResult]
    diagnostic_analysis: Optional[DiagnosticAnalysis]
    gaps: List[Gap]
    alerts: List[Alert]
    recommended_additions: List[RecommendedAddition]
    solver_metadata: SolverMetadata


# -- TypedDict: LP Problem (build_lp_problem return) ---------------------------


class LpProblemDict(TypedDict, total=False):
    """Return type of solver.build_lp_problem().

    Contains the PuLP problem, decision variables, compiled coefficients,
    and all metadata needed by call_lp_solver() and solve_cascade().
    """
    prob: Any                          # pulp.LpProblem
    x_vars: Dict[str, Any]             # ingredient_id -> pulp.LpVariable
    compiled_coefficients: Dict[str, Dict[str, float]]
    targets_per_day: Dict[str, float]
    suls_per_day: Dict[str, float]
    clinical_floor_bounds: Dict[str, float]
    big_m_values: Dict[str, float]
    has_binary_vars: bool
    em_per_g: Dict[str, float]
    der_info: Any                      # DerEnvelope
    nutrient_slack_vars: Dict[str, Any]
    sul_slack_vars: Dict[str, Any]
    der_dev_vars: Dict[str, Any]
    category_to_ingredients: Dict[str, List[str]]
    category_goals: Dict[str, Any]
    category_goals_enabled: bool
    nutrient_registry: Dict[str, Any]
    antagonism_slack_vars: Dict[str, Any]
    antagonism_penalty_weights: Dict[str, Any]


# -- TypedDict: Solver Raw Result (call_lp_solver return) ----------------------


class SolverRawResultFeasible(TypedDict, total=False):
    """Feasible return from call_lp_solver()."""
    status: Literal["feasible"]
    x_values: Dict[str, float]
    nutrient_values: Dict[str, float]
    objective_value: Optional[float]
    stages_solved: List[str]
    solve_time_ms: int
    nutrient_slack_vars: Dict[str, Any]
    sul_slack_vars: Dict[str, Any]
    der_dev_vars: Dict[str, Any]
    clinical_floor_bounds: Dict[str, float]
    clinical_floor_relaxed: bool
    category_goal_deviations: Dict[str, float]
    fix_optimum_applied: List[str]
    tie_break_applied: bool
    tie_break_weight_used: Optional[float]


class SolverRawResultInfeasible(TypedDict, total=False):
    """Infeasible return from call_lp_solver()."""
    status: Literal["infeasible"]
    reason: Optional[str]
    stages_solved: List[str]


SolverRawResult = Union[SolverRawResultFeasible, SolverRawResultInfeasible]
"""Union of feasible/infeasible raw solver results."""


# -- Type Aliases --------------------------------------------------------------

NutrientMatrix = Dict[str, Dict[str, NutrientEntry]]
"""Nutrient matrix: ingredient_id -> nutrient_id -> NutrientEntry."""

CompiledCoefficients = Dict[str, Dict[str, float]]
"""LP coefficients: variable_id -> nutrient_id -> coefficient value."""

IngredientId = str
NutrientId = str
ConstraintId = str
RefId = str

JSONDict = Dict[str, Any]
JSONList = List[Any]
JSONPrimitive = Union[str, int, float, bool, None]
JSONValue = Union[JSONPrimitive, JSONDict, JSONList]


# -- Type Guard Helpers --------------------------------------------------------


def is_measured(entry: Dict[str, Any]) -> bool:
    """Type guard: check if nutrient entry is measured."""
    return entry.get("status") == "measured" and entry.get("value") is not None


def get_value(entry: Dict[str, Any], default: float = 0.0) -> float:
    """Safely extract numeric value from a 3-state nutrient entry."""
    if is_measured(entry):
        val = entry.get("value")
        return float(val) if val is not None else default
    return default
