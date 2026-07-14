# sat_operacional — Anti-padrões, Roadmap, Curadoria, Gaps, Changelog

**v10.4** · ← `../architecture/indice_plano_central.md` (canônico) · `../../README.md`

**Responsibility:** Rejected anti-patterns (§12), priorities/roadmap (§13), curation status (§15), gaps and unimplemented dependencies (§16), V9→V10 changelog (§17).

**Depends on:** sat_princípios (§3 — canonical principles), sat_dados_schema (§9 — data pending) · **Referenced by:** None (reference, not dependency)

**Load when:** plan sprint · check if idea was rejected · audit state · review change history

> **Context:** Operational grouping: all project management in one place. Numbering preserves original (§12 → §13 → §15 → §16 → §17).

---

## 12. Rejected — Do Not Reintroduce (Inherited from V9 + V10 Additions)

| Item | Por que |
|---|---|
| `schema_ref` como validação funcional de DB | Aspiracional, não real. Python valida, não o schema. |
| Proxy genérico para `cystine_g`/`tyrosine_g` | Regra de não-inferência: extrair de USDA é preferível a aproximar. |
| `constraints.json.toxicological_limits` como fonte independente | `derived_from` explícito — mesma fonte em 2 formatos, não 2 fontes. |
| Usar `SCN_A` (crescimento rápido) como cenário ativo padrão | Marcado `WARNING_DO_NOT_OPTIMIZE` — existe só como contraste. |
| Pontuação decimal de "qualidade arquitetural" sem metodologia | Julgamento qualitativo não vira número sem inventar precisão. |
| **[V10]** Hardcode de `minTotal`/`maxTotal` como constante | Envelope deve ser DER-derived, não fixo em `[200, 1500]g`. |
| **[V10]** Lógica de cascata em código (if/else) | Política vive em `solve_cascade[]` no JSON, não em código. |
| **[V10]** Mockar testes de cascata com fixtures always-feasible | Testes devem exercitar descida real entre níveis. |
| **[V10]** Solver retornar vazio ou "infeasible" sem dados | Inviolabilidade: sempre devolve análise + 41 valores. Nível 3: `allocations = null`. |
| **[V10]** Gerar receitas em tempo real no frontend | Receitas são pré-computadas offline. Frontend lê `recipes_precomputed.json`. |
| **[V10.1]** Devolver gramas no Nível 3 como recomendação | `allocations = null` (barreira mecânica). Gramas matemáticas vivem em `diagnostic_analysis.what_would_happen`, como análise, não prescrição. |
| **[V10.2]** Tratar SUL como meta ponderada igual às demais no Nível 3 | Sem hierarquia `μ_j >> λ_der`, solver escolhe violar SUL para atingir DER. Hierarquia é obrigatória, não configurável. |
| **[V10.2]** Omitir `λ_der` da função objetivo do Nível 3 | Sem `λ_der`, solver produz `x_i=0` (degenerado). `λ_der > 0` força ponto não-trivial próximo do DER. |
| **[V10.2]** Hierarquia `μ_j >> λ_der >> σ_k` configurável pelo usuário | É constraint de segurança, não preferência. Calibração vive em JSON, mas validação da hierarquia é obrigatória em código. |
| **[V10.3]** Tolerar `x_i` clinicamente irrelevante no Nível 3 (ex: 0.5g fígado) | `λ_der > 0` impede `x_i=0`, mas não `x_i=0.5g`. Piso `x_i ≥ x_min_i` (5g default) obrigatório. Se relaxado, marcar `clinical_floor_relaxed = true`. |
| **[V10.3]** Piso clínico uniforme sem distinguir categoria | Suplementos (kelp, sal, CuSO₄) usam gramagens milimétricas. Piso por categoria: `muscle_meat=10g, organ=5g, supplement=0.1g`, ou por ingrediente via `clinical_floor_g`. |
| **[V10.4]** Pseudocódigo que assume estrutura de JSON sem checar arquivo real | `build_diagnostic_analysis` assumia `tox_limits.get("safe_upper_limits", [])` — arquivo real é `list` no topo com `sul.value` aninhado. Crasher garantido. |
| **[V10.4]** `assert` com expressão geradora inline em Python | `assert x for x in iterable` é `SyntaxError`. Usar `assert any(...)`, `assert all(...)`, ou `assert [cond for ...]`. |
| **[V10.4]** Declarar "RESOLVIDO"/"IMPLEMENTADO" sem evidência colada | Regra §9.4: `RESOLVIDO` = bloco `Evidência:` com comando + output literal. Sem isso, status = "PLANEJADO". |
| **[V10.4]** Assumir `nutrient_results` sempre tem exatamente 41 entradas | Variáveis compostas (`ca_p_ratio`, `caloric_density`, `cost_per_kg`) são penalizadas mas NÃO são nutrientes primários. Usar `>= 41` ou documentar exclusão. |
| **[Safety implementation]** Multiplicar coeficiente `por_1000kcal` diretamente por variável em gramas | Unidades incompatíveis. Compilar matriz, metas e SULs para uma única base diária antes de montar o LP. |
| **[Safety implementation]** Tratar pesos grandes como prova de prioridade lexicográfica | IU, mg, g e kcal têm escalas diferentes. Resolver SUL → DER → adequação em estágios, fixando cada ótimo. |
| **[Safety implementation]** Chamar toda inviabilidade de `unsafe_diagnostic` | Conflito hard e dado ausente exigem `structurally_infeasible` e `data_incomplete`; ambos com `allocations=null`. |

