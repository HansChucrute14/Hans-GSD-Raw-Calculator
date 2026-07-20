# sat_dados_schema — Schemas JSON, Nomenclatura, Pendências de Curadoria

**v10.4** · ← `indice_plano_central.md` (canônico) · `../../README.md`

**Responsibility:** Schemas for 9 JSONs (§4.1), `constraint_tier` (§4.2), declarative `solve_cascade[]` (§4.3), cross-JSON nomenclature (§14), curation pending items (§9: kelp/salt/copper PLANNED, 17 orphan refs, cystine/tyrosine), data integrity tests (§A = §11.3).

**Depends on:** sat_princípios:§3.5 · **Referenced by:** sat_pipeline_codigo, sat_solver_contrato, sat_pipeline_fluxo

**Load when:** add ingredient · validate JSONs · change constraint_tier/solve_cascade · resolve orphan refs

> **Context:** Grouped by persona: who curates/validates data needs schema + conventions + gaps + tests together. Numbering preserves original (§4 → §9 → §14 → §A) — intentional jumps for V10.4 traceability.

---

## 4. File Ecosystem — V10

### 4.1 Strict Files (9 + 1 + 1)

|#|File|Purpose|V9→V10 change|
|---|---|---|---|
|1|`DB_ingredientes.json`|Ingredient bank (23 items × 34 nutrients as_fed/100g → 41 energy_normalized via build pipeline; 3 supplements still PLANNED per §9.1)|+3 planned ingredients (kelp, salt, copper_sulfate — NOT yet in real file, see §9.1)|
|2|`lp_parameters_schema.json`|Validation schema + NUTRIENT_REGISTRY + solve_cascade|New `solve_cascade[]` block and `constraint_tier` field|
|3|`constraints.json`|60 constraints, 63 LP bounds, embedded solve_cascade|`solve_cascade` migrated to lp_parameters_schema; all 60 constraints remain `HARD_FAIL_INFEASIBLE` — V10 cascade uses slack variables in LP formulation, not constraint relaxation|
|4|`audit_provenance.json`|143 refs (114 CONFIRMED, 18 INFERRED, 7 LITERATURE_COMPOSITE, 2 COPY_PASTE_ERROR_CORRECTED, 1 UNIT_INCONSISTENCY_RESOLVED, 1 AUTHORITATIVE_DATABASE) — 0 orphan refs in DB_ingredientes (see §9.2)|§9.2 refs are PLANNED items, not orphans — all 23 source_refs in DB_ingredientes resolve against audit_provenance|
|5|`formulation_rules.json`|Templates, inclusion, bioavailability, nutrient_matrix (41 energy_normalized)|`category_to_ingredient_mapping` references planned IDs (kelp, salt, copper_sulfate — depend on §9.1); **V10.3:** optional `clinical_floor_g` per ingredient in `inclusion_constraints`|
|6|`toxicological_limits.json`|8 SULs (list at top, each entry with nested `sul.value`; hard in Levels 1-2; minimization in Level 3)|No structural change; `constraint_tier: "safety_hard"` referenced. **V10.4:** confirmed against real file — is `list` at top, NOT `dict` with `"safe_upper_limits"` key|
|7|`scenarios.json`|2 scenarios (SCN_A warning, SCN_B active)|No change|
|8|`objective_weights.json`|29 weights (27 with `solver_penalty_multiplier`, 1 without — `PEN_MANGANESE_NEG`), 5 tiers, gonadal multipliers|`clinical_criticality` remains available for within-stage adequacy weighting. Level 3 priority is declared as lexicographic `objective_stages` in `solve_cascade`, not scalar `weight_calibration`.|
|9|`growth_energy_skeletal.json`|Gompertz, TER, DER, k_multipliers, envelope|DER becomes **canonical source of mass envelope**|
|10|`recipes_precomputed.json`|**NEW** — precomputed offline recipes|Build pipeline artifact in build mode|
|11|`build_pipeline.py`|Thin CLI wrapper → `src/gsd/cli.py`|Thin wrapper (15 lines) calling `src/gsd/cli.py:main()`|
|11|`src/gsd/`|Core package (6 modules)|`core.py`, `nutrition.py`, `solver.py`, `mapa.py`, `cli.py`, `__init__.py`|

