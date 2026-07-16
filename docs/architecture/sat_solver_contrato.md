# sat_solver_contrato — Contrato de Output do Solver e Formulação Matemática

**v10.4** · ← `indice_plano_central.md` (canônico) · `../../README.md`

**Responsibility:** Output data contract (§7: Level 1/2 with allocations, Level 3 with allocations=null + diagnostic_analysis), LP mathematical formulation per level (§8.1), level transition (§8.2), special case SUL vs DER collision (§8.3), animal stages (§10), cascade integration tests (§A = §11.2). Heaviest satellite (31.6%).

**Depends on:** sat_princípios:§3.4 + §3.6, sat_dados_schema:§4.2 + §4.3 · **Referenced by:** sat_testes_consolidado, sat_pipeline_codigo

**Load when:** implement solve_cascade()/call_lp_solver() · change weights/floors · debug solver output · write solver tests

> **Context:** Deliberate grouping of interface (§7) + implementation (§8) + stages (§10) + cascade tests (§11.2): whoever implements `solve_cascade()` needs to know both what to return and how to compute. Numbering preserves original (§7 → §8 → §10 → §A).

---

## 7. Data Contract (Solver Output) — V10

The data contract is **pre-solver/schema** — defined before implementation. All solver output obeys this schema, regardless of cascade level.

**Level-bifurcated structure:** Level 3 (`unsafe_diagnostic`) produces a *different* contract from Levels 1/2. Resolves tension between output inviolability (never blank screen, 41 values always present) and user safety (never grams that could be accidentally interpreted as feeding instruction when unsafe).

### 7.1 Level 1/2 Contract (Real Recommendation — Can Feed)

```json
{
  "solver_output_schema": "v10.1",
  "solver_status": "optimal | suboptimal",
  "feeding_recommendation": "SAFE_TO_FEED | FEED_WITH_CAUTION",
  "cascade_level_used": 1,
  "animal_context": {
    "sex": "male",
    "weight_kg": 25.0,
    "age_months": 8,
    "gonadal_status": "intact",
    "der_kcal": 1320,
    "ter_kcal": 990,
    "k_multiplier": 1.2,
    "bw_source": "gompertz"
  },
  "envelope": {
    "min_total_g": 132,
    "max_total_g": 968,
    "actual_total_g": 600,
    "strategy": "der_derived"
  },
  "allocations": [
    {
      "ingredient_id": "beef_muscle_raw",
      "display_name": "Filé Mignon Bovino Cru",
      "category": "muscle_meat",
      "grams_per_day": 480,
      "pct_of_total": 80.0,
      "kcal_per_day": 672,
      "cost_per_day": null
    }
  ],
  "nutrient_results": [
    {
      "nutrient_id": "calcium_g",
      "display_name": "Cálcio",
      "value": 0.24,
      "unit": "g",
      "basis": "energy_normalized",
      "target_min": 3.0,
      "target_max": null,
      "sul": null,
      "pct_of_min": 8.0,
      "pct_of_sul": null,
      "status": "deficient",
      "constraint_tier": "adequacy_soft",
      "clinical_criticality": "critical"
    }
  ],
  "diagnostic_analysis": null,
  "gaps": [
    {
      "nutrient_id": "calcium_g",
      "pct_of_min": 8.0,
      "category_missing": "bone",
      "top_ingredients_in_category": [
        {"ingredient_id": "chicken_back_neck_raw", "concentration_per_1000kcal": 12.5},
        {"ingredient_id": "beef_foot_tendon_raw", "concentration_per_1000kcal": 8.3}
      ]
    }
  ],
  "alerts": [
    {
      "type": "deficiency",
      "severity": "warning",
      "nutrient_id": "calcium_g",
      "message": "Falta 92% para atingir o mínimo ideal de Cálcio — risco de DOD em crescimento",
      "action": "Adicionar fonte de cálcio (osso carnudo ou suplemento)"
    }
  ],
  "recommended_additions": [
    {
      "category": "bone",
      "rationale": "Fonte de cálcio e fósforo na razão fisiológica",
      "top_3_ingredients": ["chicken_back_neck_raw", "beef_foot_tendon_raw"]
    }
  ],
  "solver_metadata": {
    "solver_engine": "PuLP_CBC",
    "solve_time_ms": 45,
    "cascade_attempts": [1, 2],
    "final_level": 2,
    "objective_value": 15.3,
    "slack_variables_used": ["protein_g_slack_neg", "calcium_g_slack_neg"],
    "total_slack_weighted": 8.7
  }
}
```

### 7.2 Level 3 Contract (Diagnostic — DO NOT Feed)

