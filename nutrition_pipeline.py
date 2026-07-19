#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nutrition_pipeline.py -- DER/Gompertz/matrix build. Imports core only."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import math

from core import (
    _get_param, _resolve_breed_value, DerEnvelope, AnimalInput,
    get_measured_value, validate_ingredients_against_schema, UNIT_RENAME,
    BASE_DIR, SOLVER_NUTRIENTS, SCENARIO_K_MAP, SUPPLEMENTS_PLANNED,
    VALID_NUTRIENT_STATUSES,
)

def validate_inputs(data: dict) -> None:
    """Raise AssertionError if any of the 6 assertions (a-f) fail."""
    db = data.get("DB_ingredientes.json", {})
    prov = data.get("audit_provenance.json", {})
    schema = data.get("lp_parameters_data.json", {})
    fr = data.get("formulation_rules.json", {})

    all_ings = [
        i for g in db.get("protein_sources", {}).values()
        for i in g.get("ingredients", [])
    ]

    # a) 43 nutrient keys per ingredient (including composite pairs)
    for ing in all_ings:
        nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
        msg = f"{ing['ingredient_id']}: {len(nuts)} nutrient keys"
        assert len(nuts) >= 43, msg
        # Every key must have a 3-state status field
        for k, v in nuts.items():
            assert isinstance(v, dict), f"{ing['ingredient_id']}.{k}: not a dict"
            assert "status" in v, f"{ing['ingredient_id']}.{k}: missing status"
            assert v["status"] in VALID_NUTRIENT_STATUSES, \
                f"{ing['ingredient_id']}.{k}: invalid status '{v['status']}'"

    # b) non-USDA source_refs resolve in audit_provenance
    known_refs = set(prov.get("references", {}).keys())
    for ing in all_ings:
        iid = ing["ingredient_id"]
        nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
        for k, v in nuts.items():
            sr = v.get("source_ref", "")
            if sr and sr.startswith("REF_") and not sr.startswith("REF_USDA_"):
                assert sr in known_refs, f"{iid}.{k}: orphan source_ref '{sr}'"

    # c) valid categories (16+1 from schema enum)
    valid_categories = {
        "muscle_meat", "muscle_organ", "organ_secreting", "organ_non_secreting",
        "connective_tissue", "blood_source", "bone", "cartilage", "fat_source",
        "supplement", "grain", "vegetable", "fruit", "dairy", "egg", "fish",
    }
    for ing in all_ings:
        cat = ing.get("category", "")
        assert cat in valid_categories, f"{ing['ingredient_id']}: invalid category '{cat}'"

    # d) mapped ingredient_ids exist in DB (tolerating planned supplements:
    # kelp_meal_dried, salt_nacl, copper_sulfate are PLANNED, NOT applied
    # per sat_operacional:§15 — do not fail for these)
    mapping = fr.get("_inclusion_semantics", {}).get("category_to_ingredient_mapping", {})
    actual_ids = {i["ingredient_id"] for i in all_ings}
    for cat, ids in mapping.items():
        for iid in ids:
            if not iid.startswith("_") and iid not in SUPPLEMENTS_PLANNED:
                assert iid in actual_ids, f"Mapping {cat} -> '{iid}' not in DB"

    # e) NUTRIENT_REGISTRY covers all 41 solver nutrients
    registry = schema.get("NUTRIENT_REGISTRY", {})
    for nid in SOLVER_NUTRIENTS:
        assert nid in registry, f"NUTRIENT_REGISTRY missing '{nid}'"

    # f) solve_cascade has Level 1 with empty relax_tiers
    cascade = schema.get("solve_cascade", [])
    assert any(
        s.get("level") == 1 and s.get("relax_tiers") == []
        for s in cascade if isinstance(s, dict)
    ), "Level 1 of solve_cascade must have empty relax_tiers"

    # g) Formal JSON Schema validation (Draft 2020-12)
    db_path = BASE_DIR / "data" / "DB_ingredientes.json"
    schema_result = validate_ingredients_against_schema(db_path)
    # Store for MAPA report (non-blocking — validation errors don't raise here,
    # they are reported in MAPA Section 2.1)
    if schema_result["non_confirming"] > 0:
        import warnings
        warnings.warn(
            f"Schema validation: {schema_result['non_confirming']}/{schema_result['total']} ingredients non-conforming",
            UserWarning
        )


# ── §6.4a — calculate_der_and_envelope (items 1, 2, 4) ────────────────