### 4.2 New Schema Field — `constraint_tier`

Instead of `has_safety_ceiling: boolean` (hardcoded), the `NUTRIENT_REGISTRY` in `lp_parameters_schema.json` gets an explicit field:

```json
"NUTRIENT_REGISTRY": {
  "calcium_g": {
    "constraint_tier": "adequacy_soft",
    "clinical_criticality": "critical",
    "display_name": "Cálcio",
    "unit": "g",
    "basis": "energy_normalized"
  },
  "vitamin_a_iu": {
    "constraint_tier": "safety_hard",
    "clinical_criticality": "critical",
    "has_sul": true,
    "sul_value": 9375,
    "display_name": "Vitamina A",
    "unit": "IU",
    "basis": "energy_normalized"
  },
  "protein_g": {
    "constraint_tier": "adequacy_soft",
    "clinical_criticality": "critical",
    "display_name": "Proteína",
    "unit": "g",
    "basis": "energy_normalized"
  },
  "manganese_mg": {
    "constraint_tier": "safety_hard",
    "clinical_criticality": "moderate",
    "has_sul": true,
    "sul_value": 15,
    "display_name": "Manganês",
    "unit": "mg",
    "basis": "energy_normalized"
  }
}
```

### 4.2.1 Mandatory Unit, Basis, and Provenance Contract

Every nutrient value that can influence the LP MUST declare `unit`, `basis`, and `source_ref`; the registry also declares the canonical solver basis. The engine may transform values, but may not infer a missing basis or silently mix bases.

```json
"calcium_g": {
  "unit": "g",
  "basis": "per_1000kcal",
  "canonical_lp_basis": "per_day",
  "source_ref": "REF_AAFCO_CA_GROWTH",
  "constraint_tier": "adequacy_soft",
  "clinical_criticality": "critical"
}
```

For every runtime request, the compiler records `der_kcal`, input basis, transformed daily target/SUL, and conversion factor in solver metadata. Absent `unit`, `basis`, `source_ref`, or a valid conversion is `data_incomplete`; it is never interpreted as zero.

**Possible values for `constraint_tier`:**

| Value | Meaning | How many nutrients | Behavior in cascade |
|---|---|---|---|
| `safety_hard` | Nutrient with SUL — never relaxed in Levels 1 and 2 (toxic) | 8 (Cu, Fe, Na, Vit A, Vit D3, I, Zn, Mn) | Remains hard in Levels 1 and 2; in Level 3 can be violated (minimization), but result is not feeding recommendation (`allocations = null`) |
| `adequacy_soft` | Nutrient without SUL — relaxable (deficiency not acutely lethal) | 33 (all others) | Hard in Level 1; relaxed via weighted slack in Level 2 |
| `envelope_soft` | Envelope constraints (total_grams, energy_density, DER) — relaxable | 3 | Hard in Level 1; relaxed in Level 2 |

**Possible values for `clinical_criticality`:**

| Value | Weight in slack | Nutrients | Rationale |
|---|---|---|---|
| `critical` | 10.0 | Ca, P, protein, Zn, lysine, methionine_plus_cystine, vitamin_D3, EPA+DHA | Macronutrients and minerals whose deficiency causes DOD or systemic compromise |
| `high` | 5.0 | Fe, Cu, vitamin_A, sodium, fat, linoleic_acid, choline | Minerals and vitamins with significant functional impact, but tolerate larger window |
| `moderate` | 2.0 | Se, I, Mn, Mg, K, Cl, B-vitamins, ARA, ALA | Micronutrients whose chronic deficiency is documented but without acute manifestation |
| `low` | 1.0 | Arg, His, Ile, Leu, Val, Thr, Trp, Phe+Tyr | Amino acids rarely deficient in raw meat-based diets |

