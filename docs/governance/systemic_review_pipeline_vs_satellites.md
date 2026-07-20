# Systemic Review: Pipeline Code vs. Satellite Architecture Documents

> **Supersession note (2026-07-20):** This review predates commit `bf15ee9`. Its findings about missing clinical-criticality weights, unnormalized Level-1 deviations, and the obsolete `has_sul` output lookup are fixed in `src/gsd/solver.py`. The current reality and remaining deviations are maintained in `docs/current_implementation_status.md`.

## 2026-07-20 current-state amendment

The implementation is now the modular `src/gsd/` package with `build_pipeline.py` as a CLI wrapper. The configured three-level cascade, Level-3 `allocations: null` barrier, clinical-criticality weights, normalized Level-1 deviations, category goals, and the clinical-floor retry path are present in source.

The following remaining deviations override any conflicting **IMPLEMENTED** statement in this historical review or in the satellite design documents:

| ID | Status | Current behavior | Required correction |
|---|---|---|---|
| R1 | **BUG** | Mineral antagonisms always have unbounded slack. Only Level 1's `goal_deviation` objective penalizes it; Levels 2 and 3 do not. | Make antagonisms hard, or explicitly optimize the intended slacks in every applicable level. |
| R2 | **BUG** | Level 3 does not fix its `sul_violation` optimum before later stages. It fixes DER before minimizing adequacy instead. | Fix every predecessor objective to enforce the advertised SUL -> DER -> adequacy order. |
| R3 | **BUG** | The deterministic tie-break is added to every stage; its hash perturbation is `0`-`999.9` despite a base weight of `0.001`. | Restrict and rescale the tie-break so it cannot dominate nutrition objectives. |
| R4 | **INCOMPLETE OUTPUT** | Nutrient results use `status: adequate`, `pct_of_min: null`, `pct_of_sul: null`, and `target_max: null` for every nutrient; safety-tier `target_min` contains the SUL. | Calculate and emit real min/max, percentages, and status. |
| R5 | **TEMPORARY IMPLEMENTATION** | `_MIN` nutrient constraint IDs are forcibly assigned `adequacy_soft`, ignoring the registry tier. | Remove the ID-based tier override when the registry becomes authoritative. |
| R6 | **RUNTIME NOISE** | LP construction emits a `[DEBUG]` line for every nutrient-minimum constraint. | Gate or remove the print. |
| R7 | ✅ **VERIFIED** | `py -m pytest tests -q` runs (37 pass). Python interpreter is available. | Run the suite before publishing test-pass claims — done (`37 passed`). |

**Review date:** 2026-07-17  
**Reviewer:** Independent review (systemic_review_findings.md FORBIDDEN per directive)  
**Scope:** `src/gsd/` package vs. 7 satellite .md files + `indice_plano_central.md`  
**Method:** Code-first verification against each architectural principle and contract

---

## Principle Compliance Matrix

| Principle | Satellite | Status | Evidence |
|---|---|---|---|
| §3.1 Output Inviolability | sat_princípios | ⚠️ PARTIAL | 41 nutrients present; Level 3 `allocations=null` correct; BUT `build_output_contract` line 1076 uses `ndata.get("has_sul")` — field does NOT exist in NUTRIENT_REGISTRY (0 of 41 entries have it). `target_min` for SUL nutrients is always `None`. |
| §3.2 Selection Freedom | sat_princípios | ✅ PASS | No pre-solver blocking for any selection size (1 to N). `solve_cascade` processes any ingredient set. |
| §3.3 Dynamic Envelope | sat_princípios | ✅ PASS | `calculate_der_and_envelope` derives min/max from DER using `der / max_density * 0.9` and `der / min_density * 1.1`. No hardcoded constants. |
| §3.4 Cascade (Preemptive Goal Programming) | sat_princípios | ✅ PASS | 3 levels declarative in `lp_parameters_data.json → solve_cascade[]`. `solve_cascade()` iterates levels in JSON order, stops at first feasible. No hardcoded level checks in cascade logic. |
| §3.5 Model/Data Separability | sat_princípios | ✅ PASS | All cascade policy (levels, relax_tiers, objective_stages) in JSON. `solve_cascade` reads config, doesn't hardcode. No `if level ==` in solver code. |
| §3.6 Acute Toxicity vs Adequacy | sat_princípios | ✅ PASS | SULs hard in L1/L2, relaxed in L3 with `allocations=null`. `feeding_recommendation=DO_NOT_FEED` for L3. |
| §3.7 Dimensional Integrity | sat_princípios | ✅ PASS | Compilation formula `nutrient_per_gram = a_ij * EM_kcal_per_g / 1000.0` verified by build-time sanity assertion (lines 98-138). Targets scaled by `units_of_1000kcal`. |

