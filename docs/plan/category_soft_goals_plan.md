---
plan_id: plan-gsd-category-soft-goals
title: "GSD Raw Calculator — Category Soft Goals (BARF/PMR Preferences as Penalized Deviations)"
version: 1.0.0
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
repo:
  root: $PROJECT_ROOT
  data_dir: $PROJECT_ROOT/data
  scripts_dir: $PROJECT_ROOT/scripts
  tests_dir: $PROJECT_ROOT/tests
  docs_dir: $PROJECT_ROOT/docs
  base_commit: <TBD_BY_EXECUTOR>   # executor MUST capture `git rev-parse HEAD` before Task-1 and substitute here
  working_branch: feat/category-soft-goals
total_tasks: 6
parallel_groups: 0   # strictly sequential — every task depends on the previous
created: 2026-07-18T00:00:00Z
updated: 2026-07-18T00:00:00Z
language: en
paradigm: wall_vs_compass   # Level 1 goal_deviation = Wall; category_goal_deviation at 0.01x weight = Compass
---

# Plan: GSD Raw Calculator — Category Soft Goals (Option B)

## Objective

Implement soft goals for ingredient category percentages (`muscle_meat` 70%, `organ_secreting` 10%, etc.) as **penalized deviations** in the LP objective. Only categories with existing DB ingredients are included; categories without ingredients (bone, vegetable, fruit, seed, supplement, grain, dairy, egg) are excluded. This is **Option B** from the critical analysis — minimal risk, maximum value, zero structural changes to existing hard constraints or cascade architecture.

The mechanism: deviation variables `d_cat_<name>_minus` / `d_cat_<name>_plus` are added to the Level 1 and Level 2 objective stages with a **micro-weight multiplier** (`base_weight * 0.01`), guaranteeing they act strictly as tie-breakers and never override nutrient adequacy or antagonism-safety targets.

## Preconditions (plan-level — MUST hold before Task-1)

| ID | Condition | Verification command |
|---|---|---|
| P0 | Clean working tree at repo root | `cd $PROJECT_ROOT && git status --short \| wc -l` → `0` |
| P1 | Working branch created from `main` | `git rev-parse --abbrev-ref HEAD` → `feat/category-soft-goals` |
| P2 | Python ≥ 3.10 | `python --version` → `3.10+` |
| P3 | `pulp`, `pytest`, `jsonschema` installed | `python -c "import pulp, pytest, jsonschema; print('ok')"` → exit 0 |
| P4 | 32-test baseline green | `cd $PROJECT_ROOT && python -m pytest tests/ -q` → `32 passed` |
| P5 | `data/lp_parameters_data.json` exists and parses | `python -c "import json; json.load(open('$PROJECT_ROOT/data/lp_parameters_data.json'))"` → exit 0 |
| P6 | `build_pipeline.py` exists at repo root | `ls $PROJECT_ROOT/build_pipeline.py` exits 0 |
| P7 | `build_pipeline.py` exposes `_build_stage_objective`, `build_lp_problem`, `build_output_contract`, `get_ingredient_by_id` | `rg -n "def _build_stage_objective\|def build_lp_problem\|def build_output_contract\|def get_ingredient_by_id" $PROJECT_ROOT/build_pipeline.py` → 4 matches |
| P8 | `tests/test_cascade_integration.py` exists | `ls $PROJECT_ROOT/tests/test_cascade_integration.py` exits 0 |
| P9 | `data/DB_ingredientes.json` exposes `protein_sources.<group>.ingredients[].category` field (8-value enum) | `python -c "import json; db=json.load(open('$PROJECT_ROOT/data/DB_ingredientes.json')); cats=set(); [cats.add(i.get('category','')) for g in db['protein_sources'].values() if isinstance(g,dict) for i in g.get('ingredients',[])]; print(sorted(cats))"` → 8 distinct values from `{muscle_meat, muscle_organ, organ_secreting, organ_non_secreting, connective_tissue, blood_source, fish, fat_source}` |

If any precondition fails, **STOP** and report the blocker — do not attempt to auto-fix preconditions.

## Postconditions (plan-level — MUST hold after Task-6)

| ID | Condition | Verification command |
|---|---|---|
| Q0 | All 32 existing tests pass | `cd $PROJECT_ROOT && python -m pytest tests/ -q` → `32 passed` |
| Q1 | 4 new category-goal tests pass | `python -m pytest tests/test_cascade_integration.py -k category_goals -q` → `4 passed` |
| Q2 | `--gate-mapa` passes | `cd $PROJECT_ROOT && python build_pipeline.py --gate-mapa` → exit 0 |
| Q3 | Synthetic test: `muscle_meat` goal pulls solution toward 70% when ingredient pool allows | `python -m pytest tests/test_cascade_integration.py::test_category_goals_influence_solution -q` → `1 passed` |
| Q4 | Level 3 still returns `unsafe_diagnostic` for liver-only selection (hard wall unchanged) | `python -m pytest tests/test_cascade_integration.py -k liver -q` → existing test still passes |
| Q5 | No new hard constraints introduced (only deviation vars + soft objective terms) | `rg "prob \\+= .*cat_sum" $PROJECT_ROOT/build_pipeline.py` → 0 matches (only equality constraints, never `<=`/`>=` on `cat_sum`) |
| Q6 | MAPA regeneration clean | `cd $PROJECT_ROOT && python build_pipeline.py --generate-mapa --out MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md && rg -c "SOURCE: IMPLEMENTATION_SPEC" MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md` → `>= 10` |
| Q7 | Output contract includes `template_adherence` and `solver_metadata.category_goal_deviations_raw` | `python -c "import json; from build_pipeline import build_output_contract; ..."` (executor to write inline check) → both keys present |
| Q8 | Clean git working tree after final commit | `git status --short` → empty |

## Context Boundary

**The executing agent MAY read:**
- `$PROJECT_ROOT/build_pipeline.py`
- `$PROJECT_ROOT/data/lp_parameters_data.json`
- `$PROJECT_ROOT/data/DB_ingredientes.json`
- `$PROJECT_ROOT/data/db_ingredientes.schema.json`
- `$PROJECT_ROOT/tests/test_cascade_integration.py`
- `$PROJECT_ROOT/tests/test_dimensional_pipeline.py`
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
- Run `git push --force` or `git rebase -i` over other tasks' commits
- Reorder Level 1 stages — `goal_deviation` MUST come first with `fix_optimum: true`, `category_goal_deviation` second with `fix_optimum: false`, `minimize_absolute_der_deviation` third with `fix_optimum: true`

### Wall vs. Compass Architecture (DO NOT VIOLATE)

| Layer | Role | Mechanism |
|---|---|---|
| Wall (Level 1, stage 1) | Strict nutrient adequacy + antagonism safety | `goal_deviation` objective kind with `fix_optimum: true`; hard constraints (`CSTR_INCL_MAX_LIVER <= 5%`, Ca:P ratio, antagonism slack penalty 5000) |
| Compass (Level 1, stage 2 + Level 2, stage 2) | BARF/PMR category preferences | `category_goal_deviation` objective kind with `fix_optimum: false`; deviation vars `d_cat_<name>_minus/plus` with effective weight `base_weight * 0.01` (range 0.3–1.0) |

**Iron rule:** the Compass MUST NOT become a Wall. If the micro-weight multiplier is removed or scaled above 0.01, category goals could override a nutrient adequacy floor (e.g., pull muscle to 70% even when copper adequacy requires more liver). The Wall ensures the dog never suffers from hypervitaminosis A or Ca:P inversion; the Compass gently nudges toward the 70/10/5/5 evolutionary ideal only when the Wall is already satisfied.

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

**Iron rule:** the `* 0.01` multiplier is mandatory. Without it, category goals (~440) would rival nutrient deviation (~410) and could pull the solution away from clinically-required nutrient targets. With it, category goals only break ties between nutrient-equivalent solutions.

