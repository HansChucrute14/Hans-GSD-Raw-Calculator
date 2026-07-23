--- docs/governance/type-safety-implementation-plan.md (原始)


+++ docs/governance/type-safety-implementation-plan.md (修改后)
# Type Safety Implementation Plan — GSD Diet Calc V10.4
## Agent-to-Agent Executable Specification (July 2026 SOTA)

**Document Classification:** EXECUTION_PLAN
**Target Executor:** Autonomous Code Agent
**Precision Level:** ATOMIC_STEP
**Validation Mode:** STRICT_ASSERTION
**Generated:** 2026-07-22
**Codebase Version:** V10.4
**Python Target:** 3.10+

---

## EXECUTION CONTEXT

### Codebase Topology
```
/workspace/
├── pyproject.toml              # Package config (EXISTS, MODIFY)
├── src/gsd/
│   ├── __init__.py             # Package init (EXISTS, NO CHANGE)
│   ├── types.py                # Type definitions (CREATE NEW)
│   ├── core.py                 # Core utilities (596 lines, ANNOTATE)
│   ├── nutrition.py            # DER/nutrition (363 lines, ANNOTATE)
│   ├── solver.py               # LP cascade (1652 lines, ANNOTATE)
│   ├── mapa.py                 # MAPA generator (1421 lines, ANNOTATE)
│   ├── cli.py                  # CLI entry (272 lines, ANNOTATE)
│   └── doc_introspector.py     # AST introspection (1105 lines, ANNOTATE)
├── tests/                      # Test suite (EXISTING, EXTEND)
├── docs/governance/            # This plan (EXISTING, REPLACE)
└── data/                       # JSON data files (NO CHANGE)
```

### Pre-Execution State Verification
**ASSERTION 1:** All 6 Python modules exist in `/workspace/src/gsd/`
**ASSERTION 2:** `pyproject.toml` exists at `/workspace/pyproject.toml`
**ASSERTION 3:** Python version >= 3.10 is available
**ASSERTION 4:** No existing `types.py` in `/workspace/src/gsd/`

---

## PHASE 0: PRECONDITIONS & DEPENDENCIES

### Task 0.1: Install Type-Checking Toolchain
**Action:** Execute pip install command
**Command:** `pip install mypy>=1.8.0 typing-extensions>=4.9.0 ruff>=0.1.0`
**Postcondition:** `mypy --version` returns >= 1.8.0
**Rollback:** `pip uninstall mypy typing-extensions ruff`

### Task 0.2: Backup Current State
**Action:** Create git branch
**Command:** `git checkout -b feature/type-safety-v10.4`
**Postcondition:** Current branch is `feature/type-safety-v10.4`

---

## PHASE 1: FOUNDATION INFRASTRUCTURE (P0-CRITICAL)

### Task 1.1: Update pyproject.toml with mypy Configuration

**File:** `/workspace/pyproject.toml`
**Operation:** APPEND to existing file
**Content to Append:**

```toml

[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_configs = true
show_error_codes = true
show_column_numbers = true
pretty = true
exclude = ["build/", "dist/", ".eggs/"]

[[tool.mypy.overrides]]
module = ["jsonschema.*", "pulp.*"]
ignore_missing_imports = true

[tool.ruff]
line-length = 100
target-version = "py310"
select = ["E", "F", "W", "I", "UP", "TCH"]

[tool.ruff.lint.per-file-ignores]
"src/gsd/types.py" = ["TCH001", "TCH002", "TCH003"]
```

**Validation:** Run `cat /workspace/pyproject.toml` and verify `[tool.mypy]` section exists

---

### Task 1.2: Create src/gsd/types.py Module

**File:** `/workspace/src/gsd/types.py`
**Operation:** CREATE NEW FILE
**Encoding:** UTF-8
**Line Endings:** Unix (LF)

**Exact Content:**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gsd.types — Centralized type definitions for the GSD package.

This module provides:
  - Literal types for nutrient status, constraint tiers, clinical criticality
  - TypedDict structures for all JSON data contracts
  - Dataclasses for runtime request/response objects
  - Protocol types for dependency injection
  - Type aliases for complex nested structures
  - Type guard helper functions

All types are compatible with Python 3.10+ and mypy strict mode.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    Set,
    Tuple,
    TypedDict,
    Union,
)


# ── Nutrient Status Literals ────────────────────────────────────────────────

NutrientStatus = Literal["measured", "missing", "not_applicable", "data_incomplete"]
"""3-state nutrient contract per §6.4a item 5."""

ConstraintTier = Literal["adequacy_soft", "safety_hard", "clinical_critical"]
"""LP constraint tier classification."""

ClinicalCriticality = Literal["critical", "high", "moderate", "low"]
"""Clinical priority for nutrient deficiencies."""

SolverStatus = Literal["optimal", "infeasible", "unbounded", "undefined"]
"""LP solver termination status."""

CascadeLevel = Literal[1, 2, 3]
"""Lexicographic cascade level identifier."""

