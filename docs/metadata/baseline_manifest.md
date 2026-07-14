# Baseline Inventory — GSD Diet Calc V10.4
**Generated:** 2026-07-13T07:07:11.500036
**Working directory:** C:\Users\SF005\Downloads\gsd_diet_calc_v10_4_complete_archive\download\plano_modular_v10_4

## 1. File Manifest

| File | Size | SHA-256 | Purpose |
|---|---|---|---|
| `DB_ingredientes.json` | 171837 B | `f43ebb278c4986cc...` | Ingredient bank |
| `constraints.json` | 42469 B | `f576bf97a6dad834...` | LP constraints |
| `formulation_rules.json` | 29305 B | `d445208f6809677b...` | Formulation rules |
| `audit_provenance.json` | 50280 B | `5693f7587b7a42da...` | Provenance |
| `growth_energy_skeletal.json` | 28341 B | `fb5b42a80173bfc5...` | Growth/energy model |
| `objective_weights.json` | 13589 B | `1379b8cd275e8c70...` | Objective weights |
| `scenarios.json` | 7476 B | `dbb9bf8dceccc46f...` | Scenarios |
| `toxicological_limits.json` | 3447 B | `6a478b50ec1024cb...` | Toxicological limits |
| `lp_parameters.schema.json` | 44294 B | `1bb1b2aea4357b9b...` | LP validation schema |
| `lp_parameters_data.json` | 13052 B | `d377daeeb39844f1...` | LP runtime parameters (NUTRIENT_REGISTRY + solve_cascade) |

## 2. DB_ingredientes.json

- **Version:** 2.2.0
- **Claimed ingredients:** 20
- **Claimed nutrients/ingredient:** 43
- **template_ref:** docs/data-specs/INGREDIENTE_TEMPLATE_SPEC.md
- **schema_ref:** lp_parameters.schema.json
- **Actual ingredients:** 20

### 2.1 Ingredients

| ID | Category | Nutrients | Group |
|---|---|---|---|
| `beef_muscle_raw` | muscle_meat | 36 fields (+7 excl) | bovinos |
| `beef_lung_raw` | organ_non_secreting | 34 fields (+9 excl) | bovinos |
| `beef_foot_tendon_raw` | connective_tissue | 31 fields (+12 excl) | bovinos |
| `beef_tail_raw` | muscle_meat | 34 fields (+9 excl) | bovinos |
| `beef_tongue_raw` | muscle_organ | 33 fields (+10 excl) | bovinos |
| `beef_blood_raw` | blood_source | 32 fields (+11 excl) | bovinos |
| `beef_heart_raw` | muscle_organ | 39 fields (+4 excl) | bovinos |
| `beef_green_tripe_raw` | organ_non_secreting | 35 fields (+8 excl) | bovinos |
| `beef_liver_raw` | organ_secreting | 40 fields (+3 excl) | bovinos |
| `beef_kidney_raw` | organ_secreting | 39 fields (+4 excl) | bovinos |
| `beef_spleen_raw` | organ_secreting | 34 fields (+9 excl) | bovinos |
| `chicken_muscle_raw` | muscle_meat | 38 fields (+5 excl) | aves |
| `chicken_heart_raw` | muscle_organ | 32 fields (+11 excl) | aves |
| `chicken_liver_raw` | organ_secreting | 35 fields (+8 excl) | aves |
| `chicken_kidney_raw` | organ_secreting | 15 fields (+28 excl) | aves |
| `chicken_foot_tendon_raw` | connective_tissue | 11 fields (+32 excl) | aves |
| `chicken_blood_raw` | blood_source | 7 fields (+36 excl) | aves |
| `pork_muscle_raw` | muscle_meat | 37 fields (+6 excl) | suinos |
| `pork_liver_raw` | organ_secreting | 36 fields (+7 excl) | suinos |
| `salmon_atlantic_raw` | fish | 40 fields (+3 excl) | peixes |

### 2.2 Categories Found
- blood_source, connective_tissue, fish, muscle_meat, muscle_organ, organ_non_secreting, organ_secreting

### 2.3 Unified Nutrient Fields (41)

`ala_alpha_linolenic_acid_g`, `ara_arachidonic_acid_g`, `arginine_g`, `calcium_mg`, `choline_mg`, `cobalamin_b12_ug`, `copper_mg`, `cystine_g`, `epa_plus_dha_g`, `fat_g`, `folic_acid_b9_ug`, `histidine_g`, `iodine_ug`, `iron_mg`, `isoleucine_g`, `leucine_g`, `linoleic_acid_g`, `lysine_g`, `magnesium_mg`, `manganese_mg`, `methionine_g`, `niacin_b3_mg`, `pantothenic_acid_b5_mg`, `phenylalanine_g`, `phosphorus_mg`, `potassium_mg`, `protein_g`, `pyridoxine_b6_mg`, `riboflavin_b2_mg`, `selenium_ug`, `sodium_mg`, `thiamine_b1_mg`, `threonine_g`, `tryptophan_g`, `tyrosine_g`, `valine_g`, `vitamin_a_iu`, `vitamin_d3_iu`, `vitamin_e_iu`, `vitamin_k_ug`, `zinc_mg`

