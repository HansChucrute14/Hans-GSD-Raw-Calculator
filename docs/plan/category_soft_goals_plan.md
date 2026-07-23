---
plan_id: plan-gsd-category-soft-goals
title: "GSD Raw Calculator — Category Soft Goals (BARF/PMR Preferences as Penalized Deviations)"
version: 2.1.0
supersedes: 2.0.0   # folds in critical-review findings (second build_lp_problem crash, two dead
                     # safety-constraint functions); 2.0.0 is retired, do not apply separately
status: ready_for_execution
sequenced_after: none   # standalone plan
path_convention: repo_root
target_agent_profile:
  type: senior_swe_agent
  required_capabilities:
    - python_execution
    - json_editing
    - pytest_execution
    - pulp_lp_modeling
    - git_operations
  forbidden_actions:
    - modify files outside the listed paths
    - introduce hard constraints for category goals (must remain SOFT)
    - apply dynamic normalization to category targets
    - move adequacy slack into Level 1
    - skip the micro-weight multiplier (0.01x)
    - merge commits without verification
    - widen _build_stage_objective's or build_output_contract's parameter list to route around the fixes below (use problem_dict / raw_result side-channels, matching existing patterns)
    - fix the problem_dict-ordering crash without also restoring targets_per_day (a second, independent crash hiding immediately behind the first — see Task-0a)
    - verify Task-0a/Task-0b/Task-0c/Task-0d with textual (rg/import) checks alone — a live end-to-end solve is mandatory (see P11)
    - leave add_der_proximity() / add_ca_p_ratio() uncalled (Task-0b) before starting Task-1 — both are pre-existing, safety-relevant dead code, not part of the category-goals feature but blocking prerequisites for it
    - keep the unconditional db overwrite in build_lp_problem (Task-0c) — any test passing a filtered DB silently gets the full DB instead
    - leave the dead first compute_gaps definition in the file (Task-0d) — it creates misleading debugging output and risks edits targeting the wrong copy
repo:
  root: $PROJECT_ROOT
  data_dir: $PROJECT_ROOT/data
  scripts_dir: $PROJECT_ROOT/scripts
  tests_dir: $PROJECT_ROOT/tests
  docs_dir: $PROJECT_ROOT/docs
  base_commit: <TBD_BY_EXECUTOR>   # executor MUST capture `git rev-parse HEAD` before Task-0a and substitute here
  working_branch: feat/category-soft-goals
total_tasks: 11
parallel_groups: 0   # strictly sequential — every task depends on the previous
created: 2026-07-18T00:00:00Z
updated: 2026-07-17T00:00:00Z
language: en
paradigm: wall_vs_compass   # Level 1 goal_deviation = Wall; category_goal_deviation at 0.01x weight = Compass
---

# Plan: GSD Raw Calculator — Category Soft Goals (Option B) — v2.1.0

## What changed from v2.0.0

A critical-review pass (code-level, not textual) found that v2.0.0's Task-0 fixed a real crash but
was incomplete, and missed a second, independent defect cluster in the same function. Concretely:

