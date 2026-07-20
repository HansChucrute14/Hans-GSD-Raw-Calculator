# Systemic Review: Pipeline Code vs. Satellite Architecture Documents

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
| Clinical criticality weighting | ❌ BUG | All 3 slack branches use `weight = 1.0` instead of `clinical_criticality` from registry. 33 of 41 nutrients have wrong weight. |

### Level 3 — Lexicographic SUL Diagnostic
| Element | Status | Evidence |
|---|---|---|
| Stage 3A: minimize SUL violation | ✅ | `minimize_normalized_sul_violation` correctly sums `v_j⁺ / SUL_j` |
| Stage 3B: minimize DER deviation | ✅ | `minimize_absolute_der_deviation` uses `dev_plus + dev_minus` |
| Stage 3C: minimize adequacy slack | ⚠️ BUG | Same `weight = 1.0` issue as Level 2 |
| Fix optimum between stages | ✅ | `fix_optimum` respected with tolerance |
| Clinical floor MILP | ✅ | Binary variables, Big-M per ingredient, fallback relaxation |

## Code Quality Findings

### F1: `_build_stage_objective` Missing Registry Parameter (CRITICAL)

**Location:** `solver.py:607-616`  
**Issue:** Function signature does not accept `registry` or `lp_params`. `build_lp_problem` loads registry at line 38 (`registry = lp_params.get("NUTRIENT_REGISTRY", {})`) but never passes it to `_build_stage_objective`. The registry is available in `problem_dict` implicitly but the objective builder doesn't extract it.

**Impact:** All 3 objective branches that need `clinical_criticality` (lines 650, 668, 702) use `weight = 1.0` instead.

### F2: Hardcoded `weight = 1.0` (CRITICAL)

**Locations:** Lines 650, 668, 702  
**Issue:** Comment says `# clinical_criticality weight from registry` but the actual code is `weight = 1.0`.  
**Impact:** All nutrients treated equally in adequacy slack minimization. A calcium deficiency (critical, should be 10×) is penalized the same as a valine deficiency (low, weight 1.0).

**Evidence from registry:**
- 8 nutrients with `critical` criticality (should weight 10.0): calcium_g, phosphorus_g, protein_g, zinc_mg, lysine_g, methionine_plus_cystine_g, vitamin_d3_iu, epa_plus_dha_g
- 7 nutrients with `high` criticality (should weight 5.0): fat_g, choline_g, copper_mg, iron_mg, linoleic_acid_g, sodium_g, vitamin_a_iu
- 18 nutrients with `moderate` criticality (should weight 2.0)
- 8 nutrients with `low` criticality (weight 1.0 — coincidentally correct)

### F3: `goal_deviation` Not Normalized (MODERATE)

**Location:** `solver.py:672-694`  
**Issue:** Level 1 `goal_deviation` uses `expr += d_minus + d_plus` without dividing by `target`. The `weighted_normalized_deviation` branch (line 654-670) correctly normalizes with `/ target`. This means nutrients with large absolute targets (protein ~60g) dominate those with small targets (selenium ~0.03mg), even if both are equally deficient in percentage terms.

### F4: Tie-Break Weight Dominance (MODERATE)

**Location:** `solver.py:518-531`  
**Issue:** `tie_break_weight = 1000.0` added to EVERY stage objective. For a typical 5-ingredient selection with ~500g total, tie-break contribution ≈ 500,000. This dwarfs the normalized objective terms (typically 0-50 range). The tie-break should be secondary, not dominant.

**Per sat_solver_contrato §8.1:** "Secondary objective applied ONLY to the final stage... Never blend the tie-break into an intermediate stage — its magnitude would swamp fix_optimum_tolerance_abs."

### F5: `build_output_contract` Uses Non-Existent `has_sul` Field (MINOR)

**Location:** `solver.py:1076`  
**Issue:** `target_min = ndata.get("has_sul") if ndata.get("has_sul") else None` — the NUTRIENT_REGISTRY has NO `has_sul` field (verified: 0 of 41 entries). This means `target_min` is always `None` for all nutrients. Should use `constraint_tier == "safety_hard"` or check `sul_value` presence.

### F6: `validate_output` Not Implemented as Standalone (MINOR)

**Location:** `sat_pipeline_codigo.md §6.4a` specifies `validate_output()` as mandatory signature.  
**Reality:** `validate_output` exists at line 1276 in solver.py. It works but some assertions are incomplete (e.g., `len(nutrient_results) >= 41` is checked but individual field validation is partial).

## Data Contract Findings

### D1: `envelope_soft` Tier Present But Unused in NUTRIENT_REGISTRY

**Issue:** `sat_dados_schema.md §4.2` defines 3 tiers: `safety_hard`, `adequacy_soft`, `envelope_soft`. The NUTRIENT_REGISTRY has 33 `adequacy_soft` + 8 `safety_hard` = 41 total. No entries have `envelope_soft`. This is correct — envelope is a constraint type, not a nutrient. But the `add_envelope_constraints` function correctly checks `"envelope_soft" in relax_tiers`.

### D2: `constraints.json` Structure — Dict of 4 Arrays

**Verified:** `constraints.json` is a dict with keys `mineral_antagonisms` (5), `toxicological_limits` (8), `inclusion_constraints` (6), `nutrient_bounds` (41). Total 60. All code accesses these correctly via `constraints.get("nutrient_bounds", [])` etc.

## Summary of Required Fixes

| # | Severity | Description | Fix Location |
|---|---|---|---|
| F1 | CRITICAL | Pass `registry` to `_build_stage_objective` via `problem_dict` | `solver.py:169-184` (add to problem_dict), `solver.py:607` (extract from problem_dict) |
| F2 | CRITICAL | Replace `weight = 1.0` with `CRITICALITY_WEIGHT[registry[nid]["clinical_criticality"]]` | `solver.py:650, 668, 702` |
| F3 | MODERATE | Normalize `goal_deviation` by target: `expr += (d_minus + d_plus) / target` | `solver.py:683` |
| F4 | MODERATE | Move tie-break to final stage only, reduce weight to 10.0 | `solver.py:516-531` |
| F5 | MINOR | Fix `has_sul` → `sul_value` check in `build_output_contract` | `solver.py:1076` |

## Verification Commands

```bash
# After fixes:
python -m pytest tests/ -q          # Should pass 36 tests
python build_pipeline.py --validate-db  # Should pass
python build_pipeline.py --generate-mapa  # Should regenerate MAPA
grep -c "TASK4-DEBUG" src/gsd/solver.py  # Should be 0
```
