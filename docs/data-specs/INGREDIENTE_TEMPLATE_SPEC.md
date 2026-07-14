# GSD Diet Calc — Especificação de Ingrediente (Template para Pesquisa IA)

Este documento é o **contrato exato** para criar arquivos de ingredientes do LP solver de dieta canina (Pastor Alemão filhote, AAFCO growth). Bovinos.json é o **arquivo-referência validado 100%** contra o schema `lp_parameters.schema.json`.

---

## 1. ARQUIVO — ESTRUTURA TOP-LEVEL

```json
[
  { /* ingredient 1 */ },
  { /* ingredient 2 */ },
  ...
]
```

- **Tipo**: JSON Array (`[]`) de objetos `Ingredient`
- **Encoding**: UTF-8
- **Indentação**: 2 espaços
- **Sem trailing commas**

---

## 2. INGREDIENTES OBRIGATÓRIOS POR PROTEÍNA

Cada arquivo de proteína (Bovinos, Aves, Suínos, Peixes, etc.) DEVE conter os seguintes **ingredientes obrigatórios** mapeados por categoria:

### 2.1 Muscle Meat (músculo)
| # | ingredient_id padrão | Descrição | requires_cooking | TIER típico |
|---|---|---|---|---|
| 1 | `{animal}_muscle_raw` | Corte primário (ex: patinho/acém para bovino, peito para ave) | `false` | TIER_A |

### 2.2 Muscle Organ (órgão muscular)
| # | ingredient_id padrão | Descrição | requires_cooking | TIER típico |
|---|---|---|---|---|
| 2 | `{animal}_heart_raw` | Coração | `false` | TIER_A |
| 3 | `{animal}_tongue_raw` | Língua | `true` | TIER_B |

### 2.3 Organ Secreting (órgão secretor)
| # | ingredient_id padrão | Descrição | requires_cooking | TIER típico |
|---|---|---|---|---|
| 4 | `{animal}_liver_raw` | Fígado | `false` | TIER_A |
| 5 | `{animal}_kidney_raw` | Rim | `false` | TIER_A |
| 6 | `{animal}_spleen_raw` | Baço | `false` | TIER_B |

### 2.4 Organ Non-Secreting (órgão não-secretor)
| # | ingredient_id padrão | Descrição | requires_cooking | TIER típico |
|---|---|---|---|---|
| 7 | `{animal}_lung_raw` | Pulmão | `false` | TIER_A |
| 8 | `{animal}_green_tripe_raw` | Tripa verde (rúmen/estômago) | `false` | TIER_B |

### 2.5 Connective Tissue (tecido conectivo)
| # | ingredient_id padrão | Descrição | requires_cooking | TIER típico |
|---|---|---|---|---|
| 9 | `{animal}_foot_tendon_raw` | Mocotó (pé/tendão) | `true` | TIER_B |

### 2.6 Blood Source (sangue)
| # | ingredient_id padrão | Descrição | requires_cooking | TIER típico |
|---|---|---|---|---|
| 10 | `{animal}_blood_raw` | Sangue | `true` | TIER_B |

### 2.7 Outros (opcionais, se aplicável à espécie)
| # | ingredient_id padrão | Descrição | requires_cooking | TIER típico |
|---|---|---|---|---|
| 11 | `{animal}_tail_raw` | Rabo | `true` | TIER_B |
| 12 | `{animal}_gizzard_raw` | Moela (aves) | `false` | TIER_A |
| 13 | `{animal}_skin_raw` | Pele (aves) | `false` | TIER_B |

**Regra**: Todo arquivo DEVE ter no mínimo 1 `muscle_meat` + 1 `organ_secreting` (fígado). Os demais são obrigatórios se a espécie os possui anatomicamente.

---

## 3. ESTRUTURA COMPLETA DO INGREDIENTE

