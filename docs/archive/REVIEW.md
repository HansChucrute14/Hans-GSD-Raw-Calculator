# Systematic Adversarial Review - Hans GSD Raw Calculator

**Review date:** 2026-07-20  
**Tree reviewed:** `d5d8990` (`fix/dead-code-tree-and-audit-hash`)  
**Review mode:** static code and configuration review; no fresh execution claim  
**Scope:** `src/gsd/`, `data/`, JSON schemas, CLI, tests, architecture documents, and output contracts.

## 1. Executive verdict

This is a research prototype, not a feeding-recommendation system. The repository
has useful foundations: modular package boundaries, a three-level cascade,
ingredient provenance fields, a non-feedable Level 3 output barrier, and a
reasonable attempt at energy-normalized nutrient handling. Those foundations do
not make the current solver safe.

The decisive problem is not one bad coefficient. Several declared policies are
not the policies optimized by the live LP: criticality metadata and antagonism
penalties are discarded before objective construction, Level 3 is not
lexicographic, inclusion relaxations are free, and category adherence is both
dimensionally invalid and configured to be impossible. The output contract then
labels every nutrient `adequate` while leaving percentage fields null. A user can
receive a seemingly structured result that has not passed the safety logic claimed
by the documentation.

**Production readiness:** Not ready for any autonomous or advisory feeding use.
**Scientific readiness:** Not ready for clinical validation; energy data are
estimated with universal defaults for all executable ingredients.
**Overall maturity:** 3.0 / 10. The project is an auditable prototype with a
recoverable design, but the P0 defects invalidate its central optimization claims.

## 2. Method and evidence limits

The review traced data from request parsing through matrix construction, LP
assembly, objective construction, CBC invocation, output construction, and
validation. JSON rules were compared with the code that consumes them; a rule is
not treated as implemented merely because it is present in configuration.

No installed Python interpreter is available in this workspace, so tests and CLI
commands were not freshly executed. Every finding is therefore marked as static
evidence and should receive a targeted regression test before being declared
fixed. This is not a limitation that reduces severity: it means the project must
not rely on historical test-pass claims for the present tree.

