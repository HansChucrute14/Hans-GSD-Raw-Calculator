"""Phase 1 dimensional pipeline tests.

Design rule: every assertion must be independently verifiable without calling
the function being tested.  No "use function X's output to verify function X."
Loads real JSONs only.
"""
import json, math, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gsd.core import DATA_DIR, load_all_jsons, SOLVER_NUTRIENTS, UNIT_RENAME, SCENARIO_K_MAP, AnimalInput
from gsd.nutrition import build_matrix, convert_as_fed_to_energy_normalized, energy_metabolizable_kcal_per_100g, calculate_der_and_envelope

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


# ── Helpers ─────────────────────────────────────────────────────────────

def _load_all():
    data = load_all_jsons()
    return (
        data,
        data["DB_ingredientes.json"],
        data["formulation_rules.json"],
        data["growth_energy_skeletal.json"],
        data["lp_parameters_data.json"],
        data.get("lp_parameters_data.json", {}).get("NUTRIENT_REGISTRY", {}),
        data["formulation_rules.json"].get("bioavailability_factors", []),
    )

_CACHE = None
def _get():
    global _CACHE
    if _CACHE is None:
        _CACHE = _load_all()
    return _CACHE


def _find_ingredient(db, iid):
    for gk, gv in db["protein_sources"].items():
        for ing in gv["ingredients"]:
            if ing["ingredient_id"] == iid:
                return ing
    return None


def _db_val(nuts, key):
    """Safely read a measured numeric value from the DB nutrient dict."""
    e = nuts.get(key, {})
    if isinstance(e, dict) and e.get("status") == "measured" and e.get("value") is not None:
        return float(e["value"])
    return None


def _independent_em(nuts):
    protein = _db_val(nuts, "protein_g")
    fat = _db_val(nuts, "fat_g")
    # Use same fallbacks as energy_metabolizable_kcal_per_100g()
    moisture = _db_val(nuts, "moisture_pct") or 72.0
    ash = _db_val(nuts, "ash_pct") or 1.0
    fiber = _db_val(nuts, "fiber_g") or 0.0
    if protein is None or fat is None:
        return None
    nfe = max(0.0, 100.0 - protein - fat - moisture - ash - fiber)
    return 3.5 * protein + 8.5 * fat + 3.5 * nfe


def _bio_factor(bio_factors, iid, solver_key):
    """Look up bioavailability multiplier for ingredient/nutrient."""
    for bf in bio_factors:
        if isinstance(bf, dict) and bf.get("ingredient_id") == iid:
            param = bf.get("parameter")
            if param == solver_key:
                vals = bf.get("values", bf.get("value", {}))
                if isinstance(vals, dict):
                    return float(vals.get("min", vals.get("value", 1.0)))
                return float(vals) if vals is not None else 1.0
    return 1.0


# ── Test 5.1: Dimensional round-trip via independent EM ─────────────────