FeedingRecommendation = Literal["proceed", "adjust_selection", "consult_veterinarian"]
"""Solver output feeding recommendation."""


# ── TypedDict: Nutrient Entry (3-state contract) ────────────────────────────


class NutrientEntry(TypedDict, total=False):
    """3-state nutrient entry per §6.4a item 5.

    Attributes:
        status: One of "measured", "missing", "not_applicable", "data_incomplete"
        value: Numeric value (required if status="measured")
        unit: Unit string (e.g., "g", "mg", "IU")
        basis: Measurement basis (e.g., "as_fed", "energy_normalized")
        source_ref: Reference ID for data source
        anomaly_ref: Reference ID explaining missing data
        reason: Human-readable explanation for missing/not_applicable
    """
    status: NutrientStatus
    value: Optional[float]
    unit: Optional[str]
    basis: Optional[str]
    source_ref: Optional[str]
    anomaly_ref: Optional[str]
    reason: Optional[str]


class NutrientEntryMeasured(NutrientEntry):
    """TypedDict refinement for measured nutrients (has value)."""
    status: Literal["measured"]
    value: float


class NutrientEntryMissing(NutrientEntry):
    """TypedDict refinement for missing/not_applicable nutrients."""
    status: Literal["missing", "not_applicable", "data_incomplete"]
    value: None


# ── TypedDict: Bromatological Profile ───────────────────────────────────────


class BromatologicalProfile(TypedDict, total=False):
    """Ingredient bromatological profile structure.

    Attributes:
        nutrients: Dict mapping nutrient_id to NutrientEntry
        moisture_pct: Moisture percentage (as-fed basis)
        ash_pct: Ash percentage (as-fed basis)
        fiber_g: Fiber grams per 100g
    """
    nutrients: Dict[str, NutrientEntry]
    moisture_pct: Optional[float]
    ash_pct: Optional[float]
    fiber_g: Optional[float]


# ── TypedDict: Ingredient Structure ─────────────────────────────────────────


class Ingredient(TypedDict, total=False):
    """DB ingredient structure from DB_ingredientes.json.

    Attributes:
        ingredient_id: Unique identifier (e.g., "beef_muscle_raw")
        display_name: Human-readable name
        category: Ingredient category (see formulation_rules.json enum)
        bromatological_profile: Nutrient composition
        safety_alerts: List of safety alert dicts
        inclusion_limits: Max inclusion percentages
    """
    ingredient_id: str
    display_name: str
    category: str
    bromatological_profile: BromatologicalProfile
    safety_alerts: List[Dict[str, Any]]
    inclusion_limits: Optional[Dict[str, float]]


# ── TypedDict: Constraint Structures ────────────────────────────────────────


class ConstraintBound(TypedDict):
    """Single constraint bound for LP coefficients.

    Attributes:
        rhs: Right-hand side value
        sense: Constraint sense (">=", "<=", "==")
    """
    rhs: float
    sense: Literal[">=", "<=", "=="]


class LpCoefficients(TypedDict, total=False):
    """LP coefficient specification from constraints.json.

    Attributes:
        variables_referenced: List of variable IDs
        bounds: List of constraint bounds
        objective_coefficients: Optional objective weights
    """
    variables_referenced: List[str]
    bounds: List[ConstraintBound]
    objective_coefficients: Optional[Dict[str, float]]


class NutrientBound(TypedDict, total=False):
    """Nutrient bound constraint from constraints.json.

    Attributes:
        constraint_id: Unique constraint identifier
        nutrient_id: Nutrient being constrained
        lp_coefficients: LP formulation
        tier: Constraint priority tier
    """
    constraint_id: str
    nutrient_id: str
    lp_coefficients: LpCoefficients
    tier: ConstraintTier


class ToxicologicalLimit(TypedDict, total=False):
    """Toxicological limit from toxicological_limits.json.

    Attributes:
        nutrient_id: Nutrient identifier
        sul: Safe upper limit dict with value/unit
    """
    nutrient_id: str
    sul: Dict[str, Optional[float]]


# ── TypedDict: Scenario & Target Structures ─────────────────────────────────


class TargetValue(TypedDict):
    """Target value for a nutrient in scenarios.json.

    Attributes:
        nutrient_id: Nutrient identifier
        value: Target numeric value
        unit: Unit string
    """
    nutrient_id: str
    value: float
    unit: str


class Scenario(TypedDict, total=False):
    """Scenario definition from scenarios.json.

    Attributes:
        scenario_id: Unique scenario identifier
        display_name: Human-readable name
        targets: List of nutrient targets
        k_multiplier_ref: Reference to k_multiplier in growth_energy_skeletal.json
    """
    scenario_id: str
    display_name: str
    targets: List[TargetValue]
    k_multiplier_ref: Optional[str]


# ── TypedDict: LP Parameters ────────────────────────────────────────────────