```jsonc
{
  // ─── CAMPOS OBRIGATÓRIOS DO INGREDIENTE ───
  "ingredient_id": string,       // snake_case, regex: ^[a-z][a-z0-9_]*$
  "display_name": string,        // Nome legível em PT-BR
  "category": string,            // Ver enum Seção 4
  "requires_cooking": boolean,   // true = precisa cozinhar (71°C interno mínimo)

  // ─── PERFIL BROMATOLÓGICO ───
  "bromatological_profile": {
    "basis": "as_fed",           // SEMPRE "as_fed" — nunca outro valor
    "reference_mass_g": 100,     // SEMPRE 100 — base por 100g do alimento como fornecido
    "nutrients": {
      "<nutrient_key>": { /* TypedMeasure — ver Seção 5 */ }
    },
    "coverage_excluded_nutrients": [
      // Lista de nutrient_keys que este ingrediente NÃO possui dados confiáveis
      // Regras: lowercase snake_case, SEM overlap com nutrients keys
      // nutrients_count + coverage_excluded_count DEVE = 41
    ]
  },

  // ─── BIOAVAILABILITY ───
  "bioavailability_factors": {
    "iron_type": "heme" | "non_heme",  // Obrigatório
    "phytate_penalty": boolean,         // true se ingrediente tem fitato
    "oxalate_penalty": boolean          // true se ingrediente tem oxalato
    // variability_ranges — OMITIR se não houver. NÃO usar [] ou {}.
    // "variability_ranges": { "<param>": { /* TypedMeasureRange — ver Seção 6 */ } }
  },

  // ─── RESTRIÇÕES DO SOLVER ───
  "lp_constraints": {
    "max_inclusion_pct": float,    // 0-100, percentual máximo na dieta (as_fed)
    "min_inclusion_pct": float,    // 0-100, percentual mínimo na dieta (as_fed)
    "basis": "as_fed",             // SEMPRE "as_fed"
    "risk_flags": [string]         // Vocabulário controlado — ver Seção 9
  },

  // ─── ALERTAS DE SEGURANÇA ───
  "safety_alerts": [
    {
      "type": string,              // "microbiological" | "chemical_toxicity" | "physical_hazard"
      "risk": string,              // Descrição do risco em PT-BR
      "mitigation": string,        // Como mitigar em PT-BR
      "source_ref": string         // ^REF_[A-Z0-9_]+$
    }
    // Mínimo 1 alert do tipo "microbiological" é OBRIGATÓRIO
  ],

  // ─── METADADOS ───
  "metadata": {
    "source_citation": string,          // Descrição completa da(s) fonte(s) de dados
    "evidence_tier": "TIER_A" | "TIER_B",  // Ver Seção 11
    "last_reviewed_date": "YYYY-MM-DD"
  }
}
```

---

## 4. CATEGORY ENUM (vocabulário controlado)

```
muscle_meat          — Músculo esquelético
muscle_organ         — Órgão com tecido muscular (coração, língua, diafragma)
organ_secreting      — Órgão secretor (fígado, rim, baço, pâncreas)
organ_non_secreting  — Órgão não-secretor (pulmão, tripa verde)
connective_tissue    — Tecido conectivo/cartilagem (mocotó, orelha, traqueia)
blood_source         — Sangue total ou plasma
bone                 — Osso
cartilage            — Cartilagem
fat_source           — Fonte de gordura pura
supplement           — Suplemento mineral/vitamínico
grain                — Grão/cereal
vegetable            — Vegetal
fruit                — Fruta
dairy                — Laticínio
egg                  — Ovo
fish                 — Peixe
```

---

## 5. TypedMeasure — REGRA RÍGIDA

**Todo e qualquer valor numérico no arquivo DEVE usar esta estrutura. Sem exceções.**

```jsonc
{
  "value": number,        // OBRIGATÓRIO. Número (int ou float). NUNCA null, NUNCA string.
  "unit": string,         // OBRIGATÓRIO. Enum Seção 5.1.
  "basis": string,        // OBRIGATÓRIO. Enum Seção 5.2.
  "source_ref": string,   // OBRIGATÓRIO. Regex: ^REF_[A-Z0-9_]+$
  "confidence": string,   // OPCIONAL. "measured"|"estimated"|"inferred"|"extrapolated"|"interpolated"
  "note": string          // OPCIONAL. Max 200 chars.
}
```

**additionalProperties: false** — NÃO é permitido adicionar campos extras além dos 6 acima.

### 5.1 UNIT ENUM (17 valores)