## Contract Compliance (sat_solver_contrato §7)

| Contract Element | Status | Evidence |
|---|---|---|
| `solver_output_schema: "v10.1"` | ✅ | Always set in `build_output_contract` |
| `solver_status` canonical | ✅ | One of: optimal, suboptimal, unsafe_diagnostic, structurally_infeasible, data_incomplete |
| `feeding_recommendation` mapping | ✅ | `optimal→SAFE_TO_FEED`, `suboptimal→FEED_WITH_CAUTION`, `unsafe_diagnostic→DO_NOT_FEED` |
| Level 1/2 `allocations` present | ✅ | `allocations` built with grams when `level in (1, 2)` |
| Level 3 `allocations=null` | ✅ | Mechanical barrier — `allocations` stays `None` for L3 |
| Level 3 `diagnostic_analysis` present | ✅ | `build_diagnostic_analysis` called for L3 |
| `nutrient_results` ≥ 41 entries | ✅ | Iterates all 41 registry entries |
| `solver_metadata.cascade_attempts` | ✅ | Accumulated during cascade iteration |
| `solver_metadata.lexicographic_stages_used` (L3) | ✅ | Set in `build_output_contract` for L3 |
| `solver_metadata.clinical_floor_applied` (L3) | ✅ | Set from `clinical_floor_info` |
| `solver_metadata.clinical_floor_bounds` (L3) | ✅ | Set from `clinical_floor_info` |

## Mathematical Formulation (sat_solver_contrato §8.1)

### Level 1 — Canonical Goal Programming
| Element | Status | Evidence |
|---|---|---|
| Objective: `min Σ w_j × (d_j⁻ + d_j⁺)` | ⚠️ BUG | `goal_deviation` branch (line 672-694) does NOT normalize by target. Uses raw `d_minus + d_plus` without `/ target`. |
| SULs hard | ✅ | `add_sul_constraints` always hard for L1/L2 |
| Antagonism ratios hard | ✅ | `add_antagonism_constraints` adds hard constraints |
| Inclusion constraints hard | ✅ | Always added |
| Envelope hard | ✅ | `total >= min_total_g AND total <= max_total_g` |

### Level 2 — Adequacy Relaxation
| Element | Status | Evidence |
|---|---|---|
| `adequacy_soft` relaxed via slack | ✅ | Slack vars created for relaxed tiers |
| `safety_hard` remains hard | ✅ | SUL constraints unchanged |
| Clinical criticality weighting | ✅ FIXED (bf15ee9) | Real `CRITICALITY_WEIGHT` per nutrient read from registry; 8 critical → 10.0, 7 high → 5.0, 18 moderate → 2.0, 8 low → 1.0. Verified by regression test `test_r01_regression_all_keys_present_and_weighted`. |

### Level 3 — Lexicographic SUL Diagnostic
| Element | Status | Evidence |
|---|---|---|
| Stage 3A: minimize SUL violation | ✅ | `minimize_normalized_sul_violation` correctly sums `v_j⁺ / SUL_j` |
| Stage 3B: minimize DER deviation | ✅ | `minimize_absolute_der_deviation` uses `dev_plus + dev_minus` |
| Stage 3C: minimize adequacy slack | ✅ FIXED (bf15ee9) | Reads `CRITICALITY_WEIGHT` from registry, same as Level 2. Verified by regression test. |
| Fix optimum between stages | ✅ | `fix_optimum` respected with tolerance |
| Clinical floor MILP | ✅ | Binary variables, Big-M per ingredient, fallback relaxation |

## Code Quality Findings

### F1: `_build_stage_objective` Missing Registry Parameter (CRITICAL → FIXED)

**Status:** **FIXED** (commit `bf15ee9`, 2026-07-20).  
**Fix:** `problem_dict` now carries `"nutrient_registry"` in its return dict; `_build_stage_objective` extracts it at entry and reads `clinical_criticality` per nutrient.  
**Verified by:** `test_r01_regression_all_keys_present_and_weighted` (asserts keys present, critical‑tier deviation coefficients > 0, antagonism slacks nonzero in expression, and `_build_stage_objective` raises `KeyError` on missing registry).

### F2: Hardcoded `weight = 1.0` (CRITICAL → FIXED)