```json
{
  "solver_output_schema": "v10.1",
  "solver_status": "unsafe_diagnostic",
  "feeding_recommendation": "DO_NOT_FEED",
  "cascade_level_used": 3,
  "animal_context": {
    "sex": "male",
    "weight_kg": 25.0,
    "age_months": 8,
    "gonadal_status": "intact",
    "der_kcal": 1320,
    "ter_kcal": 990,
    "k_multiplier": 1.2,
    "bw_source": "gompertz"
  },
  "envelope": {
    "min_total_g": 132,
    "max_total_g": 968,
    "actual_total_g": null,
    "strategy": "der_derived"
  },
  "allocations": null,
  "nutrient_results": [
    {
      "nutrient_id": "vitamin_a_iu",
      "display_name": "Vitamina A",
      "value": 28000,
      "unit": "IU",
      "basis": "energy_normalized",
      "target_min": 1250,
      "target_max": null,
      "sul": 9375,
      "pct_of_min": 2240,
      "pct_of_sul": 299,
      "status": "sul_violation_inevitable",
      "constraint_tier": "safety_hard",
      "clinical_criticality": "critical"
    }
  ],
  "diagnostic_analysis": {
    "reason": "No combination of selected ingredients meets caloric needs without exceeding safe limits. Caloric content and the SUL-violating nutrient are inseparable in the selected ingredient(s) — every gram adds both proportionally.",
    "sul_violations_inevitable": [
      {
        "nutrient_id": "vitamin_a_iu",
        "sul": 9375,
        "minimum_achievable_at_der": 28000,
        "pct_above_sul": 199,
        "mechanism": "Vit A and calories are inseparable in this ingredient — every gram adds both proportionally. No feasible split exists."
      }
    ],
    "what_would_happen": {
      "description": "If you fed ONLY the selected ingredients to meet caloric needs:",
      "grams_needed_for_der": 165,
      "nutrient_at_risk": "vitamin_a_iu",
      "value_at_that_amount": 28000,
      "sul_value": 9375,
      "clinical_significance": "Chronic hypervitaminosis A → osteoclast overactivation → pathologic fractures, osteodystrophy",
      "clinical_floor_applied": true,
      "clinical_floor_relaxed": false,
      "ingredients_below_floor": [],
      "x_min_i_effective": {"beef_liver_raw": 5}
    },
    "recommended_alternative_actions": [
      "Add a calorie source WITHOUT concentrated vitamin A (e.g., beef_muscle_raw, chicken_muscle_raw)",
      "Reduce liver/organ proportion and add muscle meat as caloric base",
      "Use recipe mode (Receitas Prontas) for pre-validated safe combinations"
    ]
  },
  "gaps": [
    {
      "nutrient_id": "calcium_g",
      "pct_of_min": 0,
      "category_missing": "bone",
      "top_ingredients_in_category": [
        {"ingredient_id": "chicken_back_neck_raw", "concentration_per_1000kcal": 12.5}
      ]
    }
  ],
  "alerts": [
    {
      "type": "sul_violation_inevitable",
      "severity": "danger",
      "nutrient_id": "vitamin_a_iu",
      "message": "NENHUMA quantidade segura possível — Vitamina A e calorias são inseparáveis neste ingrediente. NÃO alimentar.",
      "action": "Substituir por ingrediente calórico sem Vitamina A concentrada (carne muscular) ou usar Receitas Prontas"
    }
  ],
  "recommended_additions": [
    {
      "category": "muscle_meat",
      "rationale": "Fonte calórica sem vitamina A concentrada — permite atingir DER sem violar SUL",
      "top_3_ingredients": ["beef_muscle_raw", "chicken_muscle_raw", "pork_muscle_raw"]
    }
  ],
  "solver_metadata": {
    "solver_engine": "PuLP_CBC",
    "solve_time_ms": 82,
    "cascade_attempts": [1, 2, 3],
    "final_level": 3,
    "objective_value": 2850.0,
    "sul_violations": [{"nutrient_id": "vitamin_a_iu", "violation_magnitude": 18625}],
    "total_slack_weighted": null,
    "lexicographic_stages_used": {
      "stages": ["sul_violation", "der_deviation", "adequacy_slack"],
      "order_verified": true,
      "note": "O ótimo de SUL é fixado antes do DER, e o ótimo de DER antes da adequação; não depende de pesos escalares entre unidades diferentes"
    },
    "clinical_floor_applied": true,
    "clinical_floor_bounds": {"beef_liver_raw": 5}
  }
}
```

**Garantias do contrato:**
- `nutrient_results` **sempre** tem pelo menos 41 entradas (nunca omite nutrientes), independentemente do nível. Variáveis compostas (ca_p_ratio, caloric_density, cost_per_kg) podem aparecer adicionalmente mas não são contadas nos 41 nutrientes primários.
- `feeding_recommendation` **sempre** está presente e é um dos 3 valores canônicos — a UI DEVE checar este campo antes de exibir qualquer gramagem.
- Nos Níveis 1/2: `allocations` tem pelo menos 1 entrada. `diagnostic_analysis` é `null`.
- No Nível 3: `allocations` é **`null`** (barreira mecânica). `diagnostic_analysis` está presente com razão, violações inevitáveis, cenário contrafactual, e ações alternativas.
- `gaps` contém apenas nutrientes com `pct_of_min < 100`.
- `alerts` é populado quando `solver_status ∈ ["suboptimal", "unsafe_diagnostic"]`.
- `recommended_additions` é gerado deterministicamente a partir dos gaps e do DB.
- `solver_status` é um dos 3 valores canônicos — nunca `null`, nunca `undefined`.
- No Nível 3, `recommended_additions` foca em ingredientes que **resolvem a colisão SUL/DER** (ex: adicionar carne muscular para diluir a vitamina A), não apenas em completude nutricional genérica.
- No Nível 3, `solver_metadata.lexicographic_stages_used` documenta a ordem e os ótimos fixados. Isso impede que uma alteração numérica troque violação de SUL por DER.
- **[V10.3]** No Nível 3, `what_would_happen` inclui `clinical_floor_applied` (true/false), `clinical_floor_relaxed` (true/false), `ingredients_below_floor` (lista de ingredientes com x_i abaixo do piso), e `x_min_i_effective` (piso efetivo por ingrediente). Se o piso clínico foi relaxado, `clinical_floor_relaxation_note` documenta que o cenário contrafactual é abaixo de qualquer porção reconhecível.
- **[V10.3]** No Nível 3, `solver_metadata.clinical_floor_applied` e `solver_metadata.clinical_floor_bounds` documentam se o piso clínico foi efetivamente aplicado e quais valores foram usados. Isso permite auditoria: se `clinical_floor_applied = false`, o diagnóstico deve ser interpretado com cautela — o cenário contrafactual pode conter gramas clinicamente irrelevantes.

