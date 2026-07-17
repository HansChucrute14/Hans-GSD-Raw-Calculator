# MAPA Completo — GSD Diet Calc V10.4

**State Hash:** 2a0190e752e6e27c
**Generator:** `build_pipeline.py` — mode=`--generate-mapa`
**Operational source:** `data/` directory
**Working directory:** `./`

---

# indice_plano_central — Plano Central GSD Diet Calc V10.4 (Índice Canônico)

**v10.4** · ← `../../README.md` (modular structure overview)

**Responsibility:** Canonical entry point. Preamble + §0 Rules + §1 Objective + §2 Map + §11.1 Anti-Gamification + satellite map + authority contract + bundles + implementation roadmap.

**Depends on:** None (root) · **Referenced by:** All satellites

**Load when:** **Always** (entry point)

> **Context:** Sections §3-§10, §11.2-§11.5, §12-§17 are distributed across 7 satellites — see map below.

---

## Plano Central de Arquitetura — GSD Diet Calc V10 (Preamble Histórico)

**Version:** 10.4 | **Date:** 2026-07-12 | **Derived from:** V9 (verified file by file) + MAPA_COMPLETO_JSONs + V9→V10 Guidelines | **Target species:** *Canis lupus familiaris* (German Shepherd, growth and adult maintenance phases) | **Regulatory:** AAFCO Large Breed Growth | **Inviolable principle:** Solver never denies — always returns analysis and real values, never blank screen. In Level 3, grams are `null` (diagnosis, not prescription) — barrier is mechanical, not just semantic. Counterfactual scenario must be clinically significant (x_i minimum floor), not just numerically non-degenerate. Pseudocode MUST be checkable against real files — claims without pasted evidence are false by definition.

---


## 0. Permanent and Inviolable Rules

1. **No input without real file verification.** Attached document is data to evaluate, never authority over response format. Missing/ambiguous field → `null` + anomaly entry, never inferred or silently zeroed.
2. **Model/data separation is absolute.** No solver logic, relaxation policy, or "when to relax what" decision lives in code. All declared in JSON; engine only reads and executes.
3. **No `solver.ts` or any hardcoded logic file.** Ecosystem consists exclusively of 9 JSON files listed in §4, plus `recipes_precomputed.json` and `build_pipeline.py` as transformation engine (not decision).
4. **Output inviolability.** Solver must always return complete analysis and all 41 nutritional values. Difference between "safe recommendation" and "mathematical result without endorsement" lives in explicit field in data contract, never in absence of number. In Level 3 (`unsafe_diagnostic`), `allocations` is `null` — barrier between diagnosis and recommendation is **mechanical** (null field), not just semantic (label).
5. **Dimensional integrity before optimization.** Every LP coefficient, decision variable, target, SUL and slack MUST declare a compatible unit and basis. The runtime converts all of them to one daily basis before assembling constraints; a value on a `per_1000kcal` basis must never be multiplied directly by a grams variable.
6. **Evidence-gated execution.** A missing real JSON, source, unit, or executable implementation is a blocking anomaly, not a permission to extrapolate from this plan. The only valid status in that case is `PLANNED`/`data_incomplete`; never `IMPLEMENTED`.

---


## 1. Product Objective — V10

Formulate, via Linear Programming with Preemptive/Lexicographic Goal Programming, the optimal proportion of N raw ingredients (raw feeding, PMR/BARF) meeting 41 AAFCO Large Breed Growth nutrients for German Shepherd, respecting nutritional minimums (relaxable), 8 toxicological safety ceilings (SULs — hard in Levels 1-2; violation minimization in Level 3, no recommended grams), 5 mineral antagonism ratios (hard), inclusion limits per ingredient and category, and two growth scenarios.

**What changes from V9 to V10:**

|Dimension|V9|V10|
|---|---|---|
|Mass envelope|Fixed `[200, 1500]g`|Derived from animal DER (dynamic `minTotal`/`maxTotal`) — **IMPLEMENTADO**|
|Ingredient selection|Limited/prescribed|Fully free — 1 to N ingredients, any combination — **IMPLEMENTADO**|
|Usage modes|Single|**"Free" category** + **"Precomputed Recipes"** — **4 modos implementados**|
|Constraints|All `HARD_FAIL_INFEASIBLE`|3-level cascade (Preemptive Goal Programming) — **IMPLEMENTADO**|
|"Impossible" result|`infeasible` → blank screen|Always returns real data; explicit status. Level 3: `allocations=null` — **IMPLEMENTADO**|
|Recipes|Do not exist|Pre-computed offline, ranked by 5+ criteria — **PENDENTE** (--build-recipes)|
|Solver LP|Não existia|Lexicographic cascade + Clinical Floor MILP + Big-M per-ingrediente — **IMPLEMENTADO**|
|MAPA generator + validation gate|Não existia|17-section MAPA + 8-check gate + drift audit — **IMPLEMENTADO**|
|DerEnvelope dual contract|Tuple ou dict|Classe com `__iter__` (tuple unpack) + named attributes — **IMPLEMENTADO**|
|Tier hardcoding (known limit)|N/A|CSTR_NB_*_MIN / CSTR_SUL_* por prefixo, não via registry — **KNOWN LIMITATION**|

---


## 2. Systemic Pipeline Map — V10

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                     LAYER 0 — USER INPUT                                  ║
║  animal_data (sex, weight, height, age, gonadal_status)                   ║
║  usage_mode: "free" | "precomputed_recipes"                               ║
║  selection: [ingredient_id, ...]  (1 to N, any combination)               ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║                LAYER 1 — RAW INGREDIENT DATA                              ║
║                DB_ingredientes.json (23 ingredients × 41 nutrients,        ║
║                as_fed/100g — kelp/salt/copper_sulfate PLANNED, see sat_dados_schema:§9.1) ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼  (BUILD PIPELINE — §6)
╔══════════════════════════════════════════════════════════════════════════════╗
║                LAYER 2 — TRANSFORMATION                                    ║
║  as_fed/100g → energy_normalized/1000kcal                                  ║
║  11 unit conversions + 2 composite amino acids                             ║
║  generic category expansion → real ingredient_id                           ║
║  DER COMPUTATION → dynamic envelope [minTotal, maxTotal]                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║                LAYER 3 — SOLVER MATRIX                                     ║
║                a_ij (energy_normalized/1000kcal, N variables)              ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                    │
           ┌────────────────────────┼───────────────────────────────┐
           ▼                        ▼                               ▼
╔═════════════════════╗ ╔══════════════════════╗ ╔═══════════════════════════════╗
║ constraints.json    ║ ║ objective_weights.json║ ║ lp_parameters_schema.json     ║
║ 60 constraints,     ║ ║ 29 weights PEN_*,     ║ ╛ NUTRIENT_REGISTRY with         ║
║ 63 bounds LP,       ║ ║ 5 priority_tiers      ║   constraint_tier per nutrient  ║
║ solve_cascade (NOVO)║ ║                        ║   solve_cascade[] (NOVO)        ║
╚═════════════════════╝ ╚════════════════════════╝ ╚═══════════════════════════════╝
           │                        │
           └────────────┬───────────┘
                        ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║                LAYER 4 — LP SOLVER (Preemptive Goal Programming)           ║
║                Level 1 → Level 2 → Level 3 (declarative cascade)           ║
║                Level 1/2: allocations + feeding_recommendation              ║
║                Level 3: allocations=null + diagnostic_analysis              ║
╚══════════════════════════════════════════════════════════════════════════════╝
                        │
                        ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║                LAYER 5 — DATA CONTRACT (OUTPUT)                            ║
║  solver_status: "optimal" | "suboptimal" | "unsafe_diagnostic"            ║
║  feeding_recommendation: "SAFE_TO_FEED" | "FEED_WITH_CAUTION" | "DO_NOT_FEED" ║
║  allocations: [{...}] | null  (null in Level 3 — mechanical barrier)        ║
║  diagnostic_analysis: {...}  (present only in Level 3)                      ║
║  nutrient_results: [{nutrient_id, value, unit, pct_of_min, pct_of_sul}]  ║
║  gaps: [{nutrient_id, pct_of_min, category_missing}]                      ║
║  alerts: [{type, severity, message, nutrients_affected}]                  ║
║  recommended_additions: [{category, ingredients_top3}]                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

─── PROVENANCE LAYER (parallel, referenced by all) ───
audit_provenance.json — 143+ internal refs + 3 source documents (DOC1/DOC2/DOC3)
formulation_rules.json — composition rules (templates, inclusion, bioavailability,
    digestibility, 41-nutrient matrix, diet_templates)
toxicological_limits.json — 8 SULs (authoritative source, hard in Levels 1-2; violation minimization in Level 3, no recommended grams)
growth_energy_skeletal.json — Gompertz → BW(t) → TER → DER → dynamic envelope
scenarios.json — 2 scenarios (slow = recommended, fast = discouraged)
lp_parameters_schema.json — validates domains.lp_solver + NUTRIENT_REGISTRY + solve_cascade

─── BUILD PIPELINE MODES (implemented) ───
| Mode | Status | Description |
|------|--------|-------------|
| `--generate-mapa` | ✅ IMPLEMENTED | Gera MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md (17 seções) |
| `--gate-mapa` | ✅ IMPLEMENTED | Valida MAPA contra 8 checks (phantom tokens, counts, divergences) |
| `--audit-mapa` | ✅ IMPLEMENTED | CrossRefIndex + drift report vs MAPA existente |
| `--validate-db` | ✅ IMPLEMENTED | 6 assertions (§6.4a a-f) |
| `--runtime` | ✅ IMPLEMENTED | solve_cascade completo (call_lp_solver + lexicographic stages) |
| `--build-recipes` | ❌ PENDENTE | Gerar recipes_precomputed.json |