def gompertz_weight(age_months: int, params: list[dict], sex: str, default_breed_line: str = "working_exhibition_lines") -> float:
    """W(t) = W_max × exp(-b × exp(-c × t))
    Decision (item 1): adapter over the parameters[] array-of-objects shape.
    Breed-line default: working_exhibition_lines (both sexes); assistance_dogs
    is only present for male W_max in the JSON — female has only WL line.
    """
    t_days = age_months * 30.44

    w_max_p = _get_param(params, "GRO_W_MAX_MALE" if sex == "male" else "GRO_W_MAX_FEMALE")
    if w_max_p is None:
        raise ValueError(f"W_max param not found for sex={sex}")
    w_max = _resolve_breed_value(w_max_p["value"], default_breed_line)

    b_p = _get_param(params, "GRO_B_PARAM")
    b = _resolve_breed_value(b_p["value"]) if b_p else 2.5

    c_key = "GRO_C_MALE_DAYS" if sex == "male" else "GRO_C_FEMALE_DAYS"
    c_p = _get_param(params, c_key)
    c = _resolve_breed_value(c_p["value"]) if c_p else 115.0

    return w_max * math.exp(-b * math.exp(-c * t_days))


def get_global_density_range_from_db(db: dict) -> tuple[float, float]:
    """Fallback: compute min/max energy density across all DB ingredients."""
    densities = []
    for g in db.get("protein_sources", {}).values():
        for ing in g.get("ingredients", []):
            nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
            em = energy_metabolizable_kcal_per_100g(nuts)
            densities.append(em / 100)
    if not densities:
        return (0.5, 2.5)
    return (min(densities), max(densities))


def calculate_der_and_envelope(
    animal: AnimalInput,
    growth_data: dict,
    scenario_id: str,
    selected_ids: list[str],
    db: dict,
    default_breed_line: str = "working_exhibition_lines",
) -> DerEnvelope:
    """§6.4a mandatory signature. Returns DerEnvelope (item 4) which
    satisfies the mandated 3-tuple contract via __iter__ while also
    exposing all intermediate values as named attributes.

    Scenario→k mapping (item 2): hardcoded via SCENARIO_K_MAP.
    Source: growth_energy_skeletal.json → k_multipliers → scenario's ref
    → note field "LP model default: 1.2" / "LP model alert: 2.0" → value[0].
    """

    # Body weight
    gp = growth_data.get("gompertz_parameters", {})
    params = gp.get("parameters", [])
    if animal.use_gompertz:
        bw = gompertz_weight(animal.age_months, params, animal.sex, default_breed_line)
        bw_source = "gompertz"
    else:
        bw = animal.weight_kg
        bw_source = "informed_weight"

    # TER and DER
    ter = 70.0 * (bw ** 0.75)
    k_ref = SCENARIO_K_MAP.get(scenario_id, "slow_growth_recommended")
    km_data = growth_data.get("k_multipliers", {}).get(k_ref, {})
    km_values = km_data.get("value", [1.2])
    k = km_values[0] if isinstance(km_values, list) else float(km_values)
    der = ter * k

    # Energy density range from selected ingredients
    selected = [get_ingredient_by_id(iid, db) for iid in selected_ids if get_ingredient_by_id(iid, db) is not None]
    if selected:
        densities = []
        for ing in selected:
            nuts = ing.get("bromatological_profile", {}).get("nutrients", {})
            em = energy_metabolizable_kcal_per_100g(nuts)
            densities.append(em / 100)
        min_density, max_density = min(densities), max(densities)
        density_source = "selected_ingredients"
    else:
        min_density, max_density = get_global_density_range_from_db(db)
        density_source = "global_fallback"

    min_total_g = (der / max_density) * 0.9
    max_total_g = (der / min_density) * 1.1
    units = der / 1000.0

    return DerEnvelope(
        bw_kg=bw,
        ter_kcal=ter,
        k_multiplier=k,
        der_kcal=der,
        units_of_1000kcal=units,
        min_total_g=min_total_g,
        max_total_g=max_total_g,
        strategy="der_derived",
        density_source=density_source,
    )


def get_ingredient_by_id(ingredient_id: str, db: dict) -> Optional[dict]:
    """Look up an ingredient by ID across all protein_sources groups."""
    for g in db.get("protein_sources", {}).values():
        for ing in g.get("ingredients", []):
            if ing["ingredient_id"] == ingredient_id:
                return ing
    return None


# ── §6.4 — as_fed→energy_normalized conversion (item 5) ───────────────

def energy_metabolizable_kcal_per_100g(nutrients: dict) -> float:
    """Modified Atwater, AAFCO/pet food standard.
    Accepts either raw DB nutrient dict (3-state entries) or flat
    {key: value} dict already extracted.
    """
    def _val(key, fallback=0.0):
        v = nutrients.get(key)
        if isinstance(v, dict):
            return v.get("value") if v.get("status") == "measured" else fallback
        return float(v) if v is not None else fallback

    protein = _val("protein_g")
    fat = _val("fat_g")
    # Fallbacks for missing proximate analysis data (Phase 1 data gap)
    moisture = _val("moisture_pct", 72.0)  # typical for raw muscle meat
    ash = _val("ash_pct", 1.0)
    fiber = _val("fiber_g", 0.0)

    nfe = max(0.0, 100.0 - protein - fat - moisture - ash - fiber)
    return 3.5 * protein + 8.5 * fat + 3.5 * nfe


