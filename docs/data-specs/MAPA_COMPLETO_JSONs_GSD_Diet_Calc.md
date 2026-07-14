# Mapa Completo dos Arquivos JSON — GSD Diet Calc

**Versão do banco:** 2.2.0 | **Data:** 2026-07-11 | **Espécie-alvo:** *Canis lupus familiaris* (Pastor Alemão, fases crescimento e manutenção adulta) | **Regulatório:** AAFCO Large Breed Growth | **Base energética global:** per 1000 kcal EM (energy-normalized), assumindo 3750 kcal/kg MS | **Fase idosa/sênior:** não contemplada nos dados atuais

---

## 1. Visão Arquitetural do Sistema

O GSD Diet Calc é um sistema de formulação de dietas caninas cruas (raw feeding) baseado em **Programação Linear com Goal Programming**. O solver recebe dados de ingredientes, restrições nutricionais/toxicológicas, e targets energéticos, e produz proporções ótimas de inclusão que respeitam: mínimos AAFCO para raças grandes, limites de segurança superior (SULs), antagonismos minerais, limites de inclusão por categoria, e templates estruturais (PMR/BARF).

O sistema é composto por **9 arquivos JSON** que se dividem em três camadas funcionais:

- **Camada de Dados Brutos** (o que entra no solver): `DB_ingredientes.json`, `growth_energy_skeletal.json`, `scenarios.json`
- **Camada de Regras e Restrições** (o que limita o solver): `formulation_rules.json`, `constraints.json`, `toxicological_limits.json`, `objective_weights.json`
- **Camada de Metadados e Proveniência** (o que garante rastreabilidade): `audit_provenance.json`, `lp_parameters.schema.json`

Existe um arquivo adicional — `lp_parameters.schema.json` (~44KB) — que é o JSON Schema de validação. Ele valida a estrutura dos parâmetros do solver (domains.lp_solver), **não** os dados de ingredientes. O `DB_ingredientes.json` é intencionalmente **órfão** em relação ao schema: ele tem estrutura própria, não validada por `lp_parameters.schema.json`.

A conversão entre a base de dados (as_fed/100g) e o espaço do solver (energy_normalized/1000kcal) é responsabilidade do **build pipeline** — uma camada de integração que ainda não existe como código, mas cujas regras estão documentadas em `audit_provenance.json` (seção `algorithm_logic`) e implícitas nos `derived_from` espalhados pelos JSONs de constraints.

---

## 2. DB_ingredientes.json — Banco Unificado de Ingredientes

**Caminho relativo:** `../../data/DB_ingredientes.json`
**Tamanho:** ~168KB (171837 bytes), 4763 linhas
**Status do schema:** ÓRFÃO — fora do `lp_parameters.schema.json`
**Versão:** 2.2.0

### 2.1 Propósito e Motivação

Este é o repositório central de dados composicionais de todos os ingredientes disponíveis para o solver. Cada ingrediente contém seu perfil bromatológico completo (41 nutrientes), fatores de biodisponibilidade, restrições individuais de inclusão (lp_constraints), alertas de segurança, e metadados de proveniência inline. O banco existe porque o solver precisa de valores numéricos de concentração nutricional para montar a matriz de coeficientes `a_ij` da formulação de goal programming. Sem este banco, não há dados para otimizar.

### 2.2 Estrutura Interna

O arquivo é um objeto JSON com dois blocos principais:

**`_db_metadata`** (linhas 2-26): Bloco de metadados do banco. Contém `db_name`, `version` (atualmente "2.2.0"), `created_date`, `last_updated`, `schema_ref` (aponta para `lp_parameters.schema.json`, embora este não valide este arquivo), `template_ref`, `target_species`, `breed`, `lifestage`, `standard` (AAFCO), `nutrients_per_ingredient` (41), `total_ingredients` (20), e listas de status por fonte: `validated_sources` (bovinos), `pending_sources` (aves), `partial_sources` (aves, suinos, peixes). Este bloco revela o estado atual da curadoria: apenas os bovinos estão 100% validados contra dados USDA FDC.

**`protein_sources`** (linhas 27-4763): Objeto aninhado organizado por grupos zoológicos. Cada chave de nível 1 (bovinos, aves, suinos, peixes) contém:
- `common_name`: Nome vulgar do grupo (ex: "Bovinos (Bos taurus)")
- `animal_prefix`: Prefixo dos ingredient_ids (ex: "beef")
- `status`: VALIDATED / PARTIAL / PENDING
- `validation_date`, `validation_tool`, `validation_result`
- `ingredient_count`: Número de ingredientes no grupo
- `ingredient_ids`: Array de todos os IDs do grupo
- `ingredients`: Array de objetos de ingrediente individuais

### 2.3 Estrutura de Cada Ingrediente

Cada ingrediente no array `ingredients` contém:

**Campos de identificação:**
- `ingredient_id`: Identificador único no padrão `{prefix}_{cut}_{state}` (ex: `beef_liver_raw`, `chicken_heart_raw`). Segue uma taxonomia interna.
- `display_name`: Nome em português descritivo (ex: "Fígado Bovino Cru")
- `category`: Enum da categoria taxonômica do ingrediente. **Categorias atualmente em uso (7):** `blood_source`, `connective_tissue`, `fish`, `muscle_meat`, `muscle_organ`, `organ_non_secreting`, `organ_secreting`. Outras categorias (como `bone`, `fat_source`, `supplement`) são planejadas para ingredientes futuros. Esta categoria é crítica porque alimenta o mapeamento de `formulation_rules._inclusion_semantics.category_to_ingredient_mapping`.
- `requires_cooking`: Booleano (false para todos os ingredientes atuais, pois o sistema é para dietas cruas).

**`bromatological_profile`** — O núcleo dos dados:
- `basis`: Sempre `"as_fed"` (como fornecido, incluindo umidade natural)
- `reference_mass_g`: Sempre 100 (os valores são por 100g do alimento)
- `nutrients`: Objeto com até 41 chaves nutricionais. Cada nutriente segue o TypedMeasure: `{"value": <número>, "unit": "<enum>", "basis": "as_fed", "source_ref": "REF_USDA_FDC_<NNNNNN>"}`. As unidades seguem o enum global de 17 unidades (g, mg, ug, IU, kcal, pct, etc.). O basis aqui é sempre `as_fed` porque o build pipeline fará a conversão para `energy_normalized`.

**IMPORTANTE:** O espaço do DB e o espaço do solver têm **dois conjuntos diferentes de 41 nutrientes**, com overlap parcial. O DB (as_fed/100g) armazena 41 campos: 34 nutrientes principais + 7 excluídos via `coverage_excluded_nutrients`. O solver (energy_normalized/1000kcal) otimiza outros 41 nutrientes (definidos em `formulation_rules.nutrient_matrix`). A conversão entre os dois espaços envolve renomeação (remoção de sufixo de unidade), conversão de unidade (11 nutrientes: mg→g ou ug→mg), e computação combinada (2 pares de aminoácidos).

**41 campos do DB (as_fed/100g, com sufixo de unidade):** `arginine_g`, `cystine_g`, `histidine_g`, `isoleucine_g`, `leucine_g`, `lysine_g`, `methionine_g`, `phenylalanine_g`, `threonine_g`, `tryptophan_g`, `tyrosine_g`, `valine_g` (aminoácidos), `protein_g`, `fat_g` (macronutrientes), `calcium_mg`, `phosphorus_mg`, `magnesium_mg`, `sodium_mg`, `potassium_mg`, `chloride_mg`, `iron_mg`, `copper_mg`, `zinc_mg`, `manganese_mg`, `selenium_ug`, `iodine_ug` (minerais), `vitamin_a_iu`, `vitamin_d3_iu`, `vitamin_e_iu`, `vitamin_k_ug`, `thiamine_b1_mg`, `riboflavin_b2_mg`, `pantothenic_acid_b5_mg`, `niacin_b3_mg`, `pyridoxine_b6_mg`, `folic_acid_b9_ug`, `cobalamin_b12_ug` (vitaminas), `linoleic_acid_g`, `ala_alpha_linolenic_acid_g`, `ara_arachidonic_acid_g`, `epa_plus_dha_g`, `choline_mg` (lipídios/compostos). Destes, `biotin_ug` é listado em `coverage_excluded_nutrients` mas **não** aparece como campo populado em nenhum ingrediente — está no conjunto de exclusão apenas. O solver tem 2 nutrientes adicionais (`methionine_plus_cystine_g`, `phenylalanine_plus_tyrosine_g`) computados a partir de aminoácidos individuais. Nutrientes como `moisture_pct` e `ash_pct` existem internamente nos ingredientes mas **não** fazem parte dos 41 campos unificados do DB — são campos auxiliares para cálculo de energia metabolizável.

