<!-- MAPA:STATIC-START -->
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
<!-- MAPA:STATIC-END -->
<!-- MAPA:AUTO-BUNDLES -->
## Bundles (Selective Loading per Scenario)

|Bundle|Satellites|Lines|Est. tokens|Savings|
|---|---|---|---|---|
|**BUNDLE_CURADORIA**|index + sat_dados_schema|~455|~5.5k|78%|
|**BUNDLE_DESIGN_PIPELINE**|index + sat_pipeline_fluxo + sat_princípios|~453|~5.0k|80%|
|**BUNDLE_IMPL_PIPELINE**|index + sat_pipeline_codigo + sat_dados_schema|~936|~11.3k|55%|
|**BUNDLE_SOLVER_DESIGN**|index + sat_solver_contrato + sat_princípios|~929|~10.4k|59%|
|**BUNDLE_SOLVER_IMPL**|index + sat_solver_contrato + sat_dados_schema|~1138|~12.8k|49%|
|**BUNDLE_QA_SOLVER**|index + sat_solver_contrato + sat_testes_consolidado|~867|~9.7k|61%|
|**BUNDLE_QA_DADOS**|index + sat_dados_schema + sat_testes_consolidado|~482|~5.4k|79%|
|**BUNDLE_OPERACIONAL**|index + sat_operacional|~304|~3.7k|85%|

**BUNDLE_SOLVER_DESIGN vs BUNDLE_SOLVER_IMPL distinction:**
- `BUNDLE_SOLVER_DESIGN` (with `sat_princípios`): for solver **audit/design** — review cascade principles, conceptual justification, validate if a change violates canonical principles.
- `BUNDLE_SOLVER_IMPL` (with `sat_dados_schema`): to **implement** `solve_cascade()` — needs `constraint_tier` (sat_dados_schema:§4.2), declarative `solve_cascade[]` (sat_dados_schema:§4.3), and `NUTRIENT_REGISTRY` shape. Without these, implementation is impossible.

Agent requests bundle by name. Does not select individual satellites.

---
<!-- MAPA:AUTO-ROADMAP -->
## Implementation Roadmap (build order)

Recommended sequence for agentic AI to build system from scratch. Each phase has explicit dependencies and corresponding bundle.

### Phase 0 — Verified baseline and data curation (BUNDLE_CURADORIA)
**Prerequisite:** none.
**Files:** `sat_dados_schema` (§4.1, §9.1, §9.2, §9.3, §14).
**Actions:**
1. Obtain the real 9 JSONs and executable source; record source, SHA-256, version, and parse result for each. Do not start from Markdown examples.
2. Add `kelp_meal_dried`, `salt_nacl`, `copper_sulfate` only after source, concentration, unit, variability, and SUL impact are verified (see §9.1).
3. Resolve 17 planned `source_ref`s in `audit_provenance.json` — these are entries for future ingredients, not orphans (see §9.2).
4. Extract real `cystine_g` and `tyrosine_g` from USDA (see §9.3).
5. Create/update `lp_parameters_schema.json` with `NUTRIENT_REGISTRY`, unit/basis declarations, and the declarative cascade.
**DoD:** real files parse; every critical value has unit+basis+provenance; no P0 data anomaly remains. See `sat_dados_schema:✅ Definition of Done`.

### Phase 1 — Dimensional contract and transformation pipeline (BUNDLE_IMPL_PIPELINE)
**Prerequisite:** Phase 0 completed.
**Files:** `sat_pipeline_codigo` (§6.4), `sat_dados_schema` (§4.1).
**Actions:**
1. Implement `load_all_jsons()` — loads 9 JSONs.
2. Implement `validate_inputs(data)` — 6 assertions (a-f).
3. Implement `calculate_der_and_envelope()` from the densities of the selected ingredients, with a documented fallback only when selection is empty.
4. Implement `as_fed/100g → energy_normalized/1000kcal`, then compile to one daily LP basis (`nutrient/g × g/day` or an explicitly energy-based equivalent).
5. Scale targets and SULs to the animal DER before building `a_ij`; add dimensional and round-trip tests.
**DoD:** an independent dimensional review and tests prove that coefficients, variables, targets, SULs, and output all use compatible units.

### Phase 2 — Solver, infeasibility contract, and cascade (BUNDLE_SOLVER_IMPL)
**Prerequisite:** Phase 1 completed.
**Files:** `sat_solver_contrato` (§7, §8, §A), `sat_dados_schema` (§4.2, §4.3).
**Actions:**
1. Implement `solve_cascade(matrix, constraints, schema)` as sequential lexicographic solves — minimize SUL violation, then DER deviation, then adequacy deviation — not merely scalar large weights.
2. Implement `call_lp_solver(level_config, problem)` — invokes PuLP/CVXPY/HiGHS with §8.1 formulation.
3. Implement `build_diagnostic_analysis(raw_result, clinical_floor_info)` — Level 3 only.
4. Return explicit `structurally_infeasible` and `data_incomplete` diagnoses when hard constraints or data prevent a Level 3 result; never raise a blank-screen error.
5. Implement a conditional clinical floor (`x_i = 0` OR `x_i ≥ x_min_i`) so selecting an ingredient does not force its inclusion.
**DoD:** the canonical collision, hard-ratio conflict, incomplete-data, and safe cases all yield valid, reproducible contracts.

### Phase 3 — Tests (BUNDLE_QA_SOLVER + BUNDLE_QA_DADOS)
**Prerequisite:** Phases 0-2 completed.
**Files:** `sat_testes_consolidado` (§11.5), `sat_solver_contrato:§A`, `sat_dados_schema:§A`, `sat_pipeline_fluxo:§A`.
**Actions:**
1. Implement `audit_test_result()` — log to `test_audit_log.md`.
2. Implement cascade tests (`sat_solver_contrato:§A`) — 320 lines of skeleton tests.
3. Implement data tests (`sat_dados_schema:§A`).
4. Implement recipe tests (`sat_pipeline_fluxo:§A`).
5. Run ALL against real JSONs (no fixtures).
**DoD:** `sat_testes_consolidado:✅ Definition of Done` — all 8 items checked.

### Phase 4 — Precomputed recipes (BUNDLE_DESIGN_PIPELINE)
**Prerequisite:** Phases 0-3 completed.
**Files:** `sat_pipeline_fluxo` (§5.2, §6.3, §A).
**Actions:**
1. Implement `--build-recipes` mode in `build_pipeline.py`.
2. Generate restricted combinatorial space (max 1000 combinations per template).
3. Filter combinations without minimum coverage (muscle + organ + Ca).
4. Rank by 5 criteria (completeness, safety, price, diversity, robustness).
5. Save versioned `recipes_precomputed.json`.
**DoD:** `sat_pipeline_fluxo:✅ Definition of Done` — all 9 items checked.

### Phase 5 — Anti-patterns and audit (BUNDLE_OPERACIONAL)
**Prerequisite:** Phases 0-4 completed.
**Files:** `sat_operacional` (§12, §13, §15, §16, §17).
**Actions:**
1. Verify no rejected idea in §12 was reintroduced.
2. Update §15 (curation status) with REAL ingredient count (run command and paste output).
3. Mark P0 (§13) as completed; update P1/P2.
4. Update §17 (changelog) with entry for this version.
**DoD:** `sat_operacional:✅ Definition of Done` — all 6 items checked.

### Orchestration Rule
- Each phase loads only the corresponding bundle (1-3 satellites).
- Never skip phases — dependencies are real.
- If a task needs 4+ satellites, break into sub-tasks (3-Satellite Rule).
- After each phase, run previous phase tests (regression).