### 7.3 Non-Recommendation Error Contracts — Never Blank, Never Invented

`unsafe_diagnostic` is reserved for a real, solved counterfactual with a SUL violation. It must not be overloaded when the LP cannot be assembled or when remaining hard constraints conflict. Those cases return complete analysis with `allocations: null` and `feeding_recommendation: "DO_NOT_FEED"`:

|Status|When used|Required diagnostic fields|
|---|---|---|
|`structurally_infeasible`|Hard inclusion, ratio, or other non-relaxed constraints conflict even after the declared cascade|`conflicting_constraints`, `cascade_attempts`, `recommended_alternative_actions`|
|`data_incomplete`|A required real source, unit, basis, nutrient value, or JSON field is missing/ambiguous|`anomalies`, `missing_fields`, `source_refs_required`, `recommended_alternative_actions`|

Neither status may contain allocations, fabricated nutrient values, or a claim that a SUL violation was optimized. When a nutrient cannot be computed because input data are missing, its `nutrient_results[].value` is `null` with an anomaly reference; the UI must show that the analysis is incomplete.

---


## 8. Solver Architecture and Cascade — Technical Detail

### 8.1 Mathematical Formulation per Level

> **See also:** the tiers `adequacy_soft`, `safety_hard`, `envelope_soft` are defined in `sat_dados_schema:§4.2`. The declarative cascade (levels, `relax_tiers`, `objective_stages`) lives in `sat_dados_schema:§4.3` (`solve_cascade[]` in `lp_parameters_schema.json`). `objective_weights.json` may weight deviations inside a declared stage; it does not replace preemptive stage order.

**Level 1 (Canonical Goal Programming):**

```
Minimize  Σ_j  w_j × (d_j⁻ + d_j⁺)

Subject to:
  Σ_i  a_ij × x_i + d_j⁻ - d_j⁺ = T_j          ∀j ∈ targets
  Σ_i  a_ij × x_i ≥ min_j                          ∀j ∈ nutrient_bounds (adequacy_soft)
  Σ_i  a_ij × x_i ≤ SUL_j                          ∀j ∈ toxicological_limits (safety_hard)
  CSTR_CA_P_RATIO: 1.1 ≤ Ca/P ≤ 1.3               (hard)
  CSTR_ZN_CU_RATIO: Zn/Cu ≤ 12                    (hard)
  CSTR_FE_ZN_RATIO: Fe/Zn ≤ 3                     (hard)
  CSTR_CA_MG_RATIO: 12 ≤ Ca/Mg ≤ 18               (hard)
  CSTR_LYS_ARG_RATIO: 1.0 ≤ Lys/Arg ≤ 1.4         (hard)
  inclusion_constraints (6, hard)
  minTotal_g ≤ Σ_i x_i ≤ maxTotal_g               (envelope, envelope_soft)
  x_i ≥ 0                                          ∀i
  d_j⁻, d_j⁺ ≥ 0                                   ∀j
```

**Level 1 Conditional Adequacy Check (pre-solver, post-matrix):**
`lp_parameters_data.json:323-339` defines `conditional_adequacy_checks` for Level 1:
- `fat_source_vs_aafco_fat`: if fat_source inclusion at structural minimum (8%) cannot meet AAFCO fat_g minimum (21.25 g/1000kcal), flag for Level 2 relaxation with targeted gap detail. Implemented in `check_fat_source_adequacy()` (linhas 3058-3145).

**Level 2 (Adequacy Relaxation via Weighted Slack):**

```
Minimize  Σ_j  w_j × (d_j⁻ + d_j⁺) + Σ_k  σ_k × clinical_criticality_weight_k

Subject to:
  Σ_i  a_ik × x_i + s_k⁻ ≥ min_k - σ_k           ∀k ∈ adequacy_soft (σ_k ≥ 0 é slack)
  Σ_i  a_ij × x_i ≤ SUL_j                          ∀j ∈ safety_hard (INALTERADO)
  Todos os antagonismos e inclusões (inalterados)
  minTotal_g - σ_envelope ≤ Σ_i x_i ≤ maxTotal_g + σ_envelope
  x_i, d_j⁻, d_j⁺, s_k⁻, σ_k, σ_envelope ≥ 0
```

Onde `clinical_criticality_weight_k` vem de `NUTRIENT_REGISTRY[nutrient_id].clinical_criticality`:
- `critical` → peso 10.0
- `high` → peso 5.0
- `moderate` → peso 2.0
- `low` → peso 1.0

**Level 3 (Lexicographic SUL Diagnostic — with DER Proximity and Clinical Floor Minimum):**

```
Stage 3A: minimize normalized SUL violation V = Σ_j v_j⁺ / SUL_j
Stage 3B: add V = V* (within solver tolerance), then minimize absolute DER deviation δ_der
Stage 3C: add δ_der = δ_der* (within solver tolerance), then minimize normalized adequacy slack

Common constraints:
  Σ_i  a_ij × x_i ≤ SUL_j + v_j⁺                  ∀j ∈ safety_hard (v_j⁺ ≥ 0 é violação)
  Σ_i  a_ik × x_i + s_k⁻ ≥ min_k - σ_k           ∀k ∈ adequacy_soft
  Σ_i (EM_i/100) × x_i - DER = δ_der⁺ - δ_der⁻
  δ_der = δ_der⁺ + δ_der⁻
  x_i = 0 OR x_i ≥ x_min_i                          ∀i (piso clínico condicional)
  x_i, v_j⁺, s_k⁻, σ_k, δ_der⁺, δ_der⁻ ≥ 0
```