For nutrition context, AAFCO profiles use life-stage-specific nutrient minima and
some maxima; large-size growth has special calcium/phosphorus considerations.
WSAVA also frames nutrition as an individualized clinical assessment, not only a
formula calculation. See [AAFCO nutrient profiles](https://www.aafco.org/wp-content/uploads/2023/01/Pet_Food_Report_Annual_2014-Appendix_A-Revised_AAFCO_Nutrient_Profiles-Final_092214.pdf)
and [WSAVA Global Nutrition Guidelines](https://wsava.org/global-guidelines/global-nutrition-guidelines/).

## 3. Risk register

| ID | Severity | Priority | Subsystem | Finding |
|---|---|---|---|---|
| R-01 | Critical → MITIGATED | P0 | LP objective | Registry and antagonism metadata are dropped before objective construction. **2026-07-20: Keys restored to return dict; _build_stage_objective() now raises KeyError on missing keys (no silent default).** |
| R-02 | Critical → MITIGATED | P0 | LP objective | Level 3 does not preserve the SUL optimum before later stages. **2026-07-20: `fix_optimum: true` already set for all predecessor stages in JSON; `call_lp_solver()` applies preserving constraint `prob += obj_expr <= bound` after each fixed stage; `order_verified` computed from `fix_optimum_applied` list. Mitigation verified by `test_r02_regression_fix_optimum_enforces_lexicographic_order` (raw solver-level check of `fix_optimum_applied`).** |
| R-03 | Critical → MITIGATED | P0 | LP objective | Hash perturbation dominates nutrition objectives and every stage. **2026-07-20: tie-break moved to final stage only; hash perturbation (0–999.9 per ingredient) removed; uses only JSON tie_break_weight (0.001 × grams). Mitigation verified by `test_r03_regression_tiebreak_final_stage_only`.** |
| R-04 | High | P0 | Category goals | Deviations in grams are reported as percentages. |
| R-05 | High | P0 | Category goals | Level 1/2 category targets total 110 percent. |
| R-06 | High | P0 | Safety constraints | Individual inclusion limits in the ingredient DB are never applied. |
| R-07 | High | P0 | Level 3 | Inclusion and maximum-envelope relaxations have no objective cost or output report. |
| R-08 | High | P0 | Input handling | Empty or unknown-only ingredient requests can crash before a safe response. |
| R-09 | High | P0 | Output contract | Nutrient result statuses and target fields are placeholders, not assessments. |
| R-10 | High | P1 | Nutrition/energy | Every ingredient uses default moisture, ash, and fibre in energy calculation. |
| R-11 | High | P1 | Configuration | Clinical-floor retry is promised by JSON but absent from executable control flow. |
| R-12 | High | P1 | Policy enforcement | Conditional fat adequacy is display-only and never changes cascade behavior. |
| R-13 | Medium | P1 | Input handling | Unknown scenarios get inconsistent silent fallbacks. |
| R-14 | Medium | P1 | Validation/schema | Schema non-conformance is downgraded to a warning; most data files lack schemas. |
| R-15 | Medium | P2 | Architecture | Constraint tiers are partly hardcoded by ID, defeating declarative policy. |
| R-16 | Medium | P2 | Maintainability | `objective_weights.json` is documentation/index data, not solver policy. |
| R-17 | Medium | P2 | Diagnostics | Infeasible CBC results lack constraint-level explanation or an IIS workflow. |
| R-18 | Medium | P2 | Testing | Tests assert structure and self-described metadata more often than independent outcomes. |

## 4. Findings

### R-01 - Objective metadata is silently discarded

**Severity:** Critical. **Priority:** P0.

1. **Exact location:** `src/gsd/solver.py`, `build_lp_problem()` initial
   `problem_dict` around lines 176-200, final return around lines 470-486, and
   `_build_stage_objective()` around lines 618-700.
2. **Root cause:** The local dictionary receives `nutrient_registry`,
   `antagonism_slack_vars`, and `antagonism_penalty_weights`, but the function
   returns a newly built dictionary without those keys.
3. **Evidence:** The objective reads `problem_dict.get("nutrient_registry", {})`
   and defaults every absent criticality to `low`; it reads antagonism maps with
   empty-dictionary defaults. The final return contains nutrient/SUL slack maps but
   omits registry and antagonism maps.
4. **Impact:** The apparent clinical-criticality fix is ineffective at runtime:
   all nutrients use weight 1.0. Level 1 does not penalize antagonism slacks at
   all. This invalidates the claimed objective hierarchy.
5. **Recommended solution:** Replace the loose return dictionary with a typed
   `ProblemArtifacts` dataclass, or return the one populated context object.
   Add tests that inspect actual objective coefficients for a `critical` nutrient,
   a `low` nutrient, and a Ca:P slack.
6. **Why superior:** A typed single hand-off cannot silently omit values created
   earlier in the build.
7. **Priority rationale:** No solver result is trustworthy while the declared
   clinical objective differs from the actual objective.

### R-02 - Level 3 is not lexicographic in the advertised order

**Severity:** Critical → MITIGATED. **Priority:** P0.

1. **Exact location:** `data/lp_parameters_data.json`,
   `solve_cascade[level=3].objective_stages`; `src/gsd/solver.py`,
   `call_lp_solver()` around lines 505-612 and `build_output_contract()` around
   lines 1128-1143.
2. **Root cause:** The first stage, `sul_violation`, has `fix_optimum: false`.
   The solver only adds an objective-preserving constraint when that flag is true.
3. **Evidence (original):** Stage order is SUL, DER, adequacy; DER is fixed before
   adequacy, but SUL is not fixed before DER. `build_output_contract()` emits
   `order_verified: true` and says SUL was fixed before DER.
4. **Impact:** Later stages can increase SUL violation to improve DER or adequacy.
   The output makes a false safety claim about the minimum violation scenario.
5. **2026-07-20 mitigation:**

   **a) JSON configuration (`data/lp_parameters_data.json`).** Level 3
   `objective_stages[0].fix_optimum` is already `true` (line 506);
   `objective_stages[1].fix_optimum` is already `true` (line 511); only the last
   stage `adequacy_slack` has `fix_optimum: false` (line 516). All three stages
   execute in the declared order: `sul_violation` → `der_deviation` →
   `adequacy_slack`.

   **b) Solver enforcing path (`src/gsd/solver.py:call_lp_solver()`).** At each
   stage, if `stage.get("fix_optimum")` is true the function records the stage
   name in `fix_optimum_applied` (line 567) and injects a preserving constraint
   `prob += obj_expr <= bound` where `bound = optimal_obj * (1 + tol_rel) + tol_abs`
   (lines 569-570). The tolerance is widened by `cbc_mip_gap` when binary
   variables are present (mip_tolerance_rule, lines 563-565). The
   `fix_optimum_applied` list is returned in the raw result (line 611).

   **c) Output verification (`src/gsd/solver.py:build_output_contract()`).**
   `order_verified` is computed (not hardcoded) by comparing all non-last stage
   names against `fix_optimum_applied` (line 1134). When verification fails, the
   note field contains the actual discrepancy (lines 1140-1141).

   **d) Regression test (`tests/test_cascade_integration.py`).**
   `test_r02_regression_fix_optimum_enforces_lexicographic_order` calls
   `call_lp_solver()` directly with real Level 3 objective stages from JSON and
   validates:
   - `raw_result["fix_optimum_applied"]` contains `"sul_violation"` and
     `"der_deviation"` (all predecessor stages)
   - `raw_result["fix_optimum_applied"]` does NOT contain `"adequacy_slack"`
     (last stage)
   - `build_output_contract()` returns `order_verified: True`
   - Stage names in output match `["sul_violation", "der_deviation",
     "adequacy_slack"]`