| Unit | Descrição | Usado em |
|---|---|---|
| `g` | gramas | Proteína, gordura, aminoácidos, ácidos graxos (por 100g) |
| `mg` | miligramas | Minerais, vitaminas B, colina (por 100g) |
| `ug` | microgramas | Vitaminas lipossolúveis em µg, selênio, iodo, vitamina K, folato (por 100g) |
| `IU` | unidades internacionais | Vitamina A, D3, E (por 100g) |
| `kcal` | quilocalorias | Energia bruta (raramente usado em ingredientes, mas no enum) |
| `kcal_per_kg_DM` | kcal por kg matéria seca | Densidade energética |
| `pct` | percentual | Variabilidade, retenção |
| `days` | dias | Idade, tempo |
| `months` | meses | Idade |
| `weeks` | semanas | Idade |
| `kg` | quilogramas | Peso corporal |
| `cm` | centímetros | Altura, comprimento |
| `ratio` | razão adimensional | Proporções (Ca:P, etc.) |
| `dimensionless` | adimensional | Fatores puros |
| `kcal_per_24h` | kcal por 24 horas | Taxa metabólica |
| `mg_per_kg_day` | mg/kg/dia | Doses |
| `mg_per_kg` | mg por kg | Concentração corporal |

### 5.2 BASIS ENUM (3 valores)

| Basis | Descrição | Quando usar |
|---|---|---|
| `as_fed` | Como fornecido (peso úmido) | **SEMPRE em ingredientes** |
| `dry_matter` | Matéria seca | Nunca em ingredientes (só no integration layer) |
| `energy_normalized` | Per 1000 kcal EM | Nunca em ingredientes (só no solver targets) |

### 5.3 SOURCE_REF CONVENÇÃO

```
REF_USDA_FDC_{NNNNNN}        — USDA FoodData Central (ex: REF_USDA_FDC_170196)
REF_LIT_VET_{TIPO}           — Literatura veterinária (ex: REF_LIT_VET_CHICKEN_LIVER)
REF_MC_{NOME}                — Database Monica Segal (ex: REF_MC_MONICA_SEGAL)
REF_SAFETY_{TIPO}            — Referência de segurança
REF_BIO_{TIPO}               — Referência de biodisponibilidade
```

---

## 6. TypedMeasureRange — REGRA RÍGIDA

Usado APENAS em `bioavailability_factors.variability_ranges`.

```jsonc
{
  "min": number,          // OBRIGATÓRIO
  "max": number,          // OBRIGATÓRIO
  "unit": string,         // OBRIGATÓRIO
  "basis": string,        // OBRIGATÓRIO
  "source_ref": string,   // OBRIGATÓRIO
  "confidence": string,   // OPCIONAL
  "note": string          // OPCIONAL. Max 200 chars.
}
```

**Regra**: Omitir `variability_ranges` inteiramente se não houver. **NÃO usar `{}` vazio nem `[]`**.

---

## 7. UNIVERSO DE NUTRIENTES — 41 NUTRIENTES COM FICHA COMPLETA

Cada ingrediente DEVE ter `nutrients` + `coverage_excluded_nutrients` = **exatamente 41**.

### 7.1 MACRONUTRIENTES (2)

| # | nutrient_key | Nome | Unit | O que é | Faixa típica (carne/100g) | Grupo biológico |
|---|---|---|---|---|---|---|
| 1 | `protein_g` | Proteína bruta | `g` | Nitrogênio total × 6.25 (método Kjeldahl) | 13–22 g | Macronutriente |
| 2 | `fat_g` | Gordura total (extrato etéreo) | `g` | Lipídios totais por extração | 0.2–18 g | Macronutriente |

### 7.2 AMINOÁCIDOS ESSENCIAIS (10)