### Line Number Caveat

All line numbers in Tasks 1–6 are orientation aids, not patch coordinates. The executing agent MUST re-locate each target by content (function name + signature + distinctive comment) using `rg`, NOT by line number. After each edit, re-run `rg` to confirm the target moved as expected and no other call sites were silently shifted.

## Tasks

<!--
Graph convention:
  - depends_on: list of task_ids that MUST be in `completed` status
  - parallel_group: null for all tasks (strictly sequential)
  - Each task = exactly 1 commit
  - Commit message follows Conventional Commits: `feat(scope): description`
-->

---

### Task-1: Add `category_goals` config to `lp_parameters_data.json`

```yaml
task_id: task-1
title: "Add category_goals config to Level 1 and Level 2 solve_cascade entries"
depends_on: []
parallel_group: null
files_mutated:
  - $PROJECT_ROOT/data/lp_parameters_data.json
idempotent: true
estimated_loc: ~80   # JSON additions only, no code
commit_message: "feat(config): add category_goals to Level 1 and Level 2 solve_cascade"
severity: blocker
```

**Rationale:** the LP solver reads `solve_cascade[level].objective_stages` and `solve_cascade[level].category_goals` from this JSON. Without this config, Task-2 has nothing to consume. Adding it as a separate commit keeps the config-vs-code boundary clean and lets the executor verify the schema is still valid before any Python code is touched.

**Preconditions (in addition to plan-level):**
- P0–P5 satisfied
- P9 satisfied (all 8 category values confirmed present in DB)

**Steps:**

1. Open `$PROJECT_ROOT/data/lp_parameters_data.json`
2. Locate the `solve_cascade` array (top-level key). It currently has Level 1, Level 2, Level 3 entries.
3. In the **Level 1 entry** (the one with `"relax_tiers": []`), modify `objective_stages` to insert a new stage between the existing `goal_deviation` stage and the existing `minimize_absolute_der_deviation` stage. The new stage is:
   ```json
   {
     "name": "category_preferences",
     "kind": "category_goal_deviation",
     "fix_optimum": false
   }
   ```
4. In the same Level 1 entry, add a new top-level key `category_goals` (sibling to `objective_stages`, `relax_tiers`, `result_status`):
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
5. In the **Level 2 entry** (the one with `"relax_tiers": ["adequacy_soft", "envelope_soft"]`), insert the same `category_preferences` stage between the existing `weighted_normalized_slack` stage and the existing `minimize_absolute_der_deviation` stage.
6. In the same Level 2 entry, add the identical `category_goals` block (copy-paste from Level 1 — they MUST be byte-identical).
7. **Do NOT modify Level 3.** Level 3 is the diagnostic-only fallback; it must not be touched by this plan.
8. Verify JSON still parses and Level 1 stage ordering is exactly: `goal_deviation` (fix_optimum: true) → `category_preferences` (fix_optimum: false) → `minimize_absolute_der_deviation` (fix_optimum: true).

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

# V5: targets sum to 110% (not 100% — this is intentional, see "Absolute vs. Normalized Targets" in Context Boundary)
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
- Do NOT normalize target_pct values to sum to 100% (the 110% sum is intentional; `d_plus` absorbs the overshoot)
- Do NOT add `category_goals` to Level 3 (Level 3 is diagnostic-only)
- Do NOT set `fix_optimum: true` on the `category_preferences` stage (it MUST be `false` — category goals are a Compass, not a Wall)
- Do NOT skip Level 2 (category goals MUST also exist at Level 2 to provide a "compass" when the solver drops to a relaxed floor)
- Do NOT add categories that have zero DB ingredients (bone, vegetable, fruit, etc.) — only the 7 categories listed above

---

### Task-2: Implement `category_goal_deviation` objective kind + `add_category_goals()` + pre-compute category map

```yaml
task_id: task-2
title: "Implement category_goal_deviation objective kind, add_category_goals() helper, and pre-compute category_to_ingredients map"
depends_on:
  - task-1
parallel_group: null
files_mutated:
  - $PROJECT_ROOT/build_pipeline.py
idempotent: true
estimated_loc: ~60
commit_message: "feat(solver): implement category_goal_deviation objective kind with micro-weight multiplier"
severity: blocker
```

**Rationale:** this task adds the LP-side logic that consumes the `category_goals` config from Task-1. It is split from Task-3 (output contract) because the objective builder and the output contract are different functions in `build_pipeline.py` — keeping them in separate commits makes a regression bisectable to one of two distinct concerns.

**Preconditions (in addition to plan-level):**
- Task-1 committed (V1–V6 all pass)
- P7 satisfied (the 4 required functions exist in `build_pipeline.py`)

**Steps:**

1. **Pre-compute category_to_ingredients map.** Locate `def build_lp_problem` in `$PROJECT_ROOT/build_pipeline.py` via `rg -n "def build_lp_problem" build_pipeline.py`. Immediately AFTER the existing block that compiles `valid_selected_ids` (the list of ingredient IDs the user actually selected and that exist in the DB), insert:
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
   Re-locate the target with `rg -n "valid_selected_ids" build_pipeline.py` after the edit to confirm exactly one new assignment to `problem_dict["category_to_ingredients"]` exists.

2. **Pass `db` to `build_lp_problem` if not already passed.** Locate the call site(s) of `build_lp_problem` via `rg -n "build_lp_problem(" build_pipeline.py`. If `db` is not already in the argument list, add it as a keyword argument `db=db`. Update the function signature accordingly. (This is required so `get_ingredient_by_id` can resolve category metadata.)

3. **Implement the `category_goal_deviation` objective kind.** Locate `def _build_stage_objective` via `rg -n "def _build_stage_objective" build_pipeline.py`. Inside the dispatch chain (the `if kind == ...` / `elif kind == ...` ladder), add a new branch:
   ```python
   elif kind == "category_goal_deviation":
       # Get pre-computed category map from problem_dict (O(1) lookup).
       # Built by build_lp_problem() — see "Pre-compute category_to_ingredients map" above.
       category_map = problem_dict.get("category_to_ingredients", {})
       level_config = next(
           (l for l in lp_params.get("solve_cascade", [])
            if l.get("level") == cascade_level),
           {}
       )
       goals = level_config.get("category_goals", {})

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
               # The d_minus variable for this category is never created, so no penalty.
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
4. Verify no other `kind ==` branch was clobbered by re-running `rg -n "elif kind ==" build_pipeline.py` and confirming the count increased by exactly 1.
5. Verify `pulp` is imported at the top of `build_pipeline.py` (`rg -n "^import pulp" build_pipeline.py` → 1 match).

**State mutations:**

| File | Before | After |
|---|---|---|
| `build_pipeline.py` | `_build_stage_objective` has no `category_goal_deviation` branch; `build_lp_problem` does not pre-compute `category_to_ingredients`; `build_lp_problem` may not receive `db` | New `elif kind == "category_goal_deviation"` branch (~30 LOC); `build_lp_problem` pre-computes `problem_dict["category_to_ingredients"]` (~7 LOC); `build_lp_problem` signature includes `db=db` if it didn't already |

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

# V4: category_to_ingredients pre-computation is present
rg -n "category_to_ingredients" $PROJECT_ROOT/build_pipeline.py
# expected: >= 2 matches (one in build_lp_problem, one in _build_stage_objective)

# V5: NO hard constraint was introduced on cat_sum (only equality for deviation vars)
rg -n "prob \+= cat_sum" $PROJECT_ROOT/build_pipeline.py
# expected: 0 matches (the only line starting with "prob +=" inside the category block
#            must be "prob += cat_sum - (target_pct * total_x) == d_plus - d_minus",
#            which is an equality, NOT a hard <= or >= constraint. Confirm by visual
#            inspection.)

# V6: 32-test baseline still green (no regression from the new branch — it isn't called yet
#     because no existing stage uses kind="category_goal_deviation" until Task-1's config
#     is loaded; but the dispatch chain must still resolve cleanly)
cd $PROJECT_ROOT && python -m pytest tests/ -q
# expected: 32 passed
```

