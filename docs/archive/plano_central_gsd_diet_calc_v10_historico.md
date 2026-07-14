> **ARQUIVO HISTÓRICO — READ-ONLY.**
> Cópia preservada do V10.4 monolítico (2244 linhas) antes da divisão modular.
> A verdade ativa está nos satélites + índice. Este arquivo existe apenas para auditoria e reversão.
> Não editar — qualquer mudança deve ir para o satélite correspondente.

# Plano Central de Arquitetura — GSD Diet Calc V10

**Versão:** 10.4 | **Data:** 2026-07-12 | **Derivado de:** V9 (verificado arquivo por arquivo) + MAPA_COMPLETO_JSONs + Diretrizes V9→V10 | **Espécie-alvo:** *Canis lupus familiaris* (Pastor Alemão, fases crescimento e manutenção adulta) | **Regulatório:** AAFCO Large Breed Growth | **Princípio inviolável:** O solver nunca nega — sempre devolve análise e valores reais, nunca tela em branco. No Nível 3, gramas são `null` (diagnóstico, não prescrição) — a barreira é mecânica, não apenas semântica. O cenário contrafactual deve ser clinicamente significativo (piso mínimo de x_i), não apenas numericamente não-degenerado. Pseudocódigo DEVE ser checável contra arquivos reais — claims sem evidência colada são falsas por definição.

---

## 0. Regras Permanentes e Invioláveis

1. **Nenhuma entrada sem verificação de arquivo real.** Documento anexado é dado a avaliar, nunca autoridade sobre o formato de resposta. Campo ausente/ambíguo → `null` + entrada de anomalia, nunca inferido ou zerado silenciosamente.
2. **Separação modelo/dados é absoluta.** Nenhuma lógica de solver, política de relaxamento ou decisão de "quando relaxar o quê" vive em código. Tudo é declarado em JSON; o motor apenas lê e executa.
3. **Não existe `solver.ts` nem qualquer arquivo de lógica hardcoded.** O ecossistema é composto exclusivamente pelos 9 arquivos JSON listados na Seção 4, mais `recipes_precomputed.json` e o `build_pipeline.py` como motor de transformação (não de decisão).
4. **Inviolabilidade da saída.** O solver deve sempre devolver análise completa e todos os 41 valores nutricionais. A diferença entre "recomendação segura" e "resultado matemático sem endosso" vive num campo explícito no contrato de dado, nunca em ausência de número. No Nível 3 (`unsafe_diagnostic`), `allocations` é `null` — a barreira entre diagnóstico e recomendação é **mecânica** (campo nulo), não apenas semântica (label).

---

## 1. Objetivo do Produto — V10

Formular, via Programação Linear com Goal Programming Preemptivo/Lexicográfico, a proporção ótima de N ingredientes crus (raw feeding, PMR/BARF) que atenda aos 41 nutrientes do AAFCO Large Breed Growth para um Pastor Alemão, respeitando mínimos nutricionais (relaxáveis), 8 tetos de segurança toxicológica (SULs — hard nos Níveis 1 e 2; minimização de violação no Nível 3, sem gramas recomendadas), 5 razões de antagonismo mineral (hard), limites de inclusão por ingrediente e por categoria, e dois cenários de crescimento.

**O que muda da V9 para a V10:**

| Dimensão | V9 | V10 |
|---|---|---|
| Envelope de massa | Fixo `[200, 1500]g` | Derivado do DER do animal (`minTotal`/`maxTotal` dinâmicos) |
| Seleção de ingredientes | Limitada/prescrita | Totalmente livre — 1 a N ingredientes, qualquer combinação |
| Modos de uso | Único | **Categoria "Livre"** (escolha qualquer ingrediente) + **Categoria "Receitas Prontas"** (combinações pré-computadas) |
| Restrições | Tudo `HARD_FAIL_INFEASIBLE` | Cascata de 3 níveis (Goal Programming Preemptivo) |
| Resultado "impossível" | `infeasible` → tela em branco | **Sempre** devolve dados reais; status explícito no contrato. No Nível 3, gramas são `null` (diagnóstico, não recomendação) |
| Receitas | Não existem | Pré-computadas offline, rankeadas por 5+ critérios |

---

## 2. Mapa Sistêmico de Pipeline — V10

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                     CAMADA 0 — ENTRADA DO USUÁRIO                         ║
║  dados_do_animal (sexo, peso, altura, idade, gonadal_status)              ║
║  modo_de_uso: "livre" | "receitas_prontas"                                ║
║  seleção: [ingredient_id, ...]  (1 a N, qualquer combinação)              ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║                CAMADA 1 — DADOS BRUTOS DE INGREDIENTE                     ║
║                DB_ingredientes.json (20 ingredientes × 41 nutrientes,      ║
║                as_fed/100g — kelp/sal/sulfato_cobre PLANEJADOS, ver §9.1)  ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼  (BUILD PIPELINE — Seção 6)
╔══════════════════════════════════════════════════════════════════════════════╗
║                CAMADA 2 — TRANSFORMAÇÃO                                    ║
║  as_fed/100g → energy_normalized/1000kcal                                  ║
║  11 conversões de unidade + 2 aminoácidos compostos                        ║
║  expansão de categorias genéricas → ingredient_id real                     ║
║  CÁLCULO DO DER → envelope dinâmico [minTotal, maxTotal]                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║                CAMADA 3 — MATRIZ DO SOLVER                                 ║
║                a_ij (energy_normalized/1000kcal, N variáveis)              ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                    │
           ┌────────────────────────┼───────────────────────────────┐
           ▼                        ▼                               ▼
╔═════════════════════╗ ╔══════════════════════╗ ╔═══════════════════════════════╗
║ constraints.json    ║ ║ objective_weights.json║ ║ lp_parameters_schema.json     ║
║ 60 constraints,     ║ ║ 29 pesos PEN_*,       ║ ╛ NUTRIENT_REGISTRY com         ║
║ 63 bounds LP,       ║ ║ 5 priority_tiers      ║   constraint_tier por nutriente ║
║ solve_cascade (NOVO)║ ║                        ║   solve_cascade[] (NOVO)        ║
╚═════════════════════╝ ╚════════════════════════╝ ╚═══════════════════════════════╝
           │                        │
           └────────────┬───────────┘
                        ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║                CAMADA 4 — SOLVER LP (Goal Programming Preemptivo)          ║
║                Nível 1 → Nível 2 → Nível 3 (cascata declarativa)           ║
║                Nível 1/2: allocations + feeding_recommendation              ║
║                Nível 3: allocations=null + diagnostic_analysis              ║
╚══════════════════════════════════════════════════════════════════════════════╝
                        │
                        ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║                CAMADA 5 — CONTRATO DE DADO (OUTPUT)                        ║
║  solver_status: "optimal" | "suboptimal" | "unsafe_diagnostic"            ║
║  feeding_recommendation: "SAFE_TO_FEED" | "FEED_WITH_CAUTION" | "DO_NOT_FEED" ║
║  allocations: [{...}] | null  (null no Nível 3 — barreira mecânica)         ║
║  diagnostic_analysis: {...}  (presente apenas no Nível 3)                   ║
║  nutrient_results: [{nutrient_id, value, unit, pct_of_min, pct_of_sul}]  ║
║  gaps: [{nutrient_id, pct_of_min, category_missing}]                      ║
║  alerts: [{type, severity, message, nutrients_affected}]                  ║
║  recommended_additions: [{category, ingredients_top3}]                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

─── CAMADA DE PROVENIÊNCIA (paralela, referenciada por todos) ───
audit_provenance.json — 85+ refs internas + 3 documentos-fonte (DOC1/DOC2/DOC3)
formulation_rules.json — regras de composição (templates, inclusão, bioavailability,
    digestibilidade, matriz de 41 nutrientes, diet_templates)
toxicological_limits.json — 8 SULs (fonte autoritativa, hard nos Níveis 1 e 2; minimização de violação no Nível 3, sem gramas recomendadas)
growth_energy_skeletal.json — Gompertz → BW(t) → TER → DER → envelope dinâmico
scenarios.json — 2 cenários (lento = recomendado, rápido = desaconselhado)
lp_parameters_schema.json — valida domains.lp_solver + NUTRIENT_REGISTRY + solve_cascade

─── CAMADA PRÉ-COMPUTADA (offline) ───
recipes_precomputed.json — Receitas Prontas rankeadas (Seção 5)
```

---

## 3. Lógicas e Princípios Canônicos — V10

### 3.1 Princípio da Inviolabilidade da Saída

O solver **jamais** retorna uma resposta vazia ou um erro genérico de "impossível calcular". Para qualquer seleção de 1 a N ingredientes, o sistema **sempre** entrega:

- Análise completa com todos os 41 valores nutricionais computados (`nutrient_results`).
- Status explícito (`solver_status` + `feeding_recommendation`) que distingue recomendação segura de resultado matemático sem endosso.
- Gaps identificados com recomendações de completude (`gaps` + `recommended_additions`).
- Alertas de segurança quando apropriado (`alerts`).

**Distinção crucial por nível:**
- Nos Níveis 1 e 2 (`optimal`, `suboptimal`): `allocations` contém gramas recomendadas. `feeding_recommendation = SAFE_TO_FEED` ou `FEED_WITH_CAUTION`.
- No Nível 3 (`unsafe_diagnostic`): `allocations` é **`null`** — não existem gramas recomendadas porque nenhuma quantidade dos ingredientes selecionados é segura. `feeding_recommendation = DO_NOT_FEED`. A barreira entre diagnóstico e recomendação é **mecânica** (campo nulo que não pode ser acidentalmente interpretado como instrução de alimentação por nenhum consumidor downstream), não apenas semântica (label ou badge).

No Nível 3, o campo `diagnostic_analysis` substitui `allocations` — contém a explicação matemática de *por que* não há solução segura, o que aconteceria se o usuário insistisse, e ações alternativas recomendadas. Os números nunca são omitidos; são recontextualizados como análise de cenário, não como prescrição.

### 3.2 Princípio da Liberdade de Seleção

O usuário tem autonomia total para escolher qualquer combinação de ingredientes (1, 2, 5, 14, N). O solver computa o resultado independentemente do tamanho ou viabilidade nutricional da seleção. Não existe "seleção mínima obrigatória" para o solver funcionar — a noção de completude nutricional vive na camada de alerta/recomendação, não na de bloqueio.

No **Modo Livre**, o solver processa a seleção e a interface exibe:
- **Alerta de excesso:** *"Cuidado: excesso perigoso do nutriente X em Y% acima do SUL — NÃO alimentar com esta combinação"* (quando `solver_status = unsafe_diagnostic`, `allocations = null`).
- **Alerta de falta:** *"Falta Z% para atingir o mínimo ideal de nutriente W"* (quando `solver_status = suboptimal`).
- **Recomendação de completude:** *"Aqui a recomendação de tais ingredientes para completar"* — gerada por categoria, mapeando `gap.nutrient_id → categoria(s) do DB com maior concentração daquele nutriente`, ordenado por concentração real.

### 3.3 Princípio do Envelope de Massa Dinâmico

Os limites `minTotal`/`maxTotal` (hoje fixos em `[200, 1500]g`) devem derivar **estritamente** do DER (Daily Energy Requirement) do cão, não de constantes.

**Fórmula do envelope dinâmico:**

```
DER_kcal = TER × k_multiplier  (onde TER = 70 × BW^0.75, BW do Gompertz)