6. **Verification:** `python -m pytest tests/ -q` — `38 passed` (new R-02 test
   included).
7. **Recommended solution:** Make every predecessor stage fixed, use a stored
   primary objective expression without the tie-break, and test a counterexample
   where a lower DER solution has higher SUL violation.
8. **Why superior:** It implements true preemptive optimization rather than an
   ordered sequence of unrelated solves.
9. **Priority rationale:** The safety diagnostic is misleading at exactly the
   point where users need a reliable `DO_NOT_FEED` explanation.

### R-03 - The deterministic tie-break is a primary objective

**Severity:** Critical → MITIGATED. **Priority:** P0.

1. **Exact location:** `src/gsd/solver.py`, `call_lp_solver()` around lines
   524-536; `data/lp_parameters_data.json.solver_params.tie_break_weight`.
2. **Root cause:** The base weight was changed to `0.001`, but each ingredient
   still receives `(det_hash(iid) % 10000) * 1e-1`, or 0 through 999.9, and the
   complete term is added to every stage.
3. **Evidence:** `obj_expr += tie_break_expr` follows every stage objective.
   Normalized nutrient deviations are normally order-one quantities; grams times
   a hash-derived coefficient are not.
4. **Impact:** Ingredient IDs, rather than nutrition, can select the result and
   contaminate the objective values used for stage fixing.
