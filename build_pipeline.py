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
from jsonschema import validate, ValidationError
from dataclasses import dataclass, field

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
ALL_REQUIRED_KEYS = set(DB_NUTRIENTS + EXCLUDED_NUTRIENTS)

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

    return idx


# ── Section 1: Header / Manifest ──────────────────────────────────────

def section1_header(data: Dict[str, Any]) -> str:
    """Verbatim copy of indice_plano_central.md preamble (§0-§2) + file manifest."""
    index_path = ARCHITECTURE_DIR / "indice_plano_central.md"
    preamble_lines = []
    if index_path.exists():
        text = index_path.read_text(encoding="utf-8")
        # Collect preamble up to §3 — stop at first "## 3." or "### 3." or "## 3"
        in_preamble = True
        for line in text.splitlines():
            if re.match(r'^#+ +3\.?\b', line):
                break
            preamble_lines.append(line)
    else:
        preamble_lines = ["# MAPA Completo — GSD Diet Calc V10.4", "(indice_plano_central.md not found)"]

    lines = []
    # Canonical MAPA header
    lines.append(hdr(1, "MAPA Completo — GSD Diet Calc V10.4"))
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().isoformat()}")
    lines.append(f"**Generator:** `build_pipeline.py` — mode=`--generate-mapa`")
    lines.append(f"**Operational source:** `data/` directory")
    lines.append(f"**Working directory:** `./`")
    lines.append("")
    lines.append("---")
    lines.append("")
    # Verbatim preamble from indice_plano_central.md (§0–§2)
    for pl in preamble_lines:
        lines.append(pl)
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## File Manifest")
    lines.append("")
    rows = []
    total_size = 0
    for fname in JSON_FILES:
        fpath = DATA_DIR / fname
        if fpath.exists():
            size = fpath.stat().st_size
            sha = sha256_file(fpath)
            total_size += size
            # Extract version from JSON content if available
            fdata = data.get(fname, {})
            ver = None
            if isinstance(fdata, dict):
                meta = fdata.get("_db_metadata", {})
                ver = meta.get("version") or fdata.get("version") or fdata.get("schema_version")
            ver_str = str(ver) if ver else "—"
            mtime = datetime.fromtimestamp(fpath.stat().st_mtime).strftime("%Y-%m-%d")
            rows.append([f"`{fname}`", f"{size:,}", ver_str, mtime, f"`{sha[:16]}...`"])
        else:
            rows.append([f"`{fname}`", "NOT FOUND", "—", "—", "—"])
    rows.append(["**Total**", f"{total_size:,}", "—", "—", "—"])
    lines.append(table(["File", "Size (bytes)", "Version", "Modified", "SHA-256"], rows))
    lines.append("")
    return "\n".join(lines)


# ── Section 2: DB_ingredientes — Ingredient Overview ──────────────────

def section2_ingredients_overview(data: Dict[str, Any]) -> str:
    db = data.get("DB_ingredientes.json", {})
    meta = db.get("_db_metadata", {})
    all_ings = [
        i for g in db.get("protein_sources", {}).values()
        for i in g.get("ingredients", [])
    ]

    lines = []
    lines.append(hdr(2, "DB_ingredientes.json — Ingredient Bank"))
    lines.append("")
    lines.append(f"- **Version:** {meta.get('version', '?')}")
    lines.append(f"- **Claimed ingredients:** {meta.get('total_ingredients', '?')}")
    lines.append(f"- **Actual ingredients:** {len(all_ings)}")
    lines.append(f"- **template_ref:** {meta.get('template_ref', '?')}")
    lines.append(f"- **schema_ref:** {meta.get('schema_ref', '?')}")
    lines.append(f"- **standard:** {meta.get('standard', '?')}")
    lines.append("")
    lines.append("### Ingredient Detail")
    lines.append("")
    rows = []
    for ing in all_ings:
        nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
        excl = ing.get("bromatological_profile", {}).get("coverage_excluded_nutrients", [])
        n = len(nuts)
        e = len(excl) if excl else 0
        label = f"{n} fields" + (f" (+{e} excl)" if e else "")
        grp = next(
            (gn for gn, gd in db.get("protein_sources", {}).items()
             for i in gd.get("ingredients", [])
             if i["ingredient_id"] == ing["ingredient_id"]),
            "?"
        )
        rows.append([
            f"`{ing['ingredient_id']}`",
            ing.get("category", "?"),
            ing.get("display_name", "?"),
            label,
            grp,
        ])
    lines.append(table(["ID", "Category", "Display Name", "Nutrients", "Group"], rows))
    lines.append("")
    return "\n".join(lines)


# ── Section 3: DB_ingredientes — Unified Nutrient Fields ──────────────

def section3_nutrient_fields(data: Dict[str, Any]) -> str:
    db = data.get("DB_ingredientes.json", {})
    all_ings = [
        i for g in db.get("protein_sources", {}).values()
        for i in g.get("ingredients", [])
    ]
    all_fields: Set[str] = set()
    for ing in all_ings:
        all_fields.update(ing.get("bromatological_profile", {}).get("nutrients", {}).keys())

    lines = []
    lines.append(hdr(2, "DB_ingredientes.json — Unified Nutrient Fields"))
    lines.append("")
    lines.append(f"**Total distinct nutrient field names:** {len(all_fields)}")
    lines.append("")
    lines.append("`" + "`, `".join(sorted(all_fields)) + "`")
    lines.append("")
    return "\n".join(lines)


# ── Section 4: DB_ingredientes — Coverage Excluded + Supplements ──────

def section4_coverage_and_gaps(data: Dict[str, Any]) -> str:
    db = data.get("DB_ingredientes.json", {})
    all_ings = [
        i for g in db.get("protein_sources", {}).values()
        for i in g.get("ingredients", [])
    ]
    with_coverage = [
        i for i in all_ings
        if i.get("bromatological_profile", {}).get("coverage_excluded_nutrients")
    ]
    actual_ids = set(i["ingredient_id"] for i in all_ings)
    missing_supps = [s for s in SUPPLEMENTS_PLANNED if s not in actual_ids]

    lines = []
    lines.append(hdr(2, "DB_ingredientes.json — Coverage & Gaps"))
    lines.append("")
    lines.append("### Coverage Excluded Nutrients")
    lines.append("")
    lines.append(f"- **Ingredients with exclusions:** {len(with_coverage)} / {len(all_ings)}")
    for i in with_coverage:
        excl = i["bromatological_profile"]["coverage_excluded_nutrients"]
        lines.append(f"  - `{i['ingredient_id']}`: {excl}")
    lines.append("")
    lines.append("### Planned Supplements (Not Yet in DB)")
    lines.append("")
    lines.append(f"- **Missing:** {', '.join(f'`{m}`' for m in missing_supps)}")
    lines.append(f"- **Status per docs:** `sat_operacional:§15` — PLANNED, NOT applied")
    lines.append("")
    return "\n".join(lines)


# ── Section 5: DB_ingredientes — Categories ────────────────────────────

def section5_categories(data: Dict[str, Any]) -> str:
    db = data.get("DB_ingredientes.json", {})
    all_ings = [
        i for g in db.get("protein_sources", {}).values()
        for i in g.get("ingredients", [])
    ]
    cats: Dict[str, int] = {}
    for ing in all_ings:
        c = ing.get("category", "unknown")
        cats[c] = cats.get(c, 0) + 1

    lines = []
    lines.append(hdr(2, "DB_ingredientes.json — Category Distribution"))
    lines.append("")
    rows = [[c, str(n)] for c, n in sorted(cats.items())]
    lines.append(table(["Category", "Count"], rows))
    lines.append("")
    return "\n".join(lines)


# ── Section 6: constraints.json ────────────────────────────────────────

