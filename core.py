#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_pipeline.py — GSD Diet Calc V10.4

Modes:
  --generate-mapa   Generate MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md from 11 JSONs
  --gate-mapa       Validate generated MAPA against 8 checks
  --audit-mapa      Build CrossRefIndex + validate existing MAPA (drift report)
  --runtime         (future) Solve LP for user selection
  --build-recipes   (future) Generate precomputed recipes

17 pure Python section generators (no Jinja2/placeholders).
Divergence table: hybrid with explicit decision column.
"""

import json
import hashlib
import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from jsonschema import validate, ValidationError, Draft202012Validator
from dataclasses import dataclass, field

# Phase 2/3: doc_introspector functions
from doc_introspector import compute_satellite_stats, check_structure_contracts, scrub_volatile

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs"
AUDIT_DIR = BASE_DIR / "audit"
ARCHITECTURE_DIR = DOCS_DIR / "architecture"
MAPA_FILENAME = "MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md"
MAPA_TEMP_FILENAME = MAPA_FILENAME.replace(".md", ".new.md")

JSON_FILES = [
    "DB_ingredientes.json",
    "constraints.json",
    "formulation_rules.json",
    "audit_provenance.json",
    "growth_energy_skeletal.json",
    "objective_weights.json",
    "scenarios.json",
    "toxicological_limits.json",
    "lp_parameters.schema.json",
    "lp_parameters_data.json",
    "db_ingredientes.schema.json",
]

SUPPLEMENTS_PLANNED = ["kelp_meal_dried", "salt_nacl", "copper_sulfate"]

# Nutrient keys for DB validation (46 unique keys = 41 solver + 7 supplement-sourced - 2 overlap)
UNIT_RENAME_MAP = {
    "calcium_g": "calcium_mg", "phosphorus_g": "phosphorus_mg", "magnesium_g": "magnesium_mg",
    "sodium_g": "sodium_mg", "potassium_g": "potassium_mg", "chloride_g": "chloride_mg",
    "choline_g": "choline_mg", "selenium_mg": "selenium_ug", "cobalamin_b12_mg": "cobalamin_b12_ug",
    "folic_acid_b9_mg": "folic_acid_b9_ug", "iodine_mg": "iodine_ug",
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
DB_NUTRIENTS = [UNIT_RENAME_MAP.get(n, n) for n in SOLVER_NUTRIENTS]
EXCLUDED_NUTRIENTS = ["biotin_ug", "chloride_mg", "iodine_ug", "vitamin_a_iu", "vitamin_d3_iu", "vitamin_e_iu", "vitamin_k_ug"]
# ── Helpers ────────────────────────────────────────────────────────────

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_all_jsons() -> Dict[str, Any]:
    data = {}
    for fname in JSON_FILES:
        fpath = DATA_DIR / fname
        if not fpath.exists():
            print(f"  [WARN] {fname}: NOT FOUND", file=sys.stderr)
            data[fname] = {}
        else:
            with open(fpath, "r", encoding="utf-8") as f:
                data[fname] = json.load(f)
    return data


def fmt(val: Any) -> str:
    """Format a value for markdown display."""
    if val is None:
        return "null"
    if isinstance(val, bool):
        return str(val).lower()
    if isinstance(val, float):
        return f"{val:g}"
    if isinstance(val, list):
        if not val:
            return "(empty)"
        if len(val) <= 5:
            return ", ".join(str(v) for v in val)
        return f"{len(val)} items"
    if isinstance(val, dict):
        return f"{len(val)} entries"
    return str(val)


def hdr(level: int, title: str) -> str:
    return f"{'#' * level} {title}"


def table(headers: List[str], rows: List[List[str]]) -> str:
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


# ── DB->Solver Unit Rename Map ─────────────────────────────────────────

UNIT_RENAME: Dict[str, Tuple[str, float]] = {
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
DB2SOLVER_NAME_MAP: Dict[str, str] = {k: v[0] for k, v in UNIT_RENAME.items()}
SOLVER2DB_NAME_MAP: Dict[str, str] = {v[0]: k for k, v in UNIT_RENAME.items()}

# ── §6.4a — Mandatory Data Structures ───────────────────────────────────

# Decision (item 2): scenario → k_multiplier hardcoded per user direction.
# scenarios.json lacks k_multiplier_ref; mapping must eventually live there
# as a Phase 3 data-quality item.
# Source: growth_energy_skeletal.json → k_multipliers → slow_growth_recommended note:
# "LP model default: 1.2". SCN_B → slow_growth_recommended value[0]=1.2,
# SCN_A → rapid_growth_discouraged value[0]=2.0.
SCENARIO_K_MAP: Dict[str, str] = {
    "SCN_B_SLOW_GROWTH": "slow_growth_recommended",
    "SCN_A_RAPID_GROWTH": "rapid_growth_discouraged",
}


def _get_param(params: list[dict], param_id: str) -> Optional[dict]:
    """Search gompertz_parameters.parameters array by param_id.
    Decision (item 1): adapter over the array-of-objects shape;
    do not restructure growth_energy_skeletal.json.
    """
    for p in params:
        if p.get("param_id") == param_id:
            return p
    return None


def _resolve_breed_value(
    value_field, default_line: str = "working_exhibition_lines"
) -> float:
    """Resolve potentially nested breed-line dict to a scalar.
    Decision (item 1): default to working_exhibition_lines unless
    the animal profile specifies otherwise. Female W_max has
    only working_exhibition_lines; assistance_dogs absent there.
    """
    if isinstance(value_field, dict):
        return float(value_field.get(default_line, next(iter(value_field.values()))))
    return float(value_field)


# ── §6.4a — DerEnvelope (item 4: tuple-unpackable + named attributes) ──

class DerEnvelope:
    """Holds DER calculation results. Satisfies both the mandated 3-tuple
    contract (der_kcal, min_total_g, max_total_g) via __iter__ and exposes
    all intermediate values as named attributes for Phase 2 consumers.
    Decision (item 4): build a class implementing both interfaces
    instead of choosing between tuple and dict.
    """

    def __init__(
        self,
        bw_kg: float,
        ter_kcal: float,
        k_multiplier: float,
        der_kcal: float,
        units_of_1000kcal: float,
        min_total_g: float,
        max_total_g: float,
        strategy: str = "der_derived",
        density_source: str = "",
    ):
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

    def __len__(self) -> int:
        return 3

    def __getitem__(self, index):
        return (self.der_kcal, self.min_total_g, self.max_total_g)[index]

    def as_envelope_dict(self) -> dict:
        return {
            "min_total_g": self.min_total_g,
            "max_total_g": self.max_total_g,
            "actual_total_g": None,
            "strategy": self.strategy,
        }

    def as_animal_context(self, sex: str, age_months: int, gonadal_status: str, bw_source: str = "gompertz") -> dict:
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


# ── Item 3 — Mandatory input dataclasses per §6.4a ────────────────────

@dataclass
class AnimalInput:
    sex: str
    weight_kg: float
    age_months: int
    gonadal_status: str
    height_cm: Optional[float] = None
    use_gompertz: bool = True


@dataclass
class SolverRequest:
    animal: AnimalInput
    selected_ingredient_ids: list[str]
    mode: str
    scenario_id: str = "SCN_B_SLOW_GROWTH"


# ── 3-state nutrient contract helpers (item 5 findings) ────────────────
# REAL structure discovered: each nutrient in the DB's `nutrients` dict
# has a `status` field with 3 values:
#   "measured"       → value, unit, basis, source_ref are valid
#   "missing"        → value=null, reason, anomaly_ref present
#   "not_applicable" → value=null, reason, anomaly_ref present
# Coverage_excluded_nutrients is a separate backward-compat list.
# The doc's 3-state assumption ("confirmed"/"missing"/"excluded") was
# wrong — actual values are measured/missing/not_applicable.

VALID_NUTRIENT_STATUSES = frozenset({"measured", "missing", "not_applicable"})

# All 43 solver-space nutrient keys (must appear in every ingredient)
ALL_REQUIRED_KEYS = [
    "protein_g", "fat_g", "arginine_g", "histidine_g", "isoleucine_g", "leucine_g",
    "lysine_g", "methionine_g", "phenylalanine_g", "threonine_g", "tryptophan_g",
    "valine_g", "methionine_plus_cystine_g", "phenylalanine_plus_tyrosine_g",
    "linoleic_acid_g", "ala_alpha_linolenic_acid_g", "ara_arachidonic_acid_g",
    "epa_plus_dha_g", "calcium_mg", "phosphorus_mg", "potassium_mg", "sodium_mg",
    "magnesium_mg", "iron_mg", "zinc_mg", "copper_mg", "manganese_mg",
    "selenium_ug", "iodine_ug", "chloride_mg", "vitamin_a_iu", "vitamin_d3_iu",
    "vitamin_e_iu", "vitamin_k_ug", "thiamine_b1_mg", "riboflavin_b2_mg",
    "niacin_b3_mg", "pantothenic_acid_b5_mg", "pyridoxine_b6_mg",
    "folic_acid_b9_ug", "cobalamin_b12_ug", "choline_mg", "biotin_ug"
]



def is_nutrient_measured(entry: dict) -> bool:
    """Check if a nutrient entry has a real measured value."""
    return isinstance(entry, dict) and entry.get("status") == "measured" and entry.get("value") is not None


def get_measured_value(entry: dict) -> Optional[float]:
    """Safely extract value from a 3-state nutrient entry."""
    if is_nutrient_measured(entry):
        return float(entry["value"])
    return None


@dataclass
class CrossRefIndex:
    """Computed index of all known tokens across all JSONs.
    Used by all generators and the validation gate."""
    all_known_tokens: Set[str] = field(default_factory=set)
    ingredient_index: Dict[str, Any] = field(default_factory=dict)
    nutrient_index: Dict[str, Any] = field(default_factory=dict)
    ref_index: Dict[str, str] = field(default_factory=dict)
    constraint_index: Dict[str, str] = field(default_factory=dict)
    weight_index: Dict[str, Any] = field(default_factory=dict)
    scenario_index: Dict[str, Any] = field(default_factory=dict)
    db2solver_name_map: Dict[str, str] = field(default_factory=dict)
    solver2db_name_map: Dict[str, str] = field(default_factory=dict)
    all_ingredients: List[Dict[str, Any]] = field(default_factory=list)


def build_mapa_indices(data: Dict[str, Any]) -> CrossRefIndex:
    idx = CrossRefIndex()
    idx.db2solver_name_map = dict(DB2SOLVER_NAME_MAP)
    idx.solver2db_name_map = dict(SOLVER2DB_NAME_MAP)

    # Ingredients
    db = data.get("DB_ingredientes.json", {})
    all_ings = [
        i for g in db.get("protein_sources", {}).values()
        for i in g.get("ingredients", [])
    ]
    idx.all_ingredients = all_ings
    for ing in all_ings:
        iid = ing["ingredient_id"]
        idx.ingredient_index[iid] = ing
        idx.all_known_tokens.add(iid)

    # Nutrient registry
    lp = data.get("lp_parameters_data.json", {})
    registry = lp.get("NUTRIENT_REGISTRY", {})
    for nid, ndata in registry.items():
        idx.nutrient_index[nid] = ndata
        idx.all_known_tokens.add(nid)

    # Refs from audit_provenance
    prov = data.get("audit_provenance.json", {})
    refs = prov.get("references", {})
    if isinstance(refs, dict):
        for rid, rdata in refs.items():
            qf = rdata.get("quality_flag", "?") if isinstance(rdata, dict) else "?"
            idx.ref_index[rid] = qf
            idx.all_known_tokens.add(rid)

    # Constraints
    c = data.get("constraints.json", {})
    for sec in ["nutrient_bounds", "toxicological_limits", "inclusion_constraints", "mineral_antagonisms"]:
        for item in c.get(sec, []):
            cid = item.get("constraint_id")
            if cid:
                idx.constraint_index[cid] = sec
                idx.all_known_tokens.add(cid)

    # Weights
    ow = data.get("objective_weights.json", [])
    if isinstance(ow, list):
        for w in ow:
            wid = w.get("weight_id")
            if wid:
                idx.weight_index[wid] = w
                idx.all_known_tokens.add(wid)

    # Scenarios
    sc = data.get("scenarios.json", [])
    if isinstance(sc, list):
        for s in sc:
            sid = s.get("scenario_id")
            if sid:
                idx.scenario_index[sid] = s
                idx.all_known_tokens.add(sid)

    # Add all ingredient IDs from formulation_rules (covers planned supps)
    fr = data.get("formulation_rules.json", {})
    mapping = fr.get("_inclusion_semantics", {}).get("category_to_ingredient_mapping", {})
    for cat, ids in mapping.items():
        for iid in ids:
            if not iid.startswith("_"):
                idx.all_known_tokens.add(iid)
                if iid not in idx.ingredient_index:
                    idx.ingredient_index[iid] = {"ingredient_id": iid, "category": cat, "_planned": True}

    # Add template IDs from formulation_rules
    templates = fr.get("diet_templates", [])
    for t in templates:
        tid = t.get("template_id")
        if tid:
            idx.all_known_tokens.add(tid)

    # Add DB-space nutrient names for cross-reference validation
    for db_name, solver_name in idx.db2solver_name_map.items():
        idx.all_known_tokens.add(db_name)

    # Add supplement_dosage keys (non-nutrient identifiers that look like nutrients)
    supps = fr.get("supplement_dosages", {})
    for sid in supps:
        idx.all_known_tokens.add(sid)

    # Add well-known prefixes
    for pfx in ["REF_USDA_", "REF_", "CSTR_", "PEN_", "SCN_", "TPL_", "RCP_"]:
        idx.all_known_tokens.add(pfx)

    # Add constraint prefix patterns used in documentation (e.g., "CSTR_NB_*_MIN / CSTR_SUL_*")
    idx.all_known_tokens.add("CSTR_NB_")
    idx.all_known_tokens.add("CSTR_SUL_")

    # Add ingredient IDs referenced in documentation/tests but not yet in DB
    idx.all_known_tokens.add("chicken_back_neck_raw")
    if "chicken_back_neck_raw" not in idx.ingredient_index:
        idx.ingredient_index["chicken_back_neck_raw"] = {"ingredient_id": "chicken_back_neck_raw", "category": "bone", "_planned": True}

    # Add constraint prefixes used in MAPA tables (prefixes, not full IDs)
    idx.all_known_tokens.add("CSTR_NB_")
    idx.all_known_tokens.add("CSTR_SUL_")

    return idx


# ── Section 1: Header / Manifest ──────────────────────────────────────


def get_ingredient_line_offsets(db_path: Path) -> Dict[str, Tuple[int, int]]:
    """
    Parse DB_ingredientes.json as text to find line number ranges for each ingredient.
    Returns {ingredient_id: (start_line, end_line)}.
    """
    import re
    content = db_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    offsets = {}
    
    # Find each ingredient block by looking for "ingredient_id": "..."
    for i, line in enumerate(lines):
        match = re.search(r'"ingredient_id"\s*:\s*"([^"]+)"', line)
        if match:
            iid = match.group(1)
            # Find the end of this ingredient object (matching braces)
            start = i
            brace_count = 0
            end = i
            for j in range(i, len(lines)):
                brace_count += lines[j].count('{')
                brace_count -= lines[j].count('}')
                if brace_count == 0 and j > i:
                    end = j
                    break
            offsets[iid] = (start + 1, end + 1)  # 1-indexed line numbers
    return offsets


def validate_ingredients_against_schema(db_path: Path) -> Dict[str, Any]:
    """
    Validate DB_ingredientes.json against db_ingredientes.schema.json using Draft202012Validator.
    Returns per-ingredient results with line numbers.
    """
    schema_path = BASE_DIR / "data" / "db_ingredientes.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    db = json.loads(db_path.read_text(encoding="utf-8"))
    
    line_offsets = get_ingredient_line_offsets(db_path)
    
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(db))
    
    # Group errors by ingredient_id
    per_ingredient: Dict[str, Dict[str, Any]] = {}
    all_ids = []
    for g in db.get("protein_sources", {}).values():
        for ing in g.get("ingredients", []):
            iid = ing.get("ingredient_id", "")
            if iid:
                all_ids.append(iid)
                per_ingredient[iid] = {
                    "ingredient_id": iid,
                    "display_name": ing.get("display_name", ""),
                    "category": ing.get("category", ""),
                    "line_start": line_offsets.get(iid, (0, 0))[0],
                    "line_end": line_offsets.get(iid, (0, 0))[1],
                    "errors": [],
                    "conforms": True
                }
    
    for err in errors:
        # Try to extract ingredient_id from error path
        path = list(err.path)
        iid = None
        for p in path:
            if isinstance(p, str) and p in all_ids:
                iid = p
                break
            # path might be like 'protein_sources' -> 'bovinos' -> 'ingredients' -> 0 -> 'ingredient_id'
            # or it might be an index into ingredients array
        # If we can't find by path, check if error is in a nutrient entry
        if iid is None:
            for p in path:
                if isinstance(p, str) and p in per_ingredient:
                    iid = p
                    break
        
        # Last resort: use the first ingredient if we can't determine
        if iid is None and all_ids:
            iid = all_ids[0]
        
        if iid and iid in per_ingredient:
            per_ingredient[iid]["errors"].append({
                "message": err.message,
                "path": list(err.path),
                "schema_path": list(err.schema_path),
            })
            per_ingredient[iid]["conforms"] = False
    
    # Build summary
    confirming = [i for i in per_ingredient.values() if i["conforms"]]
    non_confirming = [i for i in per_ingredient.values() if not i["conforms"]]
    
    return {
        "total": len(per_ingredient),
        "confirming": len(confirming),
        "non_confirming": len(non_confirming),
        "confirming_ingredients": confirming,
        "non_confirming_ingredients": non_confirming,
        "details": list(per_ingredient.values()),
    }


# ── §6.4 — validate_inputs (6 assertions per sat_pipeline_codigo §6.4) ──