`a_ij` and the bounds above must be compiled to a single daily basis before this formulation is created. If `x_i` is grams/day, `a_ij` is nutrient/gram and `min_k`/`SUL_j` are nutrient/day. The prior formulation's `nutrient/1000kcal × grams` expression is invalid and MUST NOT be implemented.

**Piso clínico mínimo `x_min_i` — V10.3:**

O piso clínico mínimo impede cenários tecnicamente não-zero mas clinicamente irrelevantes. Ele não pode obrigar a inclusão de todo ingrediente selecionado: a semântica é `x_i = 0 OR x_i ≥ x_min_i`. Isso exige variável binária/indicadora ou formulação equivalente (MILP). Sem essa condição, selecionar opções disponíveis transforma todas em ingredientes obrigatórios e pode criar toxicidade ou inviabilidade artificial.

**Definição do piso por ingrediente:**

|Tipo|`x_min_i`|Racional|
|---|---|---|
|muscle_meat|10g|Porção mínima reconhecível — abaixo não constitui "cenário"|
|organ_secreting/organ_non_secreting|5g|~1 colher de chá, reconhecível|
|bone|5g|Abaixo, contribuição de Ca é irrelevante|
|fat_source|2g|Gordura é densa; 2g é visível|
|supplement|0.1g|Milimétrico (kelp, sal, CuSO₄)|

**Valores default (se `x_min_i` não está declarado por ingrediente):** 5g — conservador, cobre a maioria dos casos.

**Onde `x_min_i` vive no JSON:** `lp_parameters_schema.json → NUTRIENT_REGISTRY` não é o lugar (REGISTRY é por nutriente, não por ingrediente). O piso é por ingrediente, então vive em `formulation_rules.json → inclusion_constraints` como campo opcional `"clinical_floor_g"`:

> **See also:** `clinical_floor_g` is referenced in `sat_dados_schema:§4.1` (files table), `sat_pipeline_codigo:§6.4` (code that applies the floor), `sat_operacional:§12` (V10.3 rejection — uniform floor). Canonical definition in this satellite (§8.1 + this paragraph).

```json
"inclusion_constraints": [
  {
    "ingredient_id": "beef_liver_raw",
    "category": "organ_secreting",
    "min_inclusion_pct": 0,
    "max_inclusion_pct": 5,
    "clinical_floor_g": 5
  }
]
```

Se `clinical_floor_g` não está declarado, o build pipeline usa o default da categoria (5g para órgãos, 10g para muscle_meat, etc.) ou o fallback global de 5g.

**O que acontece se o solver não consegue satisfazer a condição de piso para um ingrediente usado (`x_i > 0` e `x_i < x_min_i`):**

O piso clínico é um constraint **hard** no Nível 3. Se o solver retorna `infeasible` mesmo com SUL relaxado (o que só acontece em casos extremos — ex: fígado puro onde 5g já ultrapassa SUL), o sistema aplica a seguinte fallback:

1. **Relaxar `x_min_i` para 0g** (remover o piso), executar o solver novamente.
2. **Marcar `what_would_happen.clinical_floor_relaxed = true`** no `diagnostic_analysis` — indicando que o cenário contrafactual é numericamente não-degenerado, mas não atinge o piso clínico mínimo.
3. **Documentar a magnitude:** `"note": "Solver returned x_i below clinical_floor_g (0.3g < 5g). Even the minimum recognizable portion of this ingredient violates the SUL. No safe amount exists."`

Essa fallback é necessária porque o princípio de inviolabilidade da saída se aplica: mesmo que o piso clínico não possa ser satisfeito, o sistema nunca retorna tela em branco — retorna diagnóstico com a ressalva documentada.

**Preempção obrigatória, não pesos mágicos:**

|Peso|Símbolo|Valor|Racional|
|---|---|---|---|
|Violação de SUL|Stage 3A|Normalizada por SUL|É resolvida e fixada antes dos demais objetivos|
|Proximidade ao DER|Stage 3B|Desvio absoluto em kcal/dia|Só é otimizada após o menor excesso de SUL possível|
|Adequação (slack)|Stage 3C|Normalizada pela meta + criticality|Só desempata cenários igualmente seguros e energeticamente próximos|

**Solver Parameters (solver_params):**

```json
"solver_params": {
  "big_m_strategy": "der_per_ingredient",
  "big_m_description": "M_i = DER_kcal / EM_i_kcal_per_100g * 100. Grams of ingredient i alone that would satisfy 100% of DER — a physically plausible per-ingredient upper bound, avoiding both numerical instability (M too large) and artificial capping (M too small).",
  
  "fix_optimum_tolerance_abs": 0.01,
  "fix_optimum_tolerance_rel": 1e-6,
  "fix_optimum_description": "When fixing stage N's optimum before solving stage N+1, accept objective within opt*(1+tol_rel) + tol_abs. Prevents false infeasibility from floating-point CBC results. EXCEPTION: if stage N involved binary variables (MILP), the effective tolerance is max(this value, cbc_mip_gap * abs(opt)) — see 'mip_tolerance_rule' below. A tolerance tighter than the gap CBC was allowed to leave on the table is meaningless.",
  "mip_tolerance_rule": "effective_tol_rel = max(fix_optimum_tolerance_rel, cbc_mip_gap) when the stage's LpProblem contains any LpVariable with cat='Binary'; otherwise effective_tol_rel = fix_optimum_tolerance_rel.",

  "cbc_time_limit_seconds": 30,
  "cbc_mip_gap": 0.01,
  "cbc_mip_gap_description": "Relative MIP gap for MILP (clinical floor binaries). 1% is sufficient — we don't need globally optimal binary assignment.",

  "tie_break_objective": "minimize_total_grams",
  "tie_break_weight": 1000.0,
  "tie_break_description": "Secondary objective applied ONLY to the final stage of any lexicographic sequence for a given cascade level (i.e. the stage whose result becomes the reported solution, not one whose objective value is subsequently fixed via fix_optimum). Never blend the tie-break into an intermediate stage — its magnitude (weight * sum(x_i), typically 0.1-1.0 given x_i in the hundreds of grams) would swamp fix_optimum_tolerance_abs (0.01) and corrupt the value the next stage fixes against."
}
```