class CategoryGoal(TypedDict):
    """Category goal for cascade level.

    Attributes:
        target_pct: Target percentage (should sum to 100 per level)
        tolerance: Allowed deviation from target
    """
    target_pct: float
    tolerance: Optional[float]


class CascadeLevelConfig(TypedDict, total=False):
    """Solve cascade level configuration from lp_parameters_data.json.

    Attributes:
        level: Cascade level (1, 2, or 3)
        relax_tiers: List of tiers to relax at this level
        category_goals: Dict of category -> goal
        apply_clinical_floor: Whether to apply clinical floor
    """
    level: int
    relax_tiers: List[ConstraintTier]
    category_goals: Dict[str, CategoryGoal]
    apply_clinical_floor: bool


class SolverParams(TypedDict, total=False):
    """Solver parameters from lp_parameters_data.json.

    Attributes:
        tie_break_weight: Weight for deterministic tie-breaking
        fix_optimum_tolerance_abs: Absolute tolerance for fixing optimum
        fix_optimum_tolerance_rel: Relative tolerance for fixing optimum
        category_goals_enabled: Whether category goals are active
        max_iterations: Maximum solver iterations
        time_limit: Time limit in seconds
    """
    tie_break_weight: float
    fix_optimum_tolerance_abs: float
    fix_optimum_tolerance_rel: float
    category_goals_enabled: bool
    max_iterations: int
    time_limit: int


class NUTRIENT_REGISTRY_Entry(TypedDict, total=False):
    """NUTRIENT_REGISTRY entry from lp_parameters_data.json.

    Attributes:
        nutrient_id: Nutrient identifier
        display_name: Human-readable name
        unit: Unit string
        constraint_tier: Priority tier
        clinical_criticality: Clinical priority
        aafco_minimum: AAFCO minimum requirement
        aafco_maximum: AAFCO maximum limit
    """
    nutrient_id: str
    display_name: str
    unit: str
    constraint_tier: ConstraintTier
    clinical_criticality: ClinicalCriticality
    aafco_minimum: Optional[float]
    aafco_maximum: Optional[float]


class LPParametersData(TypedDict, total=False):
    """lp_parameters_data.json root structure.

    Attributes:
        NUTRIENT_REGISTRY: Dict of nutrient_id -> entry
        solve_cascade: List of cascade level configs
        solver_params: Solver configuration
    """
    NUTRIENT_REGISTRY: Dict[str, NUTRIENT_REGISTRY_Entry]
    solve_cascade: List[CascadeLevelConfig]
    solver_params: SolverParams


# ── TypedDict: Audit Provenance ─────────────────────────────────────────────


class ReferenceEntry(TypedDict, total=False):
    """Reference entry from audit_provenance.json.

    Attributes:
        ref_id: Reference identifier
        title: Publication title
        authors: List of author names
        year: Publication year
        quality_flag: Quality assessment flag
        url: URL to source
    """
    ref_id: str
    title: str
    authors: Optional[List[str]]
    year: Optional[int]
    quality_flag: str
    url: Optional[str]


class AuditProvenance(TypedDict, total=False):
    """audit_provenance.json root structure.

    Attributes:
        references: Dict of ref_id -> entry
        last_audit_date: ISO date string
        auditor: Auditor name
    """
    references: Dict[str, ReferenceEntry]
    last_audit_date: str
    auditor: str


# ── TypedDict: DB Metadata ──────────────────────────────────────────────────


class DBMetadata(TypedDict, total=False):
    """Database metadata from DB_ingredientes.json.

    Attributes:
        version: Database version string
        schema_version: Schema version string
        last_updated: ISO date string
    """
    version: str
    schema_version: str
    last_updated: str


class ProteinSourceGroup(TypedDict):
    """Protein source group in DB_ingredientes.json.

    Attributes:
        ingredients: List of ingredients in this group
    """
    ingredients: List[Ingredient]


class DBIngredientes(TypedDict, total=False):
    """DB_ingredientes.json root structure.

    Attributes:
        _db_metadata: Database metadata
        protein_sources: Dict of group_name -> group
    """
    _db_metadata: DBMetadata
    protein_sources: Dict[str, ProteinSourceGroup]


# ── Dataclasses: Runtime Request/Response ───────────────────────────────────


@dataclass
class AnimalInput:
    """Animal input for solver request.

    Attributes:
        sex: "male" or "female"
        weight_kg: Body weight in kilograms
        age_months: Age in months
        gonadal_status: "intact", "neutered", or "spayed"
        height_cm: Optional height in centimeters
        use_gompertz: Whether to use Gompertz model for weight
    """
    sex: Literal["male", "female"]
    weight_kg: float
    age_months: int
    gonadal_status: Literal["intact", "neutered", "spayed"]
    height_cm: Optional[float] = None
    use_gompertz: bool = True


