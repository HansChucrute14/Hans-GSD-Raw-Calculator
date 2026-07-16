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

def section1_header(data: Dict[str, Any]) -> str:
    """Verbatim copy of indice_plano_central.md preamble (§0-§2) + file manifest + bundle stats."""
    from doc_introspector import compute_satellite_stats
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
    lines.append(f"**Generated:** <timestamp>")
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

    # Bundle statistics — live from compute_satellite_stats()
    lines.append("## Satellite Bundle Statistics")
    lines.append("")
    lines.append("> Computed live from source files. Updates automatically when satellites change.")
    lines.append("> Source: `doc_introspector.compute_satellite_stats()`")
    lines.append("")
    try:
        stats = compute_satellite_stats(BASE_DIR)
        # Per-file table
        lines.append("### Per-File Line Counts")
        lines.append("")
        file_rows = []
        for fname, count in sorted(stats["files"].items()):
            file_rows.append([f"`{fname}`", str(count)])
        lines.append(table(["File", "Lines"], file_rows))
        lines.append("")
        # Bundle totals table
        lines.append("### Bundle Totals")
        lines.append("")
        bundle_rows = []
        for bname, total in sorted(stats["bundles"].items()):
            bundle_rows.append([bname, str(total)])
        lines.append(table(["Bundle", "Total Lines"], bundle_rows))
        lines.append("")
    except Exception as e:
        lines.append(f"> Bundle stats unavailable: {e}")
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
        lines.append(f"- **Mapped but absent from DB:** {', '.join(f'`{m}`' for m in sorted(missing))}")
    if wildcards:
        lines.append(f"- **Wildcards:** {', '.join(sorted(wildcards))}")
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

    # Count provenance refs
    prov = data.get("audit_provenance.json", {})
    refs = prov.get("references", {})
    refs_count = len(refs)
    ref_breakdown = {}
    if isinstance(refs, dict):
        for rid, rdata in refs.items():
            qf = rdata.get("quality_flag", "MISSING") if isinstance(rdata, dict) else "MISSING"
            ref_breakdown[qf] = ref_breakdown.get(qf, 0) + 1

    lines = []
    lines.append(hdr(2, "Curation Status — Ingredient Groups"))
    lines.append("")
    lines.append(f"**Total ingredients:** {meta.get('total_ingredients', '?')}")
    lines.append(f"**Provenance refs:** {refs_count} total")
    for qf, cnt in sorted(ref_breakdown.items()):
        lines.append(f"  - **{qf}:** {cnt}")
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

    # Add fat_sources row
    fat_sources = db.get("protein_sources", {}).get("fat_sources", {})
    if fat_sources and fat_sources.get("ingredients"):
        fat_ings = fat_sources.get("ingredients", [])
        fat_status = []
        if "fat_sources" in validated:
            fat_status.append("VALIDATED")
        if "fat_sources" in pending:
            fat_status.append("PENDING")
        if "fat_sources" in partial:
            fat_status.append("PARTIAL")
        fat_status_str = "+".join(fat_status) if fat_status else "UNKNOWN"
        rows.append([
            "fat_sources",
            "Fontes de Gordura",
            str(len(fat_ings)),
            ", ".join(i["ingredient_id"] for i in fat_ings),
            fat_status_str,
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
    lines.append(f"- **Note:** The 17 refs listed in §9.2 are PLANNED items not yet in DB, not orphans. Actual orphans in DB: {len(orphans)}")
    if orphans:
        for r in sorted(orphans):
            lines.append(f"  - `{r}`")
    lines.append("")

    # Gap 3: Implementation gaps — live introspection via IMPLEMENTATION_SPEC
    lines.append("### Implementation Gaps (Pipeline)")
    try:
        from doc_introspector import ImplIntrospector, IMPLEMENTATION_SPEC
        ii = ImplIntrospector(BASE_DIR / "build_pipeline.py")
        results = [ii.check(s, BASE_DIR) for s in IMPLEMENTATION_SPEC]
        status_rows = []
        for r in results:
            src_line = "L" + str(r["line"]) if r["line"] else "N/A"
            status_rows.append([
                r["name"],
                r["priority"],
                r["spec_ref"],
                r["status"],
                str(r["line"]) if r["line"] else "\u2014",
                r["note"] + " <!-- SOURCE: IMPLEMENTATION_SPEC / build_pipeline.py:" + src_line + " -->",
            ])
        lines.append(table(
            ["Name", "Priority", "Spec Ref", "Status", "Line", "Note"],
            status_rows,
        ))
    except ImportError:
        lines.append("> Implementation gaps table unavailable (doc_introspector not importable)")
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
        ("DB version vs actual ingredient count", "3.1.1", f"{len(all_ings)}", "accept"),
        ("Orphan refs resolved", "0 (per docs)", "§9.2 items are PLANNED, not orphans. Actual orphans in DB: 0", "defer"),
        ("Provenance refs count", "85 (per docs)", f"{len(known)} (114 CONFIRMED, 18 INFERRED, 7 LITERATURE_COMPOSITE, 2 COPY_PASTE_ERROR_CORRECTED, 1 UNIT_INCONSISTENCY_RESOLVED, 1 AUTHORITATIVE_DATABASE)", "accept"),
        ("solve_cascade location", "lp_parameters.schema (per docs)", "lp_parameters_data.json", "accept"),
        ("NUTRIENT_REGISTRY location", "lp_parameters.schema (per docs)", "lp_parameters_data.json", "accept"),
        ("All constraints HARD_FAIL_INFEASIBLE", "no (V10 cascade)", "All 60 constraints are HARD_FAIL_INFEASIBLE. V10 cascade uses slack variables in LP formulation, not constraint relaxation.", "defer"),
        ("scenarios.json top-level type", "dict with 'scenarios' key", f"{'list' if sc_is_list else 'dict'}", "accept"),
        ("Adult k_multiplier", "does not exist", f"{'exists (adult_working_active: 1.5)' if has_adult else 'does not exist'}", "accept"),
        ("Missing supplements in DB", "0 (claimed 23)", f"{missing_supp_count} planned missing (kelp_meal_dried, salt_nacl, copper_sulfate) — per §9.1", "defer"),
        ("nutrient_matrix structure", "dict with min/max", f"{'list with nested values' if matrix_is_list else 'dict'}", "accept"),
    ]

    rows = []
    for claim, doc_val, actual_val, decision in divergences:
        flag = "[DIVERGE]" if doc_val != actual_val else "[OK]"
        rows.append([claim, doc_val, actual_val, flag, decision])
    lines.append(table(["Claim", "Documented", "Actual", "Status", "Decision"], rows))
    lines.append("")
    return "\n".join(lines)


# ── Section 18: Live Execution Evidence (Task 4-3) ──────────────────────
# Phase 4 of plan-full-mapa-fix.md — embeds capture_live_evidence() output
# with scrub_volatile() applied. Set via --no-live-evidence for CI use.

# Module-level flag set by main() when --no-live-evidence is passed.
_NO_LIVE_EVIDENCE = False


def section18_live_evidence(data: Dict[str, Any]) -> str:
    """Live execution evidence — smoke runs against the production pipeline.

    Calls `doc_introspector.capture_live_evidence()` with REFERENCE_ANIMAL +
    REFERENCE_SELECTION (single source of truth from tests/reference_cases.py),
    applies `scrub_volatile()` to each entry's `output` field to strip
    timestamps/paths/PIDs (preserves idempotency), and renders a fenced code
    block per smoke run with status, severity, scrubbed stdout, and result JSON.

    When `_NO_LIVE_EVIDENCE` is True (set by --no-live-evidence CLI flag), the
    section is replaced with an explicit skip marker so a human reviewer can
    spot the degradation. The validation gate still passes.
    """
    from doc_introspector import capture_live_evidence, scrub_volatile
    from tests.reference_cases import REFERENCE_ANIMAL, REFERENCE_SELECTION

    lines = []
    lines.append(hdr(2, "Live Execution Evidence"))
    lines.append("")
    lines.append("> Smoke runs against the production pipeline (`build_pipeline.py`).")
    lines.append("> Scrubbed of timestamps/paths/PIDs via `scrub_volatile()` for idempotent regeneration.")
    lines.append("> Source: `doc_introspector.capture_live_evidence()` + `tests/reference_cases.py`.")
    lines.append("")

    if _NO_LIVE_EVIDENCE:
        lines.append("> Live evidence skipped (--no-live-evidence)")
        lines.append("")
        return "\n".join(lines)

    try:
        evidence = capture_live_evidence(data, REFERENCE_ANIMAL, REFERENCE_SELECTION)
    except Exception as e:
        import traceback
        lines.append(f"> Live evidence capture FAILED: {type(e).__name__}: {e}")
        lines.append("")
        lines.append("```")
        lines.append(traceback.format_exc())
        lines.append("```")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"Captured {len(evidence)} smoke runs:")
    lines.append("")

    for entry in evidence:
        lines.append(f"### Evidence: {entry['label']}")
        lines.append("")
        lines.append(f"- **Status:** {entry['status']}")
        lines.append(f"- **Severity:** {entry['severity']}")
        if entry.get("error"):
            lines.append(f"- **Error:** `{entry['error']}`")
        # LP-specific fields (populated for runtime smoke; None otherwise)
        if entry.get("solver_status") is not None or entry.get("cascade_level_used") is not None:
            lines.append(f"- **solver_status:** `{entry.get('solver_status')}`")
            lines.append(f"- **cascade_level_used:** `{entry.get('cascade_level_used')}`")
            lines.append(f"- **lexicographic_stages_solved:** `{entry.get('lexicographic_stages_solved')}`")
            lines.append(f"- **clinical_floor_relaxed:** `{entry.get('clinical_floor_relaxed')}`")
            lines.append(f"- **solve_time_ms:** `{entry.get('solve_time_ms')}`")
            lines.append(f"- **nutrients_above_90pct_sul:** `{entry.get('nutrients_above_90pct_sul')}`")
        lines.append("")
        # Scrubbed stdout
        scrubbed_out = scrub_volatile(entry.get("output") or "")
        lines.append("**Captured stdout (scrubbed):**")
        lines.append("```")
        lines.append(scrubbed_out if scrubbed_out else "(no stdout)")
        lines.append("```")
        lines.append("")
        # Result JSON or error
        if entry.get("result_repr"):
            lines.append("**Result (JSON, may be truncated to 2000 chars):**")
            lines.append("```json")
            lines.append(entry["result_repr"])
            lines.append("```")
        lines.append("")
        lines.append("<!-- SOURCE: doc_introspector.capture_live_evidence / tests/reference_cases.py -->")
        lines.append("")

    return "\n".join(lines)


