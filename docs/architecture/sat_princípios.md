# sat_princípios — Lógicas e Princípios Canônicos V10

**v10.4** · ← `indice_plano_central.md` (canônico) · `../../README.md`

**Responsibility:** 6 canonical principles (§3.1-§3.6): output inviolability, selection freedom, dynamic envelope, relaxation cascade, model/data separability, acute toxicity vs adequacy.

**Depends on:** None (atomic) · **Referenced by:** sat_dados_schema (§3.5), sat_solver_contrato (§3.4, §3.6), sat_pipeline_codigo (§3.5), sat_pipeline_fluxo (§3.3)

**Load when:** architecture design · review principles · assess principle violation

> **Context:** **Hot satellite** — referenced by 6/6 of other satellites. Pin in `.opencode/rules.md`.

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

> **See also:** full output contract in `sat_solver_contrato:§7` (§7.1 Level 1/2 with allocations, §7.2 Level 3 with `allocations=null` + `diagnostic_analysis`). Cascade mathematical formulation in `sat_solver_contrato:§8.1`. Canonical SUL vs DER collision case (where Level 3 is inevitable) in `sat_solver_contrato:§8.3`.

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

**IMPLEMENT:** 3 levels instead of "all hard" or "all soft". Solver only descends to next level if previous is genuinely *infeasible* — never skips to end. (Gold standard AMPL/GAMS, confirmed by IJCAI 2025 survey for AI-managed data.)

**FORBID:** skipping Level 1 → Level 3 without trying Level 2. Test `test_cascade_never_skips_level_2()` must fail if this occurs.

|Nível|O que tenta|O que relaxa|Status do resultado|
|---|---|---|---|
| **Nível 1** | TUDO respeitado: SULs (hard) + pisos de adequação (hard) + DER/densidade/Ca:P (com slack) | Nada | `optimal` |
| **Nível 2** | SULs (hard) continuam. Pisos de adequação (proteína, minerais, vitaminas — os mínimos) relaxados via slack ponderado por `clinical_criticality` | `adequacy_soft` | `suboptimal` |
| **Nível 3** | Minimiza violação de SUL aproximando DER. **`allocations=null`** (diagnóstico, não prescrição). **Pesos:** `μ_j (100k) >> λ_der (1k) >> σ_k (1-10)` (impede violar SUL por DER — ver §8.1). **Piso clínico:** `x_i ≥ x_min_i` (5g) impede cenário irrelevante (ex: 0.5g fígado). Se solver não atingir `x_min_i` para nenhum ingrediente, `what_would_happen` documenta razão + magnitude da violação. | `adequacy_soft` + `safety_hard` | `unsafe_diagnostic` |

**Contrato de dado do Nível 3 (diagnóstico, não prescrição):**
- `allocations` = **`null`** — não existem gramas recomendadas. Barreira mecânica, não semântica: nenhum consumidor downstream (API/UI/usuário) pode acidentalmente interpretar como instrução de alimentação.
- `diagnostic_analysis` substitui `allocations` — contém: (a) razão matemática da infeasibilidade, (b) violações de SUL inevitáveis com magnitude, (c) cenário contrafactual "o que aconteceria se", (d) ações alternativas recomendadas.
- 41 valores nutricionais presentes em `nutrient_results` — para diagnóstico/auditoria, não alimentação.
- `feeding_recommendation = "DO_NOT_FEED"` — UI deve checar antes de exibir gramagem.
- `optimal`/`suboptimal` = recomendação real (`feeding_recommendation ∈ ["SAFE_TO_FEED", "FEED_WITH_CAUTION"]`).
- `unsafe_diagnostic` = dado real, cálculo real, nunca omitido — mas estruturalmente inservível como instrução de alimentação. Decisão de contrato (pré-solver/schema), não de UI.

### 3.5 Princípio da Separabilidade Modelo/Dados

**IMPLEMENT:** a política de "quando relaxar o quê" deve ser declarada em **dado** (JSON), não em código. O motor do solver é genérico — lê `solve_cascade` de `lp_parameters_schema.json` e executa os níveis na ordem declarada. Trocar a política (ex: adicionar Nível 4, mudar pesos de relaxamento) é editar JSON, não reescrever código.

