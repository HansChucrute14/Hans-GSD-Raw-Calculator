"""Generate external_verification_checklist.json — prioritized list of EXTERNAL orphan refs.

Per plan §5: 82 (or current count) EXTERNAL_VERIFICATION_REQUIRED unique refs, 
sorted by leverage (occurrence_count descending), with suggested_source_to_check per prefix.

Usage: python3 build_external_checklist.py [--json <output>]
"""

import json
from collections import Counter


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# Suggested source databases for each prefix category
SOURCE_SUGGESTIONS = {
    "REF_COFID": "Cofid (UK government nutritional database: https://www.cofid.com)",
    "REF_MILAGRES2020": "Milagres et al. 2020 study",
    "REF_LITERATURE": "Literature citation to be identified by team",
    "REF_SCHWEIGERT1943": "Schweigert 1943 historical study",
    "REF_FRIDA": "FRIDA (Food Reference Database for Animal Nutrition)",
    "REF_MATVARETABELLEN": "Norwegian food composition tables",
    "REF_WHOLEFOODCATALOG": "Whole Food Catalog",
}


def generate_external_checklist(manifest_path="data/orphan_refs_manifest.json"):
    """Generate prioritized external verification checklist."""
    manifest = load_json(manifest_path)
    
    # Collect all EXTERNAL refs with their occurrence counts and affected ingredients
    ext_entries = []
    for prefix, refs in manifest.get("groups", {}).items():
        for ref_info in refs:
            if ref_info["classification"] == "EXTERNAL_VERIFICATION_REQUIRED":
                ext_entries.append({
                    "ref": ref_info["ref"],
                    "occurrences": ref_info["occurrences"],
                    "suggested_source_to_check": SOURCE_SUGGESTIONS.get(
                        prefix, f"External source to be identified for {prefix}"
                    ),
                    "verification_status": "NOT_CHECKED",  # default; will be updated where we checked
                })
    
    # Sort by occurrences descending (highest leverage first)
    ext_entries.sort(key=lambda x: -x["occurrences"])
    
    checklist = {
        "version": "3.0.1-HARDENED",
        "summary": {
            "total_external_refs": len(ext_entries),
            "total_occurrences": sum(e["occurrences"] for e in ext_entries),
        },
        "entries": ext_entries,
    }
    
    return checklist


if __name__ == "__main__":
    import sys
    
    args = sys.argv[1:]
    output_path = None

    if "--json" in args:
        idx = args.index("--json")
        if idx + 1 < len(args):
            output_path = args[idx + 1]
    
    checklist = generate_external_checklist()
    
    count = checklist["summary"]["total_external_refs"]
    
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(checklist, f, indent=2, ensure_ascii=False)
        print(f"Written to {output_path} ({count} entries)")
    else:
        # Print summary to stdout for the apply script
        s = checklist["summary"]
        print(f"Total EXTERNAL refs: {s['total_external_refs']}")
        print(f"Total occurrences: {s['total_occurrences']}")