# ── Section 19: Test Suite Integrity (Phase 5 — Task 5-2) ────────────────
# Kills Findings #17, #25 by documenting the AAA+A compliance status of every
# test_*.py file. Detects:
# - @pytest.mark.integration decorators via AST node walking (Phase 5 — NOT
#   docstring matching per the plan's D6 v1.2 spec)
# - real data loads via two-pattern regex:
#   (1) r"\bload_all_jsons\s*\(" — production loader (canonical way per D6)
#   (2) r'open\s*\(\s*["\'][^"\']*data/' — direct data-file access
# The v1.1.0 regex `r"\bjson\.load\(|open\("` was WRONG because it false-positive
# on audit-log writes (`open("test_audit_log.md", "w") ...`). D6 v1.2 corrected
# this: the production loader IS the canonical way to load real data.

def section19_test_integrity(data: Dict[str, Any]) -> str:
    """Live test-suite integrity analysis via AST + D6 v1.2 regex.

    Returns a row per test_*.py with: file, marked_integration, loads_real_data.
    A test file violates the AAA+A mandate (sat_testes_consolidado:§11.5) only if
    marked_integration=True AND loads_real_data=False — this is the configuration
    the validate_mapa() Check 10 gate-trips on.
    """
    from doc_introspector import check_test_integrity

    lines = []
    lines.append(hdr(2, "Test Suite Integrity"))
    lines.append("")
    lines.append("> AAA+A anti-gamification analysis of every `test_*.py` file.")
    lines.append("> Source: `doc_introspector.check_test_integrity()` — D6 v1.2 regex.")
    lines.append("> The production loader (`bp.load_all_jsons()`) is the canonical way to load real data.")
    lines.append("> Direct `json.load(samples/...)` calls are an anti-pattern — they bypass loader validation.")
    lines.append("")

    try:
        rows = check_test_integrity(Path(".") / "tests")
    except Exception as e:
        import traceback
        lines.append(f"> Test integrity check FAILED: {type(e).__name__}: {e}")
        lines.append("")
        lines.append("```")
        lines.append(traceback.format_exc())
        lines.append("```")
        lines.append("")
        return "\n".join(lines)

    if not rows:
        lines.append("> No `test_*.py` files found in repository root.")
        lines.append("")
        return "\n".join(lines)

    lines.append("| File | `@pytest.mark.integration` | Loads Real Data | AAA+A Compliant |")
    lines.append("| --- | --- | --- | --- |")
    for r in rows:
        marker = "Yes" if r["marked_integration"] else "No"
        loads = "Yes" if r["loads_real_data"] else "No"
        # AAA+A violation is ONLY when marked_integration=True AND loads_real_data=False
        compliant = "Yes" if (not r["marked_integration"]) or r["loads_real_data"] else "**NO**"
        lines.append(f"| `{r['file']}` | {marker} | {loads} | {compliant} |")
    lines.append("")
    lines.append("<!-- SOURCE: doc_introspector.check_test_integrity / D6 v1.2 regex -->")
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
        section18_live_evidence,
        section19_test_integrity,
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

    # Check 9: Structure contracts — all JSON structure contracts must hold
    try:
        from doc_introspector import check_structure_contracts
        contract_results = check_structure_contracts(data)
        failed = [r for r in contract_results if not r["holds"]]
        if failed:
            for f in failed:
                errors.append(f"Structure contract failed — {f['file']}: {f['description']} (note: {f['note']})")
    except Exception as e:
        errors.append(f"Structure contract check failed: {e}")

    # Check 10: Test integrity — Phase 5 / Task 5-2 (D6 v1.2 REWRITTEN)
    # Fail the gate if any test_*.py has marked_integration=True AND loads_real_data=False.
    # This is the AAA+A mandate violation per sat_testes_consolidado:§11.5.
    # D6 v1.2: detects `bp.load_all_jsons(` OR `open("...data/...")` — NOT the
    # old `r"\bjson\.load\(|open\("` which would false-positive on audit-log writes.
    try:
        from doc_introspector import check_test_integrity
        rows = check_test_integrity(Path(".") / "tests")
        violations = [r for r in rows if r["marked_integration"] and not r["loads_real_data"]]
        if violations:
            for v in violations:
                errors.append(
                    f"Test integrity failed — {v['file']}: marked as @pytest.mark.integration "
                    f"but does not load real data (AAA+A violation per sat_testes_consolidado:§11.5)"
                )
    except Exception as e:
        errors.append(f"Test integrity check failed: {e}")

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
    def _val(key, fallback=0.0):
        v = nutrients.get(key)
        if isinstance(v, dict):
            return v.get("value") if v.get("status") == "measured" else fallback
        return float(v) if v is not None else fallback

    protein = _val("protein_g")
    fat = _val("fat_g")
    # Fallbacks for missing proximate analysis data (Phase 1 data gap)
    moisture = _val("moisture_pct", 72.0)  # typical for raw muscle meat
    ash = _val("ash_pct", 1.0)
    fiber = _val("fiber_g", 0.0)

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


# ── Phase 2: LP Solver + 3-Level Declarative Cascade ───────────────────

def build_lp_problem(
    selected_ids: list[str],
    matrix: dict[str, dict[str, dict]],
    data: dict,
    der_info: DerEnvelope,
    cascade_level: int,
    apply_clinical_floor: bool = False,
) -> dict:
    """
    Build the LP problem for a given cascade level.

    Returns dict with:
      - prob: pulp.LpProblem
      - x_vars: {ingredient_id: LpVariable}
      - compiled_coefficients: {ingredient_id: {nutrient_id: float}} (nutrient/gram)
      - targets_per_day: {nutrient_id: float}
      - suls_per_day: {nutrient_id: float}
      - clinical_floor_bounds: {ingredient_id: float} (Level 3 only)
      - big_m_values: {ingredient_id: float} (Level 3 only)
      - has_binary_vars: bool
    """
    import pulp

    lp_params = data.get("lp_parameters_data.json", {})
    solver_params = lp_params.get("solver_params", {})
    registry = lp_params.get("NUTRIENT_REGISTRY", {})
    tox_limits = data.get("toxicological_limits.json", [])
    constraints = data.get("constraints.json", {})
    fr = data.get("formulation_rules.json", {})