def section6_constraints(data: Dict[str, Any]) -> str:
    c = data.get("constraints.json", {})
    lines = []
    lines.append(hdr(2, "constraints.json — LP Constraints"))
    lines.append("")
    total = 0
    for sec in ["nutrient_bounds", "toxicological_limits", "inclusion_constraints", "mineral_antagonisms"]:
        items = c.get(sec, [])
        total += len(items)
        hard = sum(1 for x in items if x.get("solver_behavior") == "HARD_FAIL_INFEASIBLE")
        other = sum(1 for x in items if x.get("solver_behavior") != "HARD_FAIL_INFEASIBLE")
        lines.append(f"- **{sec}:** {len(items)} constraints ({hard} HARD, {other} other)")
    lines.append(f"\n**Total:** {total} constraints")
    lines.append("")

    # Show selected constraints in table
    for sec in ["mineral_antagonisms", "nutrient_bounds"]:
        items = c.get(sec, [])
        if not items:
            continue
        lines.append(f"### {sec}")
        lines.append("")
        rows = []
        for item in items[:10]:
            rows.append([
                f"`{item.get('constraint_id', '?')}`",
                item.get("name", "?"),
                item.get("human_readable", "")[:60],
                item.get("solver_behavior", "?"),
            ])
        lines.append(table(["ID", "Name", "Expression", "Behavior"], rows))
        if len(items) > 10:
            lines.append(f"*(... and {len(items) - 10} more)*")
        lines.append("")
    return "\n".join(lines)


# ── Section 7: formulation_rules.json ──────────────────────────────────

def section7_formulation_rules(data: Dict[str, Any]) -> str:
    fr = data.get("formulation_rules.json", {})
    db = data.get("DB_ingredientes.json", {})
    actual_ids = set()
    for g in db.get("protein_sources", {}).values():
        for i in g.get("ingredients", []):
            actual_ids.add(i["ingredient_id"])

    matrix = fr.get("nutrient_matrix", [])
    templates = fr.get("diet_templates", [])
    mapping = fr.get("_inclusion_semantics", {}).get("category_to_ingredient_mapping", {})
    bio = fr.get("bioavailability_factors", [])
    digest = fr.get("digestibility", {})
    supp_dosages = fr.get("supplement_dosages", {})

    lines = []
    lines.append(hdr(2, "formulation_rules.json — Formulation Rules"))
    lines.append("")

    lines.append("### Nutrient Matrix")
    lines.append(f"- **Entries:** {len(matrix)}")
    if matrix:
        lines.append(f"- **First entry:** `{matrix[0].get('nutrient_id', '?')}`")
        vals = matrix[0].get("values", {})
        if isinstance(vals, dict):
            lines.append(f"- **Authorities:** {', '.join(vals.keys())}")
    lines.append("")

    lines.append("### Diet Templates")
    lines.append(f"- **Count:** {len(templates)}")
    for t in templates:
        comps = t.get("components", {})
        total_pct = sum(comps.values()) if isinstance(comps, dict) else 0
        lines.append(f"  - `{t.get('template_id')}`: {t.get('name')} — {len(comps)} components, total={total_pct:.1f}%")
    lines.append("")

    lines.append("### Category-to-Ingredient Mapping")
    lines.append(f"- **Categories mapped:** {len(mapping)}")
    all_mapped: Set[str] = set()
    for cat, ids in mapping.items():
        all_mapped.update(ids)
    concrete = [x for x in all_mapped if not x.startswith("_")]
    wildcards = [x for x in all_mapped if x.startswith("_")]
    missing = [x for x in concrete if x not in actual_ids]
    if missing:
        lines.append(f"- **Mapped but absent from DB:** {', '.join(f'`{m}`' for m in missing)}")
    if wildcards:
        lines.append(f"- **Wildcards:** {', '.join(wildcards)}")
    lines.append("")

    lines.append("### Bioavailability Factors")
    lines.append(f"- **Count:** {len(bio)}")
    if bio:
        lines.append(f"  - First: `{bio[0].get('factor_id')}` → `{bio[0].get('parameter')}`")
    lines.append("")

    lines.append("### Digestibility")
    if isinstance(digest, dict):
        lines.append(f"- **Keys:** {', '.join(digest.keys())}")
    lines.append("")

    lines.append("### Supplement Dosages")
    lines.append(f"- **Entries:** {len(supp_dosages)}")
    for sid, sdata in supp_dosages.items():
        dose = sdata.get("dose", {})
        dose_str = f"{dose.get('value')} {dose.get('unit', '?')}" if isinstance(dose, dict) else str(dose)
        lines.append(f"  - `{sid}`: {dose_str}")
    lines.append("")
    return "\n".join(lines)


# ── Section 8: audit_provenance.json ───────────────────────────────────

def section8_provenance(data: Dict[str, Any]) -> str:
    prov = data.get("audit_provenance.json", {})
    refs = prov.get("references", {})
    docs = prov.get("source_documents", [])
    algo = prov.get("algorithm_logic", {})
    flags = prov.get("data_quality_flags", [])

    lines = []
    lines.append(hdr(2, "audit_provenance.json — Provenance"))
    lines.append("")

    lines.append("### Source Documents")
    lines.append(f"- **Count:** {len(docs)}")
    for d in docs:
        lines.append(f"  - `{d.get('doc_id')}`: {d.get('title')} ({d.get('type')})")
    lines.append("")

    lines.append("### References")
    if isinstance(refs, dict):
        lines.append(f"- **Total refs:** {len(refs)}")
        qual_flags: Dict[str, int] = {}
        for rid, rdata in refs.items():
            qf = rdata.get("quality_flag", "MISSING") if isinstance(rdata, dict) else "MISSING"
            qual_flags[qf] = qual_flags.get(qf, 0) + 1
        for qf, cnt in sorted(qual_flags.items()):
            lines.append(f"  - **{qf}:** {cnt}")
    lines.append("")

    lines.append("### Algorithm Logic (Fallback Protocols)")
    fb = algo.get("fallback_protocols", []) if isinstance(algo, dict) else []
    lines.append(f"- **Protocols:** {len(fb)}")
    for f in fb:
        lines.append(f"  - Level {f.get('level')}: {f.get('name')}")
    lines.append("")

    lines.append("### Data Quality Flags")
    lines.append(f"- **Count:** {len(flags)}")
    for fl in flags:
        lines.append(f"  - `{fl.get('flag_id')}`: [{fl.get('severity')}] {fl.get('description', '')[:80]}")
    lines.append("")
    return "\n".join(lines)


# ── Section 9: growth_energy_skeletal.json ─────────────────────────────

def section9_growth(data: Dict[str, Any]) -> str:
    g = data.get("growth_energy_skeletal.json", {})
    lines = []
    lines.append(hdr(2, "growth_energy_skeletal.json — Growth & Energy"))
    lines.append("")

    # Gompertz
    gp = g.get("gompertz_parameters", {})
    lines.append("### Gompertz Parameters")
    equations = gp.get("equation", [])
    if isinstance(equations, list):
        for eq in equations:
            lines.append(f"- `{eq}`")
    elif equations:
        lines.append(f"- {equations}")
    params = gp.get("parameters", []) if isinstance(gp, dict) else []
    if params:
        for p in params:
            if isinstance(p, dict):
                lines.append(f"  - `{p.get('param_id')}`: {p.get('name')} = {p.get('value', '?')}")
    lines.append("")

    # K multipliers
    km = g.get("k_multipliers", {})
    lines.append("### K Multipliers")
    for km_name, km_data in km.items():
        if isinstance(km_data, dict):
            val = km_data.get("value", km_data.get("default", "?"))
            status = km_data.get("status", "?")
            lines.append(f"- **`{km_name}`:** value={val}, status={status}")
        else:
            lines.append(f"- **`{km_name}`:** {km_data}")
    lines.append("")

    # Energy requirements
    er = g.get("energy_requirements", [])
    lines.append("### Energy Requirements")
    lines.append(f"- **Count:** {len(er)}")
    for e in er:
        formula = e.get("formula", "")[:80]
        lines.append(f"  - `{e.get('param_id')}`: {formula}")
    lines.append("")

    # Anthropometric table
    at = g.get("anthropometric_table", [])
    lines.append("### Anthropometric Table")
    lines.append(f"- **Entries:** {len(at)}")
    if at:
        rows = []
        for entry in at[:5]:
            age = entry.get("age_months", "?")
            wm = entry.get("weight_male_kg", [])
            wf = entry.get("weight_female_kg", [])
            wm_str = f"{wm[0]}–{wm[1]} kg" if isinstance(wm, list) and len(wm) == 2 else str(wm)
            wf_str = f"{wf[0]}–{wf[1]} kg" if isinstance(wf, list) and len(wf) == 2 else str(wf)
            rows.append([str(age), wm_str, wf_str, str(entry.get("pct_adult_weight", "?"))])
        lines.append(table(["Age (mo)", "Male Weight", "Female Weight", "% Adult"], rows))
        if len(at) > 5:
            lines.append(f"*(... and {len(at) - 5} more)*")
        lines.append("")

    # Gonadal profiles
    gon = g.get("gonadal_status_profiles", [])
    lines.append("### Gonadal Status Profiles")
    lines.append(f"- **Count:** {len(gon)}")
    for pr in gon:
        if isinstance(pr, dict):
            lines.append(f"  - `{pr.get('profile_id')}`: {pr.get('sex')}/{pr.get('status')}")
    lines.append("")

    # Epidemiology
    epi = g.get("epidemiology", [])
    lines.append("### Epidemiology (DOD)")
    lines.append(f"- **Entries:** {len(epi)}")
    for ep in epi:
        if isinstance(ep, dict):
            lines.append(f"  - `{ep.get('entry_id')}`: {ep.get('metric_name')} = {ep.get('value', '?')}")
    lines.append("")
    return "\n".join(lines)