## 13. Priorities — V10

**P0 — Blocks diet viability:**
1. Obtain and fingerprint the real JSONs plus executable source; this workspace currently contains the plan, not those runtime artifacts.
2. Close unit/basis/provenance contract and compile LP quantities to a single daily basis before any solver work.
3. Define and test `structurally_infeasible` and `data_incomplete` output contracts with `allocations=null`.
4. Add `kelp_meal_dried`, `salt_nacl`, `copper_sulfate` only after source, concentration, unit, variability, and SUL impact are verified.
5. Update `lp_parameters_schema.json` with `NUTRIENT_REGISTRY`, unit/basis declarations, and declarative objective stages.

**P0 — Without this, solver is purely theoretical:**
6. Implement generic LP/MILP solver that reads declared stages and executes lexicographic SUL → DER → adequacy (§8).
7. Implement DER-derived dynamic envelope from selected-ingredient energy densities (§3.3).

**P1 — Important, doesn't block MVP:**
6. Resolve 17 orphan refs in `audit_provenance.json` (§9.2 — **PLANNED, NOT applied** — V10.4: confirmed 17 refs absent from file, referenced only in DB_ingredientes).
7. Extract real `cystine_g`/`tyrosine_g` from same USDA source (§9.3).
8. Finalize poultry validation (13+ pending issues).
9. Implement `--build-recipes` mode and generate `recipes_precomputed.json`.

**P2 — Natural extension:**
10. Create adult maintenance scenario (SCN_C) using existing `k=1.5`.
11. Implement additional recipe ranking criteria (simplicity, availability).

**P3 — Not critical now:**
12. Senior/geriatric phase — zero data today, no real immediate use requirement.
13. Formal schema for `DB_ingredientes.json` (currently orphan, validation by ad-hoc scripts).

---


## 15. Current Curation Status — V10

|Group|Ingredients|V9 status|V10 status|
|---|---|---|---|
|bovines|11|VALIDATED|VALIDATED|
|poultry|6|PARTIAL/PENDING|PARTIAL/PENDING (13+ issues)|
|pork|2|PARTIAL|PARTIAL|
|fish|1|PARTIAL|PARTIAL|
|**supplements**|**0 applied / 3 planned**|**Did not exist**|**PLANNED — kelp_meal_dried, salt_nacl, copper_sulfate; do not describe as DB entries until evidence is present**|

---


## 16. Gaps and Unimplemented Dependencies — V10

|#|Gap|V9 status|V10 status|Priority|
|---|---|---|---|---|
|1|Build Pipeline|No code exists|Specified in §6 (awaiting implementation)|P0|
|2|DB_ingredientes outside schema|Orphan by design|Orphan by design (script validation)|P3|
|3|Poultry normalization|13+ issues|13+ issues (unchanged)|P1|
|4|G8 false positive in validate_master.py|P2|P2 (unchanged)|P2|
|5|Senior/geriatric phase|Zero data|Zero data|P3|
|6|Adult scenario (SCN_C)|k=1.5 orphan|k=1.5 orphan, dynamic envelope already supports|P2|
|**7**|**Generic LP solver reading solve_cascade**|**Does not exist**|**Specified in §8 (awaiting implementation)**|**P0**|
|**8**|**DER-derived dynamic envelope**|**Fixed [200,1500]g**|**Specified in §3.3 (awaiting implementation)**|**P0**|
|**9**|**recipes_precomputed.json**|**Does not exist**|**Specified in §5.2 (awaiting build pipeline)**|**P1**|
|**10**|**Output data contract (schema)**|**Partial**|**Specified in §7 (awaiting implementation)**|**P0**|
|**11**|**Dimensional LP contract**|**Not explicit**|**Specified: compile all terms to daily basis; awaiting real implementation/tests**|**P0**|
|**12**|**Explicit infeasibility states**|**Blank/error risk**|**Specified: unsafe vs structural vs incomplete; awaiting implementation/tests**|**P0**|