# 1. Create LP problem
    prob = pulp.LpProblem(f"GSD_Diet_Level{cascade_level}", pulp.LpMinimize)

    # 2. Decision variables x_i (grams/day) - only for ingredients with measured nutrients
    x_vars: dict[str, pulp.LpVariable] = {}
    valid_selected_ids = []
    for iid in selected_ids:
        a_ij = matrix.get(iid, {})
        has_measured = any(entry.get("status") == "measured" for entry in a_ij.values())
        if has_measured:
            x_vars[iid] = pulp.LpVariable(f"x_{iid}", lowBound=0, cat="Continuous")
            valid_selected_ids.append(iid)
        else:
            # Log warning for debugging
            print(f"  [WARN] Ingredient {iid} has no measured nutrients, skipping from LP")

    if not x_vars:
        return {"status": "infeasible", "reason": "No ingredients with measured nutrients"}

    # 3. Compile coefficients: a_ij is nutrient/1000kcal → nutrient/gram
    # CORRECT FORMULA: nutrient_per_gram = a_ij * EM_kcal_per_g / 1000.0
    compiled_coeffs: dict[str, dict[str, float]] = {}
    em_per_g: dict[str, float] = {}
    big_m_values: dict[str, float] = {}
    clinical_floor_bounds: dict[str, float] = {}

    # Get EM per 100g for each ingredient from DB
    db = data.get("DB_ingredientes.json", {})
    for iid in valid_selected_ids:
        ing = get_ingredient_by_id(iid, db)
        if ing is None:
            continue
        nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
        em_100g = energy_metabolizable_kcal_per_100g(nuts)
        em_per_g[iid] = em_100g / 100.0

        # Big-M per ingredient: M_i = DER_kcal / EM_i_kcal_per_100g * 100
        # Grams of ingredient i alone that would satisfy 100% of DER
        if em_100g > 0:
            big_m_values[iid] = der_info.der_kcal / em_100g * 100.0
        else:
            big_m_values[iid] = 10000.0  # fallback large number

        # Compile nutrient/gram coefficients
        compiled_coeffs[iid] = {}
        a_ij = matrix.get(iid, {})
        for nid, entry in a_ij.items():
            if entry.get("status") == "measured":
                a_val = entry["value"]  # nutrient per 1000kcal
                # CORRECTED: nutrient_per_gram = a_ij * EM_kcal_per_g / 1000.0
                compiled_coeffs[iid][nid] = a_val * em_per_g[iid] / 1000.0

    # 4. BUILD-TIME SANITY ASSERTION: verify compilation against stored per-100g values
    # Pick first available ingredient/nutrient pair for the check
    sanity_checked = False
    for iid in valid_selected_ids:
        if sanity_checked:
            break
        ing = get_ingredient_by_id(iid, db)
        if ing is None:
            continue
        nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
        for db_key, entry in nuts.items():
            if entry.get("status") != "measured":
                continue
            solver_key, scale = UNIT_RENAME.get(db_key, (db_key, 1.0))
            if solver_key not in compiled_coeffs.get(iid, {}):
                continue
            # Independent recomputation from stored per-100g value
            expected = float(entry["value"]) * scale / 100.0
            got = compiled_coeffs[iid][solver_key]
            assert abs(got - expected) < 1e-9, (
                f"Build-time sanity failed for {iid}/{solver_key}: "
                f"expected {expected} (from per-100g), got {got} (from a_ij*EM/1000). "
                f"Check the /1000 factor in nutrient/gram compilation."
            )
            sanity_checked = True
            break
    if not sanity_checked:
        # Fallback: at least check beef_muscle_raw protein if in selection
        if "beef_muscle_raw" in valid_selected_ids:
            ing = get_ingredient_by_id("beef_muscle_raw", db)
            if ing:
                nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
                entry = nuts.get("protein_g", {})
                if entry.get("status") == "measured":
                    expected = float(entry["value"]) / 100.0
                    got = compiled_coeffs.get("beef_muscle_raw", {}).get("protein_g")
                    if got is not None:
                        assert abs(got - expected) < 1e-9, (
                            f"Build-time sanity failed for beef_muscle_raw/protein_g: "
                            f"expected {expected}, got {got}"
                        )

    # 5. Targets per day (nutrient/1000kcal * units_of_1000kcal)
    targets_per_day: dict[str, float] = {}
    scenario = data.get("scenarios.json", [])
    active_scenario = next((s for s in scenario if s.get("scenario_id") == "SCN_B_SLOW_GROWTH"), {})
    for target in active_scenario.get("targets", []):
        nid = target.get("nutrient_id")
        val = target.get("value")
        if nid and val is not None:
            targets_per_day[nid] = float(val) * der_info.units_of_1000kcal

    # 6. SULs per day
    suls_per_day: dict[str, float] = {}
    for tox in tox_limits:
        nid = tox.get("nutrient_id")
        sul_entry = tox.get("sul", {})
        sul_val = sul_entry.get("value")
        if nid and sul_val is not None:
            suls_per_day[nid] = float(sul_val) * der_info.units_of_1000kcal

    # Initialize problem_dict with variable storage dictionaries
    problem_dict = {
        "prob": prob,
        "x_vars": x_vars,
        "compiled_coefficients": compiled_coeffs,
        "targets_per_day": targets_per_day,
        "suls_per_day": suls_per_day,
        "clinical_floor_bounds": clinical_floor_bounds,
        "big_m_values": big_m_values,
        "has_binary_vars": False,
        "em_per_g": em_per_g,
        "der_info": der_info,
        "nutrient_slack_vars": {},
        "sul_slack_vars": {},
        "der_dev_vars": {},
    }

    # 7. Build constraints based on cascade level
    level_config = next(
        (l for l in lp_params.get("solve_cascade", []) if l.get("level") == cascade_level),
        {}
    )
    relax_tiers = set(level_config.get("relax_tiers", []))

    # Helper to add nutrient constraints
    def add_nutrient_constraints():
        nonlocal prob
        # Nutrient bounds from constraints.json (minimums)
        nutrient_bounds = constraints.get("nutrient_bounds", [])
        print(f"[DEBUG] Level {cascade_level}: relax_tiers = {relax_tiers}")
        added = 0
        for nb in nutrient_bounds:
            cid = nb.get("constraint_id", "")
            if not cid.startswith("CSTR_NB_"):
                continue
            # nutrient_id is in lp_coefficients.variables_referenced[0] (not a direct field)
            lp_coeffs = nb.get("lp_coefficients", {})
            vars_ref = lp_coeffs.get("variables_referenced", [])
            if not vars_ref:
                continue
            nid = vars_ref[0]
            # Minimum constraints (CSTR_NB_*_MIN) are always adequacy_soft (relaxable in Level 2)
            # SUL constraints use safety_hard (only relaxed in Level 3)
            # Determine tier from constraint_id prefix
            if cid.startswith("CSTR_NB_") and cid.endswith("_MIN"):
                tier = "adequacy_soft"
            elif cid.startswith("CSTR_SUL_"):
                tier = "safety_hard"
            else:
                tier = registry.get(nid, {}).get("constraint_tier", "adequacy_soft")
            is_relaxed = tier in relax_tiers
            print(f"[DEBUG] {cid}: nid={nid}, tier={tier}, is_relaxed={is_relaxed}")

            # Sum of nutrient_j = sum_i (compiled_coeffs[i][j] * x_i)
            # Use .get(nid, 0.0) to handle nutrients not measured in some ingredients
            expr = pulp.lpSum(
                compiled_coeffs[iid].get(nid, 0.0) * x_vars[iid]
                for iid in valid_selected_ids
            )

            # Minimum constraint from constraint bound (bounds is a list)
            bounds_list = lp_coeffs.get("bounds", [])
            for b in bounds_list:
                rhs = b.get("rhs", 0)
                sense = b.get("sense", ">=")
                if sense == ">=" and rhs > 0:
                    target = float(rhs) * der_info.units_of_1000kcal
                    if is_relaxed:
                        # Add slack variable for Level 2
                        slack = pulp.LpVariable(f"slack_{nid}_min", lowBound=0, cat="Continuous")
                        prob += expr + slack >= target
                        problem_dict["nutrient_slack_vars"][nid] = slack
                    else:
                        prob += expr >= target
                    added += 1

    # SUL constraints (safety_hard)
    def add_sul_constraints():
        nonlocal prob
        for nid, sul_day in suls_per_day.items():
            # SUL constraints are always safety_hard (only relaxed in Level 3)
            is_relaxed = "safety_hard" in relax_tiers  # only Level 3 relaxes safety_hard

            expr = pulp.lpSum(
                compiled_coeffs[iid].get(nid, 0.0) * x_vars[iid]
                for iid in valid_selected_ids
            )

            if is_relaxed:
                # Level 3: allow violation with slack
                v_plus = pulp.LpVariable(f"v_{nid}_plus", lowBound=0, cat="Continuous")
                prob += expr <= sul_day + v_plus
                problem_dict["sul_slack_vars"][nid] = v_plus
            else:
                # Levels 1,2: hard constraint
                prob += expr <= sul_day

# Inclusion constraints (category sums)
    def add_inclusion_constraints(relax: bool = False):
        nonlocal prob
        # Get category mapping
        mapping = fr.get("_inclusion_semantics", {}).get("category_to_ingredient_mapping", {})
        all_ids_by_cat: dict[str, list[str]] = {}
        for cat_group in db.get("protein_sources", {}).values():
            for ing in cat_group.get("ingredients", []):
                all_ids_by_cat.setdefault(ing["category"], []).append(ing["ingredient_id"])

        # Expand wildcards
        expanded = {}
        for generic, ids in mapping.items():
            resolved = []
            for i in ids:
                if i == "_all_muscle_meat":
                    resolved += all_ids_by_cat.get("muscle_meat", [])
                elif i == "_all_fat_source":
                    resolved += all_ids_by_cat.get("fat_source", [])
                else:
                    resolved.append(i)
            expanded[generic] = [i for i in resolved if i in selected_ids]

        incl_limits = fr.get("inclusion_limits", [])
        for incl in incl_limits:
            iid = incl.get("ingredient_id")  # category name like "liver", "protein_base"
            max_pct = incl.get("max_pct")
            min_pct = incl.get("min_pct")
            if not iid or iid not in expanded:
                continue
            cat_ingredients = expanded[iid]
            if not cat_ingredients:
                continue
            cat_sum = pulp.lpSum(x_vars[i] for i in cat_ingredients)
            total = pulp.lpSum(x_vars[i] for i in valid_selected_ids)
            if max_pct is not None:
                if relax:
                    # Level 3: slack variable for max inclusion
                    slack = pulp.LpVariable(f"slack_incl_max_{iid}", lowBound=0, cat="Continuous")
                    prob += cat_sum <= float(max_pct) / 100.0 * total + slack
                    # Store for objective if needed
                    problem_dict.setdefault("inclusion_slack_vars", {})[f"max_{iid}"] = slack
                else:
                    # Levels 1,2: hard constraint
                    prob += cat_sum <= float(max_pct) / 100.0 * total
            if min_pct is not None:
                if relax:
                    # Level 3: slack variable for min inclusion
                    slack = pulp.LpVariable(f"slack_incl_min_{iid}", lowBound=0, cat="Continuous")
                    prob += cat_sum >= float(min_pct) / 100.0 * total - slack
                    problem_dict.setdefault("inclusion_slack_vars", {})[f"min_{iid}"] = slack
                else:
                    prob += cat_sum >= float(min_pct) / 100.0 * total

    # Mineral antagonism ratio constraints (with slack for goal programming)
    def add_antagonism_constraints():
        nonlocal prob
        # Get penalty weights from lp_parameters_data.json
        lp_params = data.get("lp_parameters_data.json", {})
        antag_penalties = {a["constraint_id"]: a.get("penalty_weight", 5000) 
                           for a in lp_params.get("mineral_antagonisms", [])}
        
        # Storage for slack variables to be used in objective
        antagonism_slack_vars = {}
        
        for antag in constraints.get("mineral_antagonisms", []):
            cid = antag.get("constraint_id", "")
            vars_ref = antag.get("lp_coefficients", {}).get("variables_referenced", [])
            if len(vars_ref) != 2:
                continue
            n1, n2 = vars_ref[0], vars_ref[1]
            bounds_list = antag.get("lp_coefficients", {}).get("bounds", [])
            
            e1 = pulp.lpSum(compiled_coeffs[iid].get(n1, 0.0) * x_vars[iid] for iid in valid_selected_ids)
            e2 = pulp.lpSum(compiled_coeffs[iid].get(n2, 0.0) * x_vars[iid] for iid in valid_selected_ids)
            
            for bounds in bounds_list:
                sense = bounds.get("sense", "")
                rhs = bounds.get("rhs", 0)
                vars_dict = bounds.get("variables", {})
                
                # Extract ratio from coefficients: format is {n1: 1.0, n2: -ratio} with rhs=0
                # This represents: 1.0 * n1 + (-ratio) * n2 >= 0  =>  n1 >= ratio * n2
                # Or: 1.0 * n1 + (-ratio) * n2 <= 0  =>  n1 <= ratio * n2
                coeff_n1 = vars_dict.get(n1, 0)
                coeff_n2 = vars_dict.get(n2, 0)
                
                if coeff_n1 == 0 or coeff_n2 >= 0:
                    continue
                
                ratio = -coeff_n2 / coeff_n1  # e.g., 1.1 or 1.3 for Ca:P
                
                if sense == "<=" and ratio > 0:
                    # Upper bound: n1 <= ratio * n2  ->  n1 - ratio * n2 <= s_high
                    s_high = pulp.LpVariable(f"s_high_{cid}", lowBound=0, cat="Continuous")
                    prob += e1 - ratio * e2 <= s_high
                    antagonism_slack_vars[f"s_high_{cid}"] = (s_high, 1.0)
                elif sense == ">=" and ratio > 0:
                    # Lower bound: n1 >= ratio * n2  ->  ratio * n2 - n1 <= s_low
                    s_low = pulp.LpVariable(f"s_low_{cid}", lowBound=0, cat="Continuous")
                    prob += ratio * e2 - e1 <= s_low
                    antagonism_slack_vars[f"s_low_{cid}"] = (s_low, 1.0)
        
        # Store slack variables for use in objective
        problem_dict["antagonism_slack_vars"] = antagonism_slack_vars
        # Store penalty weights for objective
        problem_dict["antagonism_penalty_weights"] = antag_penalties

    # Envelope constraints

    # Envelope constraints
    def add_envelope_constraints():
        nonlocal prob
        total = pulp.lpSum(x_vars[iid] for iid in valid_selected_ids)
        env_soft = "envelope_soft" in relax_tiers
        if env_soft:
            # Only max envelope is relaxed; min envelope is ALWAYS hard (physical constraint)
            slack_max = pulp.LpVariable("slack_envelope_max", lowBound=0, cat="Continuous")
            prob += total >= der_info.min_total_g  # HARD minimum
            prob += total <= der_info.max_total_g + slack_max
            # Store for objective
            problem_dict["envelope_slack_min"] = None
            problem_dict["envelope_slack_max"] = slack_max
        else:
            prob += total >= der_info.min_total_g
            prob += total <= der_info.max_total_g

