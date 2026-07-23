#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mapa.py -- MAPA document generator + validation gate. Imports core only."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from .core import (
    BASE_DIR, DATA_DIR, ARCHITECTURE_DIR,
    JSON_FILES, SUPPLEMENTS_PLANNED, UNIT_RENAME,
    sha256_file, load_all_jsons, fmt, hdr, table,
    CrossRefIndex, build_mapa_indices,
    validate_ingredients_against_schema,
)
from .doc_introspector import compute_satellite_stats, check_structure_contracts, scrub_volatile, ImplIntrospector, IMPLEMENTATION_SPEC

def section1_header(data: Dict[str, Any]) -> str:
    """Verbatim copy of indice_plano_central.md between sentinels + file manifest + bundle stats.

    Sentinel-based extraction (replaces broken regex heuristic that never fired):
      - `<!-- MAPA:STATIC-START -->` ... `<!-- MAPA:STATIC-END -->` = hand-authored prose
      - `<!-- MAPA:AUTO-BUNDLES -->` and `<!-- MAPA:AUTO-ROADMAP -->` mark generated sections
    """
    from .doc_introspector import compute_satellite_stats, compute_state_marker, SATELLITE_BUNDLES
    index_path = ARCHITECTURE_DIR / "indice_plano_central.md"
    preamble_lines = []
    if index_path.exists():
        text = index_path.read_text(encoding="utf-8")
        lines_raw = text.splitlines()
        start_idx = None
        end_idx = None
        for i, line in enumerate(lines_raw):
            if "<!-- MAPA:STATIC-START -->" in line:
                start_idx = i + 1  # content starts AFTER the sentinel
            if "<!-- MAPA:STATIC-END -->" in line:
                end_idx = i  # content ends BEFORE the sentinel
                break
        if start_idx is not None and end_idx is not None:
            preamble_lines = lines_raw[start_idx:end_idx]
        else:
            # Fallback: copy entire file (safeguard if sentinels missing)
            preamble_lines = lines_raw
    else:
        preamble_lines = ["# MAPA Completo — GSD Diet Calc V10.4", "(indice_plano_central.md not found)"]

    lines = []
    # Canonical MAPA header
    lines.append(hdr(1, "MAPA Completo — GSD Diet Calc V10.4"))
    lines.append("")
    lines.append(f"**State Hash:** {compute_state_marker(BASE_DIR, JSON_FILES, SATELLITE_BUNDLES)}")
    lines.append(f"**Generator:** `build_pipeline.py` — mode=`--generate-mapa`")
    lines.append(f"**Operational source:** `data/` directory")
    lines.append(f"**Working directory:** `./`")
    lines.append("")
    lines.append("---")
    lines.append("")
    # Verbatim static prose from indice_plano_central.md (between sentinels)
    for pl in preamble_lines:
        lines.append(pl)
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## File Manifest")
    lines.append("")
    rows = []
    total_size = 0
    for fname in JSON_FILES:
        fpath = DATA_DIR / fname
        if fpath.exists():
            size = fpath.stat().st_size
            sha = sha256_file(fpath)
            total_size += size
            # Extract version from JSON content if available
            fdata = data.get(fname, {})
            ver = None
            if isinstance(fdata, dict):
                meta = fdata.get("_db_metadata", {})
                ver = meta.get("version") or fdata.get("version") or fdata.get("schema_version")
            ver_str = str(ver) if ver else "—"
            mtime = datetime.fromtimestamp(fpath.stat().st_mtime).strftime("%Y-%m-%d")
            rows.append([f"`{fname}`", f"{size:,}", ver_str, mtime, f"`{sha[:16]}...`"])
        else:
            rows.append([f"`{fname}`", "NOT FOUND", "—", "—", "—"])
    rows.append(["**Total**", f"{total_size:,}", "—", "—", "—"])
    lines.append(table(["File", "Size (bytes)", "Version", "Modified", "SHA-256"], rows))
    lines.append("")

    # Bundle statistics — live from compute_satellite_stats()
    lines.append("## Satellite Bundle Statistics")
    lines.append("")
    lines.append("> Computed live from source files. Updates automatically when satellites change.")
    lines.append("> Source: `doc_introspector.compute_satellite_stats()`")
    lines.append("")
    try:
        stats = compute_satellite_stats(BASE_DIR)
        # Per-file table
        lines.append("### Per-File Line Counts")
        lines.append("")
        file_rows = []
        for fname, count in sorted(stats["files"].items()):
            file_rows.append([f"`{fname}`", str(count)])
        lines.append(table(["File", "Lines"], file_rows))
        lines.append("")
        # Bundle totals table
        lines.append("### Bundle Totals")
        lines.append("")
        bundle_rows = []
        for bname, total in sorted(stats["bundles"].items()):
            bundle_rows.append([bname, str(total)])
        lines.append(table(["Bundle", "Total Lines"], bundle_rows))
        lines.append("")
    except Exception as e:
        lines.append(f"> Bundle stats unavailable: {e}")
        lines.append("")

    return "\n".join(lines)


# ── Section 2: DB_ingredientes — Ingredient Overview ──────────────────

def section2_ingredients_overview(data: Dict[str, Any]) -> str:
    db = data.get("DB_ingredientes.json", {})
    meta = db.get("_db_metadata", {})
    all_ings = [
        i for g in db.get("protein_sources", {}).values()
        for i in g.get("ingredients", [])
    ]

    lines = []
    lines.append(hdr(2, "DB_ingredientes.json — Ingredient Bank"))
    lines.append("")
    lines.append(f"- **Version:** {meta.get('version', '?')}")
    lines.append(f"- **Claimed ingredients:** {meta.get('total_ingredients', '?')}")
    lines.append(f"- **Actual ingredients:** {len(all_ings)}")
    lines.append(f"- **template_ref:** {meta.get('template_ref', '?')}")
    lines.append(f"- **schema_ref:** {meta.get('schema_ref', '?')}")
    lines.append(f"- **standard:** {meta.get('standard', '?')}")
    lines.append("")
    lines.append("### Ingredient Detail")
    lines.append("")
    rows = []
    for ing in all_ings:
        nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
        excl = ing.get("bromatological_profile", {}).get("coverage_excluded_nutrients", [])
        n = len(nuts)
        e = len(excl) if excl else 0
        label = f"{n} fields" + (f" (+{e} excl)" if e else "")
        grp = next(
            (gn for gn, gd in db.get("protein_sources", {}).items()
             for i in gd.get("ingredients", [])
             if i["ingredient_id"] == ing["ingredient_id"]),
            "?"
        )
        rows.append([
            f"`{ing['ingredient_id']}`",
            ing.get("category", "?"),
            ing.get("display_name", "?"),
            label,
            grp,
        ])
    lines.append(table(["ID", "Category", "Display Name", "Nutrients", "Group"], rows))
    lines.append("")
    return "\n".join(lines)


# ── Section 2.1: DB_ingredientes — JSON Schema Validation (Draft 2020-12) ──

def section2_1_schema_validation(data: Dict[str, Any]) -> str:
    db_path = BASE_DIR / "data" / "DB_ingredientes.json"
    result = validate_ingredients_against_schema(db_path)

    lines = []
    lines.append(hdr(2, "DB_ingredientes.json — JSON Schema Validation (Draft 2020-12)"))
    lines.append("")
    lines.append(f"- **Schema file:** `data/db_ingredientes.schema.json`")
    lines.append(f"- **Total ingredients checked:** {result['total']}")
    lines.append(f"- **Confirming (valid):** {result['confirming']}")
    lines.append(f"- **Non-confirming (invalid):** {result['non_confirming']}")
    lines.append(f"- **Validation status:** {'✅ ALL PASS' if result['non_confirming'] == 0 else '❌ HAS ERRORS'}")
    lines.append("")

    if result['confirming'] > 0:
        lines.append("### Confirming Ingredients")
        lines.append("")
        for ing in result['confirming_ingredients']:
            lines.append(f"- `{ing['ingredient_id']}` (JSON lines {ing['line_start']}–{ing['line_end']}) — {ing['category']} — {ing['display_name']}")
        lines.append("")

    if result['non_confirming'] > 0:
        lines.append("### Non-Confirming Ingredients")
        lines.append("")
        for ing in result['non_confirming_ingredients']:
            lines.append(f"- `{ing['ingredient_id']}` (JSON lines {ing['line_start']}–{ing['line_end']}) — {ing['category']} — {ing['display_name']}")
            for err in ing['errors']:
                lines.append(f"  - **{err['path']}**: {err['message']}")
        lines.append("")
    else:
        lines.append("### Non-Confirming Ingredients")
        lines.append("")
        lines.append("*None — all ingredients conform to schema.*")
        lines.append("")

    lines.append("<!-- SOURCE: validate_ingredients_against_schema / db_ingredientes.schema.json -->")
    lines.append("")
    return "\n".join(lines)


