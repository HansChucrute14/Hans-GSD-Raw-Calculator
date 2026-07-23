# GSD Diet Calc — Especificação Normativa de Ingrediente

**Versão do documento:** 2.1.0
**Schema de referência:** `db_ingredientes.schema.json` (Draft 2020-12) — **fonte de verdade absoluta**
**Implementação de referência:** `DB_ingredientes.json` v3.1.1
**Substitui:** INGREDIENTE_TEMPLATE_SPEC.md v1.x (estrutura `TypedMeasure` / `coverage_excluded_nutrients` — **obsoleta**)
**Changelog v2.1.0:** revogada a restrição de proveniência "toda fonte é USDA FDC ou literatura veterinária" (Seção 17); substituída por regra de identidade de substrato + lista de fontes oficiais autorizadas (nova Seção 6.2), incluindo tabelas brasileiras (TACO, TBCA, Embrapa) e europeias (CIQUAL, BLS, CoFID, Frida, EuroFIR). Motivação: 5 nutrientes tinham cobertura zero (23/23 `missing`) apenas por lacuna de escopo do USDA FDC, não por ausência real do dado na literatura.

> Este documento usa linguagem normativa RFC 2119: **DEVE** / **NÃO DEVE** (MUST/MUST NOT), **DEVERIA** / **NÃO DEVERIA** (SHOULD/SHOULD NOT), **PODE** (MAY). Toda afirmação técnica aqui é derivada diretamente de `db_ingredientes.schema.json`. Em caso de qualquer divergência entre este documento e o schema, **o schema prevalece** e este documento está incorreto.

---

## 1. Propósito

Esta especificação define, de forma exaustiva e não ambígua, a estrutura de dados válida para arquivos de ingredientes consumidos pelo GSD Diet Calc — um sistema de formulação de dieta canina (Pastor Alemão, fase de crescimento, padrão AAFCO) baseado em Programação Linear (LP) com Goal Programming.

O documento existe para que um engenheiro humano ou um agente de IA consiga gerar um objeto `Ingredient` estruturalmente válido **sem nunca precisar ler `db_ingredientes.schema.json` diretamente**. Se um JSON gerado a partir desta especificação falhar a validação contra o schema, a especificação está errada e deve ser corrigida — nunca o contrário.

---

## 2. Escopo

**Dentro do escopo:**
- Estrutura completa do arquivo `DB_ingredientes.json` (nível raiz, metadados, grupos, ingredientes).
- O contrato de 3 estados para nutrientes (`measured` / `missing` / `not_applicable`).
- Todos os `$defs` do schema: `IngredientGroup`, `Ingredient`, `BromatologicalProfile`, `NutrientEntry`, `SourceRef`.
- Vocabulários controlados (enums), regexes, constantes e regras `additionalProperties`.
- O catálogo completo dos 43 nutrientes rastreados por ingrediente.

**Fora do escopo:**
- O algoritmo do solver LP/Goal Programming em si (consome estes dados, não os define).
- A camada de integração que converte `as_fed` → `dry_matter` / `energy_normalized`.
- Metas nutricionais AAFCO (definidas em outro arquivo de targets, não neste).
- `lp_parameters.schema.json` (schema legado, referenciado apenas historicamente — ver Seção 19).

---

## 3. Visão Geral da Arquitetura

```
Pesquisa nutricional (USDA FDC / literatura veterinária)
        │
        ▼
Ingredient JSON (conforme esta especificação)
        │
        ▼
Validação contra db_ingredientes.schema.json (Draft 2020-12)
        │
        ▼
Merge em DB_ingredientes.json (protein_sources.<grupo>.ingredients[])
        │
        ▼
Camada de integração (as_fed → dry_matter / energy_normalized)
        │
        ▼
LP Solver (Goal Programming vs. metas AAFCO Large Breed Growth)
```

Cada ingrediente é validado **individualmente** contra `#/$defs/Ingredient` antes do merge, e o arquivo consolidado é validado **como um todo** contra o schema raiz.

---

## 4. Terminologia

| Termo | Definição |
|---|---|
| **Ingredient** | Objeto que descreve um alimento cru/preparado único, com perfil nutricional completo por 100 g *as_fed*. Unidade atômica de dados consumida pelo solver. |
| **IngredientGroup** | Agrupamento de ingredientes por fonte proteica/animal (ex.: `bovinos`, `aves`). Chave de nível superior dentro de `protein_sources`. |
| **Protein Source** | Sinônimo operacional de `IngredientGroup` — nome usado nas chaves de `protein_sources`. |
| **NutrientEntry** | Estrutura de um único nutriente dentro de `bromatological_profile.nutrients`. Sempre um de três estados: `measured`, `missing`, `not_applicable`. |
| **Metadata** (nível Ingredient) | Bloco de proveniência USDA e confiança de dados do ingrediente inteiro. |
| **SourceRef** | String de referência de fonte, regex `^REF_[A-Z0-9_]+$`. Usada tanto para dados medidos (`source_ref`) quanto para justificar ausência de dado (`anomaly_ref`). |
| **Safety Alert** | Alerta estruturado de risco (microbiológico, toxicidade química, etc.) associado ao ingrediente. |
| **LP Constraint** | Restrição de inclusão percentual (`min_inclusion_pct` / `max_inclusion_pct`) que o solver aplica a este ingrediente. |
| **Bioavailability** | Fatores que modulam a absorção real de nutrientes (tipo de ferro, penalidades de fitato/oxalato, faixas de variabilidade biológica). |
| **Validação** | Processo de checagem de um documento JSON contra `db_ingredientes.schema.json` usando um validador Draft 2020-12. |

---

## 5. Filosofia de Design

O schema v3.x adota um **contrato de 3 estados**: todo nutriente do universo de 43 chaves **DEVE** aparecer em `bromatological_profile.nutrients` para todo ingrediente, sempre com um `status` explícito. Não existe omissão silenciosa de chave.

Isso substitui o modelo v1.x, no qual um nutriente sem dado simplesmente não aparecia em `nutrients` e era listado (opcionalmente) em `coverage_excluded_nutrients`. Esse modelo permitia ambiguidade: uma chave ausente podia significar "não medido", "não aplicável" ou "esquecido por erro humano" — indistinguíveis programaticamente.

No modelo atual:

- **`measured`** — o valor existe, foi medido/derivado de uma fonte rastreável, e é numericamente utilizável pelo solver.
- **`missing`** — o nutriente é biologicamente relevante para este ingrediente, mas não há dado confiável na fonte consultada. O solver **DEVE** tratar isso como incerteza de dado, não como zero.
- **`not_applicable`** — o nutriente não se aplica a este ingrediente por razão estrutural (ex.: vitamina lipossolúvel que só entra via suplemento na matriz *as_fed*, conforme regras de formulação).

Um validador que encontrar menos de 43 chaves em `nutrients`, ou uma chave fora do padrão `^[a-z][a-z0-9_]*$`, ou um `NutrientEntry` sem `status` **DEVE** rejeitar o documento. Isso é o que torna o schema uma prova positiva de completude de dados: a ausência de valor é sempre uma decisão declarada, nunca um silêncio.