- `coverage_excluded_nutrients`: Lista de strings (apenas keys, NÃO objeto com valores). Enumera nutrientes que este ingrediente não reporta (ex: `["iodine_ug", "chloride_mg", "biotin_ug"]`). A soma de entradas em `nutrients` + entradas em `coverage_excluded_nutrients` = 43 sempre (não 41, pois alguns nutrientes excluídos como `biotin_ug` estão fora do conjunto unificado de 41 campos do DB). Zero sobreposição entre as duas listas.

**`bioavailability_factors`**: Fatores de correção por nutriente para este ingrediente específico. Por exemplo, o fígado pode ter fator de retenção de vitamina A que reflete a variabilidade de 400% no teor de retinol entre lotes. Estes fatores multiplicam os valores do `bromatological_profile` antes de entrar no solver.

**`lp_constraints`**: Restrições individuais de inclusão deste ingrediente específico. Contém `max_inclusion_pct` (ex: fígado bovino tem limite individual de 5% as_fed) e `min_inclusion_pct`. Estes limites operam POR INGREDIENTE INDIVIDUAL, em contraste com os limites de `formulation_rules.inclusion_limits` que operam por SOMA DE CATEGORIA. O solver deve aplicar ambos e o mais restritivo prevalece.

**`safety_alerts`**: Alertas específicos do ingrediente (ex: fígado alerta sobre toxicidade por vitamina A, osso cru alerta sobre flutuação de biodisponibilidade de cálcio 35-80%).

**`metadata`**: Proveniência inline — `usda_fdc_id`, `usda_description`, `data_confidence`, `last_validated`.

### 2.4 Ingredientes Atuais (20 total)

- **bovinos (11, VALIDATED):** beef_muscle_raw, beef_lung_raw, beef_foot_tendon_raw, beef_tail_raw, beef_tongue_raw, beef_blood_raw, beef_heart_raw, beef_green_tripe_raw, beef_liver_raw, beef_kidney_raw, beef_spleen_raw
- **aves (6, PARTIAL/PENDING):** chicken_muscle_raw, chicken_heart_raw, chicken_liver_raw, chicken_kidney_raw, chicken_foot_tendon_raw, chicken_blood_raw
- **suínos (2, PARTIAL):** pork_muscle_raw, pork_liver_raw
- **peixes (1, PARTIAL):** salmon_atlantic_raw

> **Nota:** Aves incluem apenas 6 ingredientes no DB real. `chicken_gizzard_raw`, `chicken_back_neck_raw`, `chicken_wing_raw` (mencionados em documentação anterior) **não existem** no DB_ingredientes.json v2.2.0. Peixe é `salmon_atlantic_raw`, não `salmon_raw`.

### 2.5 Relações com Outros JSONs

- **Consumido por:** O build pipeline lê este arquivo, converte as_fed → energy_normalized (por 1000kcal) renomeando os 11 nutrientes com conversão de unidade e computando os 2 pares combinados de aminoácidos, e gera a matriz `a_ij` do solver. Este processo ainda não está implementado como código.
- **Referencia `lp_parameters.schema.json`** no `_db_metadata.schema_ref`, mas na prática é validado por scripts Python separados (`validate_bovinos_deep.py`, `validate_master.py`).
- **As categorias (`category`) de cada ingrediente** alimentam o mapeamento em `formulation_rules._inclusion_semantics.category_to_ingredient_mapping`.
- **Os `source_ref`** de cada nutriente (ex: `REF_USDA_FDC_170196`) seguem a convenção `^REF_[A-Z0-9_]+$` mas referenciam fontes externas (USDA FoodData Central) e não são resolvidos dentro dos JSONs do projeto — apenas os `REF_*` internos estão em `audit_provenance.json`.

---

## 3. formulation_rules.json — Regras de Formulação Dietética

**Caminho:** `../../data/formulation_rules.json`
**Tamanho:** ~940 linhas
**Domínio no schema:** `domains.ingredients.formulation_rules`
**Status no schema:** Validado

### 3.1 Propósito e Motivação

Este arquivo define as regras que governam como os ingredientes podem ser combinados em uma dieta. Ele contém: (a) limites de inclusão por categoria de ingrediente, (b) templates estruturais de dieta (PMR, BARF, consolidado), (c) fatores de biodisponibilidade por ingrediente/parâmetro, (d) dados de perda nutricional por processamento térmico (argumento quantitativo pró-dietas cruas), (e) dados de digestibilidade ATTD (raw vs extrusado), (f) dosagens de suplementação terapêutica, e (g) a **matriz nutricional de 41 nutrientes** com seus targets (NutrientTarget). A matriz de 41 é a fonte autoritativa de quais nutrientes o solver deve otimizar e quais são seus valores-alvo por 1000kcal energy-normalized. Este arquivo é o **ponto de entrada principal para a construção das constraints LP** — o `constraints.json` é derivado parcialmente dele (campos `derived_from` em constraints.json apontam para `formulation_rules.nutrient_matrix` e `formulation_rules.inclusion_limits`).

### 3.2 Estrutura Interna

O arquivo é um objeto JSON com 8 seções de nível superior:

**`_inclusion_semantics`** (adicionado na sessão de correção 2.5): Bloco de metadados que resolve a ambiguidade sobre se os limites de inclusão se aplicam por ingrediente individual ou por soma de categoria. Define `scope: "category_sum"` e contém `category_to_ingredient_mapping` que mapeia nomes de categoria genéricos (liver, kelp, salt_nacl, copper_supplement, protein_base, fat_source) para arrays de `ingredient_id` reais do DB. Usa wildcards como `_all_muscle_meat` e `_all_fat_source` que o build pipeline deve expandir.

**`inclusion_limits`** (6 entradas): Array de objetos com `ingredient_id` (nome da categoria), `classification`, `max_pct`, `min_pct`, `basis` (as_fed), `justification_ref`, `risk_flags`, `source_ref`. As 6 entradas são: liver (max 5%), kelp (max 0.5%), salt_nacl (max 1.5%), copper_supplement (max 0.1%), protein_base (min 22%), fat_source (min 8%). O campo `risk_flags` enumera riscos biológicos (ex: `vitamin_A_toxicity`, `retinol_variability_400pct`, `hypernatremia`, `iodine_oversupplementation`). O `max_pct_justification` em alguns campos explica por que o limite existe mesmo quando a proteção primária vem do SUL.

**`diet_templates`** (3 entradas): TPL_PMR (80/10/5/5/0), TPL_BARF (70/10/5/5/7/2/1.0), TPL_PMR_BARF_CONSOLIDATED (75/10/5/5/3.5/1.5). Cada template tem `components` com percentuais, `total_pct` (100 em todos os 3 — as somas dos componentes são exatamente 100%: PMR=80+10+5+5+0, BARF=70+10+5+5+7+2+1, Consolidado=75+10+5+5+3.5+1.5), `lp_constraint_string` (ex: `x_muscle=0.80, x_bone=0.10, x_liver=0.05, x_organs=0.05`), `basis` (as_fed), e `source_ref`. O template consolidado reserva 1.5% para suplementos (kelp + sal + cobre). O template BARF reserva 1% para suplementos. Nota: o `FLAG_BARF_TOTAL` em audit_provenance descreve inconsistências nos *dados fonte originais* (DOC1/DOC2/DOC3) — os templates curados aqui já foram normalizados para 100%.

