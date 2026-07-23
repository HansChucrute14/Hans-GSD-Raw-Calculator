#!/usr/bin/env python3
"""
Fix chicken_back_raw and chicken_neck_raw FDC ID assignments and recalculate micronutrients.

The bug:
- chicken_back_raw uses FDC 172382 (neck) — should use FDC 171469 (back)
- chicken_neck_raw uses FDC 171047 (giblets+neck) — should use FDC 172382 (neck)

Methodology:
- Protein, fat, Ca, P come from DogsFirst.ie / Monica Segal (bone-in) — DON'T change
- All other micronutrients use FDC data × meat fraction — recalculate with correct FDC base
- Meat fractions: back=56%, neck=64%
- FDC values are for meat+skin only (no bone)
"""

import json
import sys
from pathlib import Path

# FDC nutrient data (per 100g, meat+skin, raw)
# FDC 171469 = Chicken, broilers or fryers, back, meat and skin, raw
FDC_171469 = {
    "potassium_mg": 144.0,
    "sodium_mg": 64.0,
    "magnesium_mg": 15.0,
    "iron_mg": 0.94,
    "zinc_mg": 1.26,
    "copper_mg": 0.047,
    "manganese_mg": 0.018,
    "selenium_ug": 12.1,
    "vitamin_a_iu": 251.0,
    "vitamin_d3_iu": 0.0,  # Not in FDC response, estimate
    "vitamin_e_iu": 0.37,
    "thiamine_b1_mg": 0.051,
    "riboflavin_b2_mg": 0.116,
    "niacin_b3_mg": 4.835,
    "pantothenic_acid_b5_mg": 0.819,
    "pyridoxine_b6_mg": 0.190,
    "folic_acid_b9_ug": 6.0,
    "cobalamin_b12_ug": 0.25,
    "choline_mg": 0.0,  # Not in FDC response, estimate
    "linoleic_acid_g": 5.58,
    "ala_alpha_linolenic_acid_g": 0.28,
    "epa_plus_dha_g": 0.04,  # EPA 0.01 + DHA 0.03
    "ara_arachidonic_acid_g": 0.10,
    "methionine_g": 0.361,
    "lysine_g": 1.102,
    "leucine_g": 0.995,
    "isoleucine_g": 0.667,
    "valine_g": 0.670,
    "tryptophan_g": 0.151,
    "phenylalanine_g": 0.536,
    "threonine_g": 0.570,
    "arginine_g": 0.909,
    "histidine_g": 0.393,
    "cystine_g": 0.194,  # For Met+Cys calculation
    "tyrosine_g": 0.434,  # For Phe+Tyr calculation
}

# FDC 172382 = Chicken, broilers or fryers, neck, meat and skin, raw
FDC_172382 = {
    "potassium_mg": 137.0,
    "sodium_mg": 64.0,
    "magnesium_mg": 13.0,
    "iron_mg": 1.90,
    "zinc_mg": 1.86,
    "copper_mg": 0.080,
    "manganese_mg": 0.033,
    "selenium_ug": 12.0,
    "vitamin_a_iu": 216.0,
    "vitamin_d3_iu": 0.0,  # Not in FDC response, estimate
    "vitamin_e_iu": 0.30,
    "thiamine_b1_mg": 0.047,
    "riboflavin_b2_mg": 0.191,
    "niacin_b3_mg": 3.608,
    "pantothenic_acid_b5_mg": 0.850,
    "pyridoxine_b6_mg": 0.170,
    "folic_acid_b9_ug": 5.0,
    "cobalamin_b12_ug": 0.26,
    "choline_mg": 0.0,  # Not in FDC response, estimate
    "linoleic_acid_g": 5.04,
    "ala_alpha_linolenic_acid_g": 0.21,
    "epa_plus_dha_g": 0.05,  # EPA 0.02 + DHA 0.03
    "ara_arachidonic_acid_g": 0.16,
    "methionine_g": 0.332,
    "lysine_g": 1.005,
    "leucine_g": 0.933,
    "isoleucine_g": 0.588,
    "valine_g": 0.641,
    "tryptophan_g": 0.137,
    "phenylalanine_g": 0.514,
    "threonine_g": 0.545,
    "arginine_g": 0.975,
    "histidine_g": 0.348,
    "cystine_g": 0.209,  # For Met+Cys calculation
    "tyrosine_g": 0.392,  # For Phe+Tyr calculation
}

# Meat fractions (bone-in RMB)
MEAT_FRACTIONS = {
    "chicken_back_raw": 0.56,  # bone = 44%
    "chicken_neck_raw": 0.64,  # bone = 36%
}

# Source ref mappings
SOURCE_REF_MAP = {
    "chicken_back_raw": {
        "old": "REF_USDA_FDC_172382",
        "new": "REF_USDA_FDC_171469",
    },
    "chicken_neck_raw": {
        "old": "REF_USDA_FDC_171047",
        "new": "REF_USDA_FDC_172382",
    },
}