5. **2026-07-20 mitigation:**

   **a) Moved to final stage only.** The tie-break is now gated by `if not
   fix_opt` (`src/gsd/solver.py` line 524). Intermediate stages (`sul_violation`,
   `der_deviation`) solve with pure nutritional objectives; their fix_optimum
   bound contains no tie-break contamination. Only the final stage
   (`adequacy_slack` in Level 3) receives the secondary term.

   **b) Removed hash perturbation.** The old `(det_hash(iid) % 10000) * 1e-1`
   perturbation produced coefficients up to 999.9 per ingredient — large enough
   to dominate the normalized nutrition (order 1). The new code uses only
   `tie_weight` (`0.001` from JSON) for every ingredient, giving a total
   contribution of ~0.6 for a 600 g diet — negligible against nutrition
   objectives and well within fix_optimum tolerance.

   **c) Regression test (`tests/test_cascade_integration.py`).**
   `test_r03_regression_tiebreak_final_stage_only` validates that:
   - `fix_optimum_applied` contains `["sul_violation", "der_deviation"]`
     (pure nutrition stages, tie-break absent)
   - Output contract `solver_metadata.tie_break_applied` is `true`
   - The `det_hash` function is no longer present in `call_lp_solver()`
     (grep-confirmed absent)

6. **Verification:** `python -m pytest tests/ -q`.
7. **Recommended solution:** Do not blend a tie-break into protected objectives.
   First solve each nutrition stage and fix its pure value; then solve a final,
   bounded secondary objective. Use a coefficient provably smaller than the
   smallest tolerated primary-objective difference, with an automated scale test.
8. **Why superior:** Determinism is retained without changing the clinical
   optimization problem.
9. **Priority rationale:** This can overturn every result and compounds R-02.

### R-04 - Category deviation units are wrong in the output contract

**Severity:** High. **Priority:** P0.

1. **Exact location:** `src/gsd/solver.py`, category objective around lines
   725-760 and `build_output_contract()` around lines 1131-1167.
2. **Root cause:** The LP equation operates in grams, so `d_cat_*_plus/minus`
   are grams. The output adds those values directly to `target_pct` and calls the
   result a percentage.
3. **Evidence:** `cat_sum - target_pct * total_x == d_plus - d_minus`; later
   `achieved = target + (d_plus - d_minus)`.
4. **Impact:** `template_adherence` can be physically impossible and its score is
   dimensionally meaningless.
5. **Recommended solution:** Calculate output percentages from final allocations:
   `100 * category_grams / total_grams`. Normalize the LP's gram deviation by a
   fixed mass reference if a percentage-like objective is required.
6. **Why superior:** The optimization remains linear and the displayed metric is
   independently reproducible.
7. **Priority rationale:** This feature directly communicates composition quality
   to users and currently misstates it.

### R-05 - Category targets are impossible to satisfy

**Severity:** High. **Priority:** P0.

1. **Exact location:** `data/lp_parameters_data.json`, category goals for Levels
   1 and 2.
2. **Root cause:** The configured targets are 70 + 10 + 5 + 5 + 5 + 3 + 12 = 110
   percent while the current category taxonomy is disjoint.
3. **Evidence:** Both Level 1 and 2 configurations total 110; no validation checks
   the sum or declares overlapping-goal semantics.
4. **Impact:** A zero category deviation is impossible. The solver must allocate
   error by arbitrary weights and the reported score has a permanent hidden floor.
5. **Recommended solution:** Make targets sum to 100 after explicitly defining
   any overlaps; reject invalid configuration at load time.
6. **Why superior:** It makes a nutritional template a coherent policy rather
   than a permanently contradictory preference set.
7. **Priority rationale:** Every normal Level 1/2 run is affected.

### R-06 - Individual ingredient inclusion limits are ignored

**Severity:** High. **Priority:** P0.

1. **Exact location:** `data/formulation_rules.json._inclusion_semantics.description`,
   `data/DB_ingredientes.json...ingredients[*].lp_constraints`, and
   `src/gsd/solver.py:add_inclusion_constraints()` around lines 275-328.
2. **Root cause:** The data contract requires both category and per-ingredient
   limits, but the solver only iterates `formulation_rules.json.inclusion_limits`
   and category mappings.
3. **Evidence:** The DB contains `max_inclusion_pct` and `min_inclusion_pct` for
   all 23 ingredients. No solver reference to either DB field exists.
4. **Impact:** A diet can exceed ingredient-specific exposure limits even when
   category limits pass. This is especially serious for organs, fats, and any
   future supplements.