**`bioavailability_factors`** (5 entradas): Fatores de biodisponibilidade que afetam como o solver interpreta os valores nutricionais. Os 5 fatores são: BIO_KELP_IODINE_RANGE (iodo no kelp varia 0.5-4.5 mg/g MS), BIO_KELP_IODINE_ABSORPTION (eficiência de absorção de iodo do kelp ~25% vs KI purificado), BIO_KELP_SODIUM (teor de sódio no kelp ~3.0% MS), BIO_VISCERA_VIT_A_VAR (fígado/visceras têm 400% variação em retinol), BIO_RAW_BONE_CA_ABSORPTION (cálcio em ossos carnudos crus flutua 35-80% biodisponibilidade). Cada entrada tem `factor_id`, `ingredient_id`, `parameter`, `values` (min/max com unidade e basis), `risk_description_ref`.

**`processing_loss_factors`** (3 sub-seções): Dados de perda nutricional por processamento térmico e armazenamento — fundamentais para justificar por que dietas cruas precisam de menores níveis de fortificação. Contém: (a) `extrusion_conditions` — parâmetros de extrusão (temperatura, pressão, umidade); (b) `vitamin_retention` — retenção de 6 vitaminas lipossolúveis/hidrossolúveis após extrusão (valores típicos: 40-90% vs 100% em dietas cruas sem processamento térmico); (c) `storage_loss` — perdas por armazenamento (lipossolúveis: percentual variável; reação de Maillard: limiar de lisina). Estes dados são o argumento quantitativo central do projeto a favor de dietas cruas.

**`nutrient_matrix`** (41 entradas NutrientTarget): A matriz central do sistema. Cada entrada contém `nutrient_id` (nome no espaço do solver, ex: `calcium_g`), `display_name`, `unit`, `basis` (energy_normalized — per 1000kcal), `min_value` (geralmente o mínimo AAFCO large breed growth), `max_value` (quando aplicável), `aaFco_min`, `nrc_min`, `fediaf_min`, `retention_factor` (fator de retenção pós-processamento), `notes`, `source_ref`. É desta matriz que os `nutrient_bounds` em `constraints.json` são derivados (cada entrada gera um `CSTR_NB_*_MIN`). Os 41 nutrientes incluem os 10 aminoácidos essenciais individuais + 2 pares combinados (Met+Cys, Phe+Tyr), macronutrientes (protein, fat), minerais (Ca, P, Mg, Na, K, Cl, Fe, Cu, Zn, Mn, Se, I), vitaminas (A, D3, E, B1, B2, B5, B3, B6, B9, B12), lipídios (linoleic, ALA, ARA, EPA+DHA), e colina. **NÃO estão na matriz:** biotina B7, vitamina C, vitamina K, taurina, L-carnitina (não requeridos), cistina separada (coberta como Met+Cys), tirosina separada (coberta como Phe+Tyr). Nota: embora `biotin_ug` e `vitamin_k_ug` apareçam no `coverage_excluded_nutrients` do DB, eles não têm entrada correspondente na matrix de 41 — são rastreados no DB mas não otimizados pelo solver.

**`digestibility`** (8 chaves): Dados de digestibilidade que fundamentam a vantagem das dietas cruas sobre extrusadas. Contém: `raw_ATTD_protein_fat_pct` (90% — digestibilidade total aparente da proteína e gordura em dietas cruas), `extruded_ATTD_protein_fat_pct` (80% — dietas extrusadas tradicionais), `BARF_ATTD_description`, `BARF_mineral_nonconformity` (nota sobre não-conformidade mineral de dietas BARF), `microbiome_raw_benefits` (benefícios do microbioma em dietas cruas), `microbiome_extruded_risks` (riscos do microbioma em extrusadas), `TyG_index` (índice triglicerides-glicose, menor em cruas), `source_ref`. A diferença ATTD 90% vs 80% é o fundamento quantitativo da superioridade digestiva das dietas cruas.

**`supplement_dosages`** (4 suplementos): Informações de dosagem para suplementação terapêutica ou corretiva. Os 4 suplementos são: (a) `calcidiol_25_OH_D3` — dose 40.5% energy-normalized, superior a D3 para elevar/sustentar níveis séricos de 25(OH)D (duração: 1 mês); (b) `vitamin_D3` — dose 5510 IU/kg DM (necessário para níveis ideais de 25(OH)D em cães adultos saudáveis), AAFCO min 125 IU/1000kcal, max 750 IU/1000kcal, com nota de que cães NÃO sintetizam vitamina D3 na pele via luz solar (dependência dietética completa); (c) `calcium_therapeutic` — dose 22 mg/kg/dia via citrato de cálcio, condicional a deficiência confirmada, com warning de que suplementação de cálcio é desnecessária e perigosa para cães em crescimento com dietas completas; (d) `iodine_via_kelp` — dose 0.175 mg/1000kcal (NRC 2006), com nota documentando que Doc1 contém erro de unidade (diz "0.175 ug" mas as demais referências confirmam mg).

### 3.3 Relações com Outros JSONs

- **Fonte para `constraints.json`:** Os `inclusion_limits` geram os 6 `CSTR_INCL_*` em constraints.json. Os `nutrient_matrix` geram os 41 `CSTR_NB_*` em constraints.json. Cada constraint em constraints.json tem `derived_from: "formulation_rules.inclusion_limits"` ou `derived_from: "formulation_rules.nutrient_matrix"`.
- **Referencia `audit_provenance.json`** via `source_ref` (ex: `REF_INCL_LIVER_JUST`, `REF_NUTR_MATRIX_41`, `REF_DIET_PMR`, `REF_BIO_KELP_IODINE`).
- **Referencia `DB_ingredientes.json`** indiretamente: o `category_to_ingredient_mapping` em `_inclusion_semantics` lista ingredient_ids que devem existir no DB. O build pipeline deve expandir `_all_muscle_meat` para todos os ingredientes com `category: "muscle_meat"` no DB.
- **Consumido por `scenarios.json`**: Os 17 targets de cada cenário são um subconjunto dos 41 nutrientes da matriz, com valores específicos para cada cenário de crescimento.

---

## 4. constraints.json — Constraints do Solver LP

**Caminho:** `../../data/constraints.json`
**Tamanho:** ~42KB, 1486 linhas
**Domínio no schema:** `domains.lp_solver.constraints`
**Status no schema:** Validado

### 4.1 Propósito e Motivação

Este é o arquivo que o solver LP consome diretamente como entrada de restrições. Ele contém todas as constraints no formato pronto para montar as matrizes do problema de programação linear. Cada constraint tem uma estrutura uniforme com `constraint_id`, `name`, `type`, `human_readable`, `lp_coefficients` (contendo `bounds` com `variables`, `sense`, `rhs`, e `variables_referenced`), `source_ref`, `solver_behavior`, e opcionalmente `derived_from`, `pathophysiology_ref`, `regulatory_gap`, `note`. O `solver_behavior` é sempre `HARD_FAIL_INFEASIBLE` — significando que se esta constraint for violada, o solver deve declarar o problema infactível em vez de relaxá-la.

### 4.2 Estrutura Interna — 4 Seções

**`mineral_antagonisms`** (5 entradas): Constraints de razão entre pares de minerais/aminoácidos. São: CSTR_CA_P_RATIO (1.1 ≤ Ca/P ≤ 1.3), CSTR_ZN_CU_RATIO (Zn/Cu ≤ 12), CSTR_FE_ZN_RATIO (Fe/Zn ≤ 3), CSTR_CA_MG_RATIO (12 ≤ Ca/Mg ≤ 18), CSTR_LYS_ARG_RATIO (1.0 ≤ Lys/Arg ≤ 1.4). Cada uma é do tipo `ratio_bound` e gera 1 ou 2 bounds LP (uma desigualdade dupla para faixas). As variáveis referenciadas usam nomes do espaço do solver (ex: `calcium_g`, `magnesium_g`, `selenium_mg`). As justificativas biológicas são referenciadas via `biological_justification_ref` (ex: `REF_MIN_ANT_CA_P` explica que fora da faixa 1.1-1.3 ocorre bloqueio da absorção de P ou secreção de PTH).