# Nutrients that come from DogsFirst.ie / Monica Segal (bone-in) — DON'T recalculate
SKIP_NUTRIENTS = {"protein_g", "fat_g", "calcium_mg", "phosphorus_mg"}

# Nutrients that are estimated zero or not applicable — DON'T recalculate
ESTIMATED_ZERO_NUTRIENTS = {"biotin_ug", "iodine_ug", "chloride_mg", "vitamin_k_ug"}


def recalculate_nutrient(nutrient_id, fdc_value, meat_fraction):
    """Recalculate a nutrient value using FDC base × meat fraction."""
    if fdc_value is None or fdc_value == 0:
        return None
    return round(fdc_value * meat_fraction, 4)


def fix_ingredient(ingredient, fdc_data, meat_fraction, new_source_ref):
    """Fix source_refs and recalculate micronutrients for an ingredient."""
    nutrients = ingredient["bromatological_profile"]["nutrients"]
    changes = []
    
    for nutrient_id, nutrient_data in nutrients.items():
        # Skip nutrients that don't use FDC data
        if nutrient_id in SKIP_NUTRIENTS or nutrient_id in ESTIMATED_ZERO_NUTRIENTS:
            continue
        
        # Skip nutrients that don't have source_ref (e.g., not_applicable)
        if "source_ref" not in nutrient_data:
            continue
        
        # Only recalculate nutrients that use the old FDC ref
        old_ref = SOURCE_REF_MAP[ingredient["ingredient_id"]]["old"]
        if nutrient_data["source_ref"] != old_ref:
            continue
        
        # Get FDC value for this nutrient
        fdc_value = fdc_data.get(nutrient_id)
        if fdc_value is None:
            # Some nutrients not in FDC response, keep existing value
            continue
        
        # Special handling for composite amino acids
        if nutrient_id == "methionine_plus_cystine_g":
            met = fdc_data.get("methionine_g", 0)
            cys = fdc_data.get("cystine_g", 0)
            new_value = round((met + cys) * meat_fraction, 4)
        elif nutrient_id == "phenylalanine_plus_tyrosine_g":
            phe = fdc_data.get("phenylalanine_g", 0)
            tyr = fdc_data.get("tyrosine_g", 0)
            new_value = round((phe + tyr) * meat_fraction, 4)
        elif nutrient_id == "epa_plus_dha_g":
            epa = fdc_data.get("epa_g", 0) or 0.01  # Estimate if missing
            dha = fdc_data.get("dha_g", 0) or 0.03  # Estimate if missing
            new_value = round((epa + dha) * meat_fraction, 4)
        else:
            new_value = recalculate_nutrient(nutrient_id, fdc_value, meat_fraction)
        
        if new_value is not None:
            old_value = nutrient_data.get("value")
            nutrient_data["value"] = new_value
            nutrient_data["source_ref"] = new_source_ref
            nutrient_data["note"] = f"USDA FDC {new_source_ref.split('_')[-1]} × {meat_fraction:.0%} meat fraction (recalculated from correct FDC base)"
            changes.append({
                "nutrient": nutrient_id,
                "old_value": old_value,
                "new_value": new_value,
                "old_ref": old_ref,
                "new_ref": new_source_ref,
            })
    
    return changes


def main():
    # Load DB
    db_path = Path(__file__).resolve().parent.parent.parent / "data" / "DB_ingredientes.json"
    with open(db_path, "r", encoding="utf-8") as f:
        db = json.load(f)
    
    all_changes = []
    
    # Process each ingredient
    for group in db["protein_sources"].values():
        for ingredient in group.get("ingredients", []):
            iid = ingredient["ingredient_id"]
            if iid not in SOURCE_REF_MAP:
                continue
            
            # Get FDC data and meat fraction
            fdc_id = SOURCE_REF_MAP[iid]["new"]
            fdc_data = FDC_171469 if fdc_id == "REF_USDA_FDC_171469" else FDC_172382
            meat_fraction = MEAT_FRACTIONS[iid]
            new_ref = SOURCE_REF_MAP[iid]["new"]
            
            # Fix ingredient
            changes = fix_ingredient(ingredient, fdc_data, meat_fraction, new_ref)
            all_changes.extend([(iid, c) for c in changes])
            
            print(f"\n{'='*60}")
            print(f"Ingredient: {iid}")
            print(f"Old FDC ref: {SOURCE_REF_MAP[iid]['old']}")
            print(f"New FDC ref: {new_ref}")
            print(f"Meat fraction: {meat_fraction:.0%}")
            print(f"Changes: {len(changes)}")
            for c in changes:
                print(f"  {c['nutrient']}: {c['old_value']} → {c['new_value']}")
    
    # Save updated DB
    backup_path = db_path.with_suffix(".json.backup-fdc-fix")
    if not backup_path.exists():
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"\nBackup saved to: {backup_path}")
    
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"Total changes: {len(all_changes)}")
    print(f"Updated DB saved to: {db_path}")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY:")
    for iid in SOURCE_REF_MAP:
        changes_for_ingredient = [c for i, c in all_changes if i == iid]
        print(f"  {iid}: {len(changes_for_ingredient)} nutrients recalculated")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