5. **Recommended solution:** Compile individual limits as `x_i <= max_i * total`
   and `x_i >= min_i * total`, with explicit level-specific relaxation policy.
   Validate that every DB limit is either enforced or explicitly marked inactive.
6. **Why superior:** It enforces the documented most-restrictive rule and keeps
   risk controls close to their ingredient data.
7. **Priority rationale:** This is a missing safety constraint, not a cosmetic
   configuration discrepancy.

### R-07 - Level 3 relaxations are unbounded, unoptimized, and unreported

**Severity:** High. **Priority:** P0.

1. **Exact location:** `src/gsd/solver.py`, inclusion slack creation around lines
   305-327, envelope slack creation around lines 386-404, and Level 3 objective
   construction around lines 630-720.
2. **Root cause:** Level 3 creates inclusion slacks and an upper-envelope slack,
   but no Level 3 objective includes them. Inclusion slacks are also not returned
   for diagnostics.
3. **Evidence:** Only nutrient/SUL/DER variables are consumed by the configured
   Level 3 stage kinds; no `inclusion_slack_vars` reaches the returned problem.
4. **Impact:** The mathematical counterfactual may violate inclusion and mass
   policy by arbitrary amounts at zero objective cost, while being described as a
   minimum-achievable diagnostic scenario.
5. **Recommended solution:** Keep structural limits hard in Level 3, or add a
   normalized inclusion-violation stage with fixed optimum and expose violations
   in `diagnostic_analysis`.
6. **Why superior:** It produces an interpretable constrained counterfactual.
7. **Priority rationale:** The fallback must be more auditable, not less, than a
   feeding recommendation.

### R-08 - Invalid selections can crash instead of failing closed

**Severity:** High. **Priority:** P0.

1. **Exact location:** `src/gsd/nutrition.py:build_matrix()` around lines 323-350;
   `src/gsd/solver.py:build_lp_problem()` around lines 50-70;
   `solve_cascade()` around lines 780-805.
2. **Root cause:** Unknown IDs become `data_incomplete` matrix entries. If none
   has measured nutrients, `build_lp_problem()` returns a partial status dict;
   `solve_cascade()` still calls `call_lp_solver()`, which indexes `prob`.
3. **Evidence:** There is no discriminated build-result branch before
   `call_lp_solver(problem, ...)`.
4. **Impact:** Empty or unknown-only user requests can yield `KeyError` instead of
   `data_incomplete` and `DO_NOT_FEED`.
5. **Recommended solution:** Validate request shape and selected IDs at the API
   boundary. Use typed domain errors or a discriminated build result, then map it
   to a structured safe output. Test empty, unknown-only, duplicate, and mixed
   selections.
6. **Why superior:** Invalid input becomes an intentional contract path instead
   of accidental exception flow.
7. **Priority rationale:** It breaks the stated output-inviolability guarantee.

### R-09 - Nutrient results are not calculated assessments

**Severity:** High. **Priority:** P0.

1. **Exact location:** `src/gsd/solver.py:build_output_contract()` around lines
   1080-1110.
2. **Root cause:** The builder inserts raw values but hardcodes `status: adequate`,
   sets `pct_of_min` and `pct_of_sul` to null, sets all `target_max` fields null,
   and uses a safety SUL as `target_min` for safety-tier nutrients.
3. **Evidence:** The source comment explicitly says the implementation is
   simplified and that real min/max computation is absent.
4. **Impact:** A result can visually claim adequacy while the corresponding
   nutrient is deficient or excessive. Downstream code cannot safely consume the
   object as a nutritional assessment.
5. **Recommended solution:** Create one canonical requirement compiler that
   supplies daily minimums, maximums, SULs, units, and status classification to
   both LP construction and output building. Make missing/unknown values explicit.
6. **Why superior:** Input constraints and output claims cannot drift apart.
7. **Priority rationale:** This is the final safety boundary presented to users.

### R-10 - Energy is estimated from universal defaults, not ingredient data

**Severity:** High. **Priority:** P1.