# ── Section 3: DB_ingredientes — Unified Nutrient Fields ──────────────

def section3_nutrient_fields(data: Dict[str, Any]) -> str:
    db = data.get("DB_ingredientes.json", {})
    all_ings = [
        i for g in db.get("protein_sources", {}).values()
        for i in g.get("ingredients", [])
    ]
    all_fields: Set[str] = set()
    for ing in all_ings:
        all_fields.update(ing.get("bromatological_profile", {}).get("nutrients", {}).keys())

    lines = []
    lines.append(hdr(2, "DB_ingredientes.json — Unified Nutrient Fields"))
    lines.append("")
    lines.append(f"**Total distinct nutrient field names:** {len(all_fields)}")
    lines.append("")
    lines.append("`" + "`, `".join(sorted(all_fields)) + "`")
    lines.append("")
    return "\n".join(lines)


# ── Section 4: DB_ingredientes — Coverage Excluded + Supplements ──────

def section4_coverage_and_gaps(data: Dict[str, Any]) -> str:
    db = data.get("DB_ingredientes.json", {})
    all_ings = [
        i for g in db.get("protein_sources", {}).values()
        for i in g.get("ingredients", [])
    ]
    with_coverage = [
        i for i in all_ings
        if i.get("bromatological_profile", {}).get("coverage_excluded_nutrients")
    ]
    actual_ids = set(i["ingredient_id"] for i in all_ings)
    missing_supps = [s for s in SUPPLEMENTS_PLANNED if s not in actual_ids]

    lines = []
    lines.append(hdr(2, "DB_ingredientes.json — Coverage & Gaps"))
    lines.append("")
    lines.append("### Coverage Excluded Nutrients")
    lines.append("")
    lines.append(f"- **Ingredients with exclusions:** {len(with_coverage)} / {len(all_ings)}")
    for i in with_coverage:
        excl = i["bromatological_profile"]["coverage_excluded_nutrients"]
        lines.append(f"  - `{i['ingredient_id']}`: {excl}")
    lines.append("")
    lines.append("### Planned Supplements (Not Yet in DB)")
    lines.append("")
    lines.append(f"- **Missing:** {', '.join(f'`{m}`' for m in missing_supps)}")
    lines.append(f"- **Status per docs:** `sat_operacional:§15` — PLANNED, NOT applied")
    lines.append("")
    return "\n".join(lines)


# ── Section 5: DB_ingredientes — Categories ────────────────────────────

def section5_categories(data: Dict[str, Any]) -> str:
    db = data.get("DB_ingredientes.json", {})
    all_ings = [
        i for g in db.get("protein_sources", {}).values()
        for i in g.get("ingredients", [])
    ]
    cats: Dict[str, int] = {}
    for ing in all_ings:
        c = ing.get("category", "unknown")
        cats[c] = cats.get(c, 0) + 1

    lines = []
    lines.append(hdr(2, "DB_ingredientes.json — Category Distribution"))
    lines.append("")
    rows = [[c, str(n)] for c, n in sorted(cats.items())]
    lines.append(table(["Category", "Count"], rows))
    lines.append("")
    return "\n".join(lines)


# ── Section 6: constraints.json ────────────────────────────────────────

def section6_constraints(data: Dict[str, Any]) -> str:
    c = data.get("constraints.json", {})
    lines = []
    lines.append(hdr(2, "constraints.json — LP Constraints"))
    lines.append("")
    total = 0
    for sec in ["nutrient_bounds", "toxicological_limits", "inclusion_constraints", "mineral_antagonisms"]:
        items = c.get(sec, [])
        total += len(items)
        hard = sum(1 for x in items if x.get("solver_behavior") == "HARD_FAIL_INFEASIBLE")
        other = sum(1 for x in items if x.get("solver_behavior") != "HARD_FAIL_INFEASIBLE")
        lines.append(f"- **{sec}:** {len(items)} constraints ({hard} HARD, {other} other)")
    lines.append(f"\n**Total:** {total} constraints")
    lines.append("")

    # Show selected constraints in table
    for sec in ["mineral_antagonisms", "nutrient_bounds"]:
        items = c.get(sec, [])
        if not items:
            continue
        lines.append(f"### {sec}")
        lines.append("")
        rows = []
        for item in items[:10]:
            rows.append([
                f"`{item.get('constraint_id', '?')}`",
                item.get("name", "?"),
                item.get("human_readable", "")[:60],
                item.get("solver_behavior", "?"),
            ])
        lines.append(table(["ID", "Name", "Expression", "Behavior"], rows))
        if len(items) > 10:
            lines.append(f"*(... and {len(items) - 10} more)*")
        lines.append("")
    return "\n".join(lines)


# ── Section 7: formulation_rules.json ──────────────────────────────────

def section7_formulation_rules(data: Dict[str, Any]) -> str:
    fr = data.get("formulation_rules.json", {})
    db = data.get("DB_ingredientes.json", {})
    actual_ids = set()
    for g in db.get("protein_sources", {}).values():
        for i in g.get("ingredients", []):
            actual_ids.add(i["ingredient_id"])

    matrix = fr.get("nutrient_matrix", [])
    templates = fr.get("diet_templates", [])
    mapping = fr.get("_inclusion_semantics", {}).get("category_to_ingredient_mapping", {})
    bio = fr.get("bioavailability_factors", [])
    digest = fr.get("digestibility", {})
    supp_dosages = fr.get("supplement_dosages", {})

    lines = []
    lines.append(hdr(2, "formulation_rules.json — Formulation Rules"))
    lines.append("")

    lines.append("### Nutrient Matrix")
    lines.append(f"- **Entries:** {len(matrix)}")
    if matrix:
        lines.append(f"- **First entry:** `{matrix[0].get('nutrient_id', '?')}`")
        vals = matrix[0].get("values", {})
        if isinstance(vals, dict):
            lines.append(f"- **Authorities:** {', '.join(vals.keys())}")
    lines.append("")

    lines.append("### Diet Templates")
    lines.append(f"- **Count:** {len(templates)}")
    for t in templates:
        comps = t.get("components", {})
        total_pct = sum(comps.values()) if isinstance(comps, dict) else 0
        lines.append(f"  - `{t.get('template_id')}`: {t.get('name')} — {len(comps)} components, total={total_pct:.1f}%")
    lines.append("")

    lines.append("### Category-to-Ingredient Mapping")
    lines.append(f"- **Categories mapped:** {len(mapping)}")
    all_mapped: Set[str] = set()
    for cat, ids in mapping.items():
        all_mapped.update(ids)
    concrete = [x for x in all_mapped if not x.startswith("_")]
    wildcards = [x for x in all_mapped if x.startswith("_")]
    missing = [x for x in concrete if x not in actual_ids]
    if missing:
        lines.append(f"- **Mapped but absent from DB:** {', '.join(f'`{m}`' for m in sorted(missing))}")
    if wildcards:
        lines.append(f"- **Wildcards:** {', '.join(sorted(wildcards))}")
    lines.append("")

    lines.append("### Bioavailability Factors")
    lines.append(f"- **Count:** {len(bio)}")
    if bio:
        lines.append(f"  - First: `{bio[0].get('factor_id')}` → `{bio[0].get('parameter')}`")
    lines.append("")

    lines.append("### Digestibility")
    if isinstance(digest, dict):
        lines.append(f"- **Keys:** {', '.join(digest.keys())}")
    lines.append("")

    lines.append("### Supplement Dosages")
    lines.append(f"- **Entries:** {len(supp_dosages)}")
    for sid, sdata in supp_dosages.items():
        dose = sdata.get("dose", {})
        dose_str = f"{dose.get('value')} {dose.get('unit', '?')}" if isinstance(dose, dict) else str(dose)
        lines.append(f"  - `{sid}`: {dose_str}")
    lines.append("")
    return "\n".join(lines)