`coverage_excluded_nutrients` é mantido apenas por **compatibilidade retroativa** e está **DEPRECATED** — será removido na v11 do schema. Documentos novos **NÃO DEVEM** depender dele para expressar ausência de dado; usar `status: "missing"` ou `status: "not_applicable"`.

---

## 6. Estrutura de Nível Superior (`DB_ingredientes.json`)

```jsonc
{
  "_db_metadata": { /* ver Seção 6.1 */ },
  "protein_sources": {
    "<nome_do_grupo>": { /* IngredientGroup — ver Seção 7 */ },
    // ex.: "bovinos", "aves", "suinos", "peixes", "fat_sources"
  }
}
```

- `additionalProperties: false` no nível raiz — **apenas** `_db_metadata` e `protein_sources` são permitidos.
- `protein_sources` é um objeto com `additionalProperties` validado por `IngredientGroup` — qualquer chave (nome de grupo) é aceita, mas o valor **DEVE** satisfazer o schema `IngredientGroup`.
- Ambos `_db_metadata` e `protein_sources` são **obrigatórios**.

### 6.2 Fontes de Dados Autorizadas (revisão v2.1.0)

**Motivação:** 5 dos 43 nutrientes tinham cobertura zero (23/23 ingredientes `missing`) na base v3.1.1 porque USDA FDC não decompõe rotineiramente `chloride_mg`, `iodine_ug`, `biotin_ug`, `methionine_plus_cystine_g` e `phenylalanine_plus_tyrosine_g` para carnes cruas. Essas lacunas **não são inerentes ao substrato** — são lacunas de cobertura da tabela USDA especificamente. Tabelas de composição de alimentos de outros órgãos oficiais frequentemente cobrem exatamente essas chaves para os mesmos cortes crus.