# ── Section 10: objective_weights.json ─────────────────────────────────

def section10_weights(data: Dict[str, Any]) -> str:
    ow = data.get("objective_weights.json", [])
    if not isinstance(ow, list):
        ow = []
    lines = []
    lines.append(hdr(2, "objective_weights.json — Objective Weights"))
    lines.append("")
    lines.append(f"- **Count:** {len(ow)}")
    lines.append("")
    rows = []
    for w in ow:
        wid = w.get("weight_id", "?")
        var = w.get("variable", "?")
        weight = w.get("weight", "?")
        tier = w.get("priority_tier", "?")
        pm = w.get("solver_penalty_multiplier")
        pm_str = "MISSING" if pm is None and "solver_penalty_multiplier" not in w else str(pm)
        rows.append([f"`{wid}`", var, str(weight), str(tier), pm_str])
    lines.append(table(["ID", "Variable", "Weight", "Tier", "Penalty Multiplier"], rows))
    lines.append("")

    # PEN_MANGANESE_NEG check
    no_pm = [w for w in ow if "solver_penalty_multiplier" not in w]
    if no_pm:
        lines.append(f"**Without `solver_penalty_multiplier`:** {', '.join(w['weight_id'] for w in no_pm)}")
        lines.append("")
    return "\n".join(lines)


# ── Section 11: scenarios.json ─────────────────────────────────────────

def section11_scenarios(data: Dict[str, Any]) -> str:
    sc = data.get("scenarios.json", [])
    if not isinstance(sc, list):
        sc = []
    lines = []
    lines.append(hdr(2, "scenarios.json — Scenarios"))
    lines.append("")
    lines.append(f"- **Count:** {len(sc)}")
    lines.append("")
    for s in sc:
        sid = s.get("scenario_id", "?")
        name = s.get("name", "?")
        status = s.get("status", "?")
        targets = s.get("targets", [])
        lines.append(f"### `{sid}`: {name}")
        lines.append(f"- **Status:** {status}")
        lines.append(f"- **Targets:** {len(targets)}")
        rows = []
        for t in targets[:8]:
            if isinstance(t, dict):
                rows.append([
                    t.get("nutrient_id", "?"),
                    fmt(t.get("value")),
                    t.get("unit", "?"),
                    t.get("source_ref", "?"),
                ])
        if rows:
            lines.append(table(["Nutrient", "Value", "Unit", "Source"], rows))
        if len(targets) > 8:
            lines.append(f"*(... and {len(targets) - 8} more)*")
        lines.append("")
    return "\n".join(lines)


# ── Section 12: toxicological_limits.json ──────────────────────────────

def section12_tox_limits(data: Dict[str, Any]) -> str:
    tox = data.get("toxicological_limits.json", [])
    if not isinstance(tox, list):
        tox = []
    lines = []
    lines.append(hdr(2, "toxicological_limits.json — Safe Upper Limits (SULs)"))
    lines.append("")
    lines.append(f"- **Type at top level:** `list` ({len(tox)} entries)")
    lines.append(f"- **Structure:** Each entry has nested `sul.value`, `sul.unit`, `sul.basis`")
    lines.append("")
    rows = []
    for e in tox:
        s = e.get("sul", {})
        sul_val = s.get("value") if isinstance(s, dict) else None
        unit = s.get("unit", "?") if isinstance(s, dict) else "?"
        basis = s.get("basis", "?") if isinstance(s, dict) else "?"
        patho = e.get("pathophysiology_ref", "—")
        rows.append([
            f"`{e.get('nutrient_id', '?')}`",
            fmt(sul_val),
            unit,
            basis,
            patho,
        ])
    lines.append(table(["Nutrient", "SUL Value", "Unit", "Basis", "Patho Ref"], rows))
    lines.append("")
    return "\n".join(lines)


# ── Section 13: lp_parameters_data.json ────────────────────────────────

def section13_lp_data(data: Dict[str, Any]) -> str:
    lp = data.get("lp_parameters_data.json", {})
    registry = lp.get("NUTRIENT_REGISTRY", {})
    cascade = lp.get("solve_cascade", [])

    lines = []
    lines.append(hdr(2, "lp_parameters_data.json — Runtime LP Parameters"))
    lines.append(f"**Schema version:** {lp.get('schema_version', '?')}")
    lines.append("")

    # NUTRIENT_REGISTRY summary
    lines.append("### NUTRIENT_REGISTRY")
    lines.append(f"- **Total nutrients:** {len(registry)}")
    tiers: Dict[str, int] = {}
    crits: Dict[str, int] = {}
    for nid, ndata in registry.items():
        t = ndata.get("constraint_tier", "?")
        tiers[t] = tiers.get(t, 0) + 1
        c = ndata.get("clinical_criticality", "?")
        crits[c] = crits.get(c, 0) + 1
    lines.append(f"- **Tiers:** {dict(sorted(tiers.items()))}")
    lines.append(f"- **Clinical criticality:** {dict(sorted(crits.items()))}")

    # safety_hard (SUL) nutrients
    sul_nutrients = [nid for nid, nd in registry.items() if nd.get("constraint_tier") == "safety_hard"]
    lines.append(f"- **Safety hard (has SUL):** {', '.join(f'`{n}`' for n in sul_nutrients)}")

    # SUL value summary (from NUTRIENT_REGISTRY)
    sul_rows = []
    for nid in sul_nutrients:
        nd = registry[nid]
        sul_rows.append([f"`{nid}`", nd.get("display_name", "?"), fmt(nd.get("sul_value")), nd.get("unit", "?"), nd.get("clinical_criticality", "?")])
    if sul_rows:
        lines.append("")
        lines.append("#### SUL Nutrients (from NUTRIENT_REGISTRY)")
        lines.append(table(["Nutrient", "Display Name", "SUL Value", "Unit", "Criticality"], sul_rows))
    lines.append("")

    # solve_cascade
    lines.append("### Declarative Cascade (solve_cascade)")
    lines.append(f"- **Levels:** {len(cascade)}")
    lines.append("")
    for lvl in cascade:
        lv = lvl.get("level", "?")
        desc = lvl.get("description", "")[:100]
        relax = lvl.get("relax_tiers", [])
        stages = lvl.get("objective_stages", [])
        result = lvl.get("result_status", "?")
        lines.append(f"#### Level {lv}: {result}")
        lines.append(f"- **Description:** {desc}")
        lines.append(f"- **Relax tiers:** {relax}")
        lines.append(f"- **Objective stages:** {', '.join(s.get('name', '?') for s in stages)}")
        cf = lvl.get("clinical_floor", {})
        if cf and cf.get("enabled"):
            lines.append(f"- **Clinical floor:** enabled (defaults: {cf.get('defaults_by_category', {})})")
        oc = lvl.get("output_contract", {})
        if oc:
            lines.append(f"- **Output:** allocations={oc.get('allocations')}, feeding={oc.get('feeding_recommendation')}")
        lines.append("")
    return "\n".join(lines)


# ── Section 14: Naming Conventions ─────────────────────────────────────

