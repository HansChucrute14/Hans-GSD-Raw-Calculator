#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 0 Audit Script for MAPA Generation
Loads all 11 JSONs, computes SHA256, builds cross-ref index, diffs vs cross_refs.json
"""

import json
import hashlib
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / "data"
CROSS_REFS_PATH = Path(__file__).parent.parent / "docs" / "metadata" / "cross_refs.json"
AUDIT_DIR = Path(__file__).parent.parent / "audit"

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
    "db_ingredientes.schema.json",  # 11th file - schema
]

# Token patterns to extract
REF_PATTERN = re.compile(r'REF_[A-Z0-9_]+')
INGREDIENT_ID_PATTERN = re.compile(r'(?:beef|chicken|pork|salmon|kelp|salt|copper)_[a-z_]+')
NUTRIENT_ID_PATTERN = re.compile(r'(?:[a-z]+_)+[a-z]+')  # generic, we'll filter by known lists
CATEGORY_PATTERN = re.compile(r'(?:muscle_meat|organ_secreting|organ_non_secreting|connective_tissue|bone|fat_source|blood_source|muscle_organ|supplement)')
CONSTRAINT_ID_PATTERN = re.compile(r'CSTR_[A-Z0-9_]+')
WEIGHT_ID_PATTERN = re.compile(r'PEN_[A-Z0-9_]+')
SCENARIO_ID_PATTERN = re.compile(r'SN_[A-Z0-9_]+')
K_MULTIPLIER_PATTERN = re.compile(r'(?:slow_growth|rapid_growth|adult_working)')

# Known IDs from data (we'll extract dynamically)
KNOWN_NUTRIENT_IDS = {
    "protein_g", "fat_g", "arginine_g", "histidine_g", "isoleucine_g", "leucine_g",
    "lysine_g", "methionine_g", "phenylalanine_g", "threonine_g", "tryptophan_g",
    "valine_g", "methionine_plus_cystine_g", "phenylalanine_plus_tyrosine_g",
    "linoleic_acid_g", "ala_alpha_linolenic_acid_g", "ara_arachidonic_acid_g",
    "epa_plus_dha_g", "calcium_g", "phosphorus_g", "magnesium_g", "sodium_g",
    "potassium_g", "chloride_g", "iron_mg", "copper_mg", "manganese_mg", "zinc_mg",
    "iodine_mg", "selenium_mg", "vitamin_a_iu", "vitamin_d3_iu", "vitamin_e_iu",
    "thiamine_b1_mg", "riboflavin_b2_mg", "pantothenic_acid_b5_mg", "niacin_b3_mg",
    "pyridoxine_b6_mg", "folic_acid_b9_mg", "cobalamin_b12_mg", "choline_g",
    "caloric_density", "ca_p_ratio", "cost_per_kg"
}


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 of a file."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_json(filepath: Path) -> Dict[str, Any]:
    """Load JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_all_tokens(obj: Any, path: str = "") -> Dict[str, Set[str]]:
    """Recursively extract all token types from JSON object."""
    tokens = defaultdict(set)
    
    def _extract(obj: Any, path: str):
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_path = f"{path}.{k}" if path else k
                # Check keys for tokens
                if isinstance(k, str):
                    if REF_PATTERN.fullmatch(k):
                        tokens['refs'].add(k)
                    elif CONSTRAINT_ID_PATTERN.fullmatch(k):
                        tokens['constraint_ids'].add(k)
                    elif WEIGHT_ID_PATTERN.fullmatch(k):
                        tokens['weight_ids'].add(k)
                    elif SCENARIO_ID_PATTERN.fullmatch(k):
                        tokens['scenario_ids'].add(k)
                _extract(v, new_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _extract(item, f"{path}[{i}]")
        elif isinstance(obj, str):
            # Extract tokens from string values
            for ref in REF_PATTERN.findall(obj):
                tokens['refs'].add(ref)
            for cid in CONSTRAINT_ID_PATTERN.findall(obj):
                tokens['constraint_ids'].add(cid)
            for wid in WEIGHT_ID_PATTERN.findall(obj):
                tokens['weight_ids'].add(wid)
            for sid in SCENARIO_ID_PATTERN.findall(obj):
                tokens['scenario_ids'].add(sid)
            # Nutrient IDs - check against known list
            for nut in KNOWN_NUTRIENT_IDS:
                if nut in obj:
                    tokens['nutrient_ids'].add(nut)
            # Ingredient IDs - check common patterns
            # Categories
            for cat in ['muscle_meat', 'organ_secreting', 'organ_non_secreting', 
                       'connective_tissue', 'bone', 'fat_source', 'blood_source', 
                       'muscle_organ', 'supplement']:
                if cat in obj:
                    tokens['categories'].add(cat)
    
    return tokens


def extract_ingredient_ids(db: Dict) -> Dict[str, Dict]:
    """Extract all ingredient IDs with metadata from DB_ingredientes.json."""
    ingredients = {}
    for group in db.get('protein_sources', {}).values():
        for ing in group.get('ingredients', []):
            ing_id = ing.get('ingredient_id')
            if ing_id:
                nutrients = ing.get('bromatological_profile', {}).get('nutrients', {})
                excluded = ing.get('bromatological_profile', {}).get('coverage_excluded_nutrients', [])
                ingredients[ing_id] = {
                    'category': ing.get('category'),
                    'group': group.get('common_name'),
                    'display_name': ing.get('display_name'),
                    'nutrient_count': len(nutrients),
                    'excluded': excluded,
                    'source_refs': [n.get('source_ref') for n in nutrients.values() if n.get('source_ref')]
                }
    return ingredients


def extract_nutrient_matrix_ids(fr: Dict) -> Set[str]:
    """Extract nutrient IDs from formulation_rules.nutrient_matrix."""
    ids = set()
    for nm in fr.get('nutrient_matrix', []):
        if 'nutrient_id' in nm:
            ids.add(nm['nutrient_id'])
    return ids


def extract_constraint_ids(constraints: Dict) -> Dict[str, Dict]:
    """Extract all constraint IDs with metadata from constraints.json."""
    result = {}
    for section in ['mineral_antagonisms', 'toxicological_limits', 'inclusion_constraints', 'nutrient_bounds']:
        for c in constraints.get(section, []):
            cid = c.get('constraint_id')
            if cid:
                result[cid] = {
                    'type': section,
                    'name': c.get('name'),
                    'human_readable': c.get('human_readable'),
                    'solver_behavior': c.get('solver_behavior'),
                    'source_ref': c.get('source_ref'),
                    'variables': c.get('lp_coefficients', {}).get('variables_referenced', [])
                }
    return result


def extract_weight_ids(weights: List) -> Dict[str, Dict]:
    """Extract all weight IDs from objective_weights.json."""
    result = {}
    for w in weights:
        wid = w.get('weight_id')
        if wid:
            result[wid] = {
                'variable': w.get('variable'),
                'direction': w.get('direction'),
                'weight': w.get('weight'),
                'priority_tier': w.get('priority_tier'),
                'solver_penalty_multiplier': w.get('solver_penalty_multiplier'),
                'source_ref': w.get('source_ref')
            }
    return result


def extract_scenario_ids(scenarios: List) -> Dict[str, Dict]:
    """Extract scenario IDs from scenarios.json."""
    result = {}
    for s in scenarios:
        sid = s.get('scenario_id')
        if sid:
            result[sid] = {
                'name': s.get('name'),
                'status': s.get('status'),
                'target_count': len(s.get('targets', [])),
                'source_ref': s.get('source_ref')
            }
    return result


def extract_k_multipliers(growth: Dict) -> Dict[str, Any]:
    """Extract k_multipliers from growth_energy_skeletal.json."""
    return growth.get('k_multipliers', {})


def extract_provenance_refs(prov: Dict) -> Dict[str, Dict]:
    """Extract all references from audit_provenance.json."""
    refs = {}
    for ref_id, ref_data in prov.get('references', {}).items():
        refs[ref_id] = {
            'quality_flag': ref_data.get('quality_flag'),
            'doc_ids': ref_data.get('doc_ids', []),
            'applies_to': ref_data.get('applies_to', [])
        }
    return refs


def build_cross_ref_index(data: Dict[str, Any]) -> Dict[str, Any]:
    """Build comprehensive cross-reference index from all JSONs."""
    index = {
        'files': {},
        'refs': {},
        'ingredient_ids': {},
        'nutrient_ids': set(),
        'constraint_ids': {},
        'weight_ids': {},
        'scenario_ids': {},
        'k_multipliers': {},
        'categories': set(),
        'provenance_refs': {}
    }
    
    # Extract from each file
    db = data.get('DB_ingredientes.json', {})
    constraints = data.get('constraints.json', {})
    fr = data.get('formulation_rules.json', {})
    prov = data.get('audit_provenance.json', {})
    growth = data.get('growth_energy_skeletal.json', {})
    weights = data.get('objective_weights.json', [])
    scenarios = data.get('scenarios.json', [])
    tox = data.get('toxicological_limits.json', [])
    lp_schema = data.get('lp_parameters.schema.json', {})
    lp_data = data.get('lp_parameters_data.json', {})
    
    # Ingredient IDs
    index['ingredient_ids'] = extract_ingredient_ids(db)
    
    # Nutrient IDs from matrix
    index['nutrient_ids'] = extract_nutrient_matrix_ids(fr)
    
    # Constraint IDs
    index['constraint_ids'] = extract_constraint_ids(constraints)
    
    # Weight IDs
    index['weight_ids'] = extract_weight_ids(weights)
    
    # Scenario IDs
    index['scenario_ids'] = extract_scenario_ids(scenarios)
    
    # K multipliers
    index['k_multipliers'] = extract_k_multipliers(growth)
    
    # Categories used
    index['categories'] = set(ing['category'] for ing in index['ingredient_ids'].values())
    
    # Categories mapped in formulation_rules
    mapping = fr.get('_inclusion_semantics', {}).get('category_to_ingredient_mapping', {})
    index['categories_mapped'] = set()
    for ids in mapping.values():
        index['categories_mapped'].update(ids)
    
    # Provenance refs
    index['provenance_refs'] = extract_provenance_refs(prov)
    
    # All REF_* tokens from all JSONs
    all_refs = set()
    for fname, fdata in data.items():
        tokens = extract_all_tokens(fdata)
        all_refs.update(tokens['refs'])
    index['refs'] = {ref: {'found_in': []} for ref in all_refs}
    
    # Track which file each ref appears in
    for fname, fdata in data.items():
        tokens = extract_all_tokens(fdata)
        for ref in tokens['refs']:
            if ref in index['refs']:
                index['refs'][ref]['found_in'].append(fname)
    
    # Also add refs from toxicological_limits (list at top level)
    for tox_entry in tox:
        if 'source_ref' in tox_entry:
            ref = tox_entry['source_ref']
            if ref not in index['refs']:
                index['refs'][ref] = {'found_in': []}
            index['refs'][ref]['found_in'].append('toxicological_limits.json')
        if 'pathophysiology_ref' in tox_entry:
            ref = tox_entry['pathophysiology_ref']
            if ref not in index['refs']:
                index['refs'][ref] = {'found_in': []}
            index['refs'][ref]['found_in'].append('toxicological_limits.json')
    
    return index


def diff_cross_refs(index: Dict[str, Any], cross_refs: Dict[str, Any]) -> Dict[str, Any]:
    """Diff computed index against docs/metadata/cross_refs.json."""
    drift = {
        'missing_in_index': [],
        'extra_in_index': [],
        'section_mapping_drift': [],
        'term_index_drift': []
    }
    
    # Check refs
    cross_refs_refs = set()
    # cross_refs.json has refs in term_index and inbound/outbound
    for term, info in cross_refs.get('term_index', {}).items():
        if term.startswith('REF_'):
            cross_refs_refs.add(term)
    
    index_refs = set(index['refs'].keys())
    
    drift['missing_in_index'] = sorted(cross_refs_refs - index_refs)
    drift['extra_in_index'] = sorted(index_refs - cross_refs_refs)
    
    # Check section_to_satellite mapping
    cross_sections = set(cross_refs.get('section_to_satellite', {}).keys())
    # We don't have a computed equivalent, just verify they exist
    
    # Check term_index
    cross_terms = set(cross_refs.get('term_index', {}).keys())
    # We don't compute term_index, but we can check if our tokens cover known terms
    
    return drift


def main():
    print("=" * 60)
    print("PHASE 0: MAPA Baseline Audit")
    print("=" * 60)
    
    AUDIT_DIR.mkdir(exist_ok=True)
    
    # Load all JSONs
    print("\n[0.1] Loading 11 JSON files...")
    data = {}
    manifest = {}
    
    for fname in JSON_FILES:
        fpath = DATA_DIR / fname
        if fpath.exists():
            content = load_json(fpath)
            data[fname] = content
            sha = compute_sha256(fpath)
            size = fpath.stat().st_size
            manifest[fname] = {
                'size_bytes': size,
                'sha256': sha,
                'keys': list(content.keys()) if isinstance(content, dict) else f'list[{len(content)}]'
            }
            print(f"  [OK] {fname}: {size:,} bytes, SHA256={sha[:16]}...")
        else:
            print(f"  ✗ {fname}: NOT FOUND")
            manifest[fname] = {'error': 'NOT FOUND'}
    
    # Save baseline manifest
    manifest_path = AUDIT_DIR / "baseline_manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"\n[0.1] Saved baseline_manifest.json")
    
    # Build cross-ref index
    print("\n[0.2] Building cross-reference index...")
    index = build_cross_ref_index(data)
    
    # Save cross-ref index
    index_path = AUDIT_DIR / "cross_ref_index.json"
    # Convert sets to lists for JSON serialization
    serializable_index = {}
    for k, v in index.items():
        if isinstance(v, set):
            serializable_index[k] = sorted(list(v))
        elif isinstance(v, dict):
            serializable_index[k] = v
        else:
            serializable_index[k] = v
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(serializable_index, f, indent=2, ensure_ascii=False)
    print(f"[0.2] Saved cross_ref_index.json")
    
    # Load existing cross_refs.json
    print("\n[0.3] Diffing against docs/metadata/cross_refs.json...")
    cross_refs = load_json(CROSS_REFS_PATH)
    drift = diff_cross_refs(index, cross_refs)
    
    # Save drift report
    drift_path = AUDIT_DIR / "cross_refs_drift.json"
    with open(drift_path, 'w', encoding='utf-8') as f:
        json.dump(drift, f, indent=2, ensure_ascii=False)
    print(f"[0.3] Saved cross_refs_drift.json")
    
    # Summary
    print("\n" + "=" * 60)
    print("AUDIT SUMMARY")
    print("=" * 60)
    print(f"Files loaded: {len([m for m in manifest.values() if 'error' not in m])}/11")
    print(f"Ingredient IDs: {len(index['ingredient_ids'])}")
    print(f"Nutrient IDs (matrix): {len(index['nutrient_ids'])}")
    print(f"Constraint IDs: {len(index['constraint_ids'])}")
    print(f"Weight IDs: {len(index['weight_ids'])}")
    print(f"Scenario IDs: {len(index['scenario_ids'])}")
    print(f"REF_* tokens: {len(index['refs'])}")
    print(f"Provenance refs: {len(index['provenance_refs'])}")
    print(f"Categories used: {len(index['categories'])}")
    print(f"Categories mapped: {len(index['categories_mapped'])}")
    print(f"\nDRIFT REPORT:")
    print(f"  Missing in index (in cross_refs but not in JSONs): {len(drift['missing_in_index'])}")
    print(f"  Extra in index (in JSONs but not in cross_refs): {len(drift['extra_in_index'])}")
    
    if drift['missing_in_index']:
        print(f"\n  Missing refs: {drift['missing_in_index'][:10]}...")
    if drift['extra_in_index']:
        print(f"\n  Extra refs: {drift['extra_in_index'][:10]}...")
    
    print(f"\nAudit files written to: {AUDIT_DIR}")
    print("=" * 60)
    
    return drift


if __name__ == "__main__":
    main()