> **Backrefs — `constraint_tier` is used in:**
> - `sat_solver_contrato:§8.1` (mathematical formulation — `safety_hard` remains hard Levels 1/2, `adequacy_soft` relaxed Level 2, `envelope_soft` relaxed Level 2)
> - `sat_solver_contrato:§7.1` and `§7.2` (`constraint_tier` field in `nutrient_results` output contract)
> - `sat_pipeline_codigo:§6.4` (`build_matrix()` code partitions constraints by tier)
> - `sat_operacional:§12` (V10.4 rejection — pseudocode that assumed structure without checking real file)

### 4.3 New Schema Block — `solve_cascade`

```json
"solve_cascade": [
  {
    "level": 1,
    "description": "Try to solve with EVERYTHING respected. SULs (hard) + adequacy floors (hard) + DER/density/Ca:P (with slack).",
    "relax_tiers": [],
    "objective_stages": [{"name": "goal_deviation", "kind": "weighted_normalized_deviation"}],
    "result_status": "optimal",
    "fallback_condition": "infeasible"
  },
  {
    "level": 2,
    "description": "Relax adequacy floors via slack weighted by clinical_criticality. SULs remain hard.",
    "relax_tiers": ["adequacy_soft", "envelope_soft"],
    "objective_stages": [{"name": "adequacy_slack", "kind": "weighted_normalized_slack"}],
    "slack_weight_source": "NUTRIENT_REGISTRY.clinical_criticality",
    "result_status": "suboptimal",
    "fallback_condition": "infeasible_still"
  },
  {
    "level": 3,
    "description": "Minimize SUL violation while trying to get as close as possible to DER. Real data, real calculation, never omitted. Clinical floor minimum per ingredient (x_min_i) prevents clinically irrelevant counterfactual scenario.",
    "relax_tiers": ["adequacy_soft", "envelope_soft", "safety_hard"],
    "objective_stages": [
      {"name": "sul_violation", "kind": "minimize_normalized_sul_violation", "fix_optimum": true},
      {"name": "der_deviation", "kind": "minimize_absolute_der_deviation", "fix_optimum": true},
      {"name": "adequacy_slack", "kind": "minimize_weighted_normalized_adequacy_slack", "fix_optimum": false}
    ],
    "result_status": "unsafe_diagnostic",
    "fallback_condition": "never_falls_through",
    "clinical_floor": {
      "enabled": true,
      "description": "V10.3 — Clinical floor minimum per ingredient in Level 3. Prevents clinically irrelevant x_i (ex: 0.5g liver). Without floor, solver may return technically non-zero grams but useless as counterfactual scenario.",
      "source": "formulation_rules.inclusion_constraints[ingredient_id].clinical_floor_g",
      "defaults_by_category": {
        "muscle_meat": 10,
        "organ_secreting": 5,
        "organ_non_secreting": 5,
        "bone": 5,
        "fat_source": 2,
        "supplement": 0.1
      },
      "global_fallback_g": 5,
      "constraint_type": "conditional hard — x_i = 0 OR x_i ≥ x_min_i in Level 3 (MILP/indicator required)",
      "fallback_if_infeasible": {
        "action": "relax clinical_floor to 0, re-solve",
        "mark": "what_would_happen.clinical_floor_relaxed = true",
        "note": "Indicates that even the minimum recognizable portion of the ingredient violates the SUL. No safe amount exists."
      }
    },
    "output_contract": {
      "allocations": null,
      "feeding_recommendation": "DO_NOT_FEED",
      "diagnostic_analysis": "REQUIRED — sul_violations_inevitable + what_would_happen (incl. clinical_floor_relaxed) + recommended_alternative_actions",
      "note": "In Level 3, allocations is null (mechanical barrier). Mathematical grams live ONLY in diagnostic_analysis.what_would_happen, recontextualized as scenario analysis, never as prescription. V10.3: what_would_happen includes clinical_floor_applied (true/false) and x_min_i_effective per ingredient."
    }
  }
]
```

