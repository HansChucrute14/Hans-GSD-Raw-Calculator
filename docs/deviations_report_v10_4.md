# Deviation Report — V10.4 Implementation (Items 1–5)

**Generated:** 2026-07-14  
**Generator:** `build_pipeline.py` runtime adapter + data inspection  
**Context:** Decisions from user response resolving 5 contradictions between architecture docs and real JSONs

---

## Item 1 — Gompertz Parameter Shape

| Field | Value |
|-------|-------|
| **Doc assumption** | Flat dict with scalar keys: `W_max_male`, `W_max_female`, `c_male`, `c_female`, `b` |
| **Real structure** | `gompertz_parameters` is a dict with `equation` (string), `parameters` (array of 5 param objects), `source_ref`. Each param has `param_id`, `name`, `value` (scalar or breed-line dict), `unit`, `confidence`, `source_ref`. |
| **W_max shape** | `GRO_W_MAX_MALE.value` = `{"assistance_dogs": 45, "working_exhibition_lines": 45}` (nested dict). `GRO_W_MAX_FEMALE.value` = `{"working_exhibition_lines": 38}` with `note: "assistance_dogs: not_specified_in_text"`. |
| **Decision** | Write `_get_param(params, param_id)` adapter + `_resolve_breed_value(value_field, default_line)` helper. Default to `"working_exhibition_lines"` for both sexes. |
| **Source citation** | `data/growth_energy_skeletal.json → gompertz_parameters` (inspected via `inspect_growth.py`) |
| **Evidence** | `python: params = data["growth_energy_skeletal.json"]["gompertz_parameters"]["parameters"]; len(params)=5, params[0]["param_id"]="GRO_W_MAX_MALE"` |

---

## Item 2 — k_multiplier → Scenario Link Missing

| Field | Value |
|-------|-------|
| **Doc assumption** | `scenarios.json` entries have a `k_multiplier_ref` field pointing into `growth_energy_skeletal.k_multipliers` |
| **Real structure** | `scenarios.json` entries have keys: `scenario_id`, `name`, `status`, `targets`, `source_ref`. **No `k_multiplier_ref` field.** |
| **Real k data** | `growth_energy_skeletal.k_multipliers` is a dict with 3 entries: `slow_growth_recommended.value=[1.2, 1.5]`, note says "LP model default: 1.2"; `rapid_growth_discouraged.value=[2.0, 3.0]`, note says "LP model alert: 2.0" |
| **Decision** | Hardcode `SCENARIO_K_MAP = {"SCN_B_SLOW_GROWTH": "slow_growth_recommended", "SCN_A_RAPID_GROWTH": "rapid_growth_discouraged"}` in code. Use `value[0]` (1.2 / 2.0). Flag as Phase 3 data-quality item. |
| **Source citation** | `data/scenarios.json` (no k_multiplier_ref); `data/growth_energy_skeletal.json → k_multipliers` (note fields) |
| **Evidence** | `python: scenarios.json entries have keys ['scenario_id', 'name', 'status', 'targets', 'source_ref']; no k_multiplier_ref field present` |

---

## Item 3 — Function Contract

| Field | Value |
|-------|-------|
| **Doc has** | §6.4a (mandatory signatures with types) + §6.4 (reference implementation code) |
| **Contradiction** | Reference code uses different param order/names vs mandated signatures |
| **Decision** | §6.4a is authoritative. Used its declared types for `AnimalInput`, `SolverRequest`, `calculate_der_and_envelope()` signature. |
| **Source citation** | `sat_pipeline_codigo.md §6.4a` |

---

## Item 4 — Return Type Design

| Field | Value |
|-------|-------|
| **Mandate says** | `tuple[float, float, float]` — 3-tuple `(der_kcal, min_total_g, max_total_g)` |
| **Reference code uses** | Rich dict with `bw_kg`, `ter_kcal`, `k_multiplier`, `units_of_1000kcal`, `envelope:{min_total_g, max_total_g, strategy, density_source}` |
| **Decision** | `DerEnvelope` class implementing both: `__iter__` for tuple unpacking + `.bw_kg`, `.ter_kcal`, `.k_multiplier`, `.units_of_1000kcal`, `.as_envelope_dict()`, `.as_animal_context()` named access. |
| **Evidence** | Runtime output confirms `der_kcal, min_t, max_t = calculate_der_and_envelope(...)` works via `__iter__`, AND `der_env.bw_kg` returns 45.0. |