1. **Exact location:** `src/gsd/nutrition.py:energy_metabolizable_kcal_per_100g()`
   around lines 210-235; ingredient nutrient records in `data/DB_ingredientes.json`.
2. **Root cause:** When moisture, ash, and fibre are absent, the energy function
   substitutes 72 percent, 1 percent, and 0 respectively. All 23 current
   ingredients lack all three fields.
3. **Evidence:** The energy function derives NFE from those defaults. It supplies
   DER envelope densities, kcal output, Big-M values, and the energy-normalized
   conversion denominator.
4. **Impact:** Total grams and calories are based on a generic muscle-meat
   assumption even for fat sources and organs. The effect does not cancel for DER,
   envelope, kcal reporting, or safety limits expressed per energy.
5. **Recommended solution:** Require measured proximate composition or a cited ME
   value for each executable ingredient. Store uncertainty/range data and reject
   missing-energy ingredients from recommendation mode.
6. **Why superior:** Energy becomes traceable, ingredient-specific input rather
   than hidden policy.
7. **Priority rationale:** Energy scaling is fundamental to life-stage nutrition.

### R-11 - Clinical-floor fallback exists only in JSON and documentation

**Severity:** High. **Priority:** P1.

1. **Exact location:** `data/lp_parameters_data.json.solve_cascade[level=3]
   .clinical_floor.fallback_if_infeasible`; `src/gsd/solver.py` around lines
   425-466 and 780-805.
2. **Root cause:** JSON promises a retry without the floor. The cascade never
   rebuilds Level 3 with `apply_clinical_floor=False`, and no code assigns
   `clinical_floor_relaxed=True`.
3. **Evidence:** The flag is only read with `get(..., False)` later in output and
   diagnostics.
4. **Impact:** Floor-induced infeasibility becomes `structurally_infeasible`,
   contradicting the promised diagnostic fallback.
5. **Recommended solution:** Implement an explicit retry transition, record both
   attempts, and test a selection infeasible only because of the floor. Otherwise
   remove the unsupported configuration promise.
6. **Why superior:** Configuration and executable behavior have one state model.
7. **Priority rationale:** The defect affects an exceptional path but that path is
   safety-sensitive.

### R-12 - Fat adequacy check is advisory print logic, not policy

**Severity:** High. **Priority:** P1.

1. **Exact location:** `src/gsd/solver.py:check_fat_source_adequacy()` around
   lines 1367 onward; `src/gsd/cli.py` around lines 238-248.
2. **Root cause:** The function estimates composition using an equal average of
   non-fat selected ingredients. The CLI prints its result, but `solve_cascade()`
   does not receive or enforce it and output construction does not include it.
3. **Evidence:** The function is invoked by the runtime CLI before solve; there is
   no invocation in `solve_cascade()`.
4. **Impact:** The declared Level 1-to-Level 2 conditional delegation is neither
   a constraint nor an output-contract decision. It can disagree with the actual
   LP and has no safety effect.
5. **Recommended solution:** Delete the heuristic or formulate the condition from
   actual LP variables and policy. If it is a pre-solver screen, return a typed
   cascade transition and include the exact evidence in the final output.
6. **Why superior:** A safety rule becomes deterministic and testable.
7. **Priority rationale:** It concerns fat adequacy in growing dogs and currently
   creates false confidence through console output.

### R-13 - Scenario resolution is inconsistent and silent

**Severity:** Medium. **Priority:** P1.

1. **Exact location:** `src/gsd/solver.py` around lines 143-153 and
   `src/gsd/nutrition.py` around lines 160-165.
2. **Root cause:** Unknown scenarios produce an empty target set in LP assembly,
   while DER independently defaults to `slow_growth_recommended`.
3. **Evidence:** Both use fallback-style dictionary access; neither validates the
   request ID against `scenarios.json` at the boundary.
4. **Impact:** A typo can combine fallback energy with no scenario deviation
   objective and no disclosure.