def get_bioavailability_factor(
    ingredient_id: str, solver_nutrient_id: str, bio_factors: list
) -> float:
    """Look up bioavailability multiplier for an ingredient/nutrient pair.
    Defaults to 1.0 if no factor is declared.
    """
    for bf in bio_factors if bio_factors else []:
        if isinstance(bf, dict) and bf.get("ingredient_id") == ingredient_id:
            param = bf.get("parameter")
            if param == solver_nutrient_id:
                vals = bf.get("values", bf.get("value", {}))
                if isinstance(vals, dict):
                    return float(vals.get("min", vals.get("value", 1.0)))
                return float(vals) if vals is not None else 1.0
    return 1.0


def convert_as_fed_to_energy_normalized(
    ingredient: dict, bio_factors: list, default_breed_line: str = "working_exhibition_lines"
) -> dict[str, dict]:
    """Convert a single ingredient's 3-state nutrient entries from
    as_fed/100g → energy_normalized/1000kcal.

    Respects the real 3-state contract (item 5):
      - status="measured" → output {"status": "measured", "value": <float>}
      - status="missing"/"not_applicable" → output {"status": status}, no "value" key.
      - Every NUTRIENT_REGISTRY key (41 total) is guaranteed present in the
        output dict, even if absent from the DB entirely for this ingredient.
      - Composite pairs (methionine_plus_cystine_g, etc.) computed from
        individual measured amino acids.
    """
    nuts = ingredient.get("bromatological_profile", {}).get("nutrients", {})
    em = energy_metabolizable_kcal_per_100g(nuts)
    if em <= 0:
        return {}

    out: dict[str, dict] = {}

    for db_key, entry in nuts.items():
        if not isinstance(entry, dict):
            continue
        status = entry.get("status", "missing")
        solver_key, _ = UNIT_RENAME.get(db_key, (db_key, 1.0))

        # Skip DB-only keys that have no solver-side counterpart
        # (e.g. biotin_ug, vitamin_k_ug — tracked in DB but not in NUTRIENT_REGISTRY)
        if solver_key not in SOLVER_NUTRIENTS:
            continue

        if status == "measured":
            value = entry.get("value")
            if value is not None:
                _, scale = UNIT_RENAME.get(db_key, (db_key, 1.0))
                converted = float(value) * scale * (1000.0 / em)
                bio = get_bioavailability_factor(
                    ingredient.get("ingredient_id", ""), solver_key, bio_factors
                )
                out[solver_key] = {"status": "measured", "value": converted * bio}
                continue
        out[solver_key] = {"status": status}

    # Composite amino acids — compute from individual measured values
    met_val = get_measured_value(nuts.get("methionine_g"))
    cys_val = get_measured_value(nuts.get("cystine_g"))
    if met_val is not None and cys_val is not None:
        raw = (met_val + cys_val) * (1000.0 / em)
        out["methionine_plus_cystine_g"] = {
            "status": "measured", "value": raw * get_bioavailability_factor(
                ingredient.get("ingredient_id", ""), "methionine_plus_cystine_g", bio_factors
            )
        }

    phe_val = get_measured_value(nuts.get("phenylalanine_g"))
    tyr_val = get_measured_value(nuts.get("tyrosine_g"))
    if phe_val is not None and tyr_val is not None:
        raw = (phe_val + tyr_val) * (1000.0 / em)
        out["phenylalanine_plus_tyrosine_g"] = {
            "status": "measured", "value": raw * get_bioavailability_factor(
                ingredient.get("ingredient_id", ""), "phenylalanine_plus_tyrosine_g", bio_factors
            )
        }

    # Guarantee all 41 NUTRIENT_REGISTRY keys are present
    for registry_key in SOLVER_NUTRIENTS:
        if registry_key not in out:
            out[registry_key] = {"status": "missing"}

    return out


def build_matrix(
    selected_ids: list[str], db: dict, formulation_rules: dict
) -> dict[str, dict[str, dict]]:
    """§6.4a mandatory signature. Return {ingredient_id: {nutrient_id: status_dict}}
    in energy_normalized basis, respecting 3-state contract.

    Missing ingredient IDs (not found in DB) are included with all 43 nutrients
    set to {"status": "data_incomplete", "anomaly_ref": ..., "reason": ...}
    rather than silently omitted — the solver must know the user selected
    something that cannot be evaluated.
    """
    bio_factors = formulation_rules.get("bioavailability_factors", [])
    matrix: dict[str, dict[str, dict]] = {}
    for iid in selected_ids:
        ing = get_ingredient_by_id(iid, db)
        if ing is None:
            matrix[iid] = {
                nid: {
                    "status": "data_incomplete",
                    "anomaly_ref": "REF_MISSING_INGREDIENT_DB",
                    "reason": f"ingredient_id '{iid}' not found in DB_ingredientes.json"
                }
                for nid in SOLVER_NUTRIENTS
            }
            continue
        converted = convert_as_fed_to_energy_normalized(ing, bio_factors)
        matrix[iid] = converted
    return matrix


# ── Phase 2: LP Solver + 3-Level Declarative Cascade ───────────────────