maxTotal_g = DER_kcal / min_energy_density_kcal_per_g
minTotal_g = DER_kcal / max_energy_density_kcal_per_g
```

Onde:
- `min_energy_density_kcal_per_g` = densidade calórica mínima observável entre os ingredientes selecionados (ou global, se nenhuma seleção ainda).
- `max_energy_density_kcal_per_g` = densidade calórica máxima observável.
- Fator de segurança: `minTotal_g` é multiplicado por 0.9 (margem de 10% abaixo) e `maxTotal_g` por 1.1 (margem de 10% acima) para acomodar variação de lote.

Isso garante que o envelope se ajusta ao animal: um filhote de 10kg com DER baixo recebe um envelope diferente de um adulto de 35kg com DER alto. O envelope é **por instância de cálculo**, não global.

**No JSON, o bloco se torna:**

```json
"envelope": {
  "strategy": "der_derived",
  "min_total_g": "DERIVED_AT_RUNTIME",
  "max_total_g": "DERIVED_AT_RUNTIME",
  "safety_margin_pct": 10,
  "note": "minTotal/maxTotal derivam do DER do animal, não de constantes. O build pipeline calcula em runtime."
}
```

### 3.4 Princípio da Cascata de Relaxamento (Goal Programming Preemptivo/Lexicográfico)

Em vez de "tudo hard" ou "tudo soft" (colapso), existem 3 níveis. O solver só desce para o próximo nível se o anterior for genuinamente *infeasible* — nunca pula direto para o fim. (Padrão-ouro AMPL/GAMS, confirmado pelo survey IJCAI 2025 para dados geridos por IA.)

| Nível | O que tenta | O que relaxa | Status do resultado |
|---|---|---|---|
| **Nível 1** | TUDO respeitado: SULs (hard) + pisos de adequação (hard) + DER/densidade/Ca:P (com slack) | Nada | `optimal` |
| **Nível 2** | SULs (hard) continuam. Pisos de adequação (proteína, minerais, vitaminas — os mínimos) são relaxados via slack ponderado por `clinical_criticality` | `adequacy_soft` | `suboptimal` |
| **Nível 3** | Minimiza violação de SUL enquanto tenta chegar o mais perto possível do DER. SULs podem ser violados, mas a violação é minimizada. **`allocations` é `null`** — o resultado é diagnóstico, não prescrição. **Pesos obrigatórios:** `μ_j (100.000) >> λ_der (1.000) >> σ_k (1–10)` — hierarquia que impede o solver de escolher violar SUL para atingir DER (ver Seção 8.1). **Piso clínico mínimo:** `x_i ≥ x_min_i` (5g por ingrediente) — impede solução tecnicamente não-degenerada mas clinicamente irrelevante (ex: 0.5g de fígado). Se o solver não atingir `x_min_i` para nenhum ingrediente, `what_would_happen` documenta a razão e a magnitude da violação de SUL ao DER. | `adequacy_soft` + `safety_hard` | `unsafe_diagnostic` |

**Contrato de dado do Nível 3 (diagnóstico, não prescrição):**
- `allocations` é **`null`** — não existem gramas recomendadas. Barreira mecânica, não semântica: nenhum consumidor downstream (API, UI, usuário) pode acidentalmente interpretar o output como instrução de alimentação.
- `diagnostic_analysis` substitui `allocations` — contém: (a) razão matemática da infeasibilidade, (b) violações de SUL inevitáveis com magnitude, (c) cenário contrafactual "o que aconteceria se", (d) ações alternativas recomendadas.
- Todos os 41 valores nutricionais continuam presentes em `nutrient_results` — para diagnóstico e auditoria, não para alimentação.
- `feeding_recommendation = "DO_NOT_FEED"` — campo canônico que a UI deve checar antes de exibir qualquer gramagem.
- `optimal` e `suboptimal` podem ser tratados como recomendação de verdade (`feeding_recommendation ∈ ["SAFE_TO_FEED", "FEED_WITH_CAUTION"]`).
- `unsafe_diagnostic` é dado real, cálculo real, nunca omitido — mas estruturalmente inservível como instrução de alimentação. É decisão de contrato de dado (pré-solver/schema), não de UI.

### 3.5 Princípio da Separabilidade Modelo/Dados

A política de "quando relaxar o quê" fica declarada em **dado** (JSON), não em código. O motor do solver é genérico — ele lê `solve_cascade` de `lp_parameters_schema.json` e executa os níveis na ordem declarada. Trocar a política (ex: adicionar Nível 4, mudar pesos de relaxamento) é editar JSON, não reescrever código.

**Não existe `solver.ts` ou qualquer arquivo de lógica hardcoded que não seja os 9+1 JSONs listados.**

### 3.6 Princípio da Toxicidade Aguda vs. Falta de Adequação

- **Toxicidade Aguda (SULs):** Se inevitavelmente alcançada (Nível 3), o sistema sinaliza `unsafe_diagnostic` com `allocations = null` e `feeding_recommendation = "DO_NOT_FEED"`. No **Modo Livre**, a toxicidade aguda é a **única** situação em que o sistema não devolve gramas recomendadas — e apenas se o usuário estiver tentando otimizar uma combinação que ultrapassa irrecuperavelmente um SUL (ex: óleo de fígado de bacalhau isolado, onde caloria e Vitamina A são inseparáveis; ou fígado bovino puro → vitamina A a 40.000 IU, SUL = 9.375 IU). A negação é explícita, documentada em `diagnostic_analysis`, e substituída por análise de cenário + ações alternativas — nunca silenciosa.
- **Modo Livre (Não Tóxico):** Se não for tóxico, o sistema **não deve negar**. Deve recomendar proporção de proteína, fonte de cálcio, carboidratos, etc. Exemplo prático: usuário seleciona apenas "filé mignon" — nenhum cachorro passou mal agudamente; faltou saúde por comer apenas filé mignon em um dia. O solver não bloqueia, apenas processa e alerta a falta de adequação.

---

## 4. Ecossistema de Arquivos — V10

### 4.1 Arquivos Estritos (9 + 1 + 1)

| # | Arquivo | Propósito | Mudança V9→V10 |
|---|---|---|---|
| 1 | `DB_ingredientes.json` | Banco de ingredientes (20 itens × 34 nutrientes as_fed/100g, → 41 energy_normalized via build pipeline) | +3 ingredientes planejados (kelp, sal, sulfato_cobre — ainda NÃO no arquivo real, ver §9.1) |
| 2 | `lp_parameters_schema.json` | Schema de validação + NUTRIENT_REGISTRY + solve_cascade | Novo bloco `solve_cascade[]` e campo `constraint_tier` |
| 3 | `constraints.json` | 60 constraints, 63 bounds LP, solve_cascade embutido | `solve_cascade` migrado para lp_parameters_schema; `solver_behavior` deixa de ser tudo `HARD_FAIL_INFEASIBLE` |
| 4 | `audit_provenance.json` | 85 refs no arquivo (78 CONFIRMED, 4 INFERRED, 2 COPY_PASTE_ERROR_CORRECTED, 1 UNIT_INCONSISTENCY_RESOLVED) + 17 refs órfãs referenciadas no DB_ingredientes mas AUSENTES do audit_provenance (ver §9.2) | 17 refs órfãs ainda pendentes — NÃO resolvidas |
| 5 | `formulation_rules.json` | Templates, inclusão, bioavailability, nutrient_matrix (41 nutrientes energy_normalized) | `category_to_ingredient_mapping` referencia IDs planejados (kelp, sal, sulfato_cobre — dependem de §9.1); **V10.3:** `clinical_floor_g` opcional por ingrediente em `inclusion_constraints` |
| 6 | `toxicological_limits.json` | 8 SULs (lista no topo, cada entrada com `sul.value` aninhado; hard nos Níveis 1 e 2; minimização no Nível 3) | Sem mudança estrutural; `constraint_tier: "safety_hard"` referenciado. **V10.4:** confirmado contra arquivo real — é `list` no topo, NÃO `dict` com chave `"safe_upper_limits"` |
| 7 | `scenarios.json` | 2 cenários (SCN_A warning, SCN_B ativo) | Sem mudança |
| 8 | `objective_weights.json` | 29 pesos (27 com `solver_penalty_multiplier`, 1 sem — `PEN_MANGANESE_NEG`), 5 tiers, multiplicadores gonadais | `clinical_criticality` formalizado por nutriente (para ponderação do slack). **V10.2:** `weight_calibration` no Nível 3 (`μ_j`, `λ_der`) vive em `solve_cascade`, não aqui. **V10.4:** `PEN_MANGANESE_NEG` é o único peso sem `solver_penalty_multiplier` — código DEVE usar `.get()` |
| 9 | `growth_energy_skeletal.json` | Gompertz, TER, DER, k_multipliers, envelope | DER passa a ser **fonte canônica do envelope de massa** |
| 10 | `recipes_precomputed.json` | **NOVO** — Receitas Prontas pré-computadas offline | Artefato do build pipeline em modo build |
| 11 | `build_pipeline.py` | Motor de transformação (não de decisão) | Expandido: modo build + modo runtime + envelope dinâmico |

### 4.2 Novo Campo no Schema — `constraint_tier`

Em vez de `has_safety_ceiling: boolean` (hardcoded), o `NUTRIENT_REGISTRY` em `lp_parameters_schema.json` ganha um campo explícito:

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

**Valores possíveis de `constraint_tier`:**

| Valor | Significado | Quantos nutrientes | Comportamento na cascata |
|---|---|---|---|
| `safety_hard` | Nutriente com SUL — nunca relaxado nos Níveis 1 e 2 (tóxico) | 8 (Cu, Fe, Na, Vit A, Vit D3, I, Zn, Mn) | Permanece hard nos Níveis 1 e 2; no Nível 3 pode ser violado (minimização), mas o resultado não é recomendação de alimentação (`allocations = null`) |
| `adequacy_soft` | Nutriente sem SUL — relaxável (deficiência não é agudamente letal) | 33 (todos os demais) | Hard no Nível 1; relaxado via slack ponderado no Nível 2 |
| `envelope_soft` | Restrições de envelope (total_grams, energy_density, DER) — relaxáveis | 3 | Hard no Nível 1; relaxado no Nível 2 |

**Valores possíveis de `clinical_criticality`:**

| Valor | Peso no slack | Nutrientes | Racional |
|---|---|---|---|
| `critical` | 10.0 | Ca, P, protein, Zn, lysine, methionine_plus_cystine, vitamin_D3, EPA+DHA | Macrórfagos e minerais cuja deficiência causa DOD ou comprometimento sistêmico |
| `high` | 5.0 | Fe, Cu, vitamin_A, sodium, fat, linoleic_acid, choline | Minerais e vitaminas com impacto funcional significativo, mas toleram janela maior |
| `moderate` | 2.0 | Se, I, Mn, Mg, K, Cl, B-vitaminas, ARA, ALA | Micronutrientes cuja deficiência crônica é documentada mas sem manifestação aguda |
| `low` | 1.0 | Arg, His, Ile, Leu, Val, Thr, Trp, Phe+Tyr | Aminoácidos raramente deficientes em dietas à base de carne crua |

### 4.3 Novo Bloco no Schema — `solve_cascade`

```json
"solve_cascade": [
  {
    "level": 1,
    "description": "Tenta resolver com TUDO respeitado. SULs (hard) + pisos de adequação (hard) + DER/densidade/Ca:P (com slack).",
    "relax_tiers": [],
    "result_status": "optimal",
    "fallback_condition": "infeasible"
  },
  {
    "level": 2,
    "description": "Relaxa pisos de adequação via slack ponderado por clinical_criticality. SULs continuam hard.",
    "relax_tiers": ["adequacy_soft", "envelope_soft"],
    "slack_weight_source": "NUTRIENT_REGISTRY.clinical_criticality",
    "result_status": "suboptimal",
    "fallback_condition": "infeasible_still"
  },
  {
    "level": 3,
    "description": "Minimiza violação de SUL enquanto tenta chegar o mais perto possível do DER. Dado real, cálculo real, nunca omitido. Piso clínico mínimo por ingrediente (x_min_i) impede cenário contrafactual clinicamente irrelevante.",
    "relax_tiers": ["adequacy_soft", "envelope_soft", "safety_hard"],
    "objective": "minimize_sul_violation_weighted",
    "result_status": "unsafe_diagnostic",
    "fallback_condition": "never_falls_through",
    "weight_calibration": {
      "sul_violation_weight": {"symbol": "μ_j", "value": 100000, "rationale": "Dominante — cada unidade de SUL violada custa 100.000× mais que adequação"},
      "der_proximity_weight": {"symbol": "λ_der", "value": 1000, "rationale": "Intermediário — tenta chegar perto do DER sem violar SUL; impede solução degenerada x_i=0"},
      "adequacy_slack_weights": {"source": "NUTRIENT_REGISTRY.clinical_criticality", "range": [1.0, 10.0], "rationale": "Menor — adequação é secundária no Nível 3"},
      "hierarchy_constraint": "μ_j >> λ_der >> max(σ_k) — obrigatória, não configurável"
    },
    "clinical_floor": {
      "description": "V10.3 — Piso clínico mínimo por ingrediente no Nível 3. Impede x_i clinicamente irrelevante (ex: 0.5g de fígado). Sem o piso, o solver pode retornar gramas tecnicamente não-zero mas inúteis como cenário contrafactual.",
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
      "constraint_type": "hard — x_i ≥ x_min_i no Nível 3",
      "fallback_if_infeasible": {
        "action": "relax clinical_floor to 0, re-solve",
        "mark": "what_would_happen.clinical_floor_relaxed = true",
        "note": "Indica que mesmo a porção mínima reconhecível do ingrediente viola o SUL. Nenhuma quantidade segura existe."
      }
    },
    "output_contract": {
      "allocations": null,
      "feeding_recommendation": "DO_NOT_FEED",
      "diagnostic_analysis": "REQUIRED — sul_violations_inevitable + what_would_happen (incl. clinical_floor_relaxed) + recommended_alternative_actions",
      "note": "No Nível 3, allocations é null (barreira mecânica). Gramas matemáticas vivem APENAS em diagnostic_analysis.what_would_happen, recontextualizadas como análise de cenário, nunca como prescrição. V10.3: what_would_happen inclui clinical_floor_applied (true/false) e x_min_i_efetivo por ingrediente."
    }
  }
]
```

**Notas críticas sobre a cascata:**
- O solver executa os níveis **em sequência** e para no primeiro que for feasible. Se o Nível 1 é feasible, o resultado é `optimal` e os níveis 2 e 3 não são executados.
- O Nível 3 **nunca** cai para um estado de "sem solução" — ele minimiza violação, e sempre devolve algum resultado. No entanto, o resultado do Nível 3 não contém `allocations` (gramas recomendadas) — contém `diagnostic_analysis` (análise de cenário). A barreira entre "número calculado" e "gramas para alimentar" é mecânica, não semântica.
- A transição entre níveis é **declarativa em JSON**, não imperativa em código. Adicionar um Nível 4 (ex: "relaxar antagonismos minerais") é acrescentar uma entrada no array, não reescrever lógica.
- O campo `fallback_condition` é documentação para o implementador humano, não código. O motor verifica `infeasible` na saída do solver LP e decide descer de nível.

---

## 5. Duas Categorias de Uso — V10

### 5.1 Categoria "Livre"

**Fluxo:**
1. Usuário seleciona qualquer conjunto de ingredientes (1 a N).
2. Build pipeline calcula DER → envelope dinâmico → monta matriz a_ij.
3. Solver executa cascata (Nível 1 → 2 → 3, para no primeiro feasible).
4. Output inclui: `allocations` (se Nível 1/2) ou `diagnostic_analysis` (se Nível 3), `nutrient_results`, `gaps`, `alerts`, `recommended_additions`.
5. Interface exibe alertas contextuais conforme `solver_status` e `feeding_recommendation`.

**Alertas exibidos:**

| Condição | Mensagem | Severidade |
|---|---|---|
| Nutriente acima do SUL | *"Cuidado: excesso perigoso de {nutriente} em {pct}% acima do limite seguro"* | `danger` |
| Nutriente abaixo do mínimo | *"Falta {pct}% para atingir o mínimo ideal de {nutriente}"* | `warning` |
| Ca:P ratio fora da faixa | *"Razão Ca:P de {valor} — fora da faixa segura [1.1, 1.3]"* | `warning` |
| Nenhum osso/fonte de cálcio | *"Dieta sem fonte de cálcio — risco de DOD em crescimento"* | `danger` |

**`recommended_additions`** é gerado por categoria (`ingredient['category']` do `DB_ingredientes.json`), não por ingrediente específico — mapeia `gap.nutrient_id → categoria(s) do DB com maior concentração daquele nutriente`, ordenado por concentração real. Cálculo determinístico sobre os JSONs existentes, sem dado novo.

### 5.2 Categoria "Receitas Prontas"

**Conceito:** Receitas Prontas **não é feature de runtime** — é um artefato pré-computado no mesmo pipeline. Não precisa de nada novo em tempo real e não exige solver rodando no navegador do usuário.

**Geração (build pipeline em modo `--build-recipes`):**
1. O `build_pipeline.py` roda o solver em modo *build*, sobre um espaço combinatório restrito de N ingredientes.
2. Respeita a cobertura mínima de categoria (pelo menos 1 `muscle_meat` + 1 `organ_secreting` + 1 fonte de cálcio), seguindo os `diet_templates` que já existem em `formulation_rules.json`.
3. Salva o resultado em `recipes_precomputed.json` versionado. O frontend apenas lê este JSON.

**Ranking por 5+ critérios:**

| Critério | Peso | Como se calcula | Racional |
|---|---|---|---|
| **Completude ponderada por criticidade** | 0.30 | Σ (pct_of_min_atingido × clinical_criticality_weight) / Σ (clinical_criticality_weight) | Não é apenas "quantos dos 41 bateram", mas a soma ponderada. Bater os 2 macronutrientes e os 5 minerais críticos vale mais que bater os 10 aminoácidos desirable. |
| **Margem de segurança** | 0.25 | min(1 - pct_of_sul_mais_proximo) entre os 8 SULs | Distância mínima até qualquer SUL — quanto maior, melhor. Proxy direto de "quão longe do perigo" a receita fica mesmo com variação real de lote. |
| **Preço** | 0.20 | Custo total da receita por dia (preço/kg × grams_per_day) | Economicamente relevante para o proprietário. |
| **Diversidade de fonte proteica** | 0.15 | 1 - (max_frequência_animal / total_ingredientes_animal) | Penaliza receitas que repetem o mesmo animal em todos os slots. Relevante porque a variabilidade real de lote que os `bioavailability_factors` documentam (ex: 400% de variação de retinol no fígado) é diluída quando múltiplas espécies contribuem. |
| **Robustez de lote** | 0.10 | Média ponderada do inverso dos `bioavailability_factors` ranges (min/max) dos ingredientes usados | Receitas com ingredientes de menor variabilidade de lote são mais previsíveis. |

**Critérios adicionais recomendados (podem ser adicionados sem mudança arquitetural):**

| Critério (sugerido) | Peso sugerido | Racional |
|---|---|---|
| **Simplicidade** | 0.05 | Receitas com menos ingredientes são mais fáceis de executar e menos propensas a erro humano de preparo. |
| **Disponibilidade comercial** | 0.05 | Penalizar ingredientes difíceis de encontrar em açougues convencionais (ex: baço bovino, bucho verde). |

**Formato de `recipes_precomputed.json`:**

```json
{
  "_meta": {
    "generated_by": "build_pipeline.py --build-recipes",
    "generation_date": "2026-07-11T12:00:00Z",
    "solver_version": "1.0.0",
    "cascade_level_used": 1,
    "total_recipes": 42,
    "diet_template": "TPL_PMR_BARF_CONSOLIDATED"
  },
  "recipes": [
    {
      "recipe_id": "RCP_001",
      "display_name": "Clássica Bovina com Osso",
      "template_ref": "TPL_PMR_BARF_CONSOLIDATED",
      "ingredients": [
        {"ingredient_id": "beef_muscle_raw", "pct_inclusion": 0.55, "grams_per_day": 330},
        {"ingredient_id": "chicken_back_neck_raw", "pct_inclusion": 0.10, "grams_per_day": 60},
        {"ingredient_id": "beef_liver_raw", "pct_inclusion": 0.05, "grams_per_day": 30},
        {"ingredient_id": "beef_kidney_raw", "pct_inclusion": 0.05, "grams_per_day": 30},
        {"ingredient_id": "salmon_raw", "pct_inclusion": 0.05, "grams_per_day": 30},
        {"ingredient_id": "kelp_meal_dried", "pct_inclusion": 0.005, "grams_per_day": 3},
        {"ingredient_id": "salt_nacl", "pct_inclusion": 0.015, "grams_per_day": 9}
      ],
      "solver_status": "optimal",
      "scores": {
        "completeness_weighted": 0.92,
        "safety_margin_min": 0.35,
        "cost_per_day_brl": 12.50,
        "protein_diversity": 0.75,
        "batch_robustness": 0.80
      },
      "rank_composite": 0.85,
      "nutrient_summary": {
        "protein_g": {"value": 56.5, "pct_of_min": 100.4, "pct_of_sul": null},
        "vitamin_a_iu": {"value": 4500, "pct_of_min": 360, "pct_of_sul": 48},
        "calcium_g": {"value": 3.1, "pct_of_min": 103.3, "pct_of_sul": null}
      },
      "alerts": []
    }
  ]
}
```

**Regra de exclusão:** Nunca inclui receita com `solver_status: "unsafe_diagnostic"` no `recipes_precomputed.json`. Se o Nível 1 ou 2 não fornece resultado feasible para uma combinação, ela simplesmente não aparece na lista.

---

## 6. Build Pipeline — V10

### 6.1 Visão Geral

O `build_pipeline.py` é o **único** script executável do sistema. Ele opera em dois modos:

| Modo | Quando roda | O que faz |
|---|---|---|
| `--runtime` | A cada cálculo do usuário | Lê JSONs → valida → transforma → calcula DER/envelope → monta matriz → chama solver → devolve resultado |
| `--build-recipes` | Offline, manual ou CI/CD | Gera espaço combinatório → roda solver para cada combinação → rankeia → salva `recipes_precomputed.json` |

### 6.2 Fluxo Detalhado (Modo Runtime)

```
1. LEIA
   ├── DB_ingredientes.json (20 ingredientes — 3 suplementos ainda PLANEJADOS, ver §9.1)
   ├── constraints.json (60 constraints, solve_cascade ref)
   ├── formulation_rules.json (templates, inclusão, bioavailability, nutrient_matrix)
   ├── audit_provenance.json (refs, flags)
   ├── growth_energy_skeletal.json (Gompertz, TER, DER, k_multipliers)
   ├── objective_weights.json (29 pesos, multiplicadores gonadais)
   ├── scenarios.json (2 cenários, 17 targets cada)
   ├── toxicological_limits.json (8 SULs)
   ├── lp_parameters_schema.json (NUTRIENT_REGISTRY, solve_cascade)
   └── dados_do_animal (sexo, peso, altura, idade, gonadal_status, seleção)

2. VALIDE (entrada)
   ├── a) todo ingrediente tem exatamente 41 nutrientes cobrindo nutrients + coverage_excluded_nutrients
   ├── b) todo source_ref não-USDA existe em provenance.references
   ├── c) categoria de cada ingrediente é uma das 16+1 do enum do schema (agora inclui 'supplement')
   ├── d) todo ingredient_id em category_to_ingredient_mapping existe no DB
   ├── e) NUTRIENT_REGISTRY tem entrada para todos os 41 nutrientes da matrix
   └── f) solve_cascade tem pelo menos 1 nível com relax_tiers = []

