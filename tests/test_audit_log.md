## test_cascade_level1_feasible_for_balanced_selection
- **Expected:** suboptimal (missing calcium at Level 2)
- **Got:** solver_status=suboptimal, level=2, gaps=27, allocations=4 items
- **Passed:** False

## test_cascade_level2_triggered_by_unbalanced_selection
- **Expected:** suboptimal
- **Got:** solver_status=suboptimal, level=2, gaps=27, allocations=3 items
- **Passed:** True

## test_cascade_level3_triggered_by_sul_collision
- **Expected:** unsafe_diagnostic
- **Got:** solver_status=unsafe_diagnostic, level=3, gaps=29, allocations=null (Level 3 — mechanical barrier)
- **Passed:** True

## test_cascade_never_skips_levels
- **Expected:** contiguous
- **Got:** solver_status=None, level=None, gaps=0, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

## test_single_ingredient_returns_result
- **Expected:** non-blank
- **Got:** solver_status=suboptimal, level=2, gaps=28, allocations=1 items
- **Passed:** False

## test_single_ingredient_sul_collision_no_allocations
- **Expected:** unsafe_diagnostic
- **Got:** solver_status=unsafe_diagnostic, level=3, gaps=29, allocations=null (Level 3 — mechanical barrier)
- **Passed:** True

## test_level3_lexicographic_order_validated
- **Expected:** lexicographic_valid
- **Got:** solver_status=unsafe_diagnostic, level=3, gaps=29, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

## test_level3_no_degenerate_solution
- **Expected:** non-degenerate
- **Got:** solver_status=unsafe_diagnostic, level=3, gaps=29, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

## test_level3_clinical_floor_prevents_irrelevant_xi
- **Expected:** floor-enforced
- **Got:** solver_status=unsafe_diagnostic, level=3, gaps=29, allocations=null (Level 3 — mechanical barrier)
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
- **Got:** solver_status=unsafe_diagnostic, level=3, gaps=29, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

## test_audit_log_written
- **Expected:** log_written
- **Got:** solver_status=None, level=None, gaps=0, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

## test_level1_optimal_synthetic
- **Expected:** optimal_with_valid_allocations
- **Got:** solver_status=optimal, level=None, gaps=0, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

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

## test_r01_regression_all_keys_present_and_weighted
- **Expected:** R-01 fix verified
- **Got:** solver_status=None, level=None, gaps=0, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

## test_r02_regression_fix_optimum_enforces_lexicographic_order
- **Expected:** R-02 fix verified
- **Got:** solver_status=None, level=None, gaps=0, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

## test_r03_regression_tiebreak_final_stage_only
- **Expected:** R-03 fix verified
- **Got:** solver_status=None, level=None, gaps=0, allocations=null (Level 3 — mechanical barrier)
- **Passed:** False

## test_category_goals_enabled_by_default_after_phase4b
- **Expected:** true
- **Got:** category_goals_enabled=True

## test_disabled_output_is_explicit_not_fake_100
- **Expected:** explicit disabled state, no fake 100.0
- **Got:** disabled=True, overall_score=None, components={}

## test_gate_suppresses_dcat_variables_when_disabled
- **Expected:** disabled=[] , enabled=4 vars
- **Got:** disabled=[], enabled=['d_cat_fs_minus', 'd_cat_fs_plus', 'd_cat_mm_minus', 'd_cat_mm_plus']

## test_enabled_flag_restores_variable_creation_end_to_end
- **Expected:** d_cat vars created when enabled
- **Got:** d_cat_count=4

## test_template_adherence_percentages_reproducible_from_allocations
- **Expected:** all achieved_pct reproducible from allocations[]
- **Got:** level=2, goals_checked=4

## test_achieved_pct_on_percent_scale_not_grams
- **Expected:** percent scale
- **Got:** all in [0,100]

## test_shipped_config_targets_sum_to_100_both_levels
- **Expected:** valid
- **Got:** both levels sum 100

## test_validator_rejects_corrupted_110_config_level_0
- **Expected:** raises CategoryGoalsConfigError
- **Got:** corrupted level index 0 raised

## test_validator_rejects_corrupted_110_config_level_1
- **Expected:** raises CategoryGoalsConfigError
- **Got:** corrupted level index 1 raised

## test_validator_ignores_levels_without_category_goals
- **Expected:** level 3 ok
- **Got:** no raise

## test_derive_bound_math
- **Expected:** max_contribution=1.0, tolerance=0.01, within_bound=False
- **Got:** {'tie_break_weight': 0.001, 'max_single_ingredient_grams': 1000.0, 'max_contribution': 1.0, 'tolerance': 0.01, 'within_bound': False}

## test_derive_bound_tiny
- **Expected:** within_bound=True
- **Got:** {'tie_break_weight': 1e-08, 'max_single_ingredient_grams': 1000.0, 'max_contribution': 1e-05, 'tolerance': 0.01, 'within_bound': True}

## test_oversized_weight_raises
- **Expected:** raises in config mode
- **Got:** TieBreakConfigError raised

## test_oversized_weight_scaled
- **Expected:** scaled below tolerance
- **Got:** effective=9.9e-06, contribution=0.0099

## test_within_bound_unchanged
- **Expected:** unchanged 1e-8
- **Got:** effective=1e-08

## test_current_config_within_bound
- **Expected:** effective contribution < tolerance
- **Got:** configured=5e-06, configured_contribution=0.005, effective=5e-06, tolerance=0.01

## test_solver_reports_bounded_weight
- **Expected:** used * max_big_m < tolerance
- **Got:** tie_break_weight_used=5e-06, max_big_m=1295.5598344101325, tolerance=0.01

## test_id_permutation_preserves_nutrition_outcome
- **Expected:** identical nutrition outcome across ID permutation
- **Got:** nutrient_sig_equal=True, total_grams=(1250.440695,1250.440695), pair_grams=(1168.6609,1168.6609), fix_applied=['sul_violation', 'der_deviation']

## test_identical_clones_have_identical_coefficients
- **Expected:** clones nutritionally identical to base and each other
- **Got:** clones_equal=True

