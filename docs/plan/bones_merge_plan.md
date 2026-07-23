# Bones Merge Plan — DB_ingredientes v3.2.0 → v3.3.0

**Date:** 2026-07-22
**Author:** opencode
**Status:** APPROVED — Ready for execution
**Scope:** Merge 5 bone ingredients from `tempDB/DB_ingredientes_bones_v3.3.0.json` into `data/DB_ingredientes.json`

---

## 0. Scope & Decisions

### Goal

Merge 5 bone ingredients into the unified ingredient DB, producing a v3.3.0 DB with 28 ingredients at 43 nutrients each.

### Confirmed Decisions

1. **Strip `vitamin_c_mg`** from all 5 bones during merge. Rationale: not in solver's 43-nutrient set (`SOLVER_NUTRIENTS` in `nutrition.py`), dogs synthesize endogenously, data preserved in `tempDB/` original.
2. **Create `REF_SEGAL_K9_KITCHEN`** as separate provenance entry. Rationale: different publication from existing `REF_MC_MONICA_SEGAL` (Monica Segal "The K9 Kitchen" vs prior DB reference).

### Source Files

| File | Role |
|---|---|
| `tempDB/DB_ingredientes_bones_v3.3.0.json` | Source — 5 bone ingredients (read-only) |
| `data/DB_ingredientes.json` | Target — main DB, v3.2.0, 23 ingredients, 43 nutrients |
| `data/audit_provenance.json` | Provenance — needs 11 new `source_ref` entries |
| `data/formulation_rules.json` | Config — needs bone `inclusion_limits` + `category_to_ingredient_mapping` |

### Files NOT Modified

`db_ingredientes.schema.json`, `lp_parameters_data.json` (bone goals already configured), `toxicological_limits.json`, `constraints.json`, `objective_weights.json`, `scenarios.json`, `lp_parameters_schema.json`, `growth_energy_skeletal.json`.

---

## Step 0 — Pre-merge Validation (automated, no file edits)

Run a Python validation script that reads both JSONs and reports pass/fail. All checks must pass before Step 1.

### 0a. Schema conformance per bone ingredient

For each of the 5 bone ingredients (`turkey_neck_raw`, `chicken_neck_raw`, `chicken_wing_raw`, `pork_rib_raw`, `chicken_back_raw`):

| Check | Expected | Failure |
|---|---|---|
| Required fields: `ingredient_id`, `display_name`, `category`, `requires_cooking`, `bromatological_profile`, `metadata`, `lp_constraints` | All 7 present | BLOCK |
| `category == "bone"` | True | BLOCK |
| `ingredient_id` matches `^[a-z][a-z0-9_]*$` | Regex match | BLOCK |
| `bromatological_profile.basis == "as_fed"` | True | BLOCK |
| `bromatological_profile.reference_mass_g == 100` | True | BLOCK |
| `nutrients` has ≥ 43 keys (pre-strip) | ≥ 43 | BLOCK |
| Every nutrient has `status` in `{measured, missing, not_applicable}` | All valid | BLOCK |
| `measured` entries have: `value` (number), `unit` (enum), `basis == "as_fed"`, `source_ref` (matches `^REF_[A-Z0-9_]+$`) | All present | BLOCK |
| `not_applicable` entries have: `value == null`, `reason` (string), `anomaly_ref` (matches `^REF_[A-Z0-9_]+$`) | All present | BLOCK |
| `lp_constraints` has: `min_inclusion_pct`, `max_inclusion_pct`, `basis` | All present | BLOCK |
| `metadata` has: `usda_fdc_id`, `data_confidence`, `last_validated` | All present | BLOCK |

### 0b. Collision detection

| Check | Expected | Failure |
|---|---|---|
| No bone `ingredient_id` exists in main DB (all 23 existing) | 0 collisions | BLOCK |
| No bone `ingredient_id` duplicates within bones file | 0 duplicates | BLOCK |

### 0c. Source ref gap analysis

| Check | Expected | Failure |
|---|---|---|
| All unique bone `source_ref` values enumerated | 11 unique refs | INFO |
| Each checked against `audit_provenance.json` top-level `references` keys | All 11 missing | INFO (resolved in Step 1) |

### 0d. Nutrient key parity (post-strip)

| Check | Expected | Failure |
|---|---|---|
| After removing `vitamin_c_mg`, remaining 43 bone keys are subset of main DB's 43 keys | True | BLOCK |

---

## Step 1 — Add 11 Provenance Entries to `audit_provenance.json`

**Structure:** `references` is a top-level dict. Each key = `reference_id`, value = object with `text`, `doc_ids`, `quality_flag`, `line_references`.

### 11 new entries