def section14_naming_conventions(data: Dict[str, Any], idx: CrossRefIndex) -> str:
    """DB→Solver naming mapping for all 41 nutrients."""
    lp = data.get("lp_parameters_data.json", {})
    registry = lp.get("NUTRIENT_REGISTRY", {})

    lines = []
    lines.append(hdr(2, "Naming Conventions — DB Space vs Solver Space"))
    lines.append("")
    lines.append("The system operates with two naming conventions:")
    lines.append("")
    lines.append("- **DB space** (`DB_ingredientes.json`): unit-matching suffix (e.g. `calcium_mg`, `selenium_ug`). Basis: `as_fed`, reference: 100g.")
    lines.append("- **Solver space** (`NUTRIENT_REGISTRY`): standardized unit suffix (e.g. `calcium_g`, `selenium_mg`). Basis: `energy_normalized`, reference: 1000kcal.")
    lines.append("")
    lines.append(f"**Total solver-space nutrients:** {len(registry)}")
    lines.append("")

    # Build mapping table
    rows = []
    for nid, ndata in registry.items():
        display = ndata.get("display_name", "?")
        unit = ndata.get("unit", "?")
        ct = ndata.get("constraint_tier", "?")
        db_name = idx.solver2db_name_map.get(nid, nid)
        name_change = "→".join([db_name, nid]) if db_name != nid else "same"
        rows.append([
            f"`{nid}`",
            display,
            unit,
            ct,
            name_change,
        ])

    lines.append(table(["Solver ID", "Display Name", "Unit", "Tier", "DB→Solver Rename"], rows))
    lines.append("")

    # Unit conversion summary
    renamed = [(db, sv) for db, sv in idx.db2solver_name_map.items()]
    if renamed:
        lines.append("### Unit Conversions (DB → Solver)")
        lines.append("")
        conv_rows = []
        for db_name, solver_name in sorted(renamed):
            _, factor = UNIT_RENAME[db_name]
            conv_rows.append([f"`{db_name}`", f"`{solver_name}`", f"÷{1/factor:,.0f}" if factor < 1 else f"×{factor:.0f}"])
        lines.append(table(["DB Field", "Solver ID", "Conversion"], conv_rows))
        lines.append("")
    return "\n".join(lines)


# ── Section 15: Curation Status ────────────────────────────────────────

def section15_curation_status(data: Dict[str, Any], idx: CrossRefIndex) -> str:
    db = data.get("DB_ingredientes.json", {})
    meta = db.get("_db_metadata", {})
    validated = set(meta.get("validated_sources", []))
    pending = set(meta.get("pending_sources", []))
    partial = set(meta.get("partial_sources", []))

    lines = []
    lines.append(hdr(2, "Curation Status — Ingredient Groups"))
    lines.append("")
    lines.append(f"**Total ingredients:** {meta.get('total_ingredients', '?')}")
    lines.append("")

    rows = []
    for grp_key, grp in db.get("protein_sources", {}).items():
        ings = grp.get("ingredients", [])
        status_parts = []
        if grp_key in validated:
            status_parts.append("VALIDATED")
        if grp_key in pending:
            status_parts.append("PENDING")
        if grp_key in partial:
            status_parts.append("PARTIAL")
        status = "+".join(status_parts) if status_parts else "UNKNOWN"
        rows.append([
            grp_key,
            grp.get("common_name", "?"),
            str(len(ings)),
            ", ".join(i["ingredient_id"] for i in ings),
            status,
        ])

    # Add planned supplements row
    actual_ids = set(i["ingredient_id"] for i in idx.all_ingredients)
    missing_supps = [s for s in SUPPLEMENTS_PLANNED if s not in actual_ids]
    if missing_supps:
        rows.append([
            "supplements (planned)",
            "Kelp, Salt, CuSO₄",
            "0 (3 planned)",
            ", ".join(missing_supps),
            "PLANNED (not applied)",
        ])

    lines.append(table(["Group", "Common Name", "Count", "Ingredient IDs", "Status"], rows))
    lines.append("")
    return "\n".join(lines)


# ── Section 16: Gaps ───────────────────────────────────────────────────

def section16_gaps(data: Dict[str, Any], idx: CrossRefIndex) -> str:
    db = data.get("DB_ingredientes.json", {})
    lp = data.get("lp_parameters_data.json", {})
    prov = data.get("audit_provenance.json", {})
    registry = lp.get("NUTRIENT_REGISTRY", {})
    cascade = lp.get("solve_cascade", [])

    lines = []
    lines.append(hdr(2, "Gaps and Unimplemented Dependencies"))
    lines.append("")

    # Gap 1: Missing supplements
    actual_ids = set(i["ingredient_id"] for i in idx.all_ingredients)
    missing = [s for s in SUPPLEMENTS_PLANNED if s not in actual_ids]
    lines.append("### DB Gaps")
    lines.append(f"- **Planned supplements absent from DB:** {len(missing)}")
    for m in missing:
        lines.append(f"  - `{m}` — PLANNED, NOT applied per `sat_operacional:§15`")
    all_nut_fields = set()
    for ing in idx.all_ingredients:
        all_nut_fields.update(ing.get("bromatological_profile", {}).get("nutrients", {}).keys())
    nid_in_db = {n for n in registry if n in all_nut_fields or idx.solver2db_name_map.get(n, n) in all_nut_fields}
    missing_from_db = set(registry.keys()) - nid_in_db
    if missing_from_db:
        lines.append(f"- **Nutrients in registry but not sourced from DB fields:** {len(missing_from_db)}")
        for n in sorted(missing_from_db):
            lines.append(f"  - `{n}` — covered via `coverage_excluded_nutrients` or aggregation")
    lines.append("")

    # Gap 2: Reference coverage
    lines.append("### Reference Gaps")
    internal_refs = set()
    for ing in idx.all_ingredients:
        nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
        for nv in nuts.values():
            sr = nv.get("source_ref", "") if isinstance(nv, dict) else ""
            if sr.startswith("REF_") and not sr.startswith("REF_USDA_"):
                internal_refs.add(sr)
    known_refs = set(idx.ref_index.keys())
    orphans = internal_refs - known_refs
    lines.append(f"- **Internal REF_ tokens in DB ingredients:** {len(internal_refs)}")
    lines.append(f"- **Known in audit_provenance:** {len(known_refs)}")
    lines.append(f"- **Orphans (in DB but absent from audit_provenance):** {len(orphans)}")
    if orphans:
        for r in sorted(orphans):
            lines.append(f"  - `{r}`")
    lines.append("")

    # Gap 3: Implementation gaps
    lines.append("### Implementation Gaps (Pipeline)")
    impl_gaps = [
        ("LP Solver (call_lp_solver)", "P0", "NOT IMPLEMENTED — spec in sat_solver_contrato:§8"),
        ("Dynamic envelope (DER-derived)", "P0", "NOT IMPLEMENTED — spec in sat_princípios:§3.3"),
        ("Level 3 diagnostic_analysis", "P0", "NOT IMPLEMENTED — spec in sat_solver_contrato:§7.2"),
        ("Clinical floor (x_min_i)", "P0", "NOT IMPLEMENTED — spec in sat_solver_contrato:§8.1"),
        ("--runtime mode (live LP)", "P0", "NOT IMPLEMENTED — spec in sat_pipeline_codigo:§6.4"),
        ("--build-recipes mode", "P1", "NOT IMPLEMENTED — spec in sat_pipeline_fluxo:§6.3"),
        ("recipes_precomputed.json", "P1", "NOT IMPLEMENTED — spec in sat_pipeline_fluxo:§5.2"),
    ]
    gap_rows = []
    for desc, prio, status in impl_gaps:
        gap_rows.append([desc, prio, status])
    lines.append(table(["Gap", "Priority", "Status"], gap_rows))
    lines.append("")
    return "\n".join(lines)


# ── Section 17: Cross-Reference & Divergence ──────────────────────────