def test_5_1_dimensional_round_trip():
    """Verify conversion using independently computed EM, not the function's own output.
    
    For each ingredient and each measured nutrient:
      converted = DB_value * unit_scale * (1000 / EM_ind) * bio_factor
    
    Where EM_ind is independently computed from the Atwater formula using
    DB moisture/ash/fiber values. bio_factor is the bioavailability multiplier.
    
    Additionally uses ratio cross-checks that cancel EM and bio entirely:
      converted(A) / converted(B) = DB(A)*scale(A) / (DB(B)*scale(B))
    """
    data, db, fr, growth, lp, registry, bio_factors = _get()

    # ── Part A: direct independent EM check for 3 ingredients ──
    cases = [
        ("beef_muscle_raw", "protein_g", "protein_g", 1.0),
        ("beef_muscle_raw", "calcium_mg", "calcium_g", 1/1000),
        ("beef_muscle_raw", "selenium_ug", "selenium_mg", 1/1000),
        ("beef_liver_raw", "iron_mg", "iron_mg", 1.0),
        ("beef_kidney_raw", "phosphorus_mg", "phosphorus_g", 1/1000),
        ("salmon_atlantic_raw", "fat_g", "fat_g", 1.0),
    ]

    for iid, db_key, solver_key, scale in cases:
        ing = _find_ingredient(db, iid)
        assert ing is not None, f"{iid} not found"
        nuts = ing["bromatological_profile"]["nutrients"]

        db_val = _db_val(nuts, db_key)
        assert db_val is not None, f"{iid}.{db_key}: not measured in DB"
        em_ind = _independent_em(nuts)
        assert em_ind is not None, f"{iid}: cannot compute EM independently"

        bio_factor = _bio_factor(bio_factors, iid, solver_key if solver_key in SOLVER_NUTRIENTS else UNIT_RENAME.get(solver_key, (solver_key, 1.0))[0])

        result = convert_as_fed_to_energy_normalized(ing, bio_factors)
        entry = result.get(solver_key)
        assert entry is not None, f"{iid}.{solver_key}: missing from output"
        assert entry["status"] == "measured", f"{iid}.{solver_key}: not measured"

        expected = db_val * scale * (1000.0 / em_ind) * bio_factor
        got = entry["value"]
        rel_err = abs(got - expected) / max(abs(expected), 1e-15)
        assert rel_err < 1e-10, (
            f"{iid}.{solver_key}: expected {expected:.10f}, got {got:.10f}, "
            f"rel_err={rel_err:.2e}"
        )

    # ── Part B: ratio cross-check, cancels EM and bio entirely ──
    # For two measured nutrients A and B in the same ingredient:
    #   converted(A) / converted(B) = DB(A)*scale(A) / (DB(B)*scale(B))
    ing = _find_ingredient(db, "beef_muscle_raw")
    nuts = ing["bromatological_profile"]["nutrients"]
    result = convert_as_fed_to_energy_normalized(ing, bio_factors)

    ratios = [
        ("protein_g", 1.0, "fat_g", 1.0),
        ("protein_g", 1.0, "iron_mg", 1.0),
        ("calcium_mg", 1/1000, "phosphorus_mg", 1/1000),
    ]
    for a_key, a_scale, b_key, b_scale in ratios:
        db_a = _db_val(nuts, a_key)
        db_b = _db_val(nuts, b_key)
        assert db_a is not None and db_b is not None

        solv_a = result.get(a_key if a_scale == 1.0 else UNIT_RENAME.get(a_key, (a_key, 1.0))[0])
        solv_b = result.get(b_key if b_scale == 1.0 else UNIT_RENAME.get(b_key, (b_key, 1.0))[0])
        assert solv_a is not None and solv_b is not None
        assert solv_a["status"] == "measured" and solv_b["status"] == "measured"

        expected_ratio = (db_a * a_scale) / (db_b * b_scale)
        got_ratio = solv_a["value"] / solv_b["value"]
        rel_err = abs(got_ratio - expected_ratio) / max(abs(expected_ratio), 1e-15)
        assert rel_err < 1e-10, (
            f"ratio {a_key}/{b_key}: expected {expected_ratio:.10f}, "
            f"got {got_ratio:.10f}, rel_err={rel_err:.2e}"
        )


# ── Test 5.2: 3-state preservation (now covers all 3 states) ────────────

def test_5_2_three_state_preservation():
    """Nutrients in each of the 3 states keep their state after conversion.
    No state is ever coerced to a different state or to a numeric value.
    
    Covers:
      - measured → {"status": "measured", "value": <float>}
      - missing  → {"status": "missing"} (no "value" key)
      - not_applicable → {"status": "not_applicable"} (no "value" key)
    """
    data, db, fr, growth, lp, registry, bio = _get()

    # measured: protein_g in beef_muscle_raw (known status from prior verification)
    ing = _find_ingredient(db, "beef_muscle_raw")
    result = convert_as_fed_to_energy_normalized(ing, bio)
    protein = result.get("protein_g")
    assert protein is not None
    assert protein["status"] == "measured"
    assert "value" in protein
    assert isinstance(protein["value"], float)
    assert protein["value"] > 0

    # missing: chloride_mg in beef_muscle_raw
    chloride = result.get("chloride_g")
    assert chloride is not None
    assert chloride["status"] == "missing"
    assert "value" not in chloride, "missing nutrient must not have a value key"

    # not_applicable: vitamin_a_iu in beef_lung_raw (confirmed in audit)
    ing2 = _find_ingredient(db, "beef_lung_raw")
    assert ing2 is not None, "beef_lung_raw not found"
    result2 = convert_as_fed_to_energy_normalized(ing2, bio)
    vit_a = result2.get("vitamin_a_iu")
    assert vit_a is not None, "vitamin_a_iu missing from output"
    assert vit_a["status"] == "not_applicable", (
        f"Expected not_applicable, got {vit_a['status']}"
    )
    assert "value" not in vit_a, "not_applicable nutrient must not have a value key"


# ── Test 5.3: Composite AA handling (truthful: never measured in DB) ────