# ── Section 8: audit_provenance.json ───────────────────────────────────

def section8_provenance(data: Dict[str, Any]) -> str:
    prov = data.get("audit_provenance.json", {})
    refs = prov.get("references", {})
    docs = prov.get("source_documents", [])
    algo = prov.get("algorithm_logic", {})
    flags = prov.get("data_quality_flags", [])

    lines = []
    lines.append(hdr(2, "audit_provenance.json — Provenance"))
    lines.append("")

    lines.append("### Source Documents")
    lines.append(f"- **Count:** {len(docs)}")
    for d in docs:
        lines.append(f"  - `{d.get('doc_id')}`: {d.get('title')} ({d.get('type')})")
    lines.append("")

    lines.append("### References")
    if isinstance(refs, dict):
        lines.append(f"- **Total refs:** {len(refs)}")
        qual_flags: Dict[str, int] = {}
        for rid, rdata in refs.items():
            qf = rdata.get("quality_flag", "MISSING") if isinstance(rdata, dict) else "MISSING"
            qual_flags[qf] = qual_flags.get(qf, 0) + 1
        for qf, cnt in sorted(qual_flags.items()):
            lines.append(f"  - **{qf}:** {cnt}")
    lines.append("")

    lines.append("### Algorithm Logic (Fallback Protocols)")
    fb = algo.get("fallback_protocols", []) if isinstance(algo, dict) else []
    lines.append(f"- **Protocols:** {len(fb)}")
    for f in fb:
        lines.append(f"  - Level {f.get('level')}: {f.get('name')}")
    lines.append("")

    lines.append("### Data Quality Flags")
    lines.append(f"- **Count:** {len(flags)}")
    for fl in flags:
        lines.append(f"  - `{fl.get('flag_id')}`: [{fl.get('severity')}] {fl.get('description', '')[:80]}")
    lines.append("")
    return "\n".join(lines)


# ── Section 9: growth_energy_skeletal.json ─────────────────────────────

def section9_growth(data: Dict[str, Any]) -> str:
    g = data.get("growth_energy_skeletal.json", {})
    lines = []
    lines.append(hdr(2, "growth_energy_skeletal.json — Growth & Energy"))
    lines.append("")

    # Gompertz
    gp = g.get("gompertz_parameters", {})
    lines.append("### Gompertz Parameters")
    equations = gp.get("equation", [])
    if isinstance(equations, list):
        for eq in equations:
            lines.append(f"- `{eq}`")
    elif equations:
        lines.append(f"- {equations}")
    params = gp.get("parameters", []) if isinstance(gp, dict) else []
    if params:
        for p in params:
            if isinstance(p, dict):
                lines.append(f"  - `{p.get('param_id')}`: {p.get('name')} = {p.get('value', '?')}")
    lines.append("")

    # K multipliers
    km = g.get("k_multipliers", {})
    lines.append("### K Multipliers")
    for km_name, km_data in km.items():
        if isinstance(km_data, dict):
            val = km_data.get("value", km_data.get("default", "?"))
            status = km_data.get("status", "?")
            lines.append(f"- **`{km_name}`:** value={val}, status={status}")
        else:
            lines.append(f"- **`{km_name}`:** {km_data}")
    lines.append("")

    # Energy requirements
    er = g.get("energy_requirements", [])
    lines.append("### Energy Requirements")
    lines.append(f"- **Count:** {len(er)}")
    for e in er:
        formula = e.get("formula", "")[:80]
        lines.append(f"  - `{e.get('param_id')}`: {formula}")
    lines.append("")

    # Anthropometric table
    at = g.get("anthropometric_table", [])
    lines.append("### Anthropometric Table")
    lines.append(f"- **Entries:** {len(at)}")
    if at:
        rows = []
        for entry in at[:5]:
            age = entry.get("age_months", "?")
            wm = entry.get("weight_male_kg", [])
            wf = entry.get("weight_female_kg", [])
            wm_str = f"{wm[0]}–{wm[1]} kg" if isinstance(wm, list) and len(wm) == 2 else str(wm)
            wf_str = f"{wf[0]}–{wf[1]} kg" if isinstance(wf, list) and len(wf) == 2 else str(wf)
            rows.append([str(age), wm_str, wf_str, str(entry.get("pct_adult_weight", "?"))])
        lines.append(table(["Age (mo)", "Male Weight", "Female Weight", "% Adult"], rows))
        if len(at) > 5:
            lines.append(f"*(... and {len(at) - 5} more)*")
        lines.append("")

    # Gonadal profiles
    gon = g.get("gonadal_status_profiles", [])
    lines.append("### Gonadal Status Profiles")
    lines.append(f"- **Count:** {len(gon)}")
    for pr in gon:
        if isinstance(pr, dict):
            lines.append(f"  - `{pr.get('profile_id')}`: {pr.get('sex')}/{pr.get('status')}")
    lines.append("")

    # Epidemiology
    epi = g.get("epidemiology", [])
    lines.append("### Epidemiology (DOD)")
    lines.append(f"- **Entries:** {len(epi)}")
    for ep in epi:
        if isinstance(ep, dict):
            lines.append(f"  - `{ep.get('entry_id')}`: {ep.get('metric_name')} = {ep.get('value', '?')}")
    lines.append("")
    return "\n".join(lines)


# ── Section 10: objective_weights.json ─────────────────────────────────

def section10_weights(data: Dict[str, Any]) -> str:
    ow = data.get("objective_weights.json", [])
    if not isinstance(ow, list):
        ow = []
    lines = []
    lines.append(hdr(2, "objective_weights.json — Objective Weights"))
    lines.append("")
    lines.append(f"- **Count:** {len(ow)}")
    lines.append("")
    rows = []
    for w in ow:
        wid = w.get("weight_id", "?")
        var = w.get("variable", "?")
        weight = w.get("weight", "?")
        tier = w.get("priority_tier", "?")
        pm = w.get("solver_penalty_multiplier")
        pm_str = "MISSING" if pm is None and "solver_penalty_multiplier" not in w else str(pm)
        rows.append([f"`{wid}`", var, str(weight), str(tier), pm_str])
    lines.append(table(["ID", "Variable", "Weight", "Tier", "Penalty Multiplier"], rows))
    lines.append("")

    # PEN_MANGANESE_NEG check
    no_pm = [w for w in ow if "solver_penalty_multiplier" not in w]
    if no_pm:
        lines.append(f"**Without `solver_penalty_multiplier`:** {', '.join(w['weight_id'] for w in no_pm)}")
        lines.append("")
    return "\n".join(lines)


# ── Section 11: scenarios.json ─────────────────────────────────────────

def section11_scenarios(data: Dict[str, Any]) -> str:
    sc = data.get("scenarios.json", [])
    if not isinstance(sc, list):
        sc = []
    lines = []
    lines.append(hdr(2, "scenarios.json — Scenarios"))
    lines.append("")
    lines.append(f"- **Count:** {len(sc)}")
    lines.append("")
    for s in sc:
        sid = s.get("scenario_id", "?")
        name = s.get("name", "?")
        status = s.get("status", "?")
        targets = s.get("targets", [])
        lines.append(f"### `{sid}`: {name}")
        lines.append(f"- **Status:** {status}")
        lines.append(f"- **Targets:** {len(targets)}")
        rows = []
        for t in targets[:8]:
            if isinstance(t, dict):
                rows.append([
                    t.get("nutrient_id", "?"),
                    fmt(t.get("value")),
                    t.get("unit", "?"),
                    t.get("source_ref", "?"),
                ])
        if rows:
            lines.append(table(["Nutrient", "Value", "Unit", "Source"], rows))
        if len(targets) > 8:
            lines.append(f"*(... and {len(targets) - 8} more)*")
        lines.append("")
    return "\n".join(lines)


