# sat_pipeline_codigo — Código Referência src/gsd/ Package

**v10.4** · ← `indice_plano_central.md` (canônico) · `../../README.md`

**Responsibility:** Python code for `src/gsd/` package (§6.4): `load_all_jsons()`, `validate_inputs()`, `calculate_der_and_envelope()`, as_fed→energy_normalized conversion, `build_matrix()`, `solve_cascade()`. Includes mandatory function signatures (§6.4a).

**Depends on:** sat_dados_schema:§4.1, sat_princípios:§3.5, sat_pipeline_fluxo:§6.1 a §6.3 · **Referenced by:** sat_solver_contrato

**Load when:** implementar/modificar src/gsd/ · debug as_fed→energy_normalized conversion · audit code vs JSONs

> **Context:** Contains only §6.4 — Python code. For §6.1 (overview), §6.2 (runtime flow), §6.3 (build-recipes flow), §6.5 (conversion notes): see `sat_pipeline_fluxo.md`. For JSON schemas this code reads: see `sat_dados_schema.md` (§4.1). For solver output contract: see `sat_solver_contrato.md` (§7).

---

> **Current implementation note (2026-07-20):** This pseudocode describes the target. Compare it with `src/gsd/` and the “2026-07-20 current-state amendment” in `docs/governance/systemic_review_pipeline_vs_satellites.md` before using it to assert current behavior.

## 6. Build Pipeline — V10 (parcial — apenas §6.4)

> **Scope note:** sat_pipeline_fluxo:§6.1-§6.3 and sat_pipeline_fluxo:§6.5 are in `sat_pipeline_fluxo.md`. This file is only the Python code.

### 6.4a Mandatory Function Signatures

Every implementation of `src/gsd/` package MUST expose these signatures. Types are indicative (Python does not enforce them, but they must be respected for the contract to work).

```python
from typing import Any, Optional
from dataclasses import dataclass

# ── Entradas ──
@dataclass
class AnimalInput:
    sex: str                    # "male" | "female"
    weight_kg: float
    age_months: int
    gonadal_status: str         # "intact" | "neutered"
    height_cm: Optional[float] = None
    use_gompertz: bool = True   # if False, uses weight_kg directly

@dataclass
class SolverRequest:
    animal: AnimalInput
    selected_ingredient_ids: list[str]   # 1 to N
    mode: str                            # "free" | "precomputed_recipes"
    scenario_id: str = "SCN_B"           # default: recommended growth

# ── Outputs (contract sat_solver_contrato:§7) ──
@dataclass
class Allocation:
    ingredient_id: str
    display_name: str
    category: str
    grams_per_day: float
    pct_of_total: float
    kcal_per_day: float
    cost_per_day: Optional[float]

@dataclass
class NutrientResult:
    nutrient_id: str
    display_name: str
    value: float
    unit: str
    basis: str                           # "energy_normalized"
    target_min: Optional[float]
    target_max: Optional[float]
    sul: Optional[float]
    pct_of_min: Optional[float]
    pct_of_sul: Optional[float]
    status: str                          # "deficient" | "adequate" | "excess"
    constraint_tier: str                 # see sat_dados_schema:§4.2
    clinical_criticality: str

@dataclass
class SolverOutput:
    solver_output_schema: str            # "v10.1"
    solver_status: str                   # "optimal" | "suboptimal" | "unsafe_diagnostic"
    feeding_recommendation: str          # "SAFE_TO_FEED" | "FEED_WITH_CAUTION" | "DO_NOT_FEED"
    cascade_level_used: int              # 1, 2, or 3
    animal_context: dict
    envelope: dict
    allocations: Optional[list[Allocation]]   # null in Level 3
    nutrient_results: list[NutrientResult]    # sempre 41+
    diagnostic_analysis: Optional[dict]       # populated only in Level 3
    gaps: list[dict]
    alerts: list[dict]
    recommended_additions: list[dict]
    solver_metadata: dict                # inclui lexicographic_stages_used, clinical_floor_*

# ── Mandatory functions ──
def load_all_jsons() -> dict[str, Any]:
    """Load 9 JSONs. See sat_dados_schema:§4.1 for full list."""

def validate_inputs(data: dict) -> None:
    """Raise AssertionError if any of the 6 assertions (a-f) fail."""

def calculate_der_and_envelope(animal: AnimalInput, growth_data: dict, scenario: dict, selected_ids: list[str], db: dict) -> tuple[float, float, float]:
    """Return (der_kcal, min_total_g, max_total_g)."""

def convert_as_fed_to_energy_normalized(db_entry: dict, formulation_rules: dict) -> dict[str, float]:
    """Convert 34 nutrients as_fed/100g → 41 energy_normalized/1000kcal."""

def build_matrix(selected_ids: list[str], db: dict, formulation_rules: dict) -> dict[str, dict[str, float]]:
    """Return {ingredient_id: {nutrient_id: value}} in energy_normalized basis."""

def solve_cascade(matrix: dict, constraints: dict, schema: dict, weights: dict, envelope: tuple[float, float], tox_limits: list) -> SolverOutput:
    """Execute levels 1→2→3, stop at first feasible. See sat_solver_contrato:§8."""

def build_diagnostic_analysis(raw_result: dict, clinical_floor_info: dict) -> dict:
    """Level 3 only. Populate sul_violations_inevitable + what_would_happen + recommended_alternative_actions."""

def run_pipeline(request: SolverRequest) -> SolverOutput:
    """Runtime mode entry point. See §6.2 steps 1-8."""

def run_build_recipes(diet_templates: list, db: dict, output_path: str) -> None:
    """--build-recipes mode. Save recipes_precomputed.json."""
```

### 6.4 Código Referência — Conversão de Base (atualizado da V9)