| # | nutrient_key | Nome | Unit | O que é | Faixa típica (carne/100g) | Nota |
|---|---|---|---|---|---|---|
| 3 | `arginine_g` | Arginina | `g` | Aminoácido essencial, precursor de óxido nítrico | 0.8–1.4 g | |
| 4 | `histidine_g` | Histidina | `g` | Aminoácido essencial, precursor de histamina | 0.3–1.2 g | |
| 5 | `isoleucine_g` | Isoleucina | `g` | Aminoácido essencial, ramificado (BCAA) | 0.2–1.0 g | |
| 6 | `leucine_g` | Leucina | `g` | Aminoácido essencial, ramificado (BCAA), principal | 0.7–2.4 g | |
| 7 | `lysine_g` | Lisina | `g` | Aminoácido essencial, frequentemente limitante | 0.8–1.8 g | |
| 8 | `methionine_g` | Metionina | `g` | Aminoácido essencial sulfurado | 0.2–0.6 g | met+cys calculado no solver |
| 9 | `phenylalanine_g` | Fenilalanina | `g` | Aminoácido essencial aromático | 0.4–1.4 g | phe+tyr calculado no solver |
| 10 | `threonine_g` | Treonina | `g` | Aminoácido essencial | 0.5–0.9 g | |
| 11 | `tryptophan_g` | Triptofano | `g` | Aminoácido essencial, precursor de serotonina | 0.05–0.28 g | Muito baixo em tecido conectivo |
| 12 | `valine_g` | Valina | `g` | Aminoácido essencial, ramificado (BCAA) | 0.5–1.4 g | |

### 7.3 ÁCIDOS GRAXOS (4)

| # | nutrient_key | Nome | Unit | O que é | Faixa típica (carne/100g) | Nota |
|---|---|---|---|---|---|---|
| 13 | `linoleic_acid_g` | Ácido linoleico (LA, ômega-6) | `g` | Ácido graxo essencial ômega-6 | 0.01–0.6 g | Deficiência causa dermatite |
| 14 | `ala_alpha_linolenic_acid_g` | Ácido alfa-linolênico (ALA, ômega-3) | `g` | Ácido graxo essencial ômega-3 precursor | 0.01–0.08 g | Muito baixo em carnes; ausente em maioria dos órgãos |
| 15 | `ara_arachidonic_acid_g` | Ácido araquidônico (ARA) | `g` | Ácido graxo ômega-6, presente em tecido animal | 0.01–0.3 g | Muito alto em língua, fígado, rim |
| 16 | `epa_plus_dha_g` | EPA + DHA combinados | `g` | Ácidos graxos ômega-3 de cadeia longa | 0.002–0.15 g | Presente principalmente em fígado; baixo em músculo |

### 7.4 MINERAIS (12)

| # | nutrient_key | Nome | Unit | O que é | Faixa típica (carne/100g) | Nota |
|---|---|---|---|---|---|---|
| 17 | `calcium_mg` | Cálcio | `mg` | Mineral estrutural (osso/dente), sinalização celular | 3–117 mg | Alto em tripa verde (conteúdo ruminal); baixo em músculo |
| 18 | `phosphorus_mg` | Fósforo | `mg` | Mineral estrutural + energético (ATP) | 23–387 mg | Muito alto em fígado e baço; baixo em sangue |
| 19 | `potassium_mg` | Potássio | `mg` | Eletrólito intracelular principal | 43–350 mg | Alto em músculo, pulmão, baço; baixo em sangue |
| 20 | `sodium_mg` | Sódio | `mg` | Eletrólito extracelular principal | 60–226 mg | Alto em sangue e pulmão |
| 21 | `magnesium_mg` | Magnésio | `mg` | Cofator enzimático, metabolismo energético | 2–20 mg | Relativamente uniforme; baixo em sangue |
| 22 | `iron_mg` | Ferro | `mg` | Transporte de O2 (hemoglobina), citocromos | 1.6–46.5 mg | **Muito alto em sangue (46.5) e baço (44.6)** |
| 23 | `zinc_mg` | Zinco | `mg` | Cofator enzimático, imunidade, pele | 0.4–5.5 mg | Alto em músculo; muito baixo em sangue (0.4) |
| 24 | `copper_mg` | Cobre | `mg` | Cofator enzimático, metabolismo do Fe | 0.05–9.8 mg | **Extremamente alto em fígado (9.8)**; 0.05-0.5 nos demais |
| 25 | `manganese_mg` | Manganês | `mg` | Cofator enzimático, metabolismo ósseo | 0.01–1.3 mg | **Alto em tripa verde (1.3)** por conteúdo ruminal |
| 26 | `selenium_ug` | Selênio | `ug` | Antioxidante (glutationa peroxidase) | 5–140 ug | **Muito alto em rim (140)**; moderado em fígado |
| 27 | `iodine_ug` | Iodo | `ug` | Componente dos hormônios tireoidianos (T3/T4) | 0–5 ug | **Dado muito raro**; presente só em sangue (bovino: 5 ug) |
| 28 | `chloride_mg` | Cloro | `mg` | Eletrólito, ácido gástrico (HCl) | dados ausentes | Sempre excluído em bovinos; verificar em outras espécies |