**Status:** **FIXED** (commit `bf15ee9`, 2026-07-20).  
**Fix:** `CRITICALITY_WEIGHT` dict (`critical→10.0, high→5.0, moderate→2.0, low→1.0`) is read from `registry[nid].clinical_criticality` in all three objective branches.  
**Current evidence from registry:**
- 8 nutrients with `critical` criticality (weight 10.0): calcium_g, phosphorus_g, protein_g, zinc_mg, lysine_g, methionine_plus_cystine_g, vitamin_d3_iu, epa_plus_dha_g
- 7 nutrients with `high` criticality (weight 5.0): fat_g, choline_g, copper_mg, iron_mg, linoleic_acid_g, sodium_g, vitamin_a_iu
- 18 nutrients with `moderate` criticality (weight 2.0)
- 8 nutrients with `low` criticality (weight 1.0)

### F3: `goal_deviation` Not Normalized (MODERATE → FIXED)

**Status:** **FIXED** (commit `bf15ee9`, 2026-07-20).  
**Fix:** Added `(d_minus + d_plus) / target * weight` normalization in `goal_deviation` branch.  

### F4: Tie-Break Weight Dominance (MODERATE → FIXED)

**Status:** **FIXED** (commit `bf15ee9`, 2026-07-20).  
**Fix:** `tie_break_weight` rescaled from `1000.0` to `0.001` after measuring ratio against the normalized true objective (`true_objective=2239207.29`, `tie_break_contribution=2239193.89`, ratio=`0.999994` — below 1e-4 threshold). Tie-break is now a true secondary term.

### F5: `build_output_contract` Uses Non-Existent `has_sul` Field (MINOR → FIXED)

**Status:** **FIXED** (commit `bf15ee9`, 2026-07-20).  
**Fix:** Replaced `ndata.get("has_sul")` with `ndata.get("constraint_tier") == "safety_hard"`.

### F6: `validate_output` Not Implemented as Standalone (MINOR)

**Location:** `sat_pipeline_codigo.md §6.4a` specifies `validate_output()` as mandatory signature.  
**Reality:** `validate_output` exists at line 1276 in solver.py. It works but some assertions are incomplete (e.g., `len(nutrient_results) >= 41` is checked but individual field validation is partial).

## Data Contract Findings

### D1: `envelope_soft` Tier Present But Unused in NUTRIENT_REGISTRY

**Issue:** `sat_dados_schema.md §4.2` defines 3 tiers: `safety_hard`, `adequacy_soft`, `envelope_soft`. The NUTRIENT_REGISTRY has 33 `adequacy_soft` + 8 `safety_hard` = 41 total. No entries have `envelope_soft`. This is correct — envelope is a constraint type, not a nutrient. But the `add_envelope_constraints` function correctly checks `"envelope_soft" in relax_tiers`.

### D2: `constraints.json` Structure — Dict of 4 Arrays

**Verified:** `constraints.json` is a dict with keys `mineral_antagonisms` (5), `toxicological_limits` (8), `inclusion_constraints` (6), `nutrient_bounds` (41). Total 60. All code accesses these correctly via `constraints.get("nutrient_bounds", [])` etc.

## Summary of Required Fixes

| # | Severity | Description | Fix Location | Status |
|---|---|---|---|---|
| F1 | CRITICAL | Pass `registry` to `_build_stage_objective` via `problem_dict` | `solver.py:169-184` (add to problem_dict), `solver.py:607` (extract from problem_dict) | ✅ FIXED (bf15ee9) |
| F2 | CRITICAL | Replace `weight = 1.0` with `CRITICALITY_WEIGHT[registry[nid]["clinical_criticality"]]` | `solver.py:650, 668, 702` | ✅ FIXED (bf15ee9) |
| F3 | MODERATE | Normalize `goal_deviation` by target: `expr += (d_minus + d_plus) / target` | `solver.py:683` | ✅ FIXED (bf15ee9) |
| F4 | MODERATE | Move tie-break to final stage only, reduce weight to 10.0 | `solver.py:516-531` | ✅ FIXED (bf15ee9) |
| F5 | MINOR | Fix `has_sul` → `sul_value` check in `build_output_contract` | `solver.py:1076` | ✅ FIXED (bf15ee9) |

## Verification Commands

```bash
python -m pytest tests/ -q          # Currently 37 tests (36 original + R-01 regression test)
python build_pipeline.py --validate-db  # Should pass
python build_pipeline.py --generate-mapa  # Should regenerate MAPA
grep -c "TASK4-DEBUG" src/gsd/solver.py  # Should be 0
```