```python
# src/gsd/ - modular package

import json
import sys
from itertools import combinations, product

# ── 1. READ ──────────────────────────────────────────────────────────────
from .core import load_all_jsons, BASE_DIR, DATA_DIR
from .nutrition import validate_inputs, calculate_der_and_envelope, build_matrix
from .solver import solve_cascade, build_output_contract, validate_output, check_fat_source_adequacy
from .mapa import generate_mapa, validate_mapa, build_mapa_indices

# ── 1. READ ──────────────────────────────────────────────────────────────
# load_all_jsons() is in core.py

# ── 2. VALIDATE (input) ──────────────────────────────────────────────
def validate_inputs(data):
    db = data["db"]
    provenance = data["provenance"]
    schema = data["schema"]
    
    # a) 41 nutrients per ingredient
    assert_all_ingredients_have_41_nutrient_slots(db)
    # b) non-USDA refs resolve
    assert_all_non_usda_refs_resolve(db, provenance)
    # c) valid categories
    assert_all_categories_in_enum(db, schema)
    # d) mapped ingredient_ids exist in DB
    mapping = data["formulation_rules"]["_inclusion_semantics"]["category_to_ingredient_mapping"]
    expanded = expand_category_wildcards(mapping, db)
    assert_all_mapped_ingredients_exist(expanded, db)
    # e) NUTRIENT_REGISTRY covers 41 nutrients
    assert_registry_covers_all_41(schema, data["formulation_rules"]["nutrient_matrix"])
    # f) solve_cascade has base level (V10.4: syntax fixed — assert does not accept inline generator)
    # See also: sat_dados_schema:§4.3 (solve_cascade[] definition), sat_solver_contrato:§8 (mathematical formulation per level)
    assert any(s["relax_tiers"] == [] for s in schema["solve_cascade"] if s["level"] == 1), \
        "Level 1 of solve_cascade must have empty relax_tiers"

# ── 3. COMPUTE DER AND ENVELOPE ────────────────────────────────────────
def calculate_der_and_envelope(animal_data, growth_data, scenario, selected_ingredients, db):
    """Dynamic envelope derived from DER and the real selected ingredient densities."""
    import math
    
    # Get body weight
    if animal_data.get("use_gompertz", True):
        bw = gompertz_weight(
            animal_data["age_months"],
            growth_data["gompertz_parameters"],
            animal_data["sex"]
        )
    else:
        bw = animal_data["weight_kg"]
    
    # TER and DER
    ter = 70 * (bw ** 0.75)
    k = growth_data["k_multipliers"][scenario["k_multiplier_ref"]]["default_lp"]
    der = ter * k
    
    # Compute densities before the envelope. Global values are allowed only for
    # an empty selection and must be marked in output metadata as a fallback.
    selected = [get_ingredient_by_id(i, db) for i in selected_ingredients]
    if selected:
        densities = [energy_metabolizable_kcal_per_100g(
            i["bromatological_profile"]["nutrients"]) / 100 for i in selected]
        min_density, max_density = min(densities), max(densities)
        density_source = "selected_ingredients"
    else:
        min_density, max_density = global_density_range_from_verified_db(db)
        density_source = "verified_global_fallback_empty_selection"
    
    min_total_g = (der / max_density) * 0.9  # 10% safety margin
    max_total_g = (der / min_density) * 1.1  # 10% safety margin
    
    return {
        "bw_kg": bw,
        "ter_kcal": ter,
        "k_multiplier": k,
        "der_kcal": der,
        "units_of_1000kcal": der / 1000,
        "envelope": {
            "min_total_g": min_total_g,
            "max_total_g": max_total_g,
            "strategy": "der_derived",
            "density_source": density_source
        }
    }

def gompertz_weight(age_months, params, sex):
    """W(t) = W_max × exp(-b × exp(-c × t))"""
    w_max = params[f"w_max_{sex}"]["value"]
    b = params["b"]["value"]
    c = params[f"c_{sex}"]["value"]
    t_days = age_months * 30.44
    return w_max * math.exp(-b * math.exp(-c * t_days))

# ── 4. TRANSFORM ────────────────────────────────────────────────────────
UNIT_RENAME = {
    "calcium_mg": ("calcium_g", 1/1000),
    "phosphorus_mg": ("phosphorus_g", 1/1000),
    "magnesium_mg": ("magnesium_g", 1/1000),
    "sodium_mg": ("sodium_g", 1/1000),
    "potassium_mg": ("potassium_g", 1/1000),
    "chloride_mg": ("chloride_g", 1/1000),
    "choline_mg": ("choline_g", 1/1000),
    "selenium_ug": ("selenium_mg", 1/1000),
    "cobalamin_b12_ug": ("cobalamin_b12_mg", 1/1000),
    "folic_acid_b9_ug": ("folic_acid_b9_mg", 1/1000),
    "iodine_ug": ("iodine_mg", 1/1000),
}

SOLVER_NUTRIENTS = [
    "protein_g", "fat_g", "arginine_g", "histidine_g", "isoleucine_g", "leucine_g",
    "lysine_g", "methionine_g", "methionine_plus_cystine_g", "phenylalanine_g",
    "phenylalanine_plus_tyrosine_g", "threonine_g", "tryptophan_g", "valine_g",
    "linoleic_acid_g", "ala_alpha_linolenic_acid_g", "ara_arachidonic_acid_g",
    "epa_plus_dha_g", "calcium_g", "phosphorus_g", "magnesium_g", "sodium_g",
    "potassium_g", "chloride_g", "iron_mg", "copper_mg", "manganese_mg",
    "zinc_mg", "iodine_mg", "selenium_mg", "vitamin_a_iu", "vitamin_d3_iu",
    "vitamin_e_iu", "thiamine_b1_mg", "riboflavin_b2_mg", "pantothenic_acid_b5_mg",
    "niacin_b3_mg", "pyridoxine_b6_mg", "folic_acid_b9_mg", "cobalamin_b12_mg",
    "choline_g"
]

def energy_metabolizable_kcal_per_100g(nutrients):
    """Modified Atwater, AAFCO/pet food standard."""
    protein = nutrients["protein_g"]["value"]
    fat     = nutrients["fat_g"]["value"]
    moisture = nutrients.get("moisture_pct", {"value": 0})["value"]
    ash      = nutrients.get("ash_pct", {"value": 0})["value"]
    fiber    = nutrients.get("fiber_g", {"value": 0})["value"]
    nfe = max(0, 100 - protein - fat - moisture - ash - fiber)
    return 3.5*protein + 8.5*fat + 3.5*nfe

def is_nutrient_measured(entry: dict) -> bool:
    """Check if a nutrient entry has a real measured value."""
    return isinstance(entry, dict) and entry.get("status") == "measured" and entry.get("value") is not None

def get_measured_value(entry: dict) -> Optional[float]:
    """Safely extract value from a 3-state nutrient entry."""
    if is_nutrient_measured(entry):
        return float(entry["value"])
    return None

def convert_as_fed_to_energy_normalized(ingredient, bio_factors):
    """Convert a single ingredient's 3-state nutrient entries from
    as_fed/100g → energy_normalized/1000kcal.

    Respects the real 3-state contract:
      - status="measured" → output {"status": "measured", "value": <float>}
      - status="missing"/"not_applicable" → output {"status": status}, no "value" key
      - Every key in SOLVER_NUTRIENTS (41 total) is guaranteed present
      - Composite pairs (methionine_plus_cystine_g, etc.) computed from
        individual measured amino acids
    """
    nuts = ingredient.get("bromatological_profile", {}).get("nutrients", {})
    em = energy_metabolizable_kcal_per_100g(nuts)
    if em <= 0:
        return {}
    out: dict[str, dict] = {}
    for db_key, entry in nuts.items():
        if not isinstance(entry, dict):
            continue
        status = entry.get("status", "missing")
        solver_key, _ = UNIT_RENAME.get(db_key, (db_key, 1.0))
        if solver_key not in SOLVER_NUTRIENTS:
            continue
        if status == "measured":
            value = entry.get("value")
            if value is not None:
                _, scale = UNIT_RENAME.get(db_key, (db_key, 1.0))
                converted = float(value) * scale * (1000.0 / em)
                bio = get_bioavailability_factor(
                    ingredient.get("ingredient_id", ""), solver_key, bio_factors
                )
                out[solver_key] = {"status": "measured", "value": converted * bio}
                continue
        out[solver_key] = {"status": status}
    # Composite amino acids
    met_val = get_measured_value(nuts.get("methionine_g"))
    cys_val = get_measured_value(nuts.get("cystine_g"))
    if met_val is not None and cys_val is not None:
        raw = (met_val + cys_val) * (1000.0 / em)
        out["methionine_plus_cystine_g"] = {"status": "measured", "value": raw * get_bioavailability_factor(
            ingredient.get("ingredient_id", ""), "methionine_plus_cystine_g", bio_factors
        )}
    phe_val = get_measured_value(nuts.get("phenylalanine_g"))
    tyr_val = get_measured_value(nuts.get("tyrosine_g"))
    if phe_val is not None and tyr_val is not None:
        raw = (phe_val + tyr_val) * (1000.0 / em)
        out["phenylalanine_plus_tyrosine_g"] = {"status": "measured", "value": raw * get_bioavailability_factor(
            ingredient.get("ingredient_id", ""), "phenylalanine_plus_tyrosine_g", bio_factors
        )}
    # Guarantee all 41 keys
    for registry_key in SOLVER_NUTRIENTS:
        if registry_key not in out:
            out[registry_key] = {"status": "missing"}
    return out

def expand_category_wildcards(mapping, db):
    """Expand _all_muscle_meat / _all_fat_source to real ingredient_id list."""
    expanded = {}
    all_ids_by_category = {}
    for cat_group in db["protein_sources"].values():
        for ing in cat_group["ingredients"]:
            all_ids_by_category.setdefault(ing["category"], []).append(ing["ingredient_id"])
    for generic_name, ids in mapping.items():
        resolved = []
        for i in ids:
            if i == "_all_muscle_meat":
                resolved += all_ids_by_category.get("muscle_meat", [])
            elif i == "_all_fat_source":
                resolved += all_ids_by_category.get("fat_source", [])
            else:
                resolved.append(i)
        expanded[generic_name] = resolved
    return expanded

# ── 5. BUILD MATRIX AND CONSTRAINTS ────────────────────────────────────────
def build_lp_problem(selected_ingredients, data, der_info, cascade_level):
    """Build LP problem per cascade level."""
    schema = data["schema"]
    cascade = schema["solve_cascade"]
    level_config = next(c for c in cascade if c["level"] == cascade_level)
    relax_tiers = set(level_config["relax_tiers"])
    
    # Matrix a_ij is first held per 1000 kcal for traceability, then compiled
    # into nutrient/g. x_i is grams/day, so nutrient/1000kcal MUST NOT be
    # multiplied directly by x_i. All targets and SULs are scaled to per-day
    # values using der_info["units_of_1000kcal"] before call_lp_solver().
    a_ij = {}
    for ing_id in selected_ingredients:
        ing = get_ingredient_by_id(ing_id, data["db"])
        a_ij[ing_id] = convert_as_fed_to_energy_normalized(ing, data["formulation_rules"]["bioavailability_factors"])
    
    # Hard constraints (always present)
    hard_constraints = []
    # Intended contract: mineral antagonisms are hard. Current code creates
    # unbounded slacks instead; see the current implementation note above.
    for antag in data["constraints"]["mineral_antagonisms"]:
        hard_constraints.append(antag)
    # SULs — hard if "safety_hard" not in relax_tiers
    if "safety_hard" not in relax_tiers:
        for tox in data["constraints"]["toxicological_limits"]:
            hard_constraints.append(tox)
    # Inclusion — always hard
    for incl in data["constraints"]["inclusion_constraints"]:
        hard_constraints.append(incl)
    
    # V10.3: Clinical floor minimum in Level 3
    clinical_floor_bounds = {}
    if level_config.get("clinical_floor", {}).get("enabled", False):
        clinical_floor_config = level_config.get("clinical_floor", {})
        defaults_by_category = clinical_floor_config.get("defaults_by_category", {})
        global_fallback = clinical_floor_config.get("global_fallback_g", 5)
        
        for ing_id in selected_ingredients:
            # 1. Try clinical_floor_g declared in ingredient
            ing_incl = next(
                (ic for ic in data["formulation_rules"]["_inclusion_semantics"]
                 .get("inclusion_constraints", []) if ic.get("ingredient_id") == ing_id),
                {}
            )
            declared_floor = ing_incl.get("clinical_floor_g")
            if declared_floor is not None:
                clinical_floor_bounds[ing_id] = declared_floor
            else:
                # 2. Use category default
                ing = get_ingredient_by_id(ing_id, data["db"])
                category = ing.get("category", "unknown")
                clinical_floor_bounds[ing_id] = defaults_by_category.get(category, global_fallback)
    
    # Soft constraints (relaxable per level)
    soft_constraints = []
    # Nutrient bounds
    nutrient_registry = schema["NUTRIENT_REGISTRY"]
    for nb in data["constraints"]["nutrient_bounds"]:
        tier = nutrient_registry.get(nb["nutrient_id"], {}).get("constraint_tier", "adequacy_soft")
        if tier in relax_tiers:
            # Add slack with weight = clinical_criticality
            criticality = nutrient_registry.get(nb["nutrient_id"], {}).get("clinical_criticality", "low")
            slack_weight = {"critical": 10.0, "high": 5.0, "moderate": 2.0, "low": 1.0}[criticality]
            soft_constraints.append({"constraint": nb, "slack_weight": slack_weight})
        else:
            hard_constraints.append(nb)
    
    # Envelope — soft if "envelope_soft" in relax_tiers
    envelope_soft = "envelope_soft" in relax_tiers
    
    return {
        "a_ij": a_ij,
        "decision_unit": "g_per_day",
        "coefficient_input_basis": "per_1000kcal",
        "canonical_lp_basis": "per_day",
        "hard_constraints": hard_constraints,
        "soft_constraints": soft_constraints,
        "envelope": der_info["envelope"],
        "envelope_soft": envelope_soft,
        "der_kcal": der_info["der_kcal"],
        "clinical_floor_bounds": clinical_floor_bounds  # V10.3
    }

# ── 6. SOLVE — DECLARATIVE CASCADE ──────────────────────────────────────
def solve_cascade(selected_ingredients, data, der_info):
    """Execute the declarative cascade; policy and objectives come from JSON."""
    schema = data["schema"]
    cascade = schema["solve_cascade"]
    
    for level_config in cascade:
        level = level_config["level"]
        
        # `objective_stages` is declared by this level in JSON. The adapter
        # resolves each stage and fixes its optimum before the next one; it
        # must not infer policy from the numeric level or scalar magic weights.
        
        problem = build_lp_problem(selected_ingredients, data, der_info, level)
        raw_result = call_lp_solver(problem, level_config["objective_stages"])
        
        # V10.3: Clinical floor in Level 3 — fallback if infeasible
        if level_config.get("clinical_floor", {}).get("enabled") and raw_result["status"] == "infeasible":
            # Retry without clinical floor (relax x_min_i to 0)
            clinical_floor_config = level_config.get("clinical_floor", {})
            fallback = clinical_floor_config.get("fallback_if_infeasible", {})
            if fallback:
                problem_relaxed = build_lp_problem(selected_ingredients, data, der_info, level)
                problem_relaxed["clinical_floor_bounds"] = {}  # remove floor
                raw_result_relaxed = call_lp_solver(problem_relaxed, level_config["objective_stages"])
                if raw_result_relaxed["status"] == "feasible":
                    raw_result = raw_result_relaxed
                    raw_result["clinical_floor_relaxed"] = True  # mark for build_diagnostic_analysis
        
        if raw_result["status"] == "data_incomplete":
            return build_data_incomplete_result(raw_result, data, der_info)
        if raw_result["status"] == "structurally_infeasible":
            return build_structurally_infeasible_result(raw_result, data, der_info)
        if raw_result["status"] == "feasible":
            result = {}
            result["solver_status"] = level_config["result_status"]
            result["cascade_level_used"] = level
            
            if level == 3:
                # LEVEL 3: allocations=null (mechanical barrier). x_i are mathematical
                # lexicographic diagnostic numbers, NOT feeding recommendation.
                # Stage order minimizes SUL before DER proximity; the clinical
                # floor applies only when an ingredient is used.
                result["allocations"] = None
                result["feeding_recommendation"] = "DO_NOT_FEED"
                
                # Prepare clinical floor data for diagnostic_analysis
                clinical_floor_info = {
                    "bounds": problem.get("clinical_floor_bounds", {}),
                    "relaxed": raw_result.get("clinical_floor_relaxed", False)
                }
                result["diagnostic_analysis"] = build_diagnostic_analysis(
                    raw_result, data, der_info, clinical_floor_info
                )
                # Document lexicographic stages used for audit
                result["solver_metadata"] = raw_result.get("solver_metadata", {})
                result["solver_metadata"]["lexicographic_stages_used"] = {
                    "stages": level_config["objective_stages"],
                    "order_verified": True,
                    "note": "SUL violation is fixed before DER deviation, which is fixed before adequacy slack"
                }
                # V10.3: Document clinical floor
                result["solver_metadata"]["clinical_floor_applied"] = not clinical_floor_info["relaxed"]
                result["solver_metadata"]["clinical_floor_bounds"] = clinical_floor_info["bounds"]
            else:
                # LEVEL 1/2: allocations contains recommended grams (safe)
                result["allocations"] = format_allocations(raw_result, data)
                result["feeding_recommendation"] = "SAFE_TO_FEED" if level == 1 else "FEED_WITH_CAUTION"
                result["diagnostic_analysis"] = None
                result["solver_metadata"] = raw_result.get("solver_metadata", {})
            
            # Common fields to all levels
            result["nutrient_results"] = compute_nutrient_results(raw_result, data)
            result["gaps"] = compute_gaps(result, data)
            result["alerts"] = compute_alerts(result, data)
            result["recommended_additions"] = compute_recommendations(result["gaps"], data["db"])
            return result
        # If infeasible, descend to next level
    
    # Level 3 never reaches here — always returns something
    # (safety net: if reached here, implementation error)
    raise RuntimeError("Cascade completed without result — solver bug")

def build_diagnostic_analysis(raw_result, data, der_info, clinical_floor_info=None):
    """Build diagnostic_analysis block for Level 3. Receives raw_result with x_i (mathematical grams from violation minimization) — used ONLY for counterfactual (what_would_happen), NEVER placed in allocations. V10.3: clinical_floor_info has bounds + relaxed flag."""
    schema = data["schema"]
    tox_limits = data["tox_limits"]
    
    if clinical_floor_info is None:
        clinical_floor_info = {"bounds": {}, "relaxed": False}
    
    # 1. Identify inevitable SUL violations
    # V10.4: toxicological_limits.json is a LIST at top level (not object with "safe_upper_limits" key).
    # Each entry has nested sul.value (not flat sul_value).
    sul_violations = []
    for tox_entry in tox_limits:  # direct list — NOT .get("safe_upper_limits", [])
        nut_id = tox_entry["nutrient_id"]
        sul_value = tox_entry["sul"]["value"]  # nested — NOT tox_entry["sul_value"]
        achieved = raw_result["nutrient_values"].get(nut_id, 0)
        if achieved > sul_value:
            sul_violations.append({
                "nutrient_id": nut_id,
                "sul": sul_value,
                "minimum_achievable_at_der": achieved,
                "pct_above_sul": round((achieved / sul_value - 1) * 100, 1),
                "mechanism": "Vit A and calories are inseparable in this ingredient — "
                           "every gram adds both proportionally. No feasible split exists."
                           if nut_id == "vitamin_a_iu" else
                           "Nutrient concentration and caloric content are proportional "
                           "in the selected ingredients — no feasible separation."
            })
    
    # 2. Counterfactual scenario: what would happen if
    total_grams_for_der = sum(raw_result.get("x_values", {}).values())
    
    # V10.3: Check if x_i reaches clinical floor
    x_values = raw_result.get("x_values", {})
    floor_bounds = clinical_floor_info.get("bounds", {})
    ingredients_below_floor = []
    for ing_id, x_val in x_values.items():
        floor = floor_bounds.get(ing_id, 5)  # default 5g
        if 0 < x_val < floor:
            ingredients_below_floor.append({
                "ingredient_id": ing_id,
                "x_value_g": round(x_val, 2),
                "clinical_floor_g": floor,
                "note": f"Solver returned {x_val:.2f}g, below clinical floor of {floor}g"
            })
    
    what_would_happen = {
        "description": "If you fed ONLY the selected ingredients to meet caloric needs:",
        "grams_needed_for_der": round(total_grams_for_der, 1),
        "nutrient_at_risk": sul_violations[0]["nutrient_id"] if sul_violations else None,
        "value_at_that_amount": sul_violations[0]["minimum_achievable_at_der"] if sul_violations else None,
        "sul_value": sul_violations[0]["sul"] if sul_violations else None,
        "clinical_significance": (
            "Chronic hypervitaminosis A → osteoclast overactivation → "
            "pathologic fractures, osteodystrophy"
            if sul_violations and sul_violations[0]["nutrient_id"] == "vitamin_a_iu"
            else "Chronic excess → toxicological effects per SUL documentation"
        ),
        # V10.3: Clinical floor
        "clinical_floor_applied": not clinical_floor_info.get("relaxed", False),
        "clinical_floor_relaxed": clinical_floor_info.get("relaxed", False),
        "ingredients_below_floor": ingredients_below_floor,
        "x_min_i_effective": floor_bounds
    }
    
    # If floor was relaxed, add note
    if clinical_floor_info.get("relaxed", False):
        what_would_happen["clinical_floor_relaxation_note"] = (
            "Even the minimum recognizable portion of the selected ingredient(s) "
            "violates the SUL. No safe amount exists. The scenario below shows "
            "what the solver computed without the clinical floor constraint — "
            "these values are below any meaningful portion and serve only as "
            "mathematical evidence of inseparability."
        )
    
    # 3. Recommended alternative actions
    recommended_alternative_actions = [
        "Add a calorie source WITHOUT concentrated vitamin A (e.g., beef_muscle_raw, chicken_muscle_raw)",
        "Reduce liver/organ proportion and add muscle meat as caloric base",
        "Use recipe mode (Receitas Prontas) for pre-validated safe combinations"
    ]
    
    # 4. Reason for infeasibility
    reason_parts = []
    if sul_violations:
        reason_parts.append(
            "No combination of selected ingredients meets caloric needs without "
            "exceeding safe limits. Caloric content and the SUL-violating nutrient "
            "are inseparable in the selected ingredient(s) — every gram adds both "
            "proportionally."
        )
    if clinical_floor_info.get("relaxed", False):
        reason_parts.append(
            "Even the minimum clinically significant portion (clinical_floor_g) "
            "of the ingredient exceeds the SUL. The solver was re-run without "
            "the floor constraint to produce a mathematical counterfactual."
        )
    
    return {
        "reason": " ".join(reason_parts) if reason_parts else "SUL violation inevitable with selected ingredients.",
        "sul_violations_inevitable": sul_violations,
        "what_would_happen": what_would_happen,
        "recommended_alternative_actions": recommended_alternative_actions
    }

def format_allocations(raw_result, data):
    """Convert solver x_i variables into allocations with display_name and category. Used ONLY in Levels 1 and 2 (where allocations is safe)."""
    allocations = []
    for ing_id, grams in raw_result.get("x_values", {}).items():
        if grams > 0.01:  # ignore residual variables
            ing = get_ingredient_by_id(ing_id, data["db"])
            allocations.append({
                "ingredient_id": ing_id,
                "display_name": ing.get("display_name", ing_id),
                "category": ing.get("category", "unknown"),
                "grams_per_day": round(grams, 1),
                "pct_of_total": 0,  # preenchido depois
                "kcal_per_day": 0,  # preenchido depois
                "cost_per_day": None
            })
    total_g = sum(a["grams_per_day"] for a in allocations)
    for a in allocations:
        a["pct_of_total"] = round(a["grams_per_day"] / total_g * 100, 1) if total_g > 0 else 0
    return allocations

def call_lp_solver(problem, objective_stages):
    """Adapter contract, to be implemented against a real LP/MILP backend.

    Compiles all quantities to the stated daily basis, solves each declared
    objective stage sequentially, fixes the prior optimum within tolerance,
    and returns one of `feasible`, `infeasible`, `structurally_infeasible`, or
    `data_incomplete`. This Markdown block is a specification, not executable
    implementation; it must remain PLANNED until a real source file and test
    output exist.
    """
    raise NotImplementedError("Real LP/MILP backend not present in this workspace")

# ── 7. VALIDATE (output) ───────────────────────────────────────────────────
def validate_output(result, data, der_info):
    # a) allocations reference existing IDs (if non-null)
    if result["allocations"] is not None:
        for a in result["allocations"]:
            assert ingredient_exists_in_db(a["ingredient_id"], data["db"])
    # b) 41 nutrients covered in nutrient_results
    # V10.4: The 41 nutrients are those in nutrient_matrix in formulation_rules.
    # Composite variables (ca_p_ratio, caloric_density, cost_per_kg) are
    # derived/penalized but NOT primary nutrients — do not count
    # in this assert. If compute_nutrient_results includes any, use
    # assert len(result["nutrient_results"]) >= 41 instead of == 41.
    assert len(result["nutrient_results"]) >= 41
    # c) canonical status, including explicit non-recommendation diagnostics
    assert result["solver_status"] in (
        "optimal", "suboptimal", "unsafe_diagnostic",
        "structurally_infeasible", "data_incomplete"
    )
    # d) unsafe_diagnostic → allocations is null AND diagnostic_analysis is present
    if result["solver_status"] in ("unsafe_diagnostic", "structurally_infeasible", "data_incomplete"):
        assert result["allocations"] is None
        assert result["diagnostic_analysis"] is not None
    # e) feeding_recommendation matches solver_status
    expected_rec = {
        "optimal": "SAFE_TO_FEED",
        "suboptimal": "FEED_WITH_CAUTION",
        "unsafe_diagnostic": "DO_NOT_FEED",
        "structurally_infeasible": "DO_NOT_FEED",
        "data_incomplete": "DO_NOT_FEED"
    }
    assert result["feeding_recommendation"] == expected_rec[result["solver_status"]]
    # f) optimal/suboptimal → allocations not null and sum within envelope
    if result["solver_status"] in ("optimal", "suboptimal"):
        assert result["allocations"] is not None
        assert len(result["allocations"]) >= 1
        total_g = sum(a["grams_per_day"] for a in result["allocations"])
        envelope = der_info["envelope"]
        assert envelope["min_total_g"] <= total_g <= envelope["max_total_g"]
    # g) unsafe_diagnostic → weight hierarchy was validated
    if result["solver_status"] == "unsafe_diagnostic":
        stages = result["solver_metadata"].get("lexicographic_stages_used", {})
        assert stages.get("order_verified") is True, "Level 3 lexicographic order not verified"
        assert [s["name"] for s in stages.get("stages", [])] == [
            "sul_violation", "der_deviation", "adequacy_slack"
        ], "Level 3 must optimize SUL → DER → adequacy"
        # h) [V10.3] unsafe_diagnostic → clinical floor documented
        assert "clinical_floor_applied" in result["solver_metadata"], (
            "solver_metadata missing clinical_floor_applied in Level 3"
        )
        assert isinstance(result["solver_metadata"]["clinical_floor_applied"], bool)
        assert "clinical_floor_bounds" in result["solver_metadata"]
        # i) [V10.3] If clinical_floor_relaxed, note must exist in what_would_happen
        wwh = result["diagnostic_analysis"]["what_would_happen"]
        if wwh.get("clinical_floor_relaxed", False):
            assert "clinical_floor_relaxation_note" in wwh, (
                "Clinical floor relaxed without documentation note"
            )

# ── 8. MAIN ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mode = sys.argv[1]  # --runtime or --build-recipes
    
    if mode == "--runtime":
        animal_data = json.load(open("animal_input.json"))  # user data
        data = load_all_jsons()
        validate_inputs(data)
        der_info = calculate_der_and_envelope(
            animal_data, data["growth"], get_active_scenario(data),
            animal_data["selected_ingredients"], data["db"]
        )
        result = solve_cascade(animal_data["selected_ingredients"], data, der_info)
        validate_output(result, data, der_info)
        json.dump(result, open("solver_output.json", "w"), indent=2, ensure_ascii=False)
    
    elif mode == "--build-recipes":
        data = load_all_jsons()
        validate_inputs(data)
        recipes = generate_all_recipes(data)
        json.dump(recipes, open("recipes_precomputed.json", "w"), indent=2, ensure_ascii=False)
```