### 7.5 VITAMINAS (13)

| # | nutrient_key | Nome | Unit | O que é | Faixa típica (carne/100g) | Nota |
|---|---|---|---|---|---|---|
| 29 | `vitamin_a_iu` | Vitamina A (retinol) | `IU` | Visão, imunidade, crescimento celular | 10–16898 IU | **Fígado tem concentração extrema (16898)**; músculo ~zero |
| 30 | `vitamin_d3_iu` | Vitamina D3 (colecalciferol) | `IU` | Absorção de Ca/P, metabolismo ósseo | 3–49 IU | Presente em fígado, rim, coração, sangue |
| 31 | `vitamin_e_iu` | Vitamina E (alfa-tocoferol) | `IU` | Antioxidante lipossolúvel, membranas celulares | 0.2–0.6 IU | Presente em fígado, rim, coração, sangue |
| 32 | `vitamin_k_ug` | Vitamina K (filoquinona/MK) | `ug` | Coagulação sanguínea, metabolismo ósseo | 0.4–3.1 ug | **Muito raro**; presente só em fígado e coração (bovino) |
| 33 | `thiamine_b1_mg` | Tiamina (B1) | `mg` | Metabolismo de carboidratos | 0.02–0.35 mg | Alto em rim; baixo em tecido conectivo |
| 34 | `riboflavin_b2_mg` | Riboflavina (B2) | `mg` | Metabolismo energético, visão | 0.05–2.75 mg | **Muito alto em fígado (2.75) e rim (1.9)** |
| 35 | `niacin_b3_mg` | Niacina (B3) | `mg` | Metabolismo energético, pele | 0.4–13.2 mg | Alto em fígado, baço, rim |
| 36 | `pantothenic_acid_b5_mg` | Ácido pantotênico (B5) | `mg` | Síntese de CoA, metabolismo energético | 0.2–7.2 mg | **Muito alto em fígado (7.2)**; ausente em sangue |
| 37 | `pyridoxine_b6_mg` | Piridoxina (B6) | `mg` | Metabolismo de aminoácidos, neurotransmissão | 0.03–1.08 mg | Alto em fígado e rim |
| 38 | `folic_acid_b9_ug` | Ácido fólico (B9/Folato) | `ug` | Síntese de DNA, divisão celular | 4–290 ug | **Extremamente alto em fígado (290)** e rim (98) |
| 39 | `cobalamin_b12_ug` | Cobalamina (B12) | `ug` | Metabolismo do folato, mielina, eritropoiese | 0.5–59.3 ug | **Extremamente alto em fígado (59.3)**; alto em sangue (12) |
| 40 | `choline_mg` | Colina | `mg` | Metilação, membranas celulares, fígado | variável | Presente em músculo, fígado, rim, coração |
| 41 | `biotin_ug` | Biotina (B7) | `ug` | Cofator carboxilase, pele, pelo | dados ausentes | Sempre excluído em bovinos; verificar em outras espécies |

### 7.6 REGRAS DE COBERTURA POR CATEGORIA (base bovino)

| Nutriente | muscle_meat | heart | liver | kidney | lung | blood | tripe | tendon | tongue | spleen | tail |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 25 comuns (protein, fat, 10 AA, 8 minerais) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `linoleic_acid_g` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `ara_arachidonic_acid_g` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ |
| `vitamin_a_iu` | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ |
| `vitamin_d3_iu` | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| `vitamin_e_iu` | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| `vitamin_k_ug` | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| `iodine_ug` | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| `choline_mg` | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| `epa_plus_dha_g` | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| `ala_alpha_linolenic_acid_g` | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ |
| `folic_acid_b9_ug` | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | ✓ | ✓ |
| `pantothenic_acid_b5_mg` | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `pyridoxine_b6_mg` | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `riboflavin_b2_mg` | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `thiamine_b1_mg` | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `biotin_ug` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| `chloride_mg` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

