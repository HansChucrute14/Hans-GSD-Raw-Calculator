# Type Safety Guide — GSD Diet Calc V10.4

## Overview

This project uses Python type annotations with mypy for static type checking.
All public functions have type signatures; the CI pipeline runs `mypy` on every push.

## Setup

```bash
pip install mypy
mypy src/gsd/ --show-error-codes
```

## mypy Configuration

In `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.10"          # minimum supported; CI runs 3.12
disallow_untyped_defs = true     # all functions must have type annotations
check_untyped_defs = true        # check bodies of functions even if untyped
warn_return_any = true
show_error_codes = true
ignore_missing_imports = false

[[tool.mypy.overrides]]
module = ["pulp.*", "jsonschema.*"]
ignore_missing_imports = true
```

## Module Architecture

| Module | Role | Type Coverage |
|--------|------|---------------|
| `types.py` | Centralized type definitions (Literals, TypedDicts, type aliases) | Definitions only |
| `core.py` | DER calculation, JSON loading, dataclasses (`AnimalInput`, `DerEnvelope`, `SolverRequest`, `CrossRefIndex`) | Fully annotated |
| `nutrition.py` | Input validation, as_fed -> energy_normalized conversion, matrix building | Fully annotated |
| `solver.py` | LP cascade, objective building, output contract | Fully annotated |
| `mapa.py` | MAPA markdown generation (17 sections) | Partially annotated |
| `cli.py` | CLI entry point | Partially annotated |
| `doc_introspector.py` | AST introspection for build pipeline | Partially annotated |

## Key Type Patterns

### 3-State Nutrient Entry

Every nutrient in `DB_ingredientes.json` follows a 3-state contract:

```python
# Status is one of: "measured", "missing", "not_applicable", "data_incomplete"
{"status": "measured", "value": 0.737}
{"status": "missing"}
{"status": "not_applicable"}
```

Use `is_measured(entry)` and `get_value(entry)` from `types.py` for safe access.

### Literal Types

String constants are defined as `Literal` types in `types.py`:

- `SolverOutputStatus`: `"optimal"`, `"suboptimal"`, `"unsafe_diagnostic"`, `"structurally_infeasible"`, `"data_incomplete"`
- `FeedingRecommendation`: `"SAFE_TO_FEED"`, `"FEED_WITH_CAUTION"`, `"DO_NOT_FEED"`
- `ConstraintTier`: `"adequacy_soft"`, `"safety_hard"`, `"envelope_soft"`
- `ClinicalCriticality`: `"critical"`, `"high"`, `"moderate"`, `"low"`

### Dataclasses vs TypedDicts

- **Dataclasses** (`AnimalInput`, `DerEnvelope`, `SolverRequest`, `CrossRefIndex`): runtime objects in `core.py`
- **TypedDicts** (`NutrientEntry`, `SolverOutput`, `AllocationEntry`, etc.): JSON structure contracts in `types.py`

### TYPE_CHECKING Pattern

For modules imported only for type annotations (avoids circular imports):

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import pulp
```

## Running Type Checks

```bash
# Full check
mypy src/gsd/

# With error codes
mypy src/gsd/ --show-error-codes

# Verbose (notes about untyped functions)
mypy src/gsd/ --warn-return-any
```

## CI Integration

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs `mypy` on every push and pull request. The `type-check` job must pass before merge.

## Known Issues and Fixes

### Bugs Fixed During Type-Safety Implementation

Three real bugs were discovered in `doc_introspector.py` and fixed:

1. **Wrong module calls**: `bp_core.calculate_der_and_envelope()` → `bp_nutrition.calculate_der_and_envelope()` (function lives in `nutrition.py`, not `core.py`)
2. **Wrong module call**: `bp_nutrition.check_fat_source_adequacy()` → `bp_solver.check_fat_source_adequacy()` (function lives in `solver.py`)
3. **Missing argument**: `bp_solver.solve_cascade(sel, data, env, scenario)` → `bp_solver.solve_cascade(sel, data, env, scenario, animal)` (5th `animal` parameter was missing)

### TypedDicts as Documentation

`LpProblemDict` and `SolverRawResult` TypedDicts are defined in `types.py` for documentation but are **not wired into function signatures**. Reason: `build_lp_problem()` has an infeasible early-return path that returns a different dict shape, and `solve_cascade()`/`build_output_contract()` construct result dicts with loose field types. Wiring these would require either `Union` return types or widespread `cast()` calls, which reduce readability without meaningful safety gain.

### Remaining `--strict` Mode Gaps

Running `mypy --strict` reveals additional gaps (missing generic type args, untyped callbacks in `mapa.py` section generators). These are beyond current scope — the project targets `disallow_untyped_defs + check_untyped_defs` as sufficient for production use.