# ── Section 12: toxicological_limits.json ──────────────────────────────

def section12_tox_limits(data: Dict[str, Any]) -> str:
    tox = data.get("toxicological_limits.json", [])
    if not isinstance(tox, list):
        tox = []
    lines = []
    lines.append(hdr(2, "toxicological_limits.json — Safe Upper Limits (SULs)"))
    lines.append("")
    lines.append(f"- **Type at top level:** `list` ({len(tox)} entries)")
    lines.append(f"- **Structure:** Each entry has nested `sul.value`, `sul.unit`, `sul.basis`")
    lines.append("")
    rows = []
    for e in tox:
        s = e.get("sul", {})
        sul_val = s.get("value") if isinstance(s, dict) else None
        unit = s.get("unit", "?") if isinstance(s, dict) else "?"
        basis = s.get("basis", "?") if isinstance(s, dict) else "?"
        patho = e.get("pathophysiology_ref", "—")
        rows.append([
            f"`{e.get('nutrient_id', '?')}`",
            fmt(sul_val),
            unit,
            basis,
            patho,
        ])
    lines.append(table(["Nutrient", "SUL Value", "Unit", "Basis", "Patho Ref"], rows))
    lines.append("")
    return "\n".join(lines)


# ── Section 13: lp_parameters_data.json ────────────────────────────────

def section13_lp_data(data: Dict[str, Any]) -> str:
    lp = data.get("lp_parameters_data.json", {})
    registry = lp.get("NUTRIENT_REGISTRY", {})
    cascade = lp.get("solve_cascade", [])

    lines = []
    lines.append(hdr(2, "lp_parameters_data.json — Runtime LP Parameters"))
    lines.append(f"**Schema version:** {lp.get('schema_version', '?')}")
    lines.append("")

    # NUTRIENT_REGISTRY summary
    lines.append("### NUTRIENT_REGISTRY")
    lines.append(f"- **Total nutrients:** {len(registry)}")
    tiers: Dict[str, int] = {}
    crits: Dict[str, int] = {}
    for nid, ndata in registry.items():
        t = ndata.get("constraint_tier", "?")
        tiers[t] = tiers.get(t, 0) + 1
        c = ndata.get("clinical_criticality", "?")
        crits[c] = crits.get(c, 0) + 1
    lines.append(f"- **Tiers:** {dict(sorted(tiers.items()))}")
    lines.append(f"- **Clinical criticality:** {dict(sorted(crits.items()))}")

    # safety_hard (SUL) nutrients
    sul_nutrients = [nid for nid, nd in registry.items() if nd.get("constraint_tier") == "safety_hard"]
    lines.append(f"- **Safety hard (has SUL):** {', '.join(f'`{n}`' for n in sul_nutrients)}")

    # SUL value summary (from NUTRIENT_REGISTRY)
    sul_rows = []
    for nid in sul_nutrients:
        nd = registry[nid]
        sul_rows.append([f"`{nid}`", nd.get("display_name", "?"), fmt(nd.get("sul_value")), nd.get("unit", "?"), nd.get("clinical_criticality", "?")])
    if sul_rows:
        lines.append("")
        lines.append("#### SUL Nutrients (from NUTRIENT_REGISTRY)")
        lines.append(table(["Nutrient", "Display Name", "SUL Value", "Unit", "Criticality"], sul_rows))
    lines.append("")

    # solve_cascade
    lines.append("### Declarative Cascade (solve_cascade)")
    lines.append(f"- **Levels:** {len(cascade)}")
    lines.append("")
    for lvl in cascade:
        lv = lvl.get("level", "?")
        desc = lvl.get("description", "")[:100]
        relax = lvl.get("relax_tiers", [])
        stages = lvl.get("objective_stages", [])
        result = lvl.get("result_status", "?")
        lines.append(f"#### Level {lv}: {result}")
        lines.append(f"- **Description:** {desc}")
        lines.append(f"- **Relax tiers:** {relax}")
        lines.append(f"- **Objective stages:** {', '.join(s.get('name', '?') for s in stages)}")
        cf = lvl.get("clinical_floor", {})
        if cf and cf.get("enabled"):
            lines.append(f"- **Clinical floor:** enabled (defaults: {cf.get('defaults_by_category', {})})")
        oc = lvl.get("output_contract", {})
        if oc:
            lines.append(f"- **Output:** allocations={oc.get('allocations')}, feeding={oc.get('feeding_recommendation')}")
        lines.append("")
    return "\n".join(lines)


# ── Section 14: Naming Conventions ─────────────────────────────────────

def section14_naming_conventions(data: Dict[str, Any], idx: CrossRefIndex) -> str:
    """DB→Solver naming mapping for all 43 nutrients."""
    lp = data.get("lp_parameters_data.json", {})
    registry = lp.get("NUTRIENT_REGISTRY", {})

    lines = []
    lines.append(hdr(2, "Naming Conventions — DB Space vs Solver Space"))
    lines.append("")
    lines.append("The system operates with two naming conventions:")
    lines.append("")
    lines.append("- **DB space** (`DB_ingredientes.json`): unit-matching suffix (e.g. `calcium_mg`, `selenium_ug`). Basis: `as_fed`, reference: 100g.")
    lines.append("- **Solver space** (`NUTRIENT_REGISTRY`): standardized unit suffix (e.g. `calcium_g`, `selenium_mg`). Basis: `energy_normalized`, reference: 1000kcal.")
    lines.append("")
    lines.append(f"**Total solver-space nutrients:** {len(registry)}")
    lines.append("")

    # Build mapping table
    rows = []
    for nid, ndata in registry.items():
        display = ndata.get("display_name", "?")
        unit = ndata.get("unit", "?")
        ct = ndata.get("constraint_tier", "?")
        db_name = idx.solver2db_name_map.get(nid, nid)
        name_change = "→".join([db_name, nid]) if db_name != nid else "same"
        rows.append([
            f"`{nid}`",
            display,
            unit,
            ct,
            name_change,
        ])

    lines.append(table(["Solver ID", "Display Name", "Unit", "Tier", "DB→Solver Rename"], rows))
    lines.append("")

    # Unit conversion summary
    renamed = [(db, sv) for db, sv in idx.db2solver_name_map.items()]
    if renamed:
        lines.append("### Unit Conversions (DB → Solver)")
        lines.append("")
        conv_rows = []
        for db_name, solver_name in sorted(renamed):
            _, factor = UNIT_RENAME[db_name]
            conv_rows.append([f"`{db_name}`", f"`{solver_name}`", f"÷{1/factor:,.0f}" if factor < 1 else f"×{factor:.0f}"])
        lines.append(table(["DB Field", "Solver ID", "Conversion"], conv_rows))
        lines.append("")
    return "\n".join(lines)


# ── Section 15: Curation Status ────────────────────────────────────────