**Rollback:**

```bash
git checkout -- $PROJECT_ROOT/build_pipeline.py
```

**Anti-patterns to avoid in this task:**
- Do NOT remove the `* 0.01` micro-weight multiplier (effective weight would jump from 0.3–1.0 to 30–100, rivaling nutrient deviation)
- Do NOT normalize `target_pct` against the sum of active categories (targets are ABSOLUTE)
- Do NOT add `prob += cat_sum <= ...` or `prob += cat_sum >= ...` (only equality constraints for deviation vars)
- Do NOT skip the `if not cat_ingredients: continue` guard — without it, `cat_sum = pulp.lpSum([])` = 0, and the deviation var would force a misleading penalty against an empty category
- Do NOT move this stage to Level 1 slot 1 — it MUST be slot 2 (after `goal_deviation` with `fix_optimum: true`)

---

### Task-3: Add `template_adherence` block + raw deviations to output contract

```yaml
task_id: task-3
title: "Add template_adherence (user-facing) and category_goal_deviations_raw (audit) to build_output_contract()"
depends_on:
  - task-2
parallel_group: null
files_mutated:
  - $PROJECT_ROOT/build_pipeline.py
idempotent: true
estimated_loc: ~35
commit_message: "feat(output): expose template_adherence and category_goal_deviations_raw in output contract"
severity: blocker
```

**Rationale:** the LP solver now produces `d_cat_<name>_minus` / `d_cat_<name>_plus` variables, but without surfacing them in the output contract, downstream consumers (CLI, MAPA generator, audit log) cannot see how closely the solution matched the BARF/PMR template. This task adds two keys: `template_adherence` (clean user-facing summary) and `solver_metadata.category_goal_deviations_raw` (auditor-facing raw deviation values).

**Preconditions (in addition to plan-level):**
- Task-2 committed (V1–V6 all pass)

**Steps:**

1. Locate `def build_output_contract` via `rg -n "def build_output_contract" build_pipeline.py`.
2. After the block that computes allocations (the existing logic that builds `output["allocations"]` or equivalent), insert:
   ```python
   # === Category goal deviations (Option B — BARF/PMR template adherence) ===
   # Reads back the d_cat_<name>_minus / d_plus variables created by the
   # category_goal_deviation objective kind (see _build_stage_objective).
   category_goals = level_config.get("category_goals", {})
   template_adherence = {"components": {}}
   total_deviation = 0.0

   for goal_name, goal in category_goals.items():
       # Read deviation values from the solved problem.
       # prob.variablesMap() returns {var_name: LpVariable}; pulp.value() extracts the float.
       d_minus_var = prob.variablesMap().get(f"d_cat_{goal_name}_minus")
       d_plus_var  = prob.variablesMap().get(f"d_cat_{goal_name}_plus")
       d_minus = pulp.value(d_minus_var) if d_minus_var is not None else 0.0
       d_plus  = pulp.value(d_plus_var)  if d_plus_var  is not None else 0.0

       target = goal.get("target_pct", 0)
       achieved = target + (d_plus - d_minus)
       abs_dev = d_plus + d_minus

       template_adherence["components"][goal_name] = {
           "target_pct": target,
           "achieved_pct": round(max(0.0, achieved), 2),
           "absolute_deviation_pct": round(abs_dev, 2),
       }

       if abs_dev > 0:
           total_deviation += abs_dev

   # Overall score: 100 = perfect BARF/PMR match, 0 = maximally deviating.
   # Clamped to [0, 100].
   template_adherence["overall_score"] = round(max(0.0, 100.0 - total_deviation), 1)

   # Inject into final output:
   #   - template_adherence: user-facing clean block
   #   - solver_metadata.category_goal_deviations_raw: auditor-facing raw values
   output["template_adherence"] = template_adherence
   output.setdefault("solver_metadata", {})["category_goal_deviations_raw"] = \
       template_adherence["components"]
   ```
3. Verify `level_config` is in scope at the insertion point. If not, locate the existing code that resolves the active level's config from `lp_params["solve_cascade"]` and reuse that variable name. If no such variable exists, add:
   ```python
   level_config = next(
       (l for l in lp_params.get("solve_cascade", [])
        if l.get("level") == cascade_level),
       {}
   )
   ```
   at the top of the new block.
4. Verify `prob` (the solved `LpProblem` instance) and `pulp` are both in scope at the insertion point. If `pulp` is not imported in this function's module, confirm it is imported at file top (`rg -n "^import pulp" build_pipeline.py` → 1 match — already verified in Task-2 V5).

**State mutations:**

| File | Before | After |
|---|---|---|
| `build_pipeline.py` | `build_output_contract` returns output dict without `template_adherence` or `category_goal_deviations_raw` | New block (~30 LOC) reads back `d_cat_<name>_*` vars, computes `achieved_pct` and `overall_score`, injects both keys into output |

**Verification (deterministic):**

```bash
# V1: file still imports cleanly
python -c "import build_pipeline; print('ok')"
# expected exit: 0

# V2: template_adherence is mentioned in build_output_contract
rg -n "template_adherence" $PROJECT_ROOT/build_pipeline.py
# expected: >= 3 matches (variable assignment, output[...] =, comment)

# V3: category_goal_deviations_raw is mentioned
rg -n "category_goal_deviations_raw" $PROJECT_ROOT/build_pipeline.py
# expected: >= 1 match

# V4: overall_score formula present and clamped
rg -n "max\(0\.0, 100\.0 - total_deviation\)" $PROJECT_ROOT/build_pipeline.py
# expected: 1 match

# V5: 32-test baseline still green
cd $PROJECT_ROOT && python -m pytest tests/ -q
# expected: 32 passed

# V6: synthetic smoke test — call build_output_contract on a tiny synthetic problem
#     and confirm both keys appear in the output dict
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
# Confirm the variable-name round-trip the output contract relies on actually works:
assert 'd_cat_muscle_meat_minus' in {v.name for v in prob.variables()}
print('OK: variable naming convention is stable')
"
# expected exit: 0
```

**Rollback:**

```bash
git checkout -- $PROJECT_ROOT/build_pipeline.py
```

**Anti-patterns to avoid in this task:**
- Do NOT compute `achieved_pct` as `target - d_minus` only — the correct formula is `target + (d_plus - d_minus)` (overshoot is positive deviation, shortfall is negative)
- Do NOT remove the `max(0.0, ...)` clamp on `achieved_pct` (a negative achieved value would be nonsensical to display)
- Do NOT compute `overall_score` as `100 - count_of_deviating_categories` — it MUST be `100 - sum_of_absolute_deviations` (a 5% deviation in one category is worse than a 1% deviation in five categories)
- Do NOT omit the `setdefault("solver_metadata", {})` guard — older code paths may not initialize `solver_metadata` before this block runs

---

### Task-4: Add 4 new tests to `test_cascade_integration.py`

```yaml
task_id: task-4
title: "Add 4 category-goal tests covering Level 1 wiring, influence on solution, Level 2 relaxation, and output contract"
depends_on:
  - task-3
parallel_group: null
files_mutated:
  - $PROJECT_ROOT/tests/test_cascade_integration.py
idempotent: true
estimated_loc: ~120
commit_message: "test(cascade): add 4 category-goal tests (Level 1 wiring, influence, Level 2 slack, output contract)"
severity: blocker
```

**Rationale:** the 4 tests below are the only thing preventing a silent regression in the Compass layer. Each test targets one of the 4 code paths added in Tasks 1–3, and each is constructed to fail loudly if the Wall-vs-Compass architecture is violated (e.g., if the micro-weight multiplier is removed, `test_category_goals_influence_solution` will fail because category goals would dominate nutrients — but `test_category_goals_do_not_override_nutrient_targets` would also fail in the opposite direction, catching both sides of the regression).