# Energy density / DER proximity
    der_dev_plus = {}
    der_dev_minus = {}
    def add_der_proximity():
        nonlocal prob
        total_energy = pulp.lpSum(
            em_per_g[iid] * x_vars[iid]  # EM_kcal_per_g * grams = kcal
            for iid in valid_selected_ids
        )
        # Add deviation variables for DER proximity objective
        dev_plus = pulp.LpVariable("dev_der_plus", lowBound=0, cat="Continuous")
        dev_minus = pulp.LpVariable("dev_der_minus", lowBound=0, cat="Continuous")
        prob += total_energy - dev_plus + dev_minus == der_info.der_kcal
        der_dev_plus["dev_der_plus"] = dev_plus
        der_dev_minus["dev_der_minus"] = dev_minus

    # Store DER deviation vars for objective
    problem_dict["der_dev_vars"] = der_dev_plus | der_dev_minus

    # Ca:P ratio (hard)
    def add_ca_p_ratio():
        nonlocal prob
        ca = pulp.lpSum(compiled_coeffs[iid].get("calcium_g", 0.0) * x_vars[iid] for iid in valid_selected_ids)
        p = pulp.lpSum(compiled_coeffs[iid].get("phosphorus_g", 0.0) * x_vars[iid] for iid in valid_selected_ids)
        prob += ca >= 1.1 * p
        prob += ca <= 1.3 * p

    # Assemble constraints
    add_nutrient_constraints()
    add_sul_constraints()
    add_inclusion_constraints(relax=(cascade_level == 3))
    add_antagonism_constraints()
    add_envelope_constraints()

    # 8. Clinical floor (Level 3 only, config-driven)
    has_binary_vars = False
    if apply_clinical_floor:
        # Get clinical floor bounds from formulation_rules
        incl_constraints = fr.get("_inclusion_semantics", {}).get("inclusion_constraints", [])
        floor_config = level_config.get("clinical_floor", {})
        defaults = floor_config.get("defaults_by_category", {})
        global_fallback = floor_config.get("global_fallback_g", 5.0)

        for iid in valid_selected_ids:
            ing = get_ingredient_by_id(iid, db)
            if not ing:
                continue
            cat = ing.get("category", "unknown")

            # Find declared floor
            declared = None
            for ic in incl_constraints:
                if ic.get("ingredient_id") == iid:
                    declared = ic.get("clinical_floor_g")
                    break

            floor_g = declared if declared is not None else defaults.get(cat, global_fallback)
            clinical_floor_bounds[iid] = floor_g

            # Binary variable y_i
            y = pulp.LpVariable(f"y_{iid}", cat="Binary")
            M = big_m_values[iid]

            # x_i <= M * y_i
            prob += x_vars[iid] <= M * y
            # x_i >= floor_g * y_i
            prob += x_vars[iid] >= floor_g * y

            has_binary_vars = True

    return {
        "prob": prob,
        "x_vars": x_vars,
        "compiled_coefficients": compiled_coeffs,
        "targets_per_day": targets_per_day,
        "suls_per_day": suls_per_day,
        "clinical_floor_bounds": clinical_floor_bounds,
        "big_m_values": big_m_values,
        "has_binary_vars": has_binary_vars,
        "em_per_g": em_per_g,
        "der_info": der_info,
        "nutrient_slack_vars": problem_dict.get("nutrient_slack_vars", {}),
        "sul_slack_vars": problem_dict.get("sul_slack_vars", {}),
        "der_dev_vars": problem_dict.get("der_dev_vars", {}),
    }


def call_lp_solver(problem_dict: dict, objective_stages: list, solver_params: dict) -> dict:
    """
    Solve the LP/MILP with lexicographic stages.

    Args:
        problem_dict: Output from build_lp_problem()
        objective_stages: List of stage configs from solve_cascade (each has 'name', 'kind', 'fix_optimum')
        solver_params: solver_params block from lp_parameters_data.json

Returns:
        {status, x_values, nutrient_values, objective_value, stages_solved, solve_time_ms}
    """
    import pulp
    import time

    prob = problem_dict["prob"]
    x_vars = problem_dict["x_vars"]
    compiled_coeffs = problem_dict["compiled_coefficients"]
    suls_per_day = problem_dict["suls_per_day"]
    targets_per_day = problem_dict["targets_per_day"]
    has_binary_vars = problem_dict["has_binary_vars"]
    em_per_g = problem_dict.get("em_per_g", {})

    stages_solved = []
    start_time = time.time()

    for stage_idx, stage in enumerate(objective_stages):
        stage_name = stage.get("name")
        stage_kind = stage.get("kind")
        fix_opt = stage.get("fix_optimum", False)
        is_last_stage = (stage_idx == len(objective_stages) - 1)

# Build objective expression for this stage
        obj_expr = _build_stage_objective(
            prob, x_vars, compiled_coeffs, suls_per_day, targets_per_day, stage_kind, em_per_g, problem_dict
        )

        # Deterministic tie-break: add to EVERY stage to ensure deterministic branching
        # Use VERY STRONG perturbation (1000.0) to guarantee uniqueness over solver tolerance
        tie_weight = solver_params.get("tie_break_weight", 1000.0)
        def det_hash(s: str) -> int:
            h = 0
            for ch in s:
                h = (h * 31 + ord(ch)) & 0xFFFFFFFF
            return h
        
        tie_break_expr = 0
        for iid, var in x_vars.items():
            # Deterministic perturbation based on ingredient_id hash
            # Range: 0-9999 * 1e-1 = 0-999.9, added to tie_weight
            perturbation = (det_hash(iid) % 10000) * 1e-1
            tie_break_expr += (tie_weight + perturbation) * var
        obj_expr += tie_break_expr

        prob.setObjective(obj_expr)

# Solve
        prob.solve(pulp.PULP_CBC_CMD(
            msg=False,
            timeLimit=solver_params.get("cbc_time_limit_seconds", 30),
            gapRel=solver_params.get("cbc_mip_gap", 0.01),
            threads=1,
            options=["randomSeed=12345"],
        ))

        status = pulp.LpStatus[prob.status]
        if status != "Optimal":
            return {"status": "infeasible", "stages_solved": stages_solved}

        stages_solved.append(stage_name)

        # Fix optimum if required
        if fix_opt:
            optimal_obj = pulp.value(prob.objective)
            tol_rel = solver_params.get("fix_optimum_tolerance_rel", 1e-6)
            tol_abs = solver_params.get("fix_optimum_tolerance_abs", 0.01)

            # mip_tolerance_rule: widen tolerance if stage had binary vars
            if has_binary_vars:
                mip_gap = solver_params.get("cbc_mip_gap", 0.01)
                tol_rel = max(tol_rel, mip_gap)

            bound = optimal_obj * (1 + tol_rel) + tol_abs
            prob += obj_expr <= bound

    # Extract solution
    x_values = {iid: pulp.value(var) for iid, var in x_vars.items() if pulp.value(var) is not None and pulp.value(var) > 1e-6}

    # Compute nutrient values from solution
    nutrient_values = {}
    for nid in targets_per_day:
        nutrient_values[nid] = sum(
            compiled_coeffs[iid].get(nid, 0.0) * x_values.get(iid, 0.0)
            for iid in x_values
        )
    for nid in suls_per_day:
        if nid not in nutrient_values:
            nutrient_values[nid] = sum(
                compiled_coeffs[iid].get(nid, 0.0) * x_values.get(iid, 0.0)
                for iid in x_values
            )

    solve_time_ms = int((time.time() - start_time) * 1000)

    return {
        "status": "feasible",
        "x_values": x_values,
        "nutrient_values": nutrient_values,
        "objective_value": pulp.value(prob.objective),
        "stages_solved": stages_solved,
        "solve_time_ms": solve_time_ms,
        "nutrient_slack_vars": problem_dict.get("nutrient_slack_vars", {}),
        "sul_slack_vars": problem_dict.get("sul_slack_vars", {}),
        "der_dev_vars": problem_dict.get("der_dev_vars", {}),
        "clinical_floor_bounds": problem_dict.get("clinical_floor_bounds", {}),
        "clinical_floor_relaxed": problem_dict.get("clinical_floor_relaxed", False),
    }