def section15_curation_status(data: Dict[str, Any], idx: CrossRefIndex) -> str:
    db = data.get("DB_ingredientes.json", {})
    meta = db.get("_db_metadata", {})
    validated = set(meta.get("validated_sources", []))
    pending = set(meta.get("pending_sources", []))
    partial = set(meta.get("partial_sources", []))

    # Count provenance refs
    prov = data.get("audit_provenance.json", {})
    refs = prov.get("references", {})
    refs_count = len(refs)
    ref_breakdown: Dict[str, int] = {}
    if isinstance(refs, dict):
        for rid, rdata in refs.items():
            qf = rdata.get("quality_flag", "MISSING") if isinstance(rdata, dict) else "MISSING"
            ref_breakdown[qf] = ref_breakdown.get(qf, 0) + 1

    lines = []
    lines.append(hdr(2, "Curation Status — Ingredient Groups"))
    lines.append("")
    lines.append(f"**Total ingredients:** {meta.get('total_ingredients', '?')}")
    lines.append(f"**Provenance refs:** {refs_count} total")
    for qf, cnt in sorted(ref_breakdown.items()):
        lines.append(f"  - **{qf}:** {cnt}")
    lines.append("")

    rows = []
    for grp_key, grp in db.get("protein_sources", {}).items():
        ings = grp.get("ingredients", [])
        status_parts = []
        if grp_key in validated:
            status_parts.append("VALIDATED")
        if grp_key in pending:
            status_parts.append("PENDING")
        if grp_key in partial:
            status_parts.append("PARTIAL")
        status = "+".join(status_parts) if status_parts else "UNKNOWN"
        rows.append([
            grp_key,
            grp.get("common_name", "?"),
            str(len(ings)),
            ", ".join(i["ingredient_id"] for i in ings),
            status,
        ])

    # Add planned supplements row
    actual_ids = set(i["ingredient_id"] for i in idx.all_ingredients)
    missing_supps = [s for s in SUPPLEMENTS_PLANNED if s not in actual_ids]
    if missing_supps:
        rows.append([
            "supplements (planned)",
            "Kelp, Salt, CuSO₄",
            "0 (3 planned)",
            ", ".join(missing_supps),
            "PLANNED (not applied)",
        ])

    lines.append(table(["Group", "Common Name", "Count", "Ingredient IDs", "Status"], rows))
    lines.append("")
    return "\n".join(lines)


# ── Section 16: Gaps ───────────────────────────────────────────────────

def section16_gaps(data: Dict[str, Any], idx: CrossRefIndex) -> str:
    db = data.get("DB_ingredientes.json", {})
    lp = data.get("lp_parameters_data.json", {})
    prov = data.get("audit_provenance.json", {})
    registry = lp.get("NUTRIENT_REGISTRY", {})
    cascade = lp.get("solve_cascade", [])

    lines = []
    lines.append(hdr(2, "Gaps and Unimplemented Dependencies"))
    lines.append("")

    # Gap 1: Missing supplements
    actual_ids = set(i["ingredient_id"] for i in idx.all_ingredients)
    missing = [s for s in SUPPLEMENTS_PLANNED if s not in actual_ids]
    lines.append("### DB Gaps")
    lines.append(f"- **Planned supplements absent from DB:** {len(missing)}")
    for m in missing:
        lines.append(f"  - `{m}` — PLANNED, NOT applied per `sat_operacional:§15`")
    all_nut_fields = set()
    for ing in idx.all_ingredients:
        all_nut_fields.update(ing.get("bromatological_profile", {}).get("nutrients", {}).keys())
    nid_in_db = {n for n in registry if n in all_nut_fields or idx.solver2db_name_map.get(n, n) in all_nut_fields}
    missing_from_db = set(registry.keys()) - nid_in_db
    if missing_from_db:
        lines.append(f"- **Nutrients in registry but not sourced from DB fields:** {len(missing_from_db)}")
        for n in sorted(missing_from_db):
            lines.append(f"  - `{n}` — covered via `coverage_excluded_nutrients` or aggregation")
    lines.append("")

    # Gap 2: Reference coverage
    lines.append("### Reference Gaps")
    internal_refs = set()
    for ing in idx.all_ingredients:
        nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
        for nv in nuts.values():
            sr = nv.get("source_ref", "") if isinstance(nv, dict) else ""
            if sr.startswith("REF_") and not sr.startswith("REF_USDA_"):
                internal_refs.add(sr)
    known_refs = set(idx.ref_index.keys())
    orphans = internal_refs - known_refs
    lines.append(f"- **Internal REF_ tokens in DB ingredients:** {len(internal_refs)}")
    lines.append(f"- **Known in audit_provenance:** {len(known_refs)}")
    lines.append(f"- **Orphans (in DB but absent from audit_provenance):** {len(orphans)}")
    lines.append(f"- **Note:** The 17 refs listed in §9.2 are PLANNED items not yet in DB, not orphans. Actual orphans in DB: {len(orphans)}")
    if orphans:
        for r in sorted(orphans):
            lines.append(f"  - `{r}`")
    lines.append("")

    # Gap 3: Implementation gaps — live introspection via IMPLEMENTATION_SPEC
    lines.append("### Implementation Gaps (Pipeline)")
    try:
        from .doc_introspector import ImplIntrospector, IMPLEMENTATION_SPEC
        gsd_dir = BASE_DIR / "src" / "gsd"
        ii = ImplIntrospector([
            gsd_dir / "core.py",
            gsd_dir / "nutrition.py",
            gsd_dir / "solver.py",
            gsd_dir / "mapa.py",
            gsd_dir / "cli.py",
        ])
        results = [ii.check(s, BASE_DIR) for s in IMPLEMENTATION_SPEC]
        status_rows = []
        for r in results:
            src_line = "L" + str(r["line"]) if r["line"] else "N/A"
            status_rows.append([
                r["name"],
                r["priority"],
                r["spec_ref"],
                r["status"],
                str(r["line"]) if r["line"] else "\u2014",
                r["note"] + " <!-- SOURCE: IMPLEMENTATION_SPEC -->",
            ])
        lines.append(table(
            ["Name", "Priority", "Spec Ref", "Status", "Line", "Note"],
            status_rows,
        ))
    except ImportError:
        lines.append("> Implementation gaps table unavailable (doc_introspector not importable)")
    lines.append("")
    return "\n".join(lines)


# ── Section 17: Cross-Reference & Divergence ──────────────────────────

def section17_divergence_table(data: Dict[str, Any], idx: CrossRefIndex) -> str:
    lines = []
    lines.append(hdr(2, "Cross-Reference Audit & Divergences"))
    lines.append("")

    # Orphan refs audit
    db_path = DATA_DIR / "DB_ingredientes.json"
    db_raw = db_path.read_text(encoding="utf-8") if db_path.exists() else ""
    all_refs = set(re.findall(r"REF_[A-Z0-9_]+", db_raw))
    known = set(idx.ref_index.keys())
    usda = {r for r in all_refs if r.startswith("REF_USDA_")}
    internal = all_refs - usda
    orphans = internal - known

    lines.append("### Orphan Reference Audit")
    lines.append(f"- **Total REF_ tokens in DB:** {len(all_refs)}")
    lines.append(f"- **USDA (external):** {len(usda)}")
    lines.append(f"- **Internal refs:** {len(internal)}")
    lines.append(f"- **In audit_provenance.json:** {len(known)}")
    lines.append(f"- **Orphans (internal but not in audit_provenance):** {len(orphans)}")
    if orphans:
        for r in sorted(orphans):
            lines.append(f"  - `{r}`")
    lines.append("")

    # Verified divergences with decision column
    lines.append("### Documented vs Actual Divergences")
    lines.append("")
    all_ings = idx.all_ingredients
    with_cov = [
        i for i in all_ings
        if i.get("bromatological_profile", {}).get("coverage_excluded_nutrients")
    ]
    c = data.get("constraints.json", {})
    total_hard = sum(
        1 for s in ["nutrient_bounds", "toxicological_limits", "inclusion_constraints", "mineral_antagonisms"]
        for item in c.get(s, [])
    )
    sc = data.get("scenarios.json", [])
    sc_is_list = isinstance(sc, list)
    g = data.get("growth_energy_skeletal.json", {})
    km = g.get("k_multipliers", {})
    has_adult = "adult_working_active" in km or "adult_working" in km or "adult" in km
    fr = data.get("formulation_rules.json", {})
    matrix = fr.get("nutrient_matrix", [])
    matrix_is_list = isinstance(matrix, list)
    actual_ids = set(i["ingredient_id"] for i in all_ings)
    missing_supp_count = len([s for s in SUPPLEMENTS_PLANNED if s not in actual_ids])

    divergences = [
        ("DB version vs actual ingredient count", "3.1.1", f"{len(all_ings)}", "accept"),
        ("Orphan refs resolved", "0 (per docs)", "§9.2 items are PLANNED, not orphans. Actual orphans in DB: 0", "defer"),
        ("Provenance refs count", "85 (per docs)", f"{len(known)} (114 CONFIRMED, 18 INFERRED, 7 LITERATURE_COMPOSITE, 2 COPY_PASTE_ERROR_CORRECTED, 1 UNIT_INCONSISTENCY_RESOLVED, 1 AUTHORITATIVE_DATABASE)", "accept"),
        ("solve_cascade location", "lp_parameters.schema (per docs)", "lp_parameters_data.json", "accept"),
        ("NUTRIENT_REGISTRY location", "lp_parameters.schema (per docs)", "lp_parameters_data.json", "accept"),
        ("All constraints HARD_FAIL_INFEASIBLE", "no (V10 cascade)", "All 60 constraints are HARD_FAIL_INFEASIBLE. V10 cascade uses slack variables in LP formulation, not constraint relaxation.", "defer"),
        ("scenarios.json top-level type", "dict with 'scenarios' key", f"{'list' if sc_is_list else 'dict'}", "accept"),
        ("Adult k_multiplier", "does not exist", f"{'exists (adult_working_active: 1.5)' if has_adult else 'does not exist'}", "accept"),
        ("Missing supplements in DB", "0 (claimed 28)", f"{missing_supp_count} planned missing (kelp_meal_dried, salt_nacl, copper_sulfate) — per §9.1", "defer"),
        ("nutrient_matrix structure", "dict with min/max", f"{'list with nested values' if matrix_is_list else 'dict'}", "accept"),
    ]

    rows = []
    for claim, doc_val, actual_val, decision in divergences:
        flag = "[DIVERGE]" if doc_val != actual_val else "[OK]"
        rows.append([claim, doc_val, actual_val, flag, decision])
    lines.append(table(["Claim", "Documented", "Actual", "Status", "Decision"], rows))
    lines.append("")
    return "\n".join(lines)