1. **A second crash hides directly behind the first.** After removing the premature
   `category_to_ingredients` precompute (v2.0.0's Task-0), `build_lp_problem` still throws —
   `targets_per_day` is read twice (into the `problem_dict` literal, and in the function's `return`)
   but is **never assigned anywhere in the function body**. The function's own numbered comments
   prove it: `# 3. Compile coefficients` → `# 4. BUILD-TIME SANITY ASSERTION` → `# 6. SULs per day`
   — step 5 is missing. This is almost certainly fallout from the same incomplete edit that produced
   the v2.0.0 bug. `targets_per_day` is not cosmetic: `call_lp_solver` and `_build_stage_objective`
   read it to build the `goal_deviation` stage — the Wall itself — plus
   `weighted_normalized_deviation`, `weighted_normalized_slack`, and
   `minimize_weighted_normalized_adequacy_slack`. v2.0.0's own anti-pattern note (former Task-0,
   "Do NOT fix this by moving the `problem_dict = {...}` literal earlier... it depends on
   `targets_per_day`... computed between the two blocks") was factually wrong: `targets_per_day` is
   not computed anywhere in the function, between those blocks or otherwise. This version corrects
   that assumption directly. See **Task-0a**.
2. **Two constraint-building helpers are defined but never called.** `add_der_proximity()` and
   `add_ca_p_ratio()` are fully implemented nested functions inside `build_lp_problem`, but the
   "Assemble constraints" block only calls five of the seven helpers defined above it. Consequences:
   the Ca:P ratio hard constraint — which this very plan's Wall-vs-Compass table already documents
   as an enforced Wall invariant — is not actually enforced today; and the
   `minimize_absolute_der_deviation` objective stage silently falls back to fresh, unconstrained
   dummy variables (its "shouldn't happen" fallback path, which currently always happens), so
   DER-centering does nothing. Both are pre-existing, safety-relevant, and unrelated to category
   goals, but they sit in the exact function this plan edits. See **Task-0b**.
3. **v2.0.0's verification could not have caught either issue**, because it never actually *executes*
   `build_lp_problem` — P10 and the former Task-0's checks are textual (`rg`/`inspect.getsource`) or
   rely on a relative pytest baseline count (`N passed`) that stays numerically satisfied even when
   the function still crashes, as long as the crashing tests were already excluded from the recorded
   baseline. This version adds a mandatory live smoke-solve to preconditions (P11) and to Task-0a/
   Task-0b's own verification, specifically so a second bug can't hide behind a first one again.
4. **Two additional pre-existing defects found during implementation.** During execution of the
   dirty-tree fixes (before committing), two more issues were discovered in the same code area:
   **Task-0c** — an unconditional `db = data.get("DB_ingredientes.json", {})` inside
   `build_lp_problem`'s Compile-coefficients block silently overwrites any `db` the caller passed,
   making the documented `db` parameter dead; and **Task-0d** — a dead first copy of `compute_gaps`
   (lines ~3066–3154) plus 4 orphaned helper functions, never called because the second copy at
   line ~3219+ shadows it at module level. Both are pre-existing, independent of category goals,
   and fixed in their own bisectable commits before Task-1.

Former Task-0 is split into **Task-0a** (both crash fixes — problem_dict ordering, restore
`targets_per_day` — one bisectable commit, since both are "the function throws before it can do
anything" bugs), **Task-0b** (wire in the two dead constraint functions — a separate commit,
since it is a silent-failure fix rather than a crash fix and may warrant independent rollback),
**Task-0c** (remove unconditional `db` overwrite, add `db` parameter — a third pre-existing defect
in the same function that silently nullifies any caller-supplied DB), and **Task-0d** (delete the
dead first `compute_gaps` definition and its 4 orphaned helpers — dead code that creates misleading
search results). Tasks 1–6 are otherwise unchanged from v2.0.0; only their `depends_on` chain and a
few preconditions referencing "Task-0" now point at Task-0a/Task-0b/Task-0c/Task-0d.

## What changed from v1.0.0

v1.0.0 was written against an assumed shape of `build_pipeline.py` rather than the actual file.
Cross-referencing the real code turned up four defects — one of them a live crash bug already
present in the file, independent of this plan. This version replaces v1.0.0 outright: same
objective, same architecture (Wall vs. Compass, absolute targets, micro-weight multiplier), same
task granularity, but every snippet below is checked against the real function signatures in
`build_pipeline.py` (`build_lp_problem`, `_build_stage_objective`, `call_lp_solver`,
`build_output_contract`, `solve_cascade`). Addenda 1 and 2 are retired — nothing here should be
read alongside them.

## Objective

Implement soft goals for ingredient category percentages (`muscle_meat` 70%, `organ_secreting` 10%,
etc.) as **penalized deviations** in the LP objective. Only categories with existing DB ingredients
are included; categories without ingredients (bone, vegetable, fruit, seed, supplement, grain,
dairy, egg) are excluded. This is **Option B** from the critical analysis — minimal risk, maximum
value, zero structural changes to existing hard constraints or cascade architecture.

The mechanism: deviation variables `d_cat_<n>_minus` / `d_cat_<n>_plus` are added to the Level 1 and
Level 2 objective stages with a **micro-weight multiplier** (`base_weight * 0.01`), guaranteeing
they act strictly as tie-breakers and never override nutrient adequacy or antagonism-safety
targets.

## Preconditions (plan-level — MUST hold before Task-0a)

| ID | Condition | Verification command |
|---|---|---|
| P0 | Clean working tree at repo root | `cd $PROJECT_ROOT && git status --short \| wc -l` → `0` |
| P1 | Working branch created from `main` | `git rev-parse --abbrev-ref HEAD` → `feat/category-soft-goals` |
| P2 | Python ≥ 3.10 | `python --version` → `3.10+` |
| P3 | `pulp`, `pytest`, `jsonschema` installed | `python -c "import pulp, pytest, jsonschema; print('ok')"` → exit 0 |
| P4 | Baseline test count established (record it — see note) | `cd $PROJECT_ROOT && python -m pytest tests/ -q` → record `N passed` |
| P5 | `data/lp_parameters_data.json` exists and parses | `python -c "import json; json.load(open('$PROJECT_ROOT/data/lp_parameters_data.json'))"` → exit 0 |
| P6 | `build_pipeline.py` exists at repo root | `ls $PROJECT_ROOT/build_pipeline.py` exits 0 |
| P7 | `build_pipeline.py` exposes `_build_stage_objective`, `build_lp_problem`, `call_lp_solver`, `solve_cascade`, `build_output_contract`, `get_ingredient_by_id` | `rg -n "def _build_stage_objective\|def build_lp_problem\|def call_lp_solver\|def solve_cascade\|def build_output_contract\|def get_ingredient_by_id" $PROJECT_ROOT/build_pipeline.py` → 6 matches |
| P8 | `tests/test_cascade_integration.py` exists | `ls $PROJECT_ROOT/tests/test_cascade_integration.py` exits 0 |
| P9 | `data/DB_ingredientes.json` exposes `protein_sources.<group>.ingredients[].category` field (16-value schema enum; expect a subset actually populated) | `python -c "import json; db=json.load(open('$PROJECT_ROOT/data/DB_ingredientes.json')); cats=set(); [cats.add(i.get('category','')) for g in db['protein_sources'].values() if isinstance(g,dict) for i in g.get('ingredients',[])]; print(sorted(cats))"` → non-empty subset of `{muscle_meat, muscle_organ, organ_secreting, organ_non_secreting, connective_tissue, blood_source, bone, cartilage, fat_source, supplement, grain, vegetable, fruit, dairy, egg, fish}` |
| P10 | **(new)** `build_lp_problem` does not already reference `problem_dict` before it is assigned | `python -c "import inspect, build_pipeline as bp; src = inspect.getsource(bp.build_lp_problem); a = src.find('problem_dict = {'); b = src.find('category_to_ingredients'); print('OK' if (b == -1 or a == -1 or b > a) else 'FAIL: category_to_ingredients precompute appears before problem_dict is assigned')"` → `OK` (if `FAIL`, do not stop — this is exactly what Task-0a fixes; proceed to Task-0a) |
| P11 | **(new)** `build_lp_problem` completes a REAL solve end-to-end without raising — a live execution, not a textual/`rg` check, so it cannot miss a second bug hiding behind a first one | `python -c "import build_pipeline as bp; data = bp.load_all_jsons(); db = data['DB_ingredientes.json']; fr = data['formulation_rules.json']; fr['_db_ref'] = db; sel = ['beef_muscle_raw','chicken_back_raw','beef_liver_raw','beef_kidney_raw','salmon_atlantic_raw']; matrix = bp.build_matrix(sel, db, fr); animal = bp.AnimalInput(sex='male', weight_kg=25.0, age_months=8, gonadal_status='intact', use_gompertz=True); der = bp.calculate_der_and_envelope(animal, data['growth_energy_skeletal.json'], 'SCN_B_SLOW_GROWTH', sel, db); p = bp.build_lp_problem(sel, matrix, data, der, cascade_level=1, db=db); print('OK' if p.get('status') != 'infeasible' else 'FAIL')"` → `OK` (if it raises `UnboundLocalError`/`NameError`, or prints `FAIL`, do not stop — this is exactly what Task-0a/Task-0b fix; proceed to Task-0a) |

If P0–P9 fail, **STOP** and report the blocker — do not attempt to auto-fix preconditions. If P10
or P11 fail (including a raised exception from P11 — capture and record which exception, it tells
you whether Task-0a's first fix, second fix, or both are still needed), proceed — Task-0a/Task-0b
exist specifically to fix them. Do NOT treat a P11 exception as a reason to stop; it is expected to
fail going into Task-0a on an unfixed checkout.

**Note on P4:** v1.0.0 assumed a 32-test baseline. Do not assume a specific number — the repo may
have drifted. Record whatever `N` actually is; all later "N passed" / "N+4 passed" checks in this
plan are relative to that recorded baseline, not to a hardcoded `32`/`36`.

## Postconditions (plan-level — MUST hold after Task-6)

| ID | Condition | Verification command |
|---|---|---|
| Q0 | All `N` baseline tests still pass | `cd $PROJECT_ROOT && python -m pytest tests/ -q -k "not category_goals"` → `N passed` |
| Q1 | 4 new category-goal tests pass | `python -m pytest tests/test_cascade_integration.py -k category_goals -q` → `4 passed` |
| Q2 | `--gate-mapa` passes | `cd $PROJECT_ROOT && python build_pipeline.py --gate-mapa` → exit 0 |
| Q3 | Synthetic test: `muscle_meat` goal pulls solution toward 70% when ingredient pool allows | `python -m pytest tests/test_cascade_integration.py::test_category_goals_influence_solution -q` → `1 passed` |
| Q4 | Level 3 still returns `unsafe_diagnostic` for liver-only selection (hard wall unchanged) | `python -m pytest tests/test_cascade_integration.py -k liver -q` → existing test still passes |
| Q5 | No new hard constraints introduced (only deviation vars + soft objective terms) | `rg -n "cat_sum.*(<=\|>=)" $PROJECT_ROOT/build_pipeline.py` → `0` matches, AND `rg -n "cat_sum - \(target_pct \* total_x\) == d_plus - d_minus" $PROJECT_ROOT/build_pipeline.py` → `1` match |
| Q6 | MAPA regeneration clean | `cd $PROJECT_ROOT && python build_pipeline.py --generate-mapa --out MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md && rg -c "SOURCE: IMPLEMENTATION_SPEC" MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md` → `>= 10` |
| Q7 | Output contract includes `template_adherence` and `solver_metadata.category_goal_deviations_raw` | executor-written inline check (Task-6 V8) → both keys present |
| Q8 | Clean git working tree after final commit | `git status --short` → empty |
| Q9 | **(new)** `build_lp_problem` runs without `UnboundLocalError` or `NameError` at every cascade level, and returns a non-empty `targets_per_day`, independent of category goals | `python -c "import build_pipeline as bp; print('import ok')"` plus Task-0a's own live-solve verification (P11's check, re-run — must still pass at the end) |
| Q10 | **(new)** `add_der_proximity()` and `add_ca_p_ratio()` are wired into `build_lp_problem`'s constraint assembly (Ca:P ratio and DER proximity actually enforced, not dead code) | `rg -c "add_der_proximity\(\)" $PROJECT_ROOT/build_pipeline.py` → `2` (1 def + 1 call), AND `rg -c "add_ca_p_ratio\(\)" $PROJECT_ROOT/build_pipeline.py` → `2`, AND Task-0b's V2/V3 live checks (must still pass at the end) |

## Context Boundary

**The executing agent MAY read:**
- `$PROJECT_ROOT/build_pipeline.py`
- `$PROJECT_ROOT/data/lp_parameters_data.json`
- `$PROJECT_ROOT/data/DB_ingredientes.json`
- `$PROJECT_ROOT/data/db_ingredientes.schema.json`
- `$PROJECT_ROOT/tests/test_cascade_integration.py`
- `$PROJECT_ROOT/tests/test_dimensional_pipeline.py`
- `$PROJECT_ROOT/tests/reference_cases.py`  *(new — Task-4 depends on its exact fixture names; read it, do not guess)*
- `$PROJECT_ROOT/docs/sat_solver_contrato.md`
- `$PROJECT_ROOT/docs/sat_pipeline_codigo.md`
- `$PROJECT_ROOT/docs/indice_plano_central.md`

**The executing agent MAY NOT:**
- Modify files under `$PROJECT_ROOT/data/` except `lp_parameters_data.json` (Task-1)
- Modify `$PROJECT_ROOT/data/DB_ingredientes.json` (read-only — category values consumed as-is)
- Introduce hard constraints on category sums (`prob += cat_sum <= ...` or `prob += cat_sum >= ...`)
- Apply dynamic normalization to category targets (targets are ABSOLUTE, not relative-to-pool)
- Move adequacy slack into Level 1 (Level 1 remains the strict wall)
- Skip the `* 0.01` micro-weight multiplier — effective weights must stay in range `[0.3, 1.0]`
- Touch existing hard constraints (`CSTR_INCL_MAX_LIVER`, antagonism penalties, etc.)
- Leave `targets_per_day` unassigned after Task-0a, or assume it is "already computed somewhere" —
  verify with a live solve (P11-style check), not by reading the code and assuming
- Gate `add_der_proximity()` / `add_ca_p_ratio()` (Task-0b) behind `cascade_level` or `relax_tiers` —
  both are always-hard Wall constraints in Levels 1/2; only Level 3's existing relaxation machinery
  (already inside `add_sul_constraints`/`add_inclusion_constraints`) may vary their behavior
- Run `git push --force` or `git rebase -i` over other tasks' commits
- Reorder Level 1 stages — `goal_deviation` MUST come first with `fix_optimum: true`,
  `category_goal_deviation` second with `fix_optimum: false`, `minimize_absolute_der_deviation`
  third with `fix_optimum: true`
- Add a `lp_params`/`cascade_level` parameter to `_build_stage_objective`, or a `prob` parameter to
  `build_output_contract`, to work around the data-flow fixes in Task-2/Task-3 — use the
  `problem_dict` / `raw_result` side-channels already established in the codebase for every other
  stage kind (`nutrient_slack_vars`, `der_dev_vars`, etc.)

### Wall vs. Compass Architecture (DO NOT VIOLATE)

| Layer | Role | Mechanism |
|---|---|---|
| Wall (Level 1, stage 1) | Strict nutrient adequacy + antagonism safety | `goal_deviation` objective kind with `fix_optimum: true`; hard constraints (`CSTR_INCL_MAX_LIVER <= 5%`, Ca:P ratio\*, antagonism slack penalty 5000) |
| Compass (Level 1, stage 2 + Level 2, stage 2) | BARF/PMR category preferences | `category_goal_deviation` objective kind with `fix_optimum: false`; deviation vars `d_cat_<n>_minus/plus` with effective weight `base_weight * 0.01` (range 0.3–1.0) |

\* **As of the pre-plan checkout, this is aspirational, not actual** — `add_ca_p_ratio()` is fully
implemented but never called, so the Ca:P ratio constraint is not currently in the solved problem.
Task-0b fixes this (independent of category goals) before Task-1 begins; do not assume this row is
true until Task-0b's Q10 verification passes.

**Iron rule:** the Compass MUST NOT become a Wall. If the micro-weight multiplier is removed or
scaled above 0.01, category goals could override a nutrient adequacy floor (e.g., pull muscle to
70% even when copper adequacy requires more liver). The Wall ensures the dog never suffers from
hypervitaminosis A or Ca:P inversion; the Compass gently nudges toward the 70/10/5/5 evolutionary
ideal only when the Wall is already satisfied.

### Absolute vs. Normalized Targets (DO NOT NORMALIZE)

| Approach | Decision | Rationale |
|---|---|---|
| Dynamic normalization (e.g., muscle = 70% / sum_of_active_categories) | REJECTED | BARF/PMR ratios are absolute biological ideals, not relative proportions of whatever is in the bowl. If user omits bone, muscle should NOT mathematically inflate to 77% just to force sum to 100%. |
| Absolute targets (muscle = 70% of total_x, always) | APPROVED | LP deviation variables `d_plus` / `d_minus` naturally absorb the math. If targets sum to 110%, `d_plus` absorbs the 10% overshoot. If a category is missing from the user's selection, `d_minus` absorbs the shortfall. Biological meaning stays intact. |

### Micro-Weight Calibration (DO NOT REMOVE)

| Objective term | Weight scale | Effective contribution |
|---|---|---|
| Nutrient deviation (41 nutrients × clinical weights) | 1–10 per nutrient | ~41–410 total |
| Antagonism slack penalty | 5000 per constraint | dominates any single violation |
| `category_goal_deviation` raw weights | 30–100 per category | ~440 total (if not scaled) |
| `category_goal_deviation` effective weights (after `* 0.01`) | 0.3–1.0 per category | ~4.4 total — strictly a tie-breaker |

**Iron rule:** the `* 0.01` multiplier is mandatory. Without it, category goals (~440) would rival
nutrient deviation (~410) and could pull the solution away from clinically-required nutrient
targets. With it, category goals only break ties between nutrient-equivalent solutions.

### Line Number Caveat

All line numbers in Tasks 0–6 are orientation aids taken from a specific snapshot of
`build_pipeline.py`, not patch coordinates. The executing agent MUST re-locate each target by
content (function name + signature + distinctive comment) using `rg`, NOT by line number. After
each edit, re-run `rg` to confirm the target moved as expected and no other call sites were
silently shifted.

### Data-Flow Map (read this before Task-2/Task-3 — it's the part v1.0.0 got wrong)

```
build_lp_problem(selected_ids, matrix, data, der_info, cascade_level, ..., db=None)
    → computes level_config = next(l for l in lp_params["solve_cascade"] if l["level"]==cascade_level)
    → returns problem_dict  (has "prob", "x_vars", "category_to_ingredients", NEW: "category_goals")
        │
        ▼
call_lp_solver(problem_dict, objective_stages, solver_params)
    → holds `prob` — the only place besides build_lp_problem that does
    → calls _build_stage_objective(..., problem_dict) once per stage
        _build_stage_objective has NO lp_params/cascade_level param —
        it can only read problem_dict["category_goals"], set above
    → returns raw_result dict (has "x_values", "nutrient_values", ..., NEW: "category_goal_deviations")
        │
        ▼
solve_cascade(selected_ids, data, der_info, scenario_id)
    → calls build_lp_problem then call_lp_solver per level, returns first feasible
    → calls build_output_contract(result, level_config, data, der_info, cascade_attempts)
        build_output_contract has NO `prob` param — it only sees raw_result (== result) —
        it must read raw_result["category_goal_deviations"], NOT prob.variablesMap()
    → returns the final output dict (constructed inline in one `return {...}` literal —
      there is no mutable `output` variable to append to; new keys go directly in that literal)
```

Every task below is written against this map. Do not reintroduce a path that requires
`_build_stage_objective` to see `lp_params`/`cascade_level`, or `build_output_contract` to see
`prob` — both would require widening function signatures the rest of the codebase doesn't touch.

---

## Tasks

<!--
Graph convention:
  - depends_on: list of task_ids that MUST be in `completed` status
  - parallel_group: null for all tasks (strictly sequential)
  - Each task = exactly 1 commit
  - Commit message follows Conventional Commits: `feat(scope): description`
-->

---

### Task-0a: Fix BOTH pre-existing crashes in `build_lp_problem` (standalone, unrelated to category goals)

```yaml
task_id: task-0a
title: "Remove premature category_to_ingredients precompute AND restore missing targets_per_day computation"
depends_on: []
parallel_group: null
files_mutated:
  - $PROJECT_ROOT/build_pipeline.py
idempotent: true
estimated_loc: -9 +12   # deletion of the premature block, addition of the missing "step 5"
commit_message: "fix(solver): remove premature problem_dict reference and restore missing targets_per_day computation in build_lp_problem"
severity: blocker
```

**Rationale:** the live file contains two independent, pre-existing crash bugs in `build_lp_problem`,
both unrelated to category goals, both very likely fallout from the same earlier incomplete edit.

*Bug 1:* a category-to-ingredients precompute block references
`problem_dict["category_to_ingredients"] = category_map` before `problem_dict` is assigned later in
the same function. Because Python resolves `problem_dict` as local to the whole function the moment
any assignment to it exists anywhere in the body, this raises `UnboundLocalError: local variable
'problem_dict' referenced before assignment` on **every call to `build_lp_problem`**.

*Bug 2 — hides directly behind Bug 1, and v2.0.0 of this plan missed it entirely:* even after Bug 1
is fixed, the very next thing the function does is build the `problem_dict = {...}` literal, which
includes `"targets_per_day": targets_per_day`. But `targets_per_day` is **never assigned anywhere in
`build_lp_problem`** — not as a local, not as a parameter, not as a nonlocal from a nested helper.
The function's own numbered comments are the tell: `# 3. Compile coefficients` → `# 4. BUILD-TIME
SANITY ASSERTION` → `# 6. SULs per day` — **step 5 is missing**. `targets_per_day` is read back out
of `problem_dict` by `call_lp_solver` and passed into `_build_stage_objective`, where it drives the
`goal_deviation` stage (the Wall itself, `fix_optimum: true`), plus `weighted_normalized_deviation`,
`weighted_normalized_slack`, and `minimize_weighted_normalized_adequacy_slack`. Without it, no
cascade level can solve at all, independent of whether category goals exist. (v2.0.0's Task-0
anti-pattern note claimed `targets_per_day` was "computed between the two blocks" — it is not; that
assumption was never actually verified against a running function, only against the source text.)

Both bugs must be fixed in this one commit — fixing only Bug 1 leaves the function just as broken,
one line later.

**Preconditions (in addition to plan-level):**
- P0–P8 satisfied (P9/P10/P11 informational — P10 and P11 are expected to read `FAIL`/raise going
  into this task)

**Steps:**

1. Locate the broken block via `rg -n "category_to_ingredients" $PROJECT_ROOT/build_pipeline.py`.
   Confirm there are exactly two near-identical blocks inside `build_lp_problem`: one appearing
   before the line `problem_dict = {`, one appearing after.
2. Delete the **first** occurrence in full (the one that appears before `problem_dict = {...}` is
   assigned):
   ```python
   # Pre-compute category to ingredients mapping for O(1) lookups in objective builder.
   # Required by the category_goal_deviation objective kind (Option B — category soft goals).
   category_map = {}
   for iid in valid_selected_ids:
       ing = get_ingredient_by_id(iid, db)
       if ing:
           cat = ing.get("category", "unknown")
           category_map.setdefault(cat, []).append(iid)
   problem_dict["category_to_ingredients"] = category_map
   ```
3. Leave the second occurrence (the one after `problem_dict = {...}`) untouched — it is correct
   as-is and Task-2 will extend it.
4. Verify by content, not position: after the edit, exactly one occurrence of
   `problem_dict["category_to_ingredients"] = category_map` should remain, and it must appear
   textually after `problem_dict = {` in the function source.
5. Locate the missing-step-5 gap via
   `rg -n "# 4\. BUILD-TIME SANITY|# 6\. SULs per day" $PROJECT_ROOT/build_pipeline.py` — confirm
   the comment numbering jumps 4 → 6 with no step 5 (diagnostic evidence, not a fix by itself).
6. Immediately before the `# 6. SULs per day` comment, insert the missing step:
   ```python
   # 5. Targets per day (nutrient minimums, from constraints.json). This step went missing in
   # the same earlier edit that produced the problem_dict-ordering bug fixed above. Required by
   # call_lp_solver / _build_stage_objective (goal_deviation, weighted_normalized_*).
   targets_per_day: dict[str, float] = {}
   for nb in constraints.get("nutrient_bounds", []):
       cid = nb.get("constraint_id", "")
       if not (cid.startswith("CSTR_NB_") and cid.endswith("_MIN")):
           continue
       vars_ref = nb.get("lp_coefficients", {}).get("variables_referenced", [])
       if not vars_ref:
           continue
       nid = vars_ref[0]
       for b in nb.get("lp_coefficients", {}).get("bounds", []):
           if b.get("sense") == ">=" and b.get("rhs", 0) > 0:
               targets_per_day[nid] = float(b["rhs"]) * der_info.units_of_1000kcal
   ```
   This mirrors the identical `target = float(rhs) * der_info.units_of_1000kcal` computation already
   inline inside `add_nutrient_constraints()` (used to build the constraint itself, but never saved
   to a dict). If the executor prefers, `add_nutrient_constraints()` may instead be modified to
   populate `targets_per_day[nid] = target` directly at its existing computation site — either is
   acceptable, but do not implement both (would silently double-count nothing, but is redundant and
   confusing for the next reader); pick one and delete the other's redundant logic if both exist.
7. Verify `targets_per_day` is assigned strictly before its first read (the `problem_dict = {...}`
   literal).

**State mutations:**

| File | Before | After |
|---|---|---|
| `build_pipeline.py` | Two copies of the category-map precompute in `build_lp_problem`, the first referencing `problem_dict` before assignment; `targets_per_day` read twice but never assigned (missing "step 5") | One copy of the category-map precompute remains, positioned after `problem_dict` is assigned; `targets_per_day` is computed from `constraints.json` nutrient minimums before first use; `build_lp_problem` no longer crashes on either bug |

**Verification (deterministic):**

```bash
# V1: file still imports cleanly
python -c "import build_pipeline; print('ok')"
# expected exit: 0

# V2: exactly one precompute assignment remains, and it is positioned after problem_dict exists
python -c "
import inspect, build_pipeline as bp
src = inspect.getsource(bp.build_lp_problem)
assert src.count('problem_dict[\"category_to_ingredients\"] = category_map') == 1, 'expected exactly 1 occurrence'
idx_assign = src.index('problem_dict = {')
idx_precompute = src.index('problem_dict[\"category_to_ingredients\"] = category_map')
assert idx_precompute > idx_assign, 'precompute still appears before problem_dict is assigned'
print('OK')
"
# expected exit: 0

# V3: targets_per_day is assigned before it is first read
python -c "
import inspect, build_pipeline as bp
src = inspect.getsource(bp.build_lp_problem)
idx_use = src.index('\"targets_per_day\": targets_per_day,')
idx_assign_candidates = [i for i in (src.find('targets_per_day: dict'), src.find('targets_per_day = {}'), src.find('targets_per_day={}')) if i != -1]
assert idx_assign_candidates, 'no targets_per_day assignment found at all'
assert min(idx_assign_candidates) < idx_use, 'targets_per_day still read before assignment'
print('OK')
"
# expected exit: 0

# V4 (the important one — a REAL execution, not a textual check; this is exactly what would
# have caught Bug 2 that v2.0.0's textual-only Task-0 verification could not see):
python -c "
import build_pipeline as bp
data = bp.load_all_jsons()
db = data['DB_ingredientes.json']
fr = data['formulation_rules.json']
fr['_db_ref'] = db
selected = ['beef_muscle_raw', 'chicken_back_raw', 'beef_liver_raw', 'beef_kidney_raw', 'salmon_atlantic_raw']
matrix = bp.build_matrix(selected, db, fr)
animal = bp.AnimalInput(sex='male', weight_kg=25.0, age_months=8, gonadal_status='intact', use_gompertz=True)
der = bp.calculate_der_and_envelope(animal, data['growth_energy_skeletal.json'], 'SCN_B_SLOW_GROWTH', selected, db)
problem = bp.build_lp_problem(selected, matrix, data, der, cascade_level=1, db=db)
assert problem.get('status') != 'infeasible', f\"build_lp_problem itself reported infeasible: {problem}\"
assert problem.get('targets_per_day'), 'targets_per_day is empty or missing — nutrient_bounds parsing failed'
print(f\"OK: build_lp_problem returned {len(problem['targets_per_day'])} nutrient targets, no exception raised\")
"
# expected: an "OK: ... N nutrient targets ..." line with N > 0, exit 0

# V5: baseline test suite still holds relative to the recorded P4 baseline
cd $PROJECT_ROOT && python -m pytest tests/ -q -k "not category_goals"
# expected: N passed (the recorded P4 baseline) — this check alone would NOT have caught Bug 2
# if the crashing tests were already excluded from the baseline; V4 above is the check that matters
```

**Rollback:**

```bash
git checkout -- $PROJECT_ROOT/build_pipeline.py
```

**Anti-patterns to avoid in this task:**
- Do NOT stop after fixing only Bug 1 (the `problem_dict` ordering issue) — the function will still
  crash one line later on the undefined `targets_per_day`; both bugs are in scope for this commit
- Do NOT trust `import build_pipeline` success or a stable pytest baseline count as proof the
  function works — neither executes `build_lp_problem`'s body far enough to hit either bug in a way
  that would be visible without V4's live solve; use V4, not just V1/V2/V3/V5, as the real gate
- Do NOT fix the `problem_dict` ordering bug by moving the `problem_dict = {...}` dict literal
  earlier in the function instead — it genuinely does depend on `suls_per_day`, `em_per_g`, and (once
  restored) `targets_per_day`, all computed between the two blocks; moving it up relocates the crash
  rather than fixing it
- Do NOT delete the second (correct) `category_to_ingredients` occurrence by mistake — confirm which
  one is "first" by textual position relative to `problem_dict = {`, not by which one visually looks
  more complete
- Do NOT invent a different source for `targets_per_day` (e.g. pulling straight from
  `NUTRIENT_REGISTRY` without going through `constraints.json`'s `nutrient_bounds`) — the rest of the
  codebase (`add_nutrient_constraints`) already treats `constraints.json`'s `CSTR_NB_*_MIN` bounds as
  the source of truth for nutrient targets; a second, divergent source would desync the constraint
  and the objective's idea of what the target is
- Do NOT fold this into Task-2's commit — it's an independent, pre-existing defect and deserves its
  own bisectable commit

---

### Task-0b: Wire the two dead safety-constraint functions into `build_lp_problem` (standalone, unrelated to category goals)

```yaml
task_id: task-0b
title: "Call add_der_proximity() and add_ca_p_ratio() in build_lp_problem's constraint-assembly block"
depends_on:
  - task-0a
parallel_group: null
files_mutated:
  - $PROJECT_ROOT/build_pipeline.py
idempotent: true
estimated_loc: +2
commit_message: "fix(solver): wire add_der_proximity and add_ca_p_ratio into constraint assembly (both were dead code)"
severity: blocker
```

**Rationale:** `add_der_proximity()` and `add_ca_p_ratio()` are fully implemented nested functions
inside `build_lp_problem`, but the "Assemble constraints" block only calls five of the seven helpers
defined above it — `add_nutrient_constraints()`, `add_sul_constraints()`,
`add_inclusion_constraints()`, `add_antagonism_constraints()`, `add_envelope_constraints()`. Neither
`add_der_proximity()` nor `add_ca_p_ratio()` is ever invoked, anywhere in the file. Two consequences,
both pre-existing and both independent of category goals:

1. **Ca:P ratio is not enforced.** This plan's own Wall-vs-Compass table documents Ca:P ratio as an
   already-enforced hard constraint of "the Wall." It is not — for a large-breed puppy
   skeletal-development calculator, an unenforced Ca:P ratio is the single highest-consequence gap in
   this codebase, and it has nothing to do with category goals.
2. **DER proximity silently no-ops.** Because `add_der_proximity()` never runs, `der_dev_plus`/
   `der_dev_minus` stay empty dicts, so `_build_stage_objective`'s `minimize_absolute_der_deviation`
   branch always hits its "Fallback - create if not exist (shouldn't happen)" path — which currently
   *always* happens — and creates fresh, unconstrained variables with no relationship to actual
   energy intake. The objective stage that's supposed to center the diet on the target daily energy
   requirement currently does nothing.

Fixing this now (rather than after category goals land) keeps the two failure classes separable:
if something goes wrong once category goals are added, it should be traceable to that feature, not
entangled with a pre-existing, unrelated gap in the Wall.

**Preconditions (in addition to plan-level):**
- Task-0a committed (V1–V5 all pass, including the live-solve V4)

**Steps:**

1. Locate the constraint-assembly block via `rg -n "# Assemble constraints" $PROJECT_ROOT/build_pipeline.py`.
2. Add the two missing calls after the existing five:
   ```python
   add_nutrient_constraints()
   add_sul_constraints()
   add_inclusion_constraints(relax=(cascade_level == 3))
   add_antagonism_constraints()
   add_envelope_constraints()
   add_der_proximity()
   add_ca_p_ratio()
   ```
3. Confirm neither function is already called elsewhere in the file (it shouldn't be — that's the
   whole bug) via `rg -n "add_der_proximity\(\)|add_ca_p_ratio\(\)" $PROJECT_ROOT/build_pipeline.py`.

**State mutations:**

| File | Before | After |
|---|---|---|
| `build_pipeline.py` | `add_der_proximity()` and `add_ca_p_ratio()` defined but never called; Ca:P ratio unenforced, DER proximity stage falls back to unconstrained dummy vars | Both helpers called in "Assemble constraints"; Ca:P ratio is a real hard constraint on every solve; DER proximity vars are properly linked to total energy |

**Verification (deterministic):**

```bash
# V1: both helpers are now called exactly once each (1 def + 1 call = 2 occurrences)
rg -c "add_der_proximity\(\)" $PROJECT_ROOT/build_pipeline.py
# expected: 2
rg -c "add_ca_p_ratio\(\)" $PROJECT_ROOT/build_pipeline.py
# expected: 2

# V2: live solve now produces real (non-fallback) DER proximity vars
python -c "
import build_pipeline as bp
data = bp.load_all_jsons()
db = data['DB_ingredientes.json']
fr = data['formulation_rules.json']
fr['_db_ref'] = db
selected = ['beef_muscle_raw', 'chicken_back_raw', 'beef_liver_raw', 'beef_kidney_raw', 'salmon_atlantic_raw']
matrix = bp.build_matrix(selected, db, fr)
animal = bp.AnimalInput(sex='male', weight_kg=25.0, age_months=8, gonadal_status='intact', use_gompertz=True)
der = bp.calculate_der_and_envelope(animal, data['growth_energy_skeletal.json'], 'SCN_B_SLOW_GROWTH', selected, db)
problem = bp.build_lp_problem(selected, matrix, data, der, cascade_level=1, db=db)
dvars = problem.get('der_dev_vars', {})
assert 'dev_der_plus' in dvars and 'dev_der_minus' in dvars, f\"add_der_proximity still not wired — der_dev_vars={dvars}\"
print('OK: DER proximity vars present')
"
# expected: OK line, exit 0

# V3: Ca:P ratio is actually enforced end-to-end (full solve, real ratio check)
python -c "
import build_pipeline as bp
data = bp.load_all_jsons()
db = data['DB_ingredientes.json']
fr = data['formulation_rules.json']
fr['_db_ref'] = db
lp_params = data['lp_parameters_data.json']
selected = ['beef_muscle_raw', 'chicken_back_raw', 'beef_liver_raw', 'beef_kidney_raw', 'salmon_atlantic_raw']
matrix = bp.build_matrix(selected, db, fr)
animal = bp.AnimalInput(sex='male', weight_kg=25.0, age_months=8, gonadal_status='intact', use_gompertz=True)
der = bp.calculate_der_and_envelope(animal, data['growth_energy_skeletal.json'], 'SCN_B_SLOW_GROWTH', selected, db)
problem = bp.build_lp_problem(selected, matrix, data, der, cascade_level=1, db=db)
level_config = next(l for l in lp_params['solve_cascade'] if l['level'] == 1)
result = bp.call_lp_solver(problem, level_config['objective_stages'], lp_params.get('solver_params', {}))
assert result['status'] == 'feasible', f\"solve failed: {result}\"
ca = result['nutrient_values'].get('calcium_g', 0)
p = result['nutrient_values'].get('phosphorus_g', 0)
assert p > 0, 'phosphorus_g not in solved nutrient_values — cannot check ratio'
ratio = ca / p
assert 1.1 - 1e-6 <= ratio <= 1.3 + 1e-6, f\"Ca:P ratio {ratio:.3f} outside [1.1, 1.3] — add_ca_p_ratio not enforced\"
print(f\"OK: Ca:P ratio = {ratio:.3f}, within [1.1, 1.3]\")
"
# expected: OK line, exit 0

# V4: baseline test suite still holds
cd $PROJECT_ROOT && python -m pytest tests/ -q -k "not category_goals"
# expected: N passed (the recorded P4 baseline)
```

**Rollback:**

```bash
git checkout -- $PROJECT_ROOT/build_pipeline.py
```

**Anti-patterns to avoid in this task:**
- Do NOT gate these two calls behind `cascade_level` or `relax_tiers` — they are always-hard Wall
  constraints at Levels 1/2; Level 3's relaxation is already handled by the existing
  `relax=(cascade_level == 3)` argument to `add_inclusion_constraints` and the `safety_hard` handling
  inside `add_sul_constraints` — do not invent a third relaxation path for these two
- Do NOT fold this into Task-0a's commit — it is a silent-failure fix, not a crash fix, and may
  warrant independent review or rollback (e.g. if it turns out some ingredient pools become
  infeasible once Ca:P ratio is actually enforced, that is a separate, potentially blocking
  discussion from "the pipeline no longer crashes")
- Do NOT "fix" V3's assertion by widening the [1.1, 1.3] tolerance — that range comes directly from
  `add_ca_p_ratio()`'s own hard-coded bounds (`ca >= 1.1 * p`, `ca <= 1.3 * p`); if V3 fails, the bug
  is in the wiring, not the test bounds
- Do NOT assume this task is optional or "nice to have" because it doesn't crash anything — an
  unenforced Ca:P ratio is a silent correctness/safety gap, not a cosmetic one

---

### Task-1: Add `category_goals` config to `lp_parameters_data.json`

```yaml
task_id: task-1
title: "Add category_goals config to Level 1 and Level 2 solve_cascade entries"
depends_on:
  - task-0b
parallel_group: null
files_mutated:
  - $PROJECT_ROOT/data/lp_parameters_data.json
idempotent: true
estimated_loc: ~80   # JSON additions only, no code
commit_message: "feat(config): add category_goals to Level 1 and Level 2 solve_cascade"
severity: blocker
```

**Rationale:** the LP solver reads `solve_cascade[level].objective_stages` and
`solve_cascade[level].category_goals` from this JSON. Without this config, Task-2 has nothing to
consume. Adding it as a separate commit keeps the config-vs-code boundary clean and lets the
executor verify the schema is still valid before any Python code is touched.

**Preconditions (in addition to plan-level):**
- Task-0a committed (V1–V5 all pass, including the live-solve V4)
- Task-0b committed (V1–V4 all pass — Ca:P ratio and DER proximity are now actually enforced)
- P9 satisfied (category values confirmed present in DB)

**Steps:**

1. Open `$PROJECT_ROOT/data/lp_parameters_data.json`.
2. Locate the `solve_cascade` array (top-level key). It currently has Level 1, Level 2, Level 3
   entries.
3. In the **Level 1 entry** (the one with `"relax_tiers": []`), modify `objective_stages` to insert
   a new stage between the existing `goal_deviation` stage and the existing
   `minimize_absolute_der_deviation` stage:
   ```json
   {
     "name": "category_preferences",
     "kind": "category_goal_deviation",
     "fix_optimum": false
   }
   ```
4. In the same Level 1 entry, add a new top-level key `category_goals` (sibling to
   `objective_stages`, `relax_tiers`, `result_status`):
   ```json
   "category_goals": {
     "muscle_meat":         {"target_pct": 70, "weight": 100, "categories": ["muscle_meat", "fish"]},
     "organ_secreting":     {"target_pct": 10, "weight": 80,  "categories": ["organ_secreting"]},
     "organ_non_secreting": {"target_pct": 5,  "weight": 40,  "categories": ["organ_non_secreting"]},
     "muscle_organ":        {"target_pct": 5,  "weight": 40,  "categories": ["muscle_organ"]},
     "connective_tissue":   {"target_pct": 5,  "weight": 30,  "categories": ["connective_tissue"]},
     "blood_source":        {"target_pct": 3,  "weight": 30,  "categories": ["blood_source"]},
     "fat_source":          {"target_pct": 12, "weight": 60,  "categories": ["fat_source"]}
   }
   ```
5. In the **Level 2 entry** (the one with `"relax_tiers": ["adequacy_soft", "envelope_soft"]`),
   insert the same `category_preferences` stage between the existing `weighted_normalized_slack`
   stage and the existing `minimize_absolute_der_deviation` stage.
6. In the same Level 2 entry, add the identical `category_goals` block (copy-paste from Level 1 —
   they MUST be byte-identical).
7. **Do NOT modify Level 3.** Level 3 is the diagnostic-only fallback; it must not be touched by
   this plan.
8. Verify JSON still parses and Level 1 stage ordering is exactly: `goal_deviation`
   (`fix_optimum: true`) → `category_preferences` (`fix_optimum: false`) →
   `minimize_absolute_der_deviation` (`fix_optimum: true`).

**State mutations:**

| File | Before | After |
|---|---|---|
| `data/lp_parameters_data.json` | Level 1 has 2 objective_stages, no `category_goals` key; Level 2 has 2 objective_stages, no `category_goals` key | Level 1 has 3 objective_stages (new `category_preferences` inserted in slot 2) + `category_goals` block with 7 entries; Level 2 mirrors Level 1; Level 3 unchanged |

**Verification (deterministic):**

```bash
# V1: JSON parses
python -c "import json; json.load(open('$PROJECT_ROOT/data/lp_parameters_data.json'))"
# expected exit: 0

# V2: Level 1 has exactly 3 objective_stages in the correct order with correct fix_optimum flags
python -c "
import json
d = json.load(open('$PROJECT_ROOT/data/lp_parameters_data.json'))
l1 = next(l for l in d['solve_cascade'] if l['level'] == 1)
stages = l1['objective_stages']
assert len(stages) == 3, f'Level 1 has {len(stages)} stages, expected 3'
assert stages[0]['kind'] == 'goal_deviation' and stages[0]['fix_optimum'] == True
assert stages[1]['kind'] == 'category_goal_deviation' and stages[1]['fix_optimum'] == False
assert stages[2]['kind'] == 'minimize_absolute_der_deviation' and stages[2]['fix_optimum'] == True
print('OK: Level 1 stage ordering correct')
"
# expected exit: 0

# V3: Level 2 has the same category_preferences stage and identical category_goals
python -c "
import json
d = json.load(open('$PROJECT_ROOT/data/lp_parameters_data.json'))
l1 = next(l for l in d['solve_cascade'] if l['level'] == 1)
l2 = next(l for l in d['solve_cascade'] if l['level'] == 2)
assert any(s['kind'] == 'category_goal_deviation' for s in l2['objective_stages']), 'Level 2 missing category_goal_deviation stage'
assert l1['category_goals'] == l2['category_goals'], 'Level 1 and Level 2 category_goals differ'
assert len(l1['category_goals']) == 7, f'Expected 7 category_goals, got {len(l1[\"category_goals\"])}'
print('OK: Level 2 mirrors Level 1')
"
# expected exit: 0

# V4: Level 3 is unchanged (still has zero category_goal_deviation stages)
python -c "
import json
d = json.load(open('$PROJECT_ROOT/data/lp_parameters_data.json'))
l3 = next(l for l in d['solve_cascade'] if l['level'] == 3)
assert not any(s['kind'] == 'category_goal_deviation' for s in l3['objective_stages']), 'Level 3 should NOT have category_goal_deviation'
assert 'category_goals' not in l3, 'Level 3 should NOT have category_goals key'
print('OK: Level 3 unchanged')
"
# expected exit: 0

# V5: targets sum to 110% (not 100% — this is intentional, see "Absolute vs. Normalized Targets")
python -c "
import json
d = json.load(open('$PROJECT_ROOT/data/lp_parameters_data.json'))
l1 = next(l for l in d['solve_cascade'] if l['level'] == 1)
total = sum(g['target_pct'] for g in l1['category_goals'].values())
assert total == 110, f'Targets sum to {total}%, expected 110% (overshoot absorbed by d_plus)'
print(f'OK: targets sum to {total}% (intentional)')
"
# expected exit: 0

# V6: schema still passes (if a JSON schema exists for lp_parameters_data.json)
python -c "
import json, jsonschema, os
schema_path = '$PROJECT_ROOT/data/lp_parameters_data.schema.json'
if os.path.exists(schema_path):
    schema = json.load(open(schema_path))
    data = json.load(open('$PROJECT_ROOT/data/lp_parameters_data.json'))
    jsonschema.validate(data, schema)
    print('OK: schema validates')
else:
    print('OK: no schema file — skipping')
"
# expected exit: 0
```

**Rollback:**

```bash
git checkout -- $PROJECT_ROOT/data/lp_parameters_data.json
```

**Anti-patterns to avoid in this task:**
- Do NOT normalize target_pct values to sum to 100% (the 110% sum is intentional; `d_plus` absorbs
  the overshoot)
- Do NOT add `category_goals` to Level 3 (Level 3 is diagnostic-only)
- Do NOT set `fix_optimum: true` on the `category_preferences` stage (it MUST be `false` — category
  goals are a Compass, not a Wall)
- Do NOT skip Level 2 (category goals MUST also exist at Level 2 to provide a "compass" when the
  solver drops to a relaxed floor)
- Do NOT add categories that have zero DB ingredients (bone, vegetable, fruit, etc.) — only the 7
  categories listed above

---

### Task-2: Implement `category_goal_deviation` objective kind (corrected data flow)

```yaml
task_id: task-2
title: "Implement category_goal_deviation objective kind via problem_dict side-channel, extend category-map precompute"
depends_on:
  - task-1
parallel_group: null
files_mutated:
  - $PROJECT_ROOT/build_pipeline.py
idempotent: true
estimated_loc: ~45
commit_message: "feat(solver): implement category_goal_deviation objective kind with micro-weight multiplier"
severity: blocker
```

**Rationale:** this task adds the LP-side logic that consumes the `category_goals` config from
Task-1. Critically, `_build_stage_objective` (the function that dispatches on `kind`) has **no
access to `lp_params` or `cascade_level`** — it only receives `problem_dict`. So `category_goals`
must be handed to it via `problem_dict`, exactly the way `nutrient_slack_vars`, `sul_slack_vars`,
and `der_dev_vars` already are. This is the part v1.0.0 got wrong (it assumed
`_build_stage_objective` could re-derive `level_config` from `lp_params` itself).

**Preconditions (in addition to plan-level):**
- Task-1 committed (V1–V6 all pass)
- Task-0a committed (`build_lp_problem` no longer crashes on either the `problem_dict` ordering bug
  or the missing `targets_per_day` computation)
- Task-0b committed (Ca:P ratio / DER proximity wired in — unrelated to this task, but sequenced
  before it)
- P7 satisfied

**Steps:**

1. **Extend the (already-fixed, single) category-map precompute in `build_lp_problem`.** Locate it
   via `rg -n "category_to_ingredients" $PROJECT_ROOT/build_pipeline.py` — after Task-0a, exactly one
   occurrence should exist, positioned after `problem_dict = {...}`. Immediately after that line
   (`problem_dict["category_to_ingredients"] = category_map`), and after `level_config` has been
   computed further down the function (`rg -n "level_config = next"` to find it — it is computed
   once, for building constraints), add:
   ```python
   # Hand category_goals to the objective builder via problem_dict — it has no
   # access to lp_params or cascade_level itself (see _build_stage_objective signature).
   problem_dict["category_goals"] = level_config.get("category_goals", {})
   ```
   If `level_config` is computed *before* `problem_dict` in the function body, add this line
   immediately after `level_config` is assigned instead; either position is correct as long as both
   `problem_dict` and `level_config` already exist at that point. Re-locate by content, not line
   number, per the Line Number Caveat.

2. **Confirm `db` reaches `build_lp_problem`.** Locate call site(s) via
   `rg -n "build_lp_problem(" $PROJECT_ROOT/build_pipeline.py`. The real signature already accepts
   `db: dict | None = None` — confirm `solve_cascade` passes `db=data.get("DB_ingredientes.json", {})`
   (it already does, per the current file). No change needed here unless a call site is found that
   omits it.

3. **Implement the `category_goal_deviation` objective kind.** Locate
   `def _build_stage_objective` via `rg -n "def _build_stage_objective"
   $PROJECT_ROOT/build_pipeline.py`. Inside the `elif kind == ...` dispatch chain, add a new branch
   — reading `category_goals` from `problem_dict`, NOT from `lp_params`:
   ```python
   elif kind == "category_goal_deviation":
       # Both maps come from problem_dict — this function has no lp_params/cascade_level
       # parameter, so it cannot re-derive level_config itself (see build_lp_problem, step 1).
       category_map = problem_dict.get("category_to_ingredients", {})
       goals = problem_dict.get("category_goals", {})

       expr = 0
       total_x = pulp.lpSum(x_vars[iid] for iid in x_vars)

       for goal_name, goal in goals.items():
           target_pct = goal.get("target_pct", 0) / 100.0  # ABSOLUTE target (e.g., 0.70)
           base_weight = goal.get("weight", 50)
           cat_list = goal.get("categories", [])

           # Gather ingredients for this category across all mapped sub-categories.
           cat_ingredients = []
           for c in cat_list:
               cat_ingredients.extend(category_map.get(c, []))

           if not cat_ingredients:
               # User didn't select any ingredients in this category — skip silently.
               # No d_minus/d_plus variables are created, so no penalty, and downstream
               # (Task-3) must treat this as "not applicable", never as "0% achieved".
               continue

           cat_sum = pulp.lpSum(x_vars[iid] for iid in cat_ingredients if iid in x_vars)

           # Create deviation variables (ABSOLUTE targets, no normalization).
           d_minus = prob.add_variable(f"d_cat_{goal_name}_minus", lowBound=0, cat="Continuous")
           d_plus  = prob.add_variable(f"d_cat_{goal_name}_plus",  lowBound=0, cat="Continuous")

           # Equality constraint: cat_sum - (target_pct * total_x) = d_plus - d_minus.
           # This is NOT a hard constraint on cat_sum — it just defines the deviation vars.
           prob += cat_sum - (target_pct * total_x) == d_plus - d_minus

           # MICRO-WEIGHT: multiply by 0.01 to ensure this is strictly a tie-breaker.
           # Effective weight range: 0.3 to 1.0.
           # Nutrient weights are 1-10. Antagonism slack is 5000.
           # This guarantees category goals NEVER override nutrient adequacy or safety.
           effective_weight = base_weight * 0.01
           expr += (d_minus + d_plus) * effective_weight

       return expr
   ```

4. Verify no other `elif kind ==` branch was clobbered by re-running
   `rg -n "elif kind ==" build_pipeline.py` and confirming the count increased by exactly 1.
5. Verify `pulp` is imported at the top of `build_pipeline.py`
   (`rg -n "^import pulp" build_pipeline.py` — note: in the current file `pulp` is imported locally
   inside functions like `build_lp_problem`/`call_lp_solver`/`_build_stage_objective` via
   `import pulp` at the top of each function body, not necessarily at module top level; confirm
   `_build_stage_objective` already has `import pulp` in its body — it does — so the new branch can
   use `pulp.lpSum` without further changes).

**State mutations:**

| File | Before | After |
|---|---|---|
| `build_pipeline.py` | `_build_stage_objective` has no `category_goal_deviation` branch; `build_lp_problem` computes `category_to_ingredients` but not `category_goals` on `problem_dict` | New `elif kind == "category_goal_deviation"` branch (~25 LOC) reading from `problem_dict`; `build_lp_problem` additionally stashes `problem_dict["category_goals"]` (~3 LOC) |

**Verification (deterministic):**

```bash
# V1: file still imports cleanly
python -c "import build_pipeline; print('ok')"
# expected exit: 0

# V2: new objective kind branch is present exactly once
rg -c "elif kind == \"category_goal_deviation\"" $PROJECT_ROOT/build_pipeline.py
# expected: 1

# V3: micro-weight multiplier is present and not removed
rg -n "effective_weight = base_weight \* 0.01" $PROJECT_ROOT/build_pipeline.py
# expected: 1 match

# V4: category_goals is populated onto problem_dict in build_lp_problem (NOT re-derived
# from lp_params inside _build_stage_objective — that lookup is structurally impossible
# given the function's real parameter list)
rg -n 'problem_dict\["category_goals"\] = level_config.get\("category_goals"' $PROJECT_ROOT/build_pipeline.py
# expected: 1 match
rg -n 'problem_dict.get\("category_goals"' $PROJECT_ROOT/build_pipeline.py
# expected: >= 1 match (inside _build_stage_objective)

# V5: NO hard constraint was introduced on cat_sum (only equality for deviation vars)
rg -n "cat_sum.*(<=|>=)" $PROJECT_ROOT/build_pipeline.py
# expected: 0 matches
rg -n "cat_sum - \(target_pct \* total_x\) == d_plus - d_minus" $PROJECT_ROOT/build_pipeline.py
# expected: 1 match

# V6: baseline tests still green (the stage isn't exercised by any existing test yet,
# but the dispatch chain and build_lp_problem must still import/run cleanly)
cd $PROJECT_ROOT && python -m pytest tests/ -q -k "not category_goals"
# expected: N passed (the recorded P4 baseline)
```

**Rollback:**

```bash
git checkout -- $PROJECT_ROOT/build_pipeline.py
```

**Anti-patterns to avoid in this task:**
- Do NOT remove the `* 0.01` micro-weight multiplier (effective weight would jump from 0.3–1.0 to
  30–100, rivaling nutrient deviation)
- Do NOT normalize `target_pct` against the sum of active categories (targets are ABSOLUTE)
- Do NOT add `prob += cat_sum <= ...` or `prob += cat_sum >= ...` (only equality constraints for
  deviation vars)
- Do NOT skip the `if not cat_ingredients: continue` guard — without it, `cat_sum = pulp.lpSum([])`
  = 0, and the deviation var would force a misleading penalty against an empty category
- Do NOT move this stage to Level 1 slot 1 — it MUST be slot 2 (after `goal_deviation` with
  `fix_optimum: true`)
- Do NOT give `_build_stage_objective` a new `lp_params`/`cascade_level` parameter to re-derive
  `category_goals` independently — that widens a function used by every objective stage for the
  sake of one stage kind, when the existing `problem_dict` side-channel already solves it

---

### Task-3: Add `template_adherence` block + raw deviations to output contract (corrected data flow)

```yaml
task_id: task-3
title: "Thread category-goal deviation values through call_lp_solver into build_output_contract"
depends_on:
  - task-2
parallel_group: null
files_mutated:
  - $PROJECT_ROOT/build_pipeline.py
idempotent: true
estimated_loc: ~45
commit_message: "feat(output): expose template_adherence and category_goal_deviations_raw in output contract"
severity: blocker
```

**Rationale:** `build_output_contract`'s real signature is
`(raw_result, level_config, data, der_info, cascade_attempts)` — it never receives `prob`, only the
plain dict that `call_lp_solver` returns. So the `d_cat_<n>_minus/plus` values must be captured
inside `call_lp_solver` (which does hold `prob`) and carried forward in its return dict — the same
pattern already used for `nutrient_slack_vars`, `sul_slack_vars`, and `der_dev_vars`. Also: any
category with zero ingredients in the pool never gets `d_minus`/`d_plus` variables created at all
(Task-2's `if not cat_ingredients: continue` guard) — the output-contract logic must recognize that
absence explicitly, not silently report it as a perfect 0-deviation match.

**Preconditions (in addition to plan-level):**
- Task-2 committed (V1–V6 all pass)

**Steps:**

1. **Capture deviation values in `call_lp_solver`.** Locate the solution-extraction block via
   `rg -n "Extract solution" $PROJECT_ROOT/build_pipeline.py` (the line
   `x_values = {iid: pulp.value(var) for iid, var in x_vars.items() ...}`). Immediately after it,
   add:
   ```python
   # Capture category-goal deviation variable values (Option B — category soft goals).
   # d_cat_<n>_minus/plus that were never created (empty category — see
   # _build_stage_objective's `if not cat_ingredients: continue`) simply won't appear here.
   category_goal_deviations = {
       v.name: pulp.value(v) for v in prob.variables() if v.name.startswith("d_cat_")
   }
   ```
2. Add it to `call_lp_solver`'s returned dict (the `return {"status": "feasible", ...}` block),
   as a new key alongside the existing `nutrient_slack_vars` / `der_dev_vars` /
   `clinical_floor_bounds` entries:
   ```python
   "category_goal_deviations": category_goal_deviations,
   ```
3. **Read the values back in `build_output_contract`.** Locate `def build_output_contract` via
   `rg -n "def build_output_contract"`. This function already builds `allocations` from
   `raw_result` and ends in a single `return {...}` dict literal (there is no mutable `output`
   variable to append keys onto — confirm this via `rg -n "^    return \{" build_pipeline.py`
   inside this function before assuming otherwise). Before that final `return`, insert:
   ```python
   # === Category goal deviations (Option B — BARF/PMR template adherence) ===
   category_goals = level_config.get("category_goals", {})
   deviations = raw_result.get("category_goal_deviations", {})
   template_adherence = {"components": {}}
   total_deviation = 0.0

   for goal_name, goal in category_goals.items():
       d_minus = deviations.get(f"d_cat_{goal_name}_minus")
       d_plus  = deviations.get(f"d_cat_{goal_name}_plus")

       if d_minus is None and d_plus is None:
           # Category had zero ingredients in the pool — no deviation vars were ever
           # created for it. Do NOT report a fabricated 100% match; mark it explicitly
           # and exclude it from overall_score.
           template_adherence["components"][goal_name] = {
               "target_pct": goal.get("target_pct", 0),
               "achieved_pct": 0.0,
               "absolute_deviation_pct": None,
               "skipped": True,
           }
           continue

       d_minus = d_minus or 0.0
       d_plus  = d_plus or 0.0
       target = goal.get("target_pct", 0)
       achieved = target + (d_plus - d_minus)
       abs_dev = d_plus + d_minus

       template_adherence["components"][goal_name] = {
           "target_pct": target,
           "achieved_pct": round(max(0.0, achieved), 2),
           "absolute_deviation_pct": round(abs_dev, 2),
           "skipped": False,
       }

       if abs_dev > 0:
           total_deviation += abs_dev

   # Overall score: 100 = perfect BARF/PMR match, 0 = maximally deviating. Clamped to [0, 100].
   # Skipped (not-applicable) categories are excluded from the sum above, not penalized.
   template_adherence["overall_score"] = round(max(0.0, 100.0 - total_deviation), 1)
   ```
4. Add two new keys to the function's final `return {...}` dict literal (do not build a separate
   mutable dict and try to `.setdefault(...)` onto it — the real function has no such variable):
   ```python
   "template_adherence": template_adherence,
   ```
   and, inside the existing `meta = {...}` dict (already built earlier in the function, used as
   `"solver_metadata": meta` in the return literal — confirm via
   `rg -n "meta = \{" build_pipeline.py` inside this function), add one line before the return:
   ```python
   meta["category_goal_deviations_raw"] = template_adherence["components"]
   ```

**State mutations:**

| File | Before | After |
|---|---|---|
| `build_pipeline.py` | `call_lp_solver`'s return dict has no deviation-variable values; `build_output_contract`'s return literal has no `template_adherence` key and `meta` has no `category_goal_deviations_raw` | `call_lp_solver` returns `category_goal_deviations`; `build_output_contract`'s return literal includes `template_adherence`; `meta["category_goal_deviations_raw"]` set before return |

**Verification (deterministic):**

```bash
# V1: file still imports cleanly
python -c "import build_pipeline; print('ok')"
# expected exit: 0

# V2: call_lp_solver threads deviation values forward
rg -n '"category_goal_deviations": category_goal_deviations' $PROJECT_ROOT/build_pipeline.py
# expected: 1 match

# V3: build_output_contract reads from raw_result, never from a bare `prob`
rg -n 'raw_result.get\("category_goal_deviations"' $PROJECT_ROOT/build_pipeline.py
# expected: 1 match
rg -n "prob\.variablesMap" $PROJECT_ROOT/build_pipeline.py
# expected: 0 matches (that pattern is only valid where `prob` is actually in scope —
# call_lp_solver / build_lp_problem — never inside build_output_contract)

# V4: template_adherence and the raw audit field are both wired into the return
rg -n '"template_adherence": template_adherence' $PROJECT_ROOT/build_pipeline.py
# expected: 1 match
rg -n 'meta\["category_goal_deviations_raw"\] = template_adherence\["components"\]' $PROJECT_ROOT/build_pipeline.py
# expected: 1 match

# V5: skipped-category guard present (never fabricate a 100% match for an empty category)
rg -n '"skipped": True' $PROJECT_ROOT/build_pipeline.py
# expected: 1 match

# V6: overall_score formula present and clamped
rg -n "max\(0\.0, 100\.0 - total_deviation\)" $PROJECT_ROOT/build_pipeline.py
# expected: 1 match

# V7: baseline tests still green
cd $PROJECT_ROOT && python -m pytest tests/ -q -k "not category_goals"
# expected: N passed (the recorded P4 baseline)

# V8: synthetic smoke test — confirm call_lp_solver's variable-name round-trip actually works
python -c "
import pulp
prob = pulp.LpProblem('smoke', pulp.LpMinimize)
x = {'beef_muscle_raw': pulp.LpVariable('x_beef_muscle_raw', 0, 1)}
total_x = pulp.lpSum(x.values())
d_minus = pulp.LpVariable('d_cat_muscle_meat_minus', 0)
d_plus  = pulp.LpVariable('d_cat_muscle_meat_plus', 0)
prob += 0.7 * total_x - 0.7 * total_x == d_plus - d_minus
prob += 0
prob.solve()
names = {v.name for v in prob.variables() if v.name.startswith('d_cat_')}
assert names == {'d_cat_muscle_meat_minus', 'd_cat_muscle_meat_plus'}
print('OK: variable naming + capture-by-prefix convention is stable')
"
# expected exit: 0
```

**Rollback:**

```bash
git checkout -- $PROJECT_ROOT/build_pipeline.py
```

**Anti-patterns to avoid in this task:**
- Do NOT add a `prob` parameter to `build_output_contract` to route around the missing scope — use
  the `raw_result["category_goal_deviations"]` side-channel already established via
  `call_lp_solver`'s return dict
- Do NOT compute `achieved_pct` as `target - d_minus` only — the correct formula is
  `target + (d_plus - d_minus)` (overshoot is positive deviation, shortfall is negative)
- Do NOT remove the `max(0.0, ...)` clamp on `achieved_pct` (a negative achieved value would be
  nonsensical to display)
- Do NOT compute `overall_score` as `100 - count_of_deviating_categories` — it MUST be
  `100 - sum_of_absolute_deviations`
- Do NOT report `achieved_pct == target_pct` (a fabricated perfect match) for a category with no
  ingredients in the pool — mark it `"skipped": True` and exclude it from `total_deviation` instead
- Do NOT assume a mutable `output` dict exists in `build_output_contract` to `.setdefault(...)` onto
  — the real function ends in a single `return {...}` literal; add new keys directly to that
  literal and to the pre-existing `meta` dict that feeds `"solver_metadata": meta`

---

### Task-4: Add 4 new tests to `test_cascade_integration.py` (corrected to match real signatures)

```yaml
task_id: task-4
title: "Add 4 category-goal tests covering Level 1 wiring, influence on solution, Level 2 relaxation, and output contract"
depends_on:
  - task-3
parallel_group: null
files_mutated:
  - $PROJECT_ROOT/tests/test_cascade_integration.py
idempotent: true
estimated_loc: ~140
commit_message: "test(cascade): add 4 category-goal tests (Level 1 wiring, influence, Level 2 slack, output contract)"
severity: blocker
```

**Rationale:** the 4 tests below are the only thing preventing a silent regression in the Compass
layer. Each targets one of the 4 code paths added in Tasks 0–3. **Before writing them, read
`tests/reference_cases.py` and confirm the exact names it exports** — the fixture names used below
(`REFERENCE_SELECTED_IDS`, `REFERENCE_ANIMAL`, `REFERENCE_SCENARIO_ID`) are best-effort based on the
real function signatures in `build_pipeline.py`; adapt them to whatever the fixtures file actually
exposes rather than assuming.

**Preconditions (in addition to plan-level):**
- Task-3 committed (V1–V8 all pass)
- Executor has read `tests/reference_cases.py` and confirmed its exported names

**Steps:**

1. Open `$PROJECT_ROOT/tests/test_cascade_integration.py`.
2. Append the following 4 test functions at the end of the file, using the **real** call chain
   (`load_all_jsons` → `build_matrix` → `calculate_der_and_envelope` → `build_lp_problem` →
   `call_lp_solver`, or `solve_cascade` directly when a full cascade run is needed — never the
   `animal=`/`selection=`/`levels=` keyword arguments from v1.0.0, which do not exist on any real
   function):

   ```python
   # === Category Soft Goals (Option B) — 4 tests ===

   def test_category_goals_in_level1_objective():
       """Verify deviation vars d_cat_<n>_minus/plus are created when Level 1 runs."""
       # Arrange
       import re
       from tests.reference_cases import REFERENCE_SELECTED_IDS, REFERENCE_ANIMAL, REFERENCE_SCENARIO_ID
       from build_pipeline import (
           load_all_jsons, build_matrix, calculate_der_and_envelope,
           build_lp_problem, call_lp_solver,
       )

       data = load_all_jsons()
       db = data["DB_ingredientes.json"]
       fr = data["formulation_rules.json"]
       fr["_db_ref"] = db
       matrix = build_matrix(REFERENCE_SELECTED_IDS, db, fr)
       der_info = calculate_der_and_envelope(
           REFERENCE_ANIMAL, data["growth_energy_skeletal.json"],
           REFERENCE_SCENARIO_ID, REFERENCE_SELECTED_IDS, db,
       )
       problem_dict = build_lp_problem(
           REFERENCE_SELECTED_IDS, matrix, data, der_info, cascade_level=1, db=db,
       )
       lp_params = data["lp_parameters_data.json"]
       level_config = next(l for l in lp_params["solve_cascade"] if l["level"] == 1)

       # Act
       result = call_lp_solver(problem_dict, level_config["objective_stages"], lp_params.get("solver_params", {}))

       # Assert
       assert result["status"] == "feasible"
       var_names = set(result["category_goal_deviations"].keys())
       assert any(v.startswith("d_cat_muscle_meat_minus") for v in var_names), \
           "Expected d_cat_muscle_meat_minus var; category_goal_deviation stage did not run at Level 1"
       assert any(v.startswith("d_cat_muscle_meat_plus") for v in var_names), \
           "Expected d_cat_muscle_meat_plus var; category_goal_deviation stage did not run at Level 1"

       # + Additional: at least 3 of the 7 categories should have deviation vars
       #   (the others may be skipped if REFERENCE_SELECTED_IDS has no ingredients in those
       #   categories). Extract the FULL goal name, not a naive split — "organ_secreting" and
       #   "organ_non_secreting" must not collapse to the same string.
       cats = {
           m.group(1) for v in var_names
           if (m := re.match(r"d_cat_(.+)_(minus|plus)$", v))
       }
       assert len(cats) >= 3, f"Expected >= 3 categories with deviation vars, got {cats}"


   def test_category_goals_influence_solution():
       """Synthetic test: muscle_meat goal (70%) pulls solution toward 70% when pool allows."""
       # Arrange
       from tests.reference_cases import REFERENCE_SELECTED_IDS, REFERENCE_ANIMAL, REFERENCE_SCENARIO_ID
       from build_pipeline import load_all_jsons, solve_cascade

       data = load_all_jsons()

       # Act — solve_cascade always walks Level 1 -> 2 -> 3 internally and returns at the
       # first feasible level; there is no `levels=` kwarg to restrict it.
       # (executor: der_info must be computed the same way as in the previous test, or
       #  solve_cascade must be confirmed to compute it internally — verify against the
       #  real function before assuming either.)
       result = solve_cascade(REFERENCE_SELECTED_IDS, data, der_info, REFERENCE_SCENARIO_ID)

       # Assert
       allocations = result["allocations"] or []
       total = sum(a["grams_per_day"] for a in allocations)
       muscle_amount = sum(
           a["grams_per_day"] for a in allocations
           if a.get("category") in ("muscle_meat", "fish")
       )
       muscle_pct = (muscle_amount / total) * 100 if total > 0 else 0
       assert muscle_pct >= 60.0, \
           f"Muscle allocation {muscle_pct:.1f}% < 60% — category goal is not influencing the solution"

       # + Additional: muscle_pct should NOT exceed 80% — the micro-weight must not dominate
       #   nutrient adequacy and force muscle to a hard 70%
       assert muscle_pct <= 80.0, \
           f"Muscle allocation {muscle_pct:.1f}% > 80% — micro-weight multiplier may have been removed"


   def test_category_goals_relaxed_at_level2():
       """Verify Level 2 still uses category_goal_deviation (compass survives the floor drop)."""
       # Arrange — executor must construct or locate an ingredient pool in reference_cases.py
       # that is known to force a Level 2 drop (Level 1 infeasible on nutrient adequacy).
       # Do NOT assume REFERENCE_SELECTED_IDS does this unless confirmed.
       from tests.reference_cases import REFERENCE_SCENARIO_ID
       from build_pipeline import load_all_jsons, solve_cascade

       data = load_all_jsons()
       level2_pool = None  # executor: substitute the confirmed Level-2-forcing pool

       # Act
       result = solve_cascade(level2_pool, data, der_info, REFERENCE_SCENARIO_ID)

       # Assert
       assert result["cascade_level_used"] >= 2, \
           "Test setup error: expected solver to drop to Level 2, but it stayed at Level 1"

       # + Additional: template_adherence should be populated in the Level 2 result
       assert "template_adherence" in result, \
           "Level 2 result missing template_adherence — output contract not invoked at Level 2"
       assert len(result["template_adherence"]["components"]) > 0, \
           "Level 2 template_adherence has no components — category_goal_deviation stage did not run"


   def test_category_goals_output_contract():
       """Verify output includes template_adherence and solver_metadata.category_goal_deviations_raw."""
       # Arrange
       from tests.reference_cases import REFERENCE_SELECTED_IDS, REFERENCE_SCENARIO_ID
       from build_pipeline import load_all_jsons, solve_cascade

       data = load_all_jsons()

       # Act
       output = solve_cascade(REFERENCE_SELECTED_IDS, data, der_info, REFERENCE_SCENARIO_ID)

       # Assert
       assert "template_adherence" in output, "Output missing template_adherence key"
       assert "components" in output["template_adherence"], \
           "template_adherence missing components sub-key"
       assert "overall_score" in output["template_adherence"], \
           "template_adherence missing overall_score sub-key"
       assert 0 <= output["template_adherence"]["overall_score"] <= 100, \
           f"overall_score {output['template_adherence']['overall_score']} out of [0,100]"

       # + Additional: raw deviations also present under solver_metadata
       assert "solver_metadata" in output, "Output missing solver_metadata"
       assert "category_goal_deviations_raw" in output["solver_metadata"], \
           "solver_metadata missing category_goal_deviations_raw"
       raw = output["solver_metadata"]["category_goal_deviations_raw"]
       assert isinstance(raw, dict), f"category_goal_deviations_raw should be dict, got {type(raw)}"
       assert len(raw) >= 1, "category_goal_deviations_raw should have at least one entry"
   ```

   Note: `der_info` above must be computed the same way `test_category_goals_in_level1_objective`
   does (via `calculate_der_and_envelope`), or `solve_cascade` must be confirmed to accept only
   `(selected_ids, data, der_info, scenario_id)` and needs it precomputed by the caller — resolve
   this against the real function before finalizing these two tests; do not leave `der_info`
   undefined.

3. Verify all 4 tests are collected by pytest:
   ```bash
   python -m pytest tests/test_cascade_integration.py --collect-only -q | grep -c category_goals
   ```
   Expected: 4 matches.

4. Run the 4 new tests:
   ```bash
   python -m pytest tests/test_cascade_integration.py -k category_goals -v
   ```
   Expected: `4 passed`. If any test fails, do NOT patch the test to force pass — investigate the
   root cause in `build_pipeline.py` (Tasks 0–3).

5. Re-run the full suite to confirm no regression against the recorded baseline:
   ```bash
   python -m pytest tests/ -q
   ```
   Expected: `N+4 passed` (where `N` is the P4 baseline).

**State mutations:**

| File | Before | After |
|---|---|---|
| `tests/test_cascade_integration.py` | `N` existing tests, no `category_goals` tests | +4 tests: `test_category_goals_in_level1_objective`, `test_category_goals_influence_solution`, `test_category_goals_relaxed_at_level2`, `test_category_goals_output_contract` |

**Verification (deterministic):**

```bash
# V1: 4 new tests collected
cd $PROJECT_ROOT && python -m pytest tests/test_cascade_integration.py --collect-only -q | grep -c category_goals
# expected: 4

# V2: 4 new tests pass — NOT "4 errors" (a TypeError from a wrong function signature would
# show as an error, not a failure; both are unacceptable, but distinguish them when debugging)
cd $PROJECT_ROOT && python -m pytest tests/test_cascade_integration.py -k category_goals -q
# expected: 4 passed

# V3: none of the new tests call a nonexistent kwarg shape
rg -n "solve_cascade\(.*levels=" $PROJECT_ROOT/tests/test_cascade_integration.py
# expected: 0 matches
rg -n "build_lp_problem\(animal=" $PROJECT_ROOT/tests/test_cascade_integration.py
# expected: 0 matches

# V4: AAA+A pattern enforced (every test has Arrange, Act, Assert, + Additional comments)
rg -c "# Arrange" $PROJECT_ROOT/tests/test_cascade_integration.py
rg -c "# Act" $PROJECT_ROOT/tests/test_cascade_integration.py
rg -c "# Assert" $PROJECT_ROOT/tests/test_cascade_integration.py
rg -c "# \+ Additional" $PROJECT_ROOT/tests/test_cascade_integration.py
# expected: each >= 4

# V5: full suite still green (N+4 total)
cd $PROJECT_ROOT && python -m pytest tests/ -q
# expected: N+4 passed
```

**Rollback:**

```bash
git checkout -- $PROJECT_ROOT/tests/test_cascade_integration.py
```

**Anti-patterns to avoid in this task:**
- Do NOT patch a failing test to force pass — if `test_category_goals_influence_solution` fails,
  the bug is in `build_pipeline.py` (most likely the micro-weight multiplier or the `problem_dict`
  side-channel from Task-2), NOT in the test
- Do NOT skip the `+ Additional` assertion in any test
- Do NOT use `pytest.mark.skip` or `pytest.mark.xfail` on any of these 4 tests
- Do NOT depend on a specific numeric allocation value — use a tolerance band
  (`60% <= muscle_pct <= 80%`)
- Do NOT write tests that mock the LP solver — exercise the real PuLP solver against real config
- Do NOT extract category names from a variable name via naive `str.split("_")` positional
  indexing — `d_cat_organ_secreting_minus` and `d_cat_organ_non_secreting_minus` both start with
  `organ` and will collapse to the same string under `.split("_")[2]`; use the anchored regex
  `r"d_cat_(.+)_(minus|plus)$"` shown above instead
- Do NOT assume `build_lp_problem` takes `animal=`/`selection=`/`scenario_id=` keywords, or that
  `solve_cascade` takes a `levels=` kwarg — neither exists; use the real signatures shown above

---

### Task-5: Update documentation

```yaml
task_id: task-5
title: "Document category_goal_deviation objective kind, the problem_dict/raw_result data flow, and template_adherence output field"
depends_on:
  - task-4
parallel_group: null
files_mutated:
  - $PROJECT_ROOT/docs/sat_solver_contrato.md
  - $PROJECT_ROOT/docs/sat_pipeline_codigo.md
  - $PROJECT_ROOT/docs/indice_plano_central.md
idempotent: true
estimated_loc: ~55
commit_message: "docs: document category_goal_deviation objective kind and template_adherence output field"
severity: low
```

**Rationale:** Tasks 0–4 added a bug fix, a new objective kind, a new data-flow side-channel, a new
output field, and a new config block — none of which are documented. Without this task, the next
agent (or human) reading the docs will not know `category_goal_deviation` exists, will not
understand why it reads from `problem_dict` instead of `lp_params` directly, and will not be able to
extend or debug the Compass layer.

**Preconditions (in addition to plan-level):**
- Task-4 committed (4 new tests pass)

**Steps:**

1. **`$PROJECT_ROOT/docs/sat_solver_contrato.md`** — locate the "Output Contract" section via
   `rg -n "## Output Contract" docs/sat_solver_contrato.md`. Add a new subsection:
   ```markdown
   ### `template_adherence` (NEW — Option B category soft goals)

   User-facing summary of how closely the solution matches the BARF/PMR template.

   | Field | Type | Description |
   |---|---|---|
   | `components` | `dict[str, {target_pct, achieved_pct, absolute_deviation_pct, skipped}]` | Per-category breakdown. `skipped: true` means the category had zero ingredients in the user's pool — no deviation was computed, and it is excluded from `overall_score`. |
   | `overall_score` | `float` in `[0, 100]` | 100 = perfect template match, 0 = maximally deviating, over non-skipped categories only. |

   Raw per-category deviation values are also available under
   `solver_metadata.category_goal_deviations_raw` for audit / debugging.
   ```
2. **`$PROJECT_ROOT/docs/sat_pipeline_codigo.md`** — locate the "Objective Kinds" section via
   `rg -n "## Objective Kinds" docs/sat_pipeline_codigo.md`. Add:
   ```markdown
   ### `category_goal_deviation` (NEW — Option B)

   Adds penalized deviation variables `d_cat_<n>_minus` / `d_cat_<n>_plus`
   for each category goal in `lp_parameters_data.json:solve_cascade[level].category_goals`.

   **Data flow (important — do not re-derive this differently):**
   `_build_stage_objective` has no `lp_params`/`cascade_level` parameter, so it cannot look up
   `category_goals` itself. `build_lp_problem` stashes it onto `problem_dict["category_goals"]`
   right after computing `level_config`; `_build_stage_objective` reads it from there. Likewise,
   `build_output_contract` has no `prob` parameter, so the solved `d_cat_*` values are captured
   inside `call_lp_solver` (which does hold `prob`) into `category_goal_deviations`, returned
   alongside `x_values`/`nutrient_values`, and read back in `build_output_contract` via
   `raw_result.get("category_goal_deviations", {})`.

   **Mechanism:**
   - For each goal with at least one matching ingredient in the pool, creates `d_minus`,
     `d_plus >= 0` continuous variables
   - Adds equality constraint: `cat_sum - (target_pct * total_x) == d_plus - d_minus`
   - Adds to objective: `(d_minus + d_plus) * base_weight * 0.01`
   - A goal with zero matching ingredients gets no variables and is marked `skipped: true`
     downstream, never a fabricated 0-deviation match

   **Micro-weight multiplier (`* 0.01`):** mandatory. Without it, category goals
   (~440 total weight) would rival nutrient deviation (~410) and could pull the
   solution away from clinically-required nutrient targets. With it, effective
   weight is 0.3–1.0 per category (~4.4 total) — strictly a tie-breaker.

   **Where it runs:** Level 1 stage 2 (`fix_optimum: false`) and Level 2 stage 2
   (`fix_optimum: false`). NOT at Level 3 (diagnostic-only).
   ```
3. **`$PROJECT_ROOT/docs/indice_plano_central.md`** — locate the changelog section via
   `rg -n "## Changelog" docs/indice_plano_central.md`. Add a new entry at the top:
   ```markdown
   - **2026-07-18** — Plan `plan-gsd-category-soft-goals` v2.0.0 merged. Fixed a
     pre-existing `UnboundLocalError` crash in `build_lp_problem` (unrelated to this
     feature). Added Option B category soft goals: 7 `category_goals` entries in
     `lp_parameters_data.json`, new `category_goal_deviation` objective kind in
     `build_pipeline.py` (wired via `problem_dict`/`raw_result` side-channels, not by
     widening existing function signatures), `template_adherence` +
     `category_goal_deviations_raw` in the output contract, 4 new tests in
     `test_cascade_integration.py`. Micro-weight multiplier `* 0.01` enforces the
     Wall-vs-Compass architecture. `N+4` tests passing.
   ```
4. Verify no other documentation file references `category_goals` or `template_adherence`:
   ```bash
   rg -l "category_goal_deviation|template_adherence" $PROJECT_ROOT/docs/
   ```
   Expected: exactly 3 files (the ones just edited).

**State mutations:**

| File | Before | After |
|---|---|---|
| `docs/sat_solver_contrato.md` | No `template_adherence` section | New subsection documenting `components`, `skipped`, and `overall_score` |
| `docs/sat_pipeline_codigo.md` | No `category_goal_deviation` section | New subsection documenting mechanism, the `problem_dict`/`raw_result` data flow, and the micro-weight multiplier |
| `docs/indice_plano_central.md` | Changelog does not mention this plan | New changelog entry at top |

**Verification (deterministic):**

```bash
# V1: template_adherence documented in output contract
rg -c "template_adherence" $PROJECT_ROOT/docs/sat_solver_contrato.md
# expected: >= 3

# V2: category_goal_deviation documented in pipeline code docs
rg -c "category_goal_deviation" $PROJECT_ROOT/docs/sat_pipeline_codigo.md
# expected: >= 2

# V3: micro-weight multiplier documented (with the 0.01 value)
rg -c "0\.01" $PROJECT_ROOT/docs/sat_pipeline_codigo.md
# expected: >= 2

# V4: changelog entry added
rg -c "plan-gsd-category-soft-goals" $PROJECT_ROOT/docs/indice_plano_central.md
# expected: >= 1

# V5: only 3 docs files mention the new identifiers
rg -l "category_goal_deviation|template_adherence" $PROJECT_ROOT/docs/ | wc -l
# expected: 3

# V6: full test baseline still green (docs changes must not break anything)
cd $PROJECT_ROOT && python -m pytest tests/ -q
# expected: N+4 passed
```

**Rollback:**

```bash
git checkout -- $PROJECT_ROOT/docs/sat_solver_contrato.md $PROJECT_ROOT/docs/sat_pipeline_codigo.md $PROJECT_ROOT/docs/indice_plano_central.md
```

**Anti-patterns to avoid in this task:**
- Do NOT document `category_goal_deviation` as a hard constraint
- Do NOT omit the `* 0.01` multiplier from the docs
- Do NOT mention Level 3 — `category_goal_deviation` does NOT run at Level 3
- Do NOT update any other docs file (only the 3 listed)
- Do NOT omit the `problem_dict`/`raw_result` data-flow note — this is the exact thing that broke
  in v1.0.0 and will break again for the next person who "simplifies" it by re-deriving
  `category_goals` or `prob` locally instead of reading the side-channel

---

### Task-6: Final validation, regression, and merge gate

```yaml
task_id: task-6
title: "Run full acceptance criteria, MAPA regeneration, and confirm clean git state"
depends_on:
  - task-5
parallel_group: null
files_mutated:
  - $PROJECT_ROOT/MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md   # regenerated by --generate-mapa
idempotent: true
estimated_loc: 0   # verification only
commit_message: "chore(validation): regenerate MAPA and confirm clean tree post category-soft-goals"
severity: blocker
```

**Rationale:** this task is the gate. Every acceptance criterion (Q0–Q10) must be checked here, in
one shot, before the branch is considered mergeable.

**Preconditions (in addition to plan-level):**
- Task-5 committed (docs updated)

**Steps:**

1. **Run the full pytest suite** — confirm `N+4` tests pass:
   ```bash
   cd $PROJECT_ROOT && python -m pytest tests/ -q
   ```
   Expected: `N+4 passed`, where `N` is the baseline recorded at P4. If fewer, do NOT proceed —
   investigate which test regressed.

2. **Run `--gate-mapa`**:
   ```bash
   cd $PROJECT_ROOT && python build_pipeline.py --gate-mapa
   ```
   Expected: exit 0.

3. **Run the synthetic influence test in isolation:**
   ```bash
   cd $PROJECT_ROOT && python -m pytest tests/test_cascade_integration.py::test_category_goals_influence_solution -v
   ```
   Expected: `1 passed`.

4. **Confirm Level 3 liver-only safety wall still triggers:**
   ```bash
   cd $PROJECT_ROOT && python -m pytest tests/test_cascade_integration.py -k liver -v
   ```
   Expected: existing test still passes. If it fails, the Compass has somehow weakened the
   liver-only hard wall — investigate immediately (clinical-safety regression).

5. **Regenerate MAPA:**
   ```bash
   cd $PROJECT_ROOT && python build_pipeline.py --generate-mapa --out MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md
   rg -c "SOURCE: IMPLEMENTATION_SPEC" $PROJECT_ROOT/MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md
   ```
   Expected: `>= 10`.

6. **Confirm no hard constraints were introduced on `cat_sum`** (corrected check — the naive
   substring check in v1.0.0 would always match the required equality line and falsely fail):
   ```bash
   rg -n "cat_sum.*(<=|>=)" $PROJECT_ROOT/build_pipeline.py
   # expected: 0 matches
   rg -n "cat_sum - \(target_pct \* total_x\) == d_plus - d_minus" $PROJECT_ROOT/build_pipeline.py
   # expected: 1 match
   ```

7. **Confirm clean working tree** (after committing the regenerated MAPA):
   ```bash
   cd $PROJECT_ROOT && git status --short
   ```
   Expected: empty.

8. **Commit the regenerated MAPA** (only if step 5 changed it):
   ```bash
   cd $PROJECT_ROOT && git add MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md && git commit -m "chore(mapa): regenerate with category-soft-goals config"
   ```

**State mutations:**

| File | Before | After |
|---|---|---|
| `MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md` | Pre-Option-B MAPA | Regenerated MAPA including `template_adherence` in live-evidence section |

**Verification (deterministic):**

```bash
# V1: Q0 — N baseline tests pass
cd $PROJECT_ROOT && python -m pytest tests/ -q -k "not category_goals"
# expected: N passed

# V2: Q1 — 4 new tests pass
cd $PROJECT_ROOT && python -m pytest tests/test_cascade_integration.py -k category_goals -q
# expected: 4 passed

# V3: Q2 — --gate-mapa passes
cd $PROJECT_ROOT && python build_pipeline.py --gate-mapa
# expected exit: 0

# V4: Q3 — synthetic test pulls muscle toward 70%
cd $PROJECT_ROOT && python -m pytest tests/test_cascade_integration.py::test_category_goals_influence_solution -q
# expected: 1 passed

# V5: Q4 — Level 3 liver-only safety still triggers
cd $PROJECT_ROOT && python -m pytest tests/test_cascade_integration.py -k liver -q
# expected: existing test passes

# V6: Q5 — no hard constraints introduced (corrected regex — see step 6 above)
rg -n "cat_sum.*(<=|>=)" $PROJECT_ROOT/build_pipeline.py
# expected: 0 matches

# V7: Q6 — MAPA regenerated with provenance markers
rg -c "SOURCE: IMPLEMENTATION_SPEC" $PROJECT_ROOT/MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md
# expected: >= 10

# V8: Q7 — output contract includes both new keys (executor: adapt fixtures to real
# tests/reference_cases.py names, confirmed in Task-4)
python -c "
from tests.reference_cases import REFERENCE_SELECTED_IDS, REFERENCE_SCENARIO_ID
from build_pipeline import load_all_jsons, solve_cascade
data = load_all_jsons()
# der_info must be constructed the same way Task-4's tests do — see that task's note
output = solve_cascade(REFERENCE_SELECTED_IDS, data, der_info, REFERENCE_SCENARIO_ID)
assert 'template_adherence' in output
assert 'category_goal_deviations_raw' in output.get('solver_metadata', {})
print('OK: Q7 satisfied')
"
# expected exit: 0

# V9: Q8 — clean git tree
cd $PROJECT_ROOT && git status --short
# expected: empty

# V10: Q9 — build_lp_problem still crash-free (Task-0a's fixes held through all subsequent edits).
# This re-runs the SAME live solve as Task-0a's V4 — a textual check alone (as in v2.0.0) would
# not have re-detected a regression that reintroduced the targets_per_day bug.
python -c "
import build_pipeline as bp
data = bp.load_all_jsons()
db = data['DB_ingredientes.json']
fr = data['formulation_rules.json']
fr['_db_ref'] = db
selected = ['beef_muscle_raw', 'chicken_back_raw', 'beef_liver_raw', 'beef_kidney_raw', 'salmon_atlantic_raw']
matrix = bp.build_matrix(selected, db, fr)
animal = bp.AnimalInput(sex='male', weight_kg=25.0, age_months=8, gonadal_status='intact', use_gompertz=True)
der = bp.calculate_der_and_envelope(animal, data['growth_energy_skeletal.json'], 'SCN_B_SLOW_GROWTH', selected, db)
problem = bp.build_lp_problem(selected, matrix, data, der, cascade_level=1, db=db)
assert problem.get('status') != 'infeasible', f\"build_lp_problem regressed: {problem}\"
assert problem.get('targets_per_day'), 'targets_per_day regressed to empty/missing'
print('OK: Q9 satisfied')
"
# expected exit: 0

# V11: Q10 — Ca:P ratio and DER proximity still wired in (Task-0b's fixes held through all
# subsequent edits)
rg -c "add_der_proximity\(\)" $PROJECT_ROOT/build_pipeline.py
# expected: 2
rg -c "add_ca_p_ratio\(\)" $PROJECT_ROOT/build_pipeline.py
# expected: 2
python -c "
import build_pipeline as bp
data = bp.load_all_jsons()
db = data['DB_ingredientes.json']
fr = data['formulation_rules.json']
fr['_db_ref'] = db
lp_params = data['lp_parameters_data.json']
selected = ['beef_muscle_raw', 'chicken_back_raw', 'beef_liver_raw', 'beef_kidney_raw', 'salmon_atlantic_raw']
matrix = bp.build_matrix(selected, db, fr)
animal = bp.AnimalInput(sex='male', weight_kg=25.0, age_months=8, gonadal_status='intact', use_gompertz=True)
der = bp.calculate_der_and_envelope(animal, data['growth_energy_skeletal.json'], 'SCN_B_SLOW_GROWTH', selected, db)
problem = bp.build_lp_problem(selected, matrix, data, der, cascade_level=1, db=db)
level_config = next(l for l in lp_params['solve_cascade'] if l['level'] == 1)
result = bp.call_lp_solver(problem, level_config['objective_stages'], lp_params.get('solver_params', {}))
assert result['status'] == 'feasible', f\"solve failed: {result}\"
ca = result['nutrient_values'].get('calcium_g', 0)
p = result['nutrient_values'].get('phosphorus_g', 0)
assert p > 0
ratio = ca / p
assert 1.1 - 1e-6 <= ratio <= 1.3 + 1e-6, f\"Ca:P ratio {ratio:.3f} regressed outside [1.1, 1.3]\"
print('OK: Q10 satisfied')
"
# expected exit: 0
```

**Rollback:**

```bash
git revert <task-0a-sha>..<task-6-sha>   # sequential revert of all 9 commits
```

**Anti-patterns to avoid in this task:**
- Do NOT skip step 4 (liver-only safety check) even under time pressure — this is the one check
  that would catch a Compass-becomes-Wall regression
- Do NOT accept a `0 matches` result on the old-style `rg "prob \+= .*cat_sum"` check as evidence of
  correctness — that check is retired; use the two-part check in step 6 instead

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Category goals override nutrient adequacy (Compass becomes Wall) | Low | Critical | Micro-weight `* 0.01` caps effective weight at 0.3–1.0 per category; antagonism slack penalty (5000) dwarfs total category weight (~4.4 effective) |
| Level 1 purity breached (adequacy slack leaks into Level 1) | Low | High | `fix_optimum: false` on `category_preferences` stage; verified by Task-1 V2 |
| Level 3 liver-only safety wall weakened | Very Low | Critical | `CSTR_INCL_MAX_LIVER <= 5%` hard constraint untouched; verified by Task-6 V5 |
| `build_lp_problem` crashes on `problem_dict` referenced before assignment, independent of this feature | Confirmed present | Critical | Task-0a fixes it, as part of a standalone, bisectable commit, before any category-goals code is added |
| **(new)** `build_lp_problem` crashes a SECOND, independent way — `targets_per_day` is read but never assigned anywhere in the function (missed by v2.0.0 entirely) | Confirmed present | Critical | Task-0a restores the computation as part of the same commit; verified by a live end-to-end solve (V4), not a textual check, since v2.0.0's textual checks could not see this |
| **(new)** `add_der_proximity()` / `add_ca_p_ratio()` fully implemented but never called — Ca:P ratio (a documented Wall invariant) is not actually enforced, and DER-proximity silently no-ops | Confirmed present | Critical | Task-0b wires both in as its own commit, verified by a live solve that checks the resulting Ca:P ratio and the presence of real `der_dev_vars` (not the fallback path) |
| **(new, Task-0c)** `build_lp_problem` silently overwrites caller's `db` parameter with the full DB — any test passing a filtered DB gets the full 23-ingredient DB instead | Confirmed present | High | Task-0c removes the unconditional overwrite and adds a `db` parameter; verified by `rg` returning exactly 1 match and live solve passing with explicit `db=` |
| **(new, Task-0d)** Two complete `compute_gaps` definitions exist in the file — first one is dead (never called), only the second is live | Confirmed present | Low (cosmetic but misleading for debugging) | Task-0d deletes the dead first copy and its 4 orphaned helpers; verified by `rg` returning exactly 1 match |
| **(new)** A second bug can hide behind a first one and go undetected by textual/`rg`-only verification or a stale relative pytest baseline | Confirmed occurred once already (v2.0.0 missed the `targets_per_day` bug this way) | High | P11 and Task-0a/Task-0b's own verification now require a live, real execution of `build_lp_problem`/`call_lp_solver`, not just `import` success or an `rg` match |
| **(new)** `_build_stage_objective` cannot access `lp_params`/`cascade_level` | Confirmed present in v1.0.0's design | High | Task-2 routes `category_goals` through `problem_dict` instead, matching the existing pattern for every other stage kind |
| **(new)** `build_output_contract` cannot access `prob` | Confirmed present in v1.0.0's design | High | Task-3 threads deviation values through `call_lp_solver`'s return dict instead |
| **(new)** Test helper signatures don't match real functions | Confirmed present in v1.0.0's design | High | Task-4 rewritten against the real `build_lp_problem`/`solve_cascade`/`call_lp_solver` signatures; executor must additionally confirm `tests/reference_cases.py`'s actual exports before finalizing |
| Category lookup failure (`get_ingredient_by_id` returns None) | Low | Medium | Defensive: `if not cat_ingredients: continue` skips the category silently instead of crashing |
| Cascade order regression (Level 1 → 2 → 3 descent broken) | Low | High | Task-6 V5 (liver-only test) + baseline test suite; any cascade reordering would break existing tests |
| Output contract change breaks downstream consumers | Low | Medium | Non-breaking: only NEW fields added (`template_adherence`, `category_goal_deviations_raw`); existing fields unchanged |
| MAPA regeneration drops provenance markers | Low | High | Task-6 V7 must return `>= 10` |
| Test author hard-codes a specific allocation percentage | Medium | Medium | Anti-pattern explicitly listed in Task-4; tolerance band `60% <= muscle_pct <= 80%` is mandatory |
| Category name string-splitting collapses distinct categories | Confirmed present in v1.0.0's design | Medium | Task-4 uses an anchored regex (`d_cat_(.+)_(minus|plus)$`) instead of positional `str.split("_")` |
| Enforcing Ca:P ratio for real (Task-0b) makes some previously-"working" ingredient pools infeasible at Level 1 | Medium | Medium | Expected and correct — those pools were silently violating Ca:P ratio before; Level 2/3 relaxation still applies. Flag to the user if the P4 baseline test count drops after Task-0b so they can confirm this is intentional, not a regression |

---

## Acceptance Criteria (mapped to postconditions and tasks)

- [ ] Q0 — All `N` baseline tests pass (Task-6 V1)
- [ ] Q1 — 4 new category-goal tests pass (Task-6 V2)
- [ ] Q2 — `--gate-mapa` passes (Task-6 V3)
- [ ] Q3 — Synthetic test: `muscle_meat` goal pulls solution toward 70% (Task-6 V4)
- [ ] Q4 — Level 3 still returns `unsafe_diagnostic` for liver-only (Task-6 V5)
- [ ] Q5 — No new hard constraints introduced (Task-6 V6)
- [ ] Q6 — MAPA regeneration clean (Task-6 V7)
- [ ] Q7 — Output contract includes `template_adherence` and `category_goal_deviations_raw` (Task-6 V8)
- [ ] Q8 — Clean git working tree after final commit (Task-6 V9)
- [ ] Q9 — `build_lp_problem` remains crash-free, incl. `targets_per_day` (Task-6 V10)
- [ ] Q10 — Ca:P ratio and DER proximity remain wired in and enforced (Task-6 V11)

---

## Timeline

| Phase | Duration |
|---|---|
| Task-0a: fix both pre-existing `build_lp_problem` crashes (`problem_dict` ordering + missing `targets_per_day`) | 30–45 min |
| Task-0b: wire `add_der_proximity()` / `add_ca_p_ratio()` into constraint assembly | 20–30 min |
| **Task-0c: remove unconditional `db` overwrite in `build_lp_problem` — add `db` parameter** | **10–15 min** |
| **Task-0d: delete dead first `compute_gaps` (and its 4 orphaned helpers)** | **5–10 min** |
| Task-1: `lp_parameters_data.json` config | 15 min |
| Task-2: `category_goal_deviation` objective kind (via `problem_dict`) | 1–1.5 hours |
| Task-3: `template_adherence` output contract (via `raw_result` threading) | 1 hour |
| Task-4: 4 new tests (AAA+A, against real signatures — includes reading `reference_cases.py`) | 1–1.5 hours |
| Task-5: Documentation | 30 min |
| Task-6: Final validation + MAPA regeneration | 30 min |
| **Total** | **~6–7.5 hours** |

---

## Approval

**Approved by**: User
**Implementation start**: Upon confirmation
**Rollback plan**: `git revert <task-0a-sha>..<task-6-sha>` (sequential revert of all 11 commits)

---

## Decisions & Resolutions

### 1. Normalization: REJECT Dynamic Normalization (Keep Absolute Targets)

**Decision:** Keep absolute targets (e.g., 70% muscle, 10% organ_secreting). Do NOT normalize
against the sum of active categories.

**Why:** BARF/PMR ratios are absolute biological ideals, not relative proportions of whatever is in
the bowl. If a user omits bone, muscle should NOT mathematically inflate to 77% just to force the
sum to 100%.

**How the math handles it:** `d_plus`/`d_minus` naturally absorb the slack. Targets sum to 110%; the
`d_plus` variables absorb the 10% overshoot. A missing category triggers Task-2's
`if not cat_ingredients: continue` guard — no `d_minus` variable is created, no penalty is incurred,
and Task-3's guard reports it as `skipped: true` rather than a fabricated match.

### 2. Level 1 Stages: CONFIRM Level 1 Purity

**Decision:** Level 1 remains the "Strict Adequacy & Safety" wall. Adequacy slack stays at Level 2.
`category_goal_deviation` is Level 1 stage 2, `fix_optimum: false`.

**Corrected Level 1 Cascade:**
1. `goal_deviation` (Nutrient targets + Antagonism penalties) → `fix_optimum: true`
2. `category_goal_deviation` (BARF/PMR preferences) → `fix_optimum: false`
3. `minimize_absolute_der_deviation` (Hit caloric envelope) → `fix_optimum: true`

### 3. Level 2 Integration: CONFIRM Category Goals at Level 2

**Decision:** `category_goal_deviation` MUST also exist at Level 2 (stage 2, same position as
Level 1), byte-identical `category_goals` block.

**Why:** if the solver drops to Level 2, it still needs a "compass" toward the closest BARF/PMR
approximation, even while relaxing nutrient adequacy floors.

### 4. Output Field Name: `template_adherence` (User) + `category_goal_deviations_raw` (Audit)

**Decision:** `template_adherence` is the clean, user-facing summary. The raw
`category_goal_deviations_raw` dict lives inside `solver_metadata` for auditability.

**Implementation (corrected in v2.0.0):** both fields are populated from the same
`template_adherence["components"]` object inside `build_output_contract`'s final `return {...}`
literal — `output["template_adherence"] = template_adherence` and
`meta["category_goal_deviations_raw"] = template_adherence["components"]` are set immediately
before that return, using values read from `raw_result["category_goal_deviations"]` (populated by
`call_lp_solver`, not from a `prob` object `build_output_contract` never receives).

### 5. Liver/Organ Edge Case: NO CODE CHANGE NEEDED

**Decision:** no special-case code is needed. The existing hard wall
(`CSTR_INCL_MAX_LIVER <= 5%`) and the new soft goal (`organ_secreting = 10%`) interact correctly
without intervention.

**Why:** a liver-only selection is blocked at 5% by the hard wall; the soft goal incurs a 5%
`d_minus` penalty (shortfall below the 10% target); `template_adherence` correctly reflects a 5%
deviation for that category. The Wall enforces clinical safety, the Compass reports the deviation,
neither needs to know about the other.

**Verification:** Task-6 step 4 / V5 confirms the existing liver-only test still passes.

### 6. **(new)** Data-Flow Corrections: Why v1.0.0's Task-2/Task-3 Couldn't Work

**Decision:** `category_goals` is threaded through `problem_dict` (set in `build_lp_problem`, read
in `_build_stage_objective`); category-goal deviation values are threaded through `raw_result` (set
in `call_lp_solver`, read in `build_output_contract`).

**Why:** `_build_stage_objective(prob, x_vars, compiled_coeffs, suls_per_day, targets_per_day, kind,
em_per_g, problem_dict)` has no `lp_params`/`cascade_level` parameter — it cannot look up
`level_config` itself. `build_output_contract(raw_result, level_config, data, der_info,
cascade_attempts)` has no `prob` parameter — it cannot call `.variablesMap()`. Both gaps mean the
"obvious" approach (re-derive `level_config` inline; read `prob` directly) simply doesn't compile
against the real functions. The existing codebase already solves this exact problem for every other
stage kind — `nutrient_slack_vars`, `sul_slack_vars`, `der_dev_vars` all travel via `problem_dict`
into the objective builder, and `nutrient_slack_vars` / `der_dev_vars` / `clinical_floor_bounds` all
travel via `call_lp_solver`'s return dict into `build_output_contract`. This plan follows that same
convention rather than introducing a new one.

### 7. **(new)** Pre-existing Crashes: Why Task-0a Exists

**Decision:** delete the duplicate, premature `category_to_ingredients` precompute block in
`build_lp_problem`, AND restore the missing `targets_per_day` computation, before doing anything
else — both in the same commit.

**Why (Bug 1 — `problem_dict` ordering):** the live codebase already contains a partial, broken
attempt at this plan's Task-2 step — likely from an earlier agent following v1.0.0's Task-2 step 1
literally ("immediately after the block that compiles `valid_selected_ids`"), which in the real
function body is *before* `problem_dict` is assigned. That instruction is corrected in this version:
the precompute must be inserted after `problem_dict = {...}` and after `level_config` is computed,
matching where the second (correct) copy already sits in the live file.

**Why (Bug 2 — missing `targets_per_day`, found in v2.1.0's critical review):** the same incomplete
earlier edit almost certainly deleted a step that used to populate `targets_per_day` from
`constraints.json`'s nutrient minimums — the function's own comment numbering (`4` → `6`, no `5`) is
the evidence. This is not the same bug as #1 and is not fixed by fixing #1; it sits one statement
later in the exact same dict literal. v2.0.0 missed it because its Task-0 verification never actually
executed `build_lp_problem` — it checked source-text ordering (`inspect.getsource`) and a pytest
pass-count that stays numerically stable even when the underlying function still throws, as long as
the affected tests were already excluded from the recorded baseline. Task-0a fixes both bugs in one
commit (both are "the function throws before doing anything" failures) and verifies with a live
solve (V4), not a textual check.

### 8. **(new)** Dead Safety-Constraint Functions: Why Task-0b Exists

**Decision:** call `add_der_proximity()` and `add_ca_p_ratio()` in `build_lp_problem`'s
constraint-assembly block, as their own commit, separate from Task-0a.

**Why:** both functions are fully implemented but never invoked — the "Assemble constraints" block
calls five of the seven helpers defined above it. This means the Ca:P ratio hard constraint, which
this plan's own Wall-vs-Compass table documents as an enforced Wall invariant, is not currently
enforced; and the `minimize_absolute_der_deviation` objective stage always falls into its
"shouldn't happen" fallback path, creating unconstrained dummy variables instead of real DER
proximity. Both are pre-existing, safety-relevant, and unrelated to category goals — for a
large-breed puppy skeletal-development tool, an unenforced Ca:P ratio is arguably the highest-stakes
finding in this whole review, independent of anything this plan otherwise does. It is kept as a
separate commit from Task-0a because it is a silent-failure fix rather than a crash fix, and because
enforcing Ca:P ratio for real may turn some previously-"feasible" ingredient pools infeasible at
Level 1 (correctly — they were silently violating the ratio before) — a distinct, potentially
worth-flagging-to-the-user outcome from "the pipeline no longer crashes," and one an executor or
reviewer may want to bisect independently.

### 9. **(new)** Silent `db` Overwrite: Why Task-0c Exists

**Decision:** delete the unconditional `db = data.get("DB_ingredientes.json", {})` assignment inside
`build_lp_problem`'s Compile-coefficients block (line ~2332 at HEAD), and add a `db` parameter to
`build_lp_problem`'s signature with a fallback `if db is None: db = data.get(...)` path. Update
the caller in `solve_cascade` to pass `db=data.get("DB_ingredientes.json", {})`.

**Why:** `build_lp_problem` already receives `data` (the full 9-JSON dict) and `db` is always
available from `data["DB_ingredientes.json"]` — so the parameter might look redundant. But inside
the function body, a *second* unconditional `db = data.get("DB_ingredientes.json", {})` sat
inside the Compile-coefficients block, overwriting any `db` the caller passed. Any caller that
passed a modified/filtered `db` (e.g., a test that passes a synthetic ingredient set, or the
build-recipes mode that works with subset DBs) would have its `db` silently replaced by the full
DB. This means:
- A test that passes a controlled 3-ingredient DB cannot validate that `build_lp_problem`
  respects its input — the real 23-ingredient DB is always used internally regardless.
- The `db` parameter in the signature is *declaratively* correct but *operationally* dead —
  a deceptive API that any future reader would trust incorrectly.

Fix: remove the unconditional overwrite, keep the documented `db` parameter, and update the only
production caller to pass `db` explicitly.

**Verification:** `rg -n "db = data.get" $PROJECT_ROOT/build_pipeline.py` returns exactly 1
match (the signature's fallback guard), not 2. And `python -c "import build_pipeline as bp;
data = bp.load_all_jsons(); db = data['DB_ingredientes.json']; sel = ['beef_muscle_raw']; ...
bp.build_lp_problem(sel, ... db=db)"` passes without silently using the full DB.

### 10. **(new)** Dead `compute_gaps` Duplicate: Why Task-0d Exists

**Decision:** delete the first (dead) `compute_gaps` definition (lines ~3066–3154 at HEAD) plus
its 4 orphaned helper functions `_map_nutrient_to_category`, `_top_ingredients_for_nutrient`,
`_map_antagonism_to_category`, `_top_ingredients_for_antagonism` (lines ~3157–3216). Only the
second `compute_gaps` (line ~3219+) survives.

**Why:** `build_pipeline.py` contains two complete definitions of `compute_gaps`, separated by
~50 lines of empty space. The first definition (lines ~3066–3154) is **never called** — every
call site in `solve_cascade`/`build_output_contract` reaches the second definition (line ~3219+).
The first definition is dead code: it sits above the second, Python's module-level scope means
the second definition replaces the first at import time, and no internal recursion or
forward-reference pattern targets it. This appears to be a merge artifact where an earlier
refactoring added a new `compute_gaps` at the bottom of the file without removing the old one.

Leaving dead code in the file is not just a cosmetic issue — it creates misleading search results
(`rg` returns 2 definitions, confusing debugging), wastes context budget, and risks that a future
edit accidentally targets the wrong copy. The four orphaned helpers are dependencies of the dead
copy and are dead by association.

**Verification:** `rg -n "def compute_gaps\b" $PROJECT_ROOT/build_pipeline.py` returns exactly 1
match, and tests pass (32/32).

### 11. **(new)** Verification Methodology: Why P11 and the Live-Solve Checks Exist

**Decision:** add P11 (a live, real execution of `build_lp_problem`) to plan-level preconditions, and
require the same live-solve pattern in Task-0a's and Task-0b's own verification, rather than relying
on `import` success, `rg`/`inspect.getsource` text matching, or a relative pytest pass-count alone.

**Why:** v2.0.0's Task-0 fixed a real bug and its verification (V1–V3) all passed — yet the fix was
incomplete, because none of those checks ever executed `build_lp_problem` far enough to reach the
second bug. A relative baseline count (`N passed`, `not category_goals`) is especially easy to
satisfy vacuously: if the affected tests were already failing (and thus already excluded from `N`)
before the fix, they can keep failing after an incomplete fix without moving `N` at all. This is a
general lesson, not specific to this plan: for any task whose job is "make a previously-crashing
function work," the verification must include at least one live call to that function asserting a
successful (non-exception, non-`infeasible`) result — a textual or import-only check cannot
distinguish "fixed" from "differently broken."

---

## Implementation Blueprint

### A. Corrected `lp_parameters_data.json`

```json
{
  "solve_cascade": [
    {
      "level": 1,
      "description": "Strict nutrient adequacy, safety walls, and BARF/PMR preferences",
      "relax_tiers": [],
      "objective_stages": [
        {
          "name": "minimize_nutrient_and_antagonism_deviation",
          "kind": "goal_deviation",
          "fix_optimum": true
        },
        {
          "name": "category_preferences",
          "kind": "category_goal_deviation",
          "fix_optimum": false
        },
        {
          "name": "minimize_absolute_der_deviation",
          "kind": "minimize_absolute_der_deviation",
          "fix_optimum": true
        }
      ],
      "category_goals": {
        "muscle_meat":         {"target_pct": 70, "weight": 100, "categories": ["muscle_meat", "fish"]},
        "organ_secreting":     {"target_pct": 10, "weight": 80,  "categories": ["organ_secreting"]},
        "organ_non_secreting": {"target_pct": 5,  "weight": 40,  "categories": ["organ_non_secreting"]},
        "muscle_organ":        {"target_pct": 5,  "weight": 40,  "categories": ["muscle_organ"]},
        "connective_tissue":   {"target_pct": 5,  "weight": 30,  "categories": ["connective_tissue"]},
        "blood_source":        {"target_pct": 3,  "weight": 30,  "categories": ["blood_source"]},
        "fat_source":          {"target_pct": 12, "weight": 60,  "categories": ["fat_source"]}
      },
      "result_status": "optimal"
    },
    {
      "level": 2,
      "description": "Relax adequacy floors, maintain category preferences and DER proximity",
      "relax_tiers": ["adequacy_soft", "envelope_soft"],
      "objective_stages": [
        {
          "name": "minimize_adequacy_slack",
          "kind": "weighted_normalized_slack",
          "fix_optimum": true
        },
        {
          "name": "category_preferences",
          "kind": "category_goal_deviation",
          "fix_optimum": false
        },
        {
          "name": "minimize_absolute_der_deviation",
          "kind": "minimize_absolute_der_deviation",
          "fix_optimum": true
        }
      ],
      "category_goals": { "...same as Level 1..." },
      "result_status": "suboptimal"
    }
  ]
}
```

### B. `build_lp_problem` — precompute + goals hand-off (replaces the broken duplicate)

```python
    # (positioned AFTER problem_dict = {...} is assigned, and AFTER level_config is computed —
    # NOT immediately after valid_selected_ids, which is before problem_dict exists)
    category_map = {}
    for iid in valid_selected_ids:
        ing = get_ingredient_by_id(iid, db)
        if ing:
            cat = ing.get("category", "unknown")
            category_map.setdefault(cat, []).append(iid)
    problem_dict["category_to_ingredients"] = category_map

    # Hand category_goals to the objective builder via problem_dict — it has no
    # access to lp_params or cascade_level itself.
    problem_dict["category_goals"] = level_config.get("category_goals", {})
```

### C. `_build_stage_objective` — the missing branch, reading only from `problem_dict`

```python
    elif kind == "category_goal_deviation":
        category_map = problem_dict.get("category_to_ingredients", {})
        goals = problem_dict.get("category_goals", {})

        expr = 0
        total_x = pulp.lpSum(x_vars[iid] for iid in x_vars)

        for goal_name, goal in goals.items():
            target_pct = goal.get("target_pct", 0) / 100.0
            base_weight = goal.get("weight", 50)
            cat_list = goal.get("categories", [])

            cat_ingredients = []
            for c in cat_list:
                cat_ingredients.extend(category_map.get(c, []))

            if not cat_ingredients:
                continue

            cat_sum = pulp.lpSum(x_vars[iid] for iid in cat_ingredients if iid in x_vars)

            d_minus = prob.add_variable(f"d_cat_{goal_name}_minus", lowBound=0, cat="Continuous")
            d_plus  = prob.add_variable(f"d_cat_{goal_name}_plus",  lowBound=0, cat="Continuous")

            prob += cat_sum - (target_pct * total_x) == d_plus - d_minus

            effective_weight = base_weight * 0.01
            expr += (d_minus + d_plus) * effective_weight

        return expr
```

### D. `call_lp_solver` — capture deviation values for downstream use

```python
    # Extract solution
    x_values = {iid: pulp.value(var) for iid, var in x_vars.items() if pulp.value(var) is not None and pulp.value(var) > 1e-6}

    category_goal_deviations = {
        v.name: pulp.value(v) for v in prob.variables() if v.name.startswith("d_cat_")
    }

    # ... (existing nutrient_values computation, unchanged) ...

    return {
        "status": "feasible",
        "x_values": x_values,
        "nutrient_values": nutrient_values,
        "objective_value": pulp.value(prob.objective),
        "stages_solved": stages_solved,
        "solve_time_ms": solve_time_ms,
        "nutrient_slack_vars": problem_dict.get("nutrient_slack_vars", {}),
        "sul_slack_vars": problem_dict.get("sul_slack_vars", {}),
        "der_dev_vars": problem_dict.get("der_dev_vars", {}),
        "clinical_floor_bounds": problem_dict.get("clinical_floor_bounds", {}),
        "clinical_floor_relaxed": problem_dict.get("clinical_floor_relaxed", False),
        "category_goal_deviations": category_goal_deviations,
    }
```

### E. `build_output_contract` — read from `raw_result`, write into the final return literal

```python
    # (inserted before the function's final `return {...}` literal)
    category_goals = level_config.get("category_goals", {})
    deviations = raw_result.get("category_goal_deviations", {})
    template_adherence = {"components": {}}
    total_deviation = 0.0

    for goal_name, goal in category_goals.items():
        d_minus = deviations.get(f"d_cat_{goal_name}_minus")
        d_plus  = deviations.get(f"d_cat_{goal_name}_plus")

        if d_minus is None and d_plus is None:
            template_adherence["components"][goal_name] = {
                "target_pct": goal.get("target_pct", 0),
                "achieved_pct": 0.0,
                "absolute_deviation_pct": None,
                "skipped": True,
            }
            continue

        d_minus = d_minus or 0.0
        d_plus  = d_plus or 0.0
        target = goal.get("target_pct", 0)
        achieved = target + (d_plus - d_minus)
        abs_dev = d_plus + d_minus

        template_adherence["components"][goal_name] = {
            "target_pct": target,
            "achieved_pct": round(max(0.0, achieved), 2),
            "absolute_deviation_pct": round(abs_dev, 2),
            "skipped": False,
        }

        if abs_dev > 0:
            total_deviation += abs_dev

    template_adherence["overall_score"] = round(max(0.0, 100.0 - total_deviation), 1)
    meta["category_goal_deviations_raw"] = template_adherence["components"]

    return {
        "solver_output_schema": "v10.1",
        "solver_status": result_status,
        "feeding_recommendation": feeding_rec,
        "cascade_level_used": level,
        "animal_context": der_info.as_animal_context("male", 8, "intact"),
        "envelope": der_info.as_envelope_dict(),
        "allocations": allocations,
        "nutrient_results": nutrient_results,
        "diagnostic_analysis": diagnostic_analysis,
        "gaps": compute_gaps(raw_result, data, der_info, level),
        "alerts": [],
        "recommended_additions": [],
        "solver_metadata": meta,
        "template_adherence": template_adherence,
        "_unrounded_total_g": unrounded_total,
    }
```