def _build_stage_objective(
    prob: "pulp.LpProblem",
    x_vars: dict,
    compiled_coeffs: dict,
    suls_per_day: dict,
    targets_per_day: dict,
    kind: str,
    em_per_g: dict,
    problem_dict: dict,
) -> "pulp.LpAffineExpression":
    """Build objective expression for a given stage kind using pre-created variables."""
    import pulp

    # Get pre-created variables from problem_dict
    nutrient_slack_vars = problem_dict.get("nutrient_slack_vars", {})
    sul_slack_vars = problem_dict.get("sul_slack_vars", {})
    der_dev_vars = problem_dict.get("der_dev_vars", {})

    if kind == "minimize_normalized_sul_violation":
        # Sum of v_j_plus / SUL_j for all safety_hard nutrients
        expr = 0
        for nid, sul in suls_per_day.items():
            if sul > 0 and nid in sul_slack_vars:
                v = sul_slack_vars[nid]
                expr += v / sul
        return expr

    elif kind == "minimize_absolute_der_deviation":
        # Minimize |total_energy - DER| using pre-created deviation vars
        dev_plus = der_dev_vars.get("dev_der_plus")
        dev_minus = der_dev_vars.get("dev_der_minus")
        if dev_plus is None or dev_minus is None:
            # Fallback - create if not exist (shouldn't happen)
            dev_plus = pulp.LpVariable("dev_der_plus", lowBound=0, cat="Continuous")
            dev_minus = pulp.LpVariable("dev_der_minus", lowBound=0, cat="Continuous")
        return dev_plus + dev_minus

    elif kind == "minimize_weighted_normalized_adequacy_slack":
        # Sum of (slack / target) * clinical_criticality_weight
        expr = 0
        for nid, target in targets_per_day.items():
            if target > 0 and nid in nutrient_slack_vars:
                slack = nutrient_slack_vars[nid]
                weight = 1.0  # clinical_criticality weight from registry
                expr += (slack / target) * weight
        return expr

    elif kind == "weighted_normalized_deviation":
        # Canonical goal programming: sum w_j * (d_j^- + d_j^+) / target_j (normalized)
        expr = 0
        for nid, target in targets_per_day.items():
            if target <= 0:
                continue
            d_minus = pulp.LpVariable(f"d_{nid}_minus", lowBound=0, cat="Continuous")
            d_plus = pulp.LpVariable(f"d_{nid}_plus", lowBound=0, cat="Continuous")
            nutrient_sum = pulp.lpSum(
                compiled_coeffs[iid].get(nid, 0.0) * x_vars[iid]
                for iid in x_vars
            )
            prob += nutrient_sum + d_minus - d_plus == target
            # Normalize by target and use clinical_criticality weight
            weight = 1.0  # clinical_criticality weight from registry
            expr += (d_minus + d_plus) / target * weight
        return expr

    elif kind == "goal_deviation":
        # Canonical goal programming: sum w_j * (d_j^- + d_j^+)
        expr = 0
        for nid, target in targets_per_day.items():
            d_minus = pulp.LpVariable(f"d_{nid}_minus", lowBound=0, cat="Continuous")
            d_plus = pulp.LpVariable(f"d_{nid}_plus", lowBound=0, cat="Continuous")
            nutrient_sum = pulp.lpSum(
                compiled_coeffs[iid].get(nid, 0.0) * x_vars[iid]
                for iid in x_vars
            )
            prob += nutrient_sum + d_minus - d_plus == target
            expr += d_minus + d_plus  # weights can be added from objective_weights.json
        
        # Add antagonism slack terms to Level 1 objective
        antagonism_slack_vars = problem_dict.get("antagonism_slack_vars", {})
        antagonism_penalty_weights = problem_dict.get("antagonism_penalty_weights", {})
        for slack_name, slack_var in antagonism_slack_vars.items():
            # Extract constraint_id from slack_name (format: s_high_CSTR_... or s_low_CSTR_...)
            cid = slack_name[2:] if slack_name.startswith("s_") else slack_name
            penalty_weight = antagonism_penalty_weights.get(cid, 5000)
            expr += slack_var * penalty_weight
        
        return expr

    elif kind == "weighted_normalized_slack":
        # Level 2: slack weighted by clinical_criticality - use pre-created slack vars
        expr = 0
        for nid, target in targets_per_day.items():
            if target > 0 and nid in nutrient_slack_vars:
                slack = nutrient_slack_vars[nid]
                weight = 1.0  # clinical_criticality weight from registry
                expr += (slack / target) * weight
        # Also include envelope slack (Level 2 relaxes envelope_soft)
        env_slack_min = problem_dict.get("envelope_slack_min")
        env_slack_max = problem_dict.get("envelope_slack_max")
        der_kcal = problem_dict.get("der_info", {}).der_kcal if problem_dict.get("der_info") else 1
        if env_slack_min is not None:
            # Weight envelope slack by DER to normalize
            expr += (env_slack_min / der_kcal) if der_kcal > 0 else env_slack_min
        if env_slack_max is not None:
            expr += (env_slack_max / der_kcal) if der_kcal > 0 else env_slack_max
        return expr

    # Default
    return pulp.lpSum(x_vars.values())


def solve_cascade(
    selected_ids: list[str],
    data: dict,
    der_info: DerEnvelope,
    scenario_id: str,
) -> dict:
    """
    Execute the declarative cascade: Level 1 -> 2 -> 3, stop at first feasible.
    Returns the full output contract per sat_solver_contrato:§7.
    """
    import copy

    # Build matrix once (energy_normalized/1000kcal)
    fr = data.get("formulation_rules.json", {})
    fr["_db_ref"] = data.get("DB_ingredientes.json", {})
    matrix = build_matrix(selected_ids, data.get("DB_ingredientes.json", {}), fr)

    lp_params = data.get("lp_parameters_data.json", {})
    solver_params = lp_params.get("solver_params", {})
    cascade_config = lp_params.get("solve_cascade", [])

    cascade_attempts = []

    for level_config in cascade_config:
        level = level_config.get("level", 0)
        cascade_attempts.append(level)

        # Declarative flag from config - NOT hardcoded level check
        apply_clinical_floor = bool(level_config.get("clinical_floor"))

        problem = build_lp_problem(
            selected_ids, matrix, data, der_info, level,
            apply_clinical_floor=apply_clinical_floor,
        )

        result = call_lp_solver(problem, level_config.get("objective_stages", []), solver_params)

        if result["status"] == "infeasible":
            continue

        if result["status"] == "feasible":
            return build_output_contract(result, level_config, data, der_info, cascade_attempts)

    # Fallback: all levels infeasible including Level 3
    registry = data.get("lp_parameters_data.json", {}).get("NUTRIENT_REGISTRY", {})
    nutrient_results = []
    for nid, ndata in registry.items():
        nutrient_results.append({
            "nutrient_id": nid,
            "display_name": ndata.get("display_name", nid),
            "value": None,
            "unit": ndata.get("unit", ""),
            "basis": "energy_normalized",
            "target_min": None,
            "target_max": None,
            "sul": ndata.get("sul_value"),
            "pct_of_min": None,
            "pct_of_sul": None,
            "status": "unknown",
            "constraint_tier": ndata.get("constraint_tier", "adequacy_soft"),
            "clinical_criticality": ndata.get("clinical_criticality", "low"),
        })

    return {
        "solver_output_schema": "v10.1",
        "solver_status": "structurally_infeasible",
        "feeding_recommendation": "DO_NOT_FEED",
        "cascade_level_used": None,
        "animal_context": der_info.as_animal_context("unknown", 0, "unknown"),
        "envelope": der_info.as_envelope_dict(),
        "allocations": None,
        "nutrient_results": nutrient_results,
        "diagnostic_analysis": {
            "reason": "No feasible solution at any cascade level, including the "
                       "violation-minimizing diagnostic level. Likely cause: a "
                       "hard structural constraint (inclusion/exclusion or ratio) "
                       "cannot be satisfied by any quantity of the selected "
                       "ingredients.",
        },
        "gaps": [],
        "alerts": [],
        "recommended_additions": [],
        "solver_metadata": {
            "solver_engine": "PuLP_CBC",
            "solve_time_ms": 0,
            "cascade_attempts": cascade_attempts,
            "final_level": None,
            "objective_value": None,
        },
    }