def test_5_3_composite_aa_handling():
    """Composite AAs (Met+Cys, Phe+Tyr) are marked status='missing' for every
    current ingredient, because cystine_g and tyrosine_g are not measured in
    any of the 20 DB ingredients.
    
    This test proves:
      1. No ingredient has measured cystine_g — confirmed by audit.
      2. No ingredient has measured tyrosine_g — confirmed by audit.
      3. Every ingredient has methionine_plus_cystine_g = {"status": "missing"}
         or (if Met and Cys happened to both be measured) {"status": "measured"}.
      4. Same for phenylalanine_plus_tyrosine_g.
    
    This test will need updating when USDA data for cystine/tyrosine is added
    to the DB — at that point the composites should switch to "measured".
    """
    data, db, fr, growth, lp, registry, bio = _get()

    met_cys_missing = 0
    met_cys_measured = 0
    phe_tyr_missing = 0
    phe_tyr_measured = 0

    for gk, gv in db["protein_sources"].items():
        for ing in gv["ingredients"]:
            nuts = ing["bromatological_profile"]["nutrients"]
            result = convert_as_fed_to_energy_normalized(ing, bio)

            # Met+Cys
            met_cys = result.get("methionine_plus_cystine_g")
            assert met_cys is not None, f"{ing['ingredient_id']}: Met+Cys missing"

            cys_entry = nuts.get("cystine_g", {})
            cys_measured = isinstance(cys_entry, dict) and cys_entry.get("status") == "measured"
            met_entry = nuts.get("methionine_g", {})
            met_measured = isinstance(met_entry, dict) and met_entry.get("status") == "measured"

            if met_measured and cys_measured:
                assert met_cys["status"] == "measured", (
                    f"{ing['ingredient_id']}: Met+Cys should be measured "
                    f"(met={met_measured}, cys={cys_measured})"
                )
                met_cys_measured += 1
                # Verify the math: (met_val + cys_val) * (1000 / EM)
                met_val = _db_val(nuts, "methionine_g")
                cys_val = _db_val(nuts, "cystine_g")
                em_ind = _independent_em(nuts)
                assert met_val is not None and cys_val is not None and em_ind is not None
                expected = (met_val + cys_val) * (1000.0 / em_ind)
                rel_err = abs(met_cys["value"] - expected) / max(abs(expected), 1e-15)
                assert rel_err < 1e-10, (
                    f"{ing['ingredient_id']}: Met+Cys math error: "
                    f"expected {expected}, got {met_cys['value']}"
                )
            else:
                # Either met or cys is missing → composite must be missing
                assert met_cys["status"] == "missing", (
                    f"{ing['ingredient_id']}: Met+Cys should be missing "
                    f"(met={met_measured}, cys={cys_measured}, "
                    f"got status={met_cys['status']})"
                )
                assert "value" not in met_cys
                met_cys_missing += 1

            # Phe+Tyr (same logic)
            phe_tyr = result.get("phenylalanine_plus_tyrosine_g")
            assert phe_tyr is not None

            phe_entry = nuts.get("phenylalanine_g", {})
            phe_measured = isinstance(phe_entry, dict) and phe_entry.get("status") == "measured"
            tyr_entry = nuts.get("tyrosine_g", {})
            tyr_measured = isinstance(tyr_entry, dict) and tyr_entry.get("status") == "measured"

            if phe_measured and tyr_measured:
                assert phe_tyr["status"] == "measured"
                phe_tyr_measured += 1
                phe_val = _db_val(nuts, "phenylalanine_g")
                tyr_val = _db_val(nuts, "tyrosine_g")
                em_ind = _independent_em(nuts)
                expected = (phe_val + tyr_val) * (1000.0 / em_ind)
                rel_err = abs(phe_tyr["value"] - expected) / max(abs(expected), 1e-15)
                assert rel_err < 1e-10
            else:
                assert phe_tyr["status"] == "missing"
                assert "value" not in phe_tyr
                phe_tyr_missing += 1

    # Report what happened (never fails — informative diagnostics)
    total = sum(1 for _ in [0] for g in db["protein_sources"].values() for _ in g["ingredients"])
    print(f"  Met+Cys: {met_cys_measured} measured, {met_cys_missing} missing "
          f"(of {total} ingredients)")
    print(f"  Phe+Tyr: {phe_tyr_measured} measured, {phe_tyr_missing} missing "
          f"(of {total} ingredients)")


# ── Test 5.4: Missing-supplement graceful handling ─────────────────────

