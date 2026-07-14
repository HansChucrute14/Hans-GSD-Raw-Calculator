# PROMPT DE PESQUISA — Dados Nutricionais de Ingredientes para LP Solver Canino

## INSTRUÇÕES PARA A IA DE PESQUISA

Este é um prompt autossuficiente. Você NÃO precisa de contexto externo — tudo está aqui. Siga EXATAMENTE. Qualquer desvio da padronização torna o dado inutilizável pelo solver.

---

## 1. OBJETIVO

Pesquisar e preencher dados nutricionais de ingredientes (alimentos crus) para um **LP solver de formulação de dieta canina** — raça Pastor Alemão, filhote em crescimento, padrão **AAFCO growth**.

Você vai receber:
- O **tipo de proteína** (ex: "Aves", "Suínos", "Peixes")
- O **arquivo de especificação** `INGREDIENTE_TEMPLATE_SPEC.md` com a estrutura exata

Você vai retornar:
- Um **arquivo JSON** (array de ingredientes) seguindo 100% a especificação
- Cada ingrediente com **41 nutrientes** (em `nutrients` ou `coverage_excluded_nutrients`)
- Dados por **100g do alimento como fornecido (as_fed, cru)**

---

## 2. METODOLOGIA DE PESQUISA — PASSO A PASSO

### PASSO 1: Identificar os ingredientes obrigatórios

Para a proteína `{ANIMAL}`, você DEVE pesquisar os seguintes ingredientes:

| # | ingredient_id | Categoria | O que buscar no USDA/literatura |
|---|---|---|---|
| 1 | `{animal}_muscle_raw` | muscle_meat | Corte primário cru (ex: Chicken breast, Pork loin) |
| 2 | `{animal}_heart_raw` | muscle_organ | Coração cru |
| 3 | `{animal}_tongue_raw` | muscle_organ | Língua crua |
| 4 | `{animal}_liver_raw` | organ_secreting | Fígado cru |
| 5 | `{animal}_kidney_raw` | organ_secreting | Rim cru |
| 6 | `{animal}_spleen_raw` | organ_secreting | Baço cru |
| 7 | `{animal}_lung_raw` | organ_non_secreting | Pulmão cru |
| 8 | `{animal}_green_tripe_raw` | organ_non_secreting | Tripa verde/estômago cru (sem lavar) |
| 9 | `{animal}_foot_tendon_raw` | connective_tissue | Pé/tendão/cartilagem crua |
| 10 | `{animal}_blood_raw` | blood_source | Sangue cru |
| 11 | `{animal}_tail_raw` | (opcional) | Rabo cru (se aplicável) |

**Regra**: Se a espécie não possui um dado ingrediente (ex: aves não têm "rabo" anatômico), omitir. Mínimo obrigatório: muscle_meat + liver.

### PASSO 2: Para cada ingrediente, buscar no USDA FoodData Central