| `reference_id` | `quality_flag` | Content | Used by |
|---|---|---|---|
| `REF_DOGSFIRST_IE` | `LITERATURE_COMPOSITE` | DogsFirst.ie raw feeding guide — bone-in composition data | protein_g, fat_g, phosphorus for all 5 bones |
| `REF_SEGAL_K9_KITCHEN` | `LITERATURE_COMPOSITE` | Monica Segal, "The K9 Kitchen" — calcium data for whole RMBs | calcium_mg for all 5 bones |
| `REF_PERFECTLYRAWSOME_RMB` | `LITERATURE_COMPOSITE` | Perfectly Rawsome — bone safety guidance | safety_alerts (BONE_SAFETY) |
| `REF_ESTIMATED_ZERO_BONE` | `INFERRED` | Estimated zero for nutrients negligible in bone tissue | biotin_ug, iodine_ug, chloride_mg = 0 |
| `REF_BONE_NA` | `INFERRED` | Not applicable annotation for nutrients absent in raw bone | vitamin_k_ug, vitamin_c_mg `not_applicable` anomaly_ref |
| `REF_NRC_2006` | `CONFIRMED` | NRC 2006 Nutrient Requirements of Dogs and Cats | safety_alerts (Ca:P ratio limits) |
| `REF_BONE_COLLAGEN_VITC` | `INFERRED` | Vitamin C absence rationale for bone/meat tissue | Supports vitamin_c_mg strip decision |
| `REF_BONE_CA_MG_P_BIOAVAILABILITY` | `LITERATURE_COMPOSITE` | Ca, Mg, P bioavailability from raw bone | bioavailability note, inclusion_limits source_ref |
| `REF_BONE_DENSITY_MICROARCHITECTURE` | `LITERATURE_COMPOSITE` | Bone density and microarchitecture data | bone ingredient notes |
| `REF_BONE_MINERAL_VARIABILITY` | `LITERATURE_COMPOSITE` | Mineral content variability across bone types | confidence notes |
| `REF_BONE_ASH_CONTENT` | `LITERATURE_COMPOSITE` | Ash content (mineral fraction) of edible raw bones | bone nutrient notes |

### Entry format

```json
"REF_DOGSFIRST_IE": {
  "text": "DogsFirst.ie raw feeding guide — bone-in composition data for meaty bones",
  "doc_ids": [],
  "quality_flag": "LITERATURE_COMPOSITE",
  "line_references": []
}
```

---

## Step 2 — Prepare Bone Ingredients (transform before inserting)

For each of the 5 bone ingredients, apply:

### 2a. Strip `vitamin_c_mg`

Remove the `vitamin_c_mg` key from `bromatological_profile.nutrients`. Post-strip: 43 nutrient keys.

### 2b. Add `coverage_excluded_nutrients`

Bones file is missing this field. Add standard backward-compat array:

```json
"coverage_excluded_nutrients": [
  "biotin_ug", "chloride_mg", "iodine_ug",
  "vitamin_a_iu", "vitamin_d3_iu", "vitamin_e_iu", "vitamin_k_ug"
]
```

### 2c. Add `bioavailability_factors`

Bones file is missing this field. Add standard animal-source profile:

```json
"bioavailability_factors": {
  "iron_type": "heme",
  "phytate_penalty": false,
  "oxalate_penalty": false
}
```

### 2d. Validate final structure

Each prepared ingredient must match the `Ingredient` schema with all 7 required fields + 2 optional fields now present.

---

## Step 3 — Merge into `DB_ingredientes.json`

### 3a. Add `protein_sources.bones` group

New key under `protein_sources` alongside existing `bovinos`, `aves`, `suinos`, `peixes`, `fat_sources`:

```json
"bones": {
  "common_name": "Bones (Edible Raw Meaty Bones for GSD Diet)",
  "animal_prefix": "mixed",
  "status": "PARTIAL",
  "validation_date": "2026-07-22",
  "validation_tool": "manual_merge",
  "validation_result": "5 bone ingredients merged from DB_ingredientes_bones_v3.3.0.json",
  "ingredient_count": 5,
  "ingredient_ids": [
    "turkey_neck_raw", "chicken_neck_raw", "chicken_wing_raw",
    "pork_rib_raw", "chicken_back_raw"
  ],
  "ingredients": [ <5 prepared ingredients from Step 2> ]
}
```

### 3b. Update `_db_metadata`

| Field | Old | New |
|---|---|---|
| `version` | `"3.2.0"` | `"3.3.0"` |
| `total_ingredients` | `23` | `28` |
| `nutrients_per_ingredient` | `43` | `43` (unchanged) |

---

## Step 4 — Update `formulation_rules.json`