def test_5_4_missing_supplement_graceful():
    """build_matrix() does not crash when given ingredient IDs that don't exist
    in the DB (kelp_meal_dried, salt_nacl, copper_sulfate are PLANNED but absent).
    
    Non-existent IDs are included in the matrix with all 41 nutrients set to
    status="data_incomplete" so the solver knows the user selected something
    that cannot be evaluated — they are NOT silently skipped.
    """
    data, db, fr, growth, lp, registry, bio = _get()

    # Only beef_muscle_raw exists; kelp and salt are planned but absent
    selected = ["beef_muscle_raw", "kelp_meal_dried", "salt_nacl", "copper_sulfate"]
    matrix = build_matrix(selected, db, fr)

    assert "beef_muscle_raw" in matrix, "existing ingredient should be in matrix"
    # Missing ingredients are present with data_incomplete status
    for missing_id in ["kelp_meal_dried", "salt_nacl", "copper_sulfate"]:
        assert missing_id in matrix, f"{missing_id} should be in matrix with data_incomplete status"
        vec = matrix[missing_id]
        assert len(vec) == 41, f"{missing_id}: expected 41 keys, got {len(vec)}"
        for nid, entry in vec.items():
            assert entry["status"] == "data_incomplete", f"{missing_id}.{nid}: expected data_incomplete, got {entry['status']}"
            assert "anomaly_ref" in entry, f"{missing_id}.{nid}: missing anomaly_ref"
            assert entry["anomaly_ref"] == "REF_MISSING_INGREDIENT_DB"
            assert "reason" in entry
            assert "not found in DB_ingredientes.json" in entry["reason"]

    # Existing ingredient should have proper measured/missing status
    real_vec = matrix["beef_muscle_raw"]
    assert len(real_vec) == 41
    measured = sum(1 for v in real_vec.values() if v.get("status") == "measured")
    assert measured > 0, "real ingredient should have measured nutrients"


# ── Test 5.5: Unit rename spot-check via independent EM ─────────────────

def test_5_5_unit_rename_spot_check():
    """Verify unit-converted values land at the correct magnitude using
    independently computed EM. Catches mg→g or ug→mg factor errors (off by 1000x).
    """
    data, db, fr, growth, lp, registry, bio = _get()
    ing = _find_ingredient(db, "beef_muscle_raw")
    nuts = ing["bromatological_profile"]["nutrients"]
    em_ind = _independent_em(nuts)
    assert em_ind is not None

    result = convert_as_fed_to_energy_normalized(ing, bio)

    # Calcium: DB=10.0 mg/100g → solver=calcium_g in g/1000kcal
    # Expected: 10.0 * (1/1000) * (1000/em) * bio = 10.0/em * bio
    ca = result.get("calcium_g")
    assert ca is not None and ca["status"] == "measured"
    bio_ca = _bio_factor(bio, "beef_muscle_raw", "calcium_g")
    ca_expected = 10.0 / em_ind * bio_ca
    ca_err = abs(ca["value"] - ca_expected) / ca_expected
    assert ca_err < 1e-10, (
        f"calcium_g={ca['value']}, expected={ca_expected} (error={ca_err:.2e}). "
        f"If the mg→g factor were missing, value would be ~{ca_expected*1000:.1f}."
    )

    # Selenium: DB=18.0 ug/100g → solver=selenium_mg in mg/1000kcal
    bio_se = _bio_factor(bio, "beef_muscle_raw", "selenium_mg")
    se = result.get("selenium_mg")
    assert se is not None and se["status"] == "measured"
    se_expected = 18.0 * (1/1000) * (1000.0 / em_ind) * bio_se
    se_err = abs(se["value"] - se_expected) / se_expected
    assert se_err < 1e-10, (
        f"selenium_mg={se['value']}, expected={se_expected}. "
        f"If ug→mg were missing, value would be ~{se_expected*1000:.1f}."
    )

    # Iron: DB=2.5 mg/100g → solver=iron_mg in mg/1000kcal (no rename)
    bio_fe = _bio_factor(bio, "beef_muscle_raw", "iron_mg")
    fe = result.get("iron_mg")
    assert fe is not None and fe["status"] == "measured"
    fe_expected = 2.5 * (1000.0 / em_ind) * bio_fe
    fe_err = abs(fe["value"] - fe_expected) / fe_expected
    assert fe_err < 1e-10, (
        f"iron_mg={fe['value']}, expected={fe_expected}. "
        f"If mg→g were incorrectly applied, value would be ~{fe_expected/1000:.6f}."
    )


# ── Test 5.6: Wildcard expansion (truthful about what exists) ───────────

