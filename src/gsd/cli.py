#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gsd.cli — CLI entry point extracted from build_pipeline.py."""

import json
import os
import re
import sys
from pathlib import Path

# Relative imports from package
from . import core
from . import nutrition
from . import solver
from . import mapa

# Re-export for compatibility (build_pipeline.py thin wrapper uses these)
from .core import (
    BASE_DIR, DATA_DIR, MAPA_FILENAME, MAPA_TEMP_FILENAME, JSON_FILES,
    load_all_jsons, sha256_file, AnimalInput, DerEnvelope,
)
from .nutrition import (
    validate_inputs, calculate_der_and_envelope, build_matrix,
)
from .solver import solve_cascade, validate_output, check_fat_source_adequacy
from .mapa import generate_mapa, validate_mapa, build_mapa_indices

# Global for --no-live-evidence flag
_NO_LIVE_EVIDENCE = False


def main():
    if len(sys.argv) < 2:
        print("Usage: build_pipeline.py [--generate-mapa | --gate-mapa | --audit-mapa | --validate-db | --runtime | --build-recipes]")
        sys.exit(1)

    mode = sys.argv[1]
    print(f"build_pipeline.py — mode={mode}")
    print(f"Working dir: {core.BASE_DIR}")
    print()

    if mode == "--generate-mapa":
        global _NO_LIVE_EVIDENCE
        _NO_LIVE_EVIDENCE = "--no-live-evidence" in sys.argv[2:]
        if _NO_LIVE_EVIDENCE:
            print("Note: --no-live-evidence set — section 18 will show skip marker")
        data = core.load_all_jsons()
        print(f"Loaded {len([k for k,v in data.items() if v])}/{len(core.JSON_FILES)} JSONs")

        # Read old MAPA's state hash before regeneration (for Check 13 comparison)
        old_state_hash = None
        old_mapa_path = core.BASE_DIR / core.MAPA_FILENAME
        if old_mapa_path.exists():
            try:
                old_content = old_mapa_path.read_text(encoding="utf-8")
                old_hash_match = re.search(r'\*\*State Hash:\*\*\s*`?([0-9a-f]{16})`?', old_content)
                if old_hash_match:
                    old_state_hash = old_hash_match.group(1)
            except Exception:
                pass

        mapa_content = mapa.generate_mapa(data)
        temp_path = core.BASE_DIR / core.MAPA_TEMP_FILENAME
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(mapa_content)
        size = temp_path.stat().st_size
        print(f"\nWritten: {temp_path.name} ({size:,} bytes)")

        # Run validation gate
        errors = mapa.validate_mapa(mapa_content, data, prev_state_hash=old_state_hash)
        if not errors:
            print(f"\nValidation gate: ALL CHECKS PASSED")
            final_path = core.BASE_DIR / core.MAPA_FILENAME
            if final_path.exists():
                old_sha = core.sha256_file(final_path)
                print(f"Current {core.MAPA_FILENAME}: SHA256={old_sha[:16]}...")
            os.replace(temp_path, final_path)
            new_sha = core.sha256_file(final_path)
            print(f"Atomic replace: {core.MAPA_FILENAME} (SHA256={new_sha[:16]}...)")
        else:
            print(f"\nValidation gate: {len(errors)} FAILURES:")
            for err in errors:
                print(f"  - {err}")
            print(f"\nTemp file retained at: {temp_path}")
            print("Fix issues and re-run --generate-mapa")
            sys.exit(1)

    elif mode == "--gate-mapa":
        data = core.load_all_jsons()
        mapa_path = core.BASE_DIR / core.MAPA_FILENAME
        if not mapa_path.exists():
            print(f"ERROR: {core.MAPA_FILENAME} not found. Run --generate-mapa first.")
            sys.exit(1)
        mapa_content = mapa_path.read_text(encoding="utf-8")
        errors = mapa.validate_mapa(mapa_content, data)
        if not errors:
            print("Validation gate: ALL CHECKS PASSED")
        else:
            print(f"Validation gate: {len(errors)} FAILURES:")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)

    elif mode == "--audit-mapa":
        data = core.load_all_jsons()
        idx = mapa.build_mapa_indices(data)
        print(f"CrossRefIndex built: {len(idx.all_known_tokens)} known tokens")
        print(f"  Ingredients: {len(idx.ingredient_index)}")
        print(f"  Nutrients: {len(idx.nutrient_index)}")
        print(f"  References: {len(idx.ref_index)}")
        print(f"  Constraints: {len(idx.constraint_index)}")
        print(f"  Weights: {len(idx.weight_index)}")
        print(f"  Scenarios: {len(idx.scenario_index)}")
        print(f"  DB->Solver renames: {len(idx.db2solver_name_map)}")
        print()
        mapa_path = core.BASE_DIR / core.MAPA_FILENAME
        if mapa_path.exists():
            mapa_content = mapa_path.read_text(encoding="utf-8")
            errors = mapa.validate_mapa(mapa_content, data)
            if not errors:
                print("Validation gate: ALL CHECKS PASSED")
            else:
                print(f"Validation gate: {len(errors)} FAILURES:")
                for err in errors:
                    print(f"  - {err}")
        else:
            print(f"{core.MAPA_FILENAME} not found - run --generate-mapa first")

    elif mode == "--validate-db":
        print("Validating DB_ingredientes.json against 3-state nutrient contract...")
        
        def load_json_local(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        
        db = load_json_local(core.DATA_DIR / "DB_ingredientes.json")
        schema = load_json_local(core.DATA_DIR / "db_ingredientes.schema.json")
        errors = []
        try:
            core.validate(instance=db, schema=schema)
        except core.ValidationError as e:
            errors.append(f"Schema validation failed at {'.'.join(str(x) for x in e.path)}: {e.message}")
        
        # Key completeness
        for group in db.get("protein_sources", {}).values():
            for ing in group.get("ingredients", []):
                bp = ing.get("bromatological_profile", {})
                nuts = bp.get("nutrients", {})
                for key in core.ALL_REQUIRED_KEYS:
                    if key not in nuts:
                        errors.append(f"Key completeness: {ing['ingredient_id']}: missing key '{key}'")
                    else:
                        entry = nuts[key]
                        if "status" not in entry:
                            errors.append(f"Key completeness: {ing['ingredient_id']}.{key}: no 'status' field")
                        elif entry["status"] not in ("measured", "missing", "not_applicable"):
                            errors.append(f"Key completeness: {ing['ingredient_id']}.{key}: invalid status '{entry['status']}'")
        
        # Source refs
        prov = load_json_local(core.DATA_DIR / "audit_provenance.json")
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
            total_ings = sum(len(g.get("ingredients", [])) for g in db.get("protein_sources", {}).values())
            print("VALIDATION PASSED: All " + str(total_ings) + " ingredients have complete 3-state nutrient entries with valid references.")

    elif mode == "--runtime":
        data = core.load_all_jsons()
        nutrition.validate_inputs(data)
        db = data.get("DB_ingredientes.json", {})

        # Build a default AnimalInput from the request JSON if provided
        req_path = core.DATA_DIR / "runtime_request.json"
        if req_path.exists():
            with open(req_path, "r", encoding="utf-8-sig") as f:
                req_data = json.load(f)
        else:
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

        animal = core.AnimalInput(**req_data.get("animal", {}))
        selected_ids = req_data.get("selected_ingredient_ids", [])
        scenario_id = req_data.get("scenario_id", "SCN_B_SLOW_GROWTH")

        # Step 3: compute DER + envelope
        growth = data.get("growth_energy_skeletal.json", {})
        der_env = nutrition.calculate_der_and_envelope(animal, growth, scenario_id, selected_ids, db)
        print(f"\n=== DER & Envelope ===")
        print(f"BW={der_env.bw_kg:.1f} kg, TER={der_env.ter_kcal:.0f} kcal, k={der_env.k_multiplier}")
        print(f"DER={der_env.der_kcal:.0f} kcal, units of 1000kcal={der_env.units_of_1000kcal:.3f}")
        print(f"Envelope: [{der_env.min_total_g:.0f}, {der_env.max_total_g:.0f}] g ({der_env.density_source})")

        # Step 4-5: convert and build matrix
        fr = data.get("formulation_rules.json", {})
        matrix = nutrition.build_matrix(selected_ids, db, fr)
        print(f"\n=== Built matrix for {len(matrix)} ingredients ===")
        for iid, vec in matrix.items():
            n = len(vec)
            measured = sum(1 for v in vec.values() if isinstance(v.get("value"), (int, float)))
            print(f"  {iid}: {n} nutrients ({measured} measured)")
            for k, v in list(vec.items())[:5]:
                print(f"    {k}: {v.get('value', 'N/A')}" if isinstance(v.get('value'), (int, float)) else f"    {k}: None")

        # Conditional adequacy check: fat source vs AAFCO fat minimum
        fat_gap = solver.check_fat_source_adequacy(matrix, selected_ids, fr, der_env, db)
        print(f"\n=== Conditional Adequacy Check ===")
        if fat_gap:
            print(f"  GAP DETECTED: fat_g at structural minimum = {fat_gap['estimated_fat_at_structural_min']:.1f} g/1000kcal (AAFCO min = {fat_gap['aafco_fat_min']})")
            print(f"  Fat source at structural minimum ({fat_gap['structural_min_pct']:.0f}%) yields {fat_gap['pct_of_min']:.1f}% of AAFCO minimum")
            print(f"  AAFCO-recommended fat source inclusion: {fat_gap['aafco_recommended_min_pct']:.0f}%")
            print(f"  Note: {fat_gap['note']}")
        else:
            print(f"  OK: Fat source at structural minimum meets AAFCO fat_g minimum")

        # Step 6: solve cascade
        result = solver.solve_cascade(selected_ids, data, der_env, scenario_id, animal)
        solver.validate_output(result, data, der_env)

        json.dump(result, open(core.DATA_DIR / "solver_output.json", "w", encoding="utf-8"),
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