**Regra de exclusão**: Um nutriente vai para `coverage_excluded_nutrients` QUANDO:
1. O ingrediente não tem esse nutriente em quantidades significativas biologicamente, E
2. Não há dados confiáveis mensurados na fonte (USDA FDC/literatura veterinária), E
3. Forçar `value: 0.0` seria enganoso (não é zero confirmado, é **ausência de dado**)

**NUNCA** colocar um nutriente em AMBOS `nutrients` e `coverage_excluded_nutrients`.

---

## 8. BIOAVAILABILITY FACTORS — REGRAS POR TIPO DE PROTEÍNA

| Tipo de proteína | iron_type | phytate_penalty | oxalate_penalty |
|---|---|---|---|
| Bovinos (carne vermelha) | `heme` | `false` | `false` |
| Aves (carne branca) | `heme` | `false` | `false` |
| Suínos | `heme` | `false` | `false` |
| Peixes | `heme` | `false` | `false` |
| Vegetais/Folhosos | `non_heme` | `false` | `true` se espinafre/oxalado |
| Grãos/Cereais/Leguminosas | `non_heme` | `true` | `false` |
| Ovos | `non_heme` (gema tem phosvitin) | `false` | `false` |
| Laticínios | `non_heme` | `false` | `false` |

---

## 9. RISK_FLAGS — VOCABULÁRIO CONTROLADO

```
vitamin_A_toxicity              — Fígado com alto retinol (hipervitaminose A)
retinol_variability_400pct      — Variabilidade extrema de vitamina A no fígado
high_collagen_low_tryptophan_imbalance — Tecido conectivo com desbalance de triptofano
high_fat_content                — Ingrediente com teor de gordura elevado
microbiological_hazard          — Risco microbiológico específico (sangue, tripas)
raw_only_requirement            — Ingrediente perde propriedades se cozido (tripa verde)
```

---

## 10. SAFETY ALERTS — REGRAS

### 10.1 Obrigatório
Todo ingrediente DEVE ter pelo menos 1 safety_alert com `type: "microbiological"`.

### 10.2 Tipos de alerta
| type | Quando usar |
|---|---|
| `microbiological` | SEMPRE (mínimo 1 por ingrediente) |
| `chemical_toxicity` | Fígado (vit A), sangue (Fe), ingredientes com contaminantes |
| `physical_hazard` | Ossos, espinhas, fragmentos |

### 10.3 Source refs de segurança
```
REF_SAFETY_{ANIMAL}_RAW_PATHOGENS     — Patógenos em carne crua (Salmonella, E. coli, Listeria)
REF_SAFETY_{ANIMAL}_COOKING           — Necessidade de cozimento (71°C interno)
REF_SAFETY_{ANIMAL}_BLOOD_PATHOGENS   — Riscos específicos do sangue (príons BSE)
REF_SAFETY_IRON_OVERLOAD              — Sobrecarga de ferro
REF_SAFETY_VITAMIN_A_TOXICITY         — Hipervitaminose A
```

---

## 11. EVIDENCE TIER — CRITÉRIOS

| Tier | Critério | Exemplo |
|---|---|---|
| **TIER_A** | Dados diretos de USDA FDC com FDC ID específico e **match exato** do corte/órgão | `beef_liver_raw` → FDC 169451 (Beef, liver, raw) |
| **TIER_B** | Literatura veterinária, proxy FDC de corte diferente, combinação de fontes, ou dados estimados | `beef_tongue_raw` → literatura veterinária (FDC 170196 era round roast, CORRIGIDO) |

**Regras**:
- Um ingrediente pode misturar TIER_A e TIER_B por nutriente (usar campo `confidence` no TypedMeasure)
- O `metadata.evidence_tier` é o tier **predominante** do ingrediente inteiro
- Se >50% dos nutrientes vêm de USDA FDC direto = TIER_A; caso contrário = TIER_B

---

## 12. LP_CONSTRAINTS — DIRETRIZES POR CATEGORIA

| Categoria | max_inclusion_pct | min_inclusion_pct | Exemplo Bovino |
|---|---|---|---|
| muscle_meat | 20–30% | 10–20% | beef_muscle_raw: 30/20 |
| muscle_organ (coração) | 10–15% | 5–10% | beef_heart_raw: 15/10 |
| muscle_organ (língua) | 10% | 0% | beef_tongue_raw: 10/0 |
| organ_secreting (fígado) | 5% | 0% | beef_liver_raw: 5/0 |
| organ_secreting (outros) | 10% | 5% | beef_kidney_raw: 10/5 |
| organ_non_secreting | 10–15% | 5–10% | beef_lung_raw: 15/10 |
| connective_tissue | 5–10% | 0–5% | beef_foot_tendon_raw: 10/5 |
| blood_source | 5% | 0–3% | beef_blood_raw: 5/3 |

