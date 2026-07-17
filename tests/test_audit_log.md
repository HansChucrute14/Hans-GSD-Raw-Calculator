## test_cascade_level1_feasible_for_balanced_selection
- **Expected:** unsafe_diagnostic (Ca:P wall at Level 3)
- **Got:** solver_status=unsafe_diagnostic, level=3, gaps=5, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

## test_cascade_level2_triggered_by_unbalanced_selection
- **Expected:** suboptimal
- **Got:** solver_status=unsafe_diagnostic, level=3, gaps=5, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

## test_cascade_level3_triggered_by_sul_collision
- **Expected:** unsafe_diagnostic
- **Got:** solver_status=structurally_infeasible, level=3, gaps=0, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

## Category Goal Tests (4 new)

## test_single_ingredient_returns_result
- **Expected:** non-blank
- **Got:** solver_status=structurally_infeasible, level=3, gaps=0, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

## test_single_ingredient_sul_collision_no_allocations
- **Expected:** unsafe_diagnostic
- **Got:** solver_status=structurally_infeasible, level=3, gaps=0, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

## test_level3_lexicographic_order_validated
- **Expected:** lexicographic_valid
- **Got:** solver_status=structurally_infeasible, level=3, gaps=0, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

## test_level3_no_degenerate_solution
- **Expected:** non-degenerate
- **Got:** solver_status=structurally_infeasible, level=3, gaps=0, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

## test_level3_clinical_floor_prevents_irrelevant_xi
- **Expected:** floor-enforced
- **Got:** solver_status=structurally_infeasible, level=3, gaps=0, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

## test_tie_break_produces_identical_output_on_repeat_runs
- **Expected:** identical
- **Got:** solver_status=None, level=None, gaps=0, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

## test_solver_timeout_returns_result
- **Expected:** timeout_handled
- **Got:** solver_status=None, level=None, gaps=0, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

## test_structurally_infeasible_selection_returns_explicit_status
- **Expected:** structurally_infeasible
- **Got:** solver_status=structurally_infeasible, level=3, gaps=0, allocations=null (Level 3 — mechanical barrier)
- **Passed:** True

## test_audit_log_written
- **Expected:** log_written
- **Got:** solver_status=None, level=None, gaps=0, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

## test_category_goals_present_across_cascade_levels
- **Expected:** verified
- **Got:** template_adherence present at Level 3 (unsafe_diagnostic), structure valid
- **Passed:** True

## test_category_goals_are_wired_into_problem_dict
- **Expected:** wired_ok
- **Got:** solver_status=None, level=None, gaps=0, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

## test_category_goal_deviations_appear_in_output
- **Expected:** present
- **Got:** solver_status=None, level=None, gaps=0, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

## test_category_goals_present_across_cascade_levels
- **Expected:** verified
- **Got:** solver_status=None, level=None, gaps=0, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

## test_category_goal_deviations_output_contract
- **Expected:** contract_valid
- **Got:** solver_status=None, level=None, gaps=0, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