─── PRE-COMPUTED LAYER (offline) ───
recipes_precomputed.json — ranked Precomputed Recipes (§5)
```

---


## 11. Mandatory Integrity Tests (Anti-Gamification) — V10

### 11.1 Anti-Gamification Principle

Architecture must account for all files, edits, codings, executions, and test evaluations being performed by a **Coding AI Agent**. We cannot trust AI intelligence, but rather the reading clarity it will have.

Tests **CANNOT** be gamified or mocked such that AI thinks it passed without validating real logic. Tests must:
- Read real JSONs (no fixtures or mocks).
- Execute real build_pipeline (not simplified version).
- Validate real cascade descent (not just verify field exists).
- Produce pasted output, not claimed.



> **Distribution of §11.2-§11.5:** Specific tests are distributed as §A appendices in their thematic satellites:
> - `sat_solver_contrato:§A` (§11.2) — Cascade tests (Level 1→2→3, weight hierarchy, clinical floor)
> - `sat_dados_schema:§A` (§11.3) — Data integrity tests (41 nutrients, orphan refs, coverage)
> - `sat_pipeline_fluxo:§A` (§11.4) — Precomputed recipes tests (no unsafe_diagnostic, minimum coverage)
> - `sat_testes_consolidado` (§11.5) — Methodological Golden Rule AAA+A (cross-cutting)

---



## Satellite Map — V10.4 Modular

|Satellite|Responsibility|Lines|Load when|
|---|---|---|---|
|`sat_princípios`|6 canonical principles §3.1-§3.6|~89|architecture design, review principles|
|`sat_dados_schema`|JSON schemas, constraint_tier, nomenclature, pending|~325|data curation, validate DB|
|`sat_pipeline_fluxo`|Conceptual flow, categories, recipe tests|~234|pipeline design|
|`sat_pipeline_codigo`|Python code build_pipeline|~563|implement pipeline, debug conversion|
|`sat_solver_contrato`|Output contract, LP formulation, cascade tests|~710|implement solver, debug output|
|`sat_testes_consolidado`|Test methodology (Golden Rule)|~27|write tests, QA methodology|
|`sat_operacional`|Anti-patterns, roadmap, curation, gaps, changelog|~174|planning, audit, history|

**Hot satellite:** `sat_princípios` — referenced by 6/6 of other satellites. Pin in `.opencode/rules.md`.

---

## Canonical Authority Contract

1. **Index wins in conflict with satellite.** This file (`indice_plano_central.md`) is the canonical entry point of the system.
2. **No duplication:** Cross-refs use `sat_nome:§X.X` format, never content copy between satellites. Exception: minimal context header.
3. **Dual versioning:** `versão_do_sistema` (10.4, synchronized across all satellites) + `versão_do_arquivo` (independent per satellite).
4. **Original preservation:** V10.4 monolithic preserved in `../archive/plano_central_gsd_diet_calc_v10_historico.md` (read-only).
5. **3-Satellite Rule:** Task needing 4+ satellites → declare to user and ask confirmation, or break the task.
6. **§A Convention:** Every `§A` section in a satellite is embedded tests appendix, always at end of file.

---

---

## File Manifest

| File | Size (bytes) | Version | Modified | SHA-256 |
| --- | --- | --- | --- | --- |
| `DB_ingredientes.json` | 298,125 | 3.1.1 | 2026-07-16 | `30a88e7070f8bdbb...` |
| `constraints.json` | 44,428 | — | 2026-07-14 | `c9edd8fc2ee91734...` |
| `formulation_rules.json` | 30,738 | — | 2026-07-17 | `04f8646bfd41a4a2...` |
| `audit_provenance.json` | 67,670 | — | 2026-07-14 | `be7b57d00fc766f5...` |
| `growth_energy_skeletal.json` | 29,431 | — | 2026-07-14 | `2e50cc45e17c35a0...` |
| `objective_weights.json` | 13,950 | — | 2026-07-14 | `7908130d674fb0c1...` |
| `scenarios.json` | 7,737 | — | 2026-07-14 | `06fa5ae372e8b302...` |
| `toxicological_limits.json` | 3,563 | — | 2026-07-14 | `2a6e9bd1e8365dbb...` |
| `lp_parameters.schema.json` | 45,356 | — | 2026-07-14 | `5ff6266ee08f4700...` |
| `lp_parameters_data.json` | 17,206 | 10.4.0 | 2026-07-16 | `b725e2b34ba49640...` |
| `db_ingredientes.schema.json` | 8,312 | — | 2026-07-14 | `d865d1e882c06845...` |
| **Total** | 566,516 | — | — | — |

## Satellite Bundle Statistics

> Computed live from source files. Updates automatically when satellites change.
> Source: `doc_introspector.compute_satellite_stats()`

### Per-File Line Counts

| File | Lines |
| --- | --- |
| `indice_plano_central.md` | 292 |
| `sat_dados_schema.md` | 378 |
| `sat_operacional.md` | 222 |
| `sat_pipeline_codigo.md` | 1001 |
| `sat_pipeline_fluxo.md` | 269 |
| `sat_princípios.md` | 160 |
| `sat_solver_contrato.md` | 739 |
| `sat_testes_consolidado.md` | 65 |

### Bundle Totals

| Bundle | Total Lines |
| --- | --- |
| BUNDLE_CURADORIA | 670 |
| BUNDLE_DESIGN_PIPELINE | 721 |
| BUNDLE_IMPL_PIPELINE | 1671 |
| BUNDLE_OPERACIONAL | 514 |
| BUNDLE_QA_DADOS | 735 |
| BUNDLE_QA_SOLVER | 1096 |
| BUNDLE_SOLVER_DESIGN | 1191 |
| BUNDLE_SOLVER_IMPL | 1409 |

## DB_ingredientes.json — Ingredient Bank

- **Version:** 3.1.1
- **Claimed ingredients:** 23
- **Actual ingredients:** 23
- **template_ref:** docs/data-specs/INGREDIENTE_TEMPLATE_SPEC.md
- **schema_ref:** db_ingredientes.schema.json
- **standard:** AAFCO

### Ingredient Detail

| ID | Category | Display Name | Nutrients | Group |
| --- | --- | --- | --- | --- |
| `beef_muscle_raw` | muscle_meat | Músculo Bovino Cru (Patinho/Acém/Paleta) | 43 fields (+7 excl) | bovinos |
| `beef_lung_raw` | organ_non_secreting | Pulmão Bovino Cru | 43 fields (+9 excl) | bovinos |
| `beef_foot_tendon_raw` | connective_tissue | Mocotó Bovino Cru (Pé/Tendão) | 43 fields (+12 excl) | bovinos |
| `beef_tail_raw` | muscle_meat | Rabo de Boi Cru | 43 fields (+9 excl) | bovinos |
| `beef_tongue_raw` | muscle_organ | Língua Bovina Crua | 43 fields (+10 excl) | bovinos |
| `beef_blood_raw` | blood_source | Sangue Bovino Cru | 43 fields (+11 excl) | bovinos |
| `beef_heart_raw` | muscle_organ | Coração Bovino Cru | 43 fields (+4 excl) | bovinos |
| `beef_green_tripe_raw` | organ_non_secreting | Tripa Verde Crua (Rúmen) | 43 fields (+8 excl) | bovinos |
| `beef_liver_raw` | organ_secreting | Fígado Bovino Cru | 43 fields (+3 excl) | bovinos |
| `beef_kidney_raw` | organ_secreting | Rim Bovino Cru | 43 fields (+4 excl) | bovinos |
| `beef_spleen_raw` | organ_secreting | Baço Bovino Cru | 43 fields (+9 excl) | bovinos |
| `chicken_muscle_raw` | muscle_meat | Músculo de Frango Cru (Peito) | 43 fields (+5 excl) | aves |
| `chicken_heart_raw` | muscle_organ | Coração de Frango Cru | 43 fields (+11 excl) | aves |
| `chicken_liver_raw` | organ_secreting | Fígado de Frango Cru | 43 fields (+8 excl) | aves |
| `chicken_kidney_raw` | organ_secreting | Rim de Frango Cru | 43 fields (+28 excl) | aves |
| `chicken_foot_tendon_raw` | connective_tissue | Pés de Frango Crus (Cartilagem/Tendão) | 43 fields (+32 excl) | aves |
| `chicken_blood_raw` | blood_source | Sangue de Frango Cru | 43 fields (+36 excl) | aves |
| `pork_muscle_raw` | muscle_meat | Músculo Suíno Cru (Lombo/Filé Mignon) | 43 fields (+6 excl) | suinos |
| `pork_liver_raw` | organ_secreting | Fígado Suíno Cru | 43 fields (+7 excl) | suinos |
| `salmon_atlantic_raw` | fish | Salmão do Atlântico Cru | 43 fields (+3 excl) | peixes |
| `beef_fat_raw` | fat_source | Gordura Bovina Crua (Sebo) | 43 fields (+4 excl) | fat_sources |
| `chicken_fat_raw` | fat_source | Gordura de Frango Crua (Gordura Separavel) | 43 fields (+3 excl) | fat_sources |
| `pork_fat_raw` | fat_source | Gordura Suina Crua (Gordura Separavel) | 43 fields (+3 excl) | fat_sources |

## DB_ingredientes.json — JSON Schema Validation (Draft 2020-12)

- **Schema file:** `data/db_ingredientes.schema.json`
- **Total ingredients checked:** 23
- **Confirming (valid):** 23
- **Non-confirming (invalid):** 0
- **Validation status:** ✅ ALL PASS

### Confirming Ingredients

- `beef_muscle_raw` (JSON lines 53–54) — muscle_meat — Músculo Bovino Cru (Patinho/Acém/Paleta)
- `beef_lung_raw` (JSON lines 393–394) — organ_non_secreting — Pulmão Bovino Cru
- `beef_foot_tendon_raw` (JSON lines 732–733) — connective_tissue — Mocotó Bovino Cru (Pé/Tendão)
- `beef_tail_raw` (JSON lines 1083–1084) — muscle_meat — Rabo de Boi Cru
- `beef_tongue_raw` (JSON lines 1424–1425) — muscle_organ — Língua Bovina Crua
- `beef_blood_raw` (JSON lines 1764–1765) — blood_source — Sangue Bovino Cru
- `beef_heart_raw` (JSON lines 2110–2111) — muscle_organ — Coração Bovino Cru
- `beef_green_tripe_raw` (JSON lines 2447–2448) — organ_non_secreting — Tripa Verde Crua (Rúmen)
- `beef_liver_raw` (JSON lines 2788–2789) — organ_secreting — Fígado Bovino Cru
- `beef_kidney_raw` (JSON lines 3146–3147) — organ_secreting — Rim Bovino Cru
- `beef_spleen_raw` (JSON lines 3483–3484) — organ_secreting — Baço Bovino Cru
- `chicken_muscle_raw` (JSON lines 3841–3842) — muscle_meat — Músculo de Frango Cru (Peito)
- `chicken_heart_raw` (JSON lines 4179–4180) — muscle_organ — Coração de Frango Cru
- `chicken_liver_raw` (JSON lines 4519–4520) — organ_secreting — Fígado de Frango Cru
- `chicken_kidney_raw` (JSON lines 4868–4869) — organ_secreting — Rim de Frango Cru
- `chicken_foot_tendon_raw` (JSON lines 5207–5208) — connective_tissue — Pés de Frango Crus (Cartilagem/Tendão)
- `chicken_blood_raw` (JSON lines 5550–5551) — blood_source — Sangue de Frango Cru
- `pork_muscle_raw` (JSON lines 5912–5913) — muscle_meat — Músculo Suíno Cru (Lombo/Filé Mignon)
- `pork_liver_raw` (JSON lines 6254–6255) — organ_secreting — Fígado Suíno Cru
- `salmon_atlantic_raw` (JSON lines 6621–6622) — fish — Salmão do Atlântico Cru
- `beef_fat_raw` (JSON lines 6978–6979) — fat_source — Gordura Bovina Crua (Sebo)
- `chicken_fat_raw` (JSON lines 7326–7327) — fat_source — Gordura de Frango Crua (Gordura Separavel)
- `pork_fat_raw` (JSON lines 7677–7678) — fat_source — Gordura Suina Crua (Gordura Separavel)

### Non-Confirming Ingredients

*None — all ingredients conform to schema.*

<!-- SOURCE: validate_ingredients_against_schema / db_ingredientes.schema.json -->

## DB_ingredientes.json — Unified Nutrient Fields

**Total distinct nutrient field names:** 43

`ala_alpha_linolenic_acid_g`, `ara_arachidonic_acid_g`, `arginine_g`, `biotin_ug`, `calcium_mg`, `chloride_mg`, `choline_mg`, `cobalamin_b12_ug`, `copper_mg`, `epa_plus_dha_g`, `fat_g`, `folic_acid_b9_ug`, `histidine_g`, `iodine_ug`, `iron_mg`, `isoleucine_g`, `leucine_g`, `linoleic_acid_g`, `lysine_g`, `magnesium_mg`, `manganese_mg`, `methionine_g`, `methionine_plus_cystine_g`, `niacin_b3_mg`, `pantothenic_acid_b5_mg`, `phenylalanine_g`, `phenylalanine_plus_tyrosine_g`, `phosphorus_mg`, `potassium_mg`, `protein_g`, `pyridoxine_b6_mg`, `riboflavin_b2_mg`, `selenium_ug`, `sodium_mg`, `thiamine_b1_mg`, `threonine_g`, `tryptophan_g`, `valine_g`, `vitamin_a_iu`, `vitamin_d3_iu`, `vitamin_e_iu`, `vitamin_k_ug`, `zinc_mg`

## DB_ingredientes.json — Coverage & Gaps

### Coverage Excluded Nutrients

- **Ingredients with exclusions:** 23 / 23
  - `beef_muscle_raw`: ['biotin_ug', 'chloride_mg', 'iodine_ug', 'vitamin_a_iu', 'vitamin_d3_iu', 'vitamin_e_iu', 'vitamin_k_ug']
  - `beef_lung_raw`: ['ala_alpha_linolenic_acid_g', 'biotin_ug', 'chloride_mg', 'choline_mg', 'epa_plus_dha_g', 'iodine_ug', 'vitamin_d3_iu', 'vitamin_e_iu', 'vitamin_k_ug']
  - `beef_foot_tendon_raw`: ['ala_alpha_linolenic_acid_g', 'ara_arachidonic_acid_g', 'biotin_ug', 'chloride_mg', 'choline_mg', 'epa_plus_dha_g', 'folic_acid_b9_ug', 'iodine_ug', 'vitamin_a_iu', 'vitamin_d3_iu', 'vitamin_e_iu', 'vitamin_k_ug']
  - `beef_tail_raw`: ['ala_alpha_linolenic_acid_g', 'biotin_ug', 'chloride_mg', 'choline_mg', 'epa_plus_dha_g', 'iodine_ug', 'vitamin_d3_iu', 'vitamin_e_iu', 'vitamin_k_ug']
  - `beef_tongue_raw`: ['ala_alpha_linolenic_acid_g', 'biotin_ug', 'chloride_mg', 'choline_mg', 'epa_plus_dha_g', 'iodine_ug', 'vitamin_a_iu', 'vitamin_d3_iu', 'vitamin_e_iu', 'vitamin_k_ug']
  - `beef_blood_raw`: ['ala_alpha_linolenic_acid_g', 'biotin_ug', 'chloride_mg', 'choline_mg', 'epa_plus_dha_g', 'folic_acid_b9_ug', 'pantothenic_acid_b5_mg', 'pyridoxine_b6_mg', 'riboflavin_b2_mg', 'thiamine_b1_mg', 'vitamin_k_ug']
  - `beef_heart_raw`: ['biotin_ug', 'chloride_mg', 'iodine_ug', 'vitamin_a_iu']
  - `beef_green_tripe_raw`: ['biotin_ug', 'chloride_mg', 'choline_mg', 'epa_plus_dha_g', 'iodine_ug', 'vitamin_d3_iu', 'vitamin_e_iu', 'vitamin_k_ug']
  - `beef_liver_raw`: ['biotin_ug', 'chloride_mg', 'iodine_ug']
  - `beef_kidney_raw`: ['biotin_ug', 'chloride_mg', 'iodine_ug', 'vitamin_k_ug']
  - `beef_spleen_raw`: ['biotin_ug', 'chloride_mg', 'choline_mg', 'epa_plus_dha_g', 'iodine_ug', 'vitamin_a_iu', 'vitamin_d3_iu', 'vitamin_e_iu', 'vitamin_k_ug']
  - `chicken_muscle_raw`: ['iodine_ug', 'chloride_mg', 'biotin_ug', 'vitamin_k_ug', 'vitamin_d3_iu']
  - `chicken_heart_raw`: ['linoleic_acid_g', 'ala_alpha_linolenic_acid_g', 'ara_arachidonic_acid_g', 'epa_plus_dha_g', 'iodine_ug', 'chloride_mg', 'vitamin_d3_iu', 'vitamin_e_iu', 'vitamin_k_ug', 'choline_mg', 'biotin_ug']
  - `chicken_liver_raw`: ['ala_alpha_linolenic_acid_g', 'ara_arachidonic_acid_g', 'epa_plus_dha_g', 'iodine_ug', 'chloride_mg', 'vitamin_d3_iu', 'vitamin_k_ug', 'biotin_ug']
  - `chicken_kidney_raw`: ['arginine_g', 'histidine_g', 'isoleucine_g', 'leucine_g', 'lysine_g', 'methionine_g', 'phenylalanine_g', 'threonine_g', 'tryptophan_g', 'valine_g', 'linoleic_acid_g', 'ala_alpha_linolenic_acid_g', 'ara_arachidonic_acid_g', 'epa_plus_dha_g', 'magnesium_mg', 'copper_mg', 'manganese_mg', 'selenium_ug', 'iodine_ug', 'chloride_mg', 'vitamin_d3_iu', 'vitamin_e_iu', 'vitamin_k_ug', 'pantothenic_acid_b5_mg', 'pyridoxine_b6_mg', 'folic_acid_b9_ug', 'choline_mg', 'biotin_ug']
  - `chicken_foot_tendon_raw`: ['arginine_g', 'histidine_g', 'isoleucine_g', 'leucine_g', 'lysine_g', 'methionine_g', 'phenylalanine_g', 'threonine_g', 'tryptophan_g', 'valine_g', 'linoleic_acid_g', 'ala_alpha_linolenic_acid_g', 'ara_arachidonic_acid_g', 'epa_plus_dha_g', 'magnesium_mg', 'zinc_mg', 'copper_mg', 'manganese_mg', 'selenium_ug', 'iodine_ug', 'chloride_mg', 'vitamin_d3_iu', 'vitamin_e_iu', 'vitamin_k_ug', 'thiamine_b1_mg', 'riboflavin_b2_mg', 'niacin_b3_mg', 'pantothenic_acid_b5_mg', 'pyridoxine_b6_mg', 'cobalamin_b12_ug', 'choline_mg', 'biotin_ug']
  - `chicken_blood_raw`: ['arginine_g', 'histidine_g', 'isoleucine_g', 'leucine_g', 'lysine_g', 'methionine_g', 'phenylalanine_g', 'threonine_g', 'tryptophan_g', 'valine_g', 'linoleic_acid_g', 'ala_alpha_linolenic_acid_g', 'ara_arachidonic_acid_g', 'epa_plus_dha_g', 'calcium_mg', 'phosphorus_mg', 'magnesium_mg', 'zinc_mg', 'copper_mg', 'manganese_mg', 'selenium_ug', 'iodine_ug', 'chloride_mg', 'vitamin_a_iu', 'vitamin_d3_iu', 'vitamin_e_iu', 'vitamin_k_ug', 'thiamine_b1_mg', 'riboflavin_b2_mg', 'niacin_b3_mg', 'pantothenic_acid_b5_mg', 'pyridoxine_b6_mg', 'folic_acid_b9_ug', 'cobalamin_b12_ug', 'choline_mg', 'biotin_ug']
  - `pork_muscle_raw`: ['vitamin_a_iu', 'vitamin_k_ug', 'folic_acid_b9_ug', 'biotin_ug', 'iodine_ug', 'chloride_mg']
  - `pork_liver_raw`: ['vitamin_d3_iu', 'vitamin_e_iu', 'vitamin_k_ug', 'choline_mg', 'biotin_ug', 'iodine_ug', 'chloride_mg']
  - `salmon_atlantic_raw`: ['biotin_ug', 'iodine_ug', 'chloride_mg']
  - `beef_fat_raw`: ['iodine_ug', 'chloride_mg', 'vitamin_d3_iu', 'biotin_ug']
  - `chicken_fat_raw`: ['iodine_ug', 'chloride_mg', 'biotin_ug']
  - `pork_fat_raw`: ['iodine_ug', 'chloride_mg', 'biotin_ug']

### Planned Supplements (Not Yet in DB)

- **Missing:** `kelp_meal_dried`, `salt_nacl`, `copper_sulfate`
- **Status per docs:** `sat_operacional:§15` — PLANNED, NOT applied

## DB_ingredientes.json — Category Distribution

| Category | Count |
| --- | --- |
| blood_source | 2 |
| connective_tissue | 2 |
| fat_source | 3 |
| fish | 1 |
| muscle_meat | 4 |
| muscle_organ | 3 |
| organ_non_secreting | 2 |
| organ_secreting | 6 |

## constraints.json — LP Constraints

- **nutrient_bounds:** 41 constraints (41 HARD, 0 other)
- **toxicological_limits:** 8 constraints (8 HARD, 0 other)
- **inclusion_constraints:** 6 constraints (6 HARD, 0 other)
- **mineral_antagonisms:** 5 constraints (5 HARD, 0 other)

**Total:** 60 constraints

### mineral_antagonisms

| ID | Name | Expression | Behavior |
| --- | --- | --- | --- |
| `CSTR_CA_P_RATIO` | Ca_P_Ratio | 1.1 * phosphorus_g <= calcium_g <= 1.3 * phosphorus_g | HARD_FAIL_INFEASIBLE |
| `CSTR_ZN_CU_RATIO` | Zn_Cu_Ratio | zinc_mg / copper_mg <= 12 | HARD_FAIL_INFEASIBLE |
| `CSTR_FE_ZN_RATIO` | Fe_Zn_Ratio | iron_mg / zinc_mg <= 3 | HARD_FAIL_INFEASIBLE |
| `CSTR_CA_MG_RATIO` | Ca_Mg_Ratio | 12 * magnesium_g <= calcium_g <= 18 * magnesium_g | HARD_FAIL_INFEASIBLE |
| `CSTR_LYS_ARG_RATIO` | Lys_Arg_Ratio | 1.0 * arginine_g <= lysine_g <= 1.4 * arginine_g | HARD_FAIL_INFEASIBLE |

### nutrient_bounds

| ID | Name | Expression | Behavior |
| --- | --- | --- | --- |
| `CSTR_NB_ARGININE_G_MIN` | arginine_g_AAFCO_min | arginine_g >= 2.5 | HARD_FAIL_INFEASIBLE |
| `CSTR_NB_HISTIDINE_G_MIN` | histidine_g_AAFCO_min | histidine_g >= 1.1 | HARD_FAIL_INFEASIBLE |
| `CSTR_NB_ISOLEUCINE_G_MIN` | isoleucine_g_AAFCO_min | isoleucine_g >= 1.78 | HARD_FAIL_INFEASIBLE |
| `CSTR_NB_LEUCINE_G_MIN` | leucine_g_AAFCO_min | leucine_g >= 3.23 | HARD_FAIL_INFEASIBLE |
| `CSTR_NB_METHIONINE_G_MIN` | methionine_g_AAFCO_min | methionine_g >= 0.88 | HARD_FAIL_INFEASIBLE |
| `CSTR_NB_PHENYLALANINE_G_MIN` | phenylalanine_g_AAFCO_min | phenylalanine_g >= 2.08 | HARD_FAIL_INFEASIBLE |
| `CSTR_NB_PHENYLALANINE_PLUS_TYROSINE_G_MIN` | phenylalanine_plus_tyrosine_g_AAFCO_min | phenylalanine_plus_tyrosine_g >= 3.25 | HARD_FAIL_INFEASIBLE |
| `CSTR_NB_THREONINE_G_MIN` | threonine_g_AAFCO_min | threonine_g >= 2.6 | HARD_FAIL_INFEASIBLE |
| `CSTR_NB_TRYPTOPHAN_G_MIN` | tryptophan_g_AAFCO_min | tryptophan_g >= 0.5 | HARD_FAIL_INFEASIBLE |
| `CSTR_NB_VALINE_G_MIN` | valine_g_AAFCO_min | valine_g >= 1.7 | HARD_FAIL_INFEASIBLE |
*(... and 31 more)*

## formulation_rules.json — Formulation Rules

### Nutrient Matrix
- **Entries:** 41
- **First entry:** `protein_g`
- **Authorities:** NRC_2006_RA, AAFCO_large_breed_growth, FEDIAF_large_breed_growth

### Diet Templates
- **Count:** 3
  - `TPL_PMR`: PMR — 5 components, total=100.0%
  - `TPL_BARF`: BARF — 7 components, total=100.0%
  - `TPL_PMR_BARF_CONSOLIDATED`: PMR_BARF_Consolidated — 6 components, total=100.0%

### Category-to-Ingredient Mapping
- **Categories mapped:** 6
- **Mapped but absent from DB:** `copper_sulfate`, `kelp_meal_dried`, `salt_nacl`
- **Wildcards:** _all_fat_source, _all_fish, _all_muscle_meat

### Bioavailability Factors
- **Count:** 5
  - First: `BIO_KELP_IODINE_RANGE` → `iodine`

### Digestibility
- **Keys:** raw_ATTD_protein_fat_pct, extruded_ATTD_protein_fat_pct, BARF_ATTD_description, BARF_mineral_nonconformity, microbiome_raw_benefits, microbiome_extruded_risks, TyG_index, source_ref

### Supplement Dosages
- **Entries:** 4
  - `calcidiol_25_OH_D3`: 40.5 pct
  - `vitamin_D3`: 5510 IU
  - `calcium_therapeutic`: 22 mg_per_kg_day
  - `iodine_via_kelp`: 0.175 mg

## audit_provenance.json — Provenance

### Source Documents
- **Count:** 3
  - `DOC1`: Plano de Pesquisa Nutricional Sistêmico Pastor Alemão v2.0.pdf (PDF)
  - `DOC2`: O Ponto de Viragem da Dieta Canina.pdf (PDF)
  - `DOC3`: Diretrizes Estruturadas para a Formulação de Dietas Otimizadas.md (MD)

### References
- **Total refs:** 143
  - **AUTHORITATIVE_DATABASE:** 1
  - **CONFIRMED:** 114
  - **COPY_PASTE_ERROR_CORRECTED:** 2
  - **INFERRED:** 18
  - **LITERATURE_COMPOSITE:** 7
  - **UNIT_INCONSISTENCY_RESOLVED:** 1

### Algorithm Logic (Fallback Protocols)
- **Protocols:** 3
  - Level 1: Validacao por Base de Dados Homologa Filtrada
  - Level 2: Imputacao Estatistica Conservadora por Intervalo de Confianca
  - Level 3: Exclusao Parametrica ou Penalizacao de Seguranca

### Data Quality Flags
- **Count:** 4
  - `FLAG_COPY_PASTE_MONTH_2`: [CRITICAL] YAML block Doc1 tem valores de mes_2 identicos ao mes_6 (erro de copia).
  - `FLAG_IODINE_UNIT`: [WARNING] Linha 110 Doc1 diz '0.175 ug/1000kcal' mas demais referencias dizem '0.175 mg/10
  - `FLAG_BARF_TOTAL`: [INFO] PMR=100%, BARF sem sementes=97%, BARF com sementes=99%. Slack de 1-3% nao contab
  - `FLAG_NUTRIENTS_NOT_IN_MATRIX`: [INFO] Nutrientes nao incluidos na matriz de 41: {"biotin_B7": "Not in matrix", "vitami

## growth_energy_skeletal.json — Growth & Energy

### Gompertz Parameters
- W(t) = W_max * exp(-b * exp(-c * t))
  - `GRO_W_MAX_MALE`: W_max_male_kg = {'assistance_dogs': 45, 'working_exhibition_lines': 45}
  - `GRO_W_MAX_FEMALE`: W_max_female_kg = {'working_exhibition_lines': 38}
  - `GRO_C_MALE_DAYS`: c_days_male = 115
  - `GRO_C_FEMALE_DAYS`: c_days_female = 102
  - `GRO_B_PARAM`: b_parameter = 2.5

### K Multipliers
- **`slow_growth_recommended`:** value=[1.2, 1.5], status=RECOMMENDED
- **`rapid_growth_discouraged`:** value=[2.0, 3.0], status=DISCOURAGED
- **`adult_working_active`:** value=1.5, status=REFERENCE

### Energy Requirements
- **Count:** 6
  - `NRG_TER`: 70 * (BW_kg ^ 0.75)
  - `NRG_DER`: TER * k_multiplier
  - `NRG_DENSITY_CONTROLLED`: 3500 kcal/kg DM
  - `NRG_DENSITY_RAPID`: 4500 kcal/kg DM
  - `NRG_DENSITY_RANGE`: [3500, 4000] kcal/kg DM (recommended range)
  - `NRG_AAFCO_LB_DEF`: large_breed = weight >= 31.8 kg (70 lbs)

### Anthropometric Table
- **Entries:** 24
| Age (mo) | Male Weight | Female Weight | % Adult |
| --- | --- | --- | --- |
| 1 | 4.7–7.7 kg | 4.0–6.5 kg | 7.5 |
| 2 | 6.0–9.0 kg | 5.0–7.5 kg | 15 |
| 3 | 10.0–14.0 kg | 8.0–12.0 kg | 25 |
| 4 | 16.0–18.0 kg | 13.0–16.0 kg | 35 |
| 5 | 18.1–22.0 kg | 16.0–20.0 kg | 45 |
*(... and 19 more)*

### Gonadal Status Profiles
- **Count:** 4
  - `GON_MALE_INTACT`: male/intact
  - `GON_MALE_NEUTERED_EARLY`: male/neutered_early
  - `GON_FEMALE_INTACT`: female/intact
  - `GON_FEMALE_SPAYED_EARLY`: female/spayed_early

### Epidemiology (DOD)
- **Entries:** 12
  - `EPI_DOD_OVERALL`: overall_DOD_pct = 2.84
  - `EPI_CHD_PCT`: CHD_pct_of_DODs = 52.24
  - `EPI_ELBOW_PCT`: elbow_dysplasia_pct_of_DODs = 7.46
  - `EPI_OSTEOCHONDROSIS_PCT`: osteochondrosis_pct_of_DODs = 5.97
  - `EPI_PANOSTEITIS_PCT`: panosteitis_pct_of_DODs = 5.97
  - `EPI_HOD_PCT`: HOD_pct_of_DODs = 7.46
  - `EPI_DOD_MAX_AGE`: max_incidence_age_months = [4, 9]
  - `EPI_CHD_MALE_PCT`: CHD_sex_prevalence_males_pct = 54
  - `EPI_CHD_FEMALE_PCT`: CHD_sex_prevalence_females_pct = 33
  - `EPI_BMD_MALE`: BMD_sex_males = 1.0
  - `EPI_BMD_FEMALE`: BMD_sex_females = 0.0
  - `EPI_BMD_AGE_TREND`: BMD_age_trend_negative_correlation = -1.0

## objective_weights.json — Objective Weights

- **Count:** 29

| ID | Variable | Weight | Tier | Penalty Multiplier |
| --- | --- | --- | --- | --- |
| `PEN_CA_POS` | calcium_g | 10000 | 1 | {'neutered_early': {'multiplier': 1.5, 'condition': 'gonadal_status == neutered_early'}, 'spayed_early': {'multiplier': 1.5, 'condition': 'gonadal_status == spayed_early'}} |
| `PEN_CA_P_RATIO_SYM` | ca_p_ratio | 7000 | 1 | None |
| `PEN_CA_NEG` | calcium_g | 5000 | 1 | None |
| `PEN_VIT_AD3_POS` | vitamin_a_iu | 4000 | 1 | None |
| `PEN_CALORIC_POS` | caloric_density | 6000 | 2 | {'neutered_early': {'multiplier': 1.3, 'condition': 'gonadal_status == neutered_early'}, 'spayed_early': {'multiplier': 1.3, 'condition': 'gonadal_status == spayed_early'}} |
| `PEN_PHOSPHORUS_NEG` | phosphorus_g | 3000 | 2 | None |
| `PEN_PROTEIN_NEG` | protein_g | 3000 | 2 | None |
| `PEN_ZINC_NEG` | zinc_mg | 2000 | 2 | None |
| `PEN_VITAMIN_A_NEG` | vitamin_a_iu | 2000 | 2 | None |
| `PEN_VITAMIN_D3_NEG` | vitamin_d3_iu | 2000 | 2 | None |
| `PEN_FAT_NEG` | fat_g | 1500 | 3 | None |
| `PEN_LYSINE_NEG` | lysine_g | 1500 | 3 | None |
| `PEN_MET_CYS_NEG` | methionine_plus_cystine_g | 1500 | 3 | None |
| `PEN_MAGNESIUM_NEG` | magnesium_g | 1000 | 3 | None |
| `PEN_EPA_DHA_NEG` | epa_plus_dha_g | 800 | 3 | None |
| `PEN_LINOLEIC_NEG` | linoleic_acid_g | 800 | 3 | None |
| `PEN_SODIUM_NEG` | sodium_g | 800 | 3 | None |
| `PEN_IRON_NEG` | iron_mg | 800 | 3 | None |
| `PEN_COPPER_NEG` | copper_mg | 800 | 3 | None |
| `PEN_SELENIUM_NEG` | selenium_mg | 800 | 3 | None |
| `PEN_VITAMIN_E_NEG` | vitamin_e_iu | 800 | 3 | None |
| `PEN_MANGANESE_NEG` | manganese_mg | 400 | 4 | None |
| `PEN_POTASSIUM_NEG` | potassium_g | 600 | 4 | None |
| `PEN_CHOLINE_NEG` | choline_g | 600 | 4 | None |
| `PEN_ALA_NEG` | ala_alpha_linolenic_acid_g | 500 | 4 | None |
| `PEN_ARA_NEG` | ara_arachidonic_acid_g | 500 | 4 | None |
| `PEN_CHLORIDE_NEG` | chloride_g | 400 | 4 | None |
| `PEN_IODINE_NEG` | iodine_mg | 400 | 4 | None |
| `PEN_COST_POS` | cost_per_kg | 10 | 5 | None |

## scenarios.json — Scenarios

- **Count:** 2

### `SCN_A_RAPID_GROWTH`: Cenario A - Crescimento Rapido (Desaconselhado)
- **Status:** WARNING_DO_NOT_OPTIMIZE
- **Targets:** 17
| Nutrient | Value | Unit | Source |
| --- | --- | --- | --- |
| caloric_density | 4500 | kcal_per_kg_DM | REF_SCENARIO_CMP |
| protein_g | 60 | g | REF_SCENARIO_CMP |
| fat_g | 25 | g | REF_SCENARIO_CMP |
| calcium_g | 4.5 | g | REF_SCENARIO_CMP |
| phosphorus_g | 4 | g | REF_SCENARIO_CMP |
| ca_p_ratio | 1.125 | ratio | REF_SCENARIO_CMP |
| linoleic_acid_g | 3.25 | g | REF_SCENARIO_CMP |
| ala_alpha_linolenic_acid_g | 0.2 | g | REF_SCENARIO_CMP |
*(... and 9 more)*

### `SCN_B_SLOW_GROWTH`: Cenario B - Crescimento Lento (Recomendado)
- **Status:** ACTIVE_TARGET
- **Targets:** 17
| Nutrient | Value | Unit | Source |
| --- | --- | --- | --- |
| caloric_density | 3500 | kcal_per_kg_DM | REF_SCENARIO_CMP |
| protein_g | 50 | g | REF_SCENARIO_CMP |
| fat_g | 15 | g | REF_SCENARIO_CMP |
| calcium_g | 3 | g | REF_SCENARIO_CMP |
| phosphorus_g | 2.5 | g | REF_SCENARIO_CMP |
| ca_p_ratio | 1.2 | ratio | REF_SCENARIO_CMP |
| linoleic_acid_g | 3.25 | g | REF_SCENARIO_CMP |
| ala_alpha_linolenic_acid_g | 0.2 | g | REF_SCENARIO_CMP |
*(... and 9 more)*

## toxicological_limits.json — Safe Upper Limits (SULs)

- **Type at top level:** `list` (8 entries)
- **Structure:** Each entry has nested `sul.value`, `sul.unit`, `sul.basis`

| Nutrient | SUL Value | Unit | Basis | Patho Ref |
| --- | --- | --- | --- | --- |
| `copper_mg` | 100 | mg | energy_normalized | REF_SUL_CU_PATHO |
| `iron_mg` | 130 | mg | energy_normalized | REF_SUL_FE_PATHO |
| `sodium_g` | 3.75 | g | energy_normalized | REF_SUL_NA_PATHO |
| `vitamin_a_iu` | 9375 | IU | energy_normalized | REF_SUL_VIT_A_PATHO |
| `vitamin_d3_iu` | 750 | IU | energy_normalized | REF_SUL_VIT_D3_PATHO |
| `iodine_mg` | 2.5 | mg | energy_normalized | REF_SUL_I_PATHO |
| `zinc_mg` | 300 | mg | energy_normalized | REF_SUL_ZN_PATHO |
| `manganese_mg` | 15 | mg | energy_normalized | REF_SUL_MN_PATHO |

## lp_parameters_data.json — Runtime LP Parameters
**Schema version:** 10.4.0

### NUTRIENT_REGISTRY
- **Total nutrients:** 41
- **Tiers:** {'adequacy_soft': 33, 'safety_hard': 8}
- **Clinical criticality:** {'critical': 8, 'high': 7, 'low': 8, 'moderate': 18}
- **Safety hard (has SUL):** `sodium_g`, `iron_mg`, `copper_mg`, `manganese_mg`, `zinc_mg`, `iodine_mg`, `vitamin_a_iu`, `vitamin_d3_iu`

#### SUL Nutrients (from NUTRIENT_REGISTRY)
| Nutrient | Display Name | SUL Value | Unit | Criticality |
| --- | --- | --- | --- | --- |
| `sodium_g` | Sodium G | 3.75 | g | high |
| `iron_mg` | Iron Mg | 130 | mg | high |
| `copper_mg` | Copper Mg | 100 | mg | high |
| `manganese_mg` | Manganese Mg | 15 | mg | moderate |
| `zinc_mg` | Zinc Mg | 300 | mg | critical |
| `iodine_mg` | Iodine Mg | 2.5 | mg | moderate |
| `vitamin_a_iu` | Vitamin A Iu | 9375 | IU | high |
| `vitamin_d3_iu` | Vitamin D3 Iu | 750 | IU | critical |

### Declarative Cascade (solve_cascade)
- **Levels:** 3

#### Level 1: optimal
- **Description:** Try to solve with EVERYTHING respected. SULs (hard) + adequacy floors (hard) + DER/density/Ca:P (wit
- **Relax tiers:** []
- **Objective stages:** goal_deviation

#### Level 2: suboptimal
- **Description:** Relax adequacy floors via slack weighted by clinical_criticality. SULs remain hard.
- **Relax tiers:** ['adequacy_soft', 'envelope_soft']
- **Objective stages:** adequacy_slack

#### Level 3: unsafe_diagnostic
- **Description:** Minimize SUL violation while trying to get as close as possible to DER. Real data, real calculation,
- **Relax tiers:** ['adequacy_soft', 'envelope_soft', 'safety_hard']
- **Objective stages:** sul_violation, der_deviation, adequacy_slack
- **Clinical floor:** enabled (defaults: {'muscle_meat': 10, 'organ_secreting': 5, 'organ_non_secreting': 5, 'bone': 5, 'fat_source': 2, 'supplement': 0.1})
- **Output:** allocations=None, feeding=DO_NOT_FEED

## Live Execution Evidence

> Smoke runs against the production pipeline (`build_pipeline.py`).
> Scrubbed of timestamps/paths/PIDs via `scrub_volatile()` for idempotent regeneration.
> Source: `doc_introspector.capture_live_evidence()` + `tests/reference_cases.py`.

Captured 4 smoke runs:

### Evidence: calculate_der_and_envelope

- **Status:** OK
- **Severity:** HARD

**Captured stdout (scrubbed):**
```
(no stdout)
```

**Result (JSON, may be truncated to 2000 chars):**
```json
{
  "bw_kg": 45.0,
  "density_source": "selected_ingredients",
  "der_kcal": 1459.4481534632191,
  "k_multiplier": 1.2,
  "max_total_g": 1459.4481534632191,
  "min_total_g": 708.8523141483524,
  "strategy": "der_derived",
  "ter_kcal": 1216.2067945526826,
  "units_of_1000kcal": 1.459448153463219
}
```

<!-- SOURCE: doc_introspector.capture_live_evidence / tests/reference_cases.py -->

### Evidence: --runtime smoke (solve_cascade)

- **Status:** OK
- **Severity:** HARD
- **solver_status:** `suboptimal`
- **cascade_level_used:** `2`
- **lexicographic_stages_solved:** `None`
- **clinical_floor_relaxed:** `None`
- **solve_time_ms:** `0`
- **nutrients_above_90pct_sul:** `[]`

**Captured stdout (scrubbed):**
```
[DEBUG] Level 1: relax_tiers = set()
[DEBUG] CSTR_NB_ARGININE_G_MIN: nid=arginine_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_HISTIDINE_G_MIN: nid=histidine_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_ISOLEUCINE_G_MIN: nid=isoleucine_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_LEUCINE_G_MIN: nid=leucine_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_METHIONINE_G_MIN: nid=methionine_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_PHENYLALANINE_G_MIN: nid=phenylalanine_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_PHENYLALANINE_PLUS_TYROSINE_G_MIN: nid=phenylalanine_plus_tyrosine_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_THREONINE_G_MIN: nid=threonine_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_TRYPTOPHAN_G_MIN: nid=tryptophan_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_VALINE_G_MIN: nid=valine_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_LINOLEIC_ACID_G_MIN: nid=linoleic_acid_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_ALA_ALPHA_LINOLENIC_ACID_G_MIN: nid=ala_alpha_linolenic_acid_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_ARA_ARACHIDONIC_ACID_G_MIN: nid=ara_arachidonic_acid_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_MAGNESIUM_G_MIN: nid=magnesium_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_SODIUM_G_MIN: nid=sodium_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_POTASSIUM_G_MIN: nid=potassium_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_CHLORIDE_G_MIN: nid=chloride_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_IRON_MG_MIN: nid=iron_mg, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_COPPER_MG_MIN: nid=copper_mg, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_MANGANESE_MG_MIN: nid=manganese_mg, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_IODINE_MG_MIN: nid=iodine_mg, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_SELENIUM_MG_MIN: nid=selenium_mg, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_VITAMIN_E_IU_MIN: nid=vitamin_e_iu, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_THIAMINE_B1_MG_MIN: nid=thiamine_b1_mg, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_RIBOFLAVIN_B2_MG_MIN: nid=riboflavin_b2_mg, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_PANTOTHENIC_ACID_B5_MG_MIN: nid=pantothenic_acid_b5_mg, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_NIACIN_B3_MG_MIN: nid=niacin_b3_mg, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_PYRIDOXINE_B6_MG_MIN: nid=pyridoxine_b6_mg, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_FOLIC_ACID_B9_MG_MIN: nid=folic_acid_b9_mg, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_COBALAMIN_B12_MG_MIN: nid=cobalamin_b12_mg, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_CHOLINE_G_MIN: nid=choline_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_CALCIUM_G_MIN: nid=calcium_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_PHOSPHORUS_G_MIN: nid=phosphorus_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_PROTEIN_G_MIN: nid=protein_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_ZINC_MG_MIN: nid=zinc_mg, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_VITAMIN_A_IU_MIN: nid=vitamin_a_iu, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_VITAMIN_D3_IU_MIN: nid=vitamin_d3_iu, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_FAT_G_MIN: nid=fat_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_LYSINE_G_MIN: nid=lysine_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_MET_PLUS_CYS_G_MIN: nid=methionine_plus_cystine_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] CSTR_NB_EPA_PLUS_DHA_G_MIN: nid=epa_plus_dha_g, tier=adequacy_soft, is_relaxed=False
[DEBUG] Level 2: relax_tiers = {'adequacy_soft', 'envelope_soft'}
[DEBUG] CSTR_NB_ARGININE_G_MIN: nid=arginine_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_HISTIDINE_G_MIN: nid=histidine_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_ISOLEUCINE_G_MIN: nid=isoleucine_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_LEUCINE_G_MIN: nid=leucine_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_METHIONINE_G_MIN: nid=methionine_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_PHENYLALANINE_G_MIN: nid=phenylalanine_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_PHENYLALANINE_PLUS_TYROSINE_G_MIN: nid=phenylalanine_plus_tyrosine_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_THREONINE_G_MIN: nid=threonine_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_TRYPTOPHAN_G_MIN: nid=tryptophan_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_VALINE_G_MIN: nid=valine_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_LINOLEIC_ACID_G_MIN: nid=linoleic_acid_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_ALA_ALPHA_LINOLENIC_ACID_G_MIN: nid=ala_alpha_linolenic_acid_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_ARA_ARACHIDONIC_ACID_G_MIN: nid=ara_arachidonic_acid_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_MAGNESIUM_G_MIN: nid=magnesium_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_SODIUM_G_MIN: nid=sodium_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_POTASSIUM_G_MIN: nid=potassium_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_CHLORIDE_G_MIN: nid=chloride_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_IRON_MG_MIN: nid=iron_mg, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_COPPER_MG_MIN: nid=copper_mg, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_MANGANESE_MG_MIN: nid=manganese_mg, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_IODINE_MG_MIN: nid=iodine_mg, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_SELENIUM_MG_MIN: nid=selenium_mg, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_VITAMIN_E_IU_MIN: nid=vitamin_e_iu, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_THIAMINE_B1_MG_MIN: nid=thiamine_b1_mg, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_RIBOFLAVIN_B2_MG_MIN: nid=riboflavin_b2_mg, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_PANTOTHENIC_ACID_B5_MG_MIN: nid=pantothenic_acid_b5_mg, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_NIACIN_B3_MG_MIN: nid=niacin_b3_mg, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_PYRIDOXINE_B6_MG_MIN: nid=pyridoxine_b6_mg, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_FOLIC_ACID_B9_MG_MIN: nid=folic_acid_b9_mg, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_COBALAMIN_B12_MG_MIN: nid=cobalamin_b12_mg, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_CHOLINE_G_MIN: nid=choline_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_CALCIUM_G_MIN: nid=calcium_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_PHOSPHORUS_G_MIN: nid=phosphorus_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_PROTEIN_G_MIN: nid=protein_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_ZINC_MG_MIN: nid=zinc_mg, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_VITAMIN_A_IU_MIN: nid=vitamin_a_iu, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_VITAMIN_D3_IU_MIN: nid=vitamin_d3_iu, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_FAT_G_MIN: nid=fat_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_LYSINE_G_MIN: nid=lysine_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_MET_PLUS_CYS_G_MIN: nid=methionine_plus_cystine_g, tier=adequacy_soft, is_relaxed=True
[DEBUG] CSTR_NB_EPA_PLUS_DHA_G_MIN: nid=epa_plus_dha_g, tier=adequacy_soft, is_relaxed=True