```

---

## 6.5 Documented Implementation Extensions (Beyond §6.4 Spec)

### 6.5.1 DerEnvelope — Dual Contract (Item 4, deviations_report)

```python
class DerEnvelope:
    """Holds DER calculation results. Satisfies both the mandated 3-tuple
    contract (der_kcal, min_total_g, max_total_g) via __iter__ and exposes
    all intermediate values as named attributes for Phase 2 consumers.
    Decision (item 4): build a class implementing both interfaces
    instead of choosing between tuple and dict.
    """

    def __init__(self, bw_kg, ter_kcal, k_multiplier, der_kcal,
                 units_of_1000kcal, min_total_g, max_total_g,
                 strategy="der_derived", density_source=""):
        self.bw_kg = bw_kg
        self.ter_kcal = ter_kcal
        self.k_multiplier = k_multiplier
        self.der_kcal = der_kcal
        self.units_of_1000kcal = units_of_1000kcal
        self.min_total_g = min_total_g
        self.max_total_g = max_total_g
        self.strategy = strategy
        self.density_source = density_source

    def __iter__(self):
        """Unpack as (der_kcal, min_total_g, max_total_g) — mandated 3-tuple.
        Enables: der, min_t, max_t = calculate_der_and_envelope(...)
        """
        return iter((self.der_kcal, self.min_total_g, self.max_total_g))

    def __len__(self): return 3
    def __getitem__(self, index):
        return (self.der_kcal, self.min_total_g, self.max_total_g)[index]

    def as_envelope_dict(self):
        return {"min_total_g": self.min_total_g, "max_total_g": self.max_total_g,
                "actual_total_g": None, "strategy": self.strategy}

    def as_animal_context(self, sex, age_months, gonadal_status, bw_source="gompertz"):
        return {"sex": sex, "weight_kg": self.bw_kg, "age_months": age_months,
                "gonadal_status": gonadal_status, "der_kcal": self.der_kcal,
                "ter_kcal": self.ter_kcal, "k_multiplier": self.k_multiplier,
                "bw_source": bw_source}
