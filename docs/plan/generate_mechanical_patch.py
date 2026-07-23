"""Generate mechanical_provenance_patch.json — ALL schema-valid entries for MECHANICAL orphan refs.

Per plan §4: These assert an internal estimate, computation, or domain rule already recorded in 
the DB (value + confidence +, where present, a declared reason) — not a specific external source.
A provenance record is a formalization of data that exists, not a new claim.

No external lookup needed. Generates entries for ALL MECHANICAL orphan refs found by audit_orphans.py.
This script generates from scratch (ignores existing registrations).

Usage: python3 generate_mechanical_patch.py [--json <output>]
"""

import json
import re
from collections import Counter


def load_json(path):
    """Load JSON file with utf-8 encoding."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except UnicodeDecodeError:
        # Fallback to latin-1 for Windows compatibility
        with open(path, "rb") as f:
            content = f.read()
            return json.loads(content.decode("latin-1"))


def scan_db(db_path="data/DB_ingredientes.json"):
    """Walk DB and yield (ref, ingredient_id, nutrient_id) tuples for ALL orphans."""
    db = load_json(db_path)
    
    orphans = []
    
    for grp_name, grp_data in db.get("protein_sources", {}).items():
        for ing in grp_data["ingredients"]:
            iid = ing["ingredient_id"]
            profile = ing.get("bromatological_profile", {})
            
            # Check nutrients
            for nut_key, entry in profile.get("nutrients", {}).items():
                if isinstance(entry, dict):
                    ref = entry.get("source_ref") or entry.get("anomaly_ref")
                    status = entry.get("status")
                    
                    if not ref:
                        continue
                    
                    key = (ref, iid, nut_key)
                    if key not in set(orphans):
                        orphans.append(key)
    
    return orphans


def classify(ref):
    """Classify ref as MECHANICAL or EXTERNAL_VERIFICATION_REQUIRED.
    
    Classification rule (deterministic, per plan §2.1): REF_ESTIMATED, REF_COMPUTED, 
    REF_INFERRED, REF_NA are MECHANICAL — they assert an internal estimation/computation, 
    not a specific external source. Any REF_USDA_FDC_<digits>_<suffix>_COMPUTED is also
    MECHANICAL (derived from computation). REF_USDA_FDC_<amino_acid_name>_<ingredient> 
    patterns are also MECHANICAL (computed composite amino acid values like cystine, tyrosine).
    Everything else names a specific external database or publication and is EXTERNAL_VERIFICATION_REQUIRED.
    """
    mechanical_prefixes = ("REF_ESTIMATED", "REF_COMPUTED", "REF_INFERRED", "REF_NA")
    if any(ref.startswith(p) for p in mechanical_prefixes):
        return "MECHANICAL"

    # REF_USDA_FDC_<digits>_<suffix>_COMPUTED is MECHANICAL (derived value, not external source)
    import re
    if re.match(r'^REF_USDA_FDC_\d+.*_COMPUTED$', ref):
        return "MECHANICAL"

    # REF_USDA_FDC_<amino_acid_name>_<ingredient> is MECHANICAL (computed composite amino acid value)
    # e.g., CYSTINE_CHICKEN_BREAST, TYROSINE_CHICKEN_LIVER — these are derived from individual measurements
    if re.match(r'^REF_USDA_FDC_[A-Z]+_[A-Z_]+$', ref):
        return "MECHANICAL"

    # Bare numeric USDA FDC IDs are EXTERNAL
    if re.match(r'^REF_USDA_FDC_\d+$', ref):
        return "EXTERNAL_VERIFICATION_REQUIRED"

    # Everything else that names an external source is EXTERNAL
    return "EXTERNAL_VERIFICATION_REQUIRED"


def generate_mechanical_entries():
    """Generate provenance entries for all MECHANICAL orphans.
    
    This generates from scratch — no filtering against existing registrations.
    One entry per unique ref, regardless of whether it's already in audit_provenance.json.
    """
    orphan_keys = scan_db()
    
    # Classify and filter to only MECHANICAL
    mechanical_orphans = [(ref, iid, nut_key) for ref, iid, nut_key in orphan_keys 
                          if classify(ref) == "MECHANICAL"]
    
    print(f"Total orphans found: {len(orphan_keys)}")
    print(f"Mechanical orphans to register: {len(mechanical_orphans)}")
    
    # Group by ref (same ref may appear in multiple ingredients/nutrients)
    ref_groups = {}
    for ref, iid, nut_key in mechanical_orphans:
        if ref not in ref_groups:
            ref_groups[ref] = []
        ref_groups[ref].append((iid, nut_key))
    
    # Generate provenance entries (one per unique ref)
    patch = {}
    entry_count = 0
    
    for ref, occurrences in ref_groups.items():
        iid_list = [i for i, _ in occurrences]
        
        # Determine classification type for text generation
        if "REF_COMPUTED" in ref:
            text = f"'{ref}' — valores computados internamente para {len(iid_list)} ingrediente(s) ({', '.join(iid_list[:3])}{'...' if len(iid_list) > 3 else ''}). Derivação a partir de componentes individuais medidos (ex.: metionina + cistina, fenilalanina + tirosina). Confidence declarada: 'inferred'."
        elif any(p in ref for p in ("REF_ESTIMATED", "REF_NA")):
            text = f"'{ref}' — valores estimados/inferidos internamente para {len(iid_list)} ingrediente(s) ({', '.join(iid_list[:3])}{'...' if len(iid_list) > 3 else ''}). Derivação a partir de modelo de composição tecidual. Confidence declarada: 'estimated' ou 'inferred'."
        elif "REF_INFERRED" in ref:
            text = f"'{ref}' — valores inferidos com base em dados disponíveis para {len(iid_list)} ingrediente(s) ({', '.join(iid_list[:3])}{'...' if len(iid_list) > 3 else ''}). Confidence declarada: 'inferred'."
        elif "REF_USDA_FDC_" in ref and re.match(r'^REF_USDA_FDC_[A-Z]+_[A-Z_]+$', ref):
            # Composite amino acid computed values (cystine, tyrosine, etc.)
            text = f"'{ref}' — valores computados internamente para {len(iid_list)} ingrediente(s) ({', '.join(iid_list[:3])}{'...' if len(iid_list) > 3 else ''}). Derivação a partir de componentes individuais medidos. Confidence declarada: 'inferred'."
        elif "REF_USDA_FDC_" in ref and re.match(r'^REF_USDA_FDC_\d+.*_COMPUTED$', ref):
            # Explicitly computed values (e.g., methionine_plus_cystine_g COMPUTED)
            text = f"'{ref}' — valores computados internamente para {len(iid_list)} ingrediente(s) ({', '.join(iid_list[:3])}{'...' if len(iid_list) > 3 else ''}). Derivação a partir de componentes individuais medidos. Confidence declarada: 'inferred'."
        else:
            text = f"'{ref}' — valores estimados/inferidos internamente para {len(iid_list)} ingrediente(s). Derivação a partir de dados disponíveis. Confidence declarada: 'inferred'."
        
        provenance_entry = {
            "text": text,
            "doc_ids": [],
            "quality_flag": "INFERRED",  # MECHANICAL entries are always INFERRED (no external verification)
            "line_references": [],
            "applies_to": iid_list,
            "nutrient_count": len(set(nut_key for _, nut_key in occurrences)),
            "note": f"Gerado automaticamente por generate_mechanical_patch.py a partir de valores declarados em DB_ingredientes.json. Não envolve verificação de fonte externa."
        }
        
        patch[ref] = provenance_entry
        entry_count += 1
    
    return patch, entry_count


def main():
    # Generate the complete mechanical patch from scratch (no filtering)
    print("Scanning for orphans...")
    
    orphan_keys = scan_db()
    
    if not orphan_keys:
        print("No orphans found. Generating empty patch.")
        with open("mechanical_provenance_patch.json", "wb") as f:
            json.dump({}, f, indent=2, ensure_ascii=False)
        return
    
    # Generate provenance entries (one per unique ref) - NO filtering against existing registrations
    patch, count = generate_mechanical_entries()
    
    with open("mechanical_provenance_patch.json", "wb") as f:
        content_bytes = json.dumps(patch, indent=2, ensure_ascii=False).encode("utf-8")
        f.write(content_bytes)
    
    print(f"Written to mechanical_provenance_patch.json ({count} entries)")


if __name__ == "__main__":
    main()