**Preconditions (in addition to plan-level):**
- Task-3 committed (V1–V6 all pass)

**Steps:**

1. Open `$PROJECT_ROOT/tests/test_cascade_integration.py`.
2. Append the following 4 test functions at the end of the file. Use AAA+A pattern (Arrange / Act / Assert / + Additional verification):

   ```python
   # === Category Soft Goals (Option B) — 4 tests ===

   def test_category_goals_in_level1_objective():
       """Verify deviation vars d_cat_<name>_minus/plus are created when Level 1 runs."""
       # Arrange
       from tests.reference_cases import REFERENCE_ANIMAL, REFERENCE_SELECTION, REFERENCE_SCENARIO_ID
       from build_pipeline import build_lp_problem, solve_cascade
       import pulp

       # Act
       prob, problem_dict, x_vars = build_lp_problem(
           animal=REFERENCE_ANIMAL,
           selection=REFERENCE_SELECTION,
           scenario_id=REFERENCE_SCENARIO_ID,
       )
       result = solve_cascade(prob, problem_dict, x_vars, levels=[1])

       # Assert
       var_names = {v.name for v in prob.variables()}
       assert any(v.startswith("d_cat_muscle_meat_minus") for v in var_names), \
           "Expected d_cat_muscle_meat_minus var; category_goal_deviation stage did not run at Level 1"
       assert any(v.startswith("d_cat_muscle_meat_plus") for v in var_names), \
           "Expected d_cat_muscle_meat_plus var; category_goal_deviation stage did not run at Level 1"

       # + Additional: at least 3 of the 7 categories should have deviation vars
       #   (the others may be skipped if REFERENCE_SELECTION has no ingredients in those categories)
       cat_with_vars = {v.split("_")[2] for v in var_names if v.startswith("d_cat_")}
       assert len(cat_with_vars) >= 3, \
           f"Expected >= 3 categories with deviation vars, got {cat_with_vars}"


   def test_category_goals_influence_solution():
       """Synthetic test: muscle_meat goal (70%) pulls solution toward 70% when pool allows."""
       # Arrange
       # Build a synthetic ingredient pool where 4 muscle ingredients + 1 liver are available.
       # Without category goals, the LP would prefer nutrient-matched allocation (any combination).
       # With category goals at 70% muscle target, the muscle allocation should be pulled toward 70%.
       from build_pipeline import build_lp_problem, solve_cascade
       import pulp

       # Use the reference pool but expect muscle allocation to be >= 60% (allowing 10% slack
       # for nutrient adequacy pulling away from the strict 70% target).
       from tests.reference_cases import REFERENCE_ANIMAL, REFERENCE_SELECTION, REFERENCE_SCENARIO_ID

       # Act
       prob, problem_dict, x_vars = build_lp_problem(
           animal=REFERENCE_ANIMAL,
           selection=REFERENCE_SELECTION,
           scenario_id=REFERENCE_SCENARIO_ID,
       )
       result = solve_cascade(prob, problem_dict, x_vars, levels=[1, 2])

       # Assert
       allocations = result["allocations"]
       total = sum(a["amount_g"] for a in allocations)
       muscle_amount = sum(
           a["amount_g"] for a in allocations
           if a.get("category") in ("muscle_meat", "fish")
       )
       muscle_pct = (muscle_amount / total) * 100 if total > 0 else 0
       assert muscle_pct >= 60.0, \
           f"Muscle allocation {muscle_pct:.1f}% < 60% — category goal is not influencing the solution"

       # + Additional: the muscle_pct should NOT exceed 80% (the micro-weight should not
       #   dominate nutrient adequacy and force muscle to a hard 70%)
       assert muscle_pct <= 80.0, \
           f"Muscle allocation {muscle_pct:.1f}% > 80% — micro-weight multiplier may have been removed"


   def test_category_goals_relaxed_at_level2():
       """Verify Level 2 still uses category_goal_deviation (compass survives the floor drop)."""
       # Arrange
       from tests.reference_cases import REFERENCE_ANIMAL, REFERENCE_SELECTION, REFERENCE_SCENARIO_ID
       from build_pipeline import build_lp_problem, solve_cascade

       # Act — force a Level 2 drop by selecting an ingredient pool that cannot satisfy Level 1
       # (e.g., a pool with only 2 ingredients that cannot meet all nutrient adequacy floors).
       # If REFERENCE_SELECTION already triggers Level 2, this test passes trivially.
       # Otherwise, the test author should construct a Level-2-only scenario here.
       prob, problem_dict, x_vars = build_lp_problem(
           animal=REFERENCE_ANIMAL,
           selection=REFERENCE_SELECTION,
           scenario_id=REFERENCE_SCENARIO_ID,
       )
       result = solve_cascade(prob, problem_dict, x_vars, levels=[1, 2])

       # Assert
       assert result["solver_metadata"]["level_reached"] >= 2, \
           "Test setup error: expected solver to drop to Level 2, but it stayed at Level 1"
       var_names = {v.name for v in prob.variables()}
       assert any(v.startswith("d_cat_") for v in var_names), \
           "Level 2 should still create d_cat_* deviation vars (category_goal_deviation must exist at Level 2)"

       # + Additional: template_adherence should be populated in the Level 2 result
       assert "template_adherence" in result, \
           "Level 2 result missing template_adherence — output contract not invoked at Level 2"


   def test_category_goals_output_contract():
       """Verify output includes template_adherence and solver_metadata.category_goal_deviations_raw."""
       # Arrange
       from tests.reference_cases import REFERENCE_ANIMAL, REFERENCE_SELECTION, REFERENCE_SCENARIO_ID
       from build_pipeline import build_lp_problem, solve_cascade, build_output_contract

       # Act
       prob, problem_dict, x_vars = build_lp_problem(
           animal=REFERENCE_ANIMAL,
           selection=REFERENCE_SELECTION,
           scenario_id=REFERENCE_SCENARIO_ID,
       )
       result = solve_cascade(prob, problem_dict, x_vars, levels=[1, 2])
       output = build_output_contract(result, prob, problem_dict)

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

3. Verify all 4 tests are collected by pytest:
   ```bash
   python -m pytest tests/test_cascade_integration.py --collect-only -q | grep category_goals
   ```
   Expected: 4 matches.

4. Run the 4 new tests:
   ```bash
   python -m pytest tests/test_cascade_integration.py -k category_goals -v
   ```
   Expected: `4 passed`. If any test fails, do NOT patch the test to force pass — investigate the root cause in `build_pipeline.py` (Tasks 2–3).

5. Re-run the full suite to confirm no regression in the existing 32 tests:
   ```bash
   python -m pytest tests/ -q
   ```
   Expected: `36 passed` (32 original + 4 new).

**State mutations:**

| File | Before | After |
|---|---|---|
| `tests/test_cascade_integration.py` | 32 existing tests, no `category_goals` tests | +4 tests: `test_category_goals_in_level1_objective`, `test_category_goals_influence_solution`, `test_category_goals_relaxed_at_level2`, `test_category_goals_output_contract` |

**Verification (deterministic):**

```bash
# V1: 4 new tests collected
cd $PROJECT_ROOT && python -m pytest tests/test_cascade_integration.py --collect-only -q | grep -c category_goals
# expected: 4

# V2: 4 new tests pass
cd $PROJECT_ROOT && python -m pytest tests/test_cascade_integration.py -k category_goals -q
# expected: 4 passed

# V3: AAA+A pattern enforced (every test has Arrange, Act, Assert, + Additional comments)
rg -c "# Arrange" $PROJECT_ROOT/tests/test_cascade_integration.py
rg -c "# Act" $PROJECT_ROOT/tests/test_cascade_integration.py
rg -c "# Assert" $PROJECT_ROOT/tests/test_cascade_integration.py
rg -c "# \+ Additional" $PROJECT_ROOT/tests/test_cascade_integration.py
# expected: each >= 4 (the 4 new tests must have all 4 markers)

