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
        print("Runtime mode: not implemented. See docs/architecture/sat_pipeline_codigo.md")
        sys.exit(0)

    elif mode == "--build-recipes":
        print("Build-recipes mode: not implemented. See docs/architecture/sat_pipeline_fluxo.md")
        sys.exit(0)

    else:
        print(f"Unknown mode: {mode}")
        print("Usage: build_pipeline.py [--generate-mapa | --gate-mapa | --audit-mapa | --validate-db | --runtime | --build-recipes]")
        sys.exit(1)


if __name__ == "__main__":
    main()