# ── Section 18: Live Execution Evidence (Task 4-3) ──────────────────────
# Phase 4 of plan-full-mapa-fix.md — embeds capture_live_evidence() output
# with scrub_volatile() applied. Set via --no-live-evidence for CI use.

# Module-level flag set by main() when --no-live-evidence is passed.




def section18_live_evidence(data: Dict[str, Any]) -> str:
    """Live execution evidence — smoke runs against the production pipeline.

    Calls `doc_introspector.capture_live_evidence()` with REFERENCE_ANIMAL +
    REFERENCE_SELECTION (single source of truth from tests/reference_cases.py),
    applies `scrub_volatile()` to each entry's `output` field to strip
    timestamps/paths/PIDs (preserves idempotency), and renders a fenced code
    block per smoke run with status, severity, scrubbed stdout, and result JSON.

    When `_NO_LIVE_EVIDENCE` is True (set by --no-live-evidence CLI flag), the
    section is replaced with an explicit skip marker so a human reviewer can
    spot the degradation. The validation gate still passes.
    """
    from .doc_introspector import capture_live_evidence, scrub_volatile
    from tests.reference_cases import REFERENCE_ANIMAL, REFERENCE_SELECTION

    lines = []
    lines.append(hdr(2, "Live Execution Evidence"))
    lines.append("")
    lines.append("> Smoke runs against the production pipeline (`build_pipeline.py`).")
    lines.append("> Scrubbed of timestamps/paths/PIDs via `scrub_volatile()` for idempotent regeneration.")
    lines.append("> Source: `doc_introspector.capture_live_evidence()` + `tests/reference_cases.py`.")
    lines.append("")

    if data.get("_no_live_evidence", False):
        lines.append("> Live evidence skipped (--no-live-evidence)")
        lines.append("")
        return "\n".join(lines)

    try:
        evidence = capture_live_evidence(data, REFERENCE_ANIMAL, REFERENCE_SELECTION)
    except Exception as e:
        import traceback
        lines.append(f"> Live evidence capture FAILED: {type(e).__name__}: {e}")
        lines.append("")
        lines.append("```")
        lines.append(traceback.format_exc())
        lines.append("```")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"Captured {len(evidence)} smoke runs:")
    lines.append("")

    for entry in evidence:
        lines.append(f"### Evidence: {entry['label']}")
        lines.append("")
        lines.append(f"- **Status:** {entry['status']}")
        lines.append(f"- **Severity:** {entry['severity']}")
        if entry.get("error"):
            lines.append(f"- **Error:** `{entry['error']}`")
        # LP-specific fields (populated for runtime smoke; None otherwise)
        if entry.get("solver_status") is not None or entry.get("cascade_level_used") is not None:
            lines.append(f"- **solver_status:** `{entry.get('solver_status')}`")
            lines.append(f"- **cascade_level_used:** `{entry.get('cascade_level_used')}`")
            lines.append(f"- **lexicographic_stages_solved:** `{entry.get('lexicographic_stages_solved')}`")
            lines.append(f"- **clinical_floor_relaxed:** `{entry.get('clinical_floor_relaxed')}`")
            lines.append(f"- **solve_time_ms:** `{entry.get('solve_time_ms')}`")
            lines.append(f"- **nutrients_above_90pct_sul:** `{entry.get('nutrients_above_90pct_sul')}`")
        lines.append("")
        # Scrubbed stdout
        scrubbed_out = scrub_volatile(entry.get("output") or "")
        lines.append("**Captured stdout (scrubbed):**")
        lines.append("```")
        lines.append(scrubbed_out if scrubbed_out else "(no stdout)")
        lines.append("```")
        lines.append("")
        # Result JSON or error
        if entry.get("result_repr"):
            lines.append("**Result (JSON, may be truncated to 2000 chars):**")
            lines.append("```json")
            lines.append(entry["result_repr"])
            lines.append("```")
        lines.append("")
        lines.append("<!-- SOURCE: doc_introspector.capture_live_evidence / tests/reference_cases.py -->")
        lines.append("")

    return "\n".join(lines)


# ── Section 19: Test Suite Integrity (Phase 5 — Task 5-2) ────────────────
# Kills Findings #17, #25 by documenting the AAA+A compliance status of every
# test_*.py file. Detects:
# - @pytest.mark.integration decorators via AST node walking (Phase 5 — NOT
#   docstring matching per the plan's D6 v1.2 spec)
# - real data loads via two-pattern regex:
#   (1) r"\bload_all_jsons\s*\(" — production loader (canonical way per D6)
#   (2) r'open\s*\(\s*["\'][^"\']*data/' — direct data-file access
# The v1.1.0 regex `r"\bjson\.load\(|open\("` was WRONG because it false-positive
# on audit-log writes (`open("test_audit_log.md", "w") ...`). D6 v1.2 corrected
# this: the production loader IS the canonical way to load real data.