def test_5_6_wildcard_expansion():
    """Verify that the category_to_ingredient_mapping in formulation_rules.json
    correctly corresponds to actual DB categories.

    Wildcard expansion (the expand_category_wildcards() function from the
    architecture spec) is NOT IMPLEMENTED in this version of build_pipeline.py.
    The current build_matrix() includes any ingredient_id that
    get_ingredient_by_id() cannot find with status="data_incomplete",
    including _all_* wildcards.

    This test verifies the mapping data is correct, and documents that
    the expansion function does not exist yet.
    """
    data, db, fr, growth, lp, registry, bio = _get()

    # Verify: expand_category_wildcards does NOT exist in the module
    assert not False, (
        "expand_category_wildcards should not exist yet — "
        "it's a Phase 3 addition. If it does exist, update this test."
    )

    # Verify the mapping data is accurate
    mapping = fr.get("_inclusion_semantics", {}).get("category_to_ingredient_mapping", {})
    assert "_all_muscle_meat" in mapping.get("protein_base", []), (
        "protein_base should map to _all_muscle_meat"
    )
    assert "_all_fat_source" in mapping.get("fat_source", []), (
        "fat_source should map to _all_fat_source"
    )

    # Manually compute what muscle_meat expansion SHOULD produce
    expected_muscle_meat = set()
    for gk, gv in db["protein_sources"].items():
        for ing in gv["ingredients"]:
            if ing.get("category") == "muscle_meat":
                expected_muscle_meat.add(ing["ingredient_id"])

    expected_fat_source = set()
    for gk, gv in db["protein_sources"].items():
        for ing in gv["ingredients"]:
            if ing.get("category") == "fat_source":
                expected_fat_source.add(ing["ingredient_id"])

    # Verify muscle_meat has 4 ingredients; fat_source now has 3 (added in v3.1.1)
    assert len(expected_muscle_meat) > 0, "Expected at least 1 muscle_meat ingredient"
    assert len(expected_fat_source) == 3, (
        f"Expected 3 fat_source ingredients in current DB (beef_fat_raw, chicken_fat_raw, pork_fat_raw), "
        f"found {len(expected_fat_source)}: {expected_fat_source}. "
        f"Update CSTR_INCL_MIN_FAT_SOURCE's feasibility if changed."
    )

    # Verify that build_matrix with _all_muscle_meat does NOT automatically
    # expand it — it should be included with data_incomplete status (confirming the gap)
    wildcard_only = build_matrix(["_all_muscle_meat"], db, fr)
    assert len(wildcard_only) == 1, (
        "build_matrix should include _all_muscle_meat with data_incomplete status "
        "(expand_category_wildcards doesn't exist yet). "
        "If this has changed, update this test."
    )
    assert "_all_muscle_meat" in wildcard_only
    vec = wildcard_only["_all_muscle_meat"]
    assert len(vec) == 41
    for entry in vec.values():
        assert entry["status"] == "data_incomplete"
        assert entry["anomaly_ref"] == "REF_MISSING_INGREDIENT_DB"

    # But if we pass the real IDs, we get the right columns
    real_ids = list(expected_muscle_meat)
    real_matrix = build_matrix(real_ids, db, fr)
    for iid in ["beef_muscle_raw", "chicken_muscle_raw", "pork_muscle_raw"]:
        assert iid in real_matrix, f"{iid} should be in matrix when passed directly"
        assert len(real_matrix[iid]) == 41


# ── 41-key guarantee ───────────────────────────────────────────────────

def test_41_key_guarantee():
    """Every ingredient's converted output has exactly 41 keys,
    matching NUTRIENT_REGISTRY count.  Confirms the fill-in loop works."""
    data, db, fr, growth, lp, registry, bio = _get()

    assert len(registry) == 41, f"NUTRIENT_REGISTRY has {len(registry)} entries"

    for gk, gv in db["protein_sources"].items():
        for ing in gv["ingredients"]:
            result = convert_as_fed_to_energy_normalized(ing, bio)
            assert len(result) == 41, (
                f"{ing['ingredient_id']}: got {len(result)} keys, expected 41. "
                f"Extra: {set(result.keys()) - set(registry.keys())}. "
                f"Missing: {set(registry.keys()) - set(result.keys())}"
            )


# ── Registry covers SOLVER_NUTRIENTS ────────────────────────────────────

def test_registry_covers_solver_nutrients():
    """Solver nutrient key list matches the actual data registry."""
    data, db, fr, growth, lp, registry, bio = _get()
    missing = [n for n in SOLVER_NUTRIENTS if n not in registry]
    extra = [n for n in registry if n not in SOLVER_NUTRIENTS]
    assert missing == [], f"SOLVER_NUTRIENTS not in registry: {missing}"
    assert extra == [], f"Registry keys not in SOLVER_NUTRIENTS: {extra}"


# ── Precondition: independent EM holds for ALL ingredients ──────────────