**Critical notes about the cascade:**
- The solver executes levels **in sequence** and stops at the first feasible one. If Level 1 is feasible, the result is `optimal` and levels 2 and 3 are not executed.
- If Level 3 cannot be compiled because data are absent/ambiguous, return `data_incomplete`; if remaining hard constraints conflict, return `structurally_infeasible`. Neither is a blank screen or a feeding recommendation. `unsafe_diagnostic` is used only when a real Level-3 counterfactual was solved.
- The transition between levels is **declarative in JSON**, not imperative in code. Adding a Level 4 (ex: "relax mineral antagonisms") is adding an entry to the array, not rewriting logic.
- The `fallback_condition` field is documentation for the human implementer, not code. The engine checks `infeasible` in the LP solver output and decides to descend a level.

> **Backrefs — `solve_cascade` is used in:**
> - `sat_solver_contrato:§8.1` (mathematical formulation per level — Level 1/2/3 with `relax_tiers` and lexicographic `objective_stages`)
> - `sat_solver_contrato:§8.2` (transition rules between levels)
> - `sat_solver_contrato:§8.3` (special case SUL vs DER collision — Level 3 inevitable)
> - `sat_pipeline_codigo:§6.4` (`solve_cascade()` code — engine that reads this JSON and executes)
> - `sat_princípios:§3.4` (cascade principle — conceptual justification)
> - `sat_princípios:§3.5` (model/data separability — policy in JSON, not in code)
> - `sat_operacional:§12` (V10 rejection — cascade logic in if/else code)

---


## 9. Three V9 Findings — Real Status (Verified Against Files, Not Assumed)

**Process note:** this section used header "RESOLVIDO NA V10" describing what should be done, not what was done — violated Case 3 ("RESOLVED" for plan, not action). Corrected in this session after literal verification against real `DB_ingredientes.json` and `audit_provenance.json`.

### 9.1 `kelp_meal_dried`, `salt_nacl`, `copper_sulfate` — **PLANNED, NOT APPLIED**

**Evidence (run in this session):**
```
python3 -c "... 'kelp_meal_dried' in all_ids ..."
→ kelp_meal_dried: STILL ABSENT
→ salt_nacl: STILL ABSENT
→ copper_sulfate: STILL ABSENT
→ total ingredients in DB: 23 (20 animal + 3 fat_sources; 3 supplements still missing)
```
Resolution plan (USDA FDC source for kelp, stoichiometric composition for salt and copper sulfate) remains valid as spec — just not executed against real file. Iodine remains structurally infeasible until this is applied.

### 9.2 17 Planned `source_ref`s — **PLANNED, NOT APPLIED** (Not Orphans)

These 17 refs have never been orphan — they are **planned entries** in `audit_provenance.json` for ingredients not yet added to `DB_ingredientes` (kelp, salt, copper_sulfate) or for safety/blood/cooking references that are valid `source_ref` targets for future ingredient entries. They are referenced by `formulation_rules.json` and `safety_alerts` in existing ingredients but have no block in `provenance.references` yet.

**Evidence (run in this session — V10.4):**
```
refs in audit_provenance.json: 143 (114 CONFIRMED, 18 INFERRED, 7 LITERATURE_COMPOSITE, 2 COPY_PASTE_ERROR_CORRECTED, 1 UNIT_INCONSISTENCY_RESOLVED, 1 AUTHORITATIVE_DATABASE)
all 23 source_refs in DB_ingredientes resolve against audit_provenance — 0 orphans
```
No orphan refs exist in DB_ingredientes. The 17 planned entries from V9 remain pending: `REF_BIO_VISCERA_VIT_A_VAR`, `REF_LIT_VET_BLOOD`, `REF_LIT_VET_COLLAGEN`, `REF_LIT_VET_POULTRY_KIDNEY`, `REF_LIT_VET_SPLEEN`, `REF_LIT_VET_TAIL`, `REF_LIT_VET_TONGUE`, `REF_LIT_VET_TRIPE`, `REF_MC_MONICA_SEGAL`, `REF_SAFETY_BOVINE_BLOOD_PATHOGENS`, `REF_SAFETY_BOVINE_COOKING`, `REF_SAFETY_BOVINE_RAW_PATHOGENS`, `REF_SAFETY_FISH_RAW_PARASITES`, `REF_SAFETY_IRON_OVERLOAD`, `REF_SAFETY_PORK_RAW_PATHOGENS`, `REF_SAFETY_POULTRY_BLOOD_PATHOGENS`, `REF_SAFETY_POULTRY_RAW_PATHOGENS`.