---

## 13. OBSERVAÇÕES CRÍTICAS

### 13.1 Valores são POR 100g AS_FED
Todos os valores nutricionais são expressos **por 100g do alimento como fornecido** (peso úmido, cru). Não converter para matéria seca nem para energy_normalized — o integration layer faz isso.

### 13.2 Unit mismatch é RESPONSABILIDADE DO INTEGRATION LAYER
O ingrediente armazena `calcium_mg` (mg/100g as_fed). O solver usa `calcium_g` (g/1000kcal). A conversão é feita pelo integration layer. O sufixo `_mg` no nutrient_key reflete a unidade **do dado bruto do ingrediente**, não do solver.

### 13.3 Nomes de nutrientes SÃO variáveis do solver
O nutrient_key (ex: `vitamin_a_iu`) é usado diretamente como FK lookup. Mixed case (`Vitamin_A_IU`) **NUNCA** funcionaria.

### 13.4 Variáveis computadas NÃO são armazenadas
- `methionine_plus_cystine_g` → calculado no solver como `methionine_g + cystine_g`
- `phenylalanine_plus_tyrosine_g` → calculado no solver como `phenylalanine_g + tyrosine_g`
- Portanto, `cystine_g` e `tyrosine_g` **não existem** no universo de 41 nutrientes

### 13.5 Dados são para CÃES FILHOTES (AAFCO growth)
NUNCA usar valores nutricionais de tabelas humanas. Sempre USDA FDC (alimento bruto) ou literatura veterinária canina/específica.

### 13.6 biotin_ug e chloride_mg
Em bovinos, estes 2 nutrientes estão em `coverage_excluded_nutrients` em TODOS os ingredientes. Para outras espécies, **pesquisar** se há dados confiáveis. Se houver, incluir em `nutrients` com valor; se não, manter em `coverage_excluded_nutrients`.

---

## 14. CHECKLIST DE VALIDAÇÃO (22 itens)

- [ ] `ingredient_id` é lowercase snake_case, começa com letra, regex `^[a-z][a-z0-9_]*$`
- [ ] `category` está no enum da Seção 4
- [ ] `bromatological_profile.basis` == `"as_fed"`
- [ ] `bromatological_profile.reference_mass_g` == `100`
- [ ] `nutrients` + `coverage_excluded_nutrients` = **41** nutrientes totais
- [ ] Zero overlap entre `nutrients` keys e `coverage_excluded_nutrients`
- [ ] Cada `TypedMeasure` tem exatamente 4 chaves required: `value`, `unit`, `basis`, `source_ref`
- [ ] Nenhum `TypedMeasure` tem chaves extras (além de `confidence` e `note` opcionais)
- [ ] `value` é número (nunca null, nunca string, nunca boolean)
- [ ] `unit` está no enum de 17 valores da Seção 5.1
- [ ] `basis` está no enum de 3 valores da Seção 5.2
- [ ] `source_ref` match regex `^REF_[A-Z0-9_]+$`
- [ ] `coverage_excluded_nutrients` items são lowercase snake_case
- [ ] `bioavailability_factors.iron_type` é `"heme"` ou `"non_heme"`
- [ ] `lp_constraints.basis` == `"as_fed"`
- [ ] `lp_constraints.risk_flags` usa vocabulário controlado da Seção 9
- [ ] Pelo menos 1 `safety_alert` com `type: "microbiological"`
- [ ] Cada `safety_alert` tem exatamente: `type`, `risk`, `mitigation`, `source_ref` (nenhum campo extra)
- [ ] `metadata.evidence_tier` é `"TIER_A"` ou `"TIER_B"`
- [ ] `metadata.last_reviewed_date` formato `YYYY-MM-DD`
- [ ] Nenhum dado nutricional é para humanos — 100% cães filhotes AAFCO growth
- [ ] Variáveis computadas (met+cys, phe+tyr) NÃO são armazenadas