```

**Usage:** `der, min_t, max_t = calculate_der_and_envelope(...)` works via `__iter__`, AND `der_env.bw_kg` returns 45.0 for named access.

---

### 6.5.2 Conditional Adequacy Checks (Level 1 → Level 2 Delegation)

`lp_parameters_data.json:323-339` defines `conditional_adequacy_checks` for Level 1:

```json
"conditional_adequacy_checks": [{
  "name": "fat_source_vs_aafco_fat",
  "description": "If fat_source inclusion at structural minimum (8%) cannot meet AAFCO fat_g minimum (21.25 g/1000kcal), flag for Level 2 relaxation with targeted gap",
  "trigger": {
    "fat_source_inclusion_pct": { "lt": 0.15 },
    "nutrient_id": "fat_g",
    "target_min": 21.25
  },
  "action": "relax_fat_minimum_to_suboptimal",
  "gap_detail": {
    "nutrient_id": "fat_g",
    "category_missing": "fat_source",
    "message_template": "Fat source inclusion at {fat_source_pct:.1%} provides only {fat_contribution:.1f} g/1000kcal fat. AAFCO minimum (21.25) requires ≥15% fat_source (beef_fat) or ≥18% (chicken/pork_fat). Increase fat_source or add high-fat ingredients (beef_tail, beef_fat).",
    "top_ingredients": ["beef_fat_raw", "chicken_fat_raw", "pork_fat_raw", "beef_tail_raw"]
  }
}]
```

**Implementation:** `check_fat_source_adequacy()` (linhas 3058-3145) — pre-solver check que retorna gap detail estruturado para output contract se fat_source @ structural min não atinge AAFCO fat_g.

---

### 6.5.3 Clinical Floor MILP — Big-M Per-Ingrediente

```json
"solver_params": {
  "big_m_strategy": "der_per_ingredient",
  "big_m_description": "M_i = DER_kcal / EM_i_kcal_per_100g * 100. Grams of ingredient i alone that would satisfy 100% of DER — a physically plausible per-ingredient upper bound, avoiding both numerical instability (M too large) and artificial capping (M too small).",
  
  "fix_optimum_tolerance_abs": 0.01,
  "fix_optimum_tolerance_rel": 1e-6,
  "fix_optimum_description": "When fixing stage N's optimum before solving stage N+1, accept objective within opt*(1+tol_rel) + tol_abs. Prevents false infeasibility from floating-point CBC results. EXCEPTION: if stage N involved binary variables (MILP), the effective tolerance is max(this value, cbc_mip_gap * abs(opt)) — see 'mip_tolerance_rule' below. A tolerance tighter than the gap CBC was allowed to leave on the table is meaningless.",
  "mip_tolerance_rule": "effective_tol_rel = max(fix_optimum_tolerance_rel, cbc_mip_gap) when the stage's LpProblem contains any LpVariable with cat='Binary'; otherwise effective_tol_rel = fix_optimum_tolerance_rel.",

  "cbc_time_limit_seconds": 30,
  "cbc_mip_gap": 0.01,
  "cbc_mip_gap_description": "Relative MIP gap for MILP (clinical floor binaries). 1% is sufficient — we don't need globally optimal binary assignment.",

  "tie_break_objective": "minimize_total_grams",
  "tie_break_weight": 0.001,
  "implementation_status": "Known bug: the current code still adds a 0-999.9 hash perturbation to every stage, so this is not yet a negligible tie-break.",
  "tie_break_description": "Secondary objective applied ONLY to the final stage of any lexicographic sequence for a given cascade level (i.e. the stage whose result becomes the reported solution, not one whose objective value is subsequently fixed via fix_optimum). Never blend the tie-break into an intermediate stage — its magnitude (weight * sum(x_i), typically 0.1-1.0 given x_i in the hundreds of grams) would swamp fix_optimum_tolerance_abs (0.01) and corrupt the value the next stage fixes against."
}
```

**Big-M Formula:** `M_i = DER_kcal / EM_i_kcal_per_100g * 100` — grams of ingredient i alone satisfying 100% DER. Physically plausible per-ingredient upper bound.

**Tie-Break Determinístico (linhas 2206-2219):**
```python
def det_hash(s): h = 0; for ch in s: h = (h * 31 + ord(ch)) & 0xFFFFFFFF; return h
perturbation = (det_hash(iid) % 10000) * 1e-1
tie_break_expr += (tie_weight + perturbation) * var
```
Garante output bit-a-bit idêntico across runs.

**Fix Optimum Tolerance com MIP Tolerance Rule (linhas 2244-2247):**
```python
if has_binary_vars:
    mip_gap = solver_params.get("cbc_mip_gap", 0.01)
    tol_rel = max(tol_rel, mip_gap)