@dataclass(frozen=True)
class DerEnvelope:
    """DER calculation results (immutable after creation).

    This dataclass satisfies both:
      - 3-tuple unpacking contract via __iter__ (der_kcal, min_total_g, max_total_g)
      - Named attribute access for intermediate values

    Attributes:
        bw_kg: Body weight in kg (Gompertz or informed)
        ter_kcal: Total energy requirement in kcal
        k_multiplier: Activity/growth multiplier
        der_kcal: Digestible energy requirement in kcal
        units_of_1000kcal: DER / 1000 (for normalization)
        min_total_g: Minimum envelope bound in grams
        max_total_g: Maximum envelope bound in grams
        strategy: Strategy identifier (default: "der_derived")
        density_source: Source of energy density range
    """
    bw_kg: float
    ter_kcal: float
    k_multiplier: float
    der_kcal: float
    units_of_1000kcal: float
    min_total_g: float
    max_total_g: float
    strategy: str = "der_derived"
    density_source: str = ""

    def __iter__(self):
        """Unpack as (der_kcal, min_total_g, max_total_g)."""
        return iter((self.der_kcal, self.min_total_g, self.max_total_g))

    def __len__(self) -> int:
        """Return 3 for tuple protocol."""
        return 3

    def __getitem__(self, index: int) -> float:
        """Index access for tuple protocol."""
        return (self.der_kcal, self.min_total_g, self.max_total_g)[index]

    def as_envelope_dict(self) -> Dict[str, Any]:
        """Convert to envelope dict for solver consumption."""
        return {
            "min_total_g": self.min_total_g,
            "max_total_g": self.max_total_g,
            "actual_total_g": None,
            "strategy": self.strategy,
        }

    def as_animal_context(
        self,
        sex: str,
        age_months: int,
        gonadal_status: str,
        bw_source: str = "gompertz"
    ) -> Dict[str, Any]:
        """Convert to animal context dict."""
        return {
            "sex": sex,
            "weight_kg": self.bw_kg,
            "age_months": age_months,
            "gonadal_status": gonadal_status,
            "der_kcal": self.der_kcal,
            "ter_kcal": self.ter_kcal,
            "k_multiplier": self.k_multiplier,
            "bw_source": bw_source,
        }


@dataclass
class SolverRequest:
    """Solver request structure.

    Attributes:
        animal: Animal input data
        selected_ingredient_ids: List of ingredient IDs to include
        mode: Solver mode ("adequacy", "optimization", "what_if")
        scenario_id: Scenario identifier (default: "SCN_B_SLOW_GROWTH")
    """
    animal: AnimalInput
    selected_ingredient_ids: List[str]
    mode: Literal["adequacy", "optimization", "what_if"]
    scenario_id: str = "SCN_B_SLOW_GROWTH"


# ── TypedDict: Solver Output Contract ───────────────────────────────────────


class AllocationEntry(TypedDict):
    """Single allocation in solver output.

    Attributes:
        ingredient_id: Ingredient identifier
        grams_per_day: Daily amount in grams
        pct_of_total: Percentage of total diet
        category: Ingredient category
    """
    ingredient_id: str
    grams_per_day: float
    pct_of_total: float
    category: str


class NutrientResult(TypedDict):
    """Nutrient result in solver output.

    Attributes:
        nutrient_id: Nutrient identifier
        achieved_per_day: Achieved amount per day
        target_per_day: Target amount per day
        sul_per_day: Safe upper limit per day
        pct_of_min: Percentage of minimum requirement
        pct_of_sul: Percentage of safe upper limit
        status: Adequacy status
        constraint_tier: Constraint tier
        clinical_criticality: Clinical priority
    """
    nutrient_id: str
    achieved_per_day: float
    target_per_day: float
    sul_per_day: float
    pct_of_min: float
    pct_of_sul: float
    status: Literal["adequate", "deficient", "excessive", "unknown"]
    constraint_tier: ConstraintTier
    clinical_criticality: ClinicalCriticality


class DiagnosticAnalysis(TypedDict, total=False):
    """Diagnostic analysis for Level 3 (infeasibility).

    Attributes:
        blocking_constraints: List of blocking constraint IDs
        minimum_relaxation_to_feasibility: Dict of constraint -> relaxation
        suggested_ingredient_additions: List of suggested ingredients
        bottleneck_nutrients: List of bottleneck nutrients
    """
    blocking_constraints: List[str]
    minimum_relaxation_to_feasibility: Dict[str, float]
    suggested_ingredient_additions: List[str]
    bottleneck_nutrients: List[str]


class LexicographicStages(TypedDict, total=False):
    """Lexicographic solve stages metadata.

    Attributes:
        order_verified: Whether order was verified
        stages_count: Number of stages executed
        relaxed_tiers: List of relaxed tiers
    """
    order_verified: bool
    stages_count: int
    relaxed_tiers: List[ConstraintTier]