### 2.4 Ingredients with `coverage_excluded_nutrients`
- **Count:** 20 / 20
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

### 2.5 Missing Supplements (planned)
- **Not in DB:** `kelp_meal_dried`, `salt_nacl`, `copper_sulfate`

## 3. constraints.json

- **nutrient_bounds:** 41 constraints (41 HARD, 0 other)
- **toxicological_limits:** 8 constraints (8 HARD, 0 other)
- **inclusion_constraints:** 6 constraints (6 HARD, 0 other)
- **mineral_antagonisms:** 5 constraints (5 HARD, 0 other)

## 4. toxicological_limits.json

- **Type:** `list` (top-level)
- **Count:** 8 SULs

| Nutrient | Value | Unit | Basis |
|---|---|---|---|
| `copper_mg` | 100 | mg | energy_normalized |
| `iron_mg` | 130 | mg | energy_normalized |
| `sodium_g` | 3.75 | g | energy_normalized |
| `vitamin_a_iu` | 9375 | IU | energy_normalized |
| `vitamin_d3_iu` | 750 | IU | energy_normalized |
| `iodine_mg` | 2.5 | mg | energy_normalized |
| `zinc_mg` | 300 | mg | energy_normalized |
| `manganese_mg` | 15 | mg | energy_normalized |

## 5. scenarios.json

- **Type:** `list` (top-level)
- **Count:** 2
  - `SCN_A_RAPID_GROWTH`: Cenario A - Crescimento Rapido (Desaconselhado) | status=WARNING_DO_NOT_OPTIMIZE | 17 targets
  - `SCN_B_SLOW_GROWTH`: Cenario B - Crescimento Lento (Recomendado) | status=ACTIVE_TARGET | 17 targets

## 6. objective_weights.json

- **Count:** 29

| ID | Penalty Multiplier | Tier |
|---|---|---|
| `PEN_CA_POS` | {'neutered_early': {'multiplier': 1.5, 'condition': 'gonadal_status == neutered_early'}, 'spayed_early': {'multiplier': 1.5, 'condition': 'gonadal_status == spayed_early'}} | 1 |
| `PEN_CA_P_RATIO_SYM` | None | 1 |
| `PEN_CA_NEG` | None | 1 |
| `PEN_VIT_AD3_POS` | None | 1 |
| `PEN_CALORIC_POS` | {'neutered_early': {'multiplier': 1.3, 'condition': 'gonadal_status == neutered_early'}, 'spayed_early': {'multiplier': 1.3, 'condition': 'gonadal_status == spayed_early'}} | 2 |
| `PEN_PHOSPHORUS_NEG` | None | 2 |
| `PEN_PROTEIN_NEG` | None | 2 |
| `PEN_ZINC_NEG` | None | 2 |
| `PEN_VITAMIN_A_NEG` | None | 2 |
| `PEN_VITAMIN_D3_NEG` | None | 2 |
| `PEN_FAT_NEG` | None | 3 |
| `PEN_LYSINE_NEG` | None | 3 |
| `PEN_MET_CYS_NEG` | None | 3 |
| `PEN_MAGNESIUM_NEG` | None | 3 |
| `PEN_EPA_DHA_NEG` | None | 3 |
| `PEN_LINOLEIC_NEG` | None | 3 |
| `PEN_SODIUM_NEG` | None | 3 |
| `PEN_IRON_NEG` | None | 3 |
| `PEN_COPPER_NEG` | None | 3 |
| `PEN_SELENIUM_NEG` | None | 3 |
| `PEN_VITAMIN_E_NEG` | None | 3 |
| `PEN_MANGANESE_NEG` | MISSING | 4 |
| `PEN_POTASSIUM_NEG` | None | 4 |
| `PEN_CHOLINE_NEG` | None | 4 |
| `PEN_ALA_NEG` | None | 4 |
| `PEN_ARA_NEG` | None | 4 |
| `PEN_CHLORIDE_NEG` | None | 4 |
| `PEN_IODINE_NEG` | None | 4 |
| `PEN_COST_POS` | None | 5 |

**Without penalty_multiplier:** PEN_MANGANESE_NEG

## 7. audit_provenance.json