**`toxicological_limits`** (8 entradas): Constraints de limite superior máximo (SUL — Safe Upper Limit) para nutrientes tóxicos. São: copper_mg (≤100), iron_mg (≤130), sodium_g (≤3.75), vitamin_a_iu (≤9375), vitamin_d3_iu (≤750), iodine_mg (≤2.5), zinc_mg (≤300), manganese_mg (≤15). Todas são `HARD_INEQUALITY_MAX` do tipo `nutrient_bound`. Cada uma tem `derived_from: "toxicological_limits.<nutrient_id>"` apontando para o `toxicological_limits.json`, e `pathophysiology_ref` com a fisiopatologia da toxicidade. Três SULs (Cu, Zn, Mn) têm `regulatory_gap: true` indicando que AAFCO não estabelece formalmente limite superior — os valores são estimados por extrapolacão patofisiológica (NRC 2006, FEDIAF 2021). A constraint de cobre é a mais crítica: sem limite formal AAFCO, o valor 100mg/1000kcal baseia-se em hepatotoxicidade por reação de Fenton.

**`inclusion_constraints`** (6 entradas): Constraints de limite de inclusão por categoria de ingrediente no espaço LP. São: CSTR_INCL_MAX_LIVER (x_liver ≤ 0.05), CSTR_INCL_MAX_KELP (x_kelp ≤ 0.005), CSTR_INCL_MIN_PROTEIN_BASE (x_protein_base ≥ 0.22), CSTR_INCL_MIN_FAT_SOURCE (x_fat_source ≥ 0.08), CSTR_INCL_MAX_SALT_NACL (x_salt_nacl ≤ 0.015), CSTR_INCL_MAX_COPPER_SUPP (x_copper_supplement ≤ 0.001). Todas derivadas de `formulation_rules.inclusion_limits`. As variáveis aqui (x_liver, x_kelp, etc.) representam proporções de inclusão no espaço LP (somam 1.0 = 100%). Nota: os limites de sal e cobre são descritos como "camada secundária de segurança" — a proteção primária vem dos SULs respectivos.

**`nutrient_bounds`** (41 entradas): Constraints de mínimo AAFCO large breed growth para cada um dos 41 nutrientes da matriz. Todas são `HARD_INEQUALITY_MIN` do tipo `nutrient_bound` com `derived_from: "formulation_rules.nutrient_matrix"`. Exemplos: protein_g ≥ 56.25, calcium_g ≥ 3.0, phosphorus_g ≥ 2.5, lysine_g ≥ 2.25, zinc_mg ≥ 25.0, vitamin_a_iu ≥ 1250. Cada entrada tem um `note` com o valor AAFCO e a unidade. O total de constraints é: 5 antagonismos (gerando 8 bounds LP: CA_P=2, ZN_CU=1, FE_ZN=1, CA_MG=2, LYS_ARG=2) + 8 toxicológicos + 6 inclusão + 41 nutricionais = 60 constraints, gerando exatamente 63 bounds LP individuais.

### 4.3 Relações com Outros JSONs

- **Derivado de `formulation_rules.json`:** As `inclusion_constraints` vêm de `formulation_rules.inclusion_limits`, os `nutrient_bounds` vêm de `formulation_rules.nutrient_matrix`.
- **Derivado de `toxicological_limits.json`:** Os `toxicological_limits` vêm diretamente dos SULs, com `derived_from` apontando para `toxicological_limits.copper_mg` etc.
- **Referencia `audit_provenance.json`** via `source_ref` e `pathophysiology_ref` (ex: `REF_SUL_CU_PATHO`, `REF_MIN_ANT_CA_P`, `REF_INCL_LIVER_JUST`).
- **Consumido pelo solver LP** diretamente — é a entrada de constraints do problema de otimização.
- **Os nomes de variável** (calcium_g, phosphorus_g, etc.) usam a convenção do espaço do solver, não do banco de dados (onde seriam calcium_g, phosphorus_g — nesse caso coincidem, mas em outros como selenium_ug↔selenium_mg há diferença).

---

## 5. toxicological_limits.json — Limites de Segurança Superior (SULs)

**Caminho:** `../../data/toxicological_limits.json`
**Tamanho:** ~117 linhas, 3447 bytes
**Domínio no schema:** não-validado diretamente (fonte para constraints.json)
**Status:** Fonte autoritativa dos SULs

### 5.1 Propósito e Motivação

Este arquivo é a fonte primária e autoritativa dos Safe Upper Limits (SULs) para nutrientes com potencial tóxico. Ele existe para separar a definição dos limites toxicológicos (motivação fisiopatológica, fundamentação regulatória) da sua representação como constraint LP (que fica em `constraints.json`). Esta separação permite que o `constraints.json` seja um arquivo puramente mecânico (pronto para o solver) enquanto este arquivo preserva o contexto biológico e regulatório.

### 5.2 Estrutura Interna

Array JSON simples com 8 objetos. Cada objeto contém:
- `nutrient_id`: Nome do nutriente no espaço do solver (ex: `copper_mg`, `vitamin_a_iu`)
- `sul`: Objeto TypedMeasure com `value`, `unit`, `basis` (sempre `energy_normalized`), `source_ref`
- `constraint_type`: Sempre `"HARD_INEQUALITY_MAX"`
- `solver_variable`: Nome da variável LP (igual ao `nutrient_id`)
- `pathophysiology_ref`: Referência à fisiopatologia em `audit_provenance.json`
- `regulatory_gap`: Booleano — true quando AAFCO não estabelece formalmente o limite (Cu, Zn, Mn)
- `source_ref`: Referência à fonte
- `note`: Explicação detalhada quando há gap regulatório ou contexto especial

Os 8 SULs cobrem: cobre (100mg, regulatory_gap=true, hepatotoxicidade por Fenton), ferro (130mg), sódio (3.75g), vitamina A (9375 IU, reabsorção osteoclastária excessiva), vitamina D3 (750 IU, calcificação metastática), iodo (2.5mg, efeito Wolff-Chaikoff), zinco (300mg, regulatory_gap=true, antagonismo Zn-Cu), manganês (15mg, regulatory_gap=true, neurotoxicidade parkinsoniana).

> **Nota:** O `toxicological_limits.json` é um array direto (não um dict com chave `safe_upper_limits`). Cada entry tem os campos acima diretamente no objeto. Isto difere de como `constraints.json` referencia estes dados (que é uma representação LP reformatada).

### 5.3 Relações com Outros JSONs

- **Fonte para `constraints.json`:** Cada entrada gera exatamente uma constraint `CSTR_SUL_*_MAX` em constraints.json. O campo `derived_from` na constraint aponta para `toxicological_limits.<nutrient_id>`.
- **Os `pathophysiology_ref`** resolvem para entradas em `audit_provenance.references` (ex: `REF_SUL_CU_PATHO` contém a cascata fisiopatológica completa: cobre livre → Fenton → radicais hidroxilo → peroxidação lipidica mitocondrial → apoptose hepatocitar).
- **Independente do `DB_ingredientes.json`** — os SULs são limites da dieta final, não dos ingredientes individuais.
- **Relação com `formulation_rules.inclusion_limits`:** Os limites de inclusão de ingredientes de risco (kelp, sal, cobre suplementar) operam como camada secundária de segurança abaixo dos SULs. Por exemplo: o SUL de iodo é 2.5mg/1000kcal, o limite de inclusão de kelp é 0.5% as_fed — mesmo que o kelp esteja dentro do limite de inclusão, se o teor de iodo variar para o máximo documentado (4.5mg/g MS), o SUL ainda pode ser violado.

---

## 6. objective_weights.json — Pesos da Função Objetivo (Goal Programming)

**Caminho:** `../../data/objective_weights.json`
**Tamanho:** 322 linhas
**Domínio no schema:** `domains.lp_solver.objective_weights`
**Status no schema:** Validado

### 6.1 Propósito e Motivação

Numa formulação de goal programming, o solver não apenas satisfaz constraints duras — ele minimiza desvios em relação a targets ideais. Este arquivo define os **pesos (penalties)** que o solver atribui a cada desvio. Quando o solver não consegue atingir o target exato de um nutriente, ele penaliza proporcionalmente o desvio. Os pesos determinam as **prioridades relativas**: o solver prefere violar um nutriente com peso baixo (ex: custo, peso 10) do que um com peso alto (ex: excesso de cálcio, peso 10000). Este arquivo é o que dá "personalidade" ao solver — é ele que faz o sistema preferir crescimento lento, evitar excesso de cálcio em caes castrados, e priorizar seguranca ortopédica sobre economia.