# V4: full suite still green (36 total = 32 original + 4 new)
cd $PROJECT_ROOT && python -m pytest tests/ -q
# expected: 36 passed
```

**Rollback:**

```bash
git checkout -- $PROJECT_ROOT/tests/test_cascade_integration.py
```

**Anti-patterns to avoid in this task:**
- Do NOT patch a failing test to force pass — if `test_category_goals_influence_solution` fails, the bug is in `build_pipeline.py` (most likely the micro-weight multiplier was removed or `category_to_ingredients` was not pre-computed), NOT in the test
- Do NOT skip the `+ Additional` assertion in any test — that's the AAA+A pattern's safety net
- Do NOT use `pytest.mark.skip` or `pytest.mark.xfail` on any of these 4 tests — they MUST pass
- Do NOT depend on a specific numeric allocation value (e.g., "muscle = exactly 70%") — the test must allow a tolerance band (`60% <= muscle_pct <= 80%`) because the micro-weight is a tie-breaker, not a hard constraint
- Do NOT write tests that mock the LP solver — these tests must exercise the real PuLP solver against real `lp_parameters_data.json` config

---

### Task-5: Update documentation

```yaml
task_id: task-5
title: "Document category_goal_deviations in output contract, build_pipeline objective kinds, and central plan index"
depends_on:
  - task-4
parallel_group: null
files_mutated:
  - $PROJECT_ROOT/docs/sat_solver_contrato.md
  - $PROJECT_ROOT/docs/sat_pipeline_codigo.md
  - $PROJECT_ROOT/docs/indice_plano_central.md
idempotent: true
estimated_loc: ~50
commit_message: "docs: document category_goal_deviation objective kind and template_adherence output field"
severity: low
```

**Rationale:** Tasks 1–4 added a new objective kind, a new output field, and a new config block — none of which are documented. Without this task, the next agent (or human) reading the docs will not know `category_goal_deviation` exists, will not know `template_adherence` is in the output contract, and will not be able to extend or debug the Compass layer.

**Preconditions (in addition to plan-level):**
- Task-4 committed (4 new tests pass)

**Steps:**

1. **`$PROJECT_ROOT/docs/sat_solver_contrato.md`** — locate the "Output Contract" section via `rg -n "## Output Contract" docs/sat_solver_contrato.md`. Add a new subsection:
   ```markdown
   ### `template_adherence` (NEW — Option B category soft goals)

   User-facing summary of how closely the solution matches the BARF/PMR template.

   | Field | Type | Description |
   |---|---|---|
   | `components` | `dict[str, {target_pct, achieved_pct, absolute_deviation_pct}]` | Per-category breakdown (muscle_meat, organ_secreting, ...) |
   | `overall_score` | `float` in `[0, 100]` | 100 = perfect template match, 0 = maximally deviating. Computed as `100 - sum(absolute_deviation_pct)`. |

   Raw per-category deviation values are also available under
   `solver_metadata.category_goal_deviations_raw` for audit / debugging.
   ```
2. **`$PROJECT_ROOT/docs/sat_pipeline_codigo.md`** — locate the "Objective Kinds" section via `rg -n "## Objective Kinds" docs/sat_pipeline_codigo.md` (or the equivalent existing section). Add:
   ```markdown
   ### `category_goal_deviation` (NEW — Option B)

   Adds penalized deviation variables `d_cat_<name>_minus` / `d_cat_<name>_plus`
   for each category goal in `lp_parameters_data.json:solve_cascade[level].category_goals`.

   **Mechanism:**
   - For each goal, creates `d_minus`, `d_plus >= 0` continuous variables
   - Adds equality constraint: `cat_sum - (target_pct * total_x) == d_plus - d_minus`
   - Adds to objective: `(d_minus + d_plus) * base_weight * 0.01`

   **Micro-weight multiplier (`* 0.01`):** mandatory. Without it, category goals
   (~440 total weight) would rival nutrient deviation (~410) and could pull the
   solution away from clinically-required nutrient targets. With it, effective
   weight is 0.3–1.0 per category (~4.4 total) — strictly a tie-breaker.

   **Where it runs:** Level 1 stage 2 (`fix_optimum: false`) and Level 2 stage 2
   (`fix_optimum: false`). NOT at Level 3 (diagnostic-only).

   **Helper function:** `add_category_goals(prob, x_vars, total, category_goals, problem_dict, db)`
   (defined inline in `_build_stage_objective` — refactor to a standalone function
   if the inline form grows beyond ~30 LOC).
   ```
3. **`$PROJECT_ROOT/docs/indice_plano_central.md`** — locate the changelog section via `rg -n "## Changelog" docs/indice_plano_central.md`. Add a new entry at the top:
   ```markdown
   - **2026-07-18** — Plan `plan-gsd-category-soft-goals` v1.0.0 merged. Added Option B
     category soft goals: 7 category_goals entries in `lp_parameters_data.json`,
     new `category_goal_deviation` objective kind in `build_pipeline.py`,
     `template_adherence` + `category_goal_deviations_raw` in output contract,
     4 new tests in `test_cascade_integration.py`. Micro-weight multiplier `* 0.01`
     enforces Wall-vs-Compass architecture (category goals strictly tie-break,
     never override nutrient adequacy). 36 tests passing (32 original + 4 new).
   ```
4. Verify no other documentation file references `category_goals` or `template_adherence` (those should be the only 3 files touched):
   ```bash
   rg -l "category_goal_deviation\|template_adherence" $PROJECT_ROOT/docs/
   ```
   Expected: exactly 3 files (the ones you just edited).

**State mutations:**

| File | Before | After |
|---|---|---|
| `docs/sat_solver_contrato.md` | No `template_adherence` section | New subsection documenting `components` and `overall_score` fields |
| `docs/sat_pipeline_codigo.md` | No `category_goal_deviation` section | New subsection documenting mechanism, micro-weight multiplier, Level 1/2 wiring |
| `docs/indice_plano_central.md` | Changelog does not mention this plan | New changelog entry at top |

**Verification (deterministic):**

```bash
# V1: template_adherence documented in output contract
rg -c "template_adherence" $PROJECT_ROOT/docs/sat_solver_contrato.md
# expected: >= 3 (heading + table rows)

# V2: category_goal_deviation documented in pipeline code docs
rg -c "category_goal_deviation" $PROJECT_ROOT/docs/sat_pipeline_codigo.md
# expected: >= 2 (heading + body)

# V3: micro-weight multiplier documented (with the 0.01 value)
rg -c "0\.01" $PROJECT_ROOT/docs/sat_pipeline_codigo.md
# expected: >= 2 (in the multiplier paragraph)

# V4: changelog entry added
rg -c "plan-gsd-category-soft-goals" $PROJECT_ROOT/docs/indice_plano_central.md
# expected: >= 1

# V5: only 3 docs files mention the new identifiers (no stray references)
rg -l "category_goal_deviation\|template_adherence" $PROJECT_ROOT/docs/ | wc -l
# expected: 3

