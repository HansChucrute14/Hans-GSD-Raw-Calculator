#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
remigrate_db.py — Proper migration using PER-INGREDIENT coverage_excluded_nutrients
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "DB_ingredientes.json"
BACKUP_PATH = DATA_DIR / "DB_ingredientes.json.bak_v3.0.0_before_remigrate"

# Unit rename map from solver space → DB space
UNIT_RENAME = {
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

EXCLUDED_NUTRIENTS = ["biotin_ug", "chloride_mg", "iodine_ug", "vitamin_a_iu", "vitamin_d3_iu", "vitamin_e_iu", "vitamin_k_ug"]

DB_NUTRIENTS = [UNIT_RENAME.get(n, n) for n in SOLVER_NUTRIENTS]
ALL_REQUIRED_KEYS = set(DB_NUTRIENTS + ["biotin_ug", "chloride_mg", "iodine_ug", "vitamin_a_iu", "vitamin_d3_iu", "vitamin_e_iu", "vitamin_k_ug"])

MISSING_ANOMALY_MAP = {
    "methionine_plus_cystine_g": "REF_MISSING_MET_CYS",
    "phenylalanine_plus_tyrosine_g": "REF_MISSING_PHE_TYR",
    "ala_alpha_linolenic_acid_g": "REF_MISSING_ALA",
    "ara_arachidonic_acid_g": "REF_MISSING_ARA",
    "epa_plus_dha_g": "REF_MISSING_EPA_DHA",
    "chloride_mg": "REF_MISSING_CHLORIDE",
    "iodine_ug": "REF_MISSING_IODINE",
    "vitamin_a_iu": "REF_MISSING_VIT_A",
    "vitamin_d3_iu": "REF_MISSING_VIT_D3",
    "vitamin_e_iu": "REF_MISSING_VIT_E",
    "vitamin_k_ug": "REF_MISSING_VIT_K",
    "biotin_ug": "REF_MISSING_BIOTIN",
    "folic_acid_b9_ug": "REF_MISSING_FOLATE",
    "choline_mg": "REF_MISSING_CHOLINE",
}
DEFAULT_MISSING_ANOMALY = "REF_EXTRACTION_COMPLETE"
NA_ANOMALY = "REF_FORMULATION_RULES_EXCLUSION"

INGREDIENT_USDA_REF = {
    "beef_muscle_raw": "REF_USDA_FDC_170196", "beef_lung_raw": "REF_USDA_FDC_170197",
    "beef_foot_tendon_raw": "REF_USDA_FDC_26002576", "beef_tail_raw": "REF_USDA_FDC_170199",
    "beef_tongue_raw": "REF_USDA_FDC_170200", "beef_blood_raw": "REF_USDA_FDC_54115122",
    "beef_heart_raw": "REF_USDA_FDC_170202", "beef_green_tripe_raw": "REF_USDA_FDC_170203",
    "beef_liver_raw": "REF_USDA_FDC_169451", "beef_kidney_raw": "REF_USDA_FDC_170205",
    "beef_spleen_raw": "REF_USDA_FDC_170206", "chicken_muscle_raw": "REF_USDA_FDC_168625",
    "chicken_heart_raw": "REF_USDA_FDC_168626", "chicken_liver_raw": "REF_USDA_FDC_168627",
    "chicken_kidney_raw": "REF_USDA_FDC_168628", "chicken_foot_tendon_raw": "REF_USDA_FDC_168629",
    "chicken_blood_raw": "REF_USDA_FDC_168630", "pork_muscle_raw": "REF_USDA_FDC_171640",
    "pork_liver_raw": "REF_USDA_FDC_171641", "salmon_atlantic_raw": "REF_USDA_FDC_172156",
}

SUPPLEMENT_SOURCED = {"biotin_ug", "chloride_mg", "iodine_ug", "vitamin_a_iu", "vitamin_d3_iu", "vitamin_e_iu", "vitamin_k_ug"}

ALL_REQUIRED_KEYS = set(
    [UNIT_RENAME.get(n, n) for n in [
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
    ]] + ["biotin_ug", "chloride_mg", "iodine_ug", "vitamin_a_iu", "vitamin_d3_iu", "vitamin_e_iu", "vitamin_k_ug"]
)

MISSING_ANOMALY_MAP = {
    "methionine_plus_cystine_g": "REF_MISSING_MET_CYS",
    "phenylalanine_plus_tyrosine_g": "REF_MISSING_PHE_TYR",
    "ala_alpha_linolenic_acid_g": "REF_MISSING_ALA",
    "ara_arachidonic_acid_g": "REF_MISSING_ARA",
    "epa_plus_dha_g": "REF_MISSING_EPA_DHA",
    "chloride_mg": "REF_MISSING_CHLORIDE",
    "iodine_ug": "REF_MISSING_IODINE",
    "vitamin_a_iu": "REF_MISSING_VIT_A",
    "vitamin_d3_iu": "REF_MISSING_VIT_D3",
    "vitamin_e_iu": "REF_MISSING_VIT_E",
    "vitamin_k_ug": "REF_MISSING_VIT_K",
    "biotin_ug": "REF_MISSING_BIOTIN",
    "folic_acid_b9_ug": "REF_MISSING_FOLATE",
    "choline_mg": "REF_MISSING_CHOLINE",
}
DEFAULT_MISSING_ANOMALY = "REF_EXTRACTION_COMPLETE"
NA_ANOMALY = "REF_FORMULATION_RULES_EXCLUSION"

SUPPLEMENT_SOURCED = {"biotin_ug", "chloride_mg", "iodine_ug", "vitamin_a_iu", "vitamin_d3_iu", "vitamin_e_iu", "vitamin_k_ug"}

ALL_REQUIRED_KEYS = set(
    [{"calcium_g": "calcium_mg", "phosphorus_g": "phosphorus_mg", "magnesium_g": "magnesium_mg",
      "sodium_g": "sodium_mg", "potassium_g": "potassium_mg", "chloride_g": "chloride_mg",
      "choline_g": "choline_mg", "selenium_mg": "selenium_ug", "cobalamin_b12_mg": "cobalamin_b12_ug",
      "folic_acid_b9_mg": "folic_acid_b9_ug", "iodine_mg": "iodine_ug"}.get(n, n)
     for n in [
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
    ]] + ["biotin_ug", "chloride_mg", "iodine_ug", "vitamin_a_iu", "vitamin_d3_iu", "vitamin_e_iu", "vitamin_k_ug"]
)

MISSING_ANOMALY_MAP = {
    "methionine_plus_cystine_g": "REF_MISSING_MET_CYS",
    "phenylalanine_plus_tyrosine_g": "REF_MISSING_PHE_TYR",
    "ala_alpha_linolenic_acid_g": "REF_MISSING_ALA",
    "ara_arachidonic_acid_g": "REF_MISSING_ARA",
    "epa_plus_dha_g": "REF_MISSING_EPA_DHA",
    "chloride_mg": "REF_MISSING_CHLORIDE",
    "iodine_ug": "REF_MISSING_IODINE",
    "vitamin_a_iu": "REF_MISSING_VIT_A",
    "vitamin_d3_iu": "REF_MISSING_VIT_D3",
    "vitamin_e_iu": "REF_MISSING_VIT_E",
    "vitamin_k_ug": "REF_MISSING_VIT_K",
    "biotin_ug": "REF_MISSING_BIOTIN",
    "folic_acid_b9_ug": "REF_MISSING_FOLATE",
    "choline_mg": "REF_MISSING_CHOLINE",
}
DEFAULT_MISSING_ANOMALY = "REF_EXTRACTION_COMPLETE"
NA_ANOMALY = "REF_FORMULATION_RULES_EXCLUSION"

SUPPLEMENT_SOURCED = {"biotin_ug", "chloride_mg", "iodine_ug", "vitamin_a_iu", "vitamin_d3_iu", "vitamin_e_iu", "vitamin_k_ug"}

INGREDIENT_USDA_REF = {
    "beef_muscle_raw": "REF_USDA_FDC_170196", "beef_lung_raw": "REF_USDA_FDC_170197",
    "beef_foot_tendon_raw": "REF_USDA_FDC_26002576", "beef_tail_raw": "REF_USDA_FDC_170199",
    "beef_tongue_raw": "REF_USDA_FDC_170200", "beef_blood_raw": "REF_USDA_FDC_54115122",
    "beef_heart_raw": "REF_USDA_FDC_170202", "beef_green_tripe_raw": "REF_USDA_FDC_170203",
    "beef_liver_raw": "REF_USDA_FDC_169451", "beef_kidney_raw": "REF_USDA_FDC_170205",
    "beef_spleen_raw": "REF_USDA_FDC_170206", "chicken_muscle_raw": "REF_USDA_FDC_168625",
    "chicken_heart_raw": "REF_USDA_FDC_168626", "chicken_liver_raw": "REF_USDA_FDC_168627",
    "chicken_kidney_raw": "REF_USDA_FDC_168628", "chicken_foot_tendon_raw": "REF_USDA_FDC_168629",
    "chicken_blood_raw": "REF_USDA_FDC_168630", "pork_muscle_raw": "REF_USDA_FDC_171640",
    "pork_liver_raw": "REF_USDA_FDC_171641", "salmon_atlantic_raw": "REF_USDA_FDC_172156",
}

ALL_REQUIRED_KEYS = set(
    [UNIT_RENAME.get(n, n) for n in [
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
    ]] + ["biotin_ug", "chloride_mg", "iodine_ug", "vitamin_a_iu", "vitamin_d3_iu", "vitamin_e_iu", "vitamin_k_ug"]
)

SUPPLEMENT_SOURCED = {"biotin_ug", "chloride_mg", "iodine_ug", "vitamin_a_iu", "vitamin_d3_iu", "vitamin_e_iu", "vitamin_k_ug"}

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def convert_entry(entry):
    """Convert old-format nutrient entry to new 3-state 'measured'."""
    new_entry = {
        "status": "measured",
        "value": entry.get("value"),
        "unit": entry.get("unit"),
        "basis": entry.get("basis", "as_fed"),
        "source_ref": entry.get("source_ref"),
    }
    for opt in ["confidence", "note", "estimation_note"]:
        if opt in entry:
            new_entry[opt] = entry[opt]
    return new_entry

def create_missing(key):
    return {
        "status": "missing",
        "value": None,
        "reason": "not measured in USDA FDC for this ingredient",
        "anomaly_ref": MISSING_ANOMALY_MAP.get(key, "REF_EXTRACTION_COMPLETE")
    }

def create_na(key):
    return {
        "status": "not_applicable",
        "value": None,
        "reason": "sourced from supplement/fortification; excluded from as_fed matrix per formulation_rules",
        "anomaly_ref": "REF_FORMULATION_RULES_EXCLUSION"
    }

def migrate():
    print("Loading DB...")
    db = load_json(DB_PATH)
    
    # Backup
    save_json(db, BACKUP_PATH)
    print(f"Backed up to {BACKUP_PATH}")
    
    SUPPLEMENT_SOURCED = {"biotin_ug", "chloride_mg", "iodine_ug", "vitamin_a_iu", "vitamin_d3_iu", "vitamin_e_iu", "vitamin_k_ug"}
    
    # Migrate each ingredient
    for group in db.get("protein_sources", {}).values():
        for ing in group.get("ingredients", []):
            iid = ing.get("ingredient_id")
            bp = ing.get("bromatological_profile", {})
            old_nutrients = bp.get("nutrients", {})
            excluded = bp.get("coverage_excluded_nutrients", [])
            excluded_set = set(excluded)
            
            new_nutrients = {}
            
            # Process ALL required keys for this ingredient
            for key in ALL_REQUIRED_KEYS:
                in_old = key in old_nutrients
                in_excluded = key in set(bp.get("coverage_excluded_nutrients", []))
                
                if key in old_nutrients:
                    old_val = old_nutrients[key].get("value")
                    if old_nutrients[key].get("value") is None:
                        # Original data had null value → missing
                        new_nutrients[key] = create_missing(key)
                    elif key in {"biotin_ug", "chloride_mg", "iodine_ug", "vitamin_a_iu", "vitamin_d3_iu", "vitamin_e_iu", "vitamin_k_ug"}:
                        # Supplement-sourced per formulation_rules → not_applicable
                        new_nutrients[key] = create_na(key)
                    elif key in set(bp.get("coverage_excluded_nutrients", [])):
                        # Has USDA value but explicitly excluded for this ingredient → missing with specific reason
                        new_nutrients[key] = {
                            "status": "missing",
                            "value": None,
                            "reason": "below detection limit / highly variable in USDA FDC for this ingredient",
                            "anomaly_ref": MISSING_ANOMALY_MAP.get(key, "REF_EXTRACTION_COMPLETE")
                        }
                    else:
                        # Has real USDA value and not excluded → measured
                        new_nutrients[key] = convert_entry(old_nutrients[key])
                elif key in set(bp.get("coverage_excluded_nutrients", [])):
                    # Explicitly excluded for this ingredient
                    if key in {"biotin_ug", "chloride_mg", "iodine_ug", "vitamin_a_iu", "vitamin_d3_iu", "vitamin_e_iu", "vitamin_k_ug"}:
                        new_nutrients[key] = create_na(key)
                    else:
                        new_nutrients[key] = {
                            "status": "missing",
                            "value": None,
                            "reason": "below detection limit / highly variable in USDA FDC for this ingredient",
                            "anomaly_ref": MISSING_ANOMALY_MAP.get(key, "REF_EXTRACTION_COMPLETE")
                        }
                else:
                    # In required set but not in USDA data → missing
                    new_nutrients[key] = create_missing(key)
            
            # Assign correct refs
            usda_ref = INGREDIENT_USDA_REF.get(iid, "REF_USDA_FDC_170196")
            for key, entry in new_nutrients.items():
                if entry["status"] == "measured":
                    entry["source_ref"] = INGREDIENT_USDA_REF.get(iid, "REF_USDA_FDC_170196")
                elif entry["status"] == "missing":
                    entry["anomaly_ref"] = MISSING_ANOMALY_MAP.get(key, "REF_EXTRACTION_COMPLETE")
                elif entry["status"] == "not_applicable":
                    entry["anomaly_ref"] = "REF_FORMULATION_RULES_EXCLUSION"
            
            bp["nutrients"] = new_nutrients
            bp["coverage_excluded_nutrients"] = bp.get("coverage_excluded_nutrients", [])
    
    # Update metadata
    db["_db_metadata"]["version"] = "3.1.0"
    db["_db_metadata"]["nutrients_per_ingredient"] = len(ALL_REQUIRED_KEYS)
    db["_db_metadata"]["last_updated"] = "2026-07-13"
    db["_db_metadata"]["note"] = "Migrated to 3-state nutrient contract using PER-INGREDIENT excluded lists. Each nutrient has explicit status (measured/missing/not_applicable). coverage_excluded_nutrients kept for backward compat."
    
    # Save
    save_json(db, DB_PATH)
    print(f"Saved migrated DB to {DB_PATH}")
    
    # Verify
    total = measured = missing = na = 0
    for group in db["protein_sources"].values():
        for ing in group.get("ingredients", []):
            for entry in ing["bromatological_profile"]["nutrients"].values():
                total += 1
                if entry["status"] == "measured": measured += 1
                elif entry["status"] == "missing": missing += 1
                elif entry["status"] == "not_applicable": na += 1
    
    print(f"Total entries: {total}")
    print(f"  measured: {measured}")
    print(f"  missing: {missing}")
    print(f"  not_applicable: {na}")
    print(f"  Ingredients: {sum(len(g.get('ingredients', [])) for g in db['protein_sources'].values())}")
    print(f"  Keys per ingredient: {total // 20}")

if __name__ == "__main__":
    migrate()