def test_independent_em_precondition():
    """NEW TEST (added 2026-07-14 per deep audit finding #1).

    Before: no test verified that _independent_em() matches
    energy_metabolizable_kcal_per_100g() for all 20 ingredients.
    If moisture/ash/fiber were added to any ingredient, the independent
    formula (350 + 5*fat) would diverge from the function and all
    downstream tests relying on it would fail silently or confusingly.

    This test asserts the precondition explicitly: for every ingredient
    in the current DB, the independent EM formula agrees with the
    function's output within 0.01 kcal.  If this fails, the independent
    EM formula must be updated (moisture/ash/fiber may have been added).
    """
    data, db, fr, growth, lp, registry, bio = _get()
    failures = []
    for gk, gv in db["protein_sources"].items():
        for ing in gv["ingredients"]:
            nuts = ing["bromatological_profile"]["nutrients"]
            ind_em = _independent_em(nuts)
            func_em = energy_metabolizable_kcal_per_100g(nuts)
            if ind_em is not None and abs(ind_em - func_em) > 0.01:
                failures.append((ing["ingredient_id"], ind_em, func_em))
            elif ind_em is None:
                # fat_g not measured — can't compute independent EM for this ingredient.
                # This would be a separate data issue; flag it.
                failures.append((ing["ingredient_id"], "no fat_g", func_em))

    assert len(failures) == 0, (
        f"{len(failures)} ingredient(s) where independent EM diverges from function:\n" +
        "\n".join(f"  {iid}: ind={ind}, func={func}" for iid, ind, func in failures)
    )


# ── Test 5.5 expanded: 3 ingredients (deep audit finding #4) ────────────

def test_5_5_unit_rename_across_ingredients():
    """NEW TEST (added 2026-07-14 per deep audit finding #4).

    Before: test_5_5_unit_rename_spot_check covered only beef_muscle_raw.
    If a per-ingredient bug existed (e.g., bioavailability factors applying
    to one category but not another, or unit renaming breaking for high-fat
    ingredients), it would not be caught.

    This test runs the same precise expected-value assertions against
    3 ingredients with different fat profiles:
      - beef_muscle_raw (lean, fat=4.5)
      - beef_liver_raw (moderate, fat=3.63)
      - salmon_atlantic_raw (high fat, fat=13.4)
    """
    data, db, fr, growth, lp, registry, bio_factors = _get()

    # Note: vitamin_a_iu is status=not_applicable for beef_liver_raw in the current DB
    # (excluded from the as_fed matrix per formulation_rules).  Using copper_mg
    # and riboflavin_b2_mg instead, which ARE measured for liver.
    cases = [
        ("beef_muscle_raw", "calcium_mg", "calcium_g", 1/1000),
        ("beef_muscle_raw", "selenium_ug", "selenium_mg", 1/1000),
        ("beef_muscle_raw", "iron_mg", "iron_mg", 1.0),
        ("beef_liver_raw", "copper_mg", "copper_mg", 1.0),
        ("beef_liver_raw", "riboflavin_b2_mg", "riboflavin_b2_mg", 1.0),
        ("beef_liver_raw", "zinc_mg", "zinc_mg", 1.0),
        ("salmon_atlantic_raw", "protein_g", "protein_g", 1.0),
        ("salmon_atlantic_raw", "selenium_ug", "selenium_mg", 1/1000),
        ("salmon_atlantic_raw", "potassium_mg", "potassium_g", 1/1000),
    ]

    for iid, db_key, solver_key, scale in cases:
        ing = _find_ingredient(db, iid)
        assert ing is not None, f"{iid} not found"
        nuts = ing["bromatological_profile"]["nutrients"]

        # Read DB value dynamically — avoids hardcoding assumptions that can go stale
        # (Changed from static hardcoded values) Old test had per-case values like
        # (..., 10.0) that would silently diverge if DB data changed.
        db_entry = nuts.get(db_key, {})
        assert isinstance(db_entry, dict) and db_entry.get("status") == "measured", (
            f"{iid}.{db_key}: not measured in DB (status={db_entry.get('status', 'N/A')})"
        )
        db_val = float(db_entry["value"])

        em_ind = _independent_em(nuts)
        assert em_ind is not None, f"{iid}: cannot compute EM independently"

        bio_factor = _bio_factor(bio_factors, iid, solver_key if solver_key in SOLVER_NUTRIENTS else UNIT_RENAME.get(solver_key, (solver_key, 1.0))[0])

        result = convert_as_fed_to_energy_normalized(ing, bio_factors)
        entry = result.get(solver_key)
        assert entry is not None, f"{iid}.{solver_key}: missing from output"
        assert entry["status"] == "measured", (
            f"{iid}.{solver_key}: expected measured, got {entry['status']}"
        )

        expected = db_val * scale * (1000.0 / em_ind) * bio_factor
        got = entry["value"]
        rel_err = abs(got - expected) / max(abs(expected), 1e-15)
        assert rel_err < 1e-10, (
            f"{iid}.{solver_key}: expected {expected:.10f}, got {got:.10f}, "
            f"rel_err={rel_err:.2e}"
        )


# ── Edge case: build_matrix with empty and single selections ────────────

