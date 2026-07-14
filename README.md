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

Current phase: **Phase 1** — dimensional transformation pipeline (as-fed/100g → energy-normalized/1000kcal, dynamic DER envelope). Solver implementation is Phase 2.