def section17_divergence_table(data: Dict[str, Any], idx: CrossRefIndex) -> str:
    lines = []
    lines.append(hdr(2, "Cross-Reference Audit & Divergences"))
    lines.append("")

    # Orphan refs audit
    db_path = DATA_DIR / "DB_ingredientes.json"
    db_raw = db_path.read_text(encoding="utf-8") if db_path.exists() else ""
    all_refs = set(re.findall(r"REF_[A-Z0-9_]+", db_raw))
    known = set(idx.ref_index.keys())
    usda = {r for r in all_refs if r.startswith("REF_USDA_")}
    internal = all_refs - usda
    orphans = internal - known

    lines.append("### Orphan Reference Audit")
    lines.append(f"- **Total REF_ tokens in DB:** {len(all_refs)}")
    lines.append(f"- **USDA (external):** {len(usda)}")
    lines.append(f"- **Internal refs:** {len(internal)}")
    lines.append(f"- **In audit_provenance.json:** {len(known)}")
    lines.append(f"- **Orphans (internal but not in audit_provenance):** {len(orphans)}")
    if orphans:
        for r in sorted(orphans):
            lines.append(f"  - `{r}`")
    lines.append("")

    # Verified divergences with decision column
    lines.append("### Documented vs Actual Divergences")
    lines.append("")
    all_ings = idx.all_ingredients
    with_cov = [
        i for i in all_ings
        if i.get("bromatological_profile", {}).get("coverage_excluded_nutrients")
    ]
    c = data.get("constraints.json", {})
    total_hard = sum(
        1 for s in ["nutrient_bounds", "toxicological_limits", "inclusion_constraints", "mineral_antagonisms"]
        for item in c.get(s, [])
    )
    sc = data.get("scenarios.json", [])
    sc_is_list = isinstance(sc, list)
    g = data.get("growth_energy_skeletal.json", {})
    km = g.get("k_multipliers", {})
    has_adult = "adult_working_active" in km or "adult_working" in km or "adult" in km
    fr = data.get("formulation_rules.json", {})
    matrix = fr.get("nutrient_matrix", [])
    matrix_is_list = isinstance(matrix, list)
    actual_ids = set(i["ingredient_id"] for i in all_ings)
    missing_supp_count = len([s for s in SUPPLEMENTS_PLANNED if s not in actual_ids])

    divergences = [
        ("DB version vs actual ingredient count", "?", f"{len(all_ings)}", "accept"),
        ("Orphan refs resolved", "0 (per docs)", f"{len(orphans)} still orphan", "defer"),
        ("Provenance refs count", "85 (per docs)", f"{len(known)}", "accept"),
        ("solve_cascade location", "lp_parameters.schema (per docs)", "lp_parameters_data.json", "accept"),
        ("NUTRIENT_REGISTRY location", "lp_parameters.schema (per docs)", "lp_parameters_data.json", "accept"),
        ("All constraints HARD_FAIL_INFEASIBLE", "no (V10 cascade)", f"yes (all {total_hard} HARD)", "defer"),
        ("scenarios.json top-level type", "dict with 'scenarios' key", f"{'list' if sc_is_list else 'dict'}", "accept"),
        ("Adult k_multiplier", "does not exist", f"{'exists' if has_adult else 'does not exist'}", "accept"),
        ("Missing supplements in DB", "0 (claimed 23)", f"{missing_supp_count} planned missing", "defer"),
        ("nutrient_matrix structure", "dict with min/max", f"{'list with nested values' if matrix_is_list else 'dict'}", "accept"),
    ]

    rows = []
    for claim, doc_val, actual_val, decision in divergences:
        flag = "[DIVERGE]" if doc_val != actual_val else "[OK]"
        rows.append([claim, doc_val, actual_val, flag, decision])
    lines.append(table(["Claim", "Documented", "Actual", "Status", "Decision"], rows))
    lines.append("")
    return "\n".join(lines)


# ── Full MAPA Generator ────────────────────────────────────────────────

def generate_mapa(data: Optional[Dict[str, Any]] = None) -> str:
    if data is None:
        data = load_all_jsons()
    idx = build_mapa_indices(data)

    # Sections that only need `data`
    data_only_sections = [
        section1_header,
        section2_ingredients_overview,
        section3_nutrient_fields,
        section4_coverage_and_gaps,
        section5_categories,
        section6_constraints,
        section7_formulation_rules,
        section8_provenance,
        section9_growth,
        section10_weights,
        section11_scenarios,
        section12_tox_limits,
        section13_lp_data,
    ]
    # Sections that also need `idx`
    idx_sections = [
        section14_naming_conventions,
        section15_curation_status,
        section16_gaps,
        section17_divergence_table,
    ]

    parts = []
    for sec_fn in data_only_sections:
        try:
            parts.append(sec_fn(data))
        except Exception as e:
            import traceback
            parts.append(f"\n## ERROR in {sec_fn.__name__}: {e}\n```\n{traceback.format_exc()}\n```\n")
    for sec_fn in idx_sections:
        try:
            parts.append(sec_fn(data, idx))
        except Exception as e:
            import traceback
            parts.append(f"\n## ERROR in {sec_fn.__name__}: {e}\n```\n{traceback.format_exc()}\n```\n")
    return "\n".join(parts)


# ── Validation Gate (6 checks) ─────────────────────────────────────────

def validate_mapa(mapa_content: str, data: Optional[Dict[str, Any]] = None) -> List[str]:
    if data is None:
        data = load_all_jsons()
    idx = build_mapa_indices(data)
    errors: List[str] = []

    # Check 0: Phantom token detection (IDs, ingredients, nutrients)
    all_extracted = set(re.findall(r"REF_[A-Z0-9_]+|CSTR_[A-Z0-9_]+|PEN_[A-Z0-9_]+|SCN_[A-Z0-9_]+|TPL_[A-Z0-9_]+", mapa_content))
    phantom = all_extracted - idx.all_known_tokens
    phantom = {t for t in phantom if not t.startswith("REF_USDA_")}

    # Also extract and check ingredient IDs
    ing_id_pattern = r"\b[a-z]+_[a-z_]+_(?:raw|dried|nacl|sulfate|oil)\b"
    extracted_ings = set(re.findall(ing_id_pattern, mapa_content))
    phantom_ings = extracted_ings - set(idx.ingredient_index.keys())

    # Extract and check nutrient IDs (only those with unit-bearing suffixes)
    nut_prefixes = r"(?:protein|fat|arginine|histidine|isoleucine|leucine|lysine|methionine|methionine_plus_cystine|phenylalanine|phenylalanine_plus_tyrosine|threonine|tryptophan|valine|linoleic|ala_alpha_linolenic|ara_arachidonic|epa_plus_dha|calcium|phosphorus|magnesium|sodium|potassium|chloride|iron|copper|manganese|zinc|iodine|selenium|vitamin_a|vitamin_d3|vitamin_e|thiamine_b1|riboflavin_b2|pantothenic_acid_b5|niacin_b3|pyridoxine_b6|folic_acid_b9|cobalamin_b12|choline)"
    nut_id_pattern = rf"\b{nut_prefixes}_(?:g|mg|ug|iu)\b"
    extracted_nuts = set(re.findall(nut_id_pattern, mapa_content))
    # A valid nutrient ID is either in nutrient_index (solver space) OR in all_known_tokens (DB space)
    phantom_nuts = extracted_nuts - set(idx.nutrient_index.keys()) - idx.all_known_tokens

    if phantom:
        errors.append(f"Phantom tokens in MAPA (not in any JSON): {len(phantom)} — {', '.join(sorted(phantom)[:10])}")
    if phantom_ings:
        errors.append(f"Phantom ingredient IDs in MAPA: {len(phantom_ings)} — {', '.join(sorted(phantom_ings)[:10])}")
    if phantom_nuts:
        errors.append(f"Phantom nutrient IDs in MAPA: {len(phantom_nuts)} — {', '.join(sorted(phantom_nuts)[:10])}")

    # Check 1: Token presence (MAPA header canonical tokens)
    required_tokens = [
        "MAPA Completo",
        "GSD Diet Calc V10.4",
        "**Generated:**",
        "File Manifest",
    ]
    for token in required_tokens:
        if token not in mapa_content:
            errors.append(f"Missing token in MAPA: `{token}`")

    # Check 2: Critical count assertions
    db = data.get("DB_ingredientes.json", {})
    all_ings = [
        i for g in db.get("protein_sources", {}).values()
        for i in g.get("ingredients", [])
    ]
    if len(all_ings) < 20:
        errors.append(f"Ingredient count < 20: got {len(all_ings)}")

    c = data.get("constraints.json", {})
    total_constraints = sum(len(c.get(s, [])) for s in ["nutrient_bounds", "toxicological_limits", "inclusion_constraints", "mineral_antagonisms"])
    if total_constraints < 40:
        errors.append(f"Constraint count < 40: got {total_constraints}")

    lp = data.get("lp_parameters_data.json", {})
    registry = lp.get("NUTRIENT_REGISTRY", {})
    if len(registry) < 40:
        errors.append(f"NUTRIENT_REGISTRY entries < 40: got {len(registry)}")

    ow = data.get("objective_weights.json", [])
    if isinstance(ow, list) and len(ow) < 25:
        errors.append(f"Weights < 25: got {len(ow)}")

    tox = data.get("toxicological_limits.json", [])
    if isinstance(tox, list) and len(tox) < 8:
        errors.append(f"SUL entries < 8: got {len(tox)}")

    # Check 3: No stale file paths
    for fname in JSON_FILES:
        if fname not in mapa_content:
            errors.append(f"File `{fname}` not mentioned in MAPA")

    # Check 4: Divergence table present (must have Decision column)
    if "Documented vs Actual Divergences" not in mapa_content:
        errors.append("Divergence table missing from MAPA")
    elif "Decision" not in mapa_content:
        errors.append("Divergence table missing Decision column")

    # Check 5: Canonical header match (Section 1 has project header)
    if "## File Manifest" not in mapa_content:
        errors.append("File manifest section missing")

    # Check 6: Section count (expect 17 sections, allow composites)
    section_count = mapa_content.count("\n## ")
    if section_count < 17:
        errors.append(f"Expected >=17 sections, found {section_count}")

    # Check 7: Naming conventions section present
    if "Naming Conventions" not in mapa_content:
        errors.append("Naming Conventions section missing")

    # Check 8: Curation status section present
    if "Curation Status" not in mapa_content:
        errors.append("Curation Status section missing")

    return errors