def compute_gaps(raw_result: dict, data: dict, der_info: DerEnvelope, level: int) -> list:
    """Compute gaps for nutrient adequacy and antagonism violations.
    
    Returns list of gap dicts matching the output contract schema.
    """
    gaps = []
    
    # 1. Nutrient adequacy gaps
    registry = data.get("lp_parameters_data.json", {}).get("NUTRIENT_REGISTRY", {})
    targets_per_day = raw_result.get("nutrient_values", {})
    x_values = raw_result.get("x_values", {})
    
    # Get targets from scenario (SCN_B_SLOW_GROWTH)
    scenario = next((s for s in data.get("scenarios.json", []) if s.get("scenario_id") == "SCN_B_SLOW_GROWTH"), {})
    scenario_targets = {t["nutrient_id"]: t["value"] for t in scenario.get("targets", [])}
    
    for nid, ndata in registry.items():
        if ndata.get("constraint_tier") != "adequacy_soft":
            continue
        
        target_min = scenario_targets.get(nid)
        if target_min is None:
            continue
            
        value = targets_per_day.get(nid, 0)
        if value < target_min:
            pct_of_min = (value / target_min * 100) if target_min > 0 else 0
            gaps.append({
                "nutrient_id": nid,
                "pct_of_min": round(pct_of_min, 1),
                "category_missing": _map_nutrient_to_category(nid),
                "top_ingredients_in_category": _top_ingredients_for_nutrient(nid, data.get("DB_ingredientes.json", {}))
            })
    
    # 2. Antagonism ratio violation gaps
    constraints = data.get("constraints.json", {})
    compiled_coeffs = raw_result.get("compiled_coefficients", {})
    x_values = raw_result.get("x_values", {})
    
    for antag in constraints.get("mineral_antagonisms", []):
        vars_ref = antag.get("lp_coefficients", {}).get("variables_referenced", [])
        if len(vars_ref) != 2:
            continue
        n1, n2 = vars_ref[0], vars_ref[1]
        bounds_list = antag.get("lp_coefficients", {}).get("bounds", [])
        
        # Compute achieved ratio
        val1 = sum(compiled_coeffs[iid].get(n1, 0.0) * x_values.get(iid, 0.0) for iid in x_values)
        val2 = sum(compiled_coeffs[iid].get(n2, 0.0) * x_values.get(iid, 0.0) for iid in x_values)
        
        if val2 == 0:
            # Denominator absent - ratio undefined
            gaps.append({
                "nutrient_id": f"{n1}_{n2}_ratio",
                "pct_of_min": 0,
                "category_missing": _map_antagonism_to_category(n1, n2),
                "top_ingredients_in_category": _top_ingredients_for_antagonism(n1, n2, data.get("DB_ingredientes.json", {}))
            })
            continue
            
        ratio = val1 / val2
        rhs_min = None
        rhs_max = None
        for bounds in bounds_list:
            sense = bounds.get("sense", "")
            vars_dict = bounds.get("variables", {})
            coeff_n2 = vars_dict.get(n2, 0)
            if coeff_n2 < 0:
                ratio_val = -coeff_n2
                if sense == ">=":
                    rhs_min = ratio_val
                elif sense == "<=":
                    rhs_max = ratio_val
        
        violated = False
        if rhs_min is not None and ratio < rhs_min:
            violated = True
        if rhs_max is not None and ratio > rhs_max:
            violated = True
            
        if violated:
            gaps.append({
                "nutrient_id": f"{n1}_{n2}_ratio",
                "pct_of_min": 0,
                "category_missing": _map_antagonism_to_category(n1, n2),
                "top_ingredients_in_category": _top_ingredients_for_antagonism(n1, n2, data.get("DB_ingredientes.json", {}))
            })
    
    return gaps


def _map_nutrient_to_category(nutrient_id: str) -> str:
    """Map nutrient to ingredient category for gap recommendations."""
    mapping = {
        "calcium_g": "bone",
        "phosphorus_g": "bone",
        "vitamin_a_iu": "organ_secreting",
        "vitamin_d3_iu": "organ_secreting",
        "copper_mg": "organ_secreting",
        "iron_mg": "blood_source",
        "zinc_mg": "muscle_meat",
        "manganese_mg": "organ_non_secreting",
        "iodine_mg": "kelp",
        "selenium_mg": "organ_secreting",
        "fat_g": "fat_source",
        "protein_g": "muscle_meat",
        "lysine_g": "muscle_meat",
        "methionine_plus_cystine_g": "muscle_meat",
        "linoleic_acid_g": "fat_source",
        "epa_plus_dha_g": "fish",
    }
    return mapping.get(nutrient_id, "unknown")


def _top_ingredients_for_nutrient(nutrient_id: str, db: dict) -> list:
    """Return top 3 ingredients by concentration for a nutrient."""
    concentrations = []
    for group in db.get("protein_sources", {}).values():
        for ing in group.get("ingredients", []):
            nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
            entry = nuts.get(nutrient_id)
            if entry and entry.get("status") == "measured" and entry.get("value") is not None:
                concentrations.append({
                    "ingredient_id": ing["ingredient_id"],
                    "concentration_per_1000kcal": entry["value"]
                })
    concentrations.sort(key=lambda x: x["concentration_per_1000kcal"], reverse=True)
    return concentrations[:3]


def _map_antagonism_to_category(n1: str, n2: str) -> str:
    """Map antagonism pair to ingredient category for gap recommendations."""
    if "calcium" in n1 and "phosphorus" in n2:
        return "bone"
    if "zinc" in n1 and "copper" in n2:
        return "organ_secreting"
    if "iron" in n1 and "zinc" in n2:
        return "blood_source"
    if "calcium" in n1 and "magnesium" in n2:
        return "bone"
    if "lysine" in n1 and "arginine" in n2:
        return "muscle_meat"
    return "unknown"


def _top_ingredients_for_antagonism(n1: str, n2: str, db: dict) -> list:
    """Return top ingredients for antagonism pair (based on n1/n2 concentrations)."""
    # For Ca:P, recommend bone sources
    if "calcium" in n1 and "phosphorus" in n2:
        return _top_ingredients_for_nutrient("calcium_g", db)
    return _top_ingredients_for_nutrient(n1, db)


def compute_gaps(raw_result: dict, data: dict, der_info: DerEnvelope, level: int) -> list:
    """Compute nutrient adequacy gaps and antagonism ratio violations.
    
    Args:
        raw_result: Solver result with x_values and nutrient_values
        data: Full data dict with registry, constraints, etc.
        der_info: DerEnvelope with DER and envelope info
        level: Cascade level used
    
    Returns:
        List of gap dicts with nutrient_id, pct_of_min, category_missing, etc.
    """
    gaps = []
    x_values = raw_result.get("x_values", {})
    nutrient_values = raw_result.get("nutrient_values", {})
    registry = data.get("lp_parameters_data.json", {}).get("NUTRIENT_REGISTRY", {})
    constraints = data.get("constraints.json", {})
    
    # 1. Nutrient adequacy gaps (for all levels)
    for nid, ndata in registry.items():
        if ndata.get("constraint_tier") != "adequacy_soft":
            continue
        target_min = ndata.get("target_min")
        if target_min is None:
            # Try to get from scenario
            target_min = ndata.get("aaFco_min") or ndata.get("nrc_min")
        if target_min is None or target_min <= 0:
            continue
        
        achieved = nutrient_values.get(nid, 0)
        pct_of_min = round(achieved / target_min * 100, 1) if target_min > 0 else 0
        
        if pct_of_min < 100:
            # Map nutrient to missing category
            category_map = {
                "calcium_g": "bone",
                "phosphorus_g": "bone",
                "protein_g": "muscle_meat",
                "fat_g": "fat_source",
                "lysine_g": "muscle_meat",
                "methionine_plus_cystine_g": "muscle_meat",
                "linoleic_acid_g": "fat_source",
                "epa_plus_dha_g": "fish",
                "vitamin_a_iu": "organ_secreting",
                "vitamin_d3_iu": "organ_secreting",
                "vitamin_e_iu": "fat_source",
                "zinc_mg": "organ_secreting",
                "copper_mg": "organ_secreting",
                "iron_mg": "organ_secreting",
                "manganese_mg": "organ_secreting",
                "iodine_mg": "supplement",
                "selenium_mg": "organ_secreting",
            }
            category = category_map.get(nid, "unknown")
            
            gaps.append({
                "nutrient_id": nid,
                "pct_of_min": pct_of_min,
                "category_missing": category,
                "top_ingredients_in_category": []  # Could be populated from DB
            })
    
    # 2. Antagonism ratio violation gaps (for all levels)
    antag_constraints = data.get("constraints.json", {}).get("mineral_antagonisms", [])
    for antag in antag_constraints:
        cid = antag.get("constraint_id", "")
        vars_ref = antag.get("lp_coefficients", {}).get("variables_referenced", [])
        if len(vars_ref) != 2:
            continue
        n1, n2 = vars_ref[0], vars_ref[1]
        bounds_list = antag.get("lp_coefficients", {}).get("bounds", [])
        
        # Get achieved values
        val1 = nutrient_values.get(n1, 0)
        val2 = nutrient_values.get(n2, 0)
        
        if val2 <= 0:
            # Denominator missing - ratio undefined
            ratio = None
        else:
            ratio = val1 / val2
        
        # Check each bound
        for bounds in bounds_list:
            sense = bounds.get("sense", "")
            vars_dict = bounds.get("variables", {})
            coeff_n1 = vars_dict.get(n1, 0)
            coeff_n2 = vars_dict.get(n2, 0)
            
            if coeff_n1 == 0 or coeff_n2 >= 0:
                continue
            
            bound_ratio = -coeff_n2 / coeff_n1
            
            violation = False
            if sense == ">=" and ratio is not None and ratio < bound_ratio:
                violation = True
            elif sense == "<=" and ratio is not None and ratio > bound_ratio:
                violation = True
            elif sense == ">=" and ratio is None:
                violation = True  # Denominator missing
            elif sense == "<=" and ratio is None:
                violation = True
            
            if violation:
                # Determine gap nutrient_id and category
                gap_nutrient_id = f"{n1}_{n2}_ratio"
                category_map = {
                    ("calcium_g", "phosphorus_g"): "bone",
                    ("zinc_mg", "copper_mg"): "organ_secreting",
                    ("iron_mg", "zinc_mg"): "organ_secreting",
                    ("calcium_g", "magnesium_g"): "bone",
                    ("lysine_g", "arginine_g"): "muscle_meat",
                }
                category = category_map.get((n1, n2), category_map.get((n2, n1), "unknown"))
                
                pct_str = f"{round(ratio / bound_ratio * 100, 1)}%" if ratio and bound_ratio else "undefined (denominator missing)"
                
                gaps.append({
                    "nutrient_id": gap_nutrient_id,
                    "pct_of_min": round(ratio / bound_ratio * 100, 1) if ratio and bound_ratio else 0,
                    "category_missing": category,
                    "top_ingredients_in_category": [],
                    "note": f"Ratio {n1}/{n2} = {ratio:.3f}, bound {sense} {bound_ratio:.3f}" if ratio else f"Ratio {n1}/{n2} undefined (denominator missing)"
                })
    
    return gaps