### 4a. Add bone entry to `inclusion_limits`

Insert after the `fat_source` entry (after line 92), before `"diet_templates"`:

```json
{
  "ingredient_id": "bone",
  "classification": "Base Nutricional",
  "max_pct": 15,
  "min_pct": null,
  "basis": "as_fed",
  "clinical_floor_g": 5,
  "risk_flags": [
    "HIGH_CALCIUM_BURDEN",
    "MONITOR_CA_P_RATIO"
  ],
  "source_ref": "REF_BONE_CA_MG_P_BIOAVAILABILITY",
  "note": "Edible raw meaty bones. Max 15% to keep Ca:P within 1.2-2.1 range per nutritionist guidance. Combined with low-Ca muscle meat. Clinical floor 5g prevents clinically irrelevant portions."
}
```

**Rationale:** `max_pct: 15` per architecture spec. `min_pct: null` (not mandatory). `clinical_floor_g: 5` matches bone category default in `lp_parameters_schema.json`.

### 4b. Add `"bone"` to `category_to_ingredient_mapping`

```json
"bone": ["_all_bone"]
```

Enables `expand_category_wildcards()` to resolve `_all_bone` to all 5 bone ingredient_ids from DB.

---

## Step 5 — Post-merge Verification

### 5a. Automated validation (Python script)

| Check | Expected | Failure |
|---|---|---|
| `len(all_ingredient_ids) == 28` | True | BLOCK |
| No duplicate `ingredient_id` across all groups | 0 duplicates | BLOCK |
| Every ingredient has exactly 43 nutrient keys | True for all 28 | BLOCK |
| Every ingredient has all 7 required schema fields | True for all 28 | BLOCK |
| Every `source_ref` in all 28 ingredients resolves in `audit_provenance.json` | 0 orphans | WARN |
| `formulation_rules.inclusion_limits` has bone entry | Present | BLOCK |
| `formulation_rules.category_to_ingredient_mapping` has `"bone"` key | Present | BLOCK |
| `lp_parameters_data.json` has `category_goals_target.bone` | Present (already exists) | INFO |

### 5b. Existing test suite

```bash
python -m pytest tests/ -x -q
```

All 58 tests must pass. No test modifications expected.

### 5c. Type check

```bash
python -m mypy src/gsd/ --config-file pyproject.toml
```

0 errors expected. No code changes in this task.

---

## Rollback Strategy

If any Step 5 check fails:

```bash
git checkout data/DB_ingredientes.json data/audit_provenance.json data/formulation_rules.json
```

Restores all 3 modified files. Investigate, fix, re-run from Step 0.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Bone `ingredient_id` collides with existing | Low (verified: 0) | High | Step 0b collision check |
| Stripping `vitamin_c_mg` loses future-useful data | Low (not in solver) | Low | Original preserved in `tempDB/` |
| 11 new provenance entries need quality review | Medium | Low | All marked LITERATURE_COMPOSITE or INFERRED — upgradeable later |
| Existing tests break from new DB structure | Low | Medium | Step 5b runs full suite |
| `expand_category_wildcards` doesn't handle `_all_bone` | Low (generic pattern) | Medium | Step 4b adds mapping |

---

## Bone Ingredient Summary

| `ingredient_id` | Ca (mg) | P (mg) | Ca:P | Protein (g) | Fat (g) | Meat% | USDA FDC |
|---|---|---|---|---|---|---|---|
| `turkey_neck_raw` | 1840 | 930 | 1.98:1 | 17.0 | 7.9 | 55% | 171086 |
| `chicken_neck_raw` | 770 | 645 | 1.2:1 | 12.7 | 16.7 | 64% | 171047 |
| `chicken_wing_raw` | 885 | 545 | 1.63:1 | 17.5 | 15.3 | 54% | 175225 |
| `pork_rib_raw` | 1490 | 750 | 1.99:1 | 17.0 | 12.0 | 70% | 100088 |
| `chicken_back_raw` | 1020 | 725 | 1.41:1 | 15.4 | 15.8 | 56% | 172382 |

**Per-ingredient `lp_constraints`:** all have `min_inclusion_pct: 5.0`, `max_inclusion_pct: 25-30`, `basis: "as_fed"`.

**Nutrients stripped:** `vitamin_c_mg` (not_applicable in all 5 — dogs synthesize endogenously).

**Nutrients consistently estimated zero:** `biotin_ug`, `iodine_ug`, `chloride_mg` (all 5 bones, source: `REF_ESTIMATED_ZERO_BONE`).

**Nutrients consistently not_applicable:** `vitamin_k_ug` (all 5), `vitamin_c_mg` (all 5, stripped).