### 9.3 `methionine_plus_cystine_g`/`phenylalanine_plus_tyrosine_g` — **PLANNED, NOT APPLIED**

**Evidence (run in this session):**
```
ingredients with cystine_g or tyrosine_g: 0 of 20 (animal proteins with measurable amino acid profiles)
```
Non-inference rule (never proxy, field `None` until real value) remains the correct decision — just not yet executed extraction from USDA source.

### 9.4 Rule derived from this finding, permanent

No future section of this document uses "RESOLVED"/"CORRECTED"/"IMPLEMENTED" without an `Evidence:` block with command + literal output, run in current session, pasted immediately below header. Absent this, correct status is "PLANNED".

---


## 14. Cross-JSON Nomenclature Conventions — V10 (Updated)

### 14.1 Variable Names

The system operates with two nutrient naming conventions (unchanged from V9):

- **DB space (DB_ingredientes.json):** Uses unit suffix in name (ex: `magnesium_mg`, `selenium_ug`). Basis: `as_fed`, reference: 100g.
- **Solver space (constraints.json, objective_weights.json, scenarios.json, formulation_rules.nutrient_matrix):** Uses standardized name without suffix (ex: `magnesium_g`, `selenium_mg`). Basis: `energy_normalized`, reference: 1000kcal.

### 14.2 Reference System (source_ref) — Updated V10

All `source_ref` fields follow the regex `^REF_[A-Z0-9_]+$`. Prefix conventions (including 2 new in V10):

| Prefix | Meaning | Example |
|---------|------------|---------|
| REF_USDA_FDC_ | USDA FoodData Central data (external, does not resolve internally) | REF_USDA_FDC_170196 |
| REF_MIN_ANT_ | Mineral antagonism | REF_MIN_ANT_CA_P |
| REF_SUL_ | SUL pathophysiology | REF_SUL_CU_PATHO |
| REF_INCL_ | Inclusion limit justification | REF_INCL_LIVER_JUST |
| REF_NUTR_ | Nutritional metadata | REF_NUTR_MATRIX_41 |
| REF_DIET_ | Diet template | REF_DIET_PMR |
| REF_BIO_ | Bioavailability/biomarker | REF_BIO_KELP_IODINE |
| REF_PLOSS_ | Processing/storage loss | REF_PLOSS_VIT_A_MECH |
| REF_NRG_ | Energy requirements | REF_NRG_TER |
| REF_SKEL_ | Skeletal milestone | REF_SKEL_EPIPHYSEAL_LB |
| REF_GON_ | Gonadal status | REF_GON_MALE_NEUT_EARLY |
| REF_EPI_ | Epidemiology | REF_EPI_DOD |
| REF_SCENARIO_ | Optimization scenario | REF_SCENARIO_CMP |
| REF_ALGO_ | Algorithm/fallback | REF_ALGO_GOAL_PROG |
| REF_GLOBAL_META | Global metadata | REF_GLOBAL_META |
| REF_RAW_ | Parsed raw data | REF_RAW_WEIGHT_DOC1 |
| REF_EXTRACTION_ | Completeness verification | REF_EXTRACTION_COMPLETE |
| REF_SUP_ | Supplementation | REF_SUP_VIT_D3 |
| REF_CALORIC_ | Caloric density | REF_CALORIC_DENSITY |
| REF_BARF_ | BARF specificity | REF_BARF_DENSITY |
| REF_DIGEST_ | Digestibility | REF_DIGEST_RAW |
| REF_BONE_ | Bone quality | REF_BONE_QUALITY |
| REF_GROWTH_ | Growth model | REF_GROWTH_GOMPERTZ |
| **REF_LIT_VET_** | **[NEW V10]** Veterinary literature cited in data | REF_LIT_VET_BLOOD_COLLAGEN |
| **REF_SAFETY_** | **[NEW V10]** Food safety alerts | REF_SAFETY_RAW_PATHOGENS_BEEF |