### 6.2 Estrutura Interna

Array JSON com 29 objetos (PEN_*). Cada penalty weight contém:
- `weight_id`: Identificador no padrão `PEN_<NUTRIENTE>_<DIRECAO>` (ex: `PEN_CA_POS`, `PEN_PROTEIN_NEG`, `PEN_CA_P_RATIO_SYM`)
- `variable`: Nome da variável no espaço do solver (ex: `calcium_g`, `selenium_mg`, `ca_p_ratio`, `caloric_density`, `cost_per_kg`). Notar que `ca_p_ratio` e `caloric_density` são **variáveis compostas** calculadas pelo solver, não variáveis LP simples — o ca_p_ratio é calcium_g/phosphorus_g e o caloric_density é kcal/kg_DM.
- `direction`: `positive_deviation` (penaliza excesso), `negative_deviation` (penaliza deficiência), ou `symmetric` (penaliza ambos os lados igualmente, usado apenas para PEN_CA_P_RATIO_SYM).
- `weight`: Valor numérico do peso (escala de 10 a 10000).
- `priority_tier`: Inteiro de 1 a 5, onde 1 é a prioridade mais alta.
- `description`: Texto descritivo em português explicando o que o peso penaliza e por quê.
- `source_ref`: Sempre `REF_ALGO_GOAL_PROG`.
- `solver_penalty_multiplier`: Dict com chaves por condição gonadal. Presente em apenas 2 penalties: PEN_CA_POS e PEN_CALORIC_POS. Estrutura: `{"neutered_early": {"multiplier": 1.5, "condition": "gonadal_status == neutered_early"}, "spayed_early": {"multiplier": 1.5, "condition": "gonadal_status == spayed_early"}}`. Quando o campo está ausente (27 das 29 entries), não há multiplicador condicional.
- `variable_note`: Notas adicionais em algumas entries explicando variáveis compostas ou targets implícitos.
- `note`: Notas extras (usado em PEN_CA_P_RATIO_SYM para explicar a relação com o hard constraint).

### 6.3 Distribuição dos 29 Pesos por Tier

- **Tier 1 (pesos 4000-10000, segurança crítica):** PEN_CA_POS (10000, excesso de Ca — risco ortopédico máximo), PEN_CA_P_RATIO_SYM (7000, desvio do ratio ideal), PEN_CA_NEG (5000, deficiência de Ca), PEN_VIT_AD3_POS (4000, toxicidade por acúmulo sistemático — nota: o weight_id sugere D3 mas a variável real é `vitamin_a_iu`, nome confuso por design)
- **Tier 2 (pesos 3000-6000, nutrição essencial e energia):** PEN_CALORIC_POS (6000, excesso calórico → crescimento acelerado), PEN_PHOSPHORUS_NEG (3000), PEN_PROTEIN_NEG (3000), PEN_ZINC_NEG (2000), PEN_VITAMIN_A_NEG (2000), PEN_VITAMIN_D3_NEG (2000)
- **Tier 3 (pesos 800-1500, micronutrientes importantes):** PEN_FAT_NEG (1500), PEN_LYSINE_NEG (1500), PEN_MET_CYS_NEG (1500), PEN_MAGNESIUM_NEG (1000), PEN_EPA_DHA_NEG (800), PEN_LINOLEIC_NEG (800), PEN_SODIUM_NEG (800), PEN_IRON_NEG (800), PEN_COPPER_NEG (800), PEN_SELENIUM_NEG (800), PEN_VITAMIN_E_NEG (800)
- **Tier 4 (pesos 400-600, micronutrientes secundários):** PEN_MANGANESE_NEG (400), POTASSIUM_NEG (600), CHOLINE_NEG (600), ALA_NEG (500), ARA_NEG (500), CHLORIDE_NEG (400), IODINE_NEG (400)
- **Tier 5 (peso 10, objetivo econômico):** PEN_COST_POS (10, custo — intencionalmente 400x menor que o tier 1 para nunca competir com segurança)

### 6.4 Variáveis Compostas

Duas entries referenciam variáveis que não são variáveis LP diretas: `ca_p_ratio` (calculada como calcium_g / phosphorus_g) e `caloric_density` (calculada como kcal/kg_DM a partir da soma dos ingredientes). Ambas requerem lógica especial no solver — o ratio é uma razão de duas variáveis de decisão e a densidade calórica depende da composição final da dieta.

### 6.5 Relações com Outros JSONs

- **Referencia `growth_energy_skeletal.json`** indiretamente: os `solver_penalty_multiplier` para PEN_CA_POS e PEN_CALORIC_POS aplicam-se quando `gonadal_status == neutered_early` ou `spayed_early`. Os perfis de status gonadal (com seus solver_penalty_multipliers) estão definidos em `growth_energy_skeletal.gonadal_status_profiles`. O build pipeline deve conectar os penalty multipliers dos perfis gonadais aos weights deste arquivo.
- **Os `variable`** usam nomes do espaço do solver, os mesmos que `constraints.json` e `scenarios.json`.
- **Relação com `scenarios.json`:** Os targets dos cenários definem os valores-alvo T_j da formulação de goal programming. Os weights deste arquivo definem os w_j. Juntos, formam a função objetivo: Min Σ w_j × (d_j_minus + d_j_plus). O solver busca a combinação de ingredientes cujos nutrientes totais se aproximem dos T_j com penalidade mínima ponderada pelos w_j.
- **Referencia `audit_provenance.json`** via `source_ref: "REF_ALGO_GOAL_PROG"` (que contém a formulação matemática completa do goal programming).

---

## 7. scenarios.json — Cenários de Otimização

**Caminho:** `../../data/scenarios.json`
**Tamanho:** 262 linhas
**Domínio no schema:** `domains.lp_solver.scenarios`
**Status no schema:** Validado

### 7.1 Propósito e Motivação

O solver precisa de um ponto de referência — um conjunto de valores-alvo para os nutrientes que a dieta deve tentar atingir. Diferentes estratégias de crescimento exigem diferentes alvos. Este arquivo define dois cenários contrastantes: crescimento rápido (desaconselhado, risco ortopédico elevado) e crescimento lento (recomendado). O cenário ativo (SCN_B) é o que o solver usa como padrão. O cenário de warning (SCN_A) existe como referência comparativa e como documentação do que acontece quando se ignora as recomendações.

### 7.2 Estrutura Interna

Array JSON com 2 objetos de cenário:

**SCN_A_RAPID_GROWTH** (`status: "WARNING_DO_NOT_OPTIMIZE"`): 17 targets. Densidade calórica 4500 kcal/kg DM, proteína 60g, gordura 25g, cálcio 4.5g, fósforo 4.0g, Ca:P ratio 1.125, ácido linoleico 3.25g, ALA 0.2g, ARA 0.075g, EPA+DHA 0.1g, magnésio 0.15g, sódio 0.75g, vitamina A 1250 IU, vitamina D3 125 IU, zinco 25mg, lisina 2.7g (+20% acima do AAFCO min), Met+Cys 2.1g (+20%). O target de lisina e Met+Cys são 20% acima do mínimo AAFCO porque o cenário de crescimento rápido exige aporte extra para sustentar a taxa de ganho de peso. Todos os targets usam basis `energy_normalized` (per 1000kcal), exceto caloric_density que usa `dry_matter`.

**SCN_B_SLOW_GROWTH** (`status: "ACTIVE_TARGET"`): 17 targets idênticos em estrutura, com valores distintos: densidade 3500 kcal/kg DM, proteína 50g, gordura 15g, cálcio 3.0g, fósforo 2.5g, Ca:P ratio 1.2, sódio 0.55g, lisina 2.25g (no AAFCO min), Met+Cys 1.75g (no AAFCO min). Vários nutrientes são idênticos entre os cenários (vitamina A 1250 IU, zinco 25mg, EPA+DHA 0.1g, ARA 0.075g) porque esses não mudam com a velocidade de crescimento — são fixos pelo mínimo regulatório.