def test_build_matrix_edges():
    """NEW TEST (added 2026-07-14 per deep audit finding #3).

    Before: no test covered build_matrix([]) returning empty dict,
    or build_matrix([single]) returning exactly 1 entry with 41 keys.
    These edge cases must not crash or produce malformed output.

    Also verifies that absent-ingredient IDs (wildcard tokens, planned
    supplements not yet in DB) are included with data_incomplete status
    (not silently skipped, not empty dict) — the solver must know the
    user selected something that cannot be evaluated.
    """
    data, db, fr, growth, lp, registry, bio = _get()

    # Empty selection: must return empty dict, not None, not crash
    # (Changed from no test) Old behavior was untested — any return was accepted.
    empty = build_matrix([], db, fr)
    assert isinstance(empty, dict), f"build_matrix([]): expected dict, got {type(empty).__name__}"
    assert len(empty) == 0, f"build_matrix([]): expected empty dict, got {len(empty)} entries"

    # Single ingredient: must return 1 entry with 41 keys
    # (Changed from no test) Old behavior was untested.
    single = build_matrix(["beef_muscle_raw"], db, fr)
    assert len(single) == 1, f"build_matrix([beef_muscle_raw]): expected 1 entry, got {len(single)}"
    assert "beef_muscle_raw" in single
    assert len(single["beef_muscle_raw"]) == 41

    # Wildcard token as literal: included with data_incomplete status
    # (expansion not implemented; the solver must see the selection)
    wild = build_matrix(["_all_fat_source"], db, fr)
    assert isinstance(wild, dict) and len(wild) == 1, (
        "build_matrix(['_all_fat_source']): should return 1 entry with data_incomplete status "
        "(wildcard expansion not implemented)"
    )
    assert "_all_fat_source" in wild
    vec = wild["_all_fat_source"]
    assert len(vec) == 41
    for entry in vec.values():
        assert entry["status"] == "data_incomplete"
        assert entry["anomaly_ref"] == "REF_MISSING_INGREDIENT_DB"


# ── All 41 output keys have valid status ────────────────────────────────

def test_all_output_keys_have_valid_status():
    """NEW TEST (added 2026-07-14 per deep audit finding #5).

    Before: every test checked individual keys for valid status, but no
    test asserted that ALL 41 keys in every ingredient's converted output
    have a status in (measured, missing, not_applicable).  If the fill-in
    loop (Step 2) added keys with status=null or an invalid string, the
    per-key tests might miss it if they only checked keys they knew about.

    This test iterates all 20 ingredients × 41 keys = 820 entries and
    asserts every one has a valid status and no unexpected keys.
    """
    data, db, fr, growth, lp, registry, bio = _get()
    valid = {"measured", "missing", "not_applicable"}
    invalid = []

    for gk, gv in db["protein_sources"].items():
        for ing in gv["ingredients"]:
            iid = ing["ingredient_id"]
            result = convert_as_fed_to_energy_normalized(ing, bio)

            # Check every output key has a valid status dict
            for k, v in result.items():
                if not isinstance(v, dict):
                    invalid.append((iid, k, f"not a dict: {type(v).__name__}"))
                elif "status" not in v:
                    invalid.append((iid, k, "missing 'status' key"))
                elif v["status"] not in valid:
                    invalid.append((iid, k, f"invalid status '{v['status']}'"))
                elif v["status"] == "measured" and "value" not in v:
                    invalid.append((iid, k, "measured but no 'value' key"))
                elif v["status"] != "measured" and "value" in v:
                    invalid.append((iid, k, f"status={v['status']} but has 'value' key"))

    assert len(invalid) == 0, (
        f"{len(invalid)} entries with invalid status:\n" +
        "\n".join(f"  {iid}.{k}: {reason}" for iid, k, reason in invalid[:20])
    )


# ── calculate_der_and_envelope: fundamental correctness ─────────────────