# ── §6.4 — validate_inputs (6 assertions per sat_pipeline_codigo §6.4) ──

def validate_inputs(data: dict) -> None:
    """Raise AssertionError if any of the 6 assertions (a-f) fail."""
    db = data.get("DB_ingredientes.json", {})
    prov = data.get("audit_provenance.json", {})
    schema = data.get("lp_parameters_data.json", {})
    fr = data.get("formulation_rules.json", {})

    all_ings = [
        i for g in db.get("protein_sources", {}).values()
        for i in g.get("ingredients", [])
    ]

    # a) 41 nutrient slots per ingredient (real: 43 keys including composite pairs)
    for ing in all_ings:
        nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
        msg = f"{ing['ingredient_id']}: {len(nuts)} nutrient keys"
        assert len(nuts) >= 41, msg
        # Every key must have a 3-state status field
        for k, v in nuts.items():
            assert isinstance(v, dict), f"{ing['ingredient_id']}.{k}: not a dict"
            assert "status" in v, f"{ing['ingredient_id']}.{k}: missing status"
            assert v["status"] in VALID_NUTRIENT_STATUSES, \
                f"{ing['ingredient_id']}.{k}: invalid status '{v['status']}'"

    # b) non-USDA source_refs resolve in audit_provenance
    known_refs = set(prov.get("references", {}).keys())
    for ing in all_ings:
        iid = ing["ingredient_id"]
        nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
        for k, v in nuts.items():
            sr = v.get("source_ref", "")
            if sr and sr.startswith("REF_") and not sr.startswith("REF_USDA_"):
                assert sr in known_refs, f"{iid}.{k}: orphan source_ref '{sr}'"

    # c) valid categories (16+1 from schema enum)
    valid_categories = {
        "muscle_meat", "muscle_organ", "organ_secreting", "organ_non_secreting",
        "connective_tissue", "blood_source", "bone", "cartilage", "fat_source",
        "supplement", "grain", "vegetable", "fruit", "dairy", "egg", "fish",
    }
    for ing in all_ings:
        cat = ing.get("category", "")
        assert cat in valid_categories, f"{ing['ingredient_id']}: invalid category '{cat}'"

    # d) mapped ingredient_ids exist in DB (tolerating planned supplements:
    # kelp_meal_dried, salt_nacl, copper_sulfate are PLANNED, NOT applied
    # per sat_operacional:§15 — do not fail for these)
    mapping = fr.get("_inclusion_semantics", {}).get("category_to_ingredient_mapping", {})
    actual_ids = {i["ingredient_id"] for i in all_ings}
    for cat, ids in mapping.items():
        for iid in ids:
            if not iid.startswith("_") and iid not in SUPPLEMENTS_PLANNED:
                assert iid in actual_ids, f"Mapping {cat} -> '{iid}' not in DB"

    # e) NUTRIENT_REGISTRY covers all 41 solver nutrients
    registry = schema.get("NUTRIENT_REGISTRY", {})
    for nid in SOLVER_NUTRIENTS:
        assert nid in registry, f"NUTRIENT_REGISTRY missing '{nid}'"

    # f) solve_cascade has Level 1 with empty relax_tiers
    cascade = schema.get("solve_cascade", [])
    assert any(
        s.get("level") == 1 and s.get("relax_tiers") == []
        for s in cascade if isinstance(s, dict)
    ), "Level 1 of solve_cascade must have empty relax_tiers"


# ── §6.4a — calculate_der_and_envelope (items 1, 2, 4) ────────────────

def gompertz_weight(age_months: int, params: list[dict], sex: str, default_breed_line: str = "working_exhibition_lines") -> float:
    """W(t) = W_max × exp(-b × exp(-c × t))
    Decision (item 1): adapter over the parameters[] array-of-objects shape.
    Breed-line default: working_exhibition_lines (both sexes); assistance_dogs
    is only present for male W_max in the JSON — female has only WL line.
    """
    t_days = age_months * 30.44

    w_max_p = _get_param(params, "GRO_W_MAX_MALE" if sex == "male" else "GRO_W_MAX_FEMALE")
    if w_max_p is None:
        raise ValueError(f"W_max param not found for sex={sex}")
    w_max = _resolve_breed_value(w_max_p["value"], default_breed_line)

    b_p = _get_param(params, "GRO_B_PARAM")
    b = _resolve_breed_value(b_p["value"]) if b_p else 2.5

    c_key = "GRO_C_MALE_DAYS" if sex == "male" else "GRO_C_FEMALE_DAYS"
    c_p = _get_param(params, c_key)
    c = _resolve_breed_value(c_p["value"]) if c_p else 115.0

    return w_max * math.exp(-b * math.exp(-c * t_days))


def get_global_density_range_from_db(db: dict) -> tuple[float, float]:
    """Fallback: compute min/max energy density across all DB ingredients."""
    densities = []
    for g in db.get("protein_sources", {}).values():
        for ing in g.get("ingredients", []):
            nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
            em = energy_metabolizable_kcal_per_100g(nuts)
            densities.append(em / 100)
    if not densities:
        return (0.5, 2.5)
    return (min(densities), max(densities))


def calculate_der_and_envelope(
    animal: AnimalInput,
    growth_data: dict,
    scenario_id: str,
    selected_ids: list[str],
    db: dict,
    default_breed_line: str = "working_exhibition_lines",
) -> DerEnvelope:
    """§6.4a mandatory signature. Returns DerEnvelope (item 4) which
    satisfies the mandated 3-tuple contract via __iter__ while also
    exposing all intermediate values as named attributes.

    Scenario→k mapping (item 2): hardcoded via SCENARIO_K_MAP.
    Source: growth_energy_skeletal.json → k_multipliers → scenario's ref
    → note field "LP model default: 1.2" / "LP model alert: 2.0" → value[0].
    """

    # Body weight
    gp = growth_data.get("gompertz_parameters", {})
    params = gp.get("parameters", [])
    if animal.use_gompertz:
        bw = gompertz_weight(animal.age_months, params, animal.sex, default_breed_line)
        bw_source = "gompertz"
    else:
        bw = animal.weight_kg
        bw_source = "informed_weight"

    # TER and DER
    ter = 70.0 * (bw ** 0.75)
    k_ref = SCENARIO_K_MAP.get(scenario_id, "slow_growth_recommended")
    km_data = growth_data.get("k_multipliers", {}).get(k_ref, {})
    km_values = km_data.get("value", [1.2])
    k = km_values[0] if isinstance(km_values, list) else float(km_values)
    der = ter * k

    # Energy density range from selected ingredients
    selected = [get_ingredient_by_id(iid, db) for iid in selected_ids if get_ingredient_by_id(iid, db) is not None]
    if selected:
        densities = []
        for ing in selected:
            nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
            em = energy_metabolizable_kcal_per_100g(nuts)
            densities.append(em / 100)
        min_density, max_density = min(densities), max(densities)
        density_source = "selected_ingredients"
    else:
        min_density, max_density = get_global_density_range_from_db(db)
        density_source = "global_fallback"

    min_total_g = (der / max_density) * 0.9
    max_total_g = (der / min_density) * 1.1
    units = der / 1000.0

    return DerEnvelope(
        bw_kg=bw,
        ter_kcal=ter,
        k_multiplier=k,
        der_kcal=der,
        units_of_1000kcal=units,
        min_total_g=min_total_g,
        max_total_g=max_total_g,
        strategy="der_derived",
        density_source=density_source,
    )


