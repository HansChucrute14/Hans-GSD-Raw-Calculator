#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_db_ingredientes.py — Validate DB_ingredientes.json against formal contract
and generate coverage report.

Gate: All 20 ingredients must pass schema; missing fields must have explicit status
(measured/missing/not_applicable) — no silent key absence.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
from jsonschema import validate, ValidationError

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
SCHEMA_PATH = DATA_DIR / "db_ingredientes.schema.json"
DB_PATH = DATA_DIR / "DB_ingredientes.json"

# Expected nutrient universe (41 solver + 7 excluded = 48 keys in DB space)
UNIT_RENAME = {
    "calcium_g": "calcium_mg",
    "phosphorus_g": "phosphorus_mg",
    "magnesium_g": "magnesium_mg",
    "sodium_g": "sodium_mg",
    "potassium_g": "potassium_mg",
    "chloride_g": "chloride_mg",
    "choline_g": "choline_mg",
    "selenium_mg": "selenium_ug",
    "cobalamin_b12_mg": "cobalamin_b12_ug",
    "folic_acid_b9_mg": "folic_acid_b9_ug",
    "iodine_mg": "iodine_ug",
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

DB_NUTRIENTS = [UNIT_RENAME.get(n, n) for n in SOLVER_NUTRIENTS]
EXCLUDED_NUTRIENTS = ["biotin_ug", "chloride_mg", "iodine_ug", "vitamin_a_iu", "vitamin_d3_iu", "vitamin_e_iu", "vitamin_k_ug"]
ALL_REQUIRED_KEYS = DB_NUTRIENTS + EXCLUDED_NUTRIENTS


def load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_schema(db: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """Validate DB against JSON Schema. Return list of errors."""
    errors = []
    try:
        validate(instance=db, schema=schema)
    except ValidationError as e:
        errors.append(f"Schema validation failed at {'.'.join(str(x) for x in e.path)}: {e.message}")
    return errors


def check_key_completeness(db: Dict[str, Any]) -> Dict[str, List[str]]:
    """Check that every ingredient has all 48 nutrient keys with explicit status."""
    issues = {
        "missing_keys": [],
        "no_status": [],
        "invalid_status": [],
    }
    
    for group_name, group in db.get("protein_sources", {}).items():
        for ing in group.get("ingredients", []):
            iid = ing.get("ingredient_id", "?")
            bp = ing.get("bromatological_profile", {})
            nutrients = bp.get("nutrients", {})
            
            for key in ALL_REQUIRED_KEYS:
                if key not in nutrients:
                    issues["missing_keys"].append(f"{iid}: missing key '{key}'")
                else:
                    entry = nutrients[key]
                    if not isinstance(entry, dict) or "status" not in entry:
                        issues["no_status"].append(f"{iid}.{key}: no 'status' field (old format)")
                    elif entry.get("status") not in ("measured", "missing", "not_applicable"):
                        issues["invalid_status"].append(f"{iid}.{key}: invalid status '{entry.get('status')}'")
    
    return issues


def check_source_refs(db: Dict[str, Any]) -> List[str]:
    """Validate all source_ref and anomaly_ref point to audit_provenance.json."""
    errors = []
    prov = load_json(DATA_DIR / "audit_provenance.json")
    known_refs = set(prov.get("references", {}).keys())
    
    for group in db.get("protein_sources", {}).values():
        for ing in group.get("ingredients", []):
            iid = ing.get("ingredient_id", "?")
            # Check metadata
            meta = ing.get("metadata", {})
            for ref in [meta.get("usda_fdc_id")]:
                if ref and not ref.startswith("REF_"):
                    pass  # usda_fdc_id is not a REF_
            # Check nutrients
            bp = ing.get("bromatological_profile", {})
            for nkey, nval in bp.get("nutrients", {}).items():
                if isinstance(nval, dict):
                    sr = nval.get("source_ref")
                    ar = nval.get("anomaly_ref")
                    if sr and sr not in known_refs:
                        errors.append(f"{iid}.{nkey}: unknown source_ref '{sr}'")
                    if ar and ar not in known_refs:
                        errors.append(f"{iid}.{nkey}: unknown anomaly_ref '{ar}'")
            # Check safety alerts
            for alert in ing.get("safety_alerts", []):
                sr = alert.get("source_ref")
                if sr and sr not in known_refs:
                    errors.append(f"{iid}.safety_alert: unknown source_ref '{sr}'")
    
    return errors


def generate_coverage_report(db: Dict[str, Any]) -> str:
    """Generate per-ingredient, per-nutrient coverage report."""
    lines = []
    lines.append("# Coverage Report — DB_ingredientes.json")
    lines.append("")
    lines.append(f"**Total ingredients:** {sum(len(g.get('ingredients', [])) for g in db.get('protein_sources', {}).values())}")
    lines.append(f"**Required nutrient keys:** {len(ALL_REQUIRED_KEYS)}")
    lines.append("")
    
    # Summary table
    lines.append("## Per-Ingredient Summary")
    lines.append("")
    lines.append("| Ingredient | Group | Measured | Missing | Not Applicable | Total |")
    lines.append("|------------|-------|----------|---------|----------------|-------|")
    
    for group_name, group in db.get("protein_sources", {}).items():
        for ing in group.get("ingredients", []):
            iid = ing.get("ingredient_id", "?")
            bp = ing.get("bromatological_profile", {})
            nutrients = bp.get("nutrients", {})
            
            measured = missing = na = 0
            for key in ALL_REQUIRED_KEYS:
                entry = nutrients.get(key, {})
                status = entry.get("status") if isinstance(entry, dict) else None
                if status == "measured":
                    measured += 1
                elif status == "missing":
                    missing += 1
                elif status == "not_applicable":
                    na += 1
                else:
                    # Old format or invalid
                    measured += 1  # count as measured for old format
            
            lines.append(f"| `{iid}` | {group_name} | {measured} | {missing} | {na} | {measured+missing+na} |")
    
    lines.append("")
    
    # Per-nutrient table
    lines.append("## Per-Nutrient Coverage")
    lines.append("")
    lines.append("| Nutrient | Measured In | Missing In | N/A In |")
    lines.append("|----------|-------------|------------|--------|")
    
    for key in ALL_REQUIRED_KEYS:
        measured_ings = []
        missing_ings = []
        na_ings = []
        
        for group_name, group in db.get("protein_sources", {}).items():
            for ing in group.get("ingredients", []):
                iid = ing.get("ingredient_id", "?")
                bp = ing.get("bromatological_profile", {})
                nutrients = bp.get("nutrients", {})
                entry = nutrients.get(key, {})
                status = entry.get("status") if isinstance(entry, dict) else None
                
                if status == "measured":
                    measured_ings.append(iid)
                elif status == "missing":
                    missing_ings.append(iid)
                elif status == "not_applicable":
                    na_ings.append(iid)
                else:
                    # Old format
                    if key in nutrients:
                        measured_ings.append(iid)
        
        lines.append(f"| `{key}` | {len(measured_ings)} | {len(missing_ings)} | {len(na_ings)} |")
    
    lines.append("")
    
    # Detailed per-ingredient
    lines.append("## Detailed Per-Ingredient Nutrient Status")
    lines.append("")
    
    for group_name, group in db.get("protein_sources", {}).items():
        lines.append(f"### Group: {group_name}")
        lines.append("")
        for ing in group.get("ingredients", []):
            iid = ing.get("ingredient_id", "?")
            lines.append(f"#### `{iid}`")
            lines.append("")
            lines.append("| Nutrient | Status | Value | Unit | Source Ref |")
            lines.append("|----------|--------|-------|------|------------|")
            bp = ing.get("bromatological_profile", {})
            nutrients = bp.get("nutrients", {})
            
            for key in ALL_REQUIRED_KEYS:
                entry = nutrients.get(key, {})
                if isinstance(entry, dict) and "status" in entry:
                    status = entry.get("status")
                    if status == "measured":
                        val = entry.get("value")
                        unit = entry.get("unit")
                        sr = entry.get("source_ref")
                    elif status == "missing":
                        val = "—"
                        unit = "—"
                        sr = entry.get("anomaly_ref", "—")
                    elif status == "not_applicable":
                        val = "N/A"
                        unit = "N/A"
                        sr = entry.get("anomaly_ref", "—")
                    else:
                        val = "INVALID"
                        unit = "INVALID"
                        sr = "INVALID"
                elif key in nutrients:
                    # Old format
                    val = entry.get("value")
                    unit = entry.get("unit")
                    sr = entry.get("source_ref")
                    status = "measured (legacy)"
                else:
                    val = "MISSING KEY"
                    unit = "—"
                    sr = "—"
                    status = "MISSING KEY"
                
                lines.append(f"| `{key}` | {status} | {val} | {unit} | {sr} |")
            lines.append("")
    
    return "\n".join(lines)


def main():
    print("Loading schema and DB...")
    schema = load_json(SCHEMA_PATH)
    db = load_json(DB_PATH)
    
    print("Running schema validation...")
    schema_errors = validate_schema(db, schema)
    
    print("Checking key completeness...")
    key_issues = check_key_completeness(db)
    
    print("Checking source references...")
    ref_errors = check_source_refs(db)
    
    all_errors = schema_errors
    all_errors.extend([f"Key completeness: {k}" for k in key_issues["missing_keys"]])
    all_errors.extend([f"Key completeness: {k}" for k in key_issues["no_status"]])
    all_errors.extend([f"Key completeness: {k}" for k in key_issues["invalid_status"]])
    all_errors.extend(ref_errors)
    
    print(f"\n{'='*60}")
    print(f"VALIDATION RESULT: {'PASS' if not all_errors else 'FAIL'}")
    print(f"Total errors: {len(all_errors)}")
    print(f"{'='*60}")
    
    if all_errors:
        for err in all_errors[:50]:
            print(f"  - {err}")
        if len(all_errors) > 50:
            print(f"  ... and {len(all_errors) - 50} more")
        print()
    
    print("Generating coverage report...")
    report = generate_coverage_report(db)
    report_path = BASE_DIR / "coverage_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Coverage report written to: {report_path}")
    
    if all_errors:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()