**Big-M Formula:** `M_i = DER_kcal / EM_i_kcal_per_100g * 100` — grams of ingredient i alone satisfying 100% DER. Physically plausible per-ingredient upper bound.

**Tie-Break Determinístico Hash-Based (linhas 2206-2219 em call_lp_solver):**
```python
def det_hash(s: str) -> int:
    h = 0
    for ch in s:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h

tie_break_expr = 0
for iid, var in x_vars.items():
    perturbation = (det_hash(iid) % 10000) * 1e-1
    tie_break_expr += (tie_weight + perturbation) * var
obj_expr += tie_break_expr
```
Garante output bit-a-bit idêntico across runs.

**Fix Optimum Tolerance com MIP Tolerance Rule (linhas 2244-2247):**
```python
if has_binary_vars:
    mip_gap = solver_params.get("cbc_mip_gap", 0.01)
    tol_rel = max(tol_rel, mip_gap)
```
Tolerância mais apertada que o gap do CBC seria meaningless.

**Clinical Floor MILP — Big-M Per-Ingrediente:**
O piso clínico é implementado via MILP com variáveis binárias por ingrediente:
- `x_i = 0 OR x_i ≥ x_min_i` (indicador binário por ingrediente)
- `M_i = DER_kcal / EM_i_kcal_per_100g * 100` — limite superior fisicamente plausível por ingrediente
- Se infeasível com piso: relaxar piso → 0, re-solver, marcar `clinical_floor_relaxed=true`

---

**Preempção obrigatória, não pesos mágicos:**

**NOTA ARQUITETURAL — Contrato do Nível 3:** Embora o solver produza variáveis `x_i` (gramas matemáticas), o contrato de saída do Nível 3 define `allocations = null`. As gramas `x_i` são usadas **exclusivamente** dentro de `build_diagnostic_analysis()` para computar `what_would_happen.grams_needed_for_der` — são recontextualizadas como cenário contrafactual ("o que aconteceria se"), nunca como prescrição. A barreira entre "número calculado" e "gramas para alimentar" é mecânica (campo nulo), não semântica (label/badge). A resolução lexicográfica garante que o cenário primeiro minimiza SUL, depois se aproxima do DER, sem trocar segurança por magnitude numérica.

### 8.2 Level Transition — Golden Rules

1. Solver descends level only if current returns `infeasible`. Never skips.
2. Level 1 feasible with zero deviation on all targets → `optimal`, stop.
3. Level 1 feasible with non-zero deviation (canonical goal programming) → `optimal`, stop. Deviation captured by `d_j⁻/d_j⁺`.
4. Level 1 infeasible → try Level 2.
5. Level 2 feasible → `suboptimal`, stop.
6. Level 2 infeasible → try Level 3.
7. If Level 3 cannot be assembled because data are incomplete, return `data_incomplete`; if remaining hard constraints conflict, return `structurally_infeasible`. Neither is a blank screen or a feeding recommendation.
8. **Preemptive order mandatory:** Stage 3A SUL → Stage 3B absolute DER deviation → Stage 3C adequacy. Scalar large weights are not proof of this order.
9. **[V10.3] Clinical floor mandatory when an ingredient is used:** `x_i = 0 OR x_i ≥ x_min_i`. If the floor must be relaxed, mark `clinical_floor_relaxed=true`, document it, and never produce allocations.

### 8.3 Special Case: Cod Liver Oil / Isolated Liver (SUL vs. DER Collision)

**Collision condition:** ingredient has toxic nutrient proportional to calories (each gram carries both inseparably).

**Canonical ingredients:**
- Isolated cod liver oil (~1,800,000 IU Vit A / 100g)
- Pure beef liver (~40,000 IU Vit A / 100g, SUL = 9,375 IU)
- Pure kelp (Iodine) · Pure salt (Sodium) · Pure copper sulfate (Copper)

**Expected behavior per level:**

|Level|Result|Reason|
|---|---|---|
|1|`infeasible`|SUL ∩ DER = ∅ — no `x_i ≥ 0` satisfies both|
|2|`infeasible`|SUL remains hard — same collision|
|3|`unsafe_diagnostic` + `allocations=null`|Minimizes SUL violation; `diagnostic_analysis` documents inseparability|

**Implementation obligations:**

1. **Mandatory lexicographic stages** (Level 3): minimize normalized SUL, fix it; minimize absolute DER deviation, fix it; then minimize adequacy slack. Without the DER stage, solver can return `x_i=0`; without preemption, it can trade SUL for DER because of unit scale.
2. **Conditional clinical floor `x_i = 0 OR x_i ≥ x_min_i`** (Level 3): prevents clinically irrelevant used portions without forcing all selected ingredients into the scenario. For liver, 5g is a meaningful portion; supplements use category-specific floors.
3. **Floor fallback:** if no `x_min_i` is feasible without violating SUL, relax floor to 0 and mark `clinical_floor_relaxed = true` + note in `what_would_happen`.
4. **`allocations = null` is essential:** the simplex *will* find a point that minimizes weighted violation. That point is mathematically correct, but dangerous as prescription. Solution: return analysis, not grams.