---

## Item 5 — 3-State Nutrient Contract (MOST CONSEQUENTIAL)

| Field | Value |
|-------|-------|
| **Doc assumption** | 3-state field `"confirmed"` / `"missing"` / `"excluded"` alongside `value` in TypedMeasure |
| **Real structure** | Field name is **`status`** (not `state`). Values are **`"measured"`** (not `"confirmed"`), `"missing"`, `"not_applicable"` (not `"excluded"`). Missing nutrients are **present** in the `nutrients` dict with `value: null` + `reason` + `anomaly_ref` — NOT absent from the dict. `coverage_excluded_nutrients` is a **separate backward-compat list**. |
| **43 keys** | The DB has 43 nutrient keys (not 41). Extra two: `methionine_plus_cystine_g` (computed pair), `phenylalanine_plus_tyrosine_g` (computed pair) — both `status: "missing"` in DB. |
| **Status counts** | `measured`: 567 occurrences, `missing`: 262 occurrences, `not_applicable`: 31 occurrences across 20 ingredients × 43 keys = 860 total entries. |
| **Decision** | Conversion code filters on `entry.get("status") == "measured"`. Composite pairs computed from individual measured amino acids (skip the DB stubs). `py.exe build_pipeline.py --validate-db` confirms all entries valid. |
| **Source citation** | `data/DB_ingredientes.json` — all 20 ingredients |
| **Evidence** | `beef_muscle_raw.chloride_mg = {"status": "missing", "value": null, "reason": "not measured in USDA FDC for this ingredient", "anomaly_ref": "REF_MISSING_CHLORIDE"}`. `beef_muscle_raw.fat_g = {"status": "measured", "value": 4.5, "unit": "g", "basis": "as_fed", "source_ref": "REF_USDA_FDC_170196"}` |

---

## Item 6 — CSTR_NB_*_MIN Tier Hardcoded (§3.5 Violation, Deferred)

| Field | Value |
|-------|-------|
| **Doc assumption** | `constraint_tier` in NUTRIENT_REGISTRY is the authoritative source for relaxation policy per nutrient (§3.5: policy in JSON, not code) |
| **Real behavior** | `build_pipeline.py:1900-1901` hardcodes `tier = "adequacy_soft"` for all constraints matching `CSTR_NB_*_MIN` pattern, bypassing the registry entirely |
| **Registry declares** | `iodine_mg` → `safety_hard`, `vitamin_d3_iu` → `safety_hard` in NUTRIENT_REGISTRY — these values are never read for CSTR_NB_* constraints |
| **Impact today** | None — all 41 CSTR_NB_*_MIN constraints are correctly relaxable at L2, so the hardcoded `adequacy_soft` matches intended behavior |
| **Future risk** | A registry edit to change a nutrient's `constraint_tier` would silently do nothing — the code never reads it for NB constraints |
| **Decision** | Log as Phase 3 backlog item. Do not fix now. Fix: read `constraint_tier` from registry instead of pattern-matching on constraint ID. |
| **Source citation** | `build_pipeline.py:1900-1901` (hardcoded tier), `lp_parameters_data.json → NUTRIENT_REGISTRY` (registry tier) |
| **Evidence** | `grep -n "CSTR_NB" build_pipeline.py` → line 1900: `if cid.startswith("CSTR_NB_") and cid.endswith("_MIN"):` / line 1901: `tier = "adequacy_soft"` |

---

## Verification

```
py.exe build_pipeline.py --runtime   # DER + envelope + matrix build: PASS
py.exe build_pipeline.py --validate-db  # 3-state contract: PASS
py.exe build_pipeline.py --generate-mapa  # MAPA regeneration: PASS
```

**Derived runtime values (demo animal: 8mo male, 5 ingredients):**
- BW=45.0 kg, TER=1216 kcal, k=1.2, DER=1459 kcal
- Envelope: [315, 439] g
- Matrix: 4 resolved ingredients × 34 measured nutrients each