Cada target tem `nutrient_id`, `value`, `unit`, `basis`, `source_ref` (sempre `REF_SCENARIO_CMP`), e opcionalmente `note` explicando decisões (ex: a nota do `ca_p_ratio` explica que é redundante com o hard constraint `CSTR_CA_P_RATIO`, mantido como referência histórica).

### 7.3 Relações com Outros JSONs

- **É consumido pelo solver** em conjunto com `objective_weights.json`: os targets T_j vêm dos scenarios, os pesos w_j vêm dos weights.
- **Subconjunto de `formulation_rules.nutrient_matrix`**: Os 17 nutrientes nos cenários são um subconjunto dos 41 da matriz. Nutrientes como tiamina, riboflavina, cobalamina, etc. não aparecem nos cenários porque seus mínimos AAFCO são garantidos pelos hard constraints (`CSTR_NB_*`), não precisando de otimização via goal programming.
- **Os valores de caloric_density** (3500 e 4500 kcal/kg DM) correspondem aos `NRG_DENSITY_CONTROLLED` e `NRG_DENSITY_RAPID` em `growth_energy_skeletal.json`.
- **Conecta-se a `growth_energy_skeletal.json`** porque o DER (Daily Energy Requirement) calculado a partir do Gompertz determina quantos 1000kcal o cão precisa por dia, e os targets por 1000kcal dos cenários são escalados pelo DER.

---

## 8. growth_energy_skeletal.json — Biologia do Crescimento e Energia

**Caminho:** `../../data/growth_energy_skeletal.json`
**Tamanho:** 1091 linhas
**Domínio no schema:** `domains.biology`
**Status no schema:** Validado

### 8.1 Propósito e Motivação

Este arquivo é o repositório de toda a biologia quantitativa do Pastor Alemão em crescimento: modelo de crescimento (Gompertz), tabela antropométrica mensal, marcos de maturação esquelética, requisitos energéticos (TER/DER), multiplicadores de energia por perfil de atividade, epidemiologia de DOD (Developmental Orthopedic Disease), perfis de status gonadal com impacto no solver, e biomarcadores metabólicos. Ele existe porque o solver precisa saber: (a) qual o peso corporal esperado para uma dada idade (para calcular TER = 70 × BW^0.75), (b) qual a DER resultante (TER × k), e (c) quantos 1000kcal a dieta deve fornecer. Além disso, fornece contexto biológico que afeta os pesos de penalidade (castração precoce → boost de penalidade de Ca e calorias).

### 8.2 Estrutura Interna — 7 Seções

**`gompertz_parameters`** (linhas 2-56): Modelo paramétrico de crescimento W(t) = W_max × exp(-b × exp(-c × t)). Contém 5 parâmetros: W_max_male (45kg para cães de trabalho/exposição e assistance_dogs), W_max_female (38kg apenas para working_exhibition_lines; assistance_dogs: not_specified_in_text), c_male (115 dias — ponto de inflexão), c_female (102 dias), b (2.5, inferido). Cada parâmetro tem `confidence` (measured/estimated/inferred), `unit`, e `source_ref`. O modelo Gompertz é a fonte CANÔNICA de peso para cálculos energéticos — a tabela antropométrica serve apenas como limites de validação.

**`weight_resolution_strategy`** (linhas 57-106): Seção crítica que resolve a ambiguidade entre o peso escalar do Gompertz e os intervalos [min, max] da tabela antropométrica. Define 4 regras: WRS_001 (usar Gompertz para cálculo de TER/DER), WRS_002 (validar W_gompertz contra [min, max] da tabela), WRS_003 (usar média da tabela APENAS como initial guess), WRS_004 (manter [min, max] na tabela, nunca converter para escalar). Inclui 2 protocolos de fallback: se Gompertz não calibrado → usar média com WARNING, se idade não na tabela → interpolar linearmente.

**`anthropometric_table`** (linhas 107-710): Tabela com 24 entradas mensais (meses 1-24). Cada entrada contém: `age_months`, `weight_male_kg` [min, max], `height_male_cm` [min, max], `weight_female_kg` [min, max], `height_female_cm` [min, max], `weekly_gain_kg`, `pct_adult_weight`. Entradas dos meses 1, 10-11, 13-17, 19-23 têm `confidence: "interpolated"` com `interpolation_method: "linear"` e `interpolated_between`. O mês 1 tem `confidence: "extrapolated"` via `backward_extrapolation_from_month_2`. A tabela mostra que machos adultos pesam 32.2-38.0 kg e fêmeas 28.0-32.0 kg aos 24 meses. O ganho semanal de pico é ~1.2 kg/semana no mês 4.

**`skeletal_milestones`** (linhas 712-818): 10 marcos esqueléticos com intervalos [min, max]: SKEL_EPIPHYSEAL_LB — fechamento epifisário raças grandes (12-15 meses), SKEL_EPIPHYSEAL_GB — raças gigantes (18-24 meses), SKEL_CLOSURE_BONES — ossos específicos úmero/rádio/ulna (5-11 meses), SKEL_MATURITY_MALE — maturidade óssea machos (18-24 meses), SKEL_MATURITY_FEMALE — fêmeas (12-18 meses), SKEL_PEAK_ACCEL — pico de aceleração (12-20 semanas), SKEL_VULN_WINDOW — janela de vulnerabilidade nutricional (12-15 meses), SKEL_DOD_MAX_AGE — idade de pico DOD (4-9 meses), SKEL_PANOSTEITIS_AGE — panosteíte (5-12 meses), SKEL_ADULT_SIZE — tamanho adulto (12-18 meses).

**`energy_requirements`** (linhas 820-873): 6 parâmetros energéticos: TER (70 × BW^0.75, kcal/24h), DER (TER × k_multiplier), densidade controlada (3500 kcal/kg DM), densidade rápida (4500), faixa recomendada [3500-4000], definição AAFCO large breed (≥31.8 kg). A fórmula TER é a ponte entre o peso do Gompertz e a energia da dieta.

**`k_multipliers`** (linhas 875-905): 3 perfis: slow_growth_recommended (k=1.2-1.5, default LP 1.2), rapid_growth_discouraged (k=2.0-3.0, alerta LP 2.0), adult_working_active (k=1.5).

**`epidemiology`** (linhas 906-1001): 12 entradas com dados epidemiológicos de DOD: incidência geral 2.84%, CHD = 52.24% dos DODs, displasia de cotovelo 7.46%, osteocondrose 5.97%, panosteíte 5.97%, HOD 7.46%, pico de idade 4-9 meses, prevalência por sexo (machos 54%, fêmeas 33% para CHD), dados de DMO/BMD por sexo e tendência etária.

**`gonadal_status_profiles`** (linhas 1003-1071): 4 perfis: GON_MALE_INTACT (BMD elevada, CHD moderada-alta), GON_MALE_NEUTERED_EARLY (BMD reduzida, CHD 33.3%, CACL 33.3%, penalty multipliers: Ca ×1.5, calorias ×1.3), GON_FEMALE_INTACT (BMD moderada-elevada), GON_FEMALE_SPAYED_EARLY (BMD moderada-reduzida, DOD ×3, penalty multipliers: Ca ×1.5, calorias ×1.3). Os `solver_penalty_multipliers` aqui conectam-se diretamente aos `solver_penalty_multiplier` em `objective_weights.json`.

**`metabolic_biomarkers`** (linhas 1073-1091): 3 biomarcadores: índice TyG (menor em dietas cruas → melhor sensibilidade insulínica), imunoglobulinas (IgA/IgG/IAP fecais aumentadas em cruas → melhor barreira epitelial), sensibilidade à insulina (melhora eixo GH/IGF-1). Cada um tem `LP_relevance` explicando a relevância indireta para o solver.

### 8.3 Relações com Outros JSONs