# V6: full test suite still green (docs changes must not break anything)
cd $PROJECT_ROOT && python -m pytest tests/ -q
# expected: 36 passed
```

**Rollback:**

```bash
git checkout -- $PROJECT_ROOT/docs/sat_solver_contrato.md $PROJECT_ROOT/docs/sat_pipeline_codigo.md $PROJECT_ROOT/docs/indice_plano_central.md
```

**Anti-patterns to avoid in this task:**
- Do NOT document `category_goal_deviation` as a hard constraint — it MUST be described as a soft penalized deviation
- Do NOT omit the `* 0.01` multiplier from the docs — future readers must understand it is mandatory
- Do NOT mention Level 3 — `category_goal_deviation` does NOT run at Level 3
- Do NOT update any other docs file (only the 3 listed)
- Do NOT use future tense ("will be added") — write in past/present tense since the code is already merged by Task-4

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

**Rationale:** this task is the gate. Every acceptance criterion (Q0–Q8) must be checked here, in one shot, before the branch is considered mergeable. Skipping any check risks merging a regression that surfaces only in production (e.g., a MAPA generation that silently drops the new `template_adherence` field).

**Preconditions (in addition to plan-level):**
- Task-5 committed (docs updated)

**Steps:**

1. **Run the full pytest suite** — confirm 36 tests pass (32 original + 4 new):
   ```bash
   cd $PROJECT_ROOT && python -m pytest tests/ -q
   ```
   Expected: `36 passed`. If <36, do NOT proceed — investigate which test regressed.

2. **Run `--gate-mapa`** — confirm the MAPA gate still passes:
   ```bash
   cd $PROJECT_ROOT && python build_pipeline.py --gate-mapa
   ```
   Expected: exit 0. If non-zero, the new `category_goal_deviation` stage is breaking the MAPA pipeline — investigate before proceeding.

3. **Run the synthetic influence test in isolation** — confirm the muscle_meat goal actually pulls the solution:
   ```bash
   cd $PROJECT_ROOT && python -m pytest tests/test_cascade_integration.py::test_category_goals_influence_solution -v
   ```
   Expected: `1 passed`. If this fails, the Compass is not influencing the solution (likely a wiring bug in Task-2 or Task-3).

4. **Confirm Level 3 liver-only safety wall still triggers** — confirm the existing test still passes:
   ```bash
   cd $PROJECT_ROOT && python -m pytest tests/test_cascade_integration.py -k liver -v
   ```
   Expected: existing test still passes. If it fails, the new Compass somehow weakened the liver-only hard wall — investigate immediately (this is a clinical-safety regression).

5. **Regenerate MAPA** with the corrected pipeline:
   ```bash
   cd $PROJECT_ROOT && python build_pipeline.py --generate-mapa --out MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md
   ```
   Then confirm the provenance markers are still present:
   ```bash
   rg -c "SOURCE: IMPLEMENTATION_SPEC" $PROJECT_ROOT/MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md
   ```
   Expected: `>= 10`. If `< 10`, the MAPA regeneration is broken — investigate.

6. **Confirm no hard constraints were introduced on `cat_sum`:**
   ```bash
   rg -n "prob \+= cat_sum" $PROJECT_ROOT/build_pipeline.py
   ```
   Expected: 0 matches. (The only `prob +=` line in the category block is the equality `prob += cat_sum - (target_pct * total_x) == d_plus - d_minus`, which is a definition, not a hard `<=`/`>=` constraint.)

7. **Confirm clean working tree** (after committing the regenerated MAPA):
   ```bash
   cd $PROJECT_ROOT && git status --short
   ```
   Expected: empty. If non-empty, either the MAPA regeneration left stray files or a previous task forgot to commit.

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
# V1: Q0 — 32 existing tests pass (subset of the 36 total)
cd $PROJECT_ROOT && python -m pytest tests/ -q --ignore-glob="*category_goals*"
# expected: 32 passed

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

# V6: Q5 — no hard constraints introduced
rg -c "prob \+= cat_sum (<=\|>=)" $PROJECT_ROOT/build_pipeline.py
# expected: 0

# V7: Q6 — MAPA regenerated with provenance markers
rg -c "SOURCE: IMPLEMENTATION_SPEC" $PROJECT_ROOT/MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md
# expected: >= 10

# V8: Q7 — output contract includes both new keys
python -c "
import json
from build_pipeline import build_lp_problem, solve_cascade, build_output_contract
from tests.reference_cases import REFERENCE_ANIMAL, REFERENCE_SELECTION, REFERENCE_SCENARIO_ID
prob, pd, xv = build_lp_problem(REFERENCE_ANIMAL, REFERENCE_SELECTION, REFERENCE_SCENARIO_ID)
result = solve_cascade(prob, pd, xv, levels=[1, 2])
output = build_output_contract(result, prob, pd)
assert 'template_adherence' in output
assert 'category_goal_deviations_raw' in output.get('solver_metadata', {})
print('OK')
"
# expected exit: 0

# V9: Q8 — clean git working tree
cd $PROJECT_ROOT && git status --short | wc -l
# expected: 0
```

**Rollback:**

```bash
# If MAPA regeneration produced a broken file:
git checkout -- $PROJECT_ROOT/MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md

# If the entire plan needs to be reverted (post-merge):
git revert <task-1-sha>..<task-6-sha>
```

**Anti-patterns to avoid in this task:**
- Do NOT skip any of the 9 verification commands (V1–V9) — each maps to a postcondition (Q0–Q8)
- Do NOT mark this task complete if `--gate-mapa` fails — the gate is non-negotiable
- Do NOT merge the branch if `test_category_goals_influence_solution` fails — the Compass is not working
- Do NOT merge the branch if the liver-only test fails — the Wall has been breached (clinical safety regression)
- Do NOT skip MAPA regeneration — without it, downstream consumers read stale evidence
- Do NOT commit any file outside the 4 listed in `files_mutated` across all tasks

---

## Continuous Checking System

The pipeline runs gates at every transition. **No transition is allowed without explicit DoD satisfaction.** Gates are hard blockers, not signals.

```
[Task-1: Config]
    │ gate: V1–V6 (JSON parses, Level 1/2 stages correct, Level 3 unchanged, targets sum to 110%, schema validates)
    ▼
[Task-2: Objective kind + pre-compute map]
    │ gate: V1–V6 (imports clean, 1 new branch, micro-weight present, category_to_ingredients present, no hard constraints, 32 tests pass)
    ▼
[Task-3: Output contract]
    │ gate: V1–V6 (imports clean, template_adherence + raw present, formula clamped, 32 tests pass, smoke test)
    ▼
[Task-4: Tests]
    │ gate: V1–V4 (4 collected, 4 pass, AAA+A markers, 36 total pass)
    ▼
[Task-5: Docs]
    │ gate: V1–V6 (3 docs files updated, no stray references, 36 tests still pass)
    ▼
[Task-6: Validation]
    │ gate: V1–V9 (Q0–Q8 all green, MAPA regenerated, clean tree)
    ▼
[PLAN COMPLETE — ready to merge]
```

### Failure Recovery Matrix

| Gate Fails | Recovery Action |
|---|---|
| Task-1 V2 (stage ordering) | Re-edit `lp_parameters_data.json`; confirm `fix_optimum` flags match the spec exactly |
| Task-1 V5 (sum ≠ 110%) | Do NOT normalize — re-add any category that was accidentally dropped, OR confirm the 110% is intentional (it is) |
| Task-2 V3 (micro-weight missing) | Re-add `effective_weight = base_weight * 0.01` — this is mandatory, not optional |
| Task-2 V5 (hard constraint introduced) | Remove any `prob += cat_sum <= ...` or `prob += cat_sum >= ...` lines; only equality definitions are allowed |
| Task-2 V6 (32 tests regressed) | `git diff build_pipeline.py` — the new branch likely shifted an existing call site; re-locate by content with `rg` |
| Task-3 V6 (smoke test fails) | The variable naming convention `d_cat_<name>_minus/plus` is broken; check the `f-string` interpolation in Task-2 step 3 |
| Task-4 V2 (test fails) | Do NOT patch the test — investigate `build_pipeline.py`. Most likely cause: `category_to_ingredients` was not pre-computed because `valid_selected_ids` is empty or `db` was not passed |
| Task-4 V4 (36 ≠ 32+4) | One of the existing 32 tests regressed; `git bisect` across Tasks 1–4 to find which commit broke it |
| Task-5 V5 (stray docs references) | Another docs file mentions `category_goal_deviation` — either delete that reference or move it to one of the 3 canonical docs files |
| Task-6 V3 (`--gate-mapa` fails) | The new objective kind is breaking MAPA generation; check `rg "SOURCE: IMPLEMENTATION_SPEC" build_pipeline.py` to confirm provenance markers didn't move |
| Task-6 V5 (liver-only test fails) | CRITICAL — clinical safety regression. The Compass somehow breached the Wall. `git revert` Tasks 1–5 immediately and re-plan |
| Task-6 V9 (working tree not clean) | Either MAPA regeneration left stray files, or a previous task forgot to commit. `git status` to identify, then commit or `git checkout` as appropriate |

