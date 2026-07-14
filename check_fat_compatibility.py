"""
Compatibility Check: beef_fat_raw.json, chicken_fat_raw.json, pork_fat_raw.json vs DB_ingredientes schema
Checks all structural and semantic inconsistencies.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple

# Define all 43 required nutrients based on schema
REQUIRED_NUTRIENTS = [
    "protein_g", "fat_g", "arginine_g", "histidine_g", "isoleucine_g", "leucine_g",
    "lysine_g", "methionine_g", "phenylalanine_g", "threonine_g", "tryptophan_g",
    "valine_g", "linoleic_acid_g", "ala_alpha_linolenic_acid_g", "epa_plus_dha_g",
    "ara_arachidonic_acid_g", "calcium_mg", "phosphorus_mg", "potassium_mg",
    "sodium_mg", "magnesium_mg", "iron_mg", "zinc_mg", "copper_mg", "manganese_mg",
    "selenium_ug", "iodine_ug", "vitamin_a_iu", "vitamin_d3_iu", "vitamin_e_iu",
    "vitamin_k_ug", "thiamine_b1_mg", "riboflavin_b2_mg", "niacin_b3_mg",
    "pantothenic_acid_b5_mg", "pyridoxine_b6_mg", "folic_acid_b9_ug",
    "cobalamin_b12_ug", "choline_mg", "chloride_mg", "biotin_ug",
    "methionine_plus_cystine_g", "phenylalanine_plus_tyrosine_g"
]

VALID_UNITS = {
    "protein_g": "g", "fat_g": "g", "arginine_g": "g", "histidine_g": "g",
    "isoleucine_g": "g", "leucine_g": "g", "lysine_g": "g", "methionine_g": "g",
    "phenylalanine_g": "g", "threonine_g": "g", "tryptophan_g": "g", "valine_g": "g",
    "linoleic_acid_g": "g", "ala_alpha_linolenic_acid_g": "g", "epa_plus_dha_g": "g",
    "ara_arachidonic_acid_g": "g", "calcium_mg": "mg", "phosphorus_mg": "mg",
    "potassium_mg": "mg", "sodium_mg": "mg", "magnesium_mg": "mg", "iron_mg": "mg",
    "zinc_mg": "mg", "copper_mg": "mg", "manganese_mg": "mg", "selenium_ug": "ug",
    "iodine_ug": "ug", "vitamin_a_iu": "IU", "vitamin_d3_iu": "IU", "vitamin_e_iu": "IU",
    "vitamin_k_ug": "ug", "thiamine_b1_mg": "mg", "riboflavin_b2_mg": "mg",
    "niacin_b3_mg": "mg", "pantothenic_acid_b5_mg": "mg", "pyridoxine_b6_mg": "mg",
    "folic_acid_b9_ug": "ug", "cobalamin_b12_ug": "ug", "choline_mg": "mg",
    "chloride_mg": "mg", "biotin_ug": "ug", "methionine_plus_cystine_g": "g",
    "phenylalanine_plus_tyrosine_g": "g"
}

VALID_CONFIDENCE = ["measured", "estimated", "inferred", "extrapolated", "interpolated"]
VALID_CATEGORIES = [
    "muscle_meat", "muscle_organ", "organ_secreting", "organ_non_secreting",
    "connective_tissue", "blood_source", "fish", "bone", "cartilage", "fat_source",
    "supplement", "grain", "vegetable", "fruit", "dairy", "egg"
]


class CompatibilityChecker:
    def __init__(self):
        self.errors = []
        self.warnings = []
        
    def check_file(self, filepath: str) -> Tuple[List[str], List[str]]:
        """Check a single raw fat file for compatibility issues."""
        self.errors = []
        self.warnings = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"JSON Parse Error: {e}")
            return self.errors, self.warnings
        except FileNotFoundError:
            self.errors.append(f"File not found: {filepath}")
            return self.errors, self.warnings
            
        if not isinstance(data, list) or len(data) == 0:
            self.errors.append("Root must be a non-empty array")
            return self.errors, self.warnings
            
        ingredient = data[0]
        self._check_ingredient_structure(ingredient)
        
        return self.errors, self.warnings
    
    def _check_ingredient_structure(self, ing: Dict):
        """Check top-level ingredient structure."""
        # Required top-level fields
        required_fields = [
            "ingredient_id", "display_name", "category", "requires_cooking",
            "bromatological_profile", "metadata", "lp_constraints"
        ]
        
        for field in required_fields:
            if field not in ing:
                self.errors.append(f"MISSING REQUIRED FIELD: {field}")
        
        # Check ingredient_id format
        if "ingredient_id" in ing:
            ing_id = ing["ingredient_id"]
            if not ing_id.islower() or not all(c.isalnum() or c == '_' for c in ing_id):
                self.errors.append(f"INVALID ingredient_id format: '{ing_id}' (must be lowercase alphanumeric + underscore)")
        
        # Check category
        if "category" in ing:
            if ing["category"] not in VALID_CATEGORIES:
                self.errors.append(f"INVALID category: '{ing['category']}' (not in schema enum)")
        
        # Check requires_cooking type
        if "requires_cooking" in ing:
            if not isinstance(ing["requires_cooking"], bool):
                self.errors.append(f"INVALID requires_cooking: must be boolean, got {type(ing['requires_cooking'])}")
        
        # Check bromatological_profile
        if "bromatological_profile" in ing:
            self._check_bromatological_profile(ing["bromatological_profile"])
        
        # Check bioavailability_factors (optional but should have structure)
        if "bioavailability_factors" in ing:
            self._check_bioavailability_factors(ing["bioavailability_factors"])
        
        # Check lp_constraints
        if "lp_constraints" in ing:
            self._check_lp_constraints(ing["lp_constraints"])
        
        # Check metadata
        if "metadata" in ing:
            self._check_metadata(ing["metadata"])
        
        # Check safety_alerts (optional but should have structure)
        if "safety_alerts" in ing:
            self._check_safety_alerts(ing["safety_alerts"])
    
    def _check_bromatological_profile(self, profile: Dict):
        """Check bromatological profile structure."""
        if "basis" not in profile:
            self.errors.append("MISSING bromatological_profile.basis")
        elif profile["basis"] != "as_fed":
            self.errors.append(f"INVALID basis: '{profile['basis']}' (must be 'as_fed')")
        
        if "reference_mass_g" not in profile:
            self.errors.append("MISSING bromatological_profile.reference_mass_g")
        elif profile["reference_mass_g"] != 100:
            self.errors.append(f"INVALID reference_mass_g: {profile['reference_mass_g']} (must be 100)")
        
        if "nutrients" not in profile:
            self.errors.append("MISSING bromatological_profile.nutrients")
            return
        
        nutrients = profile["nutrients"]
        
        # Check for missing required nutrients
        present_nutrients = set(nutrients.keys())
        missing_nutrients = set(REQUIRED_NUTRIENTS) - present_nutrients
        
        # Check if missing nutrients are in coverage_excluded_nutrients
        excluded = set(profile.get("coverage_excluded_nutrients", []))
        
        for nutrient in missing_nutrients:
            if nutrient in excluded:
                self.warnings.append(
                    f"SCHEMA VIOLATION: '{nutrient}' is in coverage_excluded_nutrients but MUST be in nutrients with status='missing' or 'not_applicable' (v10.4 3-state contract)"
                )
            else:
                self.errors.append(
                    f"MISSING REQUIRED NUTRIENT: '{nutrient}' (must be present with status='measured', 'missing', or 'not_applicable')"
                )
        
        # Check extra nutrients not in schema
        extra_nutrients = present_nutrients - set(REQUIRED_NUTRIENTS)
        for nutrient in extra_nutrients:
            self.warnings.append(f"EXTRA NUTRIENT: '{nutrient}' (not in schema's 43 required nutrients)")
        
        # Check each nutrient entry structure
        for nutrient_key, nutrient_data in nutrients.items():
            self._check_nutrient_entry(nutrient_key, nutrient_data)
        
        # Deprecated field warning
        if "coverage_excluded_nutrients" in profile:
            self.warnings.append(
                "DEPRECATED: 'coverage_excluded_nutrients' is deprecated in v10.4. All nutrients must appear in 'nutrients' with explicit status."
            )
    
    def _check_nutrient_entry(self, key: str, data: Dict):
        """Check individual nutrient entry structure."""
        # Check for old structure (no status field)
        if "status" not in data:
            self.errors.append(
                f"SCHEMA VIOLATION [{key}]: MISSING 'status' field. v10.4 requires status='measured', 'missing', or 'not_applicable'"
            )
            # Still check old structure for completeness
            if "value" not in data:
                self.errors.append(f"MISSING value in nutrient '{key}'")
            if "unit" not in data:
                self.errors.append(f"MISSING unit in nutrient '{key}'")
            if "basis" not in data:
                self.errors.append(f"MISSING basis in nutrient '{key}'")
            elif data["basis"] != "as_fed":
                self.errors.append(f"INVALID basis in '{key}': '{data['basis']}' (must be 'as_fed')")
            if "source_ref" not in data:
                self.errors.append(f"MISSING source_ref in nutrient '{key}'")
            elif not data["source_ref"].startswith("REF_"):
                self.errors.append(f"INVALID source_ref in '{key}': '{data['source_ref']}' (must start with 'REF_')")
            if "confidence" in data and data["confidence"] not in VALID_CONFIDENCE:
                self.errors.append(f"INVALID confidence in '{key}': '{data['confidence']}' (not in schema enum)")
        
        # Check unit mismatch
        if "unit" in data and key in VALID_UNITS:
            expected_unit = VALID_UNITS[key]
            if data["unit"] != expected_unit:
                self.errors.append(
                    f"UNIT MISMATCH [{key}]: expected '{expected_unit}', got '{data['unit']}'"
                )
    
    def _check_bioavailability_factors(self, factors: Dict):
        """Check bioavailability factors structure."""
        if not isinstance(factors, dict):
            self.errors.append("bioavailability_factors must be an object")
        # Schema allows mixed types, just structural check
    
    def _check_lp_constraints(self, constraints: Dict):
        """Check LP constraints structure."""
        required = ["min_inclusion_pct", "max_inclusion_pct", "basis"]
        for field in required:
            if field not in constraints:
                self.errors.append(f"MISSING lp_constraints.{field}")
        
        if "basis" in constraints and constraints["basis"] != "as_fed":
            self.errors.append(f"INVALID lp_constraints.basis: '{constraints['basis']}' (must be 'as_fed')")
        
        if "min_inclusion_pct" in constraints:
            if not isinstance(constraints["min_inclusion_pct"], (int, float)) or constraints["min_inclusion_pct"] < 0:
                self.errors.append("INVALID min_inclusion_pct: must be number >= 0")
        
        if "max_inclusion_pct" in constraints:
            if not isinstance(constraints["max_inclusion_pct"], (int, float)) or constraints["max_inclusion_pct"] < 0:
                self.errors.append("INVALID max_inclusion_pct: must be number >= 0")
    
    def _check_metadata(self, metadata: Dict):
        """Check metadata structure against OLD schema (raw files don't use new schema)."""
        # The raw files use different metadata keys than the DB schema
        # Just check for presence of some metadata
        if not isinstance(metadata, dict):
            self.errors.append("metadata must be an object")
            return
        
        # Check for common metadata fields
        if "source_citation" in metadata:
            if not isinstance(metadata["source_citation"], str):
                self.errors.append("metadata.source_citation must be string")
        
        if "evidence_tier" in metadata:
            if not isinstance(metadata["evidence_tier"], str):
                self.errors.append("metadata.evidence_tier must be string")
    
    def _check_safety_alerts(self, alerts: list):
        """Check safety alerts structure."""
        if not isinstance(alerts, list):
            self.errors.append("safety_alerts must be an array")
            return
        
        for idx, alert in enumerate(alerts):
            if not isinstance(alert, dict):
                self.errors.append(f"safety_alerts[{idx}] must be an object")
                continue
            
            # Check for expected fields (schema uses different keys)
            if "type" not in alert:
                self.warnings.append(f"safety_alerts[{idx}] missing 'type' field")
            if "risk" not in alert and "message" not in alert:
                self.warnings.append(f"safety_alerts[{idx}] missing 'risk' or 'message' field")


def main():
    """Run compatibility check on all three fat files."""
    base_path = Path(__file__).parent
    files = [
        "beef_fat_raw.json",
        "chicken_fat_raw.json",
        "pork_fat_raw.json"
    ]
    
    checker = CompatibilityChecker()
    
    print("=" * 80)
    print("GSD DIET CALC v10.4 - FAT FILES COMPATIBILITY CHECK")
    print("=" * 80)
    print()
    
    total_errors = 0
    total_warnings = 0
    
    for filename in files:
        filepath = base_path / filename
        print(f"\n{'=' * 80}")
        print(f"CHECKING: {filename}")
        print(f"{'=' * 80}")
        
        errors, warnings = checker.check_file(str(filepath))
        
        if not errors and not warnings:
            print("✓ NO ISSUES FOUND - Fully compatible with DB_ingredientes schema")
        else:
            if errors:
                print(f"\n❌ ERRORS ({len(errors)}):")
                print("-" * 80)
                for i, error in enumerate(errors, 1):
                    print(f"  {i}. {error}")
                total_errors += len(errors)
            
            if warnings:
                print(f"\n⚠️  WARNINGS ({len(warnings)}):")
                print("-" * 80)
                for i, warning in enumerate(warnings, 1):
                    print(f"  {i}. {warning}")
                total_warnings += len(warnings)
    
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total Errors:   {total_errors}")
    print(f"Total Warnings: {total_warnings}")
    
    if total_errors == 0 and total_warnings == 0:
        print("\n✓ ALL FILES ARE FULLY COMPATIBLE")
    elif total_errors == 0:
        print("\n⚠️  ALL FILES ARE STRUCTURALLY VALID BUT HAVE WARNINGS")
    else:
        print("\n❌ COMPATIBILITY ISSUES DETECTED - FILES NEED UPDATES")
    
    print()


if __name__ == "__main__":
    main()