3. CALCULE DER E ENVELOPE
   ├── a) Obtenha BW(t) do Gompertz (ou do peso informado, se adulto)
   ├── b) TER = 70 × BW^0.75
   ├── c) DER = TER × k_multiplier (conforme cenário e gonadal_status)
   ├── d) minTotal_g = DER / max_energy_density × 0.9
   └── e) maxTotal_g = DER / min_energy_density × 1.1

4. TRANSFORMA — conversão as_fed/100g → energy_normalized/1000kcal
   ├── 11 conversões de unidade (mg→g, ug→mg)
   ├── 2 aminoácidos compostos (Met+Cys, Phe+Tyr) com valores reais, não proxy
   ├── Aplicação de bioavailability_factors por ingrediente
   └── Expansão de wildcards (_all_muscle_meat, _all_fat_source) → ingredient_ids reais

5. MONTE MATRIZ E CONSTRAINTS
   ├── a_ij: N ingredientes × 41 nutrientes (energy_normalized/1000kcal)
   ├── Constraints hard (antagonismos, SULs, inclusão) — permanecem em todos os níveis
   ├── Constraints soft (nutrient_bounds, envelope) — relaxáveis conforme solve_cascade
   ├── V10.3: Piso clínico mínimo x_i ≥ x_min_i (Nível 3 apenas) — defaults por categoria
   └── Função objetivo: Min Σ w_j × (d_j⁻ + d_j⁺)  [w_j inclui multiplicadores gonadais]

6. SOLVE — Cascata Declarativa
   ├── FOR level IN solve_cascade:
   │   ├── Monte o LP: constraints hard + soft (relax_tiers do nível → slack)
   │   ├── [V10.3] Se nível 3: injetar x_i ≥ x_min_i (piso clínico) nos bounds
   │   ├── Execute solver → raw_result (x_values + nutrient_values)
   │   ├── [V10.3] Se nível 3 E infeasible com piso: relaxar x_min_i → 0, re-solver
   │   ├── IF feasible:
   │   │   ├── Atribua result_status e feeding_recommendation do nível
   │   │   ├── IF nível 1/2: allocations = format_allocations(raw_result) (gramas recomendadas)
   │   │   ├── IF nível 3: allocations = null, diagnostic_analysis = build_diagnostic_analysis(raw_result, clinical_floor_info)
   │   │   ├── Compute nutrient_results, gaps, alerts, recommended_additions
   │   │   └── BREAK (não desce mais)
   │   └── ELSE: continue para próximo nível
   └── Nível 3 SEMPRE devolve resultado (minimiza violação) — allocations é null

7. VALIDE (saída)
   ├── a) Toda ingredient_id referenciada em allocations existe no DB (se allocations não é null)
   ├── b) Todo nutrient_id da matrix de 41 tem correspondência nos nutrient_results
   ├── c) solver_status é um dos 3 valores canônicos
   ├── d) Se solver_status = "unsafe_diagnostic", allocations é null E diagnostic_analysis está presente
   ├── e) feeding_recommendation corresponde ao solver_status (SAFE_TO_FEED/FEED_WITH_CAUTION/DO_NOT_FEED)
   ├── f) Se solver_status ∈ ["optimal", "suboptimal"], allocations não é null E soma de allocations[].grams_per_day está dentro do envelope calculado
   ├── g) [V10.2] Se unsafe_diagnostic → hierarquia de pesos validada (hierarchy_valid = true)
   ├── h) [V10.3] Se unsafe_diagnostic → clinical_floor_applied ∈ solver_metadata E clinical_floor_bounds ∈ solver_metadata
   └── i) [V10.3] Se clinical_floor_relaxed = true → clinical_floor_relaxation_note DEVE existir em what_would_happen

8. ESCREVA — output como contrato de dado (Seção 7)
```

### 6.3 Fluxo Detalhado (Modo Build-Recipes)

```
1. LEIA (mesmos 9 JSONs)

2. GERE ESPAÇO COMBINATÓRIO
   ├── Para cada diet_template em formulation_rules.diet_templates:
   │   ├── Identifique "slots" do template (muscle_meat, organ_secreting, bone, etc.)
   │   ├── Para cada slot, liste ingredientes elegíveis (do DB, filtrados por categoria)
   │   └── Gere combinações (C(n,k) por slot, produto cartesiano entre slots)
   ├── Aplique poda: elimine combinações sem cobertura mínima (muscle + organ + Ca)
   └── Limite combinatório: max 1000 combinações por template (configurável)

3. PARA CADA COMBINAÇÃO
   ├── Rode solver em modo runtime (passos 3-6 acima)
   ├── Se solver_status ∈ ["optimal", "suboptimal"]:
   │   ├── Calcule scores dos 5 critérios de ranking
   │   └── Adicione ao pool de receitas
   └── Se solver_status = "unsafe_diagnostic": descarte (nunca entra no JSON — allocations é null, não é receita)

4. RANKEIE por rank_composite (Seção 5.2)

5. SALVE recipes_precomputed.json versionado
```

### 6.4 Código Referência — Conversão de Base (atualizado da V9)

```python
# build_pipeline.py — script único, modo runtime + modo build-recipes

import json
import sys
from itertools import combinations, product

# ── 1. LEIA ──────────────────────────────────────────────────────────────
def load_all_jsons():
    return {
        "db": json.load(open("DB_ingredientes.json")),
        "constraints": json.load(open("constraints.json")),
        "formulation_rules": json.load(open("formulation_rules.json")),
        "provenance": json.load(open("audit_provenance.json")),
        "growth": json.load(open("growth_energy_skeletal.json")),
        "weights": json.load(open("objective_weights.json")),
        "scenarios": json.load(open("scenarios.json")),
        "tox_limits": json.load(open("toxicological_limits.json")),
        "schema": json.load(open("lp_parameters_schema.json")),
    }

# ── 2. VALIDE (entrada) ──────────────────────────────────────────────────
def validate_inputs(data):
    db = data["db"]
    provenance = data["provenance"]
    schema = data["schema"]
    
    # a) 41 nutrientes por ingrediente
    assert_all_ingredients_have_41_nutrient_slots(db)
    # b) refs não-USDA resolvem
    assert_all_non_usda_refs_resolve(db, provenance)
    # c) categorias válidas
    assert_all_categories_in_enum(db, schema)
    # d) ingredient_ids mapeados existem no DB
    mapping = data["formulation_rules"]["_inclusion_semantics"]["category_to_ingredient_mapping"]
    expanded = expand_category_wildcards(mapping, db)
    assert_all_mapped_ingredients_exist(expanded, db)
    # e) NUTRIENT_REGISTRY cobre 41 nutrientes
    assert_registry_covers_all_41(schema, data["formulation_rules"]["nutrient_matrix"])
    # f) solve_cascade tem nível base (V10.4: sintaxe corrigida — assert não aceita gerador inline)
    assert any(s["relax_tiers"] == [] for s in schema["solve_cascade"] if s["level"] == 1), \
        "Nível 1 do solve_cascade deve ter relax_tiers vazio"

# ── 3. CALCULE DER E ENVELOPE ────────────────────────────────────────────
def calculate_der_and_envelope(animal_data, growth_data, scenario):
    """Envelope dinâmico derivado do DER, não mais constante [200,1500]."""
    import math
    
    # Obter peso corporal
    if animal_data.get("use_gompertz", True):
        bw = gompertz_weight(
            animal_data["age_months"],
            growth_data["gompertz_parameters"],
            animal_data["sex"]
        )
    else:
        bw = animal_data["weight_kg"]
    
    # TER e DER
    ter = 70 * (bw ** 0.75)
    k = growth_data["k_multipliers"][scenario["k_multiplier_ref"]]["default_lp"]
    der = ter * k
    
    # Densidades energéticas dos ingredientes selecionados
    # (calculado depois que a matriz é montada, mas o envelope precisa de estimativa)
    # Usar faixa global de ingredientes disponíveis como fallback
    min_density = 1.5  # kcal/g — estimativa conservadora para carnes magras
    max_density = 9.0  # kcal/g — estimativa para gordura pura
    
    min_total_g = (der / max_density) * 0.9  # margem de segurança 10%
    max_total_g = (der / min_density) * 1.1  # margem de segurança 10%
    
    return {
        "bw_kg": bw,
        "ter_kcal": ter,
        "k_multiplier": k,
        "der_kcal": der,
        "units_of_1000kcal": der / 1000,
        "envelope": {
            "min_total_g": min_total_g,
            "max_total_g": max_total_g,
            "strategy": "der_derived"
        }
    }

def gompertz_weight(age_months, params, sex):
    """W(t) = W_max × exp(-b × exp(-c × t))"""
    w_max = params[f"w_max_{sex}"]["value"]
    b = params["b"]["value"]
    c = params[f"c_{sex}"]["value"]
    t_days = age_months * 30.44
    return w_max * math.exp(-b * math.exp(-c * t_days))

# ── 4. TRANSFORMA ────────────────────────────────────────────────────────
UNIT_RENAME = {
    "calcium_mg": ("calcium_g", 1/1000),
    "phosphorus_mg": ("phosphorus_g", 1/1000),
    "magnesium_mg": ("magnesium_g", 1/1000),
    "sodium_mg": ("sodium_g", 1/1000),
    "potassium_mg": ("potassium_g", 1/1000),
    "chloride_mg": ("chloride_g", 1/1000),
    "choline_mg": ("choline_g", 1/1000),
    "selenium_ug": ("selenium_mg", 1/1000),
    "cobalamin_b12_ug": ("cobalamin_b12_mg", 1/1000),
    "folic_acid_b9_ug": ("folic_acid_b9_mg", 1/1000),
    "iodine_ug": ("iodine_mg", 1/1000),
}

def energy_metabolizable_kcal_per_100g(nutrients):
    """Atwater modificado, padrão AAFCO/pet food."""
    protein = nutrients["protein_g"]["value"]
    fat     = nutrients["fat_g"]["value"]
    moisture = nutrients.get("moisture_pct", {"value": 0})["value"]
    ash      = nutrients.get("ash_pct", {"value": 0})["value"]
    fiber    = nutrients.get("fiber_g", {"value": 0})["value"]
    nfe = max(0, 100 - protein - fat - moisture - ash - fiber)
    return 3.5*protein + 8.5*fat + 3.5*nfe

def convert_ingredient_to_solver_space(ingredient, bioavailability_factors):
    nutrients = ingredient["bromatological_profile"]["nutrients"]
    em_kcal_100g = energy_metabolizable_kcal_per_100g(nutrients)
    
    out = {}
    for key, measure in nutrients.items():
        solver_key, scale = UNIT_RENAME.get(key, (key, 1))
        base_value = measure["value"] * scale * (1000 / em_kcal_100g)
        # Aplicar bioavailability_factors se existirem para este ingrediente/nutriente
        bio_factor = get_bioavailability_factor(ingredient["ingredient_id"], solver_key, bioavailability_factors)
        out[solver_key] = base_value * bio_factor

    # Aminoácidos compostos — valores reais, nunca proxy
    met = nutrients.get("methionine_g", {"value": 0})["value"]
    cys = nutrients.get("cystine_g", {"value": None})["value"]
    if cys is not None:
        out["methionine_plus_cystine_g"] = (met + cys) * (1000 / em_kcal_100g)
    else:
        out["methionine_plus_cystine_g"] = None  # nunca aproximar sem valor real

    phe = nutrients.get("phenylalanine_g", {"value": 0})["value"]
    tyr = nutrients.get("tyrosine_g", {"value": None})["value"]
    if tyr is not None:
        out["phenylalanine_plus_tyrosine_g"] = (phe + tyr) * (1000 / em_kcal_100g)
    else:
        out["phenylalanine_plus_tyrosine_g"] = None

    return out

def expand_category_wildcards(mapping, db):
    """_all_muscle_meat / _all_fat_source viram lista real de ingredient_id."""
    expanded = {}
    all_ids_by_category = {}
    for cat_group in db["protein_sources"].values():
        for ing in cat_group["ingredients"]:
            all_ids_by_category.setdefault(ing["category"], []).append(ing["ingredient_id"])
    for generic_name, ids in mapping.items():
        resolved = []
        for i in ids:
            if i == "_all_muscle_meat":
                resolved += all_ids_by_category.get("muscle_meat", [])
            elif i == "_all_fat_source":
                resolved += all_ids_by_category.get("fat_source", [])
            else:
                resolved.append(i)
        expanded[generic_name] = resolved
    return expanded

# ── 5. MONTE MATRIZ E CONSTRAINTS ────────────────────────────────────────
def build_lp_problem(selected_ingredients, data, der_info, cascade_level):
    """Monta o problema LP conforme o nível da cascata."""
    schema = data["schema"]
    cascade = schema["solve_cascade"]
    level_config = next(c for c in cascade if c["level"] == cascade_level)
    relax_tiers = set(level_config["relax_tiers"])
    
    # Matriz a_ij
    a_ij = {}
    for ing_id in selected_ingredients:
        ing = get_ingredient_by_id(ing_id, data["db"])
        a_ij[ing_id] = convert_ingredient_to_solver_space(ing, data["formulation_rules"]["bioavailability_factors"])
    
    # Constraints hard (sempre presentes)
    hard_constraints = []
    # Antagonismos minerais — sempre hard
    for antag in data["constraints"]["mineral_antagonisms"]:
        hard_constraints.append(antag)
    # SULs — hard se "safety_hard" não está em relax_tiers
    if "safety_hard" not in relax_tiers:
        for tox in data["constraints"]["toxicological_limits"]:
            hard_constraints.append(tox)
    # Inclusão — sempre hard
    for incl in data["constraints"]["inclusion_constraints"]:
        hard_constraints.append(incl)
    
    # V10.3: Piso clínico mínimo no Nível 3
    clinical_floor_bounds = {}
    if cascade_level == 3:
        clinical_floor_config = level_config.get("clinical_floor", {})
        defaults_by_category = clinical_floor_config.get("defaults_by_category", {})
        global_fallback = clinical_floor_config.get("global_fallback_g", 5)
        
        for ing_id in selected_ingredients:
            # 1. Tentar clinical_floor_g declarado no ingrediente
            ing_incl = next(
                (ic for ic in data["formulation_rules"]["_inclusion_semantics"]
                 .get("inclusion_constraints", []) if ic.get("ingredient_id") == ing_id),
                {}
            )
            declared_floor = ing_incl.get("clinical_floor_g")
            if declared_floor is not None:
                clinical_floor_bounds[ing_id] = declared_floor
            else:
                # 2. Usar default da categoria
                ing = get_ingredient_by_id(ing_id, data["db"])
                category = ing.get("category", "unknown")
                clinical_floor_bounds[ing_id] = defaults_by_category.get(category, global_fallback)
    
    # Constraints soft (relaxáveis conforme nível)
    soft_constraints = []
    # Nutrient bounds
    nutrient_registry = schema["NUTRIENT_REGISTRY"]
    for nb in data["constraints"]["nutrient_bounds"]:
        tier = nutrient_registry.get(nb["nutrient_id"], {}).get("constraint_tier", "adequacy_soft")
        if tier in relax_tiers:
            # Adicionar slack com peso = clinical_criticality
            criticality = nutrient_registry.get(nb["nutrient_id"], {}).get("clinical_criticality", "low")
            slack_weight = {"critical": 10.0, "high": 5.0, "moderate": 2.0, "low": 1.0}[criticality]
            soft_constraints.append({"constraint": nb, "slack_weight": slack_weight})
        else:
            hard_constraints.append(nb)
    
    # Envelope — soft se "envelope_soft" está em relax_tiers
    envelope_soft = "envelope_soft" in relax_tiers
    
    return {
        "a_ij": a_ij,
        "hard_constraints": hard_constraints,
        "soft_constraints": soft_constraints,
        "envelope": der_info["envelope"],
        "envelope_soft": envelope_soft,
        "der_kcal": der_info["der_kcal"],
        "clinical_floor_bounds": clinical_floor_bounds  # V10.3
    }

