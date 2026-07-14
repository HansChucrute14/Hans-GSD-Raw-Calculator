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
build_pipeline.py          — Main pipeline (load, validate, transform, solve)
data/                      — 9 JSON files (ingredients, constraints, growth, etc.)
tests/                     — pytest test suite
docs/                      — Architecture satellites (sat_*.md)
```

## Quick Start

```bash
pip install -r requirements.txt
python build_pipeline.py --validate-db
python build_pipeline.py --runtime
pytest tests/ -v
```

## Status

| Phase | Status |
|---|---|
| **0 — Data curation** | **IN PROGRESS** — 20/23 ingredients; kelp/salt/copper_sulfate pending; 17 orphan refs unresolved; cystine/tyrosine missing for all ingredients |
| **1 — Dimensional pipeline** | **PARTIAL** — conversion, matrix build, DER/envelope implemented and tested. Full pipeline gated by solver. |
| **2 — Solver cascade** | **NOT STARTED** — `call_lp_solver()` unimplemented (raises NotImplementedError). `solve_cascade()`, `build_diagnostic_analysis()` not written. |
| **3 — Tests** | **PARTIAL** — 13 dimensional tests exist. Cascade, data integrity, and recipe tests not written. |
| **4 — Precomputed recipes** | **NOT STARTED** — blocked on Phase 2. |
| **5 — Anti-patterns & audit** | **NOT STARTED** — blocked on all prior phases. |

### P0 blockers
- No LP/MILP solver backend (PuLP/CVXPY/HiGHS)
- 3 supplement ingredients not in DB → iodine structurally infeasible
- Poultry data incomplete (13+ issues)

### Curation

| Group | Count | Status |
|---|---|---|
| Bovines | 11 | VALIDATED |
| Poultry | 6 | PARTIAL (13+ issues) |
| Pork | 2 | PARTIAL |
| Fish | 1 | PARTIAL |
| Supplements | 0 | PLANNED |
| **Total** | **20** | — |