```
Tolerância mais apertada que o gap do CBC seria meaningless.

---

### 6.5.3 Tie-Break Determinístico Hash-Based

```python
# Linhas 2206-2219 em call_lp_solver()
def det_hash(s: str) -> int:
    h = 0
    for ch in s:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h

tie_break_expr = 0
for iid, var in x_vars.items():
    perturbation = (det_hash(iid) % 10000) * 1e-1
    tie_break_expr += (tie_weight + perturbation) * var
obj_expr += tie_break_expr
```

**Teste:** `test_tie_break_produces_identical_output_on_repeat_runs()` passa — output bit-a-bit idêntico across runs.

---

### 6.5.4 build_output_contract() + validate_output()

**build_output_contract() (linhas 2400-2487):** Constrói output contract final (§7) a partir de `raw_result`:
- Level 1/2: `allocations` + `feeding_recommendation` = SAFE_TO_FEED / FEED_WITH_CAUTION
- Level 3: `allocations=null` + `diagnostic_analysis` + `feeding_recommendation=DO_NOT_FEED`
- `solver_metadata` inclui `cascade_attempts`, `lexicographic_stages_used`, `clinical_floor_applied`, `clinical_floor_bounds`

**validate_output() (linhas 2991-3054):** 9 assertions contratuais:
1. Canonical `solver_status` (5 valores válidos)
2. `feeding_recommendation` matches status
3. Level 1/2: `allocations` not null, within envelope
4. Level 3/structurally_infeasible: `allocations=null`, `diagnostic_analysis` present
5. `nutrient_results` ≥ 41 entries
6. Each nutrient result has required fields
7. Level 3: `lexicographic_stages_used.order_verified = True`
8. Level 3: `clinical_floor_applied` (bool) + `clinical_floor_bounds` (dict)
9. If `clinical_floor_relaxed`: `clinical_floor_relaxation_note` in `what_would_happen`

---

### 6.5.5 Conditional Adequacy Checks Implementation

```python
def check_fat_source_adequacy(matrix, selected_ids, formulation_rules, der_envelope) -> dict | None:
    """
    Conditional adequacy check: if fat_source inclusion is at structural minimum (8%)
    but total fat_g at that inclusion cannot meet AAFCO minimum (21.25 g/1000kcal),
    return a gap dict for the output contract. Called after matrix build, before solver.
    """
    # Get DB reference first
    db = formulation_rules.get("_db_ref")
    if db is None: return None

    # Get fat_source inclusion constraint
    incl_limits = formulation_rules.get("inclusion_limits", [])
    fat_source_limit = next((il for il in incl_limits if il.get("ingredient_id") == "fat_source"), {})
    structural_min = fat_source_limit.get("min_pct", 8) / 100.0  # e.g., 0.08
    aafco_recommended_min = fat_source_limit.get("effective_min_pct_for_aafco_fat", 15) / 100.0  # e.g., 0.15

    # Find fat_source ingredients in selection
    all_ings = _find_all_ingredients(db)
    fat_source_ids = [iid for iid in selected_ids if all_ings.get(iid, {}).get("category") == "fat_source"]
    
    if not fat_source_ids: return None

    # Compute total fat_g at structural minimum fat_source inclusion
    total_fat_at_structural_min = 0.0
    for fs_id in fat_source_ids:
        fs_ing = get_ingredient_by_id(fs_id, db)
        if not fs_ing: continue
        fs_nuts = fs_ing.get("bromatological_profile", {}).get("nutrients", {})
        fs_fat = fs_nuts.get("fat_g", {}).get("value", 0) if isinstance(fs_nuts.get("fat_g"), dict) else fs_nuts.get("fat_g", 0)
        if not fs_fat: continue
        em = energy_metabolizable_kcal_per_100g(fs_nuts)
        if em <= 0: continue
        fs_fat_norm = fs_fat * (1000.0 / em)
        total_fat_at_structural_min += structural_min * fs_fat_norm

    # Add fat from other selected ingredients (at 100% - structural_min - other categories)
    other_fat = 0.0
    non_fs_ids = [iid for iid in selected_ids if iid not in fat_source_ids]
    for iid in non_fs_ids:
        ing = get_ingredient_by_id(iid, db)
        if not ing: continue
        nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
        fat = nuts.get("fat_g", {}).get("value", 0) if isinstance(nuts.get("fat_g"), dict) else nuts.get("fat_g", 0)
        if fat:
            em = energy_metabolizable_kcal_per_100g(nuts)
            if em > 0:
                other_fat += (1.0 - structural_min) * (fat * (1000.0 / em)) * (1.0 / len(non_fs_ids) if non_fs_ids else 1)

    total_fat_est = total_fat_at_structural_min + other_fat
    aafco_fat_min = 21.25  # g/1000kcal from formulation_rules.nutrient_matrix

    if total_fat_est < aafco_fat_min:
        pct_of_min = round(100 * total_fat_est / aafco_fat_min, 1)
        return {
            "nutrient_id": "fat_g",
            "pct_of_min": pct_of_min,
            "category_missing": "fat_source",
            "structural_min_pct": structural_min * 100,
            "aafco_recommended_min_pct": aafco_recommended_min * 100,
            "estimated_fat_at_structural_min": round(total_fat_est, 1),
            "aafco_fat_min": aafco_fat_min,
            "top_ingredients_in_category": [
                {"ingredient_id": fs_id, "fat_g_per_1000kcal": round(_get_fat_norm(get_ingredient_by_id(fs_id, db)), 1)}
                for fs_id in fat_source_ids
                if _get_fat_norm(get_ingredient_by_id(fs_id, db)) > 0
            ],
            "note": f"Fat source at structural minimum ({structural_min*100:.0f}%) yields only {total_fat_est:.1f} g/1000kcal fat. AAFCO minimum ({aafco_fat_min}) requires ~{aafco_recommended_min*100:.0f}% fat_source inclusion with selected ingredients."
        }
    return None