```

**Result (JSON, may be truncated to 2000 chars):**
```json
{
  "_unrounded_total_g": 708.85232,
  "alerts": [],
  "allocations": [
    {
      "category": "muscle_organ",
      "cost_per_day": null,
      "display_name": "Cora\u00e7\u00e3o de Frango Cru",
      "grams_per_day": 552.9,
      "ingredient_id": "chicken_heart_raw",
      "kcal_per_day": 780.4,
      "pct_of_total": 78.0
    },
    {
      "category": "fish",
      "cost_per_day": null,
      "display_name": "Salm\u00e3o do Atl\u00e2ntico Cru",
      "grams_per_day": 155.9,
      "ingredient_id": "salmon_atlantic_raw",
      "kcal_per_day": 289.0,
      "pct_of_total": 22.0
    }
  ],
  "animal_context": {
    "age_months": 8,
    "bw_source": "gompertz",
    "der_kcal": 1459.4481534632191,
    "gonadal_status": "intact",
    "k_multiplier": 1.2,
    "sex": "male",
    "ter_kcal": 1216.2067945526826,
    "weight_kg": 45.0
  },
  "cascade_level_used": 2,
  "diagnostic_analysis": null,
  "envelope": {
    "actual_total_g": null,
    "max_total_g": 1459.4481534632191,
    "min_total_g": 708.8523141483524,
    "strategy": "der_derived"
  },
  "feeding_recommendation": "FEED_WITH_CAUTION",
  "gaps": [
    {
      "category_missing": "bone",
      "note": "Ratio calcium_g/phosphorus_g = 0.059, bound >= 1.100",
      "nutrient_id": "calcium_g_phosphorus_g_ratio",
      "pct_of_min": 5.4,
      "top_ingredients_in_category": []
    },
    {
      "category_missing": "organ_secreting",
      "note": "Ratio zinc_mg/copper_mg = 18.655, bound <= 12.000",
      "nutrient_id": "zinc_mg_copper_mg_ratio",
      "pct_of_min": 155.5,
      "top_ingredients_in_category": []
    },
    {
      "category_missing": "bone",
      "note": "Ratio calcium_g/magnesium_g = 0.643, bound >= 12.000",
      "nutrient_id": "calcium_g_magnesium_g_ratio",
      "pct_of_min": 5.4,
      "top_ingredients_in_category": []
    },
    {
      "category_missing": "muscle_meat",
      "note": "Ratio lysine_g/arginine_g undefined (denominator missing)",
      "nutrient_id": "lysine_g_arginine_g_ratio",
 ... (truncated, 16915 more chars)
```

<!-- SOURCE: doc_introspector.capture_live_evidence / tests/reference_cases.py -->

### Evidence: check_fat_source_adequacy (no fat_source)

- **Status:** OK
- **Severity:** SOFT

**Captured stdout (scrubbed):**
```
(no stdout)
```

**Result (JSON, may be truncated to 2000 chars):**
```json
{
  "fat_gap": null
}
```

<!-- SOURCE: doc_introspector.capture_live_evidence / tests/reference_cases.py -->

### Evidence: solver_status_diagnostic

- **Status:** DEGRADED
- **Severity:** SOFT

**Captured stdout (scrubbed):**
```
(no stdout)
```

**Result (JSON, may be truncated to 2000 chars):**
```json
{
  "alerts_count": 0,
  "cascade_level_used": 2,
  "first_5_alert_severities": [],
  "first_5_gap_nutrients": [
    "calcium_g_phosphorus_g_ratio",
    "zinc_mg_copper_mg_ratio",
    "calcium_g_magnesium_g_ratio",
    "lysine_g_arginine_g_ratio",
    "lysine_g_arginine_g_ratio"
  ],
  "gaps_count": 5,
  "lexicographic_stages_used": null,
  "solver_status": "suboptimal"
}
```

<!-- SOURCE: doc_introspector.capture_live_evidence / tests/reference_cases.py -->

## Test Suite Integrity

> AAA+A anti-gamification analysis of every `test_*.py` file.
> Source: `doc_introspector.check_test_integrity()` — D6 v1.2 regex.
> The production loader (`bp.load_all_jsons()`) is the canonical way to load real data.
> Direct `json.load(samples/...)` calls are an anti-pattern — they bypass loader validation.

| File | `@pytest.mark.integration` | Loads Real Data | AAA+A Compliant |
| --- | --- | --- | --- |
| `test_cascade_integration.py` | No | Yes | Yes |
| `test_dimensional_pipeline.py` | No | Yes | Yes |

<!-- SOURCE: doc_introspector.check_test_integrity / D6 v1.2 regex -->

## Naming Conventions — DB Space vs Solver Space

The system operates with two naming conventions:

- **DB space** (`DB_ingredientes.json`): unit-matching suffix (e.g. `calcium_mg`, `selenium_ug`). Basis: `as_fed`, reference: 100g.
- **Solver space** (`NUTRIENT_REGISTRY`): standardized unit suffix (e.g. `calcium_g`, `selenium_mg`). Basis: `energy_normalized`, reference: 1000kcal.

**Total solver-space nutrients:** 41

| Solver ID | Display Name | Unit | Tier | DB→Solver Rename |
| --- | --- | --- | --- | --- |
| `protein_g` | Protein G | g | adequacy_soft | same |
| `fat_g` | Fat G | g | adequacy_soft | same |
| `arginine_g` | Arginine G | g | adequacy_soft | same |
| `histidine_g` | Histidine G | g | adequacy_soft | same |
| `isoleucine_g` | Isoleucine G | g | adequacy_soft | same |
| `leucine_g` | Leucine G | g | adequacy_soft | same |
| `lysine_g` | Lysine G | g | adequacy_soft | same |
| `methionine_g` | Methionine G | g | adequacy_soft | same |
| `methionine_plus_cystine_g` | Methionine Plus Cystine G | g | adequacy_soft | same |
| `phenylalanine_g` | Phenylalanine G | g | adequacy_soft | same |
| `phenylalanine_plus_tyrosine_g` | Phenylalanine Plus Tyrosine G | g | adequacy_soft | same |
| `threonine_g` | Threonine G | g | adequacy_soft | same |
| `tryptophan_g` | Tryptophan G | g | adequacy_soft | same |
| `valine_g` | Valine G | g | adequacy_soft | same |
| `linoleic_acid_g` | Linoleic Acid G | g | adequacy_soft | same |
| `ala_alpha_linolenic_acid_g` | Ala Alpha Linolenic Acid G | g | adequacy_soft | same |
| `ara_arachidonic_acid_g` | Ara Arachidonic Acid G | g | adequacy_soft | same |
| `epa_plus_dha_g` | Epa Plus Dha G | g | adequacy_soft | same |
| `calcium_g` | Calcium G | g | adequacy_soft | calcium_mg→calcium_g |
| `phosphorus_g` | Phosphorus G | g | adequacy_soft | phosphorus_mg→phosphorus_g |
| `magnesium_g` | Magnesium G | g | adequacy_soft | magnesium_mg→magnesium_g |
| `sodium_g` | Sodium G | g | safety_hard | sodium_mg→sodium_g |
| `potassium_g` | Potassium G | g | adequacy_soft | potassium_mg→potassium_g |
| `chloride_g` | Chloride G | g | adequacy_soft | chloride_mg→chloride_g |
| `iron_mg` | Iron Mg | mg | safety_hard | same |
| `copper_mg` | Copper Mg | mg | safety_hard | same |
| `manganese_mg` | Manganese Mg | mg | safety_hard | same |
| `zinc_mg` | Zinc Mg | mg | safety_hard | same |
| `iodine_mg` | Iodine Mg | mg | safety_hard | iodine_ug→iodine_mg |
| `selenium_mg` | Selenium Mg | mg | adequacy_soft | selenium_ug→selenium_mg |
| `vitamin_a_iu` | Vitamin A Iu | IU | safety_hard | same |
| `vitamin_d3_iu` | Vitamin D3 Iu | IU | safety_hard | same |
| `vitamin_e_iu` | Vitamin E Iu | IU | adequacy_soft | same |
| `thiamine_b1_mg` | Thiamine B1 Mg | mg | adequacy_soft | same |
| `riboflavin_b2_mg` | Riboflavin B2 Mg | mg | adequacy_soft | same |
| `pantothenic_acid_b5_mg` | Pantothenic Acid B5 Mg | mg | adequacy_soft | same |
| `niacin_b3_mg` | Niacin B3 Mg | mg | adequacy_soft | same |
| `pyridoxine_b6_mg` | Pyridoxine B6 Mg | mg | adequacy_soft | same |
| `folic_acid_b9_mg` | Folic Acid B9 Mg | mg | adequacy_soft | folic_acid_b9_ug→folic_acid_b9_mg |
| `cobalamin_b12_mg` | Cobalamin B12 Mg | mg | adequacy_soft | cobalamin_b12_ug→cobalamin_b12_mg |
| `choline_g` | Choline G | g | adequacy_soft | choline_mg→choline_g |

### Unit Conversions (DB → Solver)

| DB Field | Solver ID | Conversion |
| --- | --- | --- |
| `calcium_mg` | `calcium_g` | ÷1,000 |
| `chloride_mg` | `chloride_g` | ÷1,000 |
| `choline_mg` | `choline_g` | ÷1,000 |
| `cobalamin_b12_ug` | `cobalamin_b12_mg` | ÷1,000 |
| `folic_acid_b9_ug` | `folic_acid_b9_mg` | ÷1,000 |
| `iodine_ug` | `iodine_mg` | ÷1,000 |
| `magnesium_mg` | `magnesium_g` | ÷1,000 |
| `phosphorus_mg` | `phosphorus_g` | ÷1,000 |
| `potassium_mg` | `potassium_g` | ÷1,000 |
| `selenium_ug` | `selenium_mg` | ÷1,000 |
| `sodium_mg` | `sodium_g` | ÷1,000 |

## Curation Status — Ingredient Groups

**Total ingredients:** 23
**Provenance refs:** 143 total
  - **AUTHORITATIVE_DATABASE:** 1
  - **CONFIRMED:** 114
  - **COPY_PASTE_ERROR_CORRECTED:** 2
  - **INFERRED:** 18
  - **LITERATURE_COMPOSITE:** 7
  - **UNIT_INCONSISTENCY_RESOLVED:** 1

| Group | Common Name | Count | Ingredient IDs | Status |
| --- | --- | --- | --- | --- |
| bovinos | Bovinos (Bos taurus) | 11 | beef_muscle_raw, beef_lung_raw, beef_foot_tendon_raw, beef_tail_raw, beef_tongue_raw, beef_blood_raw, beef_heart_raw, beef_green_tripe_raw, beef_liver_raw, beef_kidney_raw, beef_spleen_raw | VALIDATED |
| aves | Aves (Gallus gallus domesticus) | 6 | chicken_muscle_raw, chicken_heart_raw, chicken_liver_raw, chicken_kidney_raw, chicken_foot_tendon_raw, chicken_blood_raw | PENDING+PARTIAL |
| suinos | Suinos (Sus scrofa domesticus) | 2 | pork_muscle_raw, pork_liver_raw | PARTIAL |
| peixes | Peixes | 1 | salmon_atlantic_raw | PARTIAL |
| fat_sources | Fontes de Gordura (Suet/Sebo, Gordura Separavel) | 3 | beef_fat_raw, chicken_fat_raw, pork_fat_raw | PARTIAL |
| supplements (planned) | Kelp, Salt, CuSO₄ | 0 (3 planned) | kelp_meal_dried, salt_nacl, copper_sulfate | PLANNED (not applied) |

## Gaps and Unimplemented Dependencies

### DB Gaps
- **Planned supplements absent from DB:** 3
  - `kelp_meal_dried` — PLANNED, NOT applied per `sat_operacional:§15`
  - `salt_nacl` — PLANNED, NOT applied per `sat_operacional:§15`
  - `copper_sulfate` — PLANNED, NOT applied per `sat_operacional:§15`

### Reference Gaps
- **Internal REF_ tokens in DB ingredients:** 0
- **Known in audit_provenance:** 143
- **Orphans (in DB but absent from audit_provenance):** 0
- **Note:** The 17 refs listed in §9.2 are PLANNED items not yet in DB, not orphans. Actual orphans in DB: 0

### Implementation Gaps (Pipeline)
| Name | Priority | Spec Ref | Status | Line | Note |
| --- | --- | --- | --- | --- | --- |
| call_lp_solver | P0 | sat_solver_contrato:§8 | IMPLEMENTED | 2725 | toplevel function at L2725 <!-- SOURCE: IMPLEMENTATION_SPEC / build_pipeline.py:L2725 --> |
| DerEnvelope | P0 | sat_princípios:§3.3 | IMPLEMENTED | 192 | toplevel class at L192 <!-- SOURCE: IMPLEMENTATION_SPEC / build_pipeline.py:L192 --> |
| build_diagnostic_analysis | P0 | sat_solver_contrato:§7.2 | IMPLEMENTED | 3450 | toplevel function at L3450 <!-- SOURCE: IMPLEMENTATION_SPEC / build_pipeline.py:L3450 --> |
| build_lp_problem | P0 | sat_solver_contrato:§8.1 | IMPLEMENTED | 2269 | toplevel function at L2269 <!-- SOURCE: IMPLEMENTATION_SPEC / build_pipeline.py:L2269 --> |
| --runtime mode | P0 | sat_pipeline_codigo:§6.4 | IMPLEMENTED | — | CLI mode exists and is fully implemented <!-- SOURCE: IMPLEMENTATION_SPEC / build_pipeline.py:N/A --> |
| --build-recipes mode | P1 | sat_pipeline_fluxo:§6.3 | IMPLEMENTED | — | CLI mode is a stub (as expected) <!-- SOURCE: IMPLEMENTATION_SPEC / build_pipeline.py:N/A --> |
| recipes_precomputed.json | P1 | sat_pipeline_fluxo:§5.2 | NOT IMPLEMENTED | — | file does not exist <!-- SOURCE: IMPLEMENTATION_SPEC / build_pipeline.py:N/A --> |
| format_allocations | P2 | sat_pipeline_codigo:§6.4a | MISSING | — | not found in module AST <!-- SOURCE: IMPLEMENTATION_SPEC / build_pipeline.py:N/A --> |
| expand_category_wildcards | P2 | sat_pipeline_codigo:§6.4a | MISSING | — | not found in module AST <!-- SOURCE: IMPLEMENTATION_SPEC / build_pipeline.py:N/A --> |
| run_pipeline | P2 | sat_pipeline_codigo:§6.4 | MISSING | — | not found in module AST <!-- SOURCE: IMPLEMENTATION_SPEC / build_pipeline.py:N/A --> |

## Cross-Reference Audit & Divergences

### Orphan Reference Audit
- **Total REF_ tokens in DB:** 50
- **USDA (external):** 23
- **Internal refs:** 27
- **In audit_provenance.json:** 143
- **Orphans (internal but not in audit_provenance):** 0

### Documented vs Actual Divergences

| Claim | Documented | Actual | Status | Decision |
| --- | --- | --- | --- | --- |
| DB version vs actual ingredient count | 3.1.1 | 23 | [DIVERGE] | accept |
| Orphan refs resolved | 0 (per docs) | §9.2 items are PLANNED, not orphans. Actual orphans in DB: 0 | [DIVERGE] | defer |
| Provenance refs count | 85 (per docs) | 143 (114 CONFIRMED, 18 INFERRED, 7 LITERATURE_COMPOSITE, 2 COPY_PASTE_ERROR_CORRECTED, 1 UNIT_INCONSISTENCY_RESOLVED, 1 AUTHORITATIVE_DATABASE) | [DIVERGE] | accept |
| solve_cascade location | lp_parameters.schema (per docs) | lp_parameters_data.json | [DIVERGE] | accept |
| NUTRIENT_REGISTRY location | lp_parameters.schema (per docs) | lp_parameters_data.json | [DIVERGE] | accept |
| All constraints HARD_FAIL_INFEASIBLE | no (V10 cascade) | All 60 constraints are HARD_FAIL_INFEASIBLE. V10 cascade uses slack variables in LP formulation, not constraint relaxation. | [DIVERGE] | defer |
| scenarios.json top-level type | dict with 'scenarios' key | list | [DIVERGE] | accept |
| Adult k_multiplier | does not exist | exists (adult_working_active: 1.5) | [DIVERGE] | accept |
| Missing supplements in DB | 0 (claimed 23) | 3 planned missing (kelp_meal_dried, salt_nacl, copper_sulfate) — per §9.1 | [DIVERGE] | defer |
| nutrient_matrix structure | dict with min/max | list with nested values | [DIVERGE] | accept |


## Coverage Watch (informational)

New keys detected in live JSONs that are not yet covered by STRUCTURE_CONTRACTS:

- formulation_rules.json: top-level key '_db_ref' not in any STRUCTURE_CONTRACT covers