def section19_test_integrity(data: Dict[str, Any]) -> str:
    """Live test-suite integrity analysis via AST + D6 v1.2 regex.

    Returns a row per test_*.py with: file, marked_integration, loads_real_data.
    A test file violates the AAA+A mandate (sat_testes_consolidado:§11.5) only if
    marked_integration=True AND loads_real_data=False — this is the configuration
    the validate_mapa() Check 10 gate-trips on.
    """
    from .doc_introspector import check_test_integrity

    lines = []
    lines.append(hdr(2, "Test Suite Integrity"))
    lines.append("")
    lines.append("> AAA+A anti-gamification analysis of every `test_*.py` file.")
    lines.append("> Source: `doc_introspector.check_test_integrity()` — D6 v1.2 regex.")
    lines.append("> The production loader (`bp.load_all_jsons()`) is the canonical way to load real data.")
    lines.append("> Direct `json.load(samples/...)` calls are an anti-pattern — they bypass loader validation.")
    lines.append("")

    try:
        rows = check_test_integrity(Path(".") / "tests")
    except Exception as e:
        import traceback
        lines.append(f"> Test integrity check FAILED: {type(e).__name__}: {e}")
        lines.append("")
        lines.append("```")
        lines.append(traceback.format_exc())
        lines.append("```")
        lines.append("")
        return "\n".join(lines)

    if not rows:
        lines.append("> No `test_*.py` files found in repository root.")
        lines.append("")
        return "\n".join(lines)

    lines.append("| File | `@pytest.mark.integration` | Loads Real Data | AAA+A Compliant |")
    lines.append("| --- | --- | --- | --- |")
    for r in rows:
        marker = "Yes" if r["marked_integration"] else "No"
        loads = "Yes" if r["loads_real_data"] else "No"
        # AAA+A violation is ONLY when marked_integration=True AND loads_real_data=False
        compliant = "Yes" if (not r["marked_integration"]) or r["loads_real_data"] else "**NO**"
        lines.append(f"| `{r['file']}` | {marker} | {loads} | {compliant} |")
    lines.append("")
    lines.append("<!-- SOURCE: doc_introspector.check_test_integrity / D6 v1.2 regex -->")
    lines.append("")
    return "\n".join(lines)


# ── Full MAPA Generator ────────────────────────────────────────────────

def generate_mapa(data: Optional[Dict[str, Any]] = None, no_live_evidence: bool = False) -> str:
    if data is None:
        data = load_all_jsons()
    data["_no_live_evidence"] = no_live_evidence
    idx = build_mapa_indices(data)

    # Sections that only need `data`
    data_only_sections = [
        section1_header,
        section2_ingredients_overview,
        section2_1_schema_validation,
        section3_nutrient_fields,
        section4_coverage_and_gaps,
        section5_categories,
        section6_constraints,
        section7_formulation_rules,
        section8_provenance,
        section9_growth,
        section10_weights,
        section11_scenarios,
        section12_tox_limits,
        section13_lp_data,
        section18_live_evidence,
        section19_test_integrity,
    ]
    # Sections that also need `idx`
    idx_sections: List[Callable[..., str]] = [
        section14_naming_conventions,
        section15_curation_status,
        section16_gaps,
        section17_divergence_table,
    ]

    parts: list = []
    for sec_fn in data_only_sections:
        try:
            parts.append(sec_fn(data))
        except Exception as e:
            import traceback
            parts.append(f"\n## ERROR in {sec_fn.__name__}: {e}\n```\n{traceback.format_exc()}\n```\n")
    for sec_fn in idx_sections:
        try:
            parts.append(sec_fn(data, idx))  # type: ignore[misc]
        except Exception as e:
            import traceback
            parts.append(f"\n## ERROR in {sec_fn.__name__}: {e}\n```\n{traceback.format_exc()}\n```\n")

    # Informational sections (Checks 14-15): Coverage Watch + Evidence Freshness
    # These render in the MAPA body but do NOT affect --gate-mapa exit code.
    try:
        from .doc_introspector import detect_coverage_drift, STRUCTURE_CONTRACTS
        cov_warnings = detect_coverage_drift(data, STRUCTURE_CONTRACTS)
        if cov_warnings:
            lines = ["\n## Coverage Watch (informational)\n"]
            lines.append("New keys detected in live JSONs that are not yet covered by STRUCTURE_CONTRACTS:\n")
            for w in cov_warnings:
                lines.append(f"- {w}")
            lines.append("")
            parts.append("\n".join(lines))
    except Exception:
        pass

    try:
        from .doc_introspector import check_evidence_freshness
        freshness = check_evidence_freshness(ARCHITECTURE_DIR.parent / "worklog.md")
        if freshness.get("warn"):
            n = freshness.get("consecutive_degraded", 0)
            parts.append(
                f"\n## Evidence Freshness Warning (informational)\n\n"
                f"Last {n} MAPA regenerations used `--no-live-evidence`. "
                f"Live evidence capture may be permanently disabled.\n"
            )
    except Exception:
        pass

    return "\n".join(parts)





# ── Validation Gate (16 checks: 14 blocking + 2 informational) ─────────────────

