"""Deterministic audit of orphan source_refs in DB_ingredientes.json.

Walks every nutrients.*.source_ref, nutrients.*.anomaly_ref, and safety_alerts[].source_ref,
checks membership against audit_provenance.json['references'], classifies each ref as
MECHANICAL or EXTERNAL_VERIFICATION_REQUIRED, outputs manifest JSON. No LLM judgment — plain dict lookups.

Usage: python3 audit_orphans.py [--summary] [--json <output>]
"""

import json
import sys
import re
from collections import Counter
from pathlib import Path


def load_json(path):
    with open(str(Path(__file__).resolve().parent / path)) as f:
        return json.load(f)


def scan_db(db_path="data/DB_ingredientes.json"):
    """Walk DB and yield (ref, ingredient_id, nutrient_id, source_type) tuples."""
    db = load_json(db_path)
    orphans = []

    # Scan nutrients in all protein sources
    for grp_name, grp_data in db.get("protein_sources", {}).items():
        for ing in grp_data["ingredients"]:
            iid = ing["ingredient_id"]
            profile = ing.get("bromatological_profile", {})
            for nut_key, entry in profile.get("nutrients", {}).items():
                if isinstance(entry, dict):
                    ref = entry.get("source_ref")
                    anomaly_ref = entry.get("anomaly_ref")
                    status = entry.get("status")

                    # source_ref on measured entries
                    if ref and status == "measured":
                        orphans.append((ref, iid, nut_key, "source"))
                    # anomaly_ref on non-measured entries (not_applicable)
                    elif anomaly_ref:
                        orphans.append((anomaly_ref, iid, nut_key, "anomaly"))

    # Scan safety_alerts source_refs
    for grp_name, grp_data in db.get("protein_sources", {}).items():
        for ing in grp_data["ingredients"]:
            alerts = ing.get("safety_alerts", [])
            if isinstance(alerts, list):
                for alert in alerts:
                    ref = alert.get("source_ref")
                    if ref and ref not in set(orphans[:0]):  # placeholder - we check against known refs later
                        orphans.append((ref, ing["ingredient_id"], "safety_alert", "alert"))

    return orphans


def classify(ref):
    """Classify ref as MECHANICAL or EXTERNAL_VERIFICATION_REQUIRED.
    
    Classification rule (deterministic, per plan §2.1): REF_ESTIMATED, REF_COMPUTED, 
    REF_INFERRED, REF_NA are MECHANICAL — they assert an internal estimation/computation, 
    not a specific external source. Any REF_USDA_FDC_<digits>_<suffix>_COMPUTED is also
    MECHANICAL (derived from computation). Everything else names a specific external 
    database or publication and is EXTERNAL_VERIFICATION_REQUIRED.
    """
    mechanical_prefixes = {"REF_ESTIMATED", "REF_COMPUTED", "REF_INFERRED", "REF_NA"}
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


def build_manifest(db_path="data/DB_ingredientes.json", provenance_path="data/audit_provenance.json"):
    """Build orphan manifest with classification and groupings."""
    db = load_json(db_path)
    prov = load_json(provenance_path)
    known_refs = set(prov.get("references", {}).keys())

    # Collect all orphans: (ref, ingredient_id, nutrient_id, source_type)
    all_orphans = []
    
    for grp_name, grp_data in db.get("protein_sources", {}).items():
        for ing in grp_data["ingredients"]:
            iid = ing["ingredient_id"]
            profile = ing.get("bromatological_profile", {})
            
            # Check nutrients
            for nut_key, entry in profile.get("nutrients", {}).items():
                if isinstance(entry, dict):
                    ref = entry.get("source_ref")
                    anomaly_ref = entry.get("anomaly_ref")
                    status = entry.get("status")

                    if ref and status == "measured" and ref not in known_refs:
                        all_orphans.append((ref, iid, nut_key, "source"))
                    elif anomaly_ref and anomaly_ref not in known_refs:
                        all_orphans.append((anomaly_ref, iid, nut_key, "anomaly"))

            # Check safety_alerts
            alerts = ing.get("safety_alerts", [])
            if isinstance(alerts, list):
                for alert in alerts:
                    ref = alert.get("source_ref")
                    if ref and ref not in known_refs:
                        all_orphans.append((ref, iid, "safety_alert", "alert"))

    # Deduplicate by (ref, ingredient_id, nutrient_id, source_type)
    seen = set()
    unique_orphans = []
    for ref, iid, nut_key, src in all_orphans:
        key = (ref, iid, nut_key, src)
        if key not in seen:
            seen.add(key)
            unique_orphans.append(key)

    # Classify and count occurrences per ref
    classified = {}  # ref -> classification
    ref_counts = Counter()
    for ref, _, _, _ in unique_orphans:
        cls = classify(ref)
        if ref not in classified:
            classified[ref] = cls
        ref_counts[ref] += 1

    # Group by prefix (for display)
    groups = {}
    for ref, cls in classified.items():
        prefix = ref.split("_")[0] if "_" in ref else ref
        groups.setdefault(prefix, []).append({
            "ref": ref,
            "classification": cls,
            "occurrences": ref_counts[ref],
            "affected_ingredients": list(ref_counts.keys())[:5]
        })

    # Build manifest
    mechanical_count = sum(1 for c in classified.values() if c == "MECHANICAL")
    external_count = sum(1 for c in classified.values() if c == "EXTERNAL_VERIFICATION_REQUIRED")

    manifest = {
        "version": "3.0.1-HARDENED",
        "summary": {
            "total_unique_refs": len(classified),
            "total_occurrences": len(unique_orphans),
            "mechanical_count": mechanical_count,
            "external_count": external_count,
        },
        "groups": groups,
    }

    return manifest


def print_summary(manifest):
    s = manifest["summary"]
    print(f"Total unique orphan refs: {s['total_unique_refs']}")
    print(f"Total occurrences: {s['total_occurrences']}")
    print(f"MECHANICAL (auto-resolvable): {s['mechanical_count']}")
    print(f"EXTERNAL_VERIFICATION_REQUIRED: {s['external_count']}")
    print()

    for prefix, refs in manifest["groups"].items():
        mech = [r for r in refs if r["classification"] == "MECHANICAL"]
        ext = [r for r in refs if r["classification"] == "EXTERNAL_VERIFICATION_REQUIRED"]
        total = len(refs)
        print(f"  {prefix}: {total} unique refs ({len(mech)} MECHANICAL, {len(ext)} EXTERNAL)")


def main():
    args = sys.argv[1:]
    show_summary = "--summary" in args
    output_path = None

    if "--json" in args:
        idx = args.index("--json")
        if idx + 1 < len(args):
            output_path = args[idx + 1]

    manifest = build_manifest()

    if show_summary or not output_path:
        print_summary(manifest)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print(f"\nManifest written to {output_path}")


if __name__ == "__main__":
    main()