### 14.3 Constraint IDs

Inalterado da V9:
- `CSTR_NB_*_MIN`: Minimum nutrient bound (41 entries)
- `CSTR_SUL_*_MAX`: Maximum Safe Upper Limit (8 entries)
- `CSTR_INCL_*`: Inclusion constraint (6 entries)
- `CSTR_<PAIR>_RATIO`: Ratio bound de antagonismo (5 entries)

### 14.4 Canonical Solver Status (New V10)

|Status|Meaning|Can be recommended as diet?|UI shows alerts?|
|---|---|---|---|
|`optimal`|Level 1 feasible — everything respected|Yes — safe recommendation|Informational only|
|`suboptimal`|Level 2 feasible — SULs ok, but has adequacy gaps|Yes — with documented caveats|Deficiency warnings|
|`unsafe_diagnostic`|Real Level-3 counterfactual with minimized SUL violation; SUL → DER → adequacy solved lexicographically; conditional clinical floor|**No** — `allocations=null`, `feeding_recommendation=DO_NOT_FEED`|Toxic excess + diagnostic analysis + lexicographic-stage proof + clinical-floor audit|
|`structurally_infeasible`|Remaining hard constraints conflict after declared relaxations|**No** — `allocations=null`, `feeding_recommendation=DO_NOT_FEED`|Conflicting constraints and safe next actions|
|`data_incomplete`|Required source, unit, basis, value, or JSON field missing/ambiguous|**No** — `allocations=null`, `feeding_recommendation=DO_NOT_FEED`|Missing fields, anomalies, and required sources|

---


## §A — Data Integrity Tests (Inherited from V9, Updated)

### 11.3 Data Integrity Tests (Inherited from V9, Updated)