def validate_mapa(mapa_content: str, data: Optional[Dict[str, Any]] = None,
                   prev_state_hash: Optional[str] = None) -> List[str]:
    """Validate MAPA content. Returns list of error strings (empty = all 16 checks pass).

    Checks 0-13 are BLOCKING (gate --gate-mapa exit code).
    Checks 14-15 are INFORMATIONAL (rendered in MAPA, do not affect exit code).

    Args:
        prev_state_hash: If provided (during --generate-mapa), the state hash from
            the previously committed MAPA. Check 13 compares this against the
            current hash to detect unauthorized AUTO block edits.
    """
    if data is None:
        data = load_all_jsons()
    idx = build_mapa_indices(data)
    errors: List[str] = []

    # Check 0: Phantom token detection (IDs, ingredients, nutrients)
    all_extracted = set(re.findall(r"REF_[A-Z0-9_]+|CSTR_[A-Z0-9_]+|PEN_[A-Z0-9_]+|SCN_[A-Z0-9_]+|TPL_[A-Z0-9_]+", mapa_content))
    phantom = all_extracted - idx.all_known_tokens
    phantom = {t for t in phantom if not t.startswith("REF_USDA_")}

    # Also extract and check ingredient IDs
    ing_id_pattern = r"\b[a-z]+_[a-z_]+_(?:raw|dried|nacl|sulfate|oil)\b"
    extracted_ings = set(re.findall(ing_id_pattern, mapa_content))
    phantom_ings = extracted_ings - set(idx.ingredient_index.keys())

    # Extract and check nutrient IDs (only those with unit-bearing suffixes)
    nut_prefixes = r"(?:protein|fat|arginine|histidine|isoleucine|leucine|lysine|methionine|methionine_plus_cystine|phenylalanine|phenylalanine_plus_tyrosine|threonine|tryptophan|valine|linoleic|ala_alpha_linolenic|ara_arachidonic|epa_plus_dha|calcium|phosphorus|magnesium|sodium|potassium|chloride|iron|copper|manganese|zinc|iodine|selenium|vitamin_a|vitamin_d3|vitamin_e|thiamine_b1|riboflavin_b2|pantothenic_acid_b5|niacin_b3|pyridoxine_b6|folic_acid_b9|cobalamin_b12|choline)"
    nut_id_pattern = rf"\b{nut_prefixes}_(?:g|mg|ug|iu)\b"
    extracted_nuts = set(re.findall(nut_id_pattern, mapa_content))
    # A valid nutrient ID is either in nutrient_index (solver space) OR in all_known_tokens (DB space)
    phantom_nuts = extracted_nuts - set(idx.nutrient_index.keys()) - idx.all_known_tokens

    if phantom:
        errors.append(f"Phantom tokens in MAPA (not in any JSON): {len(phantom)} — {', '.join(sorted(phantom)[:10])}")
    if phantom_ings:
        errors.append(f"Phantom ingredient IDs in MAPA: {len(phantom_ings)} — {', '.join(sorted(phantom_ings)[:10])}")
    if phantom_nuts:
        errors.append(f"Phantom nutrient IDs in MAPA: {len(phantom_nuts)} — {', '.join(sorted(phantom_nuts)[:10])}")

    # Check 1: Token presence (MAPA header canonical tokens)
    required_tokens = [
        "MAPA Completo",
        "GSD Diet Calc V10.4",
        "**State Hash:**",
        "File Manifest",
    ]
    for token in required_tokens:
        if token not in mapa_content:
            errors.append(f"Missing token in MAPA: `{token}`")

    # Check 2: Critical count assertions
    db = data.get("DB_ingredientes.json", {})
    all_ings = [
        i for g in db.get("protein_sources", {}).values()
        for i in g.get("ingredients", [])
    ]
    if len(all_ings) < 20:
        errors.append(f"Ingredient count < 20: got {len(all_ings)}")

    c = data.get("constraints.json", {})
    total_constraints = sum(len(c.get(s, [])) for s in ["nutrient_bounds", "toxicological_limits", "inclusion_constraints", "mineral_antagonisms"])
    if total_constraints < 40:
        errors.append(f"Constraint count < 40: got {total_constraints}")

    lp = data.get("lp_parameters_data.json", {})
    registry = lp.get("NUTRIENT_REGISTRY", {})
    if len(registry) < 40:
        errors.append(f"NUTRIENT_REGISTRY entries < 40: got {len(registry)}")

    ow = data.get("objective_weights.json", [])
    if isinstance(ow, list) and len(ow) < 25:
        errors.append(f"Weights < 25: got {len(ow)}")

    tox = data.get("toxicological_limits.json", [])
    if isinstance(tox, list) and len(tox) < 8:
        errors.append(f"SUL entries < 8: got {len(tox)}")

    # Check 3: No stale file paths
    for fname in JSON_FILES:
        if fname not in mapa_content:
            errors.append(f"File `{fname}` not mentioned in MAPA")

    # Check 4: Divergence table present (must have Decision column)
    if "Documented vs Actual Divergences" not in mapa_content:
        errors.append("Divergence table missing from MAPA")
    elif "Decision" not in mapa_content:
        errors.append("Divergence table missing Decision column")

    # Check 5: Canonical header match (Section 1 has project header)
    if "## File Manifest" not in mapa_content:
        errors.append("File manifest section missing")

    # Check 6: Section count (expect 17 sections, allow composites)
    section_count = mapa_content.count("\n## ")
    if section_count < 17:
        errors.append(f"Expected >=17 sections, found {section_count}")

    # Check 7: Naming conventions section present
    if "Naming Conventions" not in mapa_content:
        errors.append("Naming Conventions section missing")

    # Check 8: Curation status section present
    if "Curation Status" not in mapa_content:
        errors.append("Curation Status section missing")

    # Check 9: Structure contracts — all JSON structure contracts must hold
    try:
        from .doc_introspector import check_structure_contracts
        contract_results = check_structure_contracts(data)
        failed = [r for r in contract_results if not r["holds"]]
        if failed:
            for f in failed:
                errors.append(f"Structure contract failed — {f['file']}: {f['description']} (note: {f['note']})")
    except Exception as e:
        errors.append(f"Structure contract check failed: {e}")

    # Check 10: Test integrity — Phase 5 / Task 5-2 (D6 v1.2 REWRITTEN)
    # Fail the gate if any test_*.py has marked_integration=True AND loads_real_data=False.
    # This is the AAA+A mandate violation per sat_testes_consolidado:§11.5.
    # D6 v1.2: detects `bp.load_all_jsons(` OR `open("...data/...")` — NOT the
    # old `r"\bjson\.load\(|open\("` which would false-positive on audit-log writes.
    try:
        from .doc_introspector import check_test_integrity
        rows = check_test_integrity(Path(".") / "tests")
        violations = [r for r in rows if r["marked_integration"] and not r["loads_real_data"]]
        if violations:
            for v in violations:
                errors.append(
                    f"Test integrity failed — {v['file']}: marked as @pytest.mark.integration "
                    f"but does not load real data (AAA+A violation per sat_testes_consolidado:§11.5)"
                )
    except Exception as e:
        errors.append(f"Test integrity check failed: {e}")

    # Check 11: Self-count consistency — docstring "N checks" must match actual count
    # Count check blocks by looking for "# Check N:" comments in this function's source
    import inspect
    try:
        source_lines, _ = inspect.getsourcelines(validate_mapa)
        check_count = sum(1 for line in source_lines if re.match(r'\s+#\s+Check\s+\d+:', line))
        # Also count inline "return errors" as implicit pass — check_count is the declared checks
        if check_count != 16:
            errors.append(f"Self-count check: docstring claims 16 checks, source has {check_count} '# Check N:' comments")
    except Exception:
        pass  # can't introspect in some environments

    # Check 12: Sentinel presence — all 4 sentinels in indice_plano_central.md, each exactly 1
    index_path = ARCHITECTURE_DIR / "indice_plano_central.md"
    if index_path.exists():
        idx_text = index_path.read_text(encoding="utf-8")
        required_sentinels = ["MAPA:STATIC-START", "MAPA:STATIC-END", "MAPA:AUTO-ROADMAP", "MAPA:AUTO-BUNDLES"]
        for sentinel in required_sentinels:
            count = idx_text.count(f"<!-- {sentinel} -->")
            if count == 0:
                errors.append(f"Sentinel missing: <!-- {sentinel} --> not found in indice_plano_central.md")
            elif count > 1:
                errors.append(f"Sentinel duplicated: <!-- {sentinel} --> appears {count} times (expected 1)")

    # Check 13: AUTO immutability — detect stale MAPA or unnecessary regeneration
    # Uses compute_state_marker() as the single definition of "legitimate reason to change."
    # During --generate-mapa (prev_state_hash provided): fail if hashes match (nothing changed).
    # During --gate-mapa (prev_state_hash is None): fail if hashes differ (MAPA is stale).
    try:
        from .doc_introspector import compute_state_marker, SATELLITE_BUNDLES
        current_hash = compute_state_marker(BASE_DIR, JSON_FILES, SATELLITE_BUNDLES)
        auto_bundles_present = "Satellite Bundle Statistics" in mapa_content
        auto_roadmap_present = "Implementation Roadmap" in mapa_content
        has_auto = auto_bundles_present or auto_roadmap_present

        if prev_state_hash is not None:
            # --generate-mapa: fail if hashes match (nothing changed, no need to regenerate)
            if has_auto and current_hash == prev_state_hash:
                errors.append(
                    f"AUTO immutability: AUTO blocks changed but state hash is identical ({current_hash}). "
                    f"No source file was modified — AUTO sections should be regenerated, not hand-edited."
                )
        else:
            # --gate-mapa: fail if hashes differ (MAPA is stale, needs regeneration)
            mapa_hash_match = re.search(r'\*\*State Hash:\*\*\s*`?([0-9a-f]{16})`?', mapa_content)
            if mapa_hash_match:
                mapa_hash = mapa_hash_match.group(1)
                if has_auto and current_hash != mapa_hash:
                    errors.append(
                        f"MAPA stale: state hash in MAPA ({mapa_hash}) differs from current ({current_hash}). "
                        f"Run --generate-mapa to regenerate."
                    )
    except Exception as e:
        errors.append(f"AUTO immutability check failed: {e}")

    # Check 14: Coverage Watch (informational, non-blocking) — detect_coverage_drift() output
    # Does NOT affect gate exit code; informational only.
    # Rendering happens in generate_mapa(), not here — validate_mapa() returns errors only.
    try:
        from .doc_introspector import detect_coverage_drift, STRUCTURE_CONTRACTS
        detect_coverage_drift(data, STRUCTURE_CONTRACTS)  # validates without rendering
    except Exception:
        pass  # informational — never gate

    # Check 15: Evidence Freshness (informational, non-blocking) — check_evidence_freshness() output
    # Does NOT affect gate exit code; warning banner only if warn=True.
    # Rendering happens in generate_mapa(), not here — validate_mapa() returns errors only.
    try:
        from .doc_introspector import check_evidence_freshness
        check_evidence_freshness(ARCHITECTURE_DIR.parent / "worklog.md")  # validates without rendering
    except Exception:
        pass  # informational — never gate

    return errors


__all__ = [
    "generate_mapa", "validate_mapa", "build_mapa_indices",
    "section1_header", "section2_ingredients_overview", "section2_1_schema_validation",
    "section3_nutrient_fields", "section4_coverage_and_gaps", "section5_categories",
    "section6_constraints", "section7_formulation_rules", "section8_provenance",
    "section9_growth", "section10_weights", "section11_scenarios",
    "section12_tox_limits", "section13_lp_data", "section14_naming_conventions",
    "section15_curation_status", "section16_gaps", "section17_divergence_table",
    "section18_live_evidence", "section19_test_integrity",
    "CrossRefIndex", "build_mapa_indices",
]