**Fonte primária**: USDA FoodData Central (https://fdc.nal.usda.gov/)

**Como buscar**:
1. Buscar por: `{Animal}, {organ/cut}, raw` (ex: "Chicken, liver, raw")
2. Encontrar o FDC ID que dá **match exato** do órgão/corte
3. **NUNCA usar FDC ID de um corte diferente** (ex: NÃO usar dados de "Chicken, broilers, breast" para "Chicken, heart")
4. Se não houver FDC exato para o órgão, usar literatura veterinária e marcar como TIER_B

**FDC ID de referência (bovinos, para comparação)**:
- Beef muscle: FDC 170196 (round, bottom round roast)
- Beef heart: FDC 168625
- Beef liver: FDC 169451
- Beef kidney: FDC 169449
- Beef lung: FDC 168628

### PASSO 3: Para cada nutriente nos 41, extrair o valor

**Os 41 nutrientes OBRIGATÓRIOS** (com unidade exata):

```
MACRONUTRIENTES (unit: g)
  protein_g, fat_g

AMINOÁCIDOS ESSENCIAIS (unit: g)
  arginine_g, histidine_g, isoleucine_g, leucine_g, lysine_g,
  methionine_g, phenylalanine_g, threonine_g, tryptophan_g, valine_g

ÁCIDOS GRAXOS (unit: g)
  linoleic_acid_g, ala_alpha_linolenic_acid_g,
  ara_arachidonic_acid_g, epa_plus_dha_g

MINERAIS
  calcium_mg (mg), phosphorus_mg (mg), potassium_mg (mg),
  sodium_mg (mg), magnesium_mg (mg), iron_mg (mg),
  zinc_mg (mg), copper_mg (mg), manganese_mg (mg),
  selenium_ug (ug), iodine_ug (ug), chloride_mg (mg)

VITAMINAS
  vitamin_a_iu (IU), vitamin_d3_iu (IU), vitamin_e_iu (IU),
  vitamin_k_ug (ug), thiamine_b1_mg (mg), riboflavin_b2_mg (mg),
  niacin_b3_mg (mg), pantothenic_acid_b5_mg (mg), pyridoxine_b6_mg (mg),
  folic_acid_b9_ug (ug), cobalamin_b12_ug (ug),
  choline_mg (mg), biotin_ug (ug)
```

**Para cada nutriente**:
1. Se o USDA FDC tem o dado → usar o valor exato, marcar `source_ref: "REF_USDA_FDC_{ID}"`
2. Se o USDA FDC NÃO tem o dado mas literatura veterinária tem → usar valor da literatura, marcar `source_ref: "REF_LIT_VET_{TIPO}"`, evidence_tier = TIER_B
3. Se NÃO há dado confiável em nenhuma fonte → colocar em `coverage_excluded_nutrients` (NUNCA forçar 0.0)

### PASSO 4: Decidir excluded vs zero

| Situação | Ação |
|---|---|
| USDA tem valor mensurado (mesmo que "0.0" ou traço) | Incluir em `nutrients` com o valor |
| USDA marca como traço/negligível | Incluir em `nutrients` com `value: 0.0` |
| USDA não lista o nutriente (campo ausente) | `coverage_excluded_nutrients` |
| Literatura veterinária confirma valor | Incluir em `nutrients`, source_ref = `REF_LIT_VET_*` |
| Nenhuma fonte confiável | `coverage_excluded_nutrients` |

**NUNCA**:
- Inventar valores ("estimar" sem fonte)
- Usar dados de tabelas nutricionais humanas
- Usar dados de alimento processado/cozido quando o ingrediente é "raw"
- Misturar dados de espécies diferentes (ex: dados de fígado de frango para fígado de peru)

### PASSO 5: Preencher os campos não-nutricionais

**bioavailability_factors**:
- `iron_type`: `"heme"` para todas as carnes/peixes, `"non_heme"` para vegetais/grãos
- `phytate_penalty`: `false` para carnes, `true` para grãos/leguminosas
- `oxalate_penalty`: `false` para carnes, `true` apenas para vegetais oxalados

**lp_constraints**:
- Seguir as diretrizes por categoria (ver especificação Seção 12)
- `risk_flags`: usar apenas vocabulário controlado (ver especificação Seção 9)

**safety_alerts**:
- Mínimo 1 alerta `microbiological` por ingrediente
- Se fígado tem >5000 IU vitamina A → adicionar alerta `chemical_toxicity` com `source_ref: "REF_SAFETY_VITAMIN_A_TOXICITY"`
- Se sangue tem >30 mg Fe → adicionar alerta `chemical_toxicity` com `source_ref: "REF_SAFETY_IRON_OVERLOAD"`

**metadata**:
- `source_citation`: descrever TODAS as fontes usadas (ex: "USDA FDC 169451 (Chicken, liver, raw) & NRC 2006 Table 15.1")
- `evidence_tier`: TIER_A se >50% dos nutrientes vêm de FDC direto; TIER_B caso contrário
- `last_reviewed_date`: data de hoje no formato YYYY-MM-DD

---

## 3. OUTPUT ESPERADO — FORMATO EXATO

### 3.1 Formato do arquivo

```json
[
  {
    "ingredient_id": "chicken_muscle_raw",
    "display_name": "Músculo de Frango Cru (Peito)",
    "category": "muscle_meat",
    "requires_cooking": false,
    "bromatological_profile": {
      "basis": "as_fed",
      "reference_mass_g": 100,
      "nutrients": {
        "protein_g": {
          "value": 23.1,
          "unit": "g",
          "basis": "as_fed",
          "source_ref": "REF_USDA_FDC_XXXXXX"
        },
        "fat_g": {
          "value": 1.7,
          "unit": "g",
          "basis": "as_fed",
          "source_ref": "REF_USDA_FDC_XXXXXX"
        }
      },
      "coverage_excluded_nutrients": [
        "iodine_ug",
        "chloride_mg"
      ]
    },
    "bioavailability_factors": {
      "iron_type": "heme",
      "phytate_penalty": false,
      "oxalate_penalty": false
    },
    "lp_constraints": {
      "max_inclusion_pct": 30.0,
      "min_inclusion_pct": 20.0,
      "basis": "as_fed",
      "risk_flags": []
    },
    "safety_alerts": [
      {
        "type": "microbiological",
        "risk": "Salmonella, E. coli, Listeria",
        "mitigation": "Congelamento profilático a -18°C por 72h ou cozimento a 71°C interno",
        "source_ref": "REF_SAFETY_POULTRY_RAW_PATHOGENS"
      }
    ],
    "metadata": {
      "source_citation": "USDA FoodData Central, FDC ID XXXXXX (Chicken, broilers, breast, meat only, raw)",
      "evidence_tier": "TIER_A",
      "last_reviewed_date": "2026-07-11"
    }
  }
]
```

### 3.2 Regras rígidas do output

1. **JSON válido** — sem trailing commas, UTF-8, 2 espaços de indentação
2. **nutrients + coverage_excluded_nutrients = 41** para CADA ingrediente
3. **Zero overlap** entre as duas listas
4. **Todo TypedMeasure** tem exatamente: `value` (number), `unit` (string do enum), `basis` ("as_fed"), `source_ref` (REF_...)
5. **Nenhum campo extra** em TypedMeasure (additionalProperties: false)
6. **source_ref** sempre match `^REF_[A-Z0-9_]+$`
7. **nutrient_key** sempre lowercase snake_case
8. **value** nunca null, nunca string, nunca boolean
9. **Todos os valores** são para CÃES FILHOTES (AAFCO growth) — NUNCA humanos

---

## 4. O QUE ESTÁ FALTANDO — GAPS COMUNS QUE VOCÊ DEVE PESQUISAR

### 4.1 Nutrientes frequentemente ausentes no USDA FDC

Estes nutrientes frequentemente NÃO aparecem no USDA para muitos órgãos. Para eles, você DEVE buscar na literatura veterinária canina:

| Nutriente | Por que é difícil | Onde buscar |
|---|---|---|
| `iodine_ug` | Raramente medido; varia com dieta do animal | NRC 2006, tabelas de composição de vísceras |
| `chloride_mg` | Raramente reportado separado do sódio | NRC 2006, tabelas de eletrólitos |
| `biotin_ug` | Concentrações muito baixas, difícil de medir | NRC 2006, pesquisa específica |
| `vitamin_k_ug` | Pouco estudado em alimentos crus | NRC 2006, literatura de nutrição canina |
| `vitamin_d3_iu` | Presente em poucos órgãos | Fígado e rim são as melhores fontes |
| `vitamin_e_iu` | Degradado por armazenamento; dados variáveis | FDC tem dados limitados |
| `choline_mg` | FDC usa unidades inconsistentes | Verificar se o valor é em mg ou mcg |
| `epa_plus_dha_g` | Baixo em carnes de terra; mais alto em peixes | FDC geralmente tem para peixes |
| `ala_alpha_linolenic_acid_g` | Muito baixo em carnes; depende da dieta do animal | FDC geralmente tem |
| `ara_arachidonic_acid_g` | Presente em tecido animal, mas FDC nem sempre lista | Literatura de composição lipídica |

### 4.2 Armadilhas comuns (ERROS QUE VOCÊ NÃO DEVE COMETER)

| Armadilha | Descrição | Como evitar |
|---|---|---|
| **FDC ID errado** | Usar dados de corte A para preencher corte B | Verificar SEMPRE que a descrição do FDC match o ingrediente |
| **Unidade errada** | O FDC reporta em mcg mas o nutriente espera ug (são iguais, mas valor numérico muda se confundir com mg) | Sempre verificar a unidade do FDC vs a unidade do nutrient_key |
| **Dado cozido** | Usar dados de "Chicken, liver, cooked" para ingrediente "raw" | Sempre buscar "raw" no FDC |
| **Base errada** | Usar dados per 100g dry matter quando deve ser as_fed | FDC padrão é as_fed (por 100g do alimento) |
| **Vitamina A em IU vs mcg** | 1 IU de retinol = 0.3 mcg RAE | Se FDC dá em mcg RAE, converter: IU = mcg_RAE / 0.3 |
| **Vitamina D em IU vs mcg** | 1 IU = 0.025 mcg de colecalciferol | Se FDC dá em mcg, converter: IU = mcg / 0.025 |
| **Colina em mg vs mcg** | Algumas tabelas usam mcg | Verificar unidade do FDC; converter para mg se necessário |
| **Selenium em ug vs mcg** | 1 ug = 1 mcg (são iguais) | Apenas confirmar que o valor numérico está correto |
| **Valores para humanos** | Tabelas nutricionais de supermercado são para humanos | Usar SEMPRE USDA FDC ou NRC 2006 (canino) |

### 4.3 Conversões que você PODE precisar fazer

| De | Para | Fator | Quando usar |
|---|---|---|---|
| mcg RAE (retinol) | IU | ÷ 0.3 | Vitamina A: FDC às vezes dá em mcg RAE |
| mcg (colecalciferol) | IU | ÷ 0.025 | Vitamina D3: FDC às vezes dá em mcg |
| mcg | mg | ÷ 1000 | Quando FDC reporta em mcg mas o nutrient_key usa `_mg` |
| mg | g | ÷ 1000 | Quando FDC reporta em mg mas o nutrient_key usa `_g` |

---

## 5. O QUE VOCÊ NÃO DEVE FAZER

1. **NÃO inventar dados** — se não encontrar, coloque em `coverage_excluded_nutrients`
2. **NÃO usar dados de ração/processados** — apenas alimento cru (raw)
3. **NÃO usar dados de outras espécies** — dados de fígado bovino NÃO valem para fígado de frango
4. **NÃO mudar a estrutura JSON** — siga EXATAMENTE a especificação
5. **NÃO omitir nutrientes** — cada ingrediente deve ter 41 (nutrients + excluded)
6. **NÃO adicionar nutrientes extras** — o universo é fixo em 41
7. **NÃO usar `value: null`** — null viola o schema; use `coverage_excluded_nutrients`
8. **NÃO usar `value: 0.0` como placeholder** — 0.0 significa "zero confirmado pelo laboratório"
9. **NÃO adicionar chaves extras em TypedMeasure** — apenas value, unit, basis, source_ref (+ confidence, note opcionais)
10. **NÃO misturar case no nutrient_key** — tudo lowercase, snake_case

---

## 6. ESTRUTURA DE RESPOSTA ESPERADA

Quando terminar a pesquisa para uma proteína, retorne:

### 6.1 O arquivo JSON completo
- Nome do arquivo: `{Animal}.json` (ex: `Aves.json`, `Suinos.json`)
- Array de ingredientes, cada um com 41 nutrientes

### 6.2 Um relatório de pesquisa (mesmo arquivo ou separado)
Para cada ingrediente, informe:
```
INGREDIENTE: {ingredient_id}
  FDC ID usado: {ID ou "N/A"}
  Tier: {A ou B}
  Nutrientes em nutrients: {N}
  Nutrientes em coverage_excluded: {M}
  Total: {N+M} (deve ser 41)
  Fontes usadas: {listar todas}
  Gaps identificados: {quais nutrientes não foram encontrados em nenhuma fonte}
  Notas: {qualquer observação relevante}
```

### 6.3 Lista de FDC IDs usados
```
{FDC_ID} → {descrição completa do alimento no USDA}
```

---

## 7. REFERÊNCIAS RECOMENDADAS PARA PESQUISA

### 7.1 Fontes primárias (usar SEMPRE que possível)
- **USDA FoodData Central**: https://fdc.nal.usda.gov/ (buscar "raw" + órgão + espécie)
- **NRC 2006**: "Nutrient Requirements of Dogs and Cats", National Research Council

### 7.2 Fontes secundárias (quando USDA não tem o dado)
- **Monica Segal Database**: dados de composição para formulação canina
- **AAFCO Official Publication**: tabelas de composição de ingredientes
- **Literatura veterinária**: artigos peer-reviewed sobre composição de vísceras

### 7.3 Exemplo de busca USDA correta
```
Buscar: "Chicken, liver, raw"
Resultado esperado: FDC ID com descrição "Chicken, liver, all classes, raw"
VERIFICAR: A descrição match "liver" e "raw"? SIM → usar
VERIFICAR: A descrição é de "cooked" ou "fried"? NÃO → usar
VERIFICAR: É da mesma espécie? SIM → usar
```

### 7.4 Exemplo de busca USDA INCORRETA
```
Buscar: "Chicken, liver, raw"
Resultado: FDC ID 05055 "Chicken, broilers or fryers, liver, all classes, cooked, simmered"
VERIFICAR: É "cooked"? SIM → NÃO USAR para ingrediente "raw"
AÇÃO: Continuar buscando até encontrar versão "raw"
```