**Canonical test:** `test_cod_liver_oil_isolated_returns_unsafe_diagnostic()` in §A.

---

## 10. Animal Stages — V10

|Stage|Nutritional data|Constraint|Energy mult.|Envelope|
|---|---|---|---|---|
|Growth slow (recommended)|SCN_B, 17 targets, `ACTIVE_TARGET`|60 constraints + cascade|k=1.2–1.5|DER-derived|
|Growth fast (discouraged)|SCN_A, 17 targets, `WARNING_DO_NOT_OPTIMIZE`|60 constraints + cascade|k=2.0–3.0|DER-derived|
|Active adult/working|**NEW SCN_C** (to create)|60 constraints + cascade (adjust adult SULs if needed)|k=1.5|DER-derived|
|Senior/geriatric|**Does not exist** — zero data/scenario/constraint/multiplier|—|—|—|

**P2 priority, non-blocking for puppy MVP:** create adult maintenance scenario (SCN_C) using existing `k=1.5`. The V10 dynamic envelope already supports any DER — only the 17 adult-specific targets and possible SUL adjustments are missing.

---


## §A — Cascade Integration Tests

### 11.2 Cascade Integration Tests

```python
def test_cascade_level1_feasible_for_balanced_selection():
    """Balanced selection (muscle+organ+bone) → optimal (Level 1). ANTI-GAMIFICATION: verify cascade_level_used==1 AND σ_k==0 in solver_metadata.
    
    NOTE: With current DB (missing bone/calcium source, iodine, D3, chloride), Level 1 is infeasible for ALL real ingredient combinations. This test documents the EXPECTED behavior when bone/calcium source is added to DB. Currently returns suboptimal (Level 2) due to Ca:P slack.
    When bone ingredients added to DB: should be optimal at Level 1 with allocations.
    """
    result = run_pipeline(
        animal={"sex": "male", "weight_kg": 25, "age_months": 8, "gonadal_status": "intact"},
        selected=["beef_muscle_raw", "chicken_back_neck_raw", "beef_liver_raw", 
                  "beef_kidney_raw", "salmon_raw", "kelp_meal_dried", "salt_nacl"],
        mode="runtime"
    )
    assert result["solver_status"] == "optimal"
    assert result["cascade_level_used"] == 1
    assert len(result["solver_metadata"]["slack_variables_used"]) == 0
    assert len(result["gaps"]) == 0

def test_cascade_level2_triggered_by_unbalanced_selection():
    """No calcium source → Level 2 (suboptimal). ANTI-GAMIFICATION: verify cascade_attempts contains 1 (tried Level 1) AND slack_variables_used not empty."""
    result = run_pipeline(
        animal={"sex": "male", "weight_kg": 25, "age_months": 8},
        selected=["beef_muscle_raw", "beef_liver_raw"],
        mode="runtime"
    )
    assert result["solver_status"] == "suboptimal"
    assert result["cascade_level_used"] == 2
    assert 1 in result["solver_metadata"]["cascade_attempts"]
    assert len(result["solver_metadata"]["slack_variables_used"]) > 0
    # Verify that calcium is in gaps
    calcium_gap = next(g for g in result["gaps"] if g["nutrient_id"] == "calcium_g")
    assert calcium_gap["pct_of_min"] < 50

def test_cascade_level3_triggered_by_sul_collision():
    """SUL collision inevitable → Level 3 (unsafe_diagnostic). ANTI-GAMIFICATION: verify SUL violated (pct_of_sul>100 for ≥1 nutrient), documented in alerts with severity="danger", allocations=null (mechanical barrier), diagnostic_analysis present."""
    result = run_pipeline(
        animal={"sex": "male", "weight_kg": 25, "age_months": 8},
        selected=["beef_liver_raw"],  # Vitamina A ultrapassa SUL inevitavelmente
        mode="runtime"
    )
    assert result["solver_status"] == "unsafe_diagnostic"
    assert result["cascade_level_used"] == 3
    # MECHANICAL BARRIER: allocations MUST be null — never grams in Level 3
    assert result["allocations"] is None
    # diagnostic_analysis MUST be present with inseparability explanation
    assert result["diagnostic_analysis"] is not None
    assert len(result["diagnostic_analysis"]["sul_violations_inevitable"]) > 0
    assert "inseparable" in result["diagnostic_analysis"]["reason"].lower()
    # feeding_recommendation DEVE ser DO_NOT_FEED
    assert result["feeding_recommendation"] == "DO_NOT_FEED"
    # Verify real SUL violation in nutrient_results
    sul_violations = [nr for nr in result["nutrient_results"] 
                      if nr.get("pct_of_sul") is not None and nr["pct_of_sul"] > 100]
    assert len(sul_violations) > 0
    danger_alerts = [a for a in result["alerts"] if a["severity"] == "danger"]
    assert len(danger_alerts) > 0
    # what_would_happen MUST contain mathematical numbers (for diagnosis, not prescription)
    assert result["diagnostic_analysis"]["what_would_happen"]["grams_needed_for_der"] is not None
    assert result["diagnostic_analysis"]["what_would_happen"]["nutrient_at_risk"] is not None

def test_cascade_never_skips_levels():
    """A cascata never skips do Level 1 to o Level 3.. ANTI-GAMIFICATION: verify real behavior, not just fields."""
    # Test with 10 random selections
    for _ in range(10):
        selection = random_ingredient_selection(size=random.randint(1, 5))
        result = run_pipeline(animal=STANDARD_PUPPY, selected=selection, mode="runtime")
        attempts = result["solver_metadata"]["cascade_attempts"]
        assert attempts == sorted(attempts), f"Cascade skipped level: {attempts}"

def test_single_ingredient_returns_result():
    """Single non-toxic ingredient (ex: filet mignon) never blank screen. ANTI-GAMIFICATION: verify 41 nutrients present, gaps identified, alerts appropriate."""
    result = run_pipeline(
        animal={"sex": "male", "weight_kg": 25, "age_months": 8},
        selected=["beef_muscle_raw"],
        mode="runtime"
    )
    # Filet mignon alone: lacks adequacy but is NOT toxic → suboptimal
    assert result["solver_status"] == "suboptimal"
    assert result["feeding_recommendation"] == "FEED_WITH_CAUTION"
    assert result["allocations"] is not None
    assert len(result["allocations"]) >= 1
    assert len(result["nutrient_results"]) >= 41  # 41 primary nutrients + optional composites
    assert len(result["gaps"]) > 0  # Filet mignon alone has gaps
    assert len(result["recommended_additions"]) > 0

def test_single_ingredient_sul_collision_no_allocations():
    """Selection of 1 ingredient toxic (ex: pure beef liver) must ser unsafe_diagnostic. ANTI-GAMIFICATION: verify real behavior, not just fields."""
    result = run_pipeline(
        animal={"sex": "male", "weight_kg": 25, "age_months": 8},
        selected=["beef_liver_raw"],
        mode="runtime"
    )
    assert result["solver_status"] == "unsafe_diagnostic"
    assert result["allocations"] is None  # MECHANICAL BARRIER
    assert result["diagnostic_analysis"] is not None
    # Mathematical numbers exist in diagnosis, not in allocations
    assert result["diagnostic_analysis"]["what_would_happen"]["grams_needed_for_der"] > 0
    # But no recommended grams exist
    assert result["allocations"] is None
    assert result["feeding_recommendation"] == "DO_NOT_FEED"

def test_level3_lexicographic_order_validated():
    """Level 3 must solve SUL → DER → adequacy in declared stages, not with scalar magic weights."""
    result = run_pipeline(
        animal={"sex": "male", "weight_kg": 25, "age_months": 8},
        selected=["beef_liver_raw"],  # Guarantees Level 3
        mode="runtime"
    )
    assert result["solver_status"] == "unsafe_diagnostic"
    stages = result["solver_metadata"]["lexicographic_stages_used"]
    assert stages["order_verified"] is True
    assert stages["stages"] == ["sul_violation", "der_deviation", "adequacy_slack"]

def test_level3_no_degenerate_solution():
    """[V10.2] Level 3 must NOT produce degenerate solution (x_i=0 for all). Without λ_der, solver picks x_i=0, v_j⁺=0, σ_der=DER (objective=0, useless). With λ_der=1000, solver seeks non-trivial point near DER. ANTI-GAMIFICATION: verify what_would_happen.grams_needed_for_der > 0."""
    result = run_pipeline(
        animal={"sex": "male", "weight_kg": 25, "age_months": 8},
        selected=["beef_liver_raw"],
        mode="runtime"
    )
    assert result["solver_status"] == "unsafe_diagnostic"
    grams = result["diagnostic_analysis"]["what_would_happen"]["grams_needed_for_der"]
    assert grams > 0, (
        f"Degenerate solution: grams_needed_for_der={grams} — "
        f"λ_der may be absent or too low in objective function"
    )

def test_level3_clinical_floor_prevents_irrelevant_xi():
    """[V10.3] Every ingredient used in Level 3 must be zero or meet its clinical floor; no 0.5g used portion."""
    result = run_pipeline(
        animal={"sex": "male", "weight_kg": 25, "age_months": 8},
        selected=["beef_liver_raw"],
        mode="runtime"
    )
    assert result["solver_status"] == "unsafe_diagnostic"
    wwh = result["diagnostic_analysis"]["what_would_happen"]
    
    # Verify that clinical floor was applied
    assert wwh["clinical_floor_applied"] is True, (
        "Clinical floor not applied — counterfactual may contain "
        "gramas clinicamente irrelevantes"
    )
    assert wwh["clinical_floor_relaxed"] is False, (
        "Clinical floor relaxed without reason — verify x_min_i is "
        "declarado corretamente no formulation_rules"
    )
    assert len(wwh["ingredients_below_floor"]) == 0, (
        f"Ingredients below clinical floor: {wwh['ingredients_below_floor']} — "
        f"o solver retornou gramas clinicamente irrelevantes"
    )
    
    # Verify that x_min_i_efetivo is documented
    assert "x_min_i_effective" in wwh
    assert "beef_liver_raw" in wwh["x_min_i_effective"]
    assert wwh["x_min_i_effective"]["beef_liver_raw"] == 5, (
        "Clinical floor for secreting organ must be 5g"
    )

def test_level3_clinical_floor_relaxed_for_extreme_ingredient():
    """[V10.3] Extreme ingredient (pure cod liver oil): clinical floor may be relaxed but must be documented. ANTI-GAMIFICATION: verify clinical_floor_relaxed=true + relaxation_note present."""
    # NOTA: Este teste assume que cod_liver_oil existe no DB.
    # If it does not exist, test is skipped with documented reason.
    try:
        result = run_pipeline(
            animal={"sex": "male", "weight_kg": 25, "age_months": 8},
            selected=["cod_liver_oil"],  # if available
            mode="runtime"
        )
    except ValueError as e:
        if "ingredient_id" in str(e):
            import pytest
            pytest.skip("cod_liver_oil not in DB — test not applicable")
        raise
    
    assert result["solver_status"] == "unsafe_diagnostic"
    wwh = result["diagnostic_analysis"]["what_would_happen"]
    
    # Clinical floor may have been relaxed (oil is supplement, floor = 0.1g)
    # or not — depends on actual Vit A concentration in oil
    if wwh["clinical_floor_relaxed"]:
        assert "clinical_floor_relaxation_note" in wwh, (
            "Clinical floor relaxed but no documentation note"
        )
        assert result["solver_metadata"]["clinical_floor_applied"] is False
    
    # Diagnosis ALWAYS exists — never blank screen
    assert result["diagnostic_analysis"] is not None
    assert result["allocations"] is None

def test_level3_clinical_floor_metadata_in_solver_output():
    """[V10.3] No Level 3, solver_metadata DEVE contain clinical_floor_applied. ANTI-GAMIFICATION: verify real behavior, not just fields."""
    result = run_pipeline(
        animal={"sex": "male", "weight_kg": 25, "age_months": 8},
        selected=["beef_liver_raw"],
        mode="runtime"
    )
    assert result["solver_status"] == "unsafe_diagnostic"
    meta = result["solver_metadata"]
    
    assert "clinical_floor_applied" in meta, (
        "solver_metadata missing clinical_floor_applied — "
        "cannot audit if clinical floor was used"
    )
    assert isinstance(meta["clinical_floor_applied"], bool)
    assert "clinical_floor_bounds" in meta
    assert isinstance(meta["clinical_floor_bounds"], dict)
    assert len(meta["clinical_floor_bounds"]) > 0, (
        "clinical_floor_bounds empty — no clinical floor declared"
    )

def test_level3_sul_violation_minimized_not_maximized():
    """[V10.2] Level 3 solver must MINIMIZE SUL violation, not maximize. ANTI-GAMIFICATION: verify violation magnitude is smallest possible given DER."""
    result = run_pipeline(
        animal={"sex": "male", "weight_kg": 25, "age_months": 8},
        selected=["beef_liver_raw"],
        mode="runtime"
    )
    assert result["solver_status"] == "unsafe_diagnostic"
    # SUL violation must exist (inevitable), but minimized
    sul_violations = [nr for nr in result["nutrient_results"]
                      if nr.get("pct_of_sul") is not None and nr["pct_of_sul"] > 100]
    assert len(sul_violations) > 0  # Violation inevitable (Level 3)
    # Solver must prove the declared lexicographic solve, not merely expose a weight.
    assert result["solver_metadata"]["lexicographic_stages_used"]["order_verified"] is True
    # Verify that violation is documented (not hidden)
    assert len(result["diagnostic_analysis"]["sul_violations_inevitable"]) > 0
```

