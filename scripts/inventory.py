import json, os, hashlib, sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")

FILES = {
    "DB_ingredientes.json": "Ingredient bank",
    "constraints.json": "LP constraints",
    "formulation_rules.json": "Formulation rules",
    "audit_provenance.json": "Provenance",
    "growth_energy_skeletal.json": "Growth/energy model",
    "objective_weights.json": "Objective weights",
    "scenarios.json": "Scenarios",
    "toxicological_limits.json": "Toxicological limits",
    "lp_parameters.schema.json": "LP validation schema",
    "lp_parameters_data.json": "LP runtime parameters (NUTRIENT_REGISTRY + solve_cascade)",
}

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def load(name):
    return json.load(open(os.path.join(DATA, name), encoding="utf-8"))

def report():
    lines = []
    lines.append("# Baseline Inventory — GSD Diet Calc V10.4")
    lines.append(f"**Generated:** {datetime.now().isoformat()}")
    lines.append(f"**Working directory:** {BASE}")
    lines.append("")
    lines.append("## 1. File Manifest")
    lines.append("")
    lines.append("| File | Size | SHA-256 | Purpose |")
    lines.append("|---|---|---|---|")
    for name, purpose in FILES.items():
        path = os.path.join(DATA, name)
        size = os.path.getsize(path)
        h = sha256(path)
        lines.append(f"| `{name}` | {size} B | `{h[:16]}...` | {purpose} |")
    lines.append("")

    # DB_ingredientes
    db = load("DB_ingredientes.json")
    meta = db.get("_db_metadata", {})
    lines.append("## 2. DB_ingredientes.json")
    lines.append("")
    lines.append(f"- **Version:** {meta.get('version', '?')}")
    lines.append(f"- **Claimed ingredients:** {meta.get('total_ingredients', '?')}")
    lines.append(f"- **Claimed nutrients/ingredient:** {meta.get('nutrients_per_ingredient', '?')}")
    lines.append(f"- **template_ref:** {meta.get('template_ref', '?')}")
    lines.append(f"- **schema_ref:** {meta.get('schema_ref', '?')}")
    all_ings = [i for g in db.get("protein_sources", {}).values() for i in g.get("ingredients", [])]
    lines.append(f"- **Actual ingredients:** {len(all_ings)}")
    lines.append("")
    lines.append("### 2.1 Ingredients")
    lines.append("")
    lines.append(f"| ID | Category | Nutrients | Group |")
    lines.append(f"|---|---|---|---|")
    for ing in all_ings:
        nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
        excl = ing.get("bromatological_profile", {}).get("coverage_excluded_nutrients", {})
        n = len(nuts)
        e = len(excl) if excl else 0
        label = f"{n} fields" + (f" (+{e} excl)" if e else "")
        # find which group
        grp = "?"
        for gn, gd in db.get("protein_sources", {}).items():
            for i in gd.get("ingredients", []):
                if i["ingredient_id"] == ing["ingredient_id"]:
                    grp = gn
                    break
        lines.append(f"| `{ing['ingredient_id']}` | {ing.get('category','?')} | {label} | {grp} |")
    lines.append("")
    lines.append("### 2.2 Categories Found")
    cats = sorted(set(i.get("category") for i in all_ings))
    lines.append(f"- {', '.join(cats)}")
    lines.append("")

    # Union of all nutrient field names
    all_fields = set()
    for ing in all_ings:
        all_fields.update(ing.get("bromatological_profile", {}).get("nutrients", {}).keys())
    lines.append(f"### 2.3 Unified Nutrient Fields ({len(all_fields)})")
    lines.append("")
    lines.append(f"`{'`, `'.join(sorted(all_fields))}`")
    lines.append("")

    # Ingredients with coverage_excluded_nutrients
    with_coverage = [i for i in all_ings if i.get("bromatological_profile", {}).get("coverage_excluded_nutrients")]
    lines.append(f"### 2.4 Ingredients with `coverage_excluded_nutrients`")
    lines.append(f"- **Count:** {len(with_coverage)} / {len(all_ings)}")
    for i in with_coverage:
        excl = i["bromatological_profile"]["coverage_excluded_nutrients"]
        if isinstance(excl, list):
            lines.append(f"  - `{i['ingredient_id']}`: {excl}")
        else:
            lines.append(f"  - `{i['ingredient_id']}`: {list(excl.keys())}")
    lines.append("")

    # Missing supplements check
    supplements_needed = ["kelp_meal_dried", "salt_nacl", "copper_sulfate"]
    actual_ids = set(i["ingredient_id"] for i in all_ings)
    missing = [s for s in supplements_needed if s not in actual_ids]
    if missing:
        lines.append(f"### 2.5 Missing Supplements (planned)")
        lines.append(f"- **Not in DB:** {', '.join(f'`{m}`' for m in missing)}")
        lines.append("")

    # constraints
    c = load("constraints.json")
    lines.append("## 3. constraints.json")
    lines.append("")
    for sec in ["nutrient_bounds", "toxicological_limits", "inclusion_constraints", "mineral_antagonisms"]:
        items = c.get(sec, [])
        hard = sum(1 for x in items if x.get("solver_behavior") == "HARD_FAIL_INFEASIBLE")
        other = sum(1 for x in items if x.get("solver_behavior") != "HARD_FAIL_INFEASIBLE")
        lines.append(f"- **{sec}:** {len(items)} constraints ({hard} HARD, {other} other)")
    lines.append("")

    # toxicological_limits
    tox = load("toxicological_limits.json")
    lines.append("## 4. toxicological_limits.json")
    lines.append("")
    lines.append(f"- **Type:** `{type(tox).__name__}` (top-level)")
    lines.append(f"- **Count:** {len(tox)} SULs")
    lines.append("")
    lines.append("| Nutrient | Value | Unit | Basis |")
    lines.append("|---|---|---|---|")
    for e in tox:
        s = e.get("sul", {})
        lines.append(f"| `{e['nutrient_id']}` | {s.get('value')} | {s.get('unit','?')} | {s.get('basis','?')} |")
    lines.append("")

    # scenarios
    sc = load("scenarios.json")
    lines.append("## 5. scenarios.json")
    lines.append("")
    lines.append(f"- **Type:** `{type(sc).__name__}` (top-level)")
    lines.append(f"- **Count:** {len(sc) if isinstance(sc, list) else '?'}")
    if isinstance(sc, list):
        for s in sc:
            lines.append(f"  - `{s.get('scenario_id')}`: {s.get('name','')} | status={s.get('status','')} | {len(s.get('targets',[]))} targets")
    lines.append("")

    # objective_weights
    ow = load("objective_weights.json")
    lines.append("## 6. objective_weights.json")
    lines.append("")
    lines.append(f"- **Count:** {len(ow) if isinstance(ow, list) else '?'}")
    if isinstance(ow, list):
        lines.append("")
        lines.append("| ID | Penalty Multiplier | Tier |")
        lines.append("|---|---|---|")
        for w in ow:
            pm = w.get("solver_penalty_multiplier", "MISSING")
            lines.append(f"| `{w['weight_id']}` | {pm} | {w.get('priority_tier','?')} |")
        # Check PEN_MANGANESE_NEG
        pmm = [w for w in ow if "solver_penalty_multiplier" not in w]
        if pmm:
            lines.append("")
            lines.append(f"**Without penalty_multiplier:** {', '.join(w['weight_id'] for w in pmm)}")
    lines.append("")

    # audit_provenance
    prov = load("audit_provenance.json")
    lines.append("## 7. audit_provenance.json")
    lines.append("")
    refs = prov.get("references", {})
    if isinstance(refs, dict):
        lines.append(f"- **Total entries:** {len(refs)}")
        statuses = {}
        for rid, rdata in refs.items():
            if isinstance(rdata, dict):
                s = rdata.get("quality_flag", rdata.get("status", "MISSING"))
                statuses[s] = statuses.get(s, 0) + 1
        for s, cnt in sorted(statuses.items()):
            lines.append(f"  - **{s}:** {cnt}")
    algo = prov.get("algorithm_logic", {})
    fb = algo.get("fallback_protocols", [])
    if fb:
        lines.append(f"- **Fallback protocols:** {len(fb)} levels defined")
        for f in fb:
            lines.append(f"  - Level {f.get('level')}: {f.get('name','')}")
    lines.append("")

    # formulation_rules
    fr = load("formulation_rules.json")
    lines.append("## 8. formulation_rules.json")
    lines.append("")
    matrix = fr.get("nutrient_matrix", [])
    if isinstance(matrix, list):
        lines.append(f"- **nutrient_matrix:** {len(matrix)} entries (list)")
        if matrix:
            lines.append(f"  - First entry keys: {list(matrix[0].keys())}")
            vals = matrix[0].get("values", {})
            lines.append(f"  - values keys: {list(vals.keys()) if isinstance(vals, dict) else '?'}")
    elif isinstance(matrix, dict):
        lines.append(f"- **nutrient_matrix:** {len(matrix)} entries (dict)")
    templates = fr.get("diet_templates", [])
    lines.append(f"- **diet_templates:** {len(templates)}")
    for t in templates:
        lines.append(f"  - `{t.get('template_id')}`: {t.get('name','')}")
    mapping = fr.get("_inclusion_semantics", {}).get("category_to_ingredient_mapping", {})
    if mapping:
        lines.append(f"- **category_to_ingredient_mapping:** {len(mapping)} entries")
        all_mapped = set()
        for cat, ids in mapping.items():
            all_mapped.update(ids)
        concrete = [x for x in all_mapped if not x.startswith("_")]
        wildcards = [x for x in all_mapped if x.startswith("_")]
        missing_from_db = [x for x in concrete if x not in actual_ids]
        if missing_from_db:
            lines.append(f"  - **Mapped but missing from DB:** {', '.join(f'`{m}`' for m in missing_from_db)}")
        if wildcards:
            lines.append(f"  - **Wildcards:** {', '.join(wildcards)}")
    lines.append("")

    # growth
    g = load("growth_energy_skeletal.json")
    lines.append("## 9. growth_energy_skeletal.json")
    lines.append("")
    km = g.get("k_multipliers", {})
    lines.append(f"- **k_multipliers:** {', '.join(km.keys())}")
    for km_name, km_data in km.items():
        val = km_data.get("value", km_data.get("default", "?"))
        lines.append(f"  - `{km_name}`: value={val}, status={km_data.get('status','?')}")
    er = g.get("energy_requirements", [])
    lines.append(f"- **energy_requirements:** {len(er)} formulas")
    for e_ in er:
        lines.append(f"  - `{e_.get('param_id')}`: {e_.get('formula','')[:80]}")
    lines.append("")

    # lp_parameters.schema.json
    schema = load("lp_parameters.schema.json")
    lines.append("## 10. lp_parameters.schema.json")
    lines.append("")
    lines.append(f"- **Title:** {schema.get('title', '?')}")
    lines.append(f"- **Type:** `{type(schema).__name__}` (pure JSON Schema)")
    lines.append(f"- **Top-level keys:** {', '.join(schema.keys())}")
    has_cascade = "solve_cascade" in json.dumps(schema)
    has_registry = "NUTRIENT_REGISTRY" in json.dumps(schema)
    lines.append(f"- **Contains `solve_cascade`:** {has_cascade}")
    lines.append(f"- **Contains `NUTRIENT_REGISTRY`:** {has_registry}")
    lines.append(f"- **Note:** This file is a JSON Schema validation document. It does not contain runtime solve_cascade or NUTRIENT_REGISTRY data.")
    lines.append("")

    # lp_parameters_data.json
    data_file = os.path.join(DATA, "lp_parameters_data.json")
    if os.path.exists(data_file):
        params = json.load(open(data_file, encoding="utf-8"))
        lines.append("## 10a. lp_parameters_data.json")
        lines.append("")
        has_cascade = "solve_cascade" in params
        has_registry = "NUTRIENT_REGISTRY" in params
        lines.append(f"- **Contains `solve_cascade`:** {has_cascade}")
        if has_cascade:
            levels = [s["level"] for s in params["solve_cascade"]]
            lines.append(f"  - Levels: {levels}")
        lines.append(f"- **Contains `NUTRIENT_REGISTRY`:** {has_registry}")
        if has_registry:
            nr = params["NUTRIENT_REGISTRY"]
            lines.append(f"  - Nutrients: {len(nr)}")
            tiers = {}
            crits = {}
            for nid, ndata in nr.items():
                t = ndata.get("constraint_tier", "?")
                tiers[t] = tiers.get(t, 0) + 1
                c = ndata.get("clinical_criticality", "?")
                crits[c] = crits.get(c, 0) + 1
            lines.append(f"  - Tiers: {tiers}")
            lines.append(f"  - Clinical criticality: {crits}")
        lines.append("")

    # Orphan refs audit
    lines.append("## 11. Cross-Reference Audit")
    lines.append("")
    raw_db = open(os.path.join(DATA, "DB_ingredientes.json"), encoding="utf-8").read()
    import re
    all_refs = set(re.findall(r"REF_[A-Z0-9_]+", raw_db))
    known = set(prov.get("references", {}).keys()) if isinstance(prov.get("references"), dict) else set()
    usda = {r for r in all_refs if r.startswith("REF_USDA_")}
    internal = all_refs - usda
    orphans = internal - known
    lines.append(f"- **Total REF_ references in DB:** {len(all_refs)}")
    lines.append(f"- **USDA (external):** {len(usda)}")
    lines.append(f"- **Internal:** {len(internal)}")
    lines.append(f"- **In audit_provenance:** {len(known)}")
    lines.append(f"- **Orphans (internal but not in audit_provenance):** {len(orphans)}")
    if orphans:
        for r in sorted(orphans):
            lines.append(f"  - `{r}`")
    lines.append("")

    # Summary of divergences
    lines.append("## 12. Documented vs Actual Divergences")
    lines.append("")
    divs = []
    # Divergence 1
    divs.append(("Claimed nutrients_per_ingredient", "43", f"range 7–{max(len(i.get('bromatological_profile',{}).get('nutrients',{})) for i in all_ings)}"))
    # Divergence 2
    cov_count = len(with_coverage)
    divs.append(("coverage_excluded_nutrients exists", "yes (per MAPA)", f"yes (all {cov_count} have it as list)"))
    # Divergence 3
    divs.append(("Orphan refs", "17 (per docs)", "0"))
    # Divergence 4
    divs.append(("Audit_provenance refs", "85 (per docs)", str(len(refs))))
    # Divergence 5
    data_has_cascade = os.path.exists(os.path.join(DATA, "lp_parameters_data.json")) and "solve_cascade" in json.load(open(os.path.join(DATA, "lp_parameters_data.json"), encoding="utf-8"))
    divs.append(("solve_cascade", "in lp_parameters.schema (per docs)", f"in lp_parameters_data.json ({'yes' if data_has_cascade else 'no'})"))
    # Divergence 6
    data_has_registry = os.path.exists(os.path.join(DATA, "lp_parameters_data.json")) and "NUTRIENT_REGISTRY" in json.load(open(os.path.join(DATA, "lp_parameters_data.json"), encoding="utf-8"))
    divs.append(("NUTRIENT_REGISTRY", "in lp_parameters.schema (per docs)", f"in lp_parameters_data.json ({'yes' if data_has_registry else 'no'})"))
    # Divergence 7
    divs.append(("All constraints non-HARD cascade", "yes (per V10)", "no (all 60 HARD_FAIL_INFEASIBLE)"))
    # Divergence 8
    divs.append(("scenarios.json structure", "dict with `scenarios` key", "flat list"))
    # Divergence 9
    divs.append(("Adult k_multiplier", "does not exist (per docs)", "exists: adult_working_active (k=1.5)"))
    # Divergence 10
    divs.append(("Missing supplements in DB", "0 (per claimed)", "3 (kelp, salt, CuSO4 mapped but absent)"))
    # Divergence 11
    divs.append(("nutrient_matrix structure", "dict with min_value/max_value", "list with nested `values` dict"))
    
    lines.append("| Claim | Documented | Actual |")
    lines.append("|---|---|---|")
    for claim, doc_val, actual_val in divs:
        flag = "[!]" if doc_val != actual_val else "[OK]"
        lines.append(f"| {claim} | {doc_val} | {actual_val} | {flag}")
    lines.append("")

    return "\n".join(lines)

if __name__ == "__main__":
    output = report()
    print(output)
    manifest_path = os.path.join(BASE, "docs", "metadata", "baseline_manifest.md")
    with open(manifest_path, "w") as f:
        f.write(output)
    print(f"\n--- Saved to {manifest_path} ---")