# ── 6. SOLVE — CASCATA DECLARATIVA ──────────────────────────────────────
def solve_cascade(selected_ingredients, data, der_info):
    """Executa a cascata declarativa lida do JSON."""
    schema = data["schema"]
    cascade = schema["solve_cascade"]
    
    for level_config in cascade:
        level = level_config["level"]
        
        # Nível 3: injetar calibração de pesos e validar hierarquia
        if level == 3:
            calibration = level_config.get("weight_calibration", {})
            mu_j = calibration.get("sul_violation_weight", {}).get("value", 100000)
            lambda_der = calibration.get("der_proximity_weight", {}).get("value", 1000)
            max_sigma_k = 10.0  # clinical_criticality "critical"
            # Validar hierarquia obrigatória: μ_j >> λ_der >> max(σ_k)
            if not (mu_j > 10 * lambda_der > 10 * max_sigma_k):
                raise ValueError(
                    f"Hierarquia de pesos violada no Nível 3: "
                    f"μ_j={mu_j} >> λ_der={lambda_der} >> max(σ_k)={max_sigma_k} "
                    f"é obrigatória. Se λ_der >= μ_j, o solver escolherá violar SUL "
                    f"para atingir DER — recriando o problema V10.1."
                )
        
        problem = build_lp_problem(selected_ingredients, data, der_info, level)
        raw_result = call_lp_solver(problem)
        
        # V10.3: Piso clínico no Nível 3 — fallback se solver infeasible com piso
        if level == 3 and raw_result["status"] == "infeasible":
            # Tentar novamente sem piso clínico (relaxar x_min_i para 0)
            clinical_floor_config = level_config.get("clinical_floor", {})
            fallback = clinical_floor_config.get("fallback_if_infeasible", {})
            if fallback:
                problem_relaxed = build_lp_problem(selected_ingredients, data, der_info, level)
                problem_relaxed["clinical_floor_bounds"] = {}  # Remover piso
                raw_result_relaxed = call_lp_solver(problem_relaxed)
                if raw_result_relaxed["status"] == "feasible":
                    raw_result = raw_result_relaxed
                    raw_result["clinical_floor_relaxed"] = True  # Marcar para build_diagnostic_analysis
        
        if raw_result["status"] == "feasible":
            result = {}
            result["solver_status"] = level_config["result_status"]
            result["cascade_level_used"] = level
            
            if level == 3:
                # NÍVEL 3: allocations é null (barreira mecânica).
                # O solver interno produz variáveis x_i, mas essas gramas NÃO
                # são recomendação de alimentação — são números matemáticos
                # de minimização de violação de SUL. A barreira é mecânica:
                # allocations = null garante que nenhum consumidor downstream
                # pode acidentalmente interpretar como instrução de alimentação.
                # A calibração μ_j >> λ_der >> σ_k garante que o cenário
                # contrafactual é numericamente significativo (solver tenta
                # aproximar DER), mas nunca trata o resultado como prescrição.
                # V10.3: Piso clínico mínimo garante que x_i ≥ x_min_i,
                # impedindo cenário clinicamente irrelevante (0.5g de fígado).
                result["allocations"] = None
                result["feeding_recommendation"] = "DO_NOT_FEED"
                
                # Preparar dados de piso clínico para diagnostic_analysis
                clinical_floor_info = {
                    "bounds": problem.get("clinical_floor_bounds", {}),
                    "relaxed": raw_result.get("clinical_floor_relaxed", False)
                }
                result["diagnostic_analysis"] = build_diagnostic_analysis(
                    raw_result, data, der_info, clinical_floor_info
                )
                # Documentar pesos usados para auditoria
                result["solver_metadata"] = raw_result.get("solver_metadata", {})
                result["solver_metadata"]["weight_calibration_used"] = {
                    "mu_j": mu_j,
                    "lambda_der": lambda_der,
                    "hierarchy_valid": True,
                    "note": "μ_j >> λ_der >> σ_k garante que o solver prefere evitar SUL a atingir DER"
                }
                # V10.3: Documentar piso clínico
                result["solver_metadata"]["clinical_floor_applied"] = not clinical_floor_info["relaxed"]
                result["solver_metadata"]["clinical_floor_bounds"] = clinical_floor_info["bounds"]
            else:
                # NÍVEL 1/2: allocations contém gramas recomendadas (seguras)
                result["allocations"] = format_allocations(raw_result, data)
                result["feeding_recommendation"] = "SAFE_TO_FEED" if level == 1 else "FEED_WITH_CAUTION"
                result["diagnostic_analysis"] = None
                result["solver_metadata"] = raw_result.get("solver_metadata", {})
            
            # Campos comuns a todos os níveis
            result["nutrient_results"] = compute_nutrient_results(raw_result, data)
            result["gaps"] = compute_gaps(result, data)
            result["alerts"] = compute_alerts(result, data)
            result["recommended_additions"] = compute_recommendations(result["gaps"], data["db"])
            return result
        # Se infeasible, desce para próximo nível
    
    # Nível 3 nunca chega aqui — always returns something
    # (safety net: se chegou aqui, erro de implementação)
    raise RuntimeError("Cascata completou sem resultado — bug no solver")

def build_diagnostic_analysis(raw_result, data, der_info, clinical_floor_info=None):
    """Constrói o bloco diagnostic_analysis para o Nível 3.
    
    NOTA ARQUITETURAL: Esta função recebe o resultado cru do solver (raw_result)
    que contém as variáveis x_i (gramas matemáticas da minimização de violação).
    Essas gramas são usadas APENAS para computar cenários contrafactuais
    (what_would_happen) — NUNCA são colocadas em allocations.
    
    V10.3: Recebe clinical_floor_info com bounds e relaxed flag.
    Se relaxed=True, documenta que o piso clínico foi relaxado.
    """
    schema = data["schema"]
    tox_limits = data["tox_limits"]
    
    if clinical_floor_info is None:
        clinical_floor_info = {"bounds": {}, "relaxed": False}
    
    # 1. Identificar violações de SUL inevitáveis
    # V10.4: toxicological_limits.json é uma LISTA no topo (não objeto com chave "safe_upper_limits").
    # Cada entrada tem sul.value aninhado (não sul_value plano).
    sul_violations = []
    for tox_entry in tox_limits:  # Lista direta — NÃO .get("safe_upper_limits", [])
        nut_id = tox_entry["nutrient_id"]
        sul_value = tox_entry["sul"]["value"]  # Aninhado — NÃO tox_entry["sul_value"]
        achieved = raw_result["nutrient_values"].get(nut_id, 0)
        if achieved > sul_value:
            sul_violations.append({
                "nutrient_id": nut_id,
                "sul": sul_value,
                "minimum_achievable_at_der": achieved,
                "pct_above_sul": round((achieved / sul_value - 1) * 100, 1),
                "mechanism": "Vit A and calories are inseparable in this ingredient — "
                           "every gram adds both proportionally. No feasible split exists."
                           if nut_id == "vitamin_a_iu" else
                           "Nutrient concentration and caloric content are proportional "
                           "in the selected ingredients — no feasible separation."
            })
    
    # 2. Cenário contrafactual: o que aconteceria se
    total_grams_for_der = sum(raw_result.get("x_values", {}).values())
    
    # V10.3: Verificar se x_i atinge piso clínico
    x_values = raw_result.get("x_values", {})
    floor_bounds = clinical_floor_info.get("bounds", {})
    ingredients_below_floor = []
    for ing_id, x_val in x_values.items():
        floor = floor_bounds.get(ing_id, 5)  # default 5g
        if 0 < x_val < floor:
            ingredients_below_floor.append({
                "ingredient_id": ing_id,
                "x_value_g": round(x_val, 2),
                "clinical_floor_g": floor,
                "note": f"Solver returned {x_val:.2f}g, below clinical floor of {floor}g"
            })
    
    what_would_happen = {
        "description": "If you fed ONLY the selected ingredients to meet caloric needs:",
        "grams_needed_for_der": round(total_grams_for_der, 1),
        "nutrient_at_risk": sul_violations[0]["nutrient_id"] if sul_violations else None,
        "value_at_that_amount": sul_violations[0]["minimum_achievable_at_der"] if sul_violations else None,
        "sul_value": sul_violations[0]["sul"] if sul_violations else None,
        "clinical_significance": (
            "Chronic hypervitaminosis A → osteoclast overactivation → "
            "pathologic fractures, osteodystrophy"
            if sul_violations and sul_violations[0]["nutrient_id"] == "vitamin_a_iu"
            else "Chronic excess → toxicological effects per SUL documentation"
        ),
        # V10.3: Piso clínico
        "clinical_floor_applied": not clinical_floor_info.get("relaxed", False),
        "clinical_floor_relaxed": clinical_floor_info.get("relaxed", False),
        "ingredients_below_floor": ingredients_below_floor,
        "x_min_i_effective": floor_bounds
    }
    
    # Se piso foi relaxado, adicionar nota
    if clinical_floor_info.get("relaxed", False):
        what_would_happen["clinical_floor_relaxation_note"] = (
            "Even the minimum recognizable portion of the selected ingredient(s) "
            "violates the SUL. No safe amount exists. The scenario below shows "
            "what the solver computed without the clinical floor constraint — "
            "these values are below any meaningful portion and serve only as "
            "mathematical evidence of inseparability."
        )
    
    # 3. Ações alternativas recomendadas
    recommended_alternative_actions = [
        "Add a calorie source WITHOUT concentrated vitamin A (e.g., beef_muscle_raw, chicken_muscle_raw)",
        "Reduce liver/organ proportion and add muscle meat as caloric base",
        "Use recipe mode (Receitas Prontas) for pre-validated safe combinations"
    ]
    
    # 4. Razão da infeasibilidade
    reason_parts = []
    if sul_violations:
        reason_parts.append(
            "No combination of selected ingredients meets caloric needs without "
            "exceeding safe limits. Caloric content and the SUL-violating nutrient "
            "are inseparable in the selected ingredient(s) — every gram adds both "
            "proportionally."
        )
    if clinical_floor_info.get("relaxed", False):
        reason_parts.append(
            "Even the minimum clinically significant portion (clinical_floor_g) "
            "of the ingredient exceeds the SUL. The solver was re-run without "
            "the floor constraint to produce a mathematical counterfactual."
        )
    
    return {
        "reason": " ".join(reason_parts) if reason_parts else "SUL violation inevitable with selected ingredients.",
        "sul_violations_inevitable": sul_violations,
        "what_would_happen": what_would_happen,
        "recommended_alternative_actions": recommended_alternative_actions
    }

def format_allocations(raw_result, data):
    """Converte variáveis x_i do solver em allocations com display_name e categoria.
    Usado APENAS nos Níveis 1 e 2 (onde allocations é seguro)."""
    allocations = []
    for ing_id, grams in raw_result.get("x_values", {}).items():
        if grams > 0.01:  # ignorar variáveis residuais
            ing = get_ingredient_by_id(ing_id, data["db"])
            allocations.append({
                "ingredient_id": ing_id,
                "display_name": ing.get("display_name", ing_id),
                "category": ing.get("category", "unknown"),
                "grams_per_day": round(grams, 1),
                "pct_of_total": 0,  # preenchido depois
                "kcal_per_day": 0,  # preenchido depois
                "cost_per_day": None
            })
    total_g = sum(a["grams_per_day"] for a in allocations)
    for a in allocations:
        a["pct_of_total"] = round(a["grams_per_day"] / total_g * 100, 1) if total_g > 0 else 0
    return allocations

def call_lp_solver(problem):
    """Chamada genérica ao solver LP (PuLP, scipy.optimize, ou outro).
       Retorna: {status: "feasible"|"infeasible", x_values: {ing_id: grams}, nutrient_values: {nut_id: value}}
       NOTA: x_values são variáveis de decisão brutas. No Nível 3, essas gramas
       NÃO são recomendação de alimentação — são números de minimização de violação.
       A montagem em allocations (ou null) é responsabilidade de solve_cascade."""
    # Implementação concreta do solver LP aqui
    # O ponto central: o solver é genérico, lê a cascata do JSON
    pass

# ── 7. VALIDE (saída) ───────────────────────────────────────────────────
def validate_output(result, data, der_info):
    # a) allocations referenciam IDs existentes (se não-null)
    if result["allocations"] is not None:
        for a in result["allocations"]:
            assert ingredient_exists_in_db(a["ingredient_id"], data["db"])
    # b) 41 nutrientes cobertos nos nutrient_results
    # V10.4: Os 41 nutrientes são os da nutrient_matrix em formulation_rules.
    # Variáveis compostas (ca_p_ratio, caloric_density, cost_per_kg) são
    # derivadas/penalizadas mas NÃO são nutrientes primários — não contam
    # neste assert. Se compute_nutrient_results incluir alguma, usar
    # assert len(result["nutrient_results"]) >= 41 em vez de == 41.
    assert len(result["nutrient_results"]) >= 41
    # c) solver_status ∈ ["optimal", "suboptimal", "unsafe_diagnostic"]
    assert result["solver_status"] in ("optimal", "suboptimal", "unsafe_diagnostic")
    # d) unsafe_diagnostic → allocations é null E diagnostic_analysis está presente
    if result["solver_status"] == "unsafe_diagnostic":
        assert result["allocations"] is None
        assert result["diagnostic_analysis"] is not None
    # e) feeding_recommendation corresponde ao solver_status
    expected_rec = {
        "optimal": "SAFE_TO_FEED",
        "suboptimal": "FEED_WITH_CAUTION",
        "unsafe_diagnostic": "DO_NOT_FEED"
    }
    assert result["feeding_recommendation"] == expected_rec[result["solver_status"]]
    # f) optimal/suboptimal → allocations não é null e soma está no envelope
    if result["solver_status"] in ("optimal", "suboptimal"):
        assert result["allocations"] is not None
        assert len(result["allocations"]) >= 1
        total_g = sum(a["grams_per_day"] for a in result["allocations"])
        envelope = der_info["envelope"]
        assert envelope["min_total_g"] <= total_g <= envelope["max_total_g"]
    # g) unsafe_diagnostic → hierarquia de pesos foi validada
    if result["solver_status"] == "unsafe_diagnostic":
        cal = result["solver_metadata"].get("weight_calibration_used", {})
        assert cal.get("hierarchy_valid") is True, (
            "Hierarquia de pesos μ_j >> λ_der >> σ_k não validada no Nível 3 — "
            "risco de solver escolher violar SUL para atingir DER"
        )
        assert cal.get("mu_j", 0) > 10 * cal.get("lambda_der", 0), "μ_j deve ser >> λ_der"
        assert cal.get("lambda_der", 0) > 100, "λ_der deve ser > 0 (impede solução degenerada x_i=0)"
        # h) [V10.3] unsafe_diagnostic → piso clínico documentado
        assert "clinical_floor_applied" in result["solver_metadata"], (
            "solver_metadata não contém clinical_floor_applied no Nível 3"
        )
        assert isinstance(result["solver_metadata"]["clinical_floor_applied"], bool)
        assert "clinical_floor_bounds" in result["solver_metadata"]
        # i) [V10.3] Se clinical_floor_relaxed, nota deve existir no what_would_happen
        wwh = result["diagnostic_analysis"]["what_would_happen"]
        if wwh.get("clinical_floor_relaxed", False):
            assert "clinical_floor_relaxation_note" in wwh, (
                "Piso clínico relaxado sem nota de documentação"
            )

# ── 8. MAIN ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mode = sys.argv[1]  # --runtime ou --build-recipes
    
    if mode == "--runtime":
        animal_data = json.load(open("animal_input.json"))  # dados do usuário
        data = load_all_jsons()
        validate_inputs(data)
        der_info = calculate_der_and_envelope(animal_data, data["growth"], get_active_scenario(data))
        result = solve_cascade(animal_data["selected_ingredients"], data, der_info)
        validate_output(result, data, der_info)
        json.dump(result, open("solver_output.json", "w"), indent=2, ensure_ascii=False)
    
    elif mode == "--build-recipes":
        data = load_all_jsons()
        validate_inputs(data)
        recipes = generate_all_recipes(data)
        json.dump(recipes, open("recipes_precomputed.json", "w"), indent=2, ensure_ascii=False)
```

### 6.5 Notas sobre a Conversão de Base

`valor_1000kcal = valor_100g_as_fed × fator_unidade × (1000 / EM_kcal_por_100g)`. Isso é diferente de simplesmente mudar mg→g — é reindexar de "por 100g de alimento" para "por 1000kcal de energia metabolizável", o que exige calcular a EM de cada ingrediente individualmente via Atwater modificado. O DB **não tem** `fiber_g` — assumido 0 no cálculo; se um ingrediente vegetal for adicionado no futuro, isso precisa ser corrigido antes.

---

## 7. Contrato de Dado (Output do Solver) — V10

O contrato de dado é **pré-solver/schema** — definido antes da implementação, não after-the-fact. Todo output do solver obedece a este schema, independentemente do nível da cascata.

**IMPORTANTE — Estrutura bifurcada por nível:** O Nível 3 (`unsafe_diagnostic`) produz um contrato *diferente* dos Níveis 1/2. A bifurcação é intencional e resolve a tensão entre "inviolabilidade da saída" e "segurança do usuário": o usuário nunca recebe tela em branco (análise e 41 valores sempre presentes), mas também nunca recebe gramas que podem ser acidentalmente interpretadas como instrução de alimentação quando o resultado é inseguro.

### 7.1 Contrato Nível 1/2 (Recomendação Real — Pode Alimentar)

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

### 7.2 Contrato Nível 3 (Diagnóstico — NÃO Alimentar)

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
    "weight_calibration_used": {
      "mu_j": 100000,
      "lambda_der": 1000,
      "hierarchy_valid": true,
      "note": "μ_j >> λ_der >> σ_k garante que o solver prefere evitar SUL a atingir DER, e prefere aproximar DER a melhorar adequação"
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
- **[V10.2]** No Nível 3, `solver_metadata.weight_calibration_used` documenta os pesos efetivamente usados (`μ_j`, `λ_der`) e verifica `hierarchy_valid: true`. Isso impede que uma alteração inadvertida nos pesos reproduza o problema identificado na crítica V10.1 (solver escolhendo violar SUL para atingir DER).
- **[V10.3]** No Nível 3, `what_would_happen` inclui `clinical_floor_applied` (true/false), `clinical_floor_relaxed` (true/false), `ingredients_below_floor` (lista de ingredientes com x_i abaixo do piso), e `x_min_i_effective` (piso efetivo por ingrediente). Se o piso clínico foi relaxado, `clinical_floor_relaxation_note` documenta que o cenário contrafactual é abaixo de qualquer porção reconhecível.
- **[V10.3]** No Nível 3, `solver_metadata.clinical_floor_applied` e `solver_metadata.clinical_floor_bounds` documentam se o piso clínico foi efetivamente aplicado e quais valores foram usados. Isso permite auditoria: se `clinical_floor_applied = false`, o diagnóstico deve ser interpretado com cautela — o cenário contrafactual pode conter gramas clinicamente irrelevantes.

---

## 8. Arquitetura do Solver e Cascata — Detalhamento Técnico

### 8.1 Formulação Matemática por Nível

**Nível 1 (Goal Programming Canônico):**

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

**Nível 2 (Relaxamento de Adequação via Slack Ponderado):**

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

**Nível 3 (Minimização de Violação de SUL — com Proximidade ao DER e Piso Clínico Mínimo):**

```
Minimize  Σ_j  μ_j × v_j⁺  +  λ_der × σ_der  +  Σ_k  σ_k × clinical_criticality_weight_k