### Iron Rules

1. **NEVER remove the `* 0.01` micro-weight multiplier.** Without it, the Compass becomes a Wall and category goals can override nutrient adequacy.
2. **NEVER normalize category targets.** Targets are ABSOLUTE (70% muscle is 70% of `total_x`, not 70% of active categories).
3. **NEVER add `category_goals` to Level 3.** Level 3 is diagnostic-only; it does not run the Compass.
4. **NEVER set `fix_optimum: true` on the `category_preferences` stage.** Category goals are a Compass, not a Wall.
5. **NEVER introduce a hard constraint on `cat_sum`.** Only equality definitions (`cat_sum - target * total_x == d_plus - d_minus`) are allowed.
6. **NEVER skip Level 2 for category goals.** The Compass must survive the floor drop — without it, a Level 2 solution has no guidance.
7. **NEVER patch a failing test to force pass.** If a category-goal test fails, the bug is in `build_pipeline.py`, not in the test.
8. **NEVER merge if the liver-only test fails.** That is a clinical-safety regression — `git revert` immediately.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Micro-weight multiplier accidentally removed in a future refactor | Medium | Critical | Iron Rule #1; documented in `sat_pipeline_codigo.md`; enforced by `test_category_goals_influence_solution` upper bound (`muscle_pct <= 80%`) |
| Category goals override nutrient adequacy (Compass becomes Wall) | Low | Critical | Micro-weight `* 0.01` caps effective weight at 0.3–1.0 per category; antagonism slack penalty (5000) dwarfs total category weight (~4.4 effective) |
| Level 1 purity breached (adequacy slack leaks into Level 1) | Low | High | Iron Rule #4; `fix_optimum: false` on `category_preferences` stage; verified by Task-1 V2 |
| Level 3 liver-only safety wall weakened | Very Low | Critical | Iron Rule #8; `CSTR_INCL_MAX_LIVER <= 5%` hard constraint untouched; verified by Task-6 V5 |
| PuLP `prob.add_variable()` API mismatch | Low | High | Use existing pattern from `build_pipeline.py` (`rg "prob.add_variable" build_pipeline.py` to find precedents); fallback to `pulp.LpVariable(...)` constructor |
| Category lookup failure (`get_ingredient_by_id` returns None) | Low | Medium | Defensive: `if not cat_ingredients: continue` skips the category silently instead of crashing |
| Cascade order regression (Level 1 → 2 → 3 descent broken) | Low | High | Task-6 V5 (liver-only test) + 32-test baseline; any cascade reordering would break existing tests |
| Output contract change breaks downstream consumers | Low | Medium | Non-breaking: only NEW fields added (`template_adherence`, `category_goal_deviations_raw`); existing fields unchanged |
| MAPA regeneration drops provenance markers | Low | High | Task-6 V7 (`rg -c "SOURCE: IMPLEMENTATION_SPEC" MAPA_COMPLETO_JSONs_GSD_Diet_Calc.md` must return `>= 10`) |
| Test author hard-codes a specific allocation percentage | Medium | Medium | Anti-pattern explicitly listed in Task-4; tolerance band `60% <= muscle_pct <= 80%` is mandatory |

---

## Acceptance Criteria (mapped to postconditions and tasks)

- [ ] Q0 — All 32 existing tests pass (Task-6 V1)
- [ ] Q1 — 4 new category-goal tests pass (Task-6 V2)
- [ ] Q2 — `--gate-mapa` passes (Task-6 V3)
- [ ] Q3 — Synthetic test: `muscle_meat` goal pulls solution toward 70% (Task-6 V4)
- [ ] Q4 — Level 3 still returns `unsafe_diagnostic` for liver-only (Task-6 V5)
- [ ] Q5 — No new hard constraints introduced (Task-6 V6)
- [ ] Q6 — MAPA regeneration clean (Task-6 V7)
- [ ] Q7 — Output contract includes `template_adherence` and `category_goal_deviations_raw` (Task-6 V8)
- [ ] Q8 — Clean git working tree after final commit (Task-6 V9)

---

## Timeline

| Phase | Duration |
|---|---|
| Task-1: `lp_parameters_data.json` config | 15 min |
| Task-2: `category_goal_deviation` objective kind + pre-compute map | 1–1.5 hours |
| Task-3: `template_adherence` output contract | 45 min |
| Task-4: 4 new tests (AAA+A) | 1 hour |
| Task-5: Documentation | 30 min |
| Task-6: Final validation + MAPA regeneration | 30 min |
| **Total** | **~4–5 hours** |

---

## Approval

**Approved by**: User  
**Implementation start**: Upon confirmation  
**Rollback plan**: `git revert <task-1-sha>..<task-6-sha>` (sequential revert of all 6 commits)

---

## Decisions & Resolutions

### 1. Normalization: REJECT Dynamic Normalization (Keep Absolute Targets)

**Decision:** Keep absolute targets (e.g., 70% muscle, 10% organ_secreting). Do NOT normalize against the sum of active categories.

**Why:** BARF/PMR ratios are absolute biological ideals, not relative proportions of whatever is in the bowl. If a user omits bone (no `bone` category exists in the DB), muscle should NOT mathematically inflate to 77% just to force the sum to 100%. The biological meaning of "70% muscle" is "70% of the dog's daily intake by mass", regardless of what else is or isn't in the bowl.

**How the math handles it:** the LP deviation variables `d_plus` and `d_minus` naturally absorb the slack. If targets sum to 110% (as they do in this plan), the `d_plus` variables absorb the 10% overshoot. If a category is missing from the user's selection (e.g., no `connective_tissue` ingredient selected), the `if not cat_ingredients: continue` guard in Task-2 skips that category entirely — no `d_minus` variable is created, so no penalty is incurred. The biological meaning stays intact.

### 2. Level 1 Stages: CONFIRM Level 1 Purity

**Decision:** Level 1 MUST remain the "Strict Adequacy & Safety" wall. Adequacy slack stays at Level 2. The new `category_goal_deviation` stage is inserted as Level 1 stage 2 (between `goal_deviation` and `minimize_absolute_der_deviation`), with `fix_optimum: false`.

**Corrected Level 1 Cascade:**
1. `goal_deviation` (Nutrient targets + Antagonism penalties) → `fix_optimum: true`
2. `category_goal_deviation` (BARF/PMR preferences) → `fix_optimum: false`
3. `minimize_absolute_der_deviation` (Hit caloric envelope) → `fix_optimum: true`

**Why `fix_optimum: false` on stage 2:** if it were `true`, the solver would be forced to find the category-goal optimum BEFORE moving to stage 3, which could pull the caloric envelope away from the user's target. With `fix_optimum: false`, the solver is allowed to deviate from the category-goal optimum if doing so better satisfies the caloric envelope in stage 3.

### 3. Level 2 Integration: CONFIRM Category Goals at Level 2

**Decision:** `category_goal_deviation` MUST also exist at Level 2 (stage 2, same position as Level 1).