class SolverMetadata(TypedDict, total=False):
    """Solver metadata in output.

    Attributes:
        clinical_floor_applied: Whether clinical floor was applied
        clinical_floor_bounds: Dict of nutrient -> bound
        clinical_floor_relaxation_note: Note on relaxation
        lexicographic_stages: Stage metadata
        cascade_level_used: Cascade level that produced solution
        solve_time_ms: Solve time in milliseconds
    """
    clinical_floor_applied: bool
    clinical_floor_bounds: Dict[str, float]
    clinical_floor_relaxation_note: Optional[str]
    lexicographic_stages: LexicographicStages
    cascade_level_used: int
    solve_time_ms: float


class SolverOutput(TypedDict, total=False):
    """Complete solver output contract per §8.1.

    Attributes:
        solver_status: Solver termination status
        cascade_level_used: Cascade level that produced solution
        feeding_recommendation: Feeding recommendation
        allocations: List of ingredient allocations (if optimal)
        nutrient_results: List of nutrient adequacy results
        diagnostic_analysis: Diagnostic info (if infeasible)
        lexicographic_stages: Stage metadata
        solver_metadata: Additional metadata
        warnings: List of warning messages
    """
    solver_status: SolverStatus
    cascade_level_used: int
    feeding_recommendation: FeedingRecommendation
    allocations: Optional[List[AllocationEntry]]
    nutrient_results: List[NutrientResult]
    diagnostic_analysis: Optional[DiagnosticAnalysis]
    lexicographic_stages: LexicographicStages
    solver_metadata: SolverMetadata
    warnings: List[str]


# ── TypedDict: MAPA Validation ──────────────────────────────────────────────


class ValidationResult(TypedDict, total=False):
    """Validation result for MAPA gate.

    Attributes:
        check_name: Name of validation check
        passed: Whether check passed
        message: Human-readable message
        details: Optional detailed info
    """
    check_name: str
    passed: bool
    message: str
    details: Optional[Dict[str, Any]]


class CrossRefIndexData(TypedDict, total=False):
    """Cross-reference index data.

    Attributes:
        all_known_tokens: Set of all known token IDs
        ingredient_index: Dict of ingredient_id -> Ingredient
        nutrient_index: Dict of nutrient_id -> registry entry
        ref_index: Dict of ref_id -> quality flag
        constraint_index: Dict of constraint_id -> section
        weight_index: Dict of weight_id -> weight data
        scenario_index: Dict of scenario_id -> Scenario
        db2solver_name_map: DB key -> solver key mapping
        solver2db_name_map: Solver key -> DB key mapping
        all_ingredients: List of all ingredients
    """
    all_known_tokens: Set[str]
    ingredient_index: Dict[str, Ingredient]
    nutrient_index: Dict[str, NUTRIENT_REGISTRY_Entry]
    ref_index: Dict[str, str]
    constraint_index: Dict[str, str]
    weight_index: Dict[str, Any]
    scenario_index: Dict[str, Scenario]
    db2solver_name_map: Dict[str, str]
    solver2db_name_map: Dict[str, str]
    all_ingredients: List[Ingredient]


# ── Protocol Types for Dependency Injection ─────────────────────────────────


class DatabaseProtocol(Protocol):
    """Protocol for database access layer."""

    def get_ingredient(self, ingredient_id: str) -> Optional[Ingredient]: ...
    def get_all_ingredients(self) -> List[Ingredient]: ...
    def get_nutrient_registry(self) -> Dict[str, NUTRIENT_REGISTRY_Entry]: ...


class SolverProtocol(Protocol):
    """Protocol for LP solver backend."""

    def solve(
        self,
        coefficients: Dict[str, Dict[str, float]],
        targets: Dict[str, float],
        bounds: Dict[str, Tuple[float, float]]
    ) -> SolverOutput: ...


# ── Type Aliases ────────────────────────────────────────────────────────────

NutrientMatrix = Dict[str, Dict[str, NutrientEntry]]
"""Nutrient matrix: ingredient_id -> nutrient_id -> entry."""

CompiledCoefficients = Dict[str, Dict[str, float]]
"""LP coefficients: variable_id -> nutrient_id -> coefficient."""

IngredientId = str
"""Type alias for ingredient identifier."""

NutrientId = str
"""Type alias for nutrient identifier."""

ConstraintId = str
"""Type alias for constraint identifier."""

RefId = str
"""Type alias for reference identifier."""

# JSON-like types for data loading
JSONPrimitive = Union[str, int, float, bool, None]
"""Primitive JSON value."""

JSONDict = Dict[str, Any]
"""JSON object/dict."""

JSONList = List[Any]
"""JSON array/list."""

JSONValue = Union[JSONPrimitive, JSONDict, JSONList]
"""Any JSON value."""


# ── Helper Type Functions (Type Guards) ─────────────────────────────────────


def is_measured(entry: NutrientEntry) -> bool:
    """Type guard: check if nutrient entry is measured.

    Args:
        entry: NutrientEntry to check

    Returns:
        True if status is "measured" and value is not None
    """
    return entry.get("status") == "measured" and entry.get("value") is not None


