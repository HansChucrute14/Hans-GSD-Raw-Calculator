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

from core import (
    BASE_DIR, DATA_DIR, DOCS_DIR, AUDIT_DIR, JSON_FILES, load_all_jsons,
    AnimalInput, DerEnvelope, UNIT_RENAME, SUPPLEMENTS_PLANNED,
    SCENARIO_K_MAP, SOLVER_NUTRIENTS, ALL_REQUIRED_KEYS,
    MAPA_FILENAME, MAPA_TEMP_FILENAME, sha256_file, build_mapa_indices,
)
from nutrition_pipeline import (
    validate_inputs, calculate_der_and_envelope, build_matrix,
    convert_as_fed_to_energy_normalized, energy_metabolizable_kcal_per_100g,
)
from solver import build_lp_problem, solve_cascade, build_output_contract, validate_output, check_fat_source_adequacy
from mapa_docs import generate_mapa, validate_mapa

# -- Test-suite compatibility re-exports --
# tests/*.py do `import build_pipeline as bp` and reach into it as a flat
# namespace (bp.SCENARIO_K_MAP, bp.build_lp_problem, etc.) -- a holdover from
# when this file was the monolith. Names above are imported for that reason
# as much as for main()'s own use. Do not remove without checking tests/*.py.

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

        # Read old MAPA's state hash before regeneration (for Check 13 comparison)
        old_state_hash = None
        old_mapa_path = BASE_DIR / MAPA_FILENAME
        if old_mapa_path.exists():
            try:
                old_content = old_mapa_path.read_text(encoding="utf-8")
                old_hash_match = re.search(r'\*\*State Hash:\*\*\s*`?([0-9a-f]{16})`?', old_content)
                if old_hash_match:
                    old_state_hash = old_hash_match.group(1)
            except Exception:
                pass

        mapa = generate_mapa(data)
        temp_path = BASE_DIR / MAPA_TEMP_FILENAME
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(mapa)
        size = temp_path.stat().st_size
        print(f"\nWritten: {temp_path.name} ({size:,} bytes)")

        # Run validation gate
        errors = validate_mapa(mapa, data, prev_state_hash=old_state_hash)
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
            print(f"{MAPA_FILENAME} not found - run --generate-mapa first")

    elif mode == "--validate-db":
        print("Validating DB_ingredientes.json against 3-state nutrient contract...")
        
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
            total_ings = sum(len(g.get("ingredients", [])) for g in db.get("protein_sources", {}).values())
            print("VALIDATION PASSED: All " + str(total_ings) + " ingredients have complete 3-state nutrient entries with valid references.")

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

        # Conditional adequacy check: fat source vs AAFCO fat minimum
        fat_gap = check_fat_source_adequacy(matrix, selected_ids, fr, der_env, db)
        print(f"\n=== Conditional Adequacy Check ===")
        if fat_gap:
            print(f"  GAP DETECTED: fat_g at structural minimum = {fat_gap['estimated_fat_at_structural_min']:.1f} g/1000kcal (AAFCO min = {fat_gap['aafco_fat_min']})")
            print(f"  Fat source at structural minimum ({fat_gap['structural_min_pct']:.0f}%) yields {fat_gap['pct_of_min']:.1f}% of AAFCO minimum")
            print(f"  AAFCO-recommended fat source inclusion: {fat_gap['aafco_recommended_min_pct']:.0f}%")
            print(f"  Note: {fat_gap['note']}")
        else:
            print(f"  OK: Fat source at structural minimum meets AAFCO fat_g minimum")

        # Step 6: solve cascade
        result = solve_cascade(selected_ids, data, der_env, scenario_id, animal)
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

from gsd.cli import main

if __name__ == "__main__":
    main()