5. **Recommended solution:** Resolve one typed scenario at request validation and
   pass it to both DER and LP compilation; reject unknown IDs.
6. **Why superior:** All policy values originate from one audited object.
7. **Priority rationale:** Avoidable silent input errors can alter nutrition.

### R-14 - Validation is permissive where safety requires fail-closed behavior

**Severity:** Medium. **Priority:** P1.

1. **Exact location:** `src/gsd/nutrition.py:validate_inputs()` around lines
   80-95; `src/gsd/core.py:validate_ingredients_against_schema()`; `data/`.
2. **Root cause:** Ingredient schema non-conformance becomes a warning. Only the
   ingredient DB and LP parameters have JSON Schema files; most operational JSON
   is accepted through ad hoc access.
3. **Evidence:** `validate_inputs()` does not raise for `non_confirming > 0`.
   There is no schema inventory for constraints, formulation rules, scenarios,
   growth data, toxicological limits, provenance, or objective weights.
4. **Impact:** Invalid data can reach a solver that assumes shape, units, and
   semantics. The failure can be a silent zero coefficient rather than an error.
5. **Recommended solution:** Define Draft 2020-12 schemas for every executable
   file, add cross-file semantic validation, and block recommendation mode on any
   invalid or unresolved critical datum.
6. **Why superior:** Schema validation becomes a safety gate instead of a report.
7. **Priority rationale:** Data quality is inseparable from solver correctness.

### R-15 - Tier policy is not fully declarative

**Severity:** Medium. **Priority:** P2.

1. **Exact location:** `src/gsd/solver.py:add_nutrient_constraints()` around
   lines 220-255.
2. **Root cause:** Every `CSTR_NB_*_MIN` is forced to `adequacy_soft` by ID,
   overriding `NUTRIENT_REGISTRY.constraint_tier`.
3. **Evidence:** The prefix branch executes before the registry fallback.
4. **Impact:** Changing data configuration does not necessarily change behavior;
   a future safety-tier minimum can silently be relaxed.
5. **Recommended solution:** Put tier authority in one registry/constraint record,
   validate consistency, and remove ID-prefix policy.
6. **Why superior:** Policy changes become reviewable data changes.
7. **Priority rationale:** It is technical debt today and a safety regression risk
   when the model evolves.

### R-16 - Objective-weight data are dead configuration

**Severity:** Medium. **Priority:** P2.

1. **Exact location:** `data/objective_weights.json`; `src/gsd/mapa.py` and
   `src/gsd/core.py` index it; `src/gsd/solver.py` does not consume it.
2. **Root cause:** Detailed weights are maintained as a separate policy artifact
   but solver objective construction uses only hardcoded criticality mapping and
   the LP-parameter antagonism map.
3. **Evidence:** Searches find `objective_weights` in documentation/index paths,
   not in LP construction.
4. **Impact:** Maintainers can edit a file believing clinical priorities changed
   when no solve changes.
5. **Recommended solution:** Either compile and validate this file into objective
   coefficients or remove it and maintain one source of truth.
6. **Why superior:** It eliminates silent policy drift.
7. **Priority rationale:** Important for maintainability after P0 correctness.

### R-17 - Infeasibility diagnostics are generic

**Severity:** Medium. **Priority:** P2.

1. **Exact location:** `src/gsd/solver.py:call_lp_solver()` around lines 540-550
   and fallback output around lines 820-855.
2. **Root cause:** Any non-optimal CBC status becomes a bare `infeasible` result;
   final explanation is a fixed generic sentence.
3. **Evidence:** No constraint residual report, conflict refiner/IIS procedure,
   solver status detail, or distinction between timeout and true infeasibility is
   retained.
4. **Impact:** Users and maintainers cannot identify the constraint or data change
   responsible for an infeasible diet.
5. **Recommended solution:** Preserve CBC status, calculate violations against a
   relaxed feasibility model, and report a ranked conflict set. Treat timeout as a
   separate status.
6. **Why superior:** It creates actionable diagnostics without pretending CBC
   natively supplies a complete IIS.