- **Alimenta o solver indiretamente** via cálculo de DER: o build pipeline usa o Gompertz para obter BW_kg → calcula TER → multiplica por k → obtém DER (kcal/24h) → divide por 1000 para obter o número de "unidades de 1000kcal" → escala os targets do cenário ativo.
- **Os `gonadal_status_profiles[].solver_penalty_multipliers`** conectam-se a `objective_weights.json` — quando o usuário seleciona `gonadal_status = neutered_early`, o build pipeline aplica os multiplicadores (1.5× para PEN_CA_POS, 1.3× para PEN_CALORIC_POS).
- **Os `energy_requirements.NRG_DENSITY_CONTROLLED`** (3500) e `NRG_DENSITY_RAPID` (4500) correspondem aos `caloric_density` targets em `scenarios.json` (SCN_B e SCN_A respectivamente).
- **Referencia `audit_provenance.json`** extensivamente via `source_ref` (REF_GROWTH_GOMPERTZ, REF_GROWTH_ANTHRO, REF_NRG_TER, REF_NRG_DER, REF_EPI_DOD, REF_SKEL_*, REF_GON_*, REF_BIO_*).

---

## 9. audit_provenance.json — Proveniência e Rastreabilidade

**Caminho:** `../../data/audit_provenance.json`
**Tamanho:** 1122 linhas
**Domínio no schema:** `domains.meta`
**Status no schema:** Validado

### 9.1 Propósito e Motivação

Este é o sistema nervoso central de rastreabilidade do projeto. Todo dado numérico em todos os outros JSONs aponta para uma referência (`source_ref`) que é resolvida neste arquivo. Ele contém: (a) flags de qualidade de dados, (b) a formulação matemática completa do algoritmo de goal programming, (c) protocolos de fallback para dados ausentes, (d) a lista de documentos fonte (DOC1, DOC2, DOC3), e (e) 102 entradas de referência com texto explicativo, documentos de origem, flags de qualidade, e referências de linha. O propósito é duplo: permitir auditoria humana (rastrear qualquer número até sua fonte documental) e permitir que outra IA entenda o contexto e a confiabilidade de cada dado.

### 9.2 Estrutura Interna — 4 Seções

**`data_quality_flags`** (4 entradas): Flags que documentam problemas conhecidos nos dados fonte. FLAG_COPY_PASTE_MONTH_2 (CRITICAL): Doc1 tem valores de mês_2 idênticos ao mês_6 (erro de cópia) — resolução: usar tabela Doc3 como autoritativa. FLAG_IODINE_UNIT (WARNING): Doc1 linha 110 diz "0.175 ug" mas as demais referências dizem "0.175 mg" — resolução: usar mg. FLAG_BARF_TOTAL (INFO): PMR=100%, BARF sem sementes=97%, com sementes=99% — mantido como no original. FLAG_NUTRIENTS_NOT_IN_MATRIX (INFO): lista nutrientes excluídos da matriz de 41 e o motivo.

**`algorithm_logic`**: Contém a formulação matemática do goal programming (variáveis x_i, a_ij, T_j, d_j+/-, função objetivo, constraint geral) e 3 níveis de protocolos de fallback: nível 1 (dados de lotes anteriores/fornecedores homólogos), nível 2 (imputação estatística conservadora: Mean-2σ para mínimos críticos de nutrientes benéficos, Mean+2σ para máximos críticos de tóxicos), nível 3 (exclusão paramétrica: -50% para benéficos, +200% para tóxicos, com bloqueio se afetar limites de segurança). O nível 2 define listas explícitas: min_critical = [Ca, P, Zn, Lys], max_critical = [I, Cu, Na, Vit A].

**`source_documents`** (3 entradas): DOC1 ("Plano de Pesquisa Nutricional Sistêmico Pastor Alemão v2.0.pdf"), DOC2 ("O Ponto de Viragem da Dieta Canina.pdf"), DOC3 ("Diretrizes Estruturadas para a Formulação de Dietas Otimizadas.md"). DOC3 é a fonte mais referenciada e é considerada a mais confiável (especialmente para a tabela antropométrica e a matriz nutricional).

**`references`** (102 entradas REF_*): O núcleo da proveniência. Cada entrada contém:
- `text`: Texto descritivo do que a referência afirma (em português). Em algumas entries (REF_RAW_*), o texto é um objeto JSON estruturado com dados brutos parseados.
- `doc_ids`: Array de documentos fonte (ex: ["DOC3"], ["DOC1", "DOC3"]).
- `quality_flag`: CONFIRMED (87 entradas), AUTHORITATIVE_DATABASE (1), INFERRED (4, dados extrapolados), COPY_PASTE_ERROR_CORRECTED (2), LITERATURE_COMPOSITE (7), UNIT_INCONSISTENCY_RESOLVED (1). Total: 102 referências.
- `line_references`: Array de strings apontando para linhas nos documentos fonte (ex: "lines 199-204", "DOC3 line 83").

As referências cobrem: antagonismos minerais (REF_MIN_ANT_*), fisiopatologia dos SULs (REF_SUL_*), justificativas de inclusão (REF_INCL_*), templates de dieta (REF_DIET_*), biodisponibilidade (REF_BIO_*), perdas por processamento (REF_PLOSS_*), energia (REF_NRG_*), esqueleto (REF_SKEL_*), gonadal (REF_GON_*), epidemiologia (REF_EPI_*), biomarcadores (REF_BIO_*), algoritmo (REF_ALGO_*), nutrientes (REF_NUTR_*, REF_SUP_*), metadados globais (REF_GLOBAL_META, REF_EXTRACTION_COMPLETE), e dados brutos parseados (REF_RAW_*).

### 9.3 Relações com Outros JSONs

- **É referenciado por TODOS os outros 7 JSONs** via campos `source_ref`. Qualquer `source_ref: "REF_..."` em qualquer arquivo resolve para uma entrada aqui.
- **É o único arquivo** que contém os documentos fonte (DOC1, DOC2, DOC3) e as flags de qualidade de dados.
- **Contém a especificação do algoritmo** (goal programming e fallbacks) que o build pipeline deve implementar.
- **Conecta-se a `growth_energy_skeletal.json`** via REF_GROWTH_*, REF_SKEL_*, REF_NRG_*, REF_GON_*, REF_EPI_*, REF_BIO_*.
- **Conecta-se a `constraints.json`** via REF_MIN_ANT_*, REF_SUL_*, REF_INCL_*, REF_NUTR_MATRIX_41.
- **Conecta-se a `formulation_rules.json`** via REF_DIET_*, REF_BIO_*, REF_INCL_*, REF_NUTR_MATRIX_41.
- **Conecta-se a `objective_weights.json`** via REF_ALGO_GOAL_PROG.
- **Conecta-se a `scenarios.json`** via REF_SCENARIO_CMP.
- **Problema resolvido:** As 11 entradas REF_* que anteriormente tinham `line_references` com arrays vazios foram corrigidas em sessão anterior — atualmente 0 entradas com line_references vazios.

---

## 10. lp_parameters.schema.json — JSON Schema de Validação

**Caminho:** `../../data/lp_parameters.schema.json`
**Tamanho:** ~44KB
**Propósito:** Validar a estrutura dos parâmetros do solver (não os ingredientes).

Este JSON Schema define a estrutura esperada para os JSONs dos domains `lp_solver` (constraints, objective_weights, scenarios) e `ingredients` (formulation_rules — especificamente o `nutrient_matrix` dentro dele). Ele **não valida** o `DB_ingredientes.json`, que é órfão por design. O schema define tipos como `TypedMeasure` (com `additionalProperties: false`, required: value/unit/basis/source_ref, optional: confidence/note), enums de unidade (17 valores), enums de basis (as_fed, dry_matter, energy_normalized), a regex de `source_ref` (`^REF_[A-Z0-9_]+$`), enums de categoria de ingrediente, e a estrutura completa das NutrientTarget entries. Ele é a garantia contratual de que os dados que entram no solver têm a forma correta.

---

## 11. Mapa de Fluxo de Dados — Como Tudo se Encaixa

### 11.1 Fluxo Principal (Build Pipeline → Solver → Resultado)