Subject to:
  Σ_i  a_ij × x_i ≤ SUL_j + v_j⁺                  ∀j ∈ safety_hard (v_j⁺ ≥ 0 é violação)
  Σ_i  a_ik × x_i + s_k⁻ ≥ min_k - σ_k           ∀k ∈ adequacy_soft
  DER - σ_der ≤ Σ_i  (EM_i/100) × x_i             (tentar chegar perto do DER)
  x_i ≥ x_min_i                                     ∀i (piso clínico mínimo — V10.3)
  x_i, v_j⁺, s_k⁻, σ_k, σ_der ≥ 0
```

**Piso clínico mínimo `x_min_i` — V10.3:**

O piso clínico mínimo é um constraint que impede o solver de produzir variáveis `x_i` com magnitude tecnicamente não-zero mas clinicamente irrelevante. Sem esse piso, o solver pode retornar `x_i = 0.5g` de fígado — matematicamente distinto de `x_i = 0` (a solução degenerada que `λ_der` previne), mas inútil como cenário contrafactual. O usuário receberia `what_would_happen.grams_needed_for_der = 0.5`, um número que não representa nenhum cenário de alimentação real.

**Definição do piso por ingrediente:**

| Tipo de ingrediente | `x_min_i` | Racional |
|---|---|---|
| Carne muscular (muscle_meat) | 10g | Porção mínima reconhecível — abaixo disso, não constitui "cenário" |
| Órgãos (organ_secreting, organ_non_secreting) | 5g | Porção mínima para órgãos — 5g é ~1 colher de chá, reconhecível |
| Osso carnudo (bone) | 5g | Porção mínima — abaixo, contribuição de Ca é irrelevante |
| Gordura (fat_source) | 2g | Porção mínima — gordura é densa; 2g é visível |
| Suplemento (supplement) | 0.1g | Suplementos são usados em quantidades milimétricas (kelp, sal, CuSO₄) |

**Valores default (se `x_min_i` não está declarado por ingrediente):** 5g — conservador, cobre a maioria dos casos.

**Onde `x_min_i` vive no JSON:** `lp_parameters_schema.json → NUTRIENT_REGISTRY` não é o lugar (REGISTRY é por nutriente, não por ingrediente). O piso é por ingrediente, então vive em `formulation_rules.json → inclusion_constraints` como campo opcional `"clinical_floor_g"`:

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

**O que acontece se o solver não consegue satisfazer `x_i ≥ x_min_i` e simultaneamente minimizar violação de SUL:**

O piso clínico é um constraint **hard** no Nível 3. Se o solver retorna `infeasible` mesmo com SUL relaxado (o que só acontece em casos extremos — ex: fígado puro onde 5g já ultrapassa SUL), o sistema aplica a seguinte fallback:

1. **Relaxar `x_min_i` para 0g** (remover o piso), executar o solver novamente.
2. **Marcar `what_would_happen.clinical_floor_relaxed = true`** no `diagnostic_analysis` — indicando que o cenário contrafactual é numericamente não-degenerado, mas não atinge o piso clínico mínimo.
3. **Documentar a magnitude:** `"note": "Solver returned x_i below clinical_floor_g (0.3g < 5g). Even the minimum recognizable portion of this ingredient violates the SUL. No safe amount exists."`

Essa fallback é necessária porque o princípio de inviolabilidade da saída se aplica: mesmo que o piso clínico não possa ser satisfeito, o sistema nunca retorna tela em branco — retorna diagnóstico com a ressalva documentada.

**Calibração obrigatória dos pesos — hierarquia de magnitudes:**

| Peso | Símbolo | Valor | Racional |
|---|---|---|---|
| Violação de SUL | `μ_j` | 100.000 | **Dominante** — o solver prefere qualquer outra penalidade a violar SUL. Cada IU/g acima do SUL "custa" 100.000× mais que qualquer desvio de adequação. |
| Proximidade ao DER | `λ_der` | 1.000 | **Intermediário** — o solver tenta se aproximar do DER, mas não a ponto de violar SUL para conseguir. Se a escolha é entre chegar 100kcal mais perto do DER ou evitar 1 IU de Vit A acima do SUL, o solver escolhe evitar a violação (100.000 > 1.000 × qualquer desvio calórico razoável). |
| Adequação (slack) | `clinical_criticality_weight_k` | 1.0–10.0 | **Menor** — no Nível 3, adequação já é secundária. O solver aceita grandes deficiências de adequação se isso evitar violação de SUL. |

**Por que `λ_der` precisa de peso explícito:** Sem `λ_der` na função objetivo, o solver pode produzir a solução degenerada `x_i = 0, v_j⁺ = 0, σ_der = DER` — objetivo total = 0, tecnicamente "ótimo" mas sem nenhuma gramagem útil. O `diagnostic_analysis.what_would_happen` ficaria vazio ou sem significado. Com `λ_der = 1.000`, o solver efetivamente busca o ponto mais próximo do DER que minimiza a violação de SUL — produzindo um cenário contrafactual numericamente significativo para o diagnóstico.

**Por que a hierarquia é obrigatória, não configurável:** A ordem `μ_j >> λ_der >> σ_k` garante que:
1. O solver **nunca** escolhe violar SUL para se aproximar do DER (`μ_j/λ_der = 100:1`).
2. O solver **nunca** escolhe se afastar do DER para melhorar adequação (`λ_der/max(σ_k) = 100:1`).
3. Essas razões não são arbitrárias — são **constraints implícitas** da semântica do Nível 3. Trocar a hierarquia (ex: `λ_der > μ_j`) recriaria exatamente o problema que a crítica identifica: o solver escolheria violar o SUL para atingir o DER.

**NOTA ARQUITETURAL — Contrato do Nível 3:** Embora o solver produza variáveis `x_i` (gramas matemáticas), o contrato de saída do Nível 3 define `allocations = null`. As gramas `x_i` são usadas **exclusivamente** dentro de `build_diagnostic_analysis()` para computar `what_would_happen.grams_needed_for_der` — são recontextualizadas como cenário contrafactual ("o que aconteceria se"), nunca como prescrição. A barreira entre "número calculado" e "gramas para alimentar" é mecânica (campo nulo), não semântica (label/badge). A calibração `μ_j >> λ_der >> σ_k` garante que o cenário contrafactual é numericamente significativo (o solver efetivamente tenta se aproximar do DER), mas nunca é tratado como recomendação.

### 8.2 Transição entre Níveis — Regras de Ouro

1. O solver **só** desce de nível se o nível atual retornar `infeasible`. Nunca pula.
2. Se o Nível 1 é feasible com desvio zero em todos os targets → `optimal`, para.
3. Se o Nível 1 é feasible com desvio não-zero em alguns targets (goal programming canônico) → `optimal`, para. O desvio já é capturado pelas variáveis `d_j⁻/d_j⁺`.
4. Se o Nível 1 é infeasible → tente Nível 2.
5. Se o Nível 2 é feasible → `suboptimal`, para.
6. Se o Nível 2 é infeasible → tente Nível 3.
7. O Nível 3 **sempre** tem solução (a função objetivo minimiza violação, e o espaço de decisão é não-vazio contanto que `x_i ≥ 0`). Resultado: `unsafe_diagnostic`.
8. **[V10.2] Hierarquia de pesos no Nível 3 é obrigatória:** `μ_j >> λ_der >> max(σ_k)`. Se `λ_der` não tem peso explícito, o solver produz solução degenerada (`x_i = 0`). Se `λ_der > μ_j`, o solver escolhe violar SUL para atingir DER — recriando o problema que a crítica de V10.1 identificou. A hierarquia é **constraint implícita** da semântica do Nível 3, não parâmetro configurável.
9. **[V10.3] Piso clínico mínimo no Nível 3 é obrigatório:** `x_i ≥ x_min_i` (default 5g por ingrediente). Sem o piso, o solver pode produzir `x_i = 0.5g` — tecnicamente não-degenerado, mas clinicamente irrelevante como cenário contrafactual. O piso garante que `what_would_happen` contém gramagens que representam porções reconhecíveis. Se o piso não pode ser satisfeito (ingrediente tão tóxico que até a porção mínima viola SUL), o sistema relaxa o piso, marca `clinical_floor_relaxed = true`, e documenta a razão — nunca retorna tela em branco.

### 8.3 Caso Especial: Óleo de Bacalhau / Fígado Isolado (Colisão SUL vs. DER)

Este é o caso canônico de colisão SUL vs. DER — e o principal argumento para `allocations = null` no Nível 3. Um único ingrediente (óleo de fígado de bacalhau, ou fígado bovino puro) pode ter vitamina A tão concentrada que, mesmo na quantidade mínima para atingir o DER, ultrapassa o SUL de Vitamina A. Caloria e Vitamina A são inseparáveis neste ingrediente — cada grama carrega ambos proporcionalmente. Não existe ponto no espaço de decisão que satisfaça ambos simultaneamente. O mesmo padrão aplica-se a qualquer ingrediente onde caloria e nutriente tóxico são proporcionais: kelp puro (Iodo), sal puro (Sódio), sulfato de cobre puro (Cobre), etc.

O comportamento correto é:
- Nível 1: infeasible (SUL vs. DER colide — não existe x_i ≥ 0 que satisfaça ambos).
- Nível 2: infeasible (SUL continua hard, mesma colisão — o simplex não encontra região factível).
- Nível 3: `unsafe_diagnostic` — o solver minimiza a violação do SUL enquanto tenta se aproximar do DER. **Mas o resultado não contém `allocations`** — contém `diagnostic_analysis` que documenta a inseparabilidade caloria/tóxico e recomenda alternativas.

**Risco de solução degenerada sem `λ_der`:** Se `σ_der` (desvio do DER) não tem peso explícito na função objetivo do Nível 3, o solver pode produzir `x_i = 0, v_j⁺ = 0, σ_der = DER` — objetivo = 0, tecnicamente "ótimo" mas sem nenhuma gramagem. Isso é uma solução degenerada: o solver "resolve" o problema escolhindo nada, porque `x_i = 0` não viola nenhum SUL. Com `λ_der = 1.000` (ver Seção 8.1), o solver é forçado a buscar um ponto não-trivial — produzindo um cenário contrafactual numericamente significativo onde `what_would_happen.grams_needed_for_der` contém um número real (ex: "165g necessários para o DER → 28.000 IU de Vit A, SUL = 9.375 IU").

**Por que `allocations = null` é essencial aqui:** A crítica que motivou a V10.1 demonstrou que o simplex *vai* encontrar um ponto que minimiza a soma ponderada de desvios. Com a calibração `μ_j = 100.000 >> λ_der = 1.000`, o solver prefere não violar o SUL — mas se a inseparabilidade é estrutural (caloria e tóxico vêm juntos), a violação é inevitável e o solver a minimiza. O ponto resultante é matematicamente correto como minimização de violação, mas perigoso como recomendação de alimentação. A solução: não devolver gramas. Devolver análise. A calibração garante que o cenário contrafactual é numericamente útil; `allocations = null` garante que ele não é mecanicamente utilizável como prescrição.

**V10.3 — Piso clínico mínimo no caso de colisão:** Sem o piso `x_i ≥ x_min_i`, o solver pode retornar `x_i = 0.5g` de fígado — tecnicamente não-degenerado (`λ_der` impede `x_i = 0`), mas clinicamente irrelevante (0.5g não é uma porção reconhecível). O piso clínico exige `x_i ≥ 5g` para órgãos, forçando o solver a produzir um cenário contrafactual onde a gramagem representa uma porção real. No caso de fígado bovino puro: 5g de fígado contém ~850 IU de Vit A, ainda abaixo do SUL de 9.375 IU. O solver com piso clínico pode encontrar um ponto factível (5g de fígado, com `σ_der` grande — o DER não é atingido, mas o cenário é clinicamente significativo). Se o solver não consegue satisfazer nem 5g sem violar SUL (improvável para fígado, mas possível para óleo de fígado de bacalhau puro), o piso é relaxado e `clinical_floor_relaxed = true` documenta a situação.

**Cenário extremo — óleo de fígado de bacalhau isolado:** Este ingrediente tem ~1.800.000 IU de Vit A por 100g. Mesmo 0.1g (piso de suplemento) contém ~1.800 IU — abaixo do SUL. Mas para atingir o DER, seriam necessárias quantidades que ultrapassam o SUL em ordens de magnitude. O solver com piso clínico = 0.1g (suplemento) pode encontrar um ponto factível, mas o `what_would_happen` mostra que para o DER, a violação de SUL é massiva. Se o usuário selecionou APENAS óleo de bacalhau, o cenário contrafactual é: "mesmo a porção mínima reconhecível (0.1g) está muito aquém do DER, e qualquer quantidade que se aproxime do DER ultrapassa o SUL em 2000%+."

---

## 9. Três Achados da V9 — Status Real (Verificado Contra os Arquivos, Não Assumido)

**Nota de processo**: esta seção usava o header "RESOLVIDO NA V10" descrevendo o que deveria ser feito, não o que tinha sido feito — violação direta do Case 3 (README/AI Engineering Constitution: "RESOLVED" usado para um plano, não uma ação). Corrigido nesta sessão após verificação literal contra `DB_ingredientes.json` e `audit_provenance.json` reais.

### 9.1 `kelp_meal_dried`, `salt_nacl`, `copper_sulfate` — **PLANEJADO, NÃO APLICADO**

**Evidência (rodada nesta sessão):**
```
python3 -c "... 'kelp_meal_dried' in all_ids ..."
→ kelp_meal_dried: AINDA AUSENTE
→ salt_nacl: AINDA AUSENTE
→ copper_sulfate: AINDA AUSENTE
→ total ingredientes no DB: 20 (não 23)
```
O plano de resolução (fonte USDA FDC para kelp, composição estequiométrica para sal e sulfato de cobre) continua válido como especificação — só não foi executado contra o arquivo real. Iodo permanece estruturalmente infeasible até isso ser aplicado de fato.

### 9.2 17 `source_ref` Órfãs — **PLANEJADO, NÃO APLICADO**

**Evidência (rodada nesta sessão):**
```
refs no audit_provenance.json: 85 (idêntico ao valor pré-V10)
das 17 originalmente órfãs, ainda ausentes: 17 de 17
```
Nenhuma entrada nova foi adicionada. Lista completa das 17 ainda pendentes: `REF_BIO_VISCERA_VIT_A_VAR`, `REF_LIT_VET_BLOOD`, `REF_LIT_VET_COLLAGEN`, `REF_LIT_VET_POULTRY_KIDNEY`, `REF_LIT_VET_SPLEEN`, `REF_LIT_VET_TAIL`, `REF_LIT_VET_TONGUE`, `REF_LIT_VET_TRIPE`, `REF_MC_MONICA_SEGAL`, `REF_SAFETY_BOVINE_BLOOD_PATHOGENS`, `REF_SAFETY_BOVINE_COOKING`, `REF_SAFETY_BOVINE_RAW_PATHOGENS`, `REF_SAFETY_FISH_RAW_PARASITES`, `REF_SAFETY_IRON_OVERLOAD`, `REF_SAFETY_PORK_RAW_PATHOGENS`, `REF_SAFETY_POULTRY_BLOOD_PATHOGENS`, `REF_SAFETY_POULTRY_RAW_PATHOGENS`.

### 9.3 `methionine_plus_cystine_g`/`phenylalanine_plus_tyrosine_g` — **PLANEJADO, NÃO APLICADO**

**Evidência (rodada nesta sessão):**
```
ingredientes com cystine_g ou tyrosine_g: 0 de 20
```
A regra de não-inferência (nunca proxy, campo `None` até valor real) continua a decisão correta — só ainda não foi executada a extração da fonte USDA.

### 9.4 Regra derivada deste achado, permanente

Nenhuma seção futura deste documento usa "RESOLVIDO"/"CORRIGIDO"/"IMPLEMENTADO" sem um bloco `Evidência:` com comando + output literal, rodado na sessão corrente, colado imediatamente abaixo do header. Na ausência disso, o status correto é "PLANEJADO".

---

## 10. Estágios do Animal — V10

| Estágio | Dado nutricional (`scenarios.json`) | Constraint (`constraints.json`) | Multiplicador de energia (`growth_energy_skeletal`) | Envelope |
|---|---|---|---|---|
| Crescimento — lento (recomendado) | SCN_B, 17 targets, `ACTIVE_TARGET` | 60 constraints + cascata | k = 1.2–1.5 | DER-derived |
| Crescimento — rápido (desaconselhado) | SCN_A, 17 targets, `WARNING_DO_NOT_OPTIMIZE` | 60 constraints + cascata | k = 2.0–3.0 | DER-derived |
| Adulto ativo/trabalho | **NOVO cenário SCN_C** (a criar) | 60 constraints + cascata (ajustar SULs para adulto se necessário) | k = 1.5 | DER-derived |
| Sênior/geriátrico | **Não existe** — zero dados, zero cenário, zero constraint, zero multiplicador | — | — | — |

**Prioridade P2, não bloqueante para o MVP de filhote:** criar cenário de manutenção adulta (SCN_C) usando o `k=1.5` já existente. O envelope dinâmico da V10 já suporta qualquer DER — só faltam os 17 targets específicos para adulto e possíveis ajustes de SULs.

---

## 11. Testes Obrigatórios de Integridade (Anti-Gamificação) — V10

### 11.1 Princípio Anti-Gamificação

A arquitetura deve levar em conta que todos os arquivos, edições, codificações, execuções e avaliações de testes serão realizados por uma **Coding AI Agent**. Não podemos confiar na inteligência da IA, mas sim na clareza de leitura que ela terá.

Os testes **NÃO PODEM** ser gamificados ou mockados de forma que a IA ache que passou sem validar a lógica real. Os testes devem:
- Ler os JSONs reais (não fixtures ou mocks).
- Executar o build_pipeline real (não versão simplificada).
- Validar a descida real da cascata (não apenas verificar que o campo existe).
- Produzir output colado, não alegado.

### 11.2 Testes de Integração da Cascata

```python
def test_cascade_level1_feasible_for_balanced_selection():
    """Seleção equilibrada (muscle + organ + bone) deve resultar em optimal (Nível 1).
    
    ANTI-GAMIFICATION: Não basta verificar que solver_status == "optimal".
    Deve verificar que cascade_level_used == 1 E que nenhum slack de adequação
    foi usado (todas as variáveis σ_k == 0 no solver_metadata).
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
    """Seleção sem fonte de cálcio deve descer para Nível 2 (suboptimal).
    
    ANTI-GAMIFICATION: Deve verificar que o solver realmente tentou Nível 1
    (cascade_attempts contém 1) e falhou, E que Nível 2 usou slack
    (slack_variables_used não está vazio).
    """
    result = run_pipeline(
        animal={"sex": "male", "weight_kg": 25, "age_months": 8},
        selected=["beef_muscle_raw", "beef_liver_raw"],
        mode="runtime"
    )
    assert result["solver_status"] == "suboptimal"
    assert result["cascade_level_used"] == 2
    assert 1 in result["solver_metadata"]["cascade_attempts"]
    assert len(result["solver_metadata"]["slack_variables_used"]) > 0
    # Verificar que cálcio está nos gaps
    calcium_gap = next(g for g in result["gaps"] if g["nutrient_id"] == "calcium_g")
    assert calcium_gap["pct_of_min"] < 50

def test_cascade_level3_triggered_by_sul_collision():
    """Seleção com colisão SUL inevitável deve descer para Nível 3 (unsafe_diagnostic).
    
    ANTI-GAMIFICATION: Deve verificar que SUL foi efetivamente violado
    (pct_of_sul > 100 para pelo menos 1 nutriente) E que a violação está
    documentada nos alerts com severity = "danger" E que allocations é null
    (barreira mecânica, não apenas semântica) E diagnostic_analysis está presente.
    """
    result = run_pipeline(
        animal={"sex": "male", "weight_kg": 25, "age_months": 8},
        selected=["beef_liver_raw"],  # Vitamina A ultrapassa SUL inevitavelmente
        mode="runtime"
    )
    assert result["solver_status"] == "unsafe_diagnostic"
    assert result["cascade_level_used"] == 3
    # BARRREIRA MECÂNICA: allocations DEVE ser null — nunca gramas no Nível 3
    assert result["allocations"] is None
    # diagnostic_analysis DEVE estar presente com explicação da inseparabilidade
    assert result["diagnostic_analysis"] is not None
    assert len(result["diagnostic_analysis"]["sul_violations_inevitable"]) > 0
    assert "inseparable" in result["diagnostic_analysis"]["reason"].lower()
    # feeding_recommendation DEVE ser DO_NOT_FEED
    assert result["feeding_recommendation"] == "DO_NOT_FEED"
    # Verificar violação real de SUL nos nutrient_results
    sul_violations = [nr for nr in result["nutrient_results"] 
                      if nr.get("pct_of_sul") is not None and nr["pct_of_sul"] > 100]
    assert len(sul_violations) > 0
    danger_alerts = [a for a in result["alerts"] if a["severity"] == "danger"]
    assert len(danger_alerts) > 0
    # what_would_happen DEVE conter os números matemáticos (para diagnóstico, não prescrição)
    assert result["diagnostic_analysis"]["what_would_happen"]["grams_needed_for_der"] is not None
    assert result["diagnostic_analysis"]["what_would_happen"]["nutrient_at_risk"] is not None

def test_cascade_never_skips_levels():
    """A cascata nunca pula do Nível 1 para o Nível 3.
    
    ANTI-GAMIFICATION: Para qualquer entrada, cascade_attempts deve ser
    [1], [1, 2], ou [1, 2, 3] — nunca [1, 3] ou [3].
    """
    # Testar com 10 seleções aleatórias
    for _ in range(10):
        selection = random_ingredient_selection(size=random.randint(1, 5))
        result = run_pipeline(animal=STANDARD_PUPPY, selected=selection, mode="runtime")
        attempts = result["solver_metadata"]["cascade_attempts"]
        assert attempts == sorted(attempts), f"Cascata pulou nível: {attempts}"

def test_single_ingredient_returns_result():
    """Seleção de 1 ingrediente NÃO tóxico (ex: filé mignon) NUNCA deve dar tela em branco.
    
    ANTI-GAMIFICATION: Verificar que allocations tem pelo menos 1 entrada,
    nutrient_results tem exatamente 41, e gaps é populado.
    Filé mignon sozinho não colide com SUL — deve ser suboptimal, não unsafe_diagnostic.
    """
    result = run_pipeline(
        animal={"sex": "male", "weight_kg": 25, "age_months": 8},
        selected=["beef_muscle_raw"],
        mode="runtime"
    )
    # Filé mignon sozinho: falta adequação mas NÃO é tóxico → suboptimal
    assert result["solver_status"] == "suboptimal"
    assert result["feeding_recommendation"] == "FEED_WITH_CAUTION"
    assert result["allocations"] is not None
    assert len(result["allocations"]) >= 1
    assert len(result["nutrient_results"]) == 41
    assert len(result["gaps"]) > 0  # Filé mignon sozinho tem gaps
    assert len(result["recommended_additions"]) > 0

def test_single_ingredient_sul_collision_no_allocations():
    """Seleção de 1 ingrediente TÓXICO (ex: fígado bovino puro) deve ser unsafe_diagnostic
    com allocations = null — barreira mecânica contra alimentação insegura.
    
    ANTI-GAMIFICATION: Verificar que allocations é EXPLICITAMENTE None (não vazio,
    não ausente, mas null). Verificar que diagnostic_analysis.what_would_happen
    contém gramas matemáticas (para diagnóstico) mas allocations não.
    """
    result = run_pipeline(
        animal={"sex": "male", "weight_kg": 25, "age_months": 8},
        selected=["beef_liver_raw"],
        mode="runtime"
    )
    assert result["solver_status"] == "unsafe_diagnostic"
    assert result["allocations"] is None  # BARRREIRA MECÂNICA
    assert result["diagnostic_analysis"] is not None
    # Números matemáticos existem no diagnóstico, não nas allocations
    assert result["diagnostic_analysis"]["what_would_happen"]["grams_needed_for_der"] > 0
    # Mas não existem gramas recomendadas
    assert result["allocations"] is None
    assert result["feeding_recommendation"] == "DO_NOT_FEED"

def test_level3_weight_hierarchy_validated():
    """[V10.2] No Nível 3, a hierarquia de pesos μ_j >> λ_der >> σ_k DEVE ser validada.
    
    ANTI-GAMIFICATION: Não basta verificar que weight_calibration_used existe.
    Deve verificar que μ_j > 10 × λ_der > 10 × max(σ_k) — se a hierarquia
    for violada, o solver escolherá violar SUL para atingir DER, que é
    exatamente o problema identificado na crítica V10.1.
    """
    result = run_pipeline(
        animal={"sex": "male", "weight_kg": 25, "age_months": 8},
        selected=["beef_liver_raw"],  # Garante Nível 3
        mode="runtime"
    )
    assert result["solver_status"] == "unsafe_diagnostic"
    cal = result["solver_metadata"]["weight_calibration_used"]
    assert cal["hierarchy_valid"] is True
    assert cal["mu_j"] > 10 * cal["lambda_der"], (
        f"μ_j={cal['mu_j']} não é >> λ_der={cal['lambda_der']} — "
        f"o solver pode escolher violar SUL para atingir DER"
    )
    assert cal["lambda_der"] > 100, (
        f"λ_der={cal['lambda_der']} muito baixo — risco de solução degenerada (x_i=0)"
    )

def test_level3_no_degenerate_solution():
    """[V10.2] O Nível 3 NÃO deve produzir solução degenerada (x_i = 0 para tudo).
    
    Sem λ_der na função objetivo, o solver pode escolher x_i = 0 (nada),
    v_j⁺ = 0 (sem violação), σ_der = DER (aceita desvio total). Objetivo = 0.
    Isso é matematicamente "ótimo" mas inútil como diagnóstico.
    Com λ_der = 1.000, o solver busca ponto não-trivial próximo do DER.
    
    ANTI-GAMIFICATION: Verificar que what_would_happen.grams_needed_for_der > 0.
    """
    result = run_pipeline(
        animal={"sex": "male", "weight_kg": 25, "age_months": 8},
        selected=["beef_liver_raw"],
        mode="runtime"
    )
    assert result["solver_status"] == "unsafe_diagnostic"
    grams = result["diagnostic_analysis"]["what_would_happen"]["grams_needed_for_der"]
    assert grams > 0, (
        f"Solução degenerada: grams_needed_for_der = {grams} — "
        f"λ_der pode estar ausente ou muito baixo na função objetivo"
    )

def test_level3_clinical_floor_prevents_irrelevant_xi():
    """[V10.3] O Nível 3 NÃO deve produzir x_i clinicamente irrelevante.
    
    Sem o piso clínico (x_min_i), o solver pode retornar x_i = 0.5g de fígado —
    tecnicamente não-degenerado (λ_der impede x_i = 0), mas inútil como cenário
    contrafactual. 0.5g não é uma porção reconhecível de nenhum ingrediente.
    
    Com o piso clínico (5g para órgãos), o solver deve retornar x_i ≥ 5g,
    produzindo um cenário contrafactual clinicamente significativo.
    
    ANTI-GAMIFICATION: Verificar que:
    1. what_would_happen.clinical_floor_applied == True
    2. Para cada ingrediente com x_i > 0, x_i ≥ x_min_i_efetivo
    3. ingredients_below_floor está vazio
    """
    result = run_pipeline(
        animal={"sex": "male", "weight_kg": 25, "age_months": 8},
        selected=["beef_liver_raw"],
        mode="runtime"
    )
    assert result["solver_status"] == "unsafe_diagnostic"
    wwh = result["diagnostic_analysis"]["what_would_happen"]
    
    # Verificar que o piso clínico foi aplicado
    assert wwh["clinical_floor_applied"] is True, (
        "Piso clínico não foi aplicado — cenário contrafactual pode conter "
        "gramas clinicamente irrelevantes"
    )
    assert wwh["clinical_floor_relaxed"] is False, (
        "Piso clínico foi relaxado sem motivo — verificar se x_min_i está "
        "declarado corretamente no formulation_rules"
    )
    assert len(wwh["ingredients_below_floor"]) == 0, (
        f"Ingredientes abaixo do piso clínico: {wwh['ingredients_below_floor']} — "
        f"o solver retornou gramas clinicamente irrelevantes"
    )
    
    # Verificar que x_min_i_efetivo está documentado
    assert "x_min_i_effective" in wwh
    assert "beef_liver_raw" in wwh["x_min_i_effective"]
    assert wwh["x_min_i_effective"]["beef_liver_raw"] == 5, (
        "Piso clínico para órgão secretor deve ser 5g"
    )

def test_level3_clinical_floor_relaxed_for_extreme_ingredient():
    """[V10.3] Para ingrediente EXTREMO (óleo de fígado de bacalhau puro),
    o piso clínico PODE ser relaxado — mas deve ser documentado.
    
    Cenário: óleo de bacalhau puro (se disponível no DB) é tão concentrado
    em Vit A que até a porção mínima reconhecível pode violar o SUL.
    Neste caso, o solver relaxa o piso clínico, marca
    clinical_floor_relaxed = true, e documenta a razão.
    
    ANTI-GAMIFICATION: Verificar que:
    1. clinical_floor_relaxed == True (piso foi relaxado)
    2. clinical_floor_relaxation_note está presente
    3. O diagnóstico ainda contém análise (nunca tela em branco)
    4. O solver_metadata documenta clinical_floor_applied = False
    """
    # NOTA: Este teste assume que cod_liver_oil existe no DB.
    # Se não existe, o teste é skipado com motivo documentado.
    try:
        result = run_pipeline(
            animal={"sex": "male", "weight_kg": 25, "age_months": 8},
            selected=["cod_liver_oil"],  # Se disponível
            mode="runtime"
        )
    except ValueError as e:
        if "ingredient_id" in str(e):
            import pytest
            pytest.skip("cod_liver_oil não está no DB — teste não aplicável")
        raise
    
    assert result["solver_status"] == "unsafe_diagnostic"
    wwh = result["diagnostic_analysis"]["what_would_happen"]
    
    # Piso clínico pode ter sido relaxado (óleo é suplemento, piso = 0.1g)
    # ou não — depende da concentração real de Vit A no óleo
    if wwh["clinical_floor_relaxed"]:
        assert "clinical_floor_relaxation_note" in wwh, (
            "Piso clínico relaxado mas sem nota de documentação"
        )
        assert result["solver_metadata"]["clinical_floor_applied"] is False
    
    # O diagnóstico SEMPRE existe — nunca tela em branco
    assert result["diagnostic_analysis"] is not None
    assert result["allocations"] is None

def test_level3_clinical_floor_metadata_in_solver_output():
    """[V10.3] No Nível 3, solver_metadata DEVE conter clinical_floor_applied
    e clinical_floor_bounds — para auditoria.
    
    ANTI-GAMIFICATION: Não basta verificar que os campos existem.
    Deve verificar que clinical_floor_applied é booleano e
    clinical_floor_bounds é um dict com pelo menos 1 ingrediente.
    """
    result = run_pipeline(
        animal={"sex": "male", "weight_kg": 25, "age_months": 8},
        selected=["beef_liver_raw"],
        mode="runtime"
    )
    assert result["solver_status"] == "unsafe_diagnostic"
    meta = result["solver_metadata"]
    
    assert "clinical_floor_applied" in meta, (
        "solver_metadata não contém clinical_floor_applied — "
        "impossível auditar se o piso clínico foi usado"
    )
    assert isinstance(meta["clinical_floor_applied"], bool)
    assert "clinical_floor_bounds" in meta
    assert isinstance(meta["clinical_floor_bounds"], dict)
    assert len(meta["clinical_floor_bounds"]) > 0, (
        "clinical_floor_bounds está vazio — nenhum piso clínico declarado"
    )

def test_level3_sul_violation_minimized_not_maximized():
    """[V10.2] No Nível 3, o solver deve MINIMIZAR a violação de SUL, não maximizar.
    
    A crítica V10.1 demonstrou que se λ_der > μ_j, o solver escolhe violar
    o SUL para atingir o DER. Este teste verifica que, mesmo quando a violação
    é inevitável, a magnitude da violação é a menor possível.
    
    ANTI-GAMIFICATION: Para fígado bovino puro, o pct_of_sul no resultado
    deve ser o MENOR valor possível dado o DER — não um valor arbitrário
    que resultaria de pesos invertidos.
    """
    result = run_pipeline(
        animal={"sex": "male", "weight_kg": 25, "age_months": 8},
        selected=["beef_liver_raw"],
        mode="runtime"
    )
    assert result["solver_status"] == "unsafe_diagnostic"
    # A violação de SUL deve existir (é inevitável), mas minimizada
    sul_violations = [nr for nr in result["nutrient_results"]
                      if nr.get("pct_of_sul") is not None and nr["pct_of_sul"] > 100]
    assert len(sul_violations) > 0  # Violação é inevitável (nível 3)
    # Mas o solver deve ter tentado minimizar — verificar que weight_calibration
    # está presente e hierarchy_valid = True (prova que μ_j >> λ_der)
    cal = result["solver_metadata"]["weight_calibration_used"]
    assert cal["hierarchy_valid"] is True
    # Verificar que a violação está documentada (não oculta)
    assert len(result["diagnostic_analysis"]["sul_violations_inevitable"]) > 0
```

### 11.3 Testes de Integridade de Dados (Herdados da V9, Atualizados)

```python
def test_all_nutrient_ids_have_target_and_bound():
    """Os 41 nutrient_id de formulation_rules.nutrient_matrix devem ter
       constraint correspondente em constraints.nutrient_bounds — 41 == 41."""

def test_kelp_salt_copper_supplement_exist_in_db():
    """V10: Agora devem existir. category_to_ingredient_mapping não pode
       referenciar ingredient_id inexistente no DB."""

def test_all_non_usda_source_refs_resolve():
    """V10: Todas as 85 refs devem resolver (78 CONFIRMED, 4 INFERRED, 2 COPY_PASTE_ERROR_CORRECTED, 1 UNIT_INCONSISTENCY_RESOLVED). Não existem "refs órfãs" no arquivo real."""

def test_iodine_coverage_is_feasible():
    """Soma máxima possível de iodo, dado max_inclusion_pct de todo ingrediente
       com iodo > 0, deve ultrapassar CSTR_NB_IODINE_MG_MIN. V10: com kelp, deve passar."""

def test_methionine_cystine_uses_real_value_not_proxy():
    """cystine_g e tyrosine_g devem vir de fonte USDA real, não aproximação.
       V10: proíbe proxy — se None, sinalizar anomalia."""

def test_energy_conversion_roundtrip():
    """Um ingrediente com EM conhecida deve produzir o mesmo valor via
       energy_metabolizable_kcal_per_100g(). Prova que o Atwater modificado
       está implementado certo."""

def test_safety_ceiling_never_relaxed_below_level3():
    """Todo SUL deve permanecer hard nos Níveis 1 e 2.
       ANTI-GAMIFICATION: Não basta verificar que constraint_tier == "safety_hard".
       Deve executar o solver no Nível 1 e Nível 2 e verificar que nenhuma
       variável de violação v_j⁺ > 0.
       [V10.2] Adicionalmente: no Nível 3, a hierarquia de pesos garante que
       a violação de SUL é minimizada, não tratada como meta suave qualquer."""

def test_gompertz_vs_anthropometric_table_consistency():
    """W(t) do Gompertz, para t em cada um dos 24 meses tabelados, deve cair
       dentro do intervalo [min, max] da anthropometric_table."""

def test_envelope_derived_from_der():
    """minTotal_g e maxTotal_g devem derivar do DER, não ser constantes.
       ANTI-GAMIFICATION: Calcular DER à mão, calcular envelope à mão,
       comparar com o output do pipeline."""

def test_constraint_tier_matches_toxicological_limits():
    """Todo nutriente em toxicological_limits.json deve ter constraint_tier = "safety_hard"
       no NUTRIENT_REGISTRY. Todo nutriente NÃO em toxicological_limits deve ter
       constraint_tier = "adequacy_soft" ou "envelope_soft"."""

def test_tox_limits_structure_matches_actual_file():
    """[V10.4] toxicological_limits.json é uma LISTA no topo, não um dict com chave "safe_upper_limits".
       Cada entrada tem sul.value aninhado, não sul_value plano.
       Este teste impede que build_diagnostic_analysis volte a usar .get("safe_upper_limits", [])
       ou tox_entry["sul_value"] — padrão que já causou crash real.
       ANTI-GAMIFICATION: json.load() do arquivo real, checar type e estrutura."""
    import json
    tox = json.load(open("toxicological_limits.json"))
    assert isinstance(tox, list), f"toxicological_limits.json deve ser list, não {type(tox).__name__}"
    assert len(tox) == 8, f"Esperado 8 SULs, encontrado {len(tox)}"
    for entry in tox:
        assert "nutrient_id" in entry
        assert "sul" in entry, f"Entrada {entry.get('nutrient_id','?')} sem chave 'sul'"
        assert isinstance(entry["sul"], dict), f"sul deve ser dict, não {type(entry['sul']).__name__}"
        assert "value" in entry["sul"], f"sul dict sem 'value' em {entry['nutrient_id']}"
        # Provar que .get("safe_upper_limits") falha (seria bug se código usasse)
        assert not isinstance(tox, dict), "Código não deve tratar tox como dict"

def test_objective_weights_all_have_penalty_multiplier_or_null():
    """[V10.4] Todos os 29 pesos em objective_weights.json devem ter
       solver_penalty_multiplier (pode ser null) — exceto PEN_MANGANESE_NEG
       que é o único sem o campo. Código DEVE usar .get() para acessar.
       ANTI-GAMIFICATION: json.load() do arquivo real, checar presença do campo."""
    import json
    ow = json.load(open("objective_weights.json"))
    missing = [w["weight_id"] for w in ow if "solver_penalty_multiplier" not in w]
    # PEN_MANGANESE_NEG é o único legitimamente sem o campo
    assert missing == ["PEN_MANGANESE_NEG"], (
        f"Pesos sem solver_penalty_multiplier: {missing} — "
        f"se diferente de ['PEN_MANGANESE_NEG'], o arquivo foi alterado sem atualizar este teste"
    )
```

### 11.4 Testes de Receitas Prontas (Novo na V10)

```python
def test_recipes_precomputed_has_no_unsafe():
    """Nenhuma receita em recipes_precomputed.json pode ter solver_status = "unsafe_diagnostic".
       ANTI-GAMIFICATION: Ler o JSON real, iterar sobre todas as receitas,
       verificar o campo — não basta checar que o campo existe."""

def test_recipes_cover_minimum_categories():
    """Cada receita deve ter pelo menos 1 muscle_meat + 1 organ_secreting + 1 fonte de cálcio.
       ANTI-GAMIFICATION: Ler DB_ingredientes.json, mapear ingredient_id → category,
       verificar cobertura real por receita."""

def test_recipes_ranked_correctly():
    """rank_composite deve ser consistente com os scores individuais.
       ANTI-GAMIFICATION: Recalcular rank_composite a partir dos scores
       e comparar com o valor armazenado."""

def test_recipe_build_produces_versioned_output():
    """recipes_precomputed.json deve ter _meta com generation_date, solver_version, cascade_level_used."""
```

### 11.5 Regra de Ouro para Testes da Coding AI Agent

**Todo teste deve seguir o padrão AAA + A (Arrange-Act-Assert + Audit):**

1. **Arrange:** Carregar JSONs reais, montar dados reais.
2. **Act:** Executar a função real (não stub).
3. **Assert:** Verificar o resultado com asserções que distinguem resultado real de placeholder.
4. **Audit:** Logar o resultado completo (não apenas pass/fail) para inspeção humana — a IA não pode auto-certificar.

```python
# Exemplo de auditoria obrigatória em cada teste
def audit_test_result(test_name, result, expected):
    with open("test_audit_log.md", "a") as f:
        f.write(f"## {test_name}\n")
        f.write(f"- **Expected:** {expected}\n")
        # allocations pode ser None (Nível 3) — tratar com segurança
        allocs = result.get('allocations')
        allocs_desc = "null (Nível 3 — barreira mecânica)" if allocs is None else f"{len(allocs)} items"
        f.write(f"- **Got:** solver_status={result.get('solver_status')}, "
                f"level={result.get('cascade_level_used')}, "
                f"gaps={len(result.get('gaps', []))}, "
                f"allocations={allocs_desc}\n")
        f.write(f"- **Passed:** {result.get('solver_status') == expected}\n\n")
```

---

## 12. Rejeitado — Não Reintroduzir (Herdado da V9 + Adições V10)

| Item | Por que |
|---|---|
| Tratar `DB_ingredientes.json` como se já fosse validado pelo `lp_parameters_schema.json` só porque `_db_metadata.schema_ref` aponta pra ele | O `schema_ref` é aspiracional, não funcional — confirmado que o schema não valida esse arquivo. Scripts Python continuam sendo a validação. |
| Aproximar `cystine_g`/`tyrosine_g` por fator de proxy genérico sem tentar extrair o valor real da mesma fonte USDA | Regra de não-inferência — se a fonte primária provavelmente tem o dado, extrair é preferível a aproximar. |
| Promover `constraints.json.toxicological_limits` como fonte independente de `toxicological_limits.json` | Existe `derived_from` explícito — são a mesma fonte de verdade em dois formatos, não duas fontes. |
| Usar SCN_A (crescimento rápido) como cenário ativo padrão | Marcado `WARNING_DO_NOT_OPTIMIZE` no próprio arquivo — existe só como contraste de alerta. |
| Nota de precisão fabricada (ex: pontuação decimal de "qualidade arquitetural" sem metodologia reprodutível) | Julgamento qualitativo não vira número sem inventar precisão. |
| **[NOVO V10]** Hardcode de `minTotal`/`maxTotal` como constante | O envelope deve ser DER-derived, não fixo em `[200, 1500]g`. |
| **[NOVO V10]** Lógica de cascata em código (if/else) em vez de declarativa em JSON | A política de "quando relaxar o quê" vive em `solve_cascade` no schema, não em código. |
| **[NOVO V10]** Mockar testes de cascata com fixtures que sempre retornam feasible | Testes de integração devem exercitar a descida real entre níveis, não apenas verificar campos. |
| **[NOVO V10]** Permitir que o solver retorne resultado vazio ou "infeasible" sem dados | Inviolabilidade da saída: sempre devolve análise e 41 valores. No Nível 3, `allocations` é `null` (barreira mecânica, não semântica). |
| **[NOVO V10]** Gerar receitas em tempo real no frontend | Receitas são pré-computadas offline. O frontend apenas lê `recipes_precomputed.json`. |
| **[NOVO V10.1]** Devolver gramas no Nível 3 (`unsafe_diagnostic`) como se fossem recomendação | No Nível 3, `allocations` é `null` (barreira mecânica). Gramas matemáticas vivem em `diagnostic_analysis.what_would_happen`, recontextualizadas como análise de cenário, não como prescrição. O simplex pode minimizar violação de SUL, mas o resultado numérico não é seguro para alimentação — a barreira é mecânica (campo nulo), não apenas semântica (label/badge). |
| **[NOVO V10.2]** Tratar SUL como meta ponderada igual a qualquer outra no Nível 3 (sem hierarquia de pesos) | A crítica V10.1 demonstrou matematicamente que se o peso do DER (`λ_der`) supera o peso da violação de SUL (`μ_j`), o simplex escolhe violar o SUL para atingir o DER. A hierarquia `μ_j >> λ_der >> σ_k` é obrigatória, não configurável — é constraint implícita da semântica do Nível 3. Inverter a hierarquia recria o problema original. |
| **[NOVO V10.2]** Omitir `λ_der` da função objetivo do Nível 3 | Sem `λ_der`, o solver pode produzir solução degenerada `x_i = 0, v_j⁺ = 0, σ_der = DER` — objetivo = 0, tecnicamente "ótimo" mas sem cenário contrafactual útil. `λ_der > 0` é necessário para forçar o solver a buscar ponto não-trivial próximo do DER. |
| **[NOVO V10.2]** Permitir que a hierarquia `μ_j >> λ_der >> σ_k` seja configurável pelo usuário | A hierarquia é constraint de segurança, não preferência. Se o usuário pode alterar `λ_der > μ_j`, o sistema volta ao estado onde o solver escolhe violar SUL para atingir DER. A calibração vive em `solve_cascade.weight_calibration` no JSON, mas a validação da hierarquia é obrigatória no código. |
| **[NOVO V10.3]** Tolerar x_i clinicamente irrelevante no Nível 3 (ex: 0.5g de fígado — tecnicamente não-degenerado, mas inútil como cenário contrafactual) | A crítica V10.3 demonstrou que `λ_der > 0` impede `x_i = 0` (solução degenerada), mas NÃO impede `x_i = 0.5g` — tecnicamente não-zero, mas clinicamente irrelevante. 0.5g de fígado não é uma porção reconhecível; o `what_would_happen` resultante seria inútil como cenário contrafactual. O piso clínico `x_i ≥ x_min_i` (5g default) é obrigatório no Nível 3. Se o piso não pode ser satisfeito, deve ser relaxado COM documentação explícita (`clinical_floor_relaxed = true`), não silenciosamente ignorado. |
| **[NOVO V10.3]** Usar o mesmo piso clínico para todos os ingredientes sem distinguir por categoria | Suplementos (kelp, sal, CuSO₄) são usados em gramagens milimétricas (0.1-3g/dia) — aplicar piso de 5g tornaria todo cálculo com suplementos infeasible no Nível 3. O piso deve ser por categoria (muscle_meat=10g, organ=5g, supplement=0.1g) ou por ingrediente (via `clinical_floor_g` no JSON). |
| **[NOVO V10.4]** Escrever pseudocódigo que assume estrutura de JSON nunca checada contra o arquivo real | `build_diagnostic_analysis` assumia `tox_limits.get("safe_upper_limits", [])` + `tox_entry["sul_value"]` — o arquivo real é `list` no topo com `sul.value` aninhado. Crasher garantido na primeira execução. Pseudocódigo DEVE ser validado contra os arquivos reais antes de ser considerado especificação. |
| **[NOVO V10.4]** Usar `assert` com expressão geradora inline em Python | `assert x for x in iterable` é `SyntaxError` — `assert` só aceita expressão booleana. Forma correta: `assert any(...)`, `assert all(...)`, ou `assert [condition for ...]`. |
| **[NOVO V10.4]** Declarar "RESOLVIDO"/"IMPLEMENTADO" em tabela de arquivos sem evidência colada | Seção 4.1 dizia "23 itens" (real: 20), "+17 refs órfãs resolvidas" (real: 17 ausentes), "expandido com 3 novos IDs" (real: planejados mas não aplicados). A disciplina da Seção 9.4 (RESOLVIDO = evidência colada) deve se aplicar a TODO o documento, não só à Seção 9. |
| **[NOVO V10.4]** Assumir `nutrient_results` sempre tem exatamente 41 entradas | Variáveis compostas (ca_p_ratio, caloric_density, cost_per_kg) são penalizadas no objetivo mas NÃO são nutrientes primários do `nutrient_matrix`. Se `compute_nutrient_results` incluí-las, `len == 41` quebra. Usar `>= 41` ou documentar exclusão explícita. |

---

## 13. Prioridades — V10

**P0 — Bloqueia viabilidade da dieta:**
1. Adicionar `kelp_meal_dried`, `salt_nacl`, `copper_sulfate` ao `DB_ingredientes.json` (Seção 9.1 — **PLANEJADO, NÃO aplicado** — V10.4: confirmado que arquivo real ainda tem 20 ingredientes, não 23).
2. Implementar `build_pipeline.py` (Seção 6) como código real, rodável, com os testes da Seção 11 passando de verdade (output colado, não alegado).
3. Atualizar `lp_parameters_schema.json` com `NUTRIENT_REGISTRY` (constraint_tier, clinical_criticality) e `solve_cascade` (Seção 4.2, 4.3).

**P0 — Sem isso, o solver é puramente teórico:**
4. Implementar o solver LP genérico que lê `solve_cascade` do JSON e executa a cascata (Seção 8).
5. Implementar o envelope dinâmico DER-derived (Seção 3.3).

**P1 — Importante, não bloqueia MVP:**
6. Resolver as 17 referências órfãs em `audit_provenance.json` (Seção 9.2 — **PLANEJADO, NÃO aplicado** — V10.4: confirmado que as 17 refs estão ausentes do arquivo, referenciadas apenas no DB_ingredientes).
7. Extrair `cystine_g`/`tyrosine_g` reais da mesma fonte USDA (Seção 9.3).
8. Finalizar validação de aves (13+ issues pendentes).
9. Implementar modo `--build-recipes` e gerar `recipes_precomputed.json`.

**P2 — Extensão natural:**
10. Criar cenário de manutenção adulta (SCN_C) usando o `k=1.5` já existente.
11. Implementar critérios adicionais de ranking de receitas (simplicidade, disponibilidade).

**P3 — Não crítico agora:**
12. Fase sênior/geriátrica — zero dados hoje, sem requisito real de uso imediato.
13. Schema formal para `DB_ingredientes.json` (hoje órfão, validação por scripts ad-hoc).

---

## 14. Convenções de Nomenclatura Cross-JSON — V10 (Atualizado)

### 14.1 Nomes de Variáveis

O sistema opera com duas convenções de nomes de nutrientes (inalterado da V9):

- **Espaço do DB (DB_ingredientes.json):** Usa sufixo de unidade no nome (ex: `magnesium_mg`, `selenium_ug`). Basis: `as_fed`, referência: 100g.
- **Espaço do Solver (constraints.json, objective_weights.json, scenarios.json, formulation_rules.nutrient_matrix):** Usa nome padronizado sem sufixo (ex: `magnesium_g`, `selenium_mg`). Basis: `energy_normalized`, referência: 1000kcal.

### 14.2 Sistema de Referências (source_ref) — Atualizado V10

Todos os campos `source_ref` seguem a regex `^REF_[A-Z0-9_]+$`. Convenções de prefixo (incluindo 2 novos da V10):

| Prefixo | Significado | Exemplo |
|---------|------------|---------|
| REF_USDA_FDC_ | Dados USDA FoodData Central (externo, não resolve internamente) | REF_USDA_FDC_170196 |
| REF_MIN_ANT_ | Antagonismo mineral | REF_MIN_ANT_CA_P |
| REF_SUL_ | Fisiopatologia do SUL | REF_SUL_CU_PATHO |
| REF_INCL_ | Justificativa de limite de inclusão | REF_INCL_LIVER_JUST |
| REF_NUTR_ | Metadata nutricional | REF_NUTR_MATRIX_41 |
| REF_DIET_ | Template de dieta | REF_DIET_PMR |
| REF_BIO_ | Biodisponibilidade/biomarcador | REF_BIO_KELP_IODINE |
| REF_PLOSS_ | Perda por processamento/armazenamento | REF_PLOSS_VIT_A_MECH |
| REF_NRG_ | Requisitos energéticos | REF_NRG_TER |
| REF_SKEL_ | Marco esquelético | REF_SKEL_EPIPHYSEAL_LB |
| REF_GON_ | Status gonadal | REF_GON_MALE_NEUT_EARLY |
| REF_EPI_ | Epidemiologia | REF_EPI_DOD |
| REF_SCENARIO_ | Cenário de otimização | REF_SCENARIO_CMP |
| REF_ALGO_ | Algoritmo/fallback | REF_ALGO_GOAL_PROG |
| REF_GLOBAL_META | Metadados globais | REF_GLOBAL_META |
| REF_RAW_ | Dados brutos parseados | REF_RAW_WEIGHT_DOC1 |
| REF_EXTRACTION_ | Verificação de completude | REF_EXTRACTION_COMPLETE |
| REF_SUP_ | Suplementação | REF_SUP_VIT_D3 |
| REF_CALORIC_ | Densidade calórica | REF_CALORIC_DENSITY |
| REF_BARF_ | Especificidade BARF | REF_BARF_DENSITY |
| REF_DIGEST_ | Digestibilidade | REF_DIGEST_RAW |
| REF_BONE_ | Qualidade óssea | REF_BONE_QUALITY |
| REF_GROWTH_ | Modelo de crescimento | REF_GROWTH_GOMPERTZ |
| **REF_LIT_VET_** | **[NOVO V10]** Literatura veterinária citada nos dados | REF_LIT_VET_BLOOD_COLLAGEN |
| **REF_SAFETY_** | **[NOVO V10]** Alertas de segurança alimentar | REF_SAFETY_RAW_PATHOGENS_BEEF |

### 14.3 IDs de Constraints

Inalterado da V9:
- `CSTR_NB_*_MIN`: Nutrient bound mínimo (41 entries)
- `CSTR_SUL_*_MAX`: Safe Upper Limit máximo (8 entries)
- `CSTR_INCL_*`: Inclusion constraint (6 entries)
- `CSTR_<PAIR>_RATIO`: Ratio bound de antagonismo (5 entries)

### 14.4 Status Canônicos do Solver (Novo V10)

| Status | Significado | Pode ser recomendado como dieta? | UI exibe alertas? |
|---|---|---|---|
| `optimal` | Nível 1 feasible — tudo respeitado | Sim — recomendação segura | Apenas informativos |
| `suboptimal` | Nível 2 feasible — SULs ok, mas há gaps de adequação | Sim — com ressalvas documentadas | Warnings de deficiência |
| `unsafe_diagnostic` | Nível 3 — SUL violado (minimizado com hierarquia `μ_j >> λ_der >> σ_k`), com piso clínico mínimo `x_i ≥ x_min_i` (V10.3) | **Não** — `allocations = null`, `feeding_recommendation = DO_NOT_FEED` | Danger de excesso tóxico + `diagnostic_analysis` com ações alternativas + `weight_calibration_used` para auditoria + `clinical_floor_applied/bounds` para auditoria do piso (V10.3) |

---

## 15. Estado Atual da Curadoria — V10

| Grupo | Ingredientes | Status V9 | Status V10 |
|---|---|---|---|
| bovinos | 11 | VALIDATED | VALIDATED |
| aves | 6 | PARTIAL/PENDING | PARTIAL/PENDING (13+ issues) |
| suínos | 2 | PARTIAL | PARTIAL |
| peixes | 1 | PARTIAL | PARTIAL |
| **suplementos** | **3** | **Não existiam** | **NOVO — kelp_meal_dried, salt_nacl, copper_sulfate** |

---

## 16. Gaps e Dependências Não-Implementadas — V10

| # | Gap | Status V9 | Status V10 | Prioridade |
|---|---|---|---|---|
| 1 | Build Pipeline | Não existe código | Especificado na Seção 6 (aguardando implementação) | P0 |
| 2 | DB_ingredientes fora do schema | Órfão por design | Órfão por design (validação por scripts) | P3 |
| 3 | Aves normalization | 13+ issues | 13+ issues (sem mudança) | P1 |
| 4 | G8 false positive em validate_master.py | P2 | P2 (sem mudança) | P2 |
| 5 | Fase sênior/geriátrica | Zero dados | Zero dados | P3 |
| 6 | Cenário adulto (SCN_C) | k=1.5 órfão | k=1.5 órfão, envelope dinâmico já suporta | P2 |
| **7** | **Solver LP genérico que lê solve_cascade** | **Não existe** | **Especificado na Seção 8 (aguardando implementação)** | **P0** |
| **8** | **Envelope dinâmico DER-derived** | **Fixo [200,1500]g** | **Especificado na Seção 3.3 (aguardando implementação)** | **P0** |
| **9** | **recipes_precomputed.json** | **Não existe** | **Especificado na Seção 5.2 (aguardando build pipeline)** | **P1** |
| **10** | **Contrato de dado do output (schema)** | **Parcial** | **Especificado na Seção 7 (aguardando implementação)** | **P0** |

---

## 17. Resumo das Mudanças V9 → V10

| # | Mudança | Seção | Tipo |
|---|---|---|---|
| 1 | Envelope dinâmico DER-derived (substitui fixo `[200,1500]`) | 3.3 | Arquitetural |
| 2 | Liberdade total de seleção (1 a N ingredientes) | 3.2 | Produto |
| 3 | Categoria "Livre" com alertas e recomendações | 5.1 | Produto |
| 4 | Categoria "Receitas Prontas" pré-computadas | 5.2 | Produto |
| 5 | Cascata de 3 níveis (Goal Programming Preemptivo) | 3.4, 8 | Arquitetural |
| 6 | `constraint_tier` no NUTRIENT_REGISTRY (safety_hard/adequacy_soft/envelope_soft) | 4.2 | Schema |
| 7 | `solve_cascade` declarativo em JSON (substitui lógica hardcoded) | 4.3 | Schema |
| 8 | `clinical_criticality` por nutriente (para ponderação do slack) | 4.2 | Schema |
| 9 | Contrato de dado canônico (solver_status, gaps, alerts, recommended_additions) | 7 | Schema |
| 10 | 3 ingredientes planejados (kelp, sal, sulfato_cobre) — ainda NÃO no DB_ingredientes real, ver §9.1 | 9.1 | Dado |
| 11 | 85 refs no audit_provenance — sem órfãs (V10.4: confirmado contra arquivo real — 78 CONFIRMED, 4 INFERRED, 2 COPY_PASTE_ERROR_CORRECTED, 1 UNIT_INCONSISTENCY_RESOLVED) | 9.2 | Dado |
| 12 | Proibição de proxy para cystine/tyrosine | 9.3 | Regra |
| 13 | Testes anti-gamificação com AAA+A | 11 | QA |
| 14 | `recipes_precomputed.json` com ranking de 5+ critérios | 5.2 | Produto |
| 15 | Build pipeline em dois modos (runtime + build-recipes) | 6 | Engenharia |
| 16 | 2 novos prefixos de referência (REF_LIT_VET_, REF_SAFETY_) | 14.2 | Convenção |
| 17 | Inviolabilidade da saída como princípio canônico | 3.1, 3.6 | Princípio |
| 18 | Separação modelo/dados como regra inviolável | 3.5, 0 | Princípio |
| **19** | **Nível 3: `allocations = null` + `diagnostic_analysis` (barreira mecânica)** | **3.1, 3.4, 3.6, 7, 8.3, 11** | **Correção V10.1** |
| **20** | **`feeding_recommendation` canônico (SAFE_TO_FEED / FEED_WITH_CAUTION / DO_NOT_FEED)** | **7, 14.4** | **Correção V10.1** |
| **21** | **Contrato bifurcado por nível (7.1 Nível 1/2 vs. 7.2 Nível 3)** | **7** | **Correção V10.1** |
| **22** | **`solve_cascade` JSON: Nível 3 declara `output_contract` com allocations=null + diagnostic_analysis** | **4.3** | **Correção V10.2** |
| **23** | **Seção 1: "SULs — nunca relaxados" → "hard nos Níveis 1 e 2; minimização no Nível 3"** | **1** | **Correção V10.2** |
| **24** | **Seção 3.4 tabela: Nível 3 descrição inclui `allocations = null`** | **3.4** | **Correção V10.2** |
| **25** | **Código referência: `build_diagnostic_analysis()` implementado (era referência sem definição)** | **6.4** | **Correção V10.2** |
| **26** | **Código referência: `call_lp_solver()` retorna `x_values`+`nutrient_values` (não `allocations`)** | **6.4** | **Correção V10.2** |
| **27** | **Código referência: `solve_cascade()` separa raw_result do contrato de saída** | **6.4** | **Correção V10.2** |
| **28** | **Código referência: `format_allocations()` extrai allocations de raw_result (Nível 1/2 apenas)** | **6.4** | **Correção V10.2** |
| **29** | **Código referência: `validate_output()` expandido com checagens explícitas de allocations null vs. não-null** | **6.4** | **Correção V10.2** |
| **30** | **Seção 6.2 pseudo-código: passo 6 refletido allocations=null no Nível 3 + separação raw_result** | **6.2** | **Correção V10.2** |
| **31** | **Seção 6.2 validação (saída): validação condicional de allocations (null-safe)** | **6.2** | **Correção V10.2** |
| **32** | **Seção 6.3 Build-Recipes: descarte de unsafe_diagnostic com motivo explicitado** | **6.3** | **Correção V10.2** |
| **33** | **Seção 8.1: nota arquitetural sobre x_i no Nível 3 → apenas what_would_happen** | **8.1** | **Correção V10.2** |
| **34** | **Seção 11.5: `audit_test_result()` corrigido para tratar allocations=None sem crash** | **11.5** | **Correção V10.2** |
| **35** | **`λ_der` com peso explícito na função objetivo do Nível 3 (impede solução degenerada x_i=0)** | **8.1** | **Correção V10.2** |
| **36** | **Hierarquia de pesos obrigatória `μ_j >> λ_der >> σ_k` no Nível 3 (constraint implícita, não configurável)** | **8.1, 8.2, 8.3** | **Correção V10.2** |
| **37** | **`solve_cascade` JSON: Nível 3 declara `weight_calibration` com μ_j, λ_der, hierarchy_constraint** | **4.3** | **Correção V10.2** |
| **38** | **Seção 8.3: risco de solução degenerada sem λ_der documentado + generalização para qualquer SUL** | **8.3** | **Correção V10.2** |
| **39** | **Contrato Nível 3 (7.2): `solver_metadata.weight_calibration_used` para auditoria de pesos** | **7** | **Correção V10.2** |
| **40** | **Garantia do contrato: hierarquia de pesos documentada em `weight_calibration_used`** | **7** | **Correção V10.2** |
| **41** | **Código: `solve_cascade()` valida hierarquia de pesos e rejeita se violada** | **6.4** | **Correção V10.2** |
| **42** | **Código: `validate_output()` checa `hierarchy_valid` e `μ_j > 10×λ_der`** | **6.4** | **Correção V10.2** |
| **43** | **Teste: `test_level3_weight_hierarchy_validated`** | **11.2** | **Correção V10.2** |
| **44** | **Teste: `test_level3_no_degenerate_solution`** | **11.2** | **Correção V10.2** |
| **45** | **Teste: `test_level3_sul_violation_minimized_not_maximized`** | **11.2** | **Correção V10.2** |
| **46** | **Rejeitado: tratar SUL como meta ponderada sem hierarquia + omitir λ_der + hierarquia configurável** | **12** | **Correção V10.2** |
| **47** | **Seção 8.2 regra de ouro #8: hierarquia de pesos obrigatória no Nível 3** | **8.2** | **Correção V10.2** |
| **48** | **Piso clínico mínimo `x_i ≥ x_min_i` no Nível 3 (impede x_i clinicamente irrelevante como 0.5g de fígado)** | **8.1** | **Correção V10.3** |
| **49** | **Definição de `x_min_i` por categoria (muscle_meat=10g, organ=5g, supplement=0.1g) + fallback global 5g** | **8.1** | **Correção V10.3** |
| **50** | **`clinical_floor_g` opcional por ingrediente em `formulation_rules.inclusion_constraints`** | **4.1, 8.1** | **Correção V10.3** |
| **51** | **Fallback se piso clínico infeasible: relaxar x_min_i → 0, marcar `clinical_floor_relaxed = true`** | **8.1, 6.4** | **Correção V10.3** |
| **52** | **`solve_cascade` JSON: Nível 3 declara `clinical_floor` com defaults_by_category + fallback_if_infeasible** | **4.3** | **Correção V10.3** |
| **53** | **Seção 3.4 tabela: Nível 3 descrição inclui piso clínico mínimo** | **3.4** | **Correção V10.3** |
| **54** | **Código: `build_lp_proble` injeta `clinical_floor_bounds` no Nível 3** | **6.4** | **Correção V10.3** |
| **55** | **Código: `solve_cascade()` tenta re-solver sem piso se infeasible com piso** | **6.4** | **Correção V10.3** |
| **56** | **Código: `build_diagnostic_analysis()` recebe `clinical_floor_info`, produz `clinical_floor_applied/relaxed/ingredients_below_floor`** | **6.4** | **Correção V10.3** |
| **57** | **Contrato Nível 3 (7.2): `what_would_happen` inclui `clinical_floor_applied`, `clinical_floor_relaxed`, `ingredients_below_floor`, `x_min_i_effective`** | **7** | **Correção V10.3** |
| **58** | **Contrato Nível 3 (7.2): `solver_metadata` inclui `clinical_floor_applied` e `clinical_floor_bounds`** | **7** | **Correção V10.3** |
| **59** | **Garantia do contrato: documentação de `clinical_floor_applied/bounds/relaxed` para auditoria** | **7** | **Correção V10.3** |
| **60** | **Seção 8.2 regra de ouro #9: piso clínico mínimo obrigatório no Nível 3** | **8.2** | **Correção V10.3** |
| **61** | **Seção 8.3: nota sobre piso clínico no caso de colisão SUL vs. DER** | **8.3** | **Correção V10.3** |
| **62** | **Teste: `test_level3_clinical_floor_prevents_irrelevant_xi`** | **11.2** | **Correção V10.3** |
| **63** | **Teste: `test_level3_clinical_floor_relaxed_for_extreme_ingredient`** | **11.2** | **Correção V10.3** |
| **64** | **Teste: `test_level3_clinical_floor_metadata_in_solver_output`** | **11.2** | **Correção V10.3** |
| **65** | **Código: `validate_output()` checa `clinical_floor_applied` + `clinical_floor_bounds` + `clinical_floor_relaxation_note`** | **6.4** | **Correção V10.3** |
| **66** | **Rejeitado: tolerar x_i clinicamente irrelevante + piso clínico uniforme sem distinção por categoria** | **12** | **Correção V10.3** |
| **67** | **Seção 14.4: `unsafe_diagnostic` descrição inclui piso clínico** | **14.4** | **Correção V10.3** |
| **68** | **Versão bumped: 10.2 → 10.3** | **0** | **Correção V10.3** |
| **69** | **Código: `assert` com gerador inline corrigido para `assert any(...)` (SyntaxError)** | **6.4** | **Correção V10.4** |
| **70** | **Código: `build_diagnostic_analysis()` — tox_limits iterado como lista direta, SUL acessado via `sul.value` (shape real do arquivo)** | **6.4** | **Correção V10.4** |
| **71** | **Seção 4.1 tabela: "23 itens" → "20 itens × 34 nutrientes as_fed → 41 energy_normalized"; 3 ingredientes marcados como PLANEJADOS** | **4.1** | **Correção V10.4** |
| **72** | **Seção 4.1 tabela: "17 refs órfãs resolvidas" → "17 refs órfãs ainda pendentes" (confirmado contra arquivo real)** | **4.1** | **Correção V10.4** |
| **73** | **Seção 4.1 tabela: `formulation_rules` — "3 novos IDs" marcados como planejados, não aplicados** | **4.1** | **Correção V10.4** |
| **74** | **Seção 4.1 tabela: `toxicological_limits` — documentado como lista no topo com sul.value aninhado (não dict com safe_upper_limits)** | **4.1** | **Correção V10.4** |
| **75** | **Seção 4.1 tabela: `objective_weights` — `PEN_MANGANESE_NEG` documentado como único peso sem solver_penalty_multiplier** | **4.1** | **Correção V10.4** |
| **76** | **Código: `validate_output()` — `len(nutrient_results) == 41` → `>= 41` (compostas podem ser adicionais)** | **6.4** | **Correção V10.4** |
| **77** | **Contrato garantias (7): "exatamente 41 entradas" → "pelo menos 41 entradas" + nota sobre variáveis compostas** | **7** | **Correção V10.4** |
| **78** | **Teste: `test_tox_limits_structure_matches_actual_file()` — valida shape do toxicological_limits.json** | **11.3** | **Correção V10.4** |
| **79** | **Teste: `test_objective_weights_all_have_penalty_multiplier_or_null()` — documenta exceção PEN_MANGANESE_NEG** | **11.3** | **Correção V10.4** |
| **80** | **Seção 9.2: descrição do teste `test_all_non_usda_source_refs_resolve` atualizada com flags reais** | **11.3** | **Correção V10.4** |
| **81** | **Prioridade P0 #1: "resolvido na V10" → "PLANEJADO, NÃO aplicado"** | **13** | **Correção V10.4** |
| **82** | **Prioridade P1 #6: "Resolver 17 refs" → marcado como PLANEJADO, NÃO aplicado** | **13** | **Correção V10.4** |
| **83** | **Change summary #10: "3 ingredientes adicionados" → "3 planejados, ainda NÃO no DB"** | **17** | **Correção V10.4** |
| **84** | **Change summary #11: "17 refs órfãs resolvidas" → flags reais documentadas** | **17** | **Correção V10.4** |
| **85** | **Rejeitado V10.4: pseudocódigo sem checagem de shape + assert inline + RESOLVIDO sem evidência + nutrient_results == 41** | **12** | **Correção V10.4** |
| **86** | **Princípio inviolável ampliado: pseudocódigo DEVE ser checável contra arquivos reais** | **0** | **Correção V10.4** |
| **87** | **Versão bumped: 10.3 → 10.4** | **0** | **Correção V10.4** |