def get_value(entry: NutrientEntry, default: float = 0.0) -> float:
    """Safely extract value from nutrient entry.

    Args:
        entry: NutrientEntry to extract from
        default: Default value if not measured

    Returns:
        Float value or default
    """
    if is_measured(entry):
        val = entry.get("value")
        return float(val) if val is not None else default
    return default


__all__ = [
    # Literals
    "NutrientStatus",
    "ConstraintTier",
    "ClinicalCriticality",
    "SolverStatus",
    "CascadeLevel",
    "FeedingRecommendation",
    # TypedDicts - Nutrient
    "NutrientEntry",
    "NutrientEntryMeasured",
    "NutrientEntryMissing",
    "BromatologicalProfile",
    "Ingredient",
    # TypedDicts - Constraints
    "ConstraintBound",
    "LpCoefficients",
    "NutrientBound",
    "ToxicologicalLimit",
    # TypedDicts - Scenarios/LP
    "TargetValue",
    "Scenario",
    "CategoryGoal",
    "CascadeLevelConfig",
    "SolverParams",
    "NUTRIENT_REGISTRY_Entry",
    "LPParametersData",
    # TypedDicts - Audit/DB
    "ReferenceEntry",
    "AuditProvenance",
    "DBMetadata",
    "ProteinSourceGroup",
    "DBIngredientes",
    # TypedDicts - Solver Output
    "AllocationEntry",
    "NutrientResult",
    "DiagnosticAnalysis",
    "LexicographicStages",
    "SolverMetadata",
    "SolverOutput",
    # TypedDicts - Validation
    "ValidationResult",
    "CrossRefIndexData",
    # Protocols
    "DatabaseProtocol",
    "SolverProtocol",
    # Dataclasses
    "AnimalInput",
    "DerEnvelope",
    "SolverRequest",
    # Type aliases
    "NutrientMatrix",
    "CompiledCoefficients",
    "IngredientId",
    "NutrientId",
    "ConstraintId",
    "RefId",
    "JSONPrimitive",
    "JSONDict",
    "JSONList",
    "JSONValue",
    # Helper functions
    "is_measured",
    "get_value",
]
```

**Validation:** Run `python -c "import sys; sys.path.insert(0, '/workspace/src'); from gsd import types; print(len(types.__all__))"` → Should print count > 40

---

## PHASE 2: CORE MODULE ANNOTATIONS (P0)

### Task 2.1: Annotate src/gsd/core.py

**File:** `/workspace/src/gsd/core.py`
**Operation:** STR_REPLACE in multiple passes
**Strategy:** Annotate from top to bottom, one function class at a time

#### Step 2.1.1: Update Imports
**Location:** Lines 17-30
**Action:** Add types imports after existing imports

```python
from .types import (
    DBIngredientes,
    LPParametersData,
    AuditProvenance,
    Ingredient,
    NUTRIENT_REGISTRY_Entry,
    Scenario,
    JSONDict,
    is_measured,
    get_value,
    NutrientStatus,
)
```

#### Step 2.1.2: Annotate sha256_file
**Location:** Line 80-85
**Current:** `def sha256_file(path: Path) -> str:`
**Action:** Already annotated - VERIFY

#### Step 2.1.3: Annotate validate_category_goals
**Location:** Lines 93-114
**Replace signature with:**
```python
def validate_category_goals(
    lp_params: LPParametersData,
    tolerance: float = 0.01
) -> None:
```

#### Step 2.1.4: Annotate load_all_jsons
**Location:** Lines 117-131
**Replace signature with:**
```python
def load_all_jsons() -> Dict[str, JSONDict]:
```

#### Step 2.1.5: Annotate fmt
**Location:** Lines 134-150
**Action:** Already annotated - VERIFY

#### Step 2.1.6: Annotate _get_param
**Location:** Lines 198-206
**Replace signature with:**
```python
def _get_param(
    params: List[Dict[str, Any]],
    param_id: str
) -> Optional[Dict[str, Any]]:
```

#### Step 2.1.7: Annotate _resolve_breed_value
**Location:** Lines 209-219
**Replace signature with:**
```python
def _resolve_breed_value(
    value_field: Union[Dict[str, float], float],
    default_line: str = "working_exhibition_lines"
) -> float:
```

#### Step 2.1.8: Annotate build_mapa_indices
**Location:** Lines 363-430
**Replace signature with:**
```python
def build_mapa_indices(data: Dict[str, JSONDict]) -> CrossRefIndex:
```

**Validation:** Run `mypy /workspace/src/gsd/core.py --no-error-summary` → Zero errors expected

---

## PHASE 3: NUTRITION MODULE ANNOTATIONS (P0)

### Task 3.1: Annotate src/gsd/nutrition.py

**File:** `/workspace/src/gsd/nutrition.py`
**Operation:** STR_REPLACE

#### Step 3.1.1: Update Imports
**Add after line 6:**
```python
from .types import (
    NutrientEntry,
    NutrientMatrix,
    Ingredient,
    BromatologicalProfile,
    is_measured,
    get_value,
)
```

#### Step 3.1.2: Annotate validate_inputs
**Location:** Lines 17-93
**Replace signature with:** `def validate_inputs(data: Dict[str, JSONDict]) -> None:`

#### Step 3.1.3: Annotate gompertz_weight
**Location:** Lines 98-118
**Replace signature with:**
```python
def gompertz_weight(
    age_months: int,
    params: List[Dict[str, Any]],
    sex: str,
    default_breed_line: str = "working_exhibition_lines"
) -> float:
```

#### Step 3.1.4: Annotate calculate_der_and_envelope
**Location:** Lines 134-197
**Replace signature with:**
```python
def calculate_der_and_envelope(
    animal: AnimalInput,
    growth_data: Dict[str, Any],
    scenario_id: str,
    selected_ids: List[str],
    db: DBIngredientes,
    default_breed_line: str = "working_exhibition_lines",
) -> DerEnvelope:
```

#### Step 3.1.5: Annotate build_matrix
**Location:** Lines 323-350
**Replace signature with:**
```python
def build_matrix(
    selected_ids: List[str],
    db: DBIngredientes,
    formulation_rules: Dict[str, Any]
) -> NutrientMatrix:
```

**Validation:** Run `mypy /workspace/src/gsd/nutrition.py --no-error-summary` → Zero errors expected

---

## PHASE 4: SOLVER MODULE ANNOTATIONS (P0)

### Task 4.1: Annotate src/gsd/solver.py

**File:** `/workspace/src/gsd/solver.py`
**Operation:** STR_REPLACE

#### Step 4.1.1: Update Imports
**Add after line 6:**
```python
from .types import (
    SolverOutput,
    AllocationEntry,
    NutrientResult,
    DiagnosticAnalysis,
    SolverMetadata,
    LexicographicStages,
    NutrientMatrix,
    CompiledCoefficients,
    SolverStatus,
    FeedingRecommendation,
)
```

#### Step 4.1.2: Annotate derive_tie_break_bound
**Location:** Lines 21-61
**Replace signature with:**
```python
def derive_tie_break_bound(
    solver_params: Dict[str, Any],
    max_single_ingredient_grams: float
) -> Dict[str, Any]:
```

#### Step 4.1.3: Annotate build_lp_problem
**Location:** Lines 101-576
**Replace signature with:**
```python
def build_lp_problem(
    matrix: NutrientMatrix,
    der_info: DerEnvelope,
    formulation_rules: Dict[str, Any],
    constraints: Dict[str, Any],
    selected_ids: List[str],
) -> Dict[str, Any]:
```

#### Step 4.1.4: Annotate call_lp_solver
**Location:** Lines 577-721
**Replace signature with:**
```python
def call_lp_solver(
    problem_dict: Dict[str, Any],
    objective_stages: List[Dict[str, Any]],
    solver_params: Dict[str, Any]
) -> Dict[str, Any]:
```

#### Step 4.1.5: Annotate solve_cascade
**Location:** Lines 884-981
**Replace signature with:**
```python
def solve_cascade(
    selected_ids: List[str],
    data: Dict[str, JSONDict],
    der_info: DerEnvelope,
    scenario_id: str,
    animal: AnimalInput
) -> SolverOutput:
```

#### Step 4.1.6: Annotate build_output_contract
**Location:** Lines 1152-1360
**Replace signature with:**
```python
def build_output_contract(
    raw_result: Dict[str, Any],
    data: Dict[str, JSONDict],
    der_info: DerEnvelope,
    level: int
) -> SolverOutput:
```

**Validation:** Run `mypy /workspace/src/gsd/solver.py --no-error-summary` → Zero errors expected

---

## PHASE 5: MAPA MODULE ANNOTATIONS (P1)

### Task 5.1: Annotate src/gsd/mapa.py

**File:** `/workspace/src/gsd/mapa.py`
**Operation:** STR_REPLACE

#### Step 5.1.1: Update Imports
**Add after line 8:**
```python
from .types import (
    CrossRefIndexData,
    ValidationResult,
    DBIngredientes,
    LPParametersData,
    AuditProvenance,
    Ingredient,
    Scenario,
    JSONDict,
)
```

#### Step 5.1.2: Annotate generate_mapa
**Location:** Lines 1115-1197
**Replace signature with:**
```python
def generate_mapa(
    data: Optional[Dict[str, JSONDict]] = None,
    no_live_evidence: bool = False
) -> str:
```

#### Step 5.1.3: Annotate validate_mapa
**Location:** Lines 1198-end
**Replace signature with:**
```python
def validate_mapa(
    mapa_content: str,
    data: Optional[Dict[str, JSONDict]] = None,
    prev_state_hash: Optional[str] = None
) -> List[str]:
```

**Validation:** Run `mypy /workspace/src/gsd/mapa.py --no-error-summary` → Zero errors expected

---

## PHASE 6: CLI MODULE ANNOTATIONS (P1)

### Task 6.1: Annotate src/gsd/cli.py

**File:** `/workspace/src/gsd/cli.py`
**Operation:** STR_REPLACE

#### Step 6.1.1: Update Imports
**Add after line 9:**
```python
from .types import (
    SolverRequest,
    AnimalInput,
    SolverOutput,
    JSONDict,
)
```

#### Step 6.1.2: Annotate main
**Location:** Lines 32-270
**Replace signature with:** `def main() -> None:`

**Validation:** Run `mypy /workspace/src/gsd/cli.py --no-error-summary` → Zero errors expected

---

## PHASE 7: DOC_INTROSPECTOR MODULE ANNOTATIONS (P1)

### Task 7.1: Annotate src/gsd/doc_introspector.py

**File:** `/workspace/src/gsd/doc_introspector.py`
**Operation:** STR_REPLACE

#### Step 7.1.1: Update ImplCheck dataclass
**Location:** Lines 22-30
**Already has types - VERIFY**

#### Step 7.1.2: Annotate compute_satellite_stats
**Location:** Find function, add return type `-> Dict[str, Any]`

#### Step 7.1.3: Annotate check_structure_contracts
**Location:** Find function, add return type `-> Dict[str, Any]`

**Validation:** Run `mypy /workspace/src/gsd/doc_introspector.py --no-error-summary` → Zero errors expected

---

## PHASE 8: TESTING & VALIDATION (P0)

### Task 8.1: Create Type Check Script

**File:** `/workspace/scripts/type_check.sh`
**Operation:** CREATE NEW FILE

```bash
#!/bin/bash
set -e