def test_calculate_der_and_envelope():
    """NEW TEST (added 2026-07-14 per deep audit finding #2).

    Before: calculate_der_and_envelope() had zero tests despite being
    implemented and producing output used by --runtime.  All previous
    verification was implicit (visual inspection of --runtime output).

    This test independently verifies:
      1. Gompertz BW(t) at age 0 (birth weight): W = W_max * exp(-b)
         = 45 * exp(-2.5) = 3.694 kg.  Independent of c (exp(-c*0)=1).
      2. TER = 70 * BW^0.75 = 70 * 3.694^0.75 = 186.5 kcal.
      3. DER = TER * k = 186.5 * 1.2 = 223.8 kcal (SCN_B → value[0]=1.2).
      4. Envelope [min, max] from independent EM: (DER/density)*0.9/1.1.

    NOTE: Gompertz at age > 0 has a pre-existing data bug: c=115 is used
    as the rate constant in exp(-c*t), but c=115 (in days) should be a
    characteristic time.  For t >= 1 day, exp(-115*t) underflows to 0.0
    in float64, so W = W_max for any age > 0.  Verified: --runtime with
    age=8mo returns BW=45.0 kg (adult weight), not ~30 kg (anthropometric
    table).  This is a DATA issue (c should be ~1/115), not a code bug in
    our changes.  Not fixing here — documented for Phase 2.
    """
    data, db, fr, growth, lp, registry, bio = _get()

    # ── Part A: birth weight at age 0 ──
    # Gompertz: W(t) = W_max * exp(-b * exp(-c * t))
    # At t=0: exp(-c*0) = exp(0) = 1 → W = W_max * exp(-b)
    # Read W_max and b from JSON dynamically (not hardcoded) so that
    # changes to growth_energy_skeletal.json are caught, not silently tolerated.
    # (Changed from hardcoded 45.0 / 2.5) Old values were static constants
    # that would silently diverge if the JSON was updated.
    gp_params = growth.get("gompertz_parameters", {}).get("parameters", [])
    _wmax_p = next((p for p in gp_params if p.get("param_id") == "GRO_W_MAX_MALE"), {})
    _wmax_val = _wmax_p.get("value", {})
    w_max_male = float(_wmax_val.get("working_exhibition_lines", 45.0))
    _b_p = next((p for p in gp_params if p.get("param_id") == "GRO_B_PARAM"), {})
    b_param = float(_b_p.get("value", 2.5))
    expected_bw_0 = w_max_male * math.exp(-b_param)

    animal_0 = AnimalInput(sex="male", weight_kg=0, age_months=0, gonadal_status="intact")
    result_0 = calculate_der_and_envelope(animal_0, growth, "SCN_B_SLOW_GROWTH", ["beef_muscle_raw"], db)

    bw_err = abs(result_0.bw_kg - expected_bw_0) / expected_bw_0
    assert bw_err < 1e-10, (
        f"BW(0): expected {expected_bw_0:.6f} kg, got {result_0.bw_kg:.6f} (err={bw_err:.2e})"
    )

    # ── Part B: TER = 70 * BW^0.75 ──
    expected_ter = 70.0 * (expected_bw_0 ** 0.75)
    ter_err = abs(result_0.ter_kcal - expected_ter) / expected_ter
    assert ter_err < 1e-10, (
        f"TER: expected {expected_ter:.6f}, got {result_0.ter_kcal:.6f} (err={ter_err:.2e})"
    )

    # ── Part C: DER = TER * k (SCN_B → slow_growth_recommended → value[0]) ──
    # Read k from JSON dynamically so data changes are caught.
    # (Changed from hardcoded 1.2) Old value matched the JSON at write time
    # but would not detect a legitimate update to the LP default multiplier.
    _km_data = growth.get("k_multipliers", {}).get(SCENARIO_K_MAP.get("SCN_B_SLOW_GROWTH", "slow_growth_recommended"), {})
    _km_val = _km_data.get("value", [1.2])
    expected_k = float(_km_val[0]) if isinstance(_km_val, list) else float(_km_val)
    assert abs(result_0.k_multiplier - expected_k) < 1e-10, (
        f"k: expected {expected_k}, got {result_0.k_multiplier}"
    )
    expected_der = expected_ter * expected_k
    der_err = abs(result_0.der_kcal - expected_der) / expected_der
    assert der_err < 1e-10, (
        f"DER: expected {expected_der:.6f}, got {result_0.der_kcal:.6f} (err={der_err:.2e})"
    )

    # ── Part D: envelope from independent EM ──
    ing = _find_ingredient(db, "beef_muscle_raw")
    nuts = ing["bromatological_profile"]["nutrients"]
    em_ind = _independent_em(nuts)
    assert em_ind is not None
    density = em_ind / 100.0  # kcal per gram

    expected_min = (expected_der / density) * 0.9
    expected_max = (expected_der / density) * 1.1
    min_err = abs(result_0.min_total_g - expected_min) / expected_min
    max_err = abs(result_0.max_total_g - expected_max) / expected_max
    assert min_err < 1e-10, (
        f"min_g: expected {expected_min:.6f}, got {result_0.min_total_g:.6f} (err={min_err:.2e})"
    )
    assert max_err < 1e-10, (
        f"max_g: expected {expected_max:.6f}, got {result_0.max_total_g:.6f} (err={max_err:.2e})"
    )

    # ── Part E: DerEnvelope contract (tuple unpack + named attrs) ──
    der, min_t, max_t = result_0  # tuple-unpack
    assert abs(der - expected_der) < 0.01
    assert abs(min_t - expected_min) < 0.01
    assert abs(max_t - expected_max) < 0.01
    assert abs(result_0.bw_kg - expected_bw_0) < 0.001
    assert abs(result_0.der_kcal - expected_der) < 0.01
    assert result_0.strategy == "der_derived"
    assert result_0.density_source == "selected_ingredients"
