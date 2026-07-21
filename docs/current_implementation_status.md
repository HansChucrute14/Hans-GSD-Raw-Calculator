# Current Implementation Status

**Last reviewed:** 2026-07-20  
**Scope:** current source under `src/gsd/` and the checked-in JSON configuration. This is a reality document, not a design target. The `docs/architecture/sat_*.md` files remain the intended architecture unless this document says otherwise.

## What is implemented

| Area | Current behavior | Evidence |
|---|---|---|
| Package structure | The executable code is the `src/gsd/` package. `build_pipeline.py` is a thin CLI wrapper. | `src/gsd/{cli,core,nutrition,solver,mapa}.py` |
| Cascade | `solve_cascade()` reads the three configured levels in `lp_parameters_data.json` and stops at the first feasible result. | `src/gsd/solver.py:763` |
| Safety outputs | Levels 1 and 2 emit allocations; Level 3 emits `allocations: null`, `DO_NOT_FEED`, and diagnostic analysis. | `src/gsd/solver.py:1031` |
| Clinical criticality | Objective branches now use `critical=10`, `high=5`, `moderate=2`, `low=1`; Level 1 deviations are normalized by target. | `src/gsd/solver.py:7,647-714` |
| Category preferences | Levels 1 and 2 have configured category goals and return `template_adherence` plus audit metadata. | `src/gsd/solver.py:725-761,1131-1167` |
| Clinical floor | Level 3 builds conditional binary floor constraints and has a retry path without the floor when infeasible. | `src/gsd/solver.py:14-480` |
| Output SUL lookup | Nutrients are identified as SULs through `constraint_tier == "safety_hard"`; the obsolete `has_sul` field is no longer used by the output builder. | `src/gsd/solver.py:1086` |

## Known deviations and bugs

| ID | Status | Actual behavior | Consequence / intended correction |
|---|---|---|---|
| R1 | **BUG** | Mineral antagonism constraints always receive unbounded slack variables. Their penalty is added only to the `goal_deviation` objective, which is Level 1; Levels 2 and 3 do not penalize those slacks. | Antagonisms are not hard constraints in any level, contrary to the satellite specifications. Decide whether to make them hard or add and optimize documented slack at every intended level. |
| R2 | **BUG** | Level 3's `sul_violation` stage has `fix_optimum: false`, while `der_deviation` is fixed before adequacy is minimized. | SUL minimization is not preserved when later Level 3 stages solve. The claimed `SUL -> DER -> adequacy` lexicographic guarantee is false. |
| R3 | **BUG** | A deterministic tie-break is added to every objective. Although `tie_break_weight` is `0.001`, the per-ingredient hash perturbation remains `0`-`999.9`. | The tie-break can dominate normalized nutrition objectives and intermediate stages. It is not a negligible tie-break. |
| R4 | **INCOMPLETE OUTPUT** | Every nutrient result is marked `adequate`; `pct_of_min` and `pct_of_sul` are `null`; `target_max` is always `null`. For safety-tier nutrients, `target_min` currently contains the SUL value rather than an adequacy minimum. | The output shape exists, but its nutrient assessment fields are placeholder-like and must not be treated as a clinical assessment. |
| R5 | **INTENTIONAL TEMPORARY IMPLEMENTATION** | Minimum nutrient constraints with IDs ending `_MIN` are forcibly assigned `adequacy_soft`, ignoring the registry tier. | Tier-driven behavior is not fully declarative. Remove the ID-based override when the registry is authoritative. |
| R6 | **IMPLEMENTATION NOISE** | LP construction prints a `[DEBUG]` line for every nutrient minimum constraint. | Runtime output is noisy; remove or gate the print before user-facing use. |
| R7 | **UNVERIFIED IN THIS WORKSPACE** | The `py` launcher reports no installed Python interpreter, so `py -m pytest tests -q` cannot run here. | Historical test claims in older documents are not fresh verification. Re-run tests after installing/activating the project Python environment. |

## Documentation rules going forward

- Use **implemented** only for behavior visible in the current source or a current successful test run.
- Use **known deviation** for behavior that conflicts with the architecture but is intentionally left until a later fix.
- Use **bug** where the current behavior can invalidate a safety, optimization, or output-contract guarantee.
- Do not describe the Level 3 solver as lexicographic, antagonisms as hard, or the tie-break as negligible until R1-R3 are resolved and tested.

## Related documents

- Intended solver contract: `docs/architecture/sat_solver_contrato.md`
- Intended pipeline code: `docs/architecture/sat_pipeline_codigo.md`
- Historical implementation review: `docs/governance/systemic_review_pipeline_vs_satellites.md` (some findings predate the latest criticality/output fixes)