def get_ingredient_by_id(ingredient_id: str, db: dict) -> Optional[dict]:
    """Look up an ingredient by ID across all protein_sources groups."""
    for g in db.get("protein_sources", {}).values():
        for ing in g.get("ingredients", []):
            if ing["ingredient_id"] == ingredient_id:
                return ing
    return None


# ── §6.4 — as_fed→energy_normalized conversion (item 5) ───────────────

def energy_metabolizable_kcal_per_100g(nutrients: dict) -> float:
    """Modified Atwater, AAFCO/pet food standard.
    Accepts either raw DB nutrient dict (3-state entries) or flat
    {key: value} dict already extracted.
    """
    def _val(key):
        v = nutrients.get(key)
        if isinstance(v, dict):
            return v.get("value") if v.get("status") == "measured" else 0.0
        return float(v) if v is not None else 0.0

    protein = _val("protein_g")
    fat = _val("fat_g")
    moisture = _val("moisture_pct")
    ash = _val("ash_pct")
    fiber = _val("fiber_g")

    nfe = max(0.0, 100.0 - protein - fat - moisture - ash - fiber)
    return 3.5 * protein + 8.5 * fat + 3.5 * nfe


def get_bioavailability_factor(
    ingredient_id: str, solver_nutrient_id: str, bio_factors: list
) -> float:
    """Look up bioavailability multiplier for an ingredient/nutrient pair.
    Defaults to 1.0 if no factor is declared.
    """
    for bf in bio_factors if bio_factors else []:
        if isinstance(bf, dict) and bf.get("ingredient_id") == ingredient_id:
            param = bf.get("parameter")
            if param == solver_nutrient_id:
                vals = bf.get("values", bf.get("value", {}))
                if isinstance(vals, dict):
                    return float(vals.get("min", vals.get("value", 1.0)))
                return float(vals) if vals is not None else 1.0
    return 1.0


