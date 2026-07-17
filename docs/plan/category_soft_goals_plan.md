# Implementation Plan: Category Soft Goals (Option B)

**Status**: APPROVED FOR IMPLEMENTATION  
**Version**: 1.0  
**Date**: 2026-07-17  
**Author**: opencode  

---

## 1. Summary

Implement soft goals for ingredient category percentages (muscle_meat 70%, organ_secreting 10%, etc.) as **penalized deviations** in the LP objective. Only categories with existing DB ingredients are included. Categories without ingredients (bone, vegetable, fruit, seed, supplement, grain, dairy, egg) are excluded.

This is **Option B** from the critical analysis - minimal risk, maximum value, zero structural changes.

---

## 2. Summary

| Aspect | Decision |
|--------|----------|
| Categories with ingredients | 8 categories (muscle_meat, fish, organ_secreting, organ_non_secreting, muscle_organ, connective_tissue, blood_source, fat_source) |
| Categories without ingredients | 8 categories (SKIPPED: bone, cartilage, supplement, grain, vegetable, fruit, dairy, egg) |
| Goal type | Soft goals (penalized deviation variables) - NOT hard constraints |
| Cascade level | Level 1 (new stage in objective_stages) + Level 2 (reuse deviation vars) |
| Mechanism | Deviation variables d_cat_<name>_minus/plus added to objective with weights |

---

## 3. Categories & Targets

| Goal Name | Target % | Weight | DB Categories | Ingredients Count |
|-----------|----------|--------|---------------|-------------------|
| muscle_meat | 70% | 100 | muscle_meat, fish | 5 |
| organ_secreting | 10% | 80 | organ_secreting | 6 |
| organ_non_secreting | 5% | 40 | organ_non_secreting | 2 |
| muscle_organ | 5% | 40 | muscle_organ | 3 |
| connective_tissue | 5% | 30 | connective_tissue | 2 |
| blood_source | 3% | 30 | blood_source | 2 |
| fat_source | 12% | 60 | fat_source | 3 |

**Note**: Targets sum to 110% (70+10+5+5+5+3+12 = 110%). Will adjust to 70/10/5/5/5/3/2 = 100% for muscle_organ=5, fat_source=2%, or keep as-is with soft penalties allowing overshoot. See Section 4 for calibration.

---

## 4. Weight Calibration

**Principle**: Weights must be comparable to existing objective scale.

- Level 1 goal_deviation: sum of nutrient deviations (41 nutrients x clinical weights 1-10)
- Antagonism slack penalty: 5000 per constraint (from lp_parameters_data.json)
- **Category goal weights**: 30-100 -> total ~440, comparable to nutrient deviation scale

**Calibration method**: Run synthetic test, verify category goals influence solution without dominating nutrient targets.

---

## 5. Implementation Steps

### 5.1 Data: lp_parameters_data.json
Add category_goals config to Level 1 and Level 2 solve_cascade entries.

### 5.2 Code: build_pipeline.py
1. **New function**: add_category_goals(prob, x_vars, total, category_goals, problem_dict, db) - creates deviation vars + constraints
2. **New objective kind**: category_goal_deviation in _build_stage_objective()
3. **Pass db** to build_lp_problem() for category lookup
4. **Output**: Add category_goal_deviations to build_output_contract()

### 5.3 Tests: test_cascade_integration.py
- test_category_goals_in_level1_objective() - verify deviation vars created
- test_category_goals_influence_solution() - synthetic test with known solution
- test_category_goals_relaxed_at_level2() - verify Level 2 uses slack
- test_category_goals_output_contract() - verify output includes deviations

### 5.4 Documentation Updates
- sat_solver_contrato.md - add category_goal_deviations to output contract
- sat_pipeline_codigo.md - document new objective kind + function
- indice_plano_central.md - update changelog

---

## 6. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Weight calibration off | Medium | Low | Synthetic test + manual inspection |
| PuLP API mismatch | Low | High | Use prob.add_variable() pattern from existing code |
| Category lookup failure | Low | Medium | Defensive: skip if no ingredients in category |
| Cascade order regression | Low | High | Test Level 1-2-3 descent still works |
| Output contract change | Low | Medium | Non-breaking: new field only |

---

## 7. Acceptance Criteria

- [ ] All 32 existing tests pass
- [ ] 4 new tests pass
- [ ] --gate-mapa passes
- [ ] Synthetic test: muscle_meat goal pulls solution toward 70%
- [ ] Level 3 still returns unsafe_diagnostic for liver-only
- [ ] No new hard constraints introduced
- [ ] MAPA regeneration clean

---

## 8. Timeline

| Phase | Duration |
|-------|----------|
| 5.1 Data + 5.2 Code | 2-3 hours |
| 5.3 Tests | 1 hour |
| 5.4 Documentation | 30 min |
| Validation | 30 min |
| **Total** | **~4-5 hours** |

---

## 9. Approval

**Approved by**: User  
**Implementation start**: Upon confirmation  
**Rollback plan**: git revert single commit if issues arise
