# GSD Diet Calc — Raw Canine Diet Formulation Engine

**Linear Programming formulation engine for raw canine diets** — German Shepherd growth and adult maintenance phases. AAFCO Large Breed Growth compliant.

## Overview

This system formulates raw diets (PMR/BARF) using **Preemptive/Lexicographic Goal Programming**. It reads 11 JSON data files describing ingredients, nutritional targets, toxicological limits, growth biology, and solver parameters, then executes a **3-level declarative cascade**:

| Level | Behavior | Output |
|-------|----------|--------|
| **1** | All constraints hard (SULs, adequacy floors, DER/density/Ca:P) | `optimal` — recommended grams (`SAFE_TO_FEED`) |
| **2** | Adequacy floors relaxed via weighted slack (clinical criticality) | `suboptimal` — feed with caution (`FEED_WITH_CAUTION`) |
| **3** | SUL violation minimized, DER proximity, adequacy — **lexicographic stages** | `unsafe_diagnostic` — diagnosis only, **no grams** (`DO_NOT_FEED`) |

**Two usage modes:**
- **Free Mode** — any 1 to N ingredient combination, real-time calculation
- **Precomputed Recipes** — offline-ranked optimal combinations (planned, not yet implemented)

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Validate ingredient database (23 ingredients, 43 nutrients each)
python build_pipeline.py --validate-db

# Run full pipeline (Free mode with sample selection)
python build_pipeline.py --runtime

# Run test suite (32 tests, zero deprecation warnings)
pytest tests/ -v

# Validate MAPA documentation
python build_pipeline.py --gate-mapa
```

## Pipeline Modes

| Mode | Description |
|------|-------------|
| `--validate-db` | Validates `DB_ingredientes.json` against 3-state nutrient contract + JSON Schema (Draft 2020-12) |
| `--runtime` | Free mode: load → validate → transform → build matrix → solve cascade → output contract |
| `--generate-mapa` | Generate `MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md` (17 sections, auto-generated) |
| `--gate-mapa` | Validate MAPA against 8 structural checks (phantom tokens, counts, drift, etc.) |
| `--audit-mapa` | Cross-reference index + drift report vs existing MAPA |
| `--build-recipes` | **NOT IMPLEMENTED** — offline recipe generation & ranking |

## Project Structure

```
build_pipeline.py              # Main pipeline (3,458 lines) — load, validate, transform, solve
data/                          # 11 JSON data files
  DB_ingredientes.json         # 23 ingredients × 43 nutrients (3-state: measured/missing/not_applicable)
  db_ingredientes.schema.json  # Draft 2020-12 schema with $defs (IngredientGroup, Ingredient, NutrientEntry, ...)
  constraints.json             # 60 constraints: 5 antagonisms, 8 SULs, 6 inclusions, 41 nutrient bounds
  formulation_rules.json       # Templates, inclusion limits, bioavailability, 41-nutrient matrix
  growth_energy_skeletal.json  # Gompertz growth, TER, DER, k-multipliers, envelope
  lp_parameters_data.json      # NUTRIENT_REGISTRY, solve_cascade[], solver_params
  lp_parameters.schema.json    # Schema for lp_parameters_data.json
  objective_weights.json       # 29 weights (27 with solver_penalty_multiplier), 5 tiers, gonadal multipliers
  scenarios.json               # SCN_A (WARNING), SCN_B (ACTIVE_TARGET) — 17 targets each
  toxicological_limits.json    # 8 SULs (list format, nested sul.value)
tests/                         # 32 tests following AAA+A pattern (Arrange-Act-Assert-Audit)
  test_cascade_integration.py  # 19 cascade tests (L1→L2→L3 descent, SUL collision, clinical floor, tie-break)
  test_dimensional_pipeline.py # 13 dimensional tests (round-trip, units, wildcards, composite AAs)