echo "=== Running mypy type checker ==="
cd /workspace
mypy src/gsd/ --show-error-codes --pretty

echo "=== Running ruff linter ==="
ruff check src/gsd/

echo "=== All type checks passed ==="
```

**Make executable:** `chmod +x /workspace/scripts/type_check.sh`

### Task 8.2: Add Pre-commit Hook

**File:** `/workspace/.pre-commit-config.yaml`
**Operation:** CREATE IF NOT EXISTS

```yaml
repos:
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        args: [--strict, --show-error-codes]
        additional_dependencies:
          - typing-extensions>=4.9.0
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
```

### Task 8.3: Run Full Type Check Suite

**Command:** `/workspace/scripts/type_check.sh`
**Expected Result:** Exit code 0, zero mypy errors
**Failure Action:** Fix reported errors iteratively

---

## PHASE 9: CI/CD INTEGRATION (P1)

### Task 9.1: Create GitHub Actions Workflow

**File:** `/workspace/.github/workflows/type-check.yml`
**Operation:** CREATE NEW FILE

```yaml
name: Type Check

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"

      - name: Install dependencies
        run: |
          pip install -e .
          pip install mypy>=1.8.0 typing-extensions>=4.9.0 ruff>=0.1.0

      - name: Run mypy
        run: mypy src/gsd/ --strict --show-error-codes

      - name: Run ruff
        run: ruff check src/gsd/