**FORBID:** there must be no `solver.ts` or any hardcoded logic file other than the 9+1 JSONs listed in `sat_dados_schema:§4.1`.

**VERIFY:** test `test_no_hardcoded_cascade_logic()` — searches for `if level ==` in solver Python code and fails if found.

### 3.6 Princípio da Toxicidade Aguda vs. Falta de Adequação

- **Toxicidade Aguda (SULs):** Se inevitavelmente alcançada (Nível 3), o sistema sinaliza `unsafe_diagnostic` com `allocations = null` e `feeding_recommendation = "DO_NOT_FEED"`. No **Modo Livre**, a toxicidade aguda é a **única** situação em que o sistema não devolve gramas recomendadas — e apenas se o usuário estiver tentando otimizar uma combinação que ultrapassa irrecuperavelmente um SUL (ex: óleo de fígado de bacalhau isolado, onde caloria e Vitamina A são inseparáveis; ou fígado bovino puro → vitamina A a 40.000 IU, SUL = 9.375 IU). A negação é explícita, documentada em `diagnostic_analysis`, e substituída por análise de cenário + ações alternativas — nunca silenciosa.
- **Modo Livre (Não Tóxico):** Se não for tóxico, o sistema **não deve negar**. Deve recomendar proporção de proteína, fonte de cálcio, carboidratos, etc. Exemplo prático: usuário seleciona apenas "filé mignon" — nenhum cachorro passou mal agudamente; faltou saúde por comer apenas filé mignon em um dia. O solver não bloqueia, apenas processa e alerta a falta de adequação.

### 3.7 Princípio da Integridade Dimensional e da Evidência Executável

Antes de qualquer otimização, o sistema deve tornar explícita a unidade e a base de cada valor: coeficientes nutricionais, variável de decisão, metas, SULs, DER, slacks e resultados. A matriz em `energy_normalized/1000kcal` é uma representação de dados; ela **não** pode ser multiplicada diretamente por `x_i` em gramas. O compilador do problema deve converter tudo para uma base diária compatível, por exemplo:

```
nutrient_per_g[i,j] = nutrient_per_1000kcal[i,j] × EM_kcal_per_g[i] / 1000
target_per_day[j]   = target_per_1000kcal[j] × DER_kcal / 1000
sul_per_day[j]      = sul_per_1000kcal[j] × DER_kcal / 1000
```

Não basta a fórmula parecer plausível: ela precisa passar teste de dimensionalidade e round-trip com dados reais. Um JSON, fonte ou campo ausente não autoriza a IA a preencher com aproximação; produz `data_incomplete` + anomalia auditável e bloqueia recomendação. Pseudocódigo em Markdown não é implementação e não pode ser marcado como executado sem arquivo fonte, comando e saída literal.

---

## ✅ Definition of Done — sat_princípios

Implementation is complete when ALL items below are true:

- [ ] For any selection of 1 to N ingredients, the solver returns analysis with 41 nutritional values (never blank screen).
- [ ] Level 1/2 returns `allocations` with grams; Level 3 returns `allocations = null` + `diagnostic_analysis`.
- [ ] `feeding_recommendation` respects mapping: `optimal → SAFE_TO_FEED`, `suboptimal → FEED_WITH_CAUTION`, `unsafe_diagnostic → DO_NOT_FEED`.
- [ ] Envelope `[minTotal, maxTotal]` derives from animal DER (not hardcoded).
- [ ] Cascade is declarative in `solve_cascade[]` in JSON; engine only reads and executes (no policy if/else in code).
- [ ] Free Mode never blocks for "insufficient selection" — only for acute toxicity (irrecoverable SUL).
- [ ] Test `test_solver_never_returns_empty()` (in `sat_solver_contrato:§A`) passes.
- [ ] Every LP coefficient, decision variable, target, SUL, and output has compatible unit/basis verified by dimensional tests.
- [ ] Missing real data/source/unit yields an auditable `data_incomplete` result, never an inferred numeric value or a feeding recommendation.

**Anti-gamification:** each item above must be verified by test that loads real JSONs, not fixtures. See `sat_testes_consolidado` (Golden Rule AAA+A).

---