docs/architecture/             # 7 satellite architecture docs (sat_*.md)
docs/data-specs/               # Ingredient template spec + research prompt
docs/governance/               # Anti-patterns, test methodology, systemic review findings
```

## Architecture Highlights

### 3-Level Declarative Cascade
- **Policy in JSON, not code** — `lp_parameters_data.json` contains `solve_cascade[]` with `relax_tiers`, `objective_stages`, `clinical_floor`
- **Lexicographic SUL→DER→Adequacy** — fixed optimum tolerance + MIP tolerance rule (`max(tol_rel, cbc_mip_gap)` when binaries present)
- **Clinical Floor MILP** — `x_i = 0 OR x_i ≥ x_min_i` via binary indicator + per-ingredient Big-M (`M_i = DER_kcal / EM_i * 100`)
- **Conditional Adequacy Check (L1→L2)** — `fat_source_vs_aafco_fat` pre-solver check delegates to L2 with structured gap detail

### Dimensional Integrity
- `as_fed/100g` → `energy_normalized/1000kcal` → **compile to daily basis** before LP
- 11 unit conversions + 2 composite AAs (Met+Cys, Phe+Tyr) with real values, no proxy
- Modified Atwater ME: `3.5×protein + 8.5×fat + 3.5×NFE`
- Dynamic envelope: `minTotal = 0.9 × DER/max_density`, `maxTotal = 1.1 × DER/min_density`

### Output Data Contract (v10.1)
- **L1/L2**: `allocations[]` with grams, `feeding_recommendation ∈ {SAFE_TO_FEED, FEED_WITH_CAUTION}`
- **L3**: `allocations = null` (mechanical barrier), `diagnostic_analysis` with `sul_violations_inevitable`, `what_would_happen` (counterfactual), `clinical_floor_applied`, `recommended_alternative_actions`
- **Always**: 41+ `nutrient_results`, `gaps`, `alerts`, `recommended_additions`, `solver_metadata` with `lexicographic_stages_used`

### Determinism
- **Hash-based tie-break** — `weight=1000.0 + hash(ingredient_id) % 10000 × 0.1` → bit-identical output across runs
- **Fix-optimum tolerance** — `abs=0.01`, `rel=max(1e-6, cbc_mip_gap)` when MILP

## Current Status

| Phase | Status | Details |
|-------|--------|---------|
| **0 — Data curation** | **IN PROGRESS** | 23/23 ingredients; kelp/salt/copper_sulfate pending; 17 planned source_refs |
| **1 — Dimensional pipeline** | **DONE** | as_fed→energy_normalized, matrix build, DER/envelope — 13 tests passing |
| **2 — Solver cascade** | **DONE** | 3-level declarative cascade, goal programming, clinical floor MILP, lexicographic SUL→DER→adequacy — 19 tests passing |
| **3 — Tests** | **DONE** | 36 total (19 cascade + 13 dimensional + 4 category-goal). Data integrity & recipe tests pending |
| **4 — Precomputed recipes** | **NOT STARTED** | Blocked on Phase 3 data completeness |
| **5 — Anti-patterns & audit** | **NOT STARTED** | Blocked on all prior phases |

### Test Results (36 passed, 0 warnings)

```
tests/test_dimensional_pipeline.py   — 13 passed
tests/test_cascade_integration.py    — 23 passed (19 baseline + 4 category-goal tests)
```

### Recent Addition: Category Soft Goals (Option B)

| Feature | Status | Description |
|---------|--------|-------------|
| `category_goals` config | **IMPLEMENTED** | `lp_parameters_data.json` Level 1+2: 7 categories with absolute targets (70% muscle, 10% organ, etc.) |
| `category_goal_deviation` objective | **IMPLEMENTED** | Stage 2 in L1/L2, penalty multiplier `0.01` (micro-weight tie-breaker) |
| `template_adherence` output | **IMPLEMENTED** | User-facing summary in output contract; `solver_metadata.category_goal_deviations_raw` for audit |

**Architecture:** Wall-vs-Compass pattern preserved — nutrient adequacy/safety targets (Wall) are never overridden by category preferences (Compass). Micro-weight ensures category goals act as tie-breakers only (~0.3–1.0 effective weight vs ~410 for nutrients).

Run with strict deprecation check:
```bash
pytest tests/ -v -W error::DeprecationWarning
```

### Known Limitations (Phase 3 Blockers)

| Gap | Impact | Required For |
|-----|--------|--------------|
| **No bone/calcium source** | All real selections hit Level 2 (Ca gap) | L1 feasibility |
| **No iodine source** | All 23 ingredients = `missing` | Structural L1 blocker |
| **No vitamin D3 source** | Only fats have D3 (129/70 IU) | Adequacy |
| **No chloride source** | All 23 ingredients = `missing` | Adequacy |
| **CSTR_NB_*_MIN tier hardcoded** | `build_pipeline.py:1900` ignores registry `constraint_tier` | Tier-driven relaxation |

### Curation Status

| Group | Count | Status |
|-------|-------|--------|
| Bovines | 11 | VALIDATED |
| Poultry | 6 | PARTIAL (13+ issues) |
| Pork | 2 | PARTIAL |
| Fish | 1 | PARTIAL |
| Fat sources | 3 | PARTIAL |
| **Total** | **23** | — |

## Testing Strategy

Tests follow the **AAA+A pattern** (Arrange-Act-Assert-Audit) from `sat_testes_consolidado`:

1. **Arrange** — Load real JSONs (no fixtures/mocks)
2. **Act** — Execute real functions (no stubs)
3. **Assert** — Verify results distinguish real implementation from placeholder
4. **Audit** — Log complete result to `tests/test_audit_log.md` for human inspection

```bash
# Full suite
pytest tests/ -v

# With audit log
pytest tests/ -v 2>&1 | tee tests/test_audit_log.md
```

## Dependencies

- `pulp==3.3.2` — LP/MILP solver (CBC bundled via `COIN_CMD`)
- `jsonschema` — Draft 2020-12 validation

## License

Private project — not for distribution.