- **Total entries:** 102
  - **AUTHORITATIVE_DATABASE:** 1
  - **CONFIRMED:** 87
  - **COPY_PASTE_ERROR_CORRECTED:** 2
  - **INFERRED:** 4
  - **LITERATURE_COMPOSITE:** 7
  - **UNIT_INCONSISTENCY_RESOLVED:** 1
- **Fallback protocols:** 3 levels defined
  - Level 1: Validacao por Base de Dados Homologa Filtrada
  - Level 2: Imputacao Estatistica Conservadora por Intervalo de Confianca
  - Level 3: Exclusao Parametrica ou Penalizacao de Seguranca

## 8. formulation_rules.json

- **nutrient_matrix:** 41 entries (list)
  - First entry keys: ['nutrient_id', 'display_name', 'values', 'unit', 'basis', 'source_ref']
  - values keys: ['NRC_2006_RA', 'AAFCO_large_breed_growth', 'FEDIAF_large_breed_growth']
- **diet_templates:** 3
  - `TPL_PMR`: PMR
  - `TPL_BARF`: BARF
  - `TPL_PMR_BARF_CONSOLIDATED`: PMR_BARF_Consolidated
- **category_to_ingredient_mapping:** 6 entries
  - **Mapped but missing from DB:** `copper_sulfate`, `salt_nacl`, `kelp_meal_dried`
  - **Wildcards:** _all_fat_source, _all_muscle_meat

## 9. growth_energy_skeletal.json

- **k_multipliers:** slow_growth_recommended, rapid_growth_discouraged, adult_working_active
  - `slow_growth_recommended`: value=[1.2, 1.5], status=RECOMMENDED
  - `rapid_growth_discouraged`: value=[2.0, 3.0], status=DISCOURAGED
  - `adult_working_active`: value=1.5, status=REFERENCE
- **energy_requirements:** 6 formulas
  - `NRG_TER`: 70 * (BW_kg ^ 0.75)
  - `NRG_DER`: TER * k_multiplier
  - `NRG_DENSITY_CONTROLLED`: 3500 kcal/kg DM
  - `NRG_DENSITY_RAPID`: 4500 kcal/kg DM
  - `NRG_DENSITY_RANGE`: [3500, 4000] kcal/kg DM (recommended range)
  - `NRG_AAFCO_LB_DEF`: large_breed = weight >= 31.8 kg (70 lbs)

## 10. lp_parameters.schema.json

- **Title:** LP Parameters Schema — Pastor Alemao (GSD) Nutritional Solver
- **Type:** `dict` (pure JSON Schema)
- **Top-level keys:** $schema, $id, title, description, type, required, additionalProperties, definitions, properties
- **Contains `solve_cascade`:** False
- **Contains `NUTRIENT_REGISTRY`:** False
- **Note:** This file is a JSON Schema validation document. It does not contain runtime solve_cascade or NUTRIENT_REGISTRY data.

## 10a. lp_parameters_data.json

- **Contains `solve_cascade`:** True
  - Levels: [1, 2, 3]
- **Contains `NUTRIENT_REGISTRY`:** True
  - Nutrients: 41
  - Tiers: {'adequacy_soft': 33, 'safety_hard': 8}
  - Clinical criticality: {'critical': 8, 'high': 7, 'low': 8, 'moderate': 18}

## 11. Cross-Reference Audit

- **Total REF_ references in DB:** 36
- **USDA (external):** 17
- **Internal:** 19
- **In audit_provenance:** 102
- **Orphans (internal but not in audit_provenance):** 0

## 12. Documented vs Actual Divergences

| Claim | Documented | Actual |
|---|---|---|
| Claimed nutrients_per_ingredient | 43 | range 7–40 | [!]
| coverage_excluded_nutrients exists | yes (per MAPA) | yes (all 20 have it as list) | [!]
| Orphan refs | 17 (per docs) | 0 | [!]
| Audit_provenance refs | 85 (per docs) | 102 | [!]
| solve_cascade | in lp_parameters.schema (per docs) | in lp_parameters_data.json (yes) | [!]
| NUTRIENT_REGISTRY | in lp_parameters.schema (per docs) | in lp_parameters_data.json (yes) | [!]
| All constraints non-HARD cascade | yes (per V10) | no (all 60 HARD_FAIL_INFEASIBLE) | [!]
| scenarios.json structure | dict with `scenarios` key | flat list | [!]
| Adult k_multiplier | does not exist (per docs) | exists: adult_working_active (k=1.5) | [!]
| Missing supplements in DB | 0 (per claimed) | 3 (kelp, salt, CuSO4 mapped but absent) | [!]
| nutrient_matrix structure | dict with min_value/max_value | list with nested `values` dict | [!]