**Why:** if the solver drops to Level 2 (e.g., user selected an imbalanced pool of ingredients that cannot meet Level 1's strict nutrient floors), it still needs a "compass" to guide it toward the closest possible BARF/PMR approximation, even while it is actively relaxing nutrient adequacy floors. Without the Compass at Level 2, a Level 2 solution would be nutrient-adequate (relaxed) but category-arbitrary — the dog might get 95% muscle and 5% liver, which is biologically inappropriate even if copper adequacy is met.

**Implementation:** the `category_goals` block is byte-identical between Level 1 and Level 2 (verified by Task-1 V3). The objective kind dispatch in `_build_stage_objective` reads the active level's config via `next(l for l in lp_params["solve_cascade"] if l["level"] == cascade_level)`, so the same code path serves both levels.

### 4. Output Field Name: `template_adherence` (User) + `category_goal_deviations_raw` (Audit)

**Decision:** use `template_adherence` as the clean, user-facing summary block. Embed the raw `category_goal_deviations_raw` dict inside `solver_metadata` for strict auditability.

**Why two fields:** the user-facing `template_adherence` block includes computed fields (`achieved_pct`, `overall_score`) that are convenient for display but lossy (rounded to 2 decimals, clamped to `[0, 100]`). The auditor-facing `category_goal_deviations_raw` is the unprocessed per-category dict, useful for debugging regressions or proving to a regulator that the solver behaved as specified.

**Implementation:** both fields are populated by the same loop in `build_output_contract` (Task-3 step 2). The raw field is a direct reference to `template_adherence["components"]`, not a copy — this guarantees they cannot diverge.

### 5. Liver/Organ Edge Case: NO CODE CHANGE NEEDED

**Decision:** no special-case code is needed for the liver-only edge case. The existing hard wall (`CSTR_INCL_MAX_LIVER <= 5%`) and the new soft goal (`organ_secreting = 10%`) interact correctly without intervention.

**Why:** if the user selects *only* liver, the hard wall (`CSTR_INCL_MAX_LIVER <= 5%`) blocks the solver at 5% liver allocation. The soft goal (`organ_secreting = 10%`) incurs a 5% `d_minus` penalty (the shortfall below the 10% target). The solver outputs 5% liver, and the `template_adherence` score correctly reflects the 5% deviation. The math handles it perfectly — the Wall enforces clinical safety, the Compass reports the deviation, and neither needs to know about the other.

**Verification:** Task-6 V5 (`python -m pytest tests/test_cascade_integration.py -k liver -v`) confirms the existing liver-only test still passes. If it fails, the Compass has somehow breached the Wall — a critical regression requiring immediate `git revert`.

---

## Implementation Blueprint

### A. Corrected `lp_parameters_data.json`

Notice the strict separation of Level 1 (strict) and Level 2 (relaxed), and the absence of dynamic normalization.

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

### B. Corrected `build_pipeline.py` (Objective Builder)

This snippet implements the **absolute targets** (no normalization) and the **micro-weight multiplier** to guarantee it acts strictly as a tie-breaker.

```python
elif kind == "category_goal_deviation":
    # Get pre-computed category map from problem_dict (O(1) lookup)
    category_map = problem_dict.get("category_to_ingredients", {})
    level_config = next(
        (l for l in lp_params.get("solve_cascade", [])
         if l.get("level") == cascade_level),
        {}
    )
    goals = level_config.get("category_goals", {})

    expr = 0
    total_x = pulp.lpSum(x_vars[iid] for iid in x_vars)

    for goal_name, goal in goals.items():
        target_pct = goal.get("target_pct", 0) / 100.0  # ABSOLUTE target (e.g., 0.70)
        base_weight = goal.get("weight", 50)
        cat_list = goal.get("categories", [])

        # Gather ingredients for this category
        cat_ingredients = []
        for c in cat_list:
            cat_ingredients.extend(category_map.get(c, []))

        if not cat_ingredients:
            continue  # Skip if user didn't select any ingredients in this category

        cat_sum = pulp.lpSum(x_vars[iid] for iid in cat_ingredients if iid in x_vars)

        # Create deviation variables (Absolute targets, no normalization)
        d_minus = prob.add_variable(f"d_cat_{goal_name}_minus", lowBound=0, cat="Continuous")
        d_plus  = prob.add_variable(f"d_cat_{goal_name}_plus",  lowBound=0, cat="Continuous")

        # Constraint: cat_sum - (target_pct * total_x) = d_plus - d_minus
        # (equality definition, NOT a hard <= / >= constraint on cat_sum)
        prob += cat_sum - (target_pct * total_x) == d_plus - d_minus

        # MICRO-WEIGHT: Multiply by 0.01 to ensure this is strictly a tie-breaker.
        # Effective weight: 0.3 to 1.0.
        # Nutrient weights are 1-10. Antagonism is 5000. This guarantees safety.
        effective_weight = base_weight * 0.01
        expr += (d_minus + d_plus) * effective_weight

    return expr
```

### C. Pre-compute Category Map (Performance Fix)

Add this to `build_lp_problem()` right after compiling coefficients to ensure O(1) lookups in the objective builder:

```python
# Pre-compute category to ingredients mapping for O(1) lookups.
# Required by the category_goal_deviation objective kind (Option B).
category_map = {}
for iid in valid_selected_ids:
    ing = get_ingredient_by_id(iid, db)
    if ing:
        cat = ing.get("category", "unknown")
        category_map.setdefault(cat, []).append(iid)
problem_dict["category_to_ingredients"] = category_map
```

### D. Output Contract (`build_output_contract`)

Add the `template_adherence` block for the user, and raw deviations for the auditor.

```python
# Inside build_output_contract, after computing allocations:
category_goals = level_config.get("category_goals", {})
template_adherence = {"components": {}}
total_deviation = 0.0

for goal_name, goal in category_goals.items():
    # Extract deviations from the solver result (passed via problem_dict)
    d_minus_var = prob.variablesMap().get(f"d_cat_{goal_name}_minus")
    d_plus_var  = prob.variablesMap().get(f"d_cat_{goal_name}_plus")
    d_minus = pulp.value(d_minus_var) if d_minus_var is not None else 0.0
    d_plus  = pulp.value(d_plus_var)  if d_plus_var  is not None else 0.0

    target = goal.get("target_pct", 0)
    achieved = target + (d_plus - d_minus)
    abs_dev = d_plus + d_minus

    template_adherence["components"][goal_name] = {
        "target_pct": target,
        "achieved_pct": round(max(0.0, achieved), 2),
        "absolute_deviation_pct": round(abs_dev, 2),
    }

    if abs_dev > 0:
        total_deviation += abs_dev

# Calculate overall score (100 = perfect BARF/PMR match)
template_adherence["overall_score"] = round(max(0.0, 100.0 - total_deviation), 1)

# Inject into final output
output["template_adherence"] = template_adherence
output.setdefault("solver_metadata", {})["category_goal_deviations_raw"] = \
    template_adherence["components"]
```

---

## Summary of the Paradigm

By rejecting dynamic normalization and enforcing Level 1 purity, this plan preserves the **Wall vs. Compass** architecture:

- **The Wall** (Level 1 `goal_deviation` stage 1 + hard constraints like `CSTR_INCL_MAX_LIVER <= 5%` and antagonism slack penalty 5000) ensures the dog never suffers from hypervitaminosis A, Ca:P inversion, or copper toxicity. The Wall is non-negotiable and untouched by this plan.
- **The Compass** (`category_goal_deviation` at Level 1 stage 2 and Level 2 stage 2, with `* 0.01` micro-weight multiplier) gently pulls the formulation toward the 70/10/5/5 evolutionary BARF/PMR ideal. It gracefully degrades to a "suboptimal but viable" state if the user's ingredient pool lacks the necessary categories (the `if not cat_ingredients: continue` guard skips empty categories silently), all without crashing the solver or breaching the Wall.

The micro-weight multiplier (`* 0.01`) is the linchpin. Without it, the Compass becomes a Wall and category goals could override nutrient adequacy. With it, effective per-category weight stays in `[0.3, 1.0]` — strictly a tie-breaker, never a dictator. Iron Rule #1 enforces this forever.