**Regra de identidade de substrato:** uma fonte é válida se, e somente se, o item catalogado é o mesmo tecido animal cru/*in natura*, sem preparo, do mesmo órgão/corte. A origem institucional da tabela (humana, veterinária, animal/*feed*) não é critério de validade.

**Fontes oficiais autorizadas (não exaustivo — qualquer tabela de composição nacional/institucional com metodologia AOAC ou equivalente e revisão por pares/órgão público é aceitável mediante o mesmo critério):**

| Região | Instituição | Base | Prefixo `REF_` sugerido |
|---|---|---|---|
| Brasil | NEPA/UNICAMP | TACO — Tabela Brasileira de Composição de Alimentos | `REF_TACO_<id>` |
| Brasil | FoRC/USP | TBCA — Tabela Brasileira de Composição de Alimentos (USP) | `REF_TBCA_<id>` |
| Brasil | Embrapa | Tabelas de composição de carnes e derivados (pesquisa pecuária) | `REF_EMBRAPA_<id>` |
| França | ANSES | CIQUAL — Table de composition nutritionnelle des aliments | `REF_CIQUAL_<id>` |
| Alemanha | Max Rubner-Institut | BLS — Bundeslebensmittelschlüssel | `REF_BLS_<id>` |
| Reino Unido | PHE/McCance & Widdowson | CoFID — Composition of Foods Integrated Dataset | `REF_COFID_<id>` |
| Dinamarca | DTU Food | Danish Food Composition Databank (Frida) | `REF_FRIDA_<id>` |
| UE (agregador) | EuroFIR AISBL | Rede de bases nacionais europeias padronizadas | `REF_EUROFIR_<id>` |
| EUA (mantido) | USDA | FoodData Central (alimento bruto) | `REF_USDA_FDC_<id>` |
| Internacional (feed/veterinária) | NRC, INRAE, literatura veterinária | Tabelas de exigências e composição para *feed* animal | `REF_NRC_<id>`, `REF_INRAE_<id>` |
| Brasil (feed/AA) | UFV — Rostagno et al. | Tabelas Brasileiras para Aves e Suínos (composição e AA digestível de ingredientes de origem animal) | `REF_ROSTAGNO_<id>` |

**Nota de metadata:** o campo `metadata.usda_fdc_id` (Seção 10) permanece `string`, mas quando a fonte primária não é USDA, **DEVE** conter o ID do item na fonte efetivamente usada (ex.: código TACO/TBCA), com `metadata.usda_description` documentando claramente a fonte real (ex.: `"TBCA C0123T — Coração, bovino, cru"`). Isso é uma convenção de conteúdo, não uma mudança estrutural — não requer alteração do `db_ingredientes.schema.json` em si, já que o campo continua `string` livre. Caso o volume de fontes não-USDA cresça, recomenda-se generalizar para `primary_source_db` + `primary_source_id` em uma v4 do schema — fora do escopo desta revisão de spec.

**O que continua proibido:** dados de alimentos processados/preparados (cozidos, temperados, curados, embutidos) sendo usados para preencher o perfil `as_fed` de um ingrediente definido como cru; conversões implícitas de matéria seca para *as_fed* sem documentar o fator usado; e qualquer valor sem `source_ref` rastreável ao registro específico da tabela de origem.

### 6.1 `_db_metadata`

Campos obrigatórios: `db_name`, `version`, `created_date`, `last_updated`, `schema_ref`, `template_ref`, `target_species`, `breed`, `lifestage`, `standard`, `nutrients_per_ingredient`, `total_ingredients`, `validated_sources`, `pending_sources`, `partial_sources`.

| Campo | Tipo | Regra | Exemplo real |
|---|---|---|---|
| `db_name` | string | livre | `"GSD Diet Calc — Banco Unificado de Ingredientes"` |
| `version` | string | regex `^\d+\.\d+\.\d+$` (SemVer) | `"3.1.1"` |
| `created_date` | string | livre (data) | `"2026-07-11"` |
| `last_updated` | string | livre (data) | `"2026-07-14"` |
| `schema_ref` | string | nome do arquivo de schema | `"db_ingredientes.schema.json"` |
| `template_ref` | string | caminho desta especificação | `"docs/data-specs/INGREDIENTE_TEMPLATE_SPEC.md"` |
| `target_species` | string | nome científico | `"Canis lupus familiaris"` |
| `breed` | string | raça alvo | `"German Shepherd Dog"` |
| `lifestage` | string | fase de vida | `"growth"` |
| `standard` | string | padrão nutricional | `"AAFCO"` |
| `nutrients_per_ingredient` | integer | `minimum: 43` — **DEVE** refletir a contagem real de chaves em `nutrients` | `43` |
| `total_ingredients` | integer | `minimum: 20` — contagem total de ingredientes no arquivo | `28` |
| `validated_sources` | array\<string\> | nomes de grupos com `status: "VALIDATED"` | `["bovinos"]` |
| `pending_sources` | array\<string\> | nomes de grupos com `status: "PENDING"` | `["aves"]` |
| `partial_sources` | array\<string\> | nomes de grupos com `status: "PARTIAL"` | `["aves","suinos","peixes","fat_sources"]` |
| `note` (opcional) | string | não validado pelo schema formal, mas usado na prática para anotar migrações | — |

**Regra de consistência (não imposta pelo schema, mas exigida operacionalmente):** um grupo listado em `validated_sources` **DEVERIA** ter `status: "VALIDATED"` no `IngredientGroup` correspondente, e o mesmo vale para `pending_sources`/`PENDING` e `partial_sources`/`PARTIAL`. Um grupo pode aparecer simultaneamente em `pending_sources` e `partial_sources` durante transições de status (comportamento observado na referência).

---

## 7. `IngredientGroup`

Campos obrigatórios: `common_name`, `animal_prefix`, `status`, `ingredient_count`, `ingredient_ids`, `ingredients`.

```jsonc
{
  "common_name": "Bovinos (Bos taurus)",
  "animal_prefix": "beef",
  "status": "VALIDATED",
  "validation_date": "2026-07-10",
  "validation_tool": "validate_bovinos_deep.py",
  "validation_result": "0 errors, 11 warnings (expected)",
  "ingredient_count": 11,
  "ingredient_ids": ["beef_muscle_raw", "beef_lung_raw", "..."],
  "notes": "texto livre opcional",
  "ingredients": [ /* array de Ingredient — ver Seção 8 */ ]
}
```

| Campo | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `common_name` | string | sim | Nome comum + nome científico entre parênteses, ex.: `"Aves (Gallus gallus domesticus)"`. |
| `animal_prefix` | string | sim | Prefixo usado em todo `ingredient_id` do grupo (ex.: `beef`, `chicken`, `pork`). |
| `status` | string | sim | Enum: `VALIDATED` \| `PARTIAL` \| `PENDING`. |
| `validation_date` | string ou null | não | Data ISO da última validação formal, ou `null` se nunca validado. |
| `validation_tool` | string | não | Nome do script/ferramenta usada na validação (ex.: `"validate_bovinos_deep.py"`). Tipicamente presente apenas quando `status: "VALIDATED"`. |
| `validation_result` | string | não | Resumo textual do resultado (ex.: `"0 errors, 11 warnings (expected)"`). |
| `ingredient_count` | integer | sim | **DEVE** ser igual a `len(ingredient_ids)` e a `len(ingredients)`. |
| `ingredient_ids` | array\<string\> | sim | Lista dos `ingredient_id` presentes em `ingredients`, na mesma ordem lógica. |
| `notes` | string | não | Observações livres (ex.: ingredientes obrigatórios ainda faltando). |
| `ingredients` | array\<Ingredient\> | sim | Array de objetos `Ingredient` — ver Seção 8. |

**Regra crítica de sincronismo:** `ingredient_count`, `ingredient_ids` e o array `ingredients` **DEVEM** estar mutuamente consistentes. Um `ingredient_id` presente em `ingredients[].ingredient_id` que não aparece em `ingredient_ids` (ou vice-versa) é um erro de integridade, mesmo que passe na validação estrutural do JSON Schema (o schema não impõe essa consistência cruzada — é responsabilidade do gerador).

---

## 8. `Ingredient`

Campos obrigatórios: `ingredient_id`, `display_name`, `category`, `requires_cooking`, `bromatological_profile`, `metadata`, `lp_constraints`.
Campos opcionais: `bioavailability_factors`, `safety_alerts`.

```jsonc
{
  "ingredient_id": "beef_muscle_raw",
  "display_name": "Músculo Bovino Cru (Patinho/Acém/Paleta)",
  "category": "muscle_meat",
  "requires_cooking": false,

  "bromatological_profile": { /* ver Seção 9 */ },

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
      "severity": "warning",
      "message": "Salmonella, E. coli, Listeria",
      "source_ref": "REF_SAFETY_BOVINE_RAW_PATHOGENS"
    }
  ],

  "metadata": {
    "usda_fdc_id": "170196",
    "usda_description": "Beef, round, bottom round roast, separable lean only, raw",
    "data_confidence": "HIGH",
    "last_validated": "2026-07-10"
  }
}
```

> Exemplo ilustrativo: `bromatological_profile.nutrients` foi omitido acima por brevidade. Um `Ingredient` real **DEVE** conter as 43 chaves de nutriente descritas na Seção 16.

### 8.1 Campos do nível `Ingredient`

| Campo | Tipo | Obrigatório | Regra |
|---|---|---|---|
| `ingredient_id` | string | sim | Regex `^[a-z][a-z0-9_]*$`. snake_case, começa com letra minúscula. Convenção: `{animal_prefix}_{corte}_{estado}` (ex.: `beef_liver_raw`). |
| `display_name` | string | sim | Nome legível, tipicamente em PT-BR. |
| `category` | string | sim | Enum de 16 valores — ver Seção 15.1. |
| `requires_cooking` | boolean | sim | `true` se o ingrediente precisa ser cozinhado (71 °C interno mínimo) antes de servir. |
| `bromatological_profile` | object | sim | Ver Seção 9. |
| `bioavailability_factors` | object | não | Tipos mistos (objetos, strings, booleanos) — validação apenas estrutural pelo schema (`additionalProperties: {}`). Ver Seção 11. |
| `lp_constraints` | object | sim | Ver Seção 12. |
| `safety_alerts` | array\<object\> | não | Ver Seção 13. |
| `metadata` | object | sim | Ver Seção 10. |

O objeto `Ingredient` em si **não** declara `additionalProperties: false` — chaves de nível superior além das listadas **PODEM** ser adicionadas sem violar o schema, mas **NÃO DEVERIAM** ser adicionadas sem necessidade documentada, para manter uniformidade entre ingredientes.

---

## 9. `NutrientEntry` e o Contrato de 3 Estados

Esta é a seção mais crítica da especificação. `bromatological_profile` tem a forma:

```jsonc
{
  "basis": "as_fed",
  "reference_mass_g": 100,
  "nutrients": {
    "<nutrient_key>": { /* NutrientEntry */ },
    // ... exatamente as 43 chaves do catálogo (Seção 16)
  },
  "coverage_excluded_nutrients": [ /* DEPRECATED — ver Seção 5 */ ]
}
```

| Campo | Tipo | Regra |
|---|---|---|
| `basis` | string | `const: "as_fed"` — **DEVE** ser exatamente esse valor. |
| `reference_mass_g` | integer | `const: 100` — todo valor é por 100 g do alimento como fornecido. |
| `nutrients` | object | `additionalProperties: false` combinado com `patternProperties: "^[a-z][a-z0-9_]*$"` e `minProperties: 43`. Cada chave **DEVE** casar o padrão e ter valor validado por `NutrientEntry`. |
| `coverage_excluded_nutrients` | array\<string\> | **DEPRECATED**. Mantido apenas por compatibilidade. Não usar em documentos novos. |

`NutrientEntry` é um `oneOf` de exatamente três formas. O validador aceita o documento se e somente se ele casar **exatamente uma** delas.

### 9.1 Estado `measured`

```jsonc
{
  "status": "measured",
  "value": 4.5,
  "unit": "g",
  "basis": "as_fed",
  "source_ref": "REF_USDA_FDC_170196",
  "confidence": "measured",
  "note": "texto opcional, máx. 200 caracteres"
}
```

- Campos obrigatórios: `status` (`const: "measured"`), `value`, `unit`, `basis`, `source_ref`.
- Campos opcionais: `confidence`, `note`.
- `additionalProperties: false` — **nenhuma** chave além das 7 listadas acima é permitida.
- `value`: `number` — nunca `null`, nunca string, nunca booleano.
- `unit`: enum de 7 valores — `g` \| `mg` \| `ug` \| `IU` \| `kcal` \| `pct` \| `ratio`. (Nota: este enum é mais restrito que o vocabulário de unidades do template v1.x — ver Seção 15.2 para a lista completa e diferenças.)
- `basis`: `const: "as_fed"` — repetido a nível de nutriente para permitir validação local sem dependência do objeto pai.
- `source_ref`: `SourceRef` — regex `^REF_[A-Z0-9_]+$`. Ver Seção 14.
- `confidence` (opcional): enum `measured` \| `estimated` \| `inferred` \| `extrapolated` \| `interpolated`. Default declarado no schema: `"measured"`.
- `note` (opcional): string, `maxLength: 200`.

### 9.2 Estado `missing`

```jsonc
{
  "status": "missing",
  "value": null,
  "reason": "not measured in USDA FDC for this ingredient",
  "anomaly_ref": "REF_MISSING_CHLORIDE"
}
```

- Campos obrigatórios: `status` (`const: "missing"`), `reason`, `anomaly_ref`.
- `value`, se presente, **DEVE** ser `null` (`type: "null", const: null`).
- `reason`: string, `maxLength: 200` — justificativa textual da ausência.
- `anomaly_ref`: `SourceRef` — referência que documenta a decisão de marcar como ausente (não uma fonte de dado, mas uma fonte de *decisão*).
- `additionalProperties: false` — nenhuma chave além de `status`, `value`, `reason`, `anomaly_ref`.
- Semântica: o nutriente **é biologicamente relevante** para este ingrediente, mas a fonte consultada não o mediu.

### 9.3 Estado `not_applicable`

```jsonc
{
  "status": "not_applicable",
  "value": null,
  "reason": "sourced from supplement/fortification; excluded from as_fed matrix per formulation_rules",
  "anomaly_ref": "REF_FORMULATION_RULES_EXCLUSION"
}
```

- Estrutura idêntica a `missing` (mesmos campos obrigatórios, mesmo `additionalProperties: false`), diferindo apenas em `status` (`const: "not_applicable"`).
- Semântica: o nutriente **não se aplica** a este ingrediente por decisão estrutural do modelo (ex.: nutrientes lipossolúveis fortificados exclusivamente via suplemento, e por isso excluídos da matriz *as_fed* dos ingredientes crus, conforme `formulation_rules`).
- **Distinção prática entre `missing` e `not_applicable`:** `missing` = "procuramos e não achamos"; `not_applicable` = "por design, este dado não pertence a este tipo de entrada".

### 9.4 Por que o `oneOf` existe

O `oneOf` (em vez de `anyOf`) força que cada `NutrientEntry` seja inequivocamente **uma e apenas uma** das três formas. Isso impede documentos ambíguos como um objeto com `status: "measured"` mas `value: null`, ou um objeto com `status: "missing"` mas contendo `value: 4.5` e `unit`. Um validador Draft 2020-12 rejeitará qualquer `NutrientEntry` que satisfaça mais de um ramo do `oneOf` ou nenhum deles.

### 9.5 Regras de Validação — Checklist do `NutrientEntry`

- [ ] `status` está presente e é um dos três valores válidos.
- [ ] Se `status == "measured"`: `value`, `unit`, `basis`, `source_ref` **DEVEM** estar presentes; `reason`/`anomaly_ref` **NÃO DEVEM** estar presentes.
- [ ] Se `status` ∈ {`missing`, `not_applicable`}: `reason` e `anomaly_ref` **DEVEM** estar presentes; `unit`/`source_ref`/`confidence`/`note` **NÃO DEVEM** estar presentes; `value`, se presente, **DEVE** ser `null`.
- [ ] Nenhuma chave fora das listadas para o estado correspondente (`additionalProperties: false` em todos os três ramos).
- [ ] `unit` (quando aplicável) pertence ao enum de 7 valores da Seção 15.2.
- [ ] `basis` (quando aplicável) é exatamente `"as_fed"`.
- [ ] `source_ref`/`anomaly_ref` casam o regex `^REF_[A-Z0-9_]+$`.

---

## 10. `metadata` (nível `Ingredient`)

```jsonc
{
  "usda_fdc_id": "170196",
  "usda_description": "Beef, round, bottom round roast, separable lean only, raw",
  "data_confidence": "HIGH",
  "last_validated": "2026-07-10"
}
```

Campos obrigatórios: `usda_fdc_id`, `usda_description`, `data_confidence`, `last_validated`. Todos do tipo `string` no schema (não há enum formal para `data_confidence`, mas o valor observado na base de referência é uniformemente `"HIGH"`).

| Campo | Tipo | Propósito |
|---|---|---|
| `usda_fdc_id` | string | ID numérico (como string) do item no USDA FoodData Central que serviu de base primária para este ingrediente. |
| `usda_description` | string | Descrição textual exata do item no USDA FDC, para rastreabilidade (ex.: `"Beef, round, bottom round roast, separable lean only, raw"`). |
| `data_confidence` | string | Nível de confiança agregado do ingrediente. Valor observado na referência: `"HIGH"`. Não há enum imposto pelo schema; **DEVERIA** seguir vocabulário consistente em maiúsculas (`HIGH`/`MEDIUM`/`LOW`) por convenção. |
| `last_validated` | string | Data (formato livre no schema; convenção `YYYY-MM-DD`) da última checagem manual/automática dos dados deste ingrediente. |

**Nota de migração:** este bloco substitui os campos `source_citation` e `evidence_tier` (`TIER_A`/`TIER_B`) do template v1.x. `usda_fdc_id` + `usda_description` fornecem rastreabilidade mais granular do que `source_citation`; `data_confidence` substitui `evidence_tier`. Ver Seção 19.

---

## 11. `bioavailability_factors`

Campo opcional no nível `Ingredient`. O schema o define como `additionalProperties: {}` — ou seja, **validação puramente estrutural** (é um objeto), sem restrição de forma sobre seu conteúdo. A convenção observada na base de referência é:

```jsonc
{
  "iron_type": "heme",
  "phytate_penalty": false,
  "oxalate_penalty": false,
  "variability_ranges": {
    "vitamin_a_variation_pct": {
      "min": -75,
      "max": 300,
      "unit": "pct",
      "basis": "as_fed",
      "source_ref": "REF_BIO_VISCERA_VIT_A"
    }
  }
}
```

| Chave (convenção) | Tipo | Notas |
|---|---|---|
| `iron_type` | string | `"heme"` ou `"non_heme"`. Não é um enum de schema, mas convenção do domínio (carnes/vísceras/sangue = `heme`; vegetais/grãos/ovos/laticínios = `non_heme`). |
| `phytate_penalty` | boolean | `true` se o ingrediente contém fitato relevante (tipicamente grãos/leguminosas). |
| `oxalate_penalty` | boolean | `true` se o ingrediente contém oxalato relevante (tipicamente certos vegetais). |
| `variability_ranges` | object (opcional) | Mapa de `<parametro>: TypedMeasureRange`. **DEVE ser omitido inteiramente** se não houver variabilidade documentada — **NÃO usar** `{}` vazio nem `[]`. Cada entrada usa a forma `{min, max, unit, basis, source_ref}` (min/max numéricos; demais campos seguem a mesma convenção de `NutrientEntry.measured`, sem imposição formal de schema além de ser um objeto). |

`variability_ranges` é usado esparsamente na base de referência — apenas quando há literatura documentando faixas de variação biológica relevantes (ex.: absorção de cálcio em osso cru varia 35–80%; vitamina A em fígado varia -75% a +300% conforme dieta do animal de origem).

---

## 12. `lp_constraints`

Campo **obrigatório**. Campos obrigatórios internos: `min_inclusion_pct`, `max_inclusion_pct`, `basis`.

```jsonc
{
  "max_inclusion_pct": 30.0,
  "min_inclusion_pct": 20.0,
  "basis": "as_fed",
  "risk_flags": []
}
```

| Campo | Tipo | Regra |
|---|---|---|
| `min_inclusion_pct` | number | `minimum: 0`. Percentual mínimo de inclusão na dieta formulada, base *as_fed*. |
| `max_inclusion_pct` | number | `minimum: 0`. Percentual máximo de inclusão. **DEVE** ser ≥ `min_inclusion_pct` (não imposto pelo schema — responsabilidade do gerador). |
| `basis` | string | `const: "as_fed"`. |
| `risk_flags` | array\<string\> (opcional) | Vocabulário controlado por convenção de domínio — ver Seção 15.4. Array vazio `[]` é válido e comum quando não há flags aplicáveis. |

Diretrizes de faixa por categoria (convenção operacional, não imposta pelo schema — observadas na base de referência de bovinos):

| Categoria | `max_inclusion_pct` típico | `min_inclusion_pct` típico |
|---|---|---|
| `muscle_meat` | 20–30% | 10–20% |
| `muscle_organ` (coração) | 10–15% | 5–10% |
| `muscle_organ` (língua) | 10% | 0% |
| `organ_secreting` (fígado) | 5% | 0% |
| `organ_secreting` (demais) | 10% | 5% |
| `organ_non_secreting` | 10–15% | 5–10% |
| `connective_tissue` | 5–10% | 0–5% |
| `blood_source` | 5% | 0–3% |
| `fat_source` | variável, tipicamente baixo | 0% |

---

## 13. `safety_alerts`

Campo opcional (array). Cada item é validado individualmente; campos obrigatórios: `type`, `severity`, `message`, `source_ref`.

```jsonc
{
  "type": "microbiological",
  "severity": "warning",
  "message": "Salmonella, E. coli, Listeria",
  "source_ref": "REF_SAFETY_BOVINE_RAW_PATHOGENS"
}
```

| Campo | Tipo | Obrigatório | Notas |
|---|---|---|---|
| `type` | string | sim | Sem enum formal no schema. Valores observados na referência: `microbiological`, `chemical_toxicity`. O template v1.x também previa `physical_hazard` — **DEVERIA** continuar sendo usado quando aplicável (ossos, fragmentos), por convenção de domínio. |
| `severity` | string | sim | Sem enum formal no schema. Único valor observado na referência: `warning`. |
| `message` | string | sim | Descrição do risco em linguagem natural (PT-BR ou EN, conforme convenção do dataset). |
| `source_ref` | `SourceRef` | sim | Regex `^REF_[A-Z0-9_]+$`. |

O schema **não declara `additionalProperties: false`** para este objeto — campos extras são estruturalmente permitidos. Isso é usado na prática: a base de referência mantém, por compatibilidade com ferramentas legadas, os campos adicionais `risk` e `mitigation` (equivalentes semânticos de `message` e de uma recomendação de mitigação) em paralelo a `type`/`severity`/`message`/`source_ref`:

```jsonc
{
  "type": "microbiological",
  "risk": "Salmonella, E. coli, Listeria",
  "mitigation": "Congelamento profilático a -18°C por 72h ou cozimento a 71°C interno",
  "source_ref": "REF_SAFETY_BOVINE_RAW_PATHOGENS",
  "severity": "warning",
  "message": "Salmonella, E. coli, Listeria"
}
```

Documentos novos **DEVEM** incluir os 4 campos obrigatórios (`type`, `severity`, `message`, `source_ref`); incluir `risk`/`mitigation` adicionalmente é **PERMITIDO** e **RECOMENDADO** para manter paridade com a base existente, mas não é exigido pelo schema.

**Regra de domínio (não imposta pelo schema, mas obrigatória operacionalmente):** todo ingrediente cru **DEVE** ter no mínimo 1 `safety_alert` com `type: "microbiological"`.

---

## 14. Referências de Fonte (`SourceRef`)

```json
{ "type": "string", "pattern": "^REF_[A-Z0-9_]+$" }
```

Regra formal única: string começando com `REF_`, seguida de um ou mais caracteres em `[A-Z0-9_]`.

Convenções de nomenclatura observadas na base de referência (não impostas pelo schema, mas obrigatórias por consistência de projeto):

| Prefixo | Uso | Exemplo real |
|---|---|---|
| `REF_USDA_FDC_{ID}` | Fonte primária USDA FoodData Central, para `NutrientEntry` com `status: "measured"` | `REF_USDA_FDC_170196` |
| `REF_MISSING_{NUTRIENTE}` | `anomaly_ref` para `status: "missing"`, específico ao nutriente ausente | `REF_MISSING_CHLORIDE`, `REF_MISSING_VIT_A`, `REF_MISSING_MET_CYS` |
| `REF_EXTRACTION_COMPLETE` | `anomaly_ref` genérico para `status: "missing"` quando a ausência decorre de escopo de extração (não de nutriente específico) | usado em 68 entradas da base de referência |
| `REF_FORMULATION_RULES_EXCLUSION` | `anomaly_ref` para `status: "not_applicable"` — nutriente excluído da matriz *as_fed* por regra de formulação (tipicamente vitaminas lipossolúveis fortificadas via suplemento) | usado em 31 entradas da base de referência |
| `REF_SAFETY_{ANIMAL}_{TIPO}` | `source_ref` de `safety_alerts` | `REF_SAFETY_BOVINE_RAW_PATHOGENS` |
| `REF_BIO_{TIPO}` | `source_ref` de `variability_ranges` em `bioavailability_factors` | `REF_BIO_VISCERA_VIT_A`, `REF_BIO_RAW_BONE_CA` |

`REF_LIT_VET_{TIPO}` e `REF_MC_{NOME}` (literatura veterinária, database Monica Segal) permanecem convenções válidas do domínio para fontes secundárias, herdadas do template v1.x, e **PODEM** ser usadas quando a fonte primária não for USDA FDC.

---

## 15. Vocabulários Controlados

### 15.1 `category` (16 valores — enum do schema)

```
muscle_meat            organ_non_secreting     bone            grain
muscle_organ            connective_tissue       cartilage       vegetable
organ_secreting          blood_source            fat_source      fruit
fish                                                             dairy
                                                                  egg
                                                                  supplement