---


## 17. Summary of V9 → V10 Changes

|#|Change|Section|Type|
|---|---|---|---|
|1|DER-derived dynamic envelope (replaces fixed `[200,1500]`)|3.3|Architectural|
|2|Total selection freedom (1 to N ingredients)|3.2|Product|
|3|"Free" category with alerts and recommendations|5.1|Product|
|4|"Precomputed Recipes" category|5.2|Product|
|5|3-level cascade (Preemptive Goal Programming)|3.4, 8|Architectural|
|6|`constraint_tier` in NUTRIENT_REGISTRY (safety_hard/adequacy_soft/envelope_soft)|4.2|Schema|
|7|Declarative `solve_cascade` in JSON (replaces hardcoded logic)|4.3|Schema|
|8|`clinical_criticality` per nutrient (for slack weighting)|4.2|Schema|
|9|Canonical data contract (solver_status, gaps, alerts, recommended_additions)|7|Schema|
|10|3 planned ingredients (kelp, salt, copper_sulfate) — NOT yet in real DB_ingredientes, see sat_dados_schema:§9.1|9.1|Data|
|11|85 refs in audit_provenance — no orphans (V10.4: confirmed against real file — 78 CONFIRMED, 4 INFERRED, 2 COPY_PASTE_ERROR_CORRECTED, 1 UNIT_INCONSISTENCY_RESOLVED)|9.2|Data|
|12|Proxy prohibition for cystine/tyrosine|9.3|Rule|
|13|Anti-gamification tests with AAA+A|11|QA|
|14|`recipes_precomputed.json` with 5+ criteria ranking|5.2|Product|
|15|Build pipeline in two modes (runtime + build-recipes)|6|Engineering|
|16|2 new reference prefixes (REF_LIT_VET_, REF_SAFETY_)|14.2|Convention|
|17|Output inviolability as canonical principle|3.1, 3.6|Principle|
|18|Model/data separation as inviolable rule|3.5, 0|Principle|
|**19**|**Level 3: `allocations=null` + `diagnostic_analysis` (mechanical barrier)**|**3.1, 3.4, 3.6, 7, 8.3, 11**|**V10.1 fix**|
|**20**|**Canonical `feeding_recommendation` (SAFE_TO_FEED / FEED_WITH_CAUTION / DO_NOT_FEED)**|**7, 14.4**|**V10.1 fix**|
|**21**|**Level-bifurcated contract (7.1 Level 1/2 vs. 7.2 Level 3)**|**7**|**V10.1 fix**|
|**22**|**`solve_cascade` JSON: Level 3 declares `output_contract` with allocations=null + diagnostic_analysis**|**4.3**|**V10.2 fix**|
|**23**|**§1: "SULs — never relaxed" → "hard in Levels 1-2; minimization in Level 3"**|**1**|**V10.2 fix**|
|**24**|**§3.4 table: Level 3 description includes `allocations=null`**|**3.4**|**V10.2 fix**|
|**25**|**Reference code: `build_diagnostic_analysis()` implemented (was reference without definition)**|**6.4**|**V10.2 fix**|
|**26**|**Reference code: `call_lp_solver()` returns `x_values`+`nutrient_values` (not `allocations`)**|**6.4**|**V10.2 fix**|
|**27**|**Reference code: `solve_cascade()` separates raw_result from output contract**|**6.4**|**V10.2 fix**|
|**28**|**Reference code: `format_allocations()` extracts allocations from raw_result (Level 1/2 only)**|**6.4**|**V10.2 fix**|
|**29**|**Reference code: `validate_output()` expanded with explicit null vs non-null allocations checks**|**6.4**|**V10.2 fix**|
|**30**|**§6.2 pseudocode: step 6 reflected allocations=null in Level 3 + raw_result separation**|**6.2**|**V10.2 fix**|
|**31**|**§6.2 validation (output): conditional allocations validation (null-safe)**|**6.2**|**V10.2 fix**|
|**32**|**§6.3 Build-Recipes: unsafe_diagnostic discard with explicit reason**|**6.3**|**V10.2 fix**|
|**33**|**§8.1: architectural note about x_i in Level 3 → only what_would_happen**|**8.1**|**V10.2 fix**|
|**34**|**§11.5: `audit_test_result()` fixed to handle allocations=None without crash**|**11.5**|**V10.2 fix**|
|**35**|**`λ_der` with explicit weight in Level 3 objective function (prevents degenerate x_i=0)**|**8.1**|**V10.2 fix**|
|**36**|**Mandatory weight hierarchy `μ_j >> λ_der >> σ_k` in Level 3 (implicit constraint, not configurable)**|**8.1, 8.2, 8.3**|**V10.2 fix**|
|**37**|**`solve_cascade` JSON: Level 3 declares `weight_calibration` with μ_j, λ_der, hierarchy_constraint**|**4.3**|**V10.2 fix**|
|**38**|**§8.3: degenerate solution risk without λ_der documented + generalization to any SUL**|**8.3**|**V10.2 fix**|
|**39**|**Level 3 contract (7.2): `solver_metadata.weight_calibration_used` for weight audit**|**7**|**V10.2 fix**|
|**40**|**Contract guarantee: weight hierarchy documented in `weight_calibration_used`**|**7**|**V10.2 fix**|
|**41**|**Code: `solve_cascade()` validates weight hierarchy and rejects if violated**|**6.4**|**V10.2 fix**|
|**42**|**Code: `validate_output()` checks `hierarchy_valid` and `μ_j > 10×λ_der`**|**6.4**|**V10.2 fix**|
|**43**|**Test: `test_level3_weight_hierarchy_validated`**|**11.2**|**V10.2 fix**|
|**44**|**Test: `test_level3_no_degenerate_solution`**|**11.2**|**V10.2 fix**|
|**45**|**Test: `test_level3_sul_violation_minimized_not_maximized`**|**11.2**|**V10.2 fix**|
|**46**|**Rejected: treat SUL as weighted goal without hierarchy + omit λ_der + configurable hierarchy**|**12**|**V10.2 fix**|
|**47**|**§8.2 golden rule #8: mandatory weight hierarchy in Level 3**|**8.2**|**V10.2 fix**|
|**48**|**Clinical floor minimum `x_i ≥ x_min_i` in Level 3 (prevents clinically irrelevant x_i like 0.5g liver)**|**8.1**|**V10.3 fix**|
|**49**|**`x_min_i` definition per category (muscle_meat=10g, organ=5g, supplement=0.1g) + global fallback 5g**|**8.1**|**V10.3 fix**|
|**50**|**Optional `clinical_floor_g` per ingredient in `formulation_rules.inclusion_constraints`**|**4.1, 8.1**|**V10.3 fix**|
|**51**|**Fallback if clinical floor infeasible: relax x_min_i → 0, mark `clinical_floor_relaxed=true`**|**8.1, 6.4**|**V10.3 fix**|
|**52**|**`solve_cascade` JSON: Level 3 declares `clinical_floor` with defaults_by_category + fallback_if_infeasible**|**4.3**|**V10.3 fix**|
|**53**|**§3.4 table: Level 3 description includes clinical floor minimum**|**3.4**|**V10.3 fix**|
|**54**|**Code: `build_lp_problem` injects `clinical_floor_bounds` in Level 3**|**6.4**|**V10.3 fix**|
| **55** | **Código: `solve_cascade()` tenta re-solver sem piso se infeasible com piso** | **6.4** |**V10.3 fix**|
|**56**|**Code: `build_diagnostic_analysis()` receives `clinical_floor_info`, produces `clinical_floor_applied/relaxed/ingredients_below_floor`**|**6.4**|**V10.3 fix**|
|**57**|**Level 3 contract (7.2): `what_would_happen` includes `clinical_floor_applied`, `clinical_floor_relaxed`, `ingredients_below_floor`, `x_min_i_effective`**|**7**|**V10.3 fix**|
|**58**|**Level 3 contract (7.2): `solver_metadata` includes `clinical_floor_applied` and `clinical_floor_bounds`**|**7**|**V10.3 fix**|
|**59**|**Contract guarantee: `clinical_floor_applied/bounds/relaxed` documentation for audit**|**7**|**V10.3 fix**|
|**60**|**§8.2 golden rule #9: mandatory clinical floor minimum in Level 3**|**8.2**|**V10.3 fix**|
|**61**|**§8.3: note about clinical floor in SUL vs DER collision case**|**8.3**|**V10.3 fix**|
|**62**|**Test: `test_level3_clinical_floor_prevents_irrelevant_xi`**|**11.2**|**V10.3 fix**|
|**63**|**Test: `test_level3_clinical_floor_relaxed_for_extreme_ingredient`**|**11.2**|**V10.3 fix**|
|**64**|**Test: `test_level3_clinical_floor_metadata_in_solver_output`**|**11.2**|**V10.3 fix**|
|**65**|**Code: `validate_output()` checks `clinical_floor_applied` + `clinical_floor_bounds` + `clinical_floor_relaxation_note`**|**6.4**|**V10.3 fix**|
|**66**|**Rejected: tolerate clinically irrelevant x_i + uniform clinical floor without category distinction**|**12**|**V10.3 fix**|
|**67**|**§14.4: `unsafe_diagnostic` description includes clinical floor**|**14.4**|**V10.3 fix**|
|**68**|**Version bumped: 10.2 → 10.3**|**0**|**V10.3 fix**|
|**69**|**Code: `assert` with inline generator fixed to `assert any(...)` (SyntaxError)**|**6.4**|**V10.4 fix**|
|**70**|**Code: `build_diagnostic_analysis()` — tox_limits iterated as direct list, SUL accessed via `sul.value` (real file shape)**|**6.4**|**V10.4 fix**|
|**71**|**§4.1 table: "23 items" → "20 items × 34 nutrients as_fed → 41 energy_normalized"; 3 ingredients marked as PLANNED**|**4.1**|**V10.4 fix**|
|**72**|**§4.1 table: "17 orphan refs resolved" → "17 orphan refs still pending" (confirmed against real file)**|**4.1**|**V10.4 fix**|
|**73**|**§4.1 table: `formulation_rules` — "3 new IDs" marked as planned, not applied**|**4.1**|**V10.4 fix**|
|**74**|**§4.1 table: `toxicological_limits` — documented as list at top with nested sul.value (not dict with safe_upper_limits)**|**4.1**|**V10.4 fix**|
|**75**|**§4.1 table: `objective_weights` — `PEN_MANGANESE_NEG` documented as only weight without solver_penalty_multiplier**|**4.1**|**V10.4 fix**|
|**76**|**Code: `validate_output()` — `len(nutrient_results) == 41` → `>= 41` (composites may be additional)**|**6.4**|**V10.4 fix**|
|**77**|**Contract guarantees (7): "exactly 41 entries" → "at least 41 entries" + note about composite variables**|**7**|**V10.4 fix**|
|**78**|**Test: `test_tox_limits_structure_matches_actual_file()` — validates toxicological_limits.json shape**|**11.3**|**V10.4 fix**|
|**79**|**Test: `test_objective_weights_all_have_penalty_multiplier_or_null()` — documents PEN_MANGANESE_NEG exception**|**11.3**|**V10.4 fix**|
|**80**|**§9.2: `test_all_non_usda_source_refs_resolve` description updated with real flags**|**11.3**|**V10.4 fix**|
|**81**|**Priority P0 #1: "resolved in V10" → "PLANNED, NOT applied"**|**13**|**V10.4 fix**|
|**82**|**Priority P1 #6: "Resolve 17 refs" → marked as PLANNED, NOT applied**|**13**|**V10.4 fix**|
|**83**|**Change summary #10: "3 ingredients added" → "3 planned, NOT yet in DB"**|**17**|**V10.4 fix**|
|**84**|**Change summary #11: "17 orphan refs resolved" → real flags documented**|**17**|**V10.4 fix**|
|**85**|**Rejected V10.4: pseudocode without shape check + inline assert + RESOLVED without evidence + nutrient_results == 41**|**12**|**V10.4 fix**|
|**86**|**Inviolable principle extended: pseudocode MUST be checkable against real files**|**0**|**V10.4 fix**|
|**87**|**Version bumped: 10.3 → 10.4**|**0**|**V10.4 fix**|
---

## ✅ Definition of Done — sat_operacional

Project operational state is traceable when:

- [ ] Every rejected idea (§12) has 1-line justification + version that rejected it.
- [ ] Roadmap (§13) has P0/P1/P2 with status (blocking/non-blocking) and explicit dependency.
- [ ] Curation status (§15) reflects REAL ingredient count (run `python3 -c "import json; print(len(json.load(open('DB_ingredientes.json'))['ingredients']))"` and paste output).
- [ ] Gaps (§16) list unimplemented dependencies with "PLANNED, NOT APPLIED" when applicable (never "RESOLVED" without evidence).
- [ ] Changelog (§17) has entry for each V10.x version with: date, item, affected section, change type.
- [ ] No entry says "RESOLVED"/"IMPLEMENTED" without `Evidence:` block with command + literal output (rule §9.4).

---