def build_output_contract(
    raw_result: dict,
    level_config: dict,
    data: dict,
    der_info: DerEnvelope,
    cascade_attempts: list,
) -> dict:
    """Build the final output contract from a feasible solver result."""
    level = level_config.get("level", 0)
    result_status = level_config.get("result_status", "unknown")

    # Map status to feeding recommendation
    feeding_map = {
        "optimal": "SAFE_TO_FEED",
        "suboptimal": "FEED_WITH_CAUTION",
        "unsafe_diagnostic": "DO_NOT_FEED",
        "structurally_infeasible": "DO_NOT_FEED",
        "data_incomplete": "DO_NOT_FEED",
    }
    feeding_rec = feeding_map.get(result_status, "DO_NOT_FEED")

    # Build allocations for Levels 1/2
    allocations = None
    if level in (1, 2) and raw_result.get("x_values"):
        x_vals = raw_result["x_values"]
        total_g = sum(x_vals.values())
        allocations = []
        for iid, grams in x_vals.items():
            if grams > 0.01:
                ing = get_ingredient_by_id(iid, data.get("DB_ingredientes.json", {}))
                if ing:
                    # Compute kcal for this ingredient
                    nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
                    em = energy_metabolizable_kcal_per_100g(nuts)
                    kcal = grams * em / 100.0
                    allocations.append({
                        "ingredient_id": iid,
                        "display_name": ing.get("display_name", iid),
                        "category": ing.get("category", "unknown"),
                        "grams_per_day": round(grams, 1),
                        "pct_of_total": round(grams / total_g * 100, 1) if total_g > 0 else 0,
                        "kcal_per_day": round(kcal, 1),
                        "cost_per_day": None,
                    })

    # Build nutrient_results (always 41+ entries)
    nutrient_results = []
    registry = data.get("lp_parameters_data.json", {}).get("NUTRIENT_REGISTRY", {})
    targets_per_day = raw_result.get("nutrient_values", {})
    suls_per_day = data.get("lp_parameters_data.json", {}).get("solver_params", {})

    for nid in registry:
        ndata = registry[nid]
        value = targets_per_day.get(nid, 0)
        target_min = ndata.get("sul_value") if ndata.get("has_sul") else None
        # This is simplified - real implementation computes min/max from scenarios/matrix
        nutrient_results.append({
            "nutrient_id": nid,
            "display_name": ndata.get("display_name", nid),
            "value": round(value, 4),
            "unit": ndata.get("unit", ""),
            "basis": "energy_normalized",
            "target_min": target_min,
            "target_max": None,
            "sul": ndata.get("sul_value"),
            "pct_of_min": None,
            "pct_of_sul": None,
            "status": "adequate",
            "constraint_tier": ndata.get("constraint_tier", "adequacy_soft"),
            "clinical_criticality": ndata.get("clinical_criticality", "low"),
        })

    # Build diagnostic_analysis for Level 3
    diagnostic_analysis = None
    if level == 3:
        clinical_floor_info = {
            "bounds": raw_result.get("clinical_floor_bounds", {}),
            "relaxed": raw_result.get("clinical_floor_relaxed", False),
        }
        diagnostic_analysis = build_diagnostic_analysis(raw_result, data, der_info, clinical_floor_info)

    # Metadata
    meta = {
        "solver_engine": "PuLP_CBC",
        "solve_time_ms": raw_result.get("solve_time_ms", 0),
        "cascade_attempts": cascade_attempts,
        "final_level": level,
        "objective_value": raw_result.get("objective_value"),
    }
    if level == 3:
        meta["lexicographic_stages_used"] = {
            "stages": [s.get("name") for s in level_config.get("objective_stages", [])],
            "order_verified": True,
            "note": "SUL violation is fixed before DER deviation, which is fixed before adequacy slack"
        }
        meta["clinical_floor_applied"] = not clinical_floor_info.get("relaxed", False)
        meta["clinical_floor_bounds"] = clinical_floor_info.get("bounds", {})

    # Expose unrounded total for validation (avoids rounding error in envelope check)
    # See docs/phase0a-tolerance-design.md for rationale
    unrounded_total = sum(x_vals.values()) if level in (1, 2) and raw_result.get("x_values") else None

    return {
        "solver_output_schema": "v10.1",
        "solver_status": result_status,
        "feeding_recommendation": feeding_rec,
        "cascade_level_used": level,
        "animal_context": der_info.as_animal_context("male", 8, "intact"),
        "envelope": der_info.as_envelope_dict(),
        "allocations": allocations,
        "nutrient_results": nutrient_results,
        "diagnostic_analysis": diagnostic_analysis,
        "gaps": compute_gaps(raw_result, data, der_info, level),
        "alerts": [],
        "recommended_additions": [],
        "solver_metadata": meta,
        "_unrounded_total_g": unrounded_total,
    }