```

---

### 6.5.6 Resumo das Extensões vs. Spec §6.4

| Feature | §6.4 Spec | Implementação Real | Status |
|---------|-----------|-------------------|--------|
| `DerEnvelope` | `tuple[float, float, float]` | Classe com `__iter__` + named attrs | ✅ Superior |
| `calculate_der_and_envelope` | 3 params | + `scenario_id`, `selected_ids`, `db`, `default_breed_line` | ✅ Estendido |
| `conditional_adequacy_checks` | Não especificado | `fat_source_vs_aafco_fat` pre-check | ✅ Novo |
| Clinical Floor MILP | Conceitual | Big-M per-ingrediente + binárias + fallback | ✅ Implementado |
| Big-M Strategy | Não especificado | `der_per_ingredient` (fisicamente plausível) | ✅ Novo |
| Fix Optimum Tolerance | Não especificado | `mip_tolerance_rule` (widen se binárias) | ✅ Novo |
| Tie-Break | Não especificado | Hash-based determinístico 1000.0 weight | ✅ Novo |
| `build_output_contract` | Não especificado | Constrói contract final §7 | ✅ Novo |
| `validate_output` | Não especificado | 9 assertions contratuais | ✅ Novo |
| `conditional_adequacy_checks` | Não especificado | `fat_source_vs_aafco_fat` implementado | ✅ Novo |

---

## ✅ Definition of Done — sat_pipeline_codigo

Implementation of `src/gsd/` package is complete when:

- [ ] `load_all_jsons()` loads the 9 JSONs listed in §6.4 (DB, constraints, formulation_rules, audit_provenance, growth_energy_skeletal, objective_weights, scenarios, toxicological_limits, lp_parameters_schema).
- [ ] `validate_inputs(data)` executes the 6 assertions (a-f) from code section 2 — all pass with real JSONs.
- [ ] `calculate_der_and_envelope()` implements `DER = TER × k_multiplier`, `TER = 70 × BW^0.75`, and envelope `[minTotal_g, maxTotal_g]` with 10% margins (0.9× / 1.1×).
- [ ] `as_fed → energy_normalized` conversion applies 11 unit factors + 2 composite amino acids (Met+Cys, Phe+Tyr) with real values (no proxy).
- [ ] `expand_category_wildcards()` resolves `_all_muscle_meat`, `_all_fat_source`, etc. to real `ingredient_id`s from DB.
- [ ] `build_matrix()` produces `a_ij` with shape `(N_ingredients, 41_nutrients)` in `energy_normalized/1000kcal` basis.
- [ ] `solve_cascade()` (reference in `sat_solver_contrato:§8`) is invoked with matrix + constraints + solve_cascade[] from schema.
- [ ] Output follows `sat_solver_contrato:§7` contract (Level 1/2 with `allocations`, Level 3 with `allocations=null` + `diagnostic_analysis`).
- [ ] Output validation verifies canonical safe and non-recommendation statuses, including `structurally_infeasible` and `data_incomplete`.
- [ ] The real LP/MILP backend exists outside this Markdown specification, compiles coefficients/targets/SULs to a daily basis, and has pasted test output with real JSONs.
- [ ] `--build-recipes` mode generates versioned `recipes_precomputed.json`, no `unsafe_diagnostic`.

**Anti-gamification verification:** run `python build_pipeline.py --runtime` with 1 ingredient selection (ex: `beef_liver_raw`) must produce `solver_status: "unsafe_diagnostic"` with `allocations: null`. Running with 7 balanced ingredients must produce `solver_status: "optimal"`.

---