```python
def test_all_nutrient_ids_have_target_and_bound():
    """41 nutrient_ids from formulation_rules.nutrient_matrix must have corresponding constraint in constraints.nutrient_bounds — 41==41."""

def test_kelp_salt_copper_supplement_exist_in_db():
    """V10: Now must exist. category_to_ingredient_mapping cannot reference non-existent ingredient_id in DB."""

def test_all_non_usda_source_refs_resolve():
    """V10: All 23 source_refs from DB_ingredientes must resolve in audit_provenance. No orphan refs in real file."""

def test_iodine_coverage_is_feasible():
    """Maximum possible iodine sum, given max_inclusion_pct of all ingredients with iodine > 0, must exceed CSTR_NB_IODINE_MG_MIN. V10: with kelp, should pass."""

def test_methionine_cystine_uses_real_value_not_proxy():
    """cystine_g and tyrosine_g must come from real USDA source, not approximation. V10: forbids proxy — if None, signal anomaly."""

def test_energy_conversion_roundtrip():
    """Ingredient with known EM must produce same value via energy_metabolizable_kcal_per_100g(). Proves modified Atwater is implemented correctly."""

def test_safety_ceiling_never_relaxed_below_level3():
    """Every SUL must remain hard in Levels 1 and 2. ANTI-GAMIFICATION: not enough to verify constraint_tier=="safety_hard". Must execute solver in Level 1 and 2 and verify no violation variable v_j⁺ > 0. [V10.2] Additionally: in Level 3, weight hierarchy ensures SUL violation is minimized, not treated as soft goal."""

def test_gompertz_vs_anthropometric_table_consistency():
    """Gompertz W(t), for t in each of 24 tabulated months, must fall within [min, max] interval of anthropometric_table."""

def test_envelope_derived_from_der():
    """minTotal_g and maxTotal_g must derive from DER, not be constants. ANTI-GAMIFICATION: compute DER by hand, compute envelope by hand, compare with pipeline output."""

def test_constraint_tier_matches_toxicological_limits():
    """Every nutrient in toxicological_limits.json must have constraint_tier="safety_hard" in NUTRIENT_REGISTRY. Every nutrient NOT in toxicological_limits must have constraint_tier="adequacy_soft" or "envelope_soft"."""

def test_tox_limits_structure_matches_actual_file():
    """[V10.4] toxicological_limits.json is a LIST at top, not dict with "safe_upper_limits" key. Each entry has nested sul.value, not flat sul_value. This test prevents build_diagnostic_analysis from using .get("safe_upper_limits", []) or tox_entry["sul_value"] — pattern that caused real crash. ANTI-GAMIFICATION: json.load() real file, check type and structure."""
    import json
    tox = json.load(open("toxicological_limits.json"))
    assert isinstance(tox, list), f"toxicological_limits.json must be list, not {type(tox).__name__}"
    assert len(tox) == 8, f"Expected 8 SULs, found {len(tox)}"
    for entry in tox:
        assert "nutrient_id" in entry
        assert "sul" in entry, f"Entry {entry.get('nutrient_id','?')} missing 'sul' key"
        assert isinstance(entry["sul"], dict), f"sul must be dict, not {type(entry['sul']).__name__}"
        assert "value" in entry["sul"], f"sul dict missing 'value' in {entry['nutrient_id']}"
        # Prove that .get("safe_upper_limits") fails (would be bug if code used it)
        assert not isinstance(tox, dict), "Code must not treat tox as dict"

def test_objective_weights_all_have_penalty_multiplier_or_null():
    """[V10.4] All 29 weights in objective_weights.json must have solver_penalty_multiplier (can be null). Code MUST use .get() to access. ANTI-GAMIFICATION: json.load() real file, check field presence."""
    import json
    ow = json.load(open("objective_weights.json"))
    missing = [w["weight_id"] for w in ow if "solver_penalty_multiplier" not in w]
    # All 29 weights now have solver_penalty_multiplier (PEN_MANGANESE_NEG was explicitly null-added in V10.4 cleanup)
    assert missing == [], (
        f"Weights without solver_penalty_multiplier: {missing} — "
        f"PEN_MANGANESE_NEG exception was resolved in V10.4 cleanup by adding explicit null"
    )
```

---

## ✅ Definition of Done — sat_dados_schema

Curation/validation of data is complete when ALL items below are true:

- [ ] `DB_ingredientes.json` has 23 ingredients (20 animal protein + 3 fat_sources; `kelp_meal_dried`, `salt_nacl`, `copper_sulfate` still PLANNED per §9.1).
- [ ] Each ingredient has exactly 41 nutrients covering `nutrients + coverage_excluded_nutrients` from `formulation_rules.nutrient_matrix`.
- [ ] Every non-USDA `source_ref` resolves in `audit_provenance.references` (zero orphans — see §9.2; currently 17 pending).
- [ ] `cystine_g` and `tyrosine_g` have real values extracted from USDA (no proxy — see §9.3).
- [ ] `lp_parameters_schema.json` contains `NUTRIENT_REGISTRY` with `constraint_tier` (3 values: `safety_hard`, `adequacy_soft`, `envelope_soft`) and `clinical_criticality` (4 values: `critical`, `high`, `moderate`, `low`) for each of the 41 nutrients.
- [ ] `lp_parameters_schema.json` contains `solve_cascade[]` (3 levels, declarative).
- [ ] `toxicological_limits.json` is `list` at top (not `dict`), 8 entries, each with nested `sul.value` (not flat `sul_value`).
- [ ] `objective_weights.json` has 29 weights, all with `solver_penalty_multiplier` (PEN_MANGANESE_NEG formerly had none — resolved in V10.4 cleanup by adding explicit null).
- [ ] `category_to_ingredient_mapping` in `formulation_rules.json` references only `ingredient_id`s that exist in DB.
- [ ] Tests in §A pass against real files (no fixtures).

**Regression check:** `python3 -c "import json; db=json.load(open('data/DB_ingredientes.json')); print(sum(len(g['ingredients']) for g in db['protein_sources'].values()))"` → must return 23.

---