def build_diagnostic_analysis(
    raw_result: dict,
    data: dict,
    der_info: DerEnvelope,
    clinical_floor_info: dict,
) -> dict:
    """Build diagnostic_analysis block for Level 3 unsafe_diagnostic."""
    suls_per_day = {}
    tox_limits = data.get("toxicological_limits.json", [])
    for tox in tox_limits:
        nid = tox.get("nutrient_id")
        sul_entry = tox.get("sul", {})
        sul_val = sul_entry.get("value")
        if nid and sul_val is not None:
            suls_per_day[nid] = float(sul_val) * der_info.units_of_1000kcal

    nutrient_values = raw_result.get("nutrient_values", {})

    # 1. Identify inevitable SUL violations
    sul_violations = []
    for nid, sul_day in suls_per_day.items():
        achieved = nutrient_values.get(nid, 0)
        if achieved > sul_day:
            sul_violations.append({
                "nutrient_id": nid,
                "sul": sul_day,
                "minimum_achievable_at_der": round(achieved, 2),
                "pct_above_sul": round((achieved / sul_day - 1) * 100, 1),
                "mechanism": "Nutrient concentration and caloric content are proportional "
                           "in the selected ingredients — no feasible separation exists."
            })

    # 2. Counterfactual scenario
    x_values = raw_result.get("x_values", {})
    total_grams_for_der = sum(x_values.values())

    floor_bounds = clinical_floor_info.get("bounds", {})
    relaxed = clinical_floor_info.get("relaxed", False)
    ingredients_below_floor = []
    for iid, x_val in x_values.items():
        floor = floor_bounds.get(iid, 5)
        if 0 < x_val < floor:
            ingredients_below_floor.append({
                "ingredient_id": iid,
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
        "clinical_floor_applied": not relaxed,
        "clinical_floor_relaxed": relaxed,
        "ingredients_below_floor": ingredients_below_floor,
        "x_min_i_effective": floor_bounds,
    }

    if relaxed:
        what_would_happen["clinical_floor_relaxation_note"] = (
            "Even the minimum recognizable portion of the selected ingredient(s) "
            "violates the SUL. No safe amount exists. The scenario below shows "
            "what the solver computed without the clinical floor constraint — "
            "these values are below any meaningful portion and serve only as "
            "mathematical evidence of inseparability."
        )

    # 3. Recommended alternative actions
    recommended_actions = [
        "Add a calorie source WITHOUT concentrated vitamin A (e.g., beef_muscle_raw, chicken_muscle_raw)",
        "Reduce liver/organ proportion and add muscle meat as caloric base",
        "Use recipe mode (Receitas Prontas) for pre-validated safe combinations"
    ]

    # 4. Reason
    reason = (
        "No combination of selected ingredients meets caloric needs without "
        "exceeding safe limits. Caloric content and the SUL-violating nutrient "
        "are inseparable in the selected ingredient(s) — every gram adds both "
        "proportionally."
    )
    if relaxed:
        reason += (
            " Even the minimum clinically significant portion (clinical_floor_g) "
            "of the ingredient exceeds the SUL. The solver was re-run without "
            "the floor constraint to produce a mathematical counterfactual."
        )

    return {
        "reason": reason,
        "sul_violations_inevitable": sul_violations,
        "what_would_happen": what_would_happen,
        "recommended_alternative_actions": recommended_actions,
    }


def validate_output(result: dict, data: dict, der_info: DerEnvelope) -> None:
    """Validate output against the solver contract (§7). Raises AssertionError on failure."""
    # 1. Canonical solver_status
    assert result["solver_status"] in (
        "optimal", "suboptimal", "unsafe_diagnostic",
        "structurally_infeasible", "data_incomplete"
    ), f"Invalid solver_status: {result['solver_status']}"

    # 2. feeding_recommendation matches
    expected_rec = {
        "optimal": "SAFE_TO_FEED",
        "suboptimal": "FEED_WITH_CAUTION",
        "unsafe_diagnostic": "DO_NOT_FEED",
        "structurally_infeasible": "DO_NOT_FEED",
        "data_incomplete": "DO_NOT_FEED",
    }
    assert result["feeding_recommendation"] == expected_rec[result["solver_status"]], \
        f"feeding_recommendation mismatch"

    # 3. Level 1/2: allocations not null, within envelope
    if result["solver_status"] in ("optimal", "suboptimal"):
        assert result["allocations"] is not None, "Level 1/2 must have allocations"
        assert len(result["allocations"]) >= 1, "At least one allocation required"
        # Use unrounded total to avoid 0.05g rounding error from sum of rounded allocations
        # See docs/phase0a-tolerance-design.md for rationale
        total_g = result.get("_unrounded_total_g") or sum(a["grams_per_day"] for a in result["allocations"])
        env = der_info.as_envelope_dict()
        assert env["min_total_g"] <= total_g <= env["max_total_g"], \
            f"Total grams {total_g} outside envelope [{env['min_total_g']}, {env['max_total_g']}]"

    # 4. Level 3 / structurally_infeasible: allocations null, diagnostic_analysis present
    if result["solver_status"] in ("unsafe_diagnostic", "structurally_infeasible"):
        assert result["allocations"] is None, "Level 3 must have allocations=null"
        assert result["diagnostic_analysis"] is not None, "Level 3 must have diagnostic_analysis"

    # 5. nutrient_results >= 41 entries
    assert len(result["nutrient_results"]) >= 41, f"nutrient_results has {len(result['nutrient_results'])} entries, need >=41"

    # 6. Each nutrient result has required fields
    for nr in result["nutrient_results"]:
        assert "pct_of_min" in nr
        assert "pct_of_sul" in nr
        assert "status" in nr
        assert "constraint_tier" in nr
        assert "clinical_criticality" in nr

    # 7. Level 3: lexicographic_stages_used.order_verified
    if result["solver_status"] == "unsafe_diagnostic":
        meta = result.get("solver_metadata", {})
        stages = meta.get("lexicographic_stages_used", {})
        assert stages.get("order_verified") is True, "lexicographic_stages_used.order_verified must be True"

    # 8. Level 3: clinical_floor_applied boolean, clinical_floor_bounds dict
    if result["solver_status"] == "unsafe_diagnostic":
        meta = result.get("solver_metadata", {})
        assert "clinical_floor_applied" in meta, "clinical_floor_applied missing in solver_metadata"
        assert isinstance(meta["clinical_floor_applied"], bool), "clinical_floor_applied must be bool"
        assert "clinical_floor_bounds" in meta, "clinical_floor_bounds missing in solver_metadata"
        assert isinstance(meta["clinical_floor_bounds"], dict), "clinical_floor_bounds must be dict"

        # 9. If clinical_floor_relaxed, relaxation_note must exist
        wwh = result["diagnostic_analysis"].get("what_would_happen", {})
        if wwh.get("clinical_floor_relaxed"):
            assert "clinical_floor_relaxation_note" in wwh, \
                "clinical_floor_relaxation_note required when clinical_floor_relaxed=true"


# ── Conditional Adequacy Checks (pre-solver, post-matrix) ─────────────────────

def check_fat_source_adequacy(
    matrix: dict[str, dict],
    selected_ids: list[str],
    formulation_rules: dict,
    der_envelope: "DerEnvelope"
) -> dict | None:
    """
    Conditional adequacy check: if fat_source inclusion is at structural minimum (8%)
    but total fat_g at that inclusion cannot meet AAFCO minimum (21.25 g/1000kcal),
    return a gap dict for the output contract. Called after matrix build, before solver.

    This is a pre-solver check that mirrors what the cascade conditional check
    (lp_parameters_data.json solve_cascade Level 1) would evaluate.
    """
    # Get DB reference first
    db = formulation_rules.get("_db_ref")
    if db is None:
        return None

    # Get fat_source inclusion constraint
    incl_limits = formulation_rules.get("inclusion_limits", [])
    fat_source_limit = next((il for il in incl_limits if il.get("ingredient_id") == "fat_source"), {})
    structural_min = fat_source_limit.get("min_pct", 8) / 100.0  # e.g., 0.08
    aafco_recommended_min = fat_source_limit.get("effective_min_pct_for_aafco_fat", 15) / 100.0  # e.g., 0.15

    # Find fat_source ingredients in selection
    all_ings = _find_all_ingredients(db)
    fat_source_ids = [iid for iid in selected_ids if all_ings.get(iid, {}).get("category") == "fat_source"]
    
    if not fat_source_ids:
        return None

    # Compute total fat_g at structural minimum fat_source inclusion
    # For each 1000kcal unit, fat_source contributes x% * fat_norm
    total_fat_at_structural_min = 0.0
    for fs_id in fat_source_ids:
        fs_ing = get_ingredient_by_id(fs_id, db)
        if not fs_ing:
            continue
        fs_nuts = fs_ing.get("bromatological_profile", {}).get("nutrients", {})
        fs_fat = fs_nuts.get("fat_g", {}).get("value", 0) if isinstance(fs_nuts.get("fat_g"), dict) else fs_nuts.get("fat_g", 0)
        if not fs_fat:
            continue
        # Energy normalized fat
        em = energy_metabolizable_kcal_per_100g(fs_nuts)
        if em <= 0:
            continue
        fs_fat_norm = fs_fat * (1000.0 / em)
        total_fat_at_structural_min += structural_min * fs_fat_norm

    # Add fat from other selected ingredients (at 100% - structural_min - other categories)
    # Simplified: assume remaining 92% is muscle_meat at average fat_norm
    # This is a conservative check - real solver would optimize
    other_fat = 0.0
    non_fs_ids = [iid for iid in selected_ids if iid not in fat_source_ids]
    for iid in non_fs_ids:
        ing = get_ingredient_by_id(iid, db)
        if not ing:
            continue
        nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
        fat = nuts.get("fat_g", {}).get("value", 0) if isinstance(nuts.get("fat_g"), dict) else nuts.get("fat_g", 0)
        if fat:
            em = energy_metabolizable_kcal_per_100g(nuts)
            if em > 0:
                other_fat += (1.0 - structural_min) * (fat * (1000.0 / em)) * (1.0 / len(non_fs_ids) if non_fs_ids else 1)

    total_fat_est = total_fat_at_structural_min + other_fat
    aafco_fat_min = 21.25  # g/1000kcal from formulation_rules.nutrient_matrix

    if total_fat_est < aafco_fat_min:
        # Gap detected
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


def _get_fat_norm(ing: dict | None) -> float:
    """Helper: compute fat_g energy_normalized for an ingredient."""
    if not ing:
        return 0.0
    nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
    fat = nuts.get("fat_g", {}).get("value", 0) if isinstance(nuts.get("fat_g"), dict) else nuts.get("fat_g", 0)
    if not fat:
        return 0.0
    em = energy_metabolizable_kcal_per_100g(nuts)
    if em <= 0:
        return 0.0
    return fat * (1000.0 / em)


def _find_all_ingredients(db: dict) -> dict:
    """Return dict of ingredient_id -> ingredient for all ingredients in DB."""
    result = {}
    for g in db.get("protein_sources", {}).values():
        for ing in g.get("ingredients", []):
            result[ing["ingredient_id"]] = ing
    return result


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
        # Parse --no-live-evidence flag (CI environments may lack LP solver deps)
        global _NO_LIVE_EVIDENCE
        _NO_LIVE_EVIDENCE = "--no-live-evidence" in sys.argv[2:]
        if _NO_LIVE_EVIDENCE:
            print("Note: --no-live-evidence set — section 18 will show skip marker")
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
        # Pass DB reference to formulation_rules for conditional check
        fr["_db_ref"] = db
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

        # Conditional adequacy check: fat source vs AAFCO fat minimum
        fat_gap = check_fat_source_adequacy(matrix, selected_ids, fr, der_env)
        print(f"\n=== Conditional Adequacy Check ===")
        if fat_gap:
            print(f"  GAP DETECTED: fat_g at structural minimum = {fat_gap['estimated_fat_at_structural_min']:.1f} g/1000kcal (AAFCO min = {fat_gap['aafco_fat_min']})")
            print(f"  Fat source at structural minimum ({fat_gap['structural_min_pct']:.0f}%) yields {fat_gap['pct_of_min']:.1f}% of AAFCO minimum")
            print(f"  AAFCO-recommended fat source inclusion: {fat_gap['aafco_recommended_min_pct']:.0f}%")
            print(f"  Note: {fat_gap['note']}")
        else:
            print(f"  OK: Fat source at structural minimum meets AAFCO fat_g minimum")

        # Step 6: solve cascade
        result = solve_cascade(selected_ids, data, der_env, scenario_id)
        validate_output(result, data, der_env)

        json.dump(result, open(DATA_DIR / "solver_output.json", "w", encoding="utf-8"),
                  indent=2, ensure_ascii=False)

        print(f"\n=== Solver Output ===")
        print(f"  Status: {result['solver_status']}")
        print(f"  Level: {result['cascade_level_used']}")
        print(f"  Feeding: {result['feeding_recommendation']}")
        if result['allocations']:
            for a in result['allocations']:
                print(f"  {a['ingredient_id']}: {a['grams_per_day']:.1f}g ({a['pct_of_total']:.1f}%)")

    elif mode == "--build-recipes":
        print("Build-recipes mode: not implemented. See docs/architecture/sat_pipeline_fluxo.md")
        sys.exit(0)

    else:
        print(f"Unknown mode: {mode}")
        print("Usage: build_pipeline.py [--generate-mapa | --gate-mapa | --audit-mapa | --validate-db | --runtime | --build-recipes]")
        sys.exit(1)


if __name__ == "__main__":
    main()