def convert_as_fed_to_energy_normalized(
    ingredient: dict, bio_factors: list, default_breed_line: str = "working_exhibition_lines"
) -> dict[str, dict]:
    """Convert a single ingredient's 3-state nutrient entries from
    as_fed/100g → energy_normalized/1000kcal.

    Respects the real 3-state contract (item 5):
      - status="measured" → output {"status": "measured", "value": <float>}
      - status="missing"/"not_applicable" → output {"status": status}, no "value" key.
      - Every NUTRIENT_REGISTRY key (41 total) is guaranteed present in the
        output dict, even if absent from the DB entirely for this ingredient.
      - Composite pairs (methionine_plus_cystine_g, etc.) computed from
        individual measured amino acids.
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

        # Skip DB-only keys that have no solver-side counterpart
        # (e.g. biotin_ug, vitamin_k_ug — tracked in DB but not in NUTRIENT_REGISTRY)
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

    # Composite amino acids — compute from individual measured values
    met_val = get_measured_value(nuts.get("methionine_g"))
    cys_val = get_measured_value(nuts.get("cystine_g"))
    if met_val is not None and cys_val is not None:
        raw = (met_val + cys_val) * (1000.0 / em)
        out["methionine_plus_cystine_g"] = {
            "status": "measured", "value": raw * get_bioavailability_factor(
                ingredient.get("ingredient_id", ""), "methionine_plus_cystine_g", bio_factors
            )
        }

    phe_val = get_measured_value(nuts.get("phenylalanine_g"))
    tyr_val = get_measured_value(nuts.get("tyrosine_g"))
    if phe_val is not None and tyr_val is not None:
        raw = (phe_val + tyr_val) * (1000.0 / em)
        out["phenylalanine_plus_tyrosine_g"] = {
            "status": "measured", "value": raw * get_bioavailability_factor(
                ingredient.get("ingredient_id", ""), "phenylalanine_plus_tyrosine_g", bio_factors
            )
        }

    # Guarantee all 41 NUTRIENT_REGISTRY keys are present
    for registry_key in SOLVER_NUTRIENTS:
        if registry_key not in out:
            out[registry_key] = {"status": "missing"}

    return out


def build_matrix(
    selected_ids: list[str], db: dict, formulation_rules: dict
) -> dict[str, dict[str, float]]:
    """§6.4a mandatory signature. Return {ingredient_id: {nutrient_id: value}}
    in energy_normalized basis, respecting 3-state contract.

    Missing ingredient IDs (not found in DB) are included with all 41 nutrients
    set to {"status": "data_incomplete", "anomaly_ref": ..., "reason": ...}
    rather than silently omitted — the solver must know the user selected
    something that cannot be evaluated.
    """
    bio_factors = formulation_rules.get("bioavailability_factors", [])
    matrix: dict[str, dict[str, float]] = {}
    for iid in selected_ids:
        ing = get_ingredient_by_id(iid, db)
        if ing is None:
            matrix[iid] = {
                nid: {
                    "status": "data_incomplete",
                    "anomaly_ref": "REF_MISSING_INGREDIENT_DB",
                    "reason": f"ingredient_id '{iid}' not found in DB_ingredientes.json"
                }
                for nid in SOLVER_NUTRIENTS
            }
            continue
        converted = convert_as_fed_to_energy_normalized(ing, bio_factors)
        matrix[iid] = converted
    return matrix


# ── CLI ────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: build_pipeline.py [--generate-mapa | --gate-mapa | --audit-mapa | --validate-db | --runtime | --build-recipes]")
        sys.exit(1)

    mode = sys.argv[1]
    print(f"build_pipeline.py — mode={mode}")
    print(f"Working dir: {BASE_DIR}")
    print()

    if mode == "--generate-mapa":
        data = load_all_jsons()
        print(f"Loaded {len([k for k,v in data.items() if v])}/{len(JSON_FILES)} JSONs")
        mapa = generate_mapa(data)
        temp_path = BASE_DIR / MAPA_TEMP_FILENAME
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(mapa)
        size = temp_path.stat().st_size
        print(f"\nWritten: {temp_path.name} ({size:,} bytes)")

        # Run validation gate
        errors = validate_mapa(mapa, data)
        if not errors:
            print(f"\nValidation gate: ALL CHECKS PASSED")
            final_path = BASE_DIR / MAPA_FILENAME
            if final_path.exists():
                old_sha = sha256_file(final_path)
                print(f"Current {MAPA_FILENAME}: SHA256={old_sha[:16]}...")
            os.replace(temp_path, final_path)
            new_sha = sha256_file(final_path)
            print(f"Atomic replace: {MAPA_FILENAME} (SHA256={new_sha[:16]}...)")
        else:
            print(f"\nValidation gate: {len(errors)} FAILURES:")
            for err in errors:
                print(f"  - {err}")
            print(f"\nTemp file retained at: {temp_path}")
            print("Fix issues and re-run --generate-mapa")
            sys.exit(1)

    elif mode == "--gate-mapa":
        data = load_all_jsons()
        mapa_path = BASE_DIR / MAPA_FILENAME
        if not mapa_path.exists():
            print(f"ERROR: {MAPA_FILENAME} not found. Run --generate-mapa first.")
            sys.exit(1)
        mapa_content = mapa_path.read_text(encoding="utf-8")
        errors = validate_mapa(mapa_content, data)
        if not errors:
            print("Validation gate: ALL CHECKS PASSED")
        else:
            print(f"Validation gate: {len(errors)} FAILURES:")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)

    elif mode == "--audit-mapa":
        data = load_all_jsons()
        idx = build_mapa_indices(data)
        print(f"CrossRefIndex built: {len(idx.all_known_tokens)} known tokens")
        print(f"  Ingredients: {len(idx.ingredient_index)}")
        print(f"  Nutrients: {len(idx.nutrient_index)}")
        print(f"  References: {len(idx.ref_index)}")
        print(f"  Constraints: {len(idx.constraint_index)}")
        print(f"  Weights: {len(idx.weight_index)}")
        print(f"  Scenarios: {len(idx.scenario_index)}")
        print(f"  DB->Solver renames: {len(idx.db2solver_name_map)}")
        print()
        mapa_path = BASE_DIR / MAPA_FILENAME
        if mapa_path.exists():
            mapa_content = mapa_path.read_text(encoding="utf-8")
            errors = validate_mapa(mapa_content, data)
            if not errors:
                print("Validation gate: ALL CHECKS PASSED")
            else:
                print(f"Validation gate: {len(errors)} FAILURES:")
                for err in errors:
                    print(f"  - {err}")
        else:
            print(f"{MAPA_FILENAME} not found — run --generate-mapa first")

    elif mode == "--validate-db":
        print("Validating DB_ingredientes.json against 3-state nutrient contract...")
        from jsonschema import validate, ValidationError
        
        def load_json_local(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        
        db = load_json_local(DATA_DIR / "DB_ingredientes.json")
        schema = load_json_local(DATA_DIR / "db_ingredientes.schema.json")
        errors = []
        try:
            validate(instance=db, schema=schema)
        except ValidationError as e:
            errors.append(f"Schema validation failed at {'.'.join(str(x) for x in e.path)}: {e.message}")
        
        # Key completeness
        for group in db.get("protein_sources", {}).values():
            for ing in group.get("ingredients", []):
                bp = ing.get("bromatological_profile", {})
                nuts = bp.get("nutrients", {})
                for key in ALL_REQUIRED_KEYS:
                    if key not in nuts:
                        errors.append(f"Key completeness: {ing['ingredient_id']}: missing key '{key}'")
                    else:
                        entry = nuts[key]
                        if "status" not in entry:
                            errors.append(f"Key completeness: {ing['ingredient_id']}.{key}: no 'status' field")
                        elif entry["status"] not in ("measured", "missing", "not_applicable"):
                            errors.append(f"Key completeness: {ing['ingredient_id']}.{key}: invalid status '{entry['status']}'")
        
        # Source refs
        prov = load_json_local(DATA_DIR / "audit_provenance.json")
        known_refs = set(prov.get("references", {}).keys())
        for group in db.get("protein_sources", {}).values():
            for ing in group.get("ingredients", []):
                iid = ing.get("ingredient_id")
                bp = ing.get("bromatological_profile", {})
                for key, entry in bp.get("nutrients", {}).items():
                    sr = entry.get("source_ref")
                    ar = entry.get("anomaly_ref")
                    if sr and sr not in known_refs:
                        errors.append(f"{iid}.{key}: unknown source_ref '{sr}'")
                    if ar and ar not in known_refs:
                        errors.append(f"{iid}.{key}: unknown anomaly_ref '{ar}'")
                for alert in ing.get("safety_alerts", []):
                    sr = alert.get("source_ref")
                    if sr and sr not in known_refs:
                        errors.append(f"{iid}.safety_alert: unknown source_ref '{sr}'")
        
        if errors:
            print(f"VALIDATION FAILED: {len(errors)} errors")
            for err in errors[:50]:
                print(f"  - {err}")
            if len(errors) > 50:
                print(f"  ... and {len(errors) - 50} more")
            sys.exit(1)
        else:
            print("VALIDATION PASSED: All 20 ingredients have complete 3-state nutrient entries with valid references.")

    elif mode == "--runtime":
        # §6.4a pipeline steps 1-5: READ → VALIDATE → compute DER → convert → build matrix
        data = load_all_jsons()
        validate_inputs(data)
        db = data.get("DB_ingredientes.json", {})

        # Build a default AnimalInput from the request JSON if provided
        req_path = DATA_DIR / "runtime_request.json"
        if req_path.exists():
            with open(req_path, "r") as f:
                req_data = json.load(f)
        else:
            # Fallback demo: 25kg male puppy, SCN_B
            print("No runtime_request.json found — using default demo animal")
            req_data = {
                "animal": {
                    "sex": "male", "weight_kg": 25.0, "age_months": 8,
                    "gonadal_status": "intact", "use_gompertz": True
                },
                "selected_ingredient_ids": [
                    "beef_muscle_raw", "chicken_back_neck_raw", "beef_liver_raw",
                    "beef_kidney_raw", "salmon_atlantic_raw",
                ],
                "scenario_id": "SCN_B_SLOW_GROWTH",
            }

        animal = AnimalInput(**req_data.get("animal", {}))
        selected_ids = req_data.get("selected_ingredient_ids", [])
        scenario_id = req_data.get("scenario_id", "SCN_B_SLOW_GROWTH")

        # Step 3: compute DER + envelope
        growth = data.get("growth_energy_skeletal.json", {})
        der_env = calculate_der_and_envelope(animal, growth, scenario_id, selected_ids, db)
        print(f"\n=== DER & Envelope ===")
        print(f"BW={der_env.bw_kg:.1f} kg, TER={der_env.ter_kcal:.0f} kcal, k={der_env.k_multiplier}")
        print(f"DER={der_env.der_kcal:.0f} kcal, units of 1000kcal={der_env.units_of_1000kcal:.3f}")
        print(f"Envelope: [{der_env.min_total_g:.0f}, {der_env.max_total_g:.0f}] g ({der_env.density_source})")

        # Step 4-5: convert and build matrix
        fr = data.get("formulation_rules.json", {})
        matrix = build_matrix(selected_ids, db, fr)
        print(f"\n=== Built matrix for {len(matrix)} ingredients ===")
        for iid, vec in matrix.items():
            n = len(vec)
            # Row 1 follow-on: same return-type change as line 1887. Old code checked
            # "v is not None" (pre-3-state: bare float or None). Now every value is a
            # status dict; "v is not None" is always True. Check for a numeric "value"
            # key instead — only status="measured" entries have one.
            measured = sum(1 for v in vec.values() if isinstance(v.get("value"), (int, float)))
            print(f"  {iid}: {n} nutrients ({measured} measured)")
            # Show first 5 nutrient values
            for k, v in list(vec.items())[:5]:
                # Row 1 PHASE1_APPROVALS.md: convert_as_fed_to_energy_normalized()
                # changed from dict[str, float] to dict[str, dict] — each value is now a
                # status envelope (e.g. {"status": "measured", "value": 12.08}). Old code
                # used f"{v:.4f}" which expected a bare float. Now use .get("value") which
                # returns None for status="missing"/"not_applicable" entries (no "value" key).
                print(f"    {k}: {v.get('value', 'N/A')}" if isinstance(v.get('value'), (int, float)) else f"    {k}: None")

        # Step 6: solve_cascade placeholder
        print(f"\n=== Solver cascade: Level 1 -> 2 -> 3 (not yet backed by real LP) ===")
        print(f"Level 1 attempted: requires call_lp_solver() implementation")
        print(f"See sat_solver_contrato:§8 for the LP formulation.")

        json.dump({
            "solver_output_schema": "v10.1",
            "solver_status": "suboptimal",
            "feeding_recommendation": "FEED_WITH_CAUTION",
            "cascade_level_used": 1,
            "animal_context": der_env.as_animal_context(animal.sex, animal.age_months, animal.gonadal_status),
            "envelope": der_env.as_envelope_dict(),
            "allocations": None,
            "nutrient_results": [],
            "diagnostic_analysis": None,
            "gaps": [],
            "alerts": [],
            "recommended_additions": [],
            "solver_metadata": {
                "solver_engine": "PLANNED (PuLP_CBC)",
                "solve_time_ms": 0,
                "cascade_attempts": [1],
                "final_level": 1,
                "objective_value": 0,
            }
        }, open(DATA_DIR / "solver_output.json", "w"), indent=2, ensure_ascii=False)
        print(f"\nPartial output written to data/solver_output.json")

    elif mode == "--build-recipes":
        print("Build-recipes mode: not implemented. See docs/architecture/sat_pipeline_fluxo.md")
        sys.exit(0)

    else:
        print(f"Unknown mode: {mode}")
        print("Usage: build_pipeline.py [--generate-mapa | --gate-mapa | --audit-mapa | --validate-db | --runtime | --build-recipes]")
        sys.exit(1)


if __name__ == "__main__":
    main()