```

---

## PHASE 10: DOCUMENTATION UPDATE (P2)

### Task 10.1: Update Architecture Docs

**File:** `/workspace/docs/architecture/type-safety-guide.md`
**Operation:** CREATE NEW FILE

Document:
- Type hierarchy overview
- When to use TypedDict vs dataclass
- Type guard patterns
- Migration checklist for future modules

---

## SUCCESS CRITERIA

1. **Zero mypy errors** across all 6 modules with strict mode
2. **100% type coverage**: All public functions have signatures
3. **No runtime regressions**: All existing tests pass
4. **CI pipeline green**: GitHub Actions type-check job passes
5. **Documentation complete**: Type safety guide published

---

## ROLLBACK PROCEDURE

If type annotations cause issues:

1. `git checkout main` to revert all changes
2. Remove `types.py`: `rm /workspace/src/gsd/types.py`
3. Restore original `pyproject.toml` from git
4. Report failure mode with mypy error logs

---

## EXECUTION ORDER SUMMARY

| Phase | Tasks | Priority | Estimated Time |
|-------|-------|----------|----------------|
| 0 | Preconditions | P0 | 5 min |
| 1 | Foundation (types.py + config) | P0 | 15 min |
| 2 | core.py annotations | P0 | 20 min |
| 3 | nutrition.py annotations | P0 | 15 min |
| 4 | solver.py annotations | P0 | 30 min |
| 5 | mapa.py annotations | P1 | 20 min |
| 6 | cli.py annotations | P1 | 10 min |
| 7 | doc_introspector.py | P1 | 15 min |
| 8 | Testing & validation | P0 | 15 min |
| 9 | CI/CD integration | P1 | 10 min |
| 10 | Documentation | P2 | 20 min |
| **TOTAL** | | | **~3 hours** |

---

**END OF EXECUTION PLAN**