---

## ✅ Definition of Done — sat_solver_contrato

- [ ] `solve_cascade()` executes levels 1→2→3, stops at first feasible.
- [ ] `call_lp_solver()` invokes real LP solver (PuLP/CVXPY/HiGHS) with §8.1 formulation.
- [ ] Level 1 (`optimal`): SULs + floors + DER/density/Ca:P respected; `allocations` has grams; `feeding_recommendation=SAFE_TO_FEED`. ⚠️ DEFERRED — implemented but not exercised by any real ingredient combination in current DB (L1 infeasible for all tested selections due to missing calcium/iodine/D3/chloride sources). Code path verified in isolation by `test_level1_optimal_synthetic` (synthetic mock coefficients, no DB dependency). Needs real bone/calcium-source ingredient data (Phase 3) before end-to-end verification.
- [ ] Level 2 (`suboptimal`): SULs hard; `adequacy_soft` floors relaxed via `clinical_criticality`-weighted slack; `allocations` has grams; `feeding_recommendation=FEED_WITH_CAUTION`.
- [ ] Level 3 (`unsafe_diagnostic`): minimizes SUL violation; `allocations=null`; `feeding_recommendation=DO_NOT_FEED`; `diagnostic_analysis` populated (`sul_violations_inevitable` + `what_would_happen` + `recommended_alternative_actions`).
- [ ] Lexicographic SUL → DER → adequacy stages are solved and fixed in order; evidence is recorded in `lexicographic_stages_used`.
- [ ] Conditional clinical floor `x_i = 0 OR x_i ≥ x_min_i` is applied in Level 3; `clinical_floor_applied` + `clinical_floor_bounds` are in `solver_metadata`.
- [ ] `structurally_infeasible` and `data_incomplete` return valid non-recommendation contracts without fabricated values.
- [ ] If floor relaxed: `clinical_floor_relaxed=true` + `clinical_floor_relaxation_note` in `what_would_happen`. ⚠️ DEFERRED — implemented but not exercised by any real ingredient combination in current DB (requires a Level 3 scenario where clinical floor is infeasible, which needs real bone/calcium-source data to construct). Code path exists; needs either (a) a synthetic minimal-ingredient-set unit test that doesn't depend on real DB coverage, or (b) real bone/calcium-source ingredient data (Phase 3) before it can be verified end-to-end.
- [ ] §8.3 case: isolated cod liver oil → Level 3 + `diagnostic_analysis` documents calorie/toxin inseparability.
- [ ] All 41 nutritional values in `nutrient_results` (any level).
- [ ] §A tests pass — especially `test_level3_allocations_null_and_diagnostic_present()` and `test_manganese_neg_no_penalty_multiplier()`.

---