```

| Categoria | Significado |
|---|---|
| `muscle_meat` | Músculo esquelético |
| `muscle_organ` | Órgão com tecido muscular (coração, língua) |
| `organ_secreting` | Órgão secretor (fígado, rim, baço) |
| `organ_non_secreting` | Órgão não secretor (pulmão, tripa verde) |
| `connective_tissue` | Tecido conectivo/cartilagem (mocotó, tendão) |
| `blood_source` | Sangue total ou plasma |
| `fish` | Peixe (categoria própria, distinta de `muscle_meat`) |
| `bone` | Osso |
| `cartilage` | Cartilagem |
| `fat_source` | Fonte de gordura pura (sebo, gordura separável) |
| `supplement` | Suplemento mineral/vitamínico |
| `grain` | Grão/cereal |
| `vegetable` | Vegetal |
| `fruit` | Fruta |
| `dairy` | Laticínio |
| `egg` | Ovo |

### 15.2 `unit` do `NutrientEntry.measured` (7 valores — enum do schema)

```
g    mg    ug    IU    kcal    pct    ratio
```

**Nota de migração crítica:** o template v1.x descrevia um enum de 17 unidades (incluindo `kcal_per_kg_DM`, `days`, `months`, `weeks`, `kg`, `cm`, `dimensionless`, `kcal_per_24h`, `mg_per_kg_day`, `mg_per_kg`). Esse vocabulário estendido **não existe mais** no contexto de `NutrientEntry` — o schema atual restringe `unit` a apenas 7 valores, todos usados exclusivamente para compor o perfil bromatológico por 100 g. As unidades removidas pertenciam a outros contextos do sistema (idade, peso corporal, doses) e nunca deveriam ter sido documentadas como parte do vocabulário de nutrientes de ingrediente — este era um erro do template v1.x, corrigido aqui.

### 15.3 `basis` (`const`, não enum)

Tanto em `BromatologicalProfile.basis` quanto em `NutrientEntry.measured.basis` quanto em `lp_constraints.basis`, o valor **DEVE** ser exatamente `"as_fed"`. Não é um enum de múltiplas opções — é uma constante fixa (`const`) repetida em três pontos do documento para permitir validação local independente. `dry_matter` e `energy_normalized`, mencionados no template v1.x, pertencem exclusivamente à camada de integração e ao solver — **nunca** aparecem em arquivos de ingrediente.

### 15.4 `risk_flags` (vocabulário de convenção, não enum de schema)

`lp_constraints.risk_flags` é tipado como `array<string>` livre pelo schema — não há enum formal. O vocabulário abaixo é convenção de domínio observada na base de referência e **DEVERIA** ser reutilizado antes de se cunhar uma flag nova:

```
vitamin_A_toxicity                       — Fígado com alto retinol (hipervitaminose A)
retinol_variability_400pct               — Variabilidade extrema de vitamina A no fígado
high_collagen_low_tryptophan_imbalance   — Tecido conectivo com desbalanço de triptofano
high_fat_content                         — Ingrediente com teor de gordura elevado
microbiological_hazard                   — Risco microbiológico específico (sangue, tripas)
raw_only_requirement                     — Ingrediente perde propriedades se cozido
```

### 15.5 `status` do `NutrientEntry` (3 valores — enum implícito via `oneOf`/`const`)

```
measured    missing    not_applicable
```

### 15.6 `confidence` do `NutrientEntry.measured` (5 valores, opcional)

```
measured    estimated    inferred    extrapolated    interpolated
```

Default declarado no schema: `"measured"`.

### 15.7 `IngredientGroup.status` (3 valores)

```
VALIDATED    PARTIAL    PENDING
```

---

## 16. Catálogo de Nutrientes (43 chaves)

Toda entrada de `bromatological_profile.nutrients` **DEVE** conter exatamente estas 43 chaves — nem mais, nem menos (`minProperties: 43` combinado com `additionalProperties: false` e `patternProperties`). A tabela abaixo é organizada por grupo biológico; a coluna "Unit" reflete o valor usado quando `status: "measured"`.

### 16.1 Macronutrientes (2)

| # | `nutrient_key` | Nome | Unit |
|---|---|---|---|
| 1 | `protein_g` | Proteína bruta (N × 6,25) | `g` |
| 2 | `fat_g` | Gordura total (extrato etéreo) | `g` |

### 16.2 Aminoácidos Essenciais (10)

| # | `nutrient_key` | Nome | Unit |
|---|---|---|---|
| 3 | `arginine_g` | Arginina | `g` |
| 4 | `histidine_g` | Histidina | `g` |
| 5 | `isoleucine_g` | Isoleucina (BCAA) | `g` |
| 6 | `leucine_g` | Leucina (BCAA) | `g` |
| 7 | `lysine_g` | Lisina | `g` |
| 8 | `methionine_g` | Metionina | `g` |
| 9 | `phenylalanine_g` | Fenilalanina | `g` |
| 10 | `threonine_g` | Treonina | `g` |
| 11 | `tryptophan_g` | Triptofano | `g` |
| 12 | `valine_g` | Valina (BCAA) | `g` |

### 16.3 Aminoácidos Compostos (2)

| # | `nutrient_key` | Nome | Unit |
|---|---|---|---|
| 13 | `methionine_plus_cystine_g` | Metionina + Cistina | `g` |
| 14 | `phenylalanine_plus_tyrosine_g` | Fenilalanina + Tirosina | `g` |

> **Nota de migração:** no template v1.x, estas duas variáveis eram descritas como *calculadas pelo solver* (`methionine_g + cystine_g` e `phenylalanine_g + tyrosine_g`) e explicitamente **não armazenadas** no universo de nutrientes do ingrediente. O schema v3.x **reverte essa decisão**: ambas as chaves agora fazem parte do contrato de 43 nutrientes e **DEVEM** estar presentes em todo ingrediente — tipicamente com `status: "missing"` quando a fonte primária (USDA FDC) não decompõe esses valores combinados. Documentos gerados a partir do template antigo que omitiam essas chaves são **inválidos** contra o schema atual.

### 16.4 Ácidos Graxos (4)

| # | `nutrient_key` | Nome | Unit |
|---|---|---|---|
| 15 | `linoleic_acid_g` | Ácido linoleico (LA, ômega-6) | `g` |
| 16 | `ala_alpha_linolenic_acid_g` | Ácido alfa-linolênico (ALA, ômega-3) | `g` |
| 17 | `ara_arachidonic_acid_g` | Ácido araquidônico (ARA) | `g` |
| 18 | `epa_plus_dha_g` | EPA + DHA combinados | `g` |

### 16.5 Minerais (12)

| # | `nutrient_key` | Nome | Unit |
|---|---|---|---|
| 19 | `calcium_mg` | Cálcio | `mg` |
| 20 | `phosphorus_mg` | Fósforo | `mg` |
| 21 | `potassium_mg` | Potássio | `mg` |
| 22 | `sodium_mg` | Sódio | `mg` |
| 23 | `magnesium_mg` | Magnésio | `mg` |
| 24 | `iron_mg` | Ferro | `mg` |
| 25 | `zinc_mg` | Zinco | `mg` |
| 26 | `copper_mg` | Cobre | `mg` |
| 27 | `manganese_mg` | Manganês | `mg` |
| 28 | `selenium_ug` | Selênio | `ug` |
| 29 | `iodine_ug` | Iodo | `ug` |
| 30 | `chloride_mg` | Cloro | `mg` |

### 16.6 Vitaminas (13)

| # | `nutrient_key` | Nome | Unit |
|---|---|---|---|
| 31 | `vitamin_a_iu` | Vitamina A (retinol) | `IU` |
| 32 | `vitamin_d3_iu` | Vitamina D3 (colecalciferol) | `IU` |
| 33 | `vitamin_e_iu` | Vitamina E (alfa-tocoferol) | `IU` |
| 34 | `vitamin_k_ug` | Vitamina K (filoquinona/MK) | `ug` |
| 35 | `thiamine_b1_mg` | Tiamina (B1) | `mg` |
| 36 | `riboflavin_b2_mg` | Riboflavina (B2) | `mg` |
| 37 | `niacin_b3_mg` | Niacina (B3) | `mg` |
| 38 | `pantothenic_acid_b5_mg` | Ácido pantotênico (B5) | `mg` |
| 39 | `pyridoxine_b6_mg` | Piridoxina (B6) | `mg` |
| 40 | `folic_acid_b9_ug` | Ácido fólico (B9/Folato) | `ug` |
| 41 | `cobalamin_b12_ug` | Cobalamina (B12) | `ug` |
| 42 | `choline_mg` | Colina | `mg` |
| 43 | `biotin_ug` | Biotina (B7) | `ug` |

### 16.7 Estatística de estados observada na base de referência

Sobre 28 ingredientes × 43 nutrientes = 1204 `NutrientEntry` na base de referência (`DB_ingredientes.json` v3.3.0):

| Status | Contagem | % |
|---|---|---|
| `measured` | 680 | 68,8% |
| `missing` | 278 | 28,1% |
| `not_applicable` | 31 | 3,1% |

Nutrientes mais frequentemente `missing`: `chloride_mg`, `phenylalanine_plus_tyrosine_g`, `biotin_ug`, `methionine_plus_cystine_g` (28/28 ingredientes cada, na base atual — cobertura zero). `not_applicable` concentra-se em vitaminas lipossolúveis (`vitamin_a_iu`, `vitamin_d3_iu`) em ingredientes onde a regra de formulação exclui a fonte *as_fed* em favor de suplementação.

---

## 17. Regras de Validação — Checklist Normativo

- [ ] Documento raiz contém exatamente `_db_metadata` e `protein_sources` (`additionalProperties: false`).
- [ ] `_db_metadata.version` casa `^\d+\.\d+\.\d+$`.
- [ ] `_db_metadata.nutrients_per_ingredient` ≥ 43.
- [ ] `_db_metadata.total_ingredients` ≥ 20.
- [ ] Todo grupo em `protein_sources` satisfaz `IngredientGroup`.
- [ ] `IngredientGroup.status` ∈ {`VALIDATED`, `PARTIAL`, `PENDING`}.
- [ ] `IngredientGroup.ingredient_count` == `len(ingredient_ids)` == `len(ingredients)`.
- [ ] Todo `Ingredient` contém os 7 campos obrigatórios: `ingredient_id`, `display_name`, `category`, `requires_cooking`, `bromatological_profile`, `metadata`, `lp_constraints`.
- [ ] `ingredient_id` casa `^[a-z][a-z0-9_]*$`.
- [ ] `category` ∈ enum de 16 valores (Seção 15.1).
- [ ] `bromatological_profile.basis` == `"as_fed"`.
- [ ] `bromatological_profile.reference_mass_g` == `100`.
- [ ] `bromatological_profile.nutrients` contém **exatamente** as 43 chaves do catálogo (Seção 16), cada uma casando `^[a-z][a-z0-9_]*$`.
- [ ] Cada `NutrientEntry` satisfaz **exatamente um** ramo do `oneOf` (`measured` / `missing` / `not_applicable`).
- [ ] Em `NutrientEntry.measured`: `value` é `number`; `unit` ∈ enum de 7 valores (Seção 15.2); `basis` == `"as_fed"`; `source_ref` casa `^REF_[A-Z0-9_]+$`; nenhuma chave além de `status,value,unit,basis,source_ref,confidence,note`.
- [ ] Em `NutrientEntry.missing`/`not_applicable`: `value` é `null` (se presente); `reason` ≤ 200 caracteres; `anomaly_ref` casa `^REF_[A-Z0-9_]+$`; nenhuma chave além de `status,value,reason,anomaly_ref`.
- [ ] `lp_constraints` contém `min_inclusion_pct`, `max_inclusion_pct` (ambos ≥ 0), `basis` == `"as_fed"`.
- [ ] `lp_constraints.max_inclusion_pct` ≥ `lp_constraints.min_inclusion_pct` (regra de domínio, não de schema).
- [ ] Cada `safety_alerts[]` contém `type`, `severity`, `message`, `source_ref` (`source_ref` casando o regex).
- [ ] Todo ingrediente cru tem no mínimo 1 `safety_alerts[]` com `type: "microbiological"` (regra de domínio).
- [ ] `metadata` contém `usda_fdc_id`, `usda_description`, `data_confidence`, `last_validated` (todos string).
- [ ] **(revisado v2.1.0 — ver Seção 6.2)** Todo dado nutricional é proveniente de uma fonte autorizada (Seção 6.2), e o item medido é o **mesmo substrato físico**: mesma espécie animal, mesmo corte/órgão anatômico, mesmo estado (cru/*in natura*, sem cozimento/cura/tempero/processamento), com metodologia analítica comparável (AOAC ou equivalente). A audiência-alvo da tabela (nutrição humana vs. veterinária/animal) **NÃO É** critério de exclusão — é irrelevante para o valor bromatológico bruto do tecido, que é uma propriedade físico-química do substrato, não da disciplina de quem o mediu. Isso não se aplica a `bioavailability_factors`, que **DEVE** continuar refletindo diferenças de absorção específicas de *Canis lupus familiaris* independentemente da fonte do dado bromatológico bruto.
- [ ] Nenhum nutriente aparece simultaneamente em `nutrients` com uma chave duplicada — impossível estruturalmente dado `additionalProperties: false` sobre um objeto JSON, mas **DEVE** ser verificado na geração se o processo usa merge de dicionários.

---

## 18. Erros Comuns

| Erro | Por que invalida | Correção |
|---|---|---|
| Omitir uma das 43 chaves de nutriente | Viola `minProperties: 43` (e, em geradores automáticos, tipicamente indica bug de iteração) | Garantir que todo gerador itere sobre o catálogo fixo de 43 chaves, nunca apenas sobre os dados disponíveis |
| Usar `status: "measured"` com `value: null` | Viola o ramo `measured` do `oneOf` (`value` é `number`, não `null`) | Se o valor não é conhecido, usar `status: "missing"` |
| Usar `status: "missing"` mas incluir `unit`/`source_ref` | Viola `additionalProperties: false` do ramo `missing` | Remover `unit`/`source_ref`; usar apenas `status, value, reason, anomaly_ref` |
| Usar unidade fora do enum de 7 valores (ex.: `kcal_per_kg_DM`) | Essas unidades não existem mais no contexto de `NutrientEntry` (Seção 15.2) | Confirmar que a unidade pertence a `{g, mg, ug, IU, kcal, pct, ratio}`; conversões de outras unidades pertencem à camada de integração |
| `basis` diferente de `"as_fed"` em qualquer nível | Viola `const: "as_fed"` | Nunca gravar `dry_matter` ou `energy_normalized` em arquivo de ingrediente |
| `source_ref`/`anomaly_ref` sem prefixo `REF_` ou com minúsculas | Viola regex `^REF_[A-Z0-9_]+$` | Sempre `REF_` seguido de maiúsculas/dígitos/underscore |
| Popular `coverage_excluded_nutrients` em vez de marcar `status: "missing"`/`"not_applicable"` na chave correspondente em `nutrients` | Campo deprecated não substitui o contrato de 3 estados; a chave ainda precisa existir em `nutrients` | Sempre expressar ausência via `status` dentro de `nutrients`, nunca só via lista externa |
| `ingredient_id` em CamelCase ou com espaços | Viola regex `^[a-z][a-z0-9_]*$` | snake_case, minúsculas, começando com letra |
| `IngredientGroup.ingredient_count` divergente do tamanho real de `ingredients[]` | Não é erro de JSON Schema per se, mas quebra integridade referencial exigida operacionalmente | Recalcular `ingredient_count` a cada merge |
| `safety_alerts[]` sem `severity` ou `message` | Viola `required` do item | Incluir os 4 campos obrigatórios; `risk`/`mitigation` são aceitos como extras, não substitutos |
| Confundir `oneOf` com `anyOf` ao escrever um gerador customizado que aceita múltiplos ramos simultaneamente | Um `NutrientEntry` que satisfaz 2 ramos do `oneOf` (ex.: tem `value` numérico E `reason`) é rejeitado | Gerar cada `NutrientEntry` a partir de exatamente um template de estado, nunca mesclando campos de estados diferentes |

---

## 19. Notas de Migração (v1.x → v2.0 desta especificação / schema v3.x)

| Conceito v1.x (obsoleto) | Substituído por | Notas |
|---|---|---|
| `TypedMeasure` (`value, unit, basis, source_ref, confidence?, note?`) aplicado uniformemente a todo valor numérico do documento | `NutrientEntry` com `oneOf` de 3 estados, aplicável apenas a `bromatological_profile.nutrients` | O conceito de "toda métrica usa a mesma estrutura" foi abandonado em favor de um contrato específico para nutrientes que força declaração explícita de ausência |
| `coverage_excluded_nutrients` como mecanismo primário de declarar ausência (`nutrients_count + coverage_excluded_count == 41`) | Toda chave (43, não 41) sempre presente em `nutrients`, com `status` explícito | `coverage_excluded_nutrients` sobrevive apenas como campo legado, sem função normativa |
| Universo de 41 nutrientes | Universo de 43 nutrientes | As 2 chaves adicionais são `methionine_plus_cystine_g` e `phenylalanine_plus_tyrosine_g`, anteriormente tratadas como variáveis calculadas pelo solver e agora parte do contrato de dados do ingrediente (tipicamente `status: "missing"`) |
| Enum de 17 `unit` (incluindo unidades de idade, peso corporal, dose) | Enum de 7 `unit` (`g, mg, ug, IU, kcal, pct, ratio`) | As unidades removidas nunca pertenceram ao domínio de nutrientes de ingrediente; eram vazamento de outros contextos do sistema |
| `metadata.source_citation` + `metadata.evidence_tier` (`TIER_A`/`TIER_B`) | `metadata.usda_fdc_id` + `metadata.usda_description` + `metadata.data_confidence` | Rastreabilidade granular por FDC ID substitui citação textual livre; `data_confidence` substitui a classificação em tiers |
| `safety_alerts[].risk` + `safety_alerts[].mitigation` como campos obrigatórios | `safety_alerts[].type` + `severity` + `message` + `source_ref` como obrigatórios | `risk`/`mitigation` tornam-se opcionais/complementares — permitidos mas não exigidos pelo schema |
| `TypedMeasureRange` (`min, max, unit, basis, source_ref, confidence?, note?`) | Estrutura equivalente dentro de `bioavailability_factors.variability_ranges`, sem validação formal de schema (campo `additionalProperties: {}`) | Convenção de domínio preservada, mas não mais imposta estruturalmente pelo JSON Schema |

---

## 20. Apêndices

### 20.1 Exemplo Completo Mínimo de `Ingredient` (truncado nos nutrientes)

```json
{
  "ingredient_id": "chicken_liver_raw",
  "display_name": "Fígado de Frango Cru",
  "category": "organ_secreting",
  "requires_cooking": false,
  "bromatological_profile": {
    "basis": "as_fed",
    "reference_mass_g": 100,
    "nutrients": {
      "protein_g": {
        "status": "measured",
        "value": 16.9,
        "unit": "g",
        "basis": "as_fed",
        "source_ref": "REF_USDA_FDC_171060"
      },
      "vitamin_a_iu": {
        "status": "not_applicable",
        "value": null,
        "reason": "sourced from supplement/fortification; excluded from as_fed matrix per formulation_rules",
        "anomaly_ref": "REF_FORMULATION_RULES_EXCLUSION"
      },
      "biotin_ug": {
        "status": "missing",
        "value": null,
        "reason": "not measured in USDA FDC for this ingredient",
        "anomaly_ref": "REF_MISSING_BIOTIN"
      }
      // ... as 40 chaves restantes do catálogo (Seção 16) DEVEM estar presentes
    }
  },
  "bioavailability_factors": {
    "iron_type": "heme",
    "phytate_penalty": false,
    "oxalate_penalty": false
  },
  "lp_constraints": {
    "max_inclusion_pct": 5.0,
    "min_inclusion_pct": 0.0,
    "basis": "as_fed",
    "risk_flags": ["vitamin_A_toxicity"]
  },
  "safety_alerts": [
    {
      "type": "microbiological",
      "severity": "warning",
      "message": "Salmonella, Campylobacter",
      "source_ref": "REF_SAFETY_POULTRY_RAW_PATHOGENS"
    }
  ],
  "metadata": {
    "usda_fdc_id": "171060",
    "usda_description": "Chicken, liver, all classes, raw",
    "data_confidence": "HIGH",
    "last_validated": "2026-07-10"
  }
}
```

### 20.2 Glossário Rápido

- **AAFCO** — Association of American Feed Control Officials; padrão nutricional de referência para alimentação animal.
- **as_fed** — "como fornecido"; base de peso úmido/cru, oposta a matéria seca.
- **FDC** — FoodData Central, base de dados nutricional do USDA.
- **Goal Programming** — variante de programação linear que minimiza desvios ponderados de múltiplas metas simultâneas, em vez de otimizar uma única função objetivo.
- **oneOf** — palavra-chave JSON Schema que exige que o documento satisfaça exatamente um, entre vários subsquemas candidatos.

### 20.3 Checklist Final de Entrega por Ingrediente

- [ ] 43/43 chaves de nutriente presentes.
- [ ] Todo estado `oneOf` internamente consistente (Seção 9.5).
- [ ] `lp_constraints` e `bioavailability_factors` preenchidos por categoria (Seções 11–12).
- [ ] ≥ 1 `safety_alert` do tipo `microbiological`.
- [ ] `metadata` com FDC ID real ou justificativa de fonte alternativa (literatura veterinária).
- [ ] `ingredient_id` e `ingredient_count`/`ingredient_ids` do grupo pai sincronizados.
- [ ] `_db_metadata.total_ingredients` e `nutrients_per_ingredient` atualizados após o merge.