```
DB_ingredientes.json (as_fed/100g, 20 ingredientes × 41 nutrientes)
        │
        ▼ conversão unitária (11 nutrientes) + rename + computação de 2 pares combinados (build pipeline)
        │
Matriz a_ij (energy_normalized/1000kcal)
        │
        ├──► constraints.json (60 constraints, 63 bounds LP)
        │       ├── mineral_antagonisms (5) ← audit_provenance (REF_MIN_ANT_*)
        │       ├── toxicological_limits (8) ← toxicological_limits.json ← audit_provenance (REF_SUL_*)
        │       ├── inclusion_constraints (6) ← formulation_rules.inclusion_limits ← audit_provenance (REF_INCL_*)
        │       └── nutrient_bounds (41) ← formulation_rules.nutrient_matrix ← audit_provenance (REF_NUTR_MATRIX_41)
        │
        ├──► objective_weights.json (29 pesos, 5 tiers)
        │       └── penalty multipliers ← growth_energy_skeletal.gonadal_status_profiles
        │
        ├──► scenarios.json (17 targets do cenário ativo SCN_B)
        │       └── caloric_density ← growth_energy_skeletal.energy_requirements
        │
        └──► growth_energy_skeletal.json
                ├── Gompertz → BW_kg(t) → TER = 70 × BW^0.75
                ├── k_multiplier (1.2 slow growth / 2.0 rapid discouraged / 1.5 adult working)
                └── DER = TER × k → número de 1000kcal/dia
                        │
                        ▼
                ESCALA os targets por 1000kcal pelo DER
```

### 11.2 O Solver Recebe

1. **Matriz de coeficientes a_ij** (de DB_ingredientes, convertido)
2. **Constraints duras** (de constraints.json — todos com solver_behavior HARD_FAIL_INFEASIBLE)
3. **Função objetivo** (de objective_weights.json — pesos w_j e variáveis)
4. **Targets T_j** (de scenarios.json — cenário ativo)
5. **DER total** (de growth_energy_skeletal — quantas unidades de 1000kcal)

### 11.3 O Solver Produz

Proporções ótimas x_i (uma por ingrediente) que minimizam Σ w_j × (d_j_minus + d_j_plus) sujeito a todas as constraints duras. A solução indica: quanto de beef_muscle_raw, beef_liver_raw, chicken_muscle_raw, etc. incluir na dieta.

---

## 12. Convenções de Nomenclatura Cross-JSON

### 12.1 Nomes de Variáveis

O sistema opera com duas convenções de nomes de nutrientes:

- **Espaço do DB (DB_ingredientes.json):** Usa sufixo de unidade no nome (ex: `magnesium_mg`, `selenium_ug`, `copper_mg`). Basis: `as_fed`, referência: 100g.
- **Espaço do Solver (constraints.json, objective_weights.json, scenarios.json, formulation_rules.nutrient_matrix):** Usa nome padronizado sem sufixo de unidade (ex: `magnesium_g`, `selenium_mg`, `copper_mg`). Basis: `energy_normalized`, referência: 1000kcal.

A interseção entre os dois espaços contém 28 nomes idênticos. As 13 diferenças dividem-se em 3 categorias:
- **11 conversões de unidade** (mg→g ou ug→mg): calcium_mg↔calcium_g, phosphorus_mg↔phosphorus_g, magnesium_mg↔magnesium_g, sodium_mg↔sodium_g, potassium_mg↔potassium_g, chloride_mg↔chloride_g, choline_mg↔choline_g, selenium_ug↔selenium_mg, cobalamin_b12_ug↔cobalamin_b12_mg, folic_acid_b9_ug↔folic_acid_b9_mg, iodine_ug↔iodine_mg. O build pipeline é responsável por estas conversões.
- **2 nutrientes no DB mas NÃO na matrix do solver:** `biotin_ug`, `vitamin_k_ug` — são rastreados no DB (em `coverage_excluded_nutrients`) mas não são otimizados pelo solver.
- **2 nutrientes na matrix mas NÃO como dados individuais no DB:** `methionine_plus_cystine_g`, `phenylalanine_plus_tyrosine_g` — existem apenas como entries na `nutrient_matrix` e são computados pelo build pipeline como soma dos aminoácidos individuais (methionine_g + cystine_proxy e phenylalanine_g + tyrosine_proxy).

### 12.2 Sistema de Referências (source_ref)

Todos os campos `source_ref` seguem a regex `^REF_[A-Z0-9_]+$`. Convenções de prefixo:

| Prefixo | Significado | Exemplo |
|---------|------------|---------|
| REF_USDA_FDC_ | Dados USDA FoodData Central | REF_USDA_FDC_170196 |
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
As referências `REF_USDA_FDC_*` não são resolvidas dentro do sistema — apontam para uma fonte externa. Todas as demais referências devem ter uma entrada correspondente em `audit_provenance.references`.

### 12.3 IDs de Constraints

As constraints em `constraints.json` seguem o padrão `CSTR_<TIPO>_<NUTRIENTE>_<DIRECAO>`:
- `CSTR_NB_*_MIN`: Nutrient bound mínimo (41 entries)
- `CSTR_SUL_*_MAX`: Safe Upper Limit máximo (8 entries)
- `CSTR_INCL_*`: Inclusion constraint (6 entries)
- `CSTR_<PAIR>_RATIO`: Ratio bound de antagonismo (5 entries)

---

## 13. Estado Atual da Curadoria

| Grupo | Ingredientes | Status | Validado por |
|-------|-------------|--------|--------------|
| bovinos | 11 (beef_muscle_raw, beef_lung_raw, beef_foot_tendon_raw, beef_tail_raw, beef_tongue_raw, beef_blood_raw, beef_heart_raw, beef_green_tripe_raw, beef_liver_raw, beef_kidney_raw, beef_spleen_raw) | VALIDATED (0 errors, 11 warnings esperados) | validate_bovinos_deep.py |
| aves | 6 (chicken_muscle_raw, chicken_heart_raw, chicken_liver_raw, chicken_kidney_raw, chicken_foot_tendon_raw, chicken_blood_raw) | PARTIAL/PENDING (13+ issues conhecidos) | Pendente |
| suínos | 2 (pork_muscle_raw, pork_liver_raw) | PARTIAL (ambos auditados) | Parcial |
| peixes | 1 (salmon_atlantic_raw) | PARTIAL (salmon_atlantic auditado) | Parcial |

O `_db_metadata.validated_sources` lista apenas "bovinos". O `pending_sources` lista "aves". O `partial_sources` lista "aves", "suinos", "peixes". Há uma sobreposição intencional: aves aparece em ambos porque tem dados populados mas não validados formalmente.

---

## 14. Gaps e Dependências Não-Implementadas

1. **Build Pipeline** (crítico): Não existe código que conecte os JSONs ao solver. A conversão as_fed → energy_normalized, o rename de 11 nutrientes com conversão de unidade, a computação de 2 pares combinados de aminoácidos, a expansão de `_all_muscle_meat`, e o cálculo de DER a partir do Gompertz são todos processos documentados mas não implementados.
2. **DB_ingredientes fora do schema**: Intencional, mas não há schema alternativo para validá-lo. A validação é feita por scripts Python ad-hoc.
3. **Aves normalization**: 13+ issues pendentes nos 6 ingredientes de aves.
4. **G8 false positive** em validate_master.py (P2).
5. **Fase idosa/sênior não implementada**: Não há dados, constraints, ou cenários para cães idosos. O `k_multipliers.adult_working_active` (k=1.5) existe no `growth_energy_skeletal.json` com status=REFERENCE — pode ser usado para manutenção adulta, mas não há cenário adulto correspondente em `scenarios.json`. O sistema operacionaliza apenas crescimento (SCN_A/SCN_B). A extensão para manutenção adulta e idoso requer: (a) novos cenários com targets apropriados, (b) possível ajuste de SULs e constraints para faixas etárias avançadas, (c) k_multipliers para senior/sedentário.
6. **3 suplementos planejados mas ausentes do DB**: `kelp_meal_dried`, `salt_nacl`, `copper_sulfate` estão mapeados em `formulation_rules._inclusion_semantics.category_to_ingredient_mapping` mas **não existem** como ingredientes no `DB_ingredientes.json`. Iodo permanece estruturalmente infactível até que kelp seja adicionado.
7. **lp_parameters.schema.json é schema puro**: Não contém `solve_cascade` nem `NUTRIENT_REGISTRY`. Ambos são descritos na documentação como blocos de dados runtime (`lp_parameters_schema.json` na arquitetura V10.4), mas o arquivo real é exclusivamente um JSON Schema de validação. A localização definitiva destes blocos precisa ser decidida: criar um novo `lp_parameters_data.json` ou adicionar ao `constraints.json`.