7. **Priority rationale:** Needed for trustworthy operation and debugging.

### R-18 - Tests do not independently prove the safety claims

**Severity:** Medium. **Priority:** P2.

1. **Exact location:** `tests/test_cascade_integration.py` and
   `tests/test_dimensional_pipeline.py`.
2. **Root cause:** Many tests assert output shape, configured stage names, or
   metadata such as `order_verified`; several use synthetic fixtures. They do not
   assert independent daily nutrient/SUL outcomes on vetted real reference cases.
3. **Evidence:** A test can pass when `order_verified` is hardcoded true even
   though R-02 proves stage preservation is absent. Current coverage also lacks
   empty/unknown request, category-unit, category-sum, individual-limit, and
   clinical-floor-retry tests.
4. **Impact:** The suite can confirm implementation self-consistency while missing
   policy failure and nutritional invalidity.
5. **Recommended solution:** Add signed golden cases with independently calculated
   inputs and expected outputs; property tests for unit conversion and constraints;
   mutation tests for each safety branch; and end-to-end tests through the public
   request contract.
6. **Why superior:** Tests validate observable behavior against an external oracle,
   not the same assumptions used to implement it.
7. **Priority rationale:** Essential before claiming P0 fixes are complete.

## 5. Architecture and data-flow assessment

The package split into `core`, `nutrition`, `solver`, `mapa`, and `cli` is a real
improvement over a root-level monolith. It is still not a clean dependency model:
`solver.py` owns LP compilation, objective policy, solver invocation, cascade
transition, output mapping, diagnostics, and validation. The hand-off defect in
R-01 is a direct consequence of that untyped dictionary architecture.

The recommended target architecture is:

```mermaid
flowchart LR
    A[Validated Request] --> B[Typed Scenario and Ingredient Snapshot]
    B --> C[Requirement Compiler]
    B --> D[LP Model Builder]
    C --> D
    D --> E[Pure Stage Objectives]
    E --> F[CBC Adapter]
    F --> G[Result Classifier and Diagnostics]
    C --> G
    G --> H[Validated Output Contract]
```

The `Requirement Compiler` should be the sole owner of units, daily minima,
maxima, SULs, inclusion policies, and their identifiers. The LP and output layers
should consume that immutable representation; neither should re-derive targets
from different JSON paths.

## 6. Remediation roadmap

### P0 - Block all feeding recommendations

1. Repair R-01, then test effective objective coefficients.
2. Implement true lexicographic solves and remove the contaminated tie-break
   from primary objectives (R-02, R-03).
3. Disable category goals until their units and 110-percent configuration are
   fixed (R-04, R-05).
4. Enforce individual limits and make every Level 3 relaxation explicit,
   optimized, and reported (R-06, R-07).
5. Fail closed for invalid selections and replace placeholder nutrient results
   with calculated classifications (R-08, R-09).

### P1 - Establish credible nutrition and configuration behavior

1. Replace universal energy defaults with ingredient data and uncertainty bounds
   (R-10).
2. Implement or remove the clinical-floor fallback promise (R-11).
3. Replace display-only fat heuristic with an actual policy transition (R-12).
4. Add closed request schemas for scenarios and all executable JSON artifacts
   (R-13, R-14).

### P2 - Make the system maintainable and auditable

1. Remove hardcoded tier rules and dead policy files (R-15, R-16).
2. Add infeasibility explanation and distinguish timeout from infeasibility
   (R-17).
3. Build nutritionist-reviewed golden cases and independent property tests
   (R-18).
4. Split `solver.py` into model builder, objective factory, solver adapter,
   diagnostics, and output serializer.

## 7. Release gate

Do not label output `SAFE_TO_FEED` until all P0 work is complete, tests execute
in a reproducible environment, and a veterinary nutritionist has independently
reviewed real-data golden cases for large-breed growth and adult maintenance.
Until then, the only responsible product posture is an internal research tool with
no feeding recommendation authority.
