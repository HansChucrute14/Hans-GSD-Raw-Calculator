# Hans GSD Raw Calculator

Linear Programming formulation engine for raw canine diets — German Shepherd growth and adult maintenance phases. AAFCO Large Breed Growth compliant.

## Architecture

The system reads 9+ JSON data files describing ingredients, nutritional targets, toxicological limits, and growth biology, then executes a 3-level preemptive goal programming cascade:

| Level | Behavior | Output |
|---|---|---|
| 1 | All constraints hard | `optimal` — recommended grams |
| 2 | Adequacy floors relaxed via weighted slack | `suboptimal` — feed with caution |
| 3 | SUL violation minimized, DER proximity | `unsafe_diagnostic` — diagnosis only, no grams |

Two usage modes:
- **Free mode** — any 1 to N ingredient combination, real-time calculation
- **Precomputed Recipes** — offline-ranked optimal combinations

## Project Structure

```
build_pipeline.py              — Main pipeline (load, validate, transform, solve)
data/                          — 9 JSON files (ingredients, constraints, growth, etc.)
tests/                         — pytest test suite (32 tests)
docs/architecture/             — Architecture satellites (sat_*.md)
docs/data-specs/               — Data specifications and research prompts
```

## Quick Start

```bash
pip install -r requirements.txt
python build_pipeline.py --validate-db
python build_pipeline.py --runtime
pytest tests/ -v
```

## Status

| Phase | Status | Details |
|---|---|---|
| **0 — Data curation** | **IN PROGRESS** | 23/23 ingredients; kelp/salt/copper_sulfate pending; 17 orphan refs unresolved |
| **1 — Dimensional pipeline** | **DONE** | as_fed→energy_normalized conversion, matrix build, DER/envelope — 13 tests passing |
| **2 — Solver cascade** | **DONE** | 3-level declarative cascade, goal programming, clinical floor, lexicographic SUL→DER→adequacy — 19 tests passing |
| **3 — Tests** | **PARTIAL** | 32 tests total (19 cascade + 13 dimensional). Data integrity and recipe tests pending. |
| **4 — Precomputed recipes** | **NOT STARTED** | Blocked on Phase 3 data completeness |
| **5 — Anti-patterns & audit** | **NOT STARTED** | Blocked on all prior phases |

### Test Results

```
tests/test_dimensional_pipeline.py   — 13 passed
tests/test_cascade_integration.py    — 19 passed (incl. synthetic L1, Ca:P gap, SUL regression)
```

### Known Limitations (Phase 3)

- **No bone/calcium source** — USDA FDC has no raw bone-in product with Ca >1g/100g. Gate A (muscle+fat+liver+kidney) hits Level 2 due to Ca gap.
- **No iodine source** — all 23 ingredients = `missing`. Structural L1 blocker.
- **No vitamin D3 source** — `chicken_fat_raw` (129 IU) and `pork_fat_raw` (70 IU) are the only D3 sources.
- **No chloride source** — all 23 ingredients = `missing`.
- **CSTR_NB_*_MIN tier hardcoded** — `build_pipeline.py:1900-1901` ignores registry `constraint_tier` for NB constraints. Deferred to Phase 3.

### Curation

| Group | Count | Status |
|---|---|---|
| Bovines | 11 | VALIDATED |
| Poultry | 6 | PARTIAL (13+ issues) |
| Pork | 2 | PARTIAL |
| Fish | 1 | PARTIAL |
| Fat sources | 3 | PARTIAL |
| **Total** | **23** | — |

## Testing Strategy

Tests follow the **AAA+A pattern** (Arrange-Act-Assert-Audit) from `sat_testes_consolidado`:
- Load real JSONs (no fixtures)
- Execute real functions (no stubs)
- Audit results to `tests/test_audit_log.md`

Run the full suite:
```bash
pytest tests/ -v
```

## License

Private project